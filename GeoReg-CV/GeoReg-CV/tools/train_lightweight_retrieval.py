"""Train a MobileNetV3 cross-view retrieval encoder on AnyVisLoc.

The positive reference is an aerial-map crop centered at the UAV ground-truth
position stored in each sample NPZ. In-batch negatives provide the contrastive
training signal. This script is intentionally independent of the official CAMP
implementation so the frozen baseline remains reproducible.
"""

from __future__ import annotations

import argparse
import json
import random
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large


def scene_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


# Aerial maps are very large; keep only one decoded map to avoid exhausting
# RAM when samples are shuffled across scenes on Windows.
@lru_cache(maxsize=1)
def load_scene_meta(scene_dir: str) -> tuple[str, float, float]:
    scene = Path(scene_dir)
    ref = next(scene.glob("L??_reference.json"))
    data = json.loads(ref.read_text(encoding="utf-8"))
    mode = data["modes"]["aerial"]
    return str(scene / mode["map_path"]), float(mode["map_resolution"][0]), float(mode["map_resolution"][1])


@lru_cache(maxsize=1)
def load_map(path: str, downsample: int) -> np.ndarray:
    flags = {1: cv2.IMREAD_COLOR, 2: cv2.IMREAD_REDUCED_COLOR_2,
             4: cv2.IMREAD_REDUCED_COLOR_4, 8: cv2.IMREAD_REDUCED_COLOR_8}
    image = cv2.imread(path, flags.get(downsample, cv2.IMREAD_REDUCED_COLOR_4))
    if image is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


class AnyVisLocPairs(Dataset):
    def __init__(self, root: str, scenes: list[str], crop_size: int = 384, jitter_px: int = 32, max_samples: int | None = None, map_downsample: int = 4, training: bool = True):
        self.root = Path(root)
        self.crop_size = crop_size
        self.map_downsample = map_downsample
        self.training = training
        self.jitter_px = jitter_px
        self.paths = []
        for scene in scenes:
            self.paths.extend(sorted((self.root / scene).glob("L??_????.npz")))
        if not self.paths:
            raise FileNotFoundError(f"No AnyVisLoc NPZ samples found for {scenes} under {root}")
        if max_samples is not None:
            self.paths = self.paths[:max_samples]
        ops = [transforms.ToPILImage(), transforms.Resize((crop_size, crop_size))]
        if training:
            ops += [transforms.RandomHorizontalFlip(0.5), transforms.ColorJitter(0.15, 0.15, 0.15, 0.05)]
        ops += [transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]
        self.transform = transforms.Compose(ops)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        path = self.paths[index]
        with np.load(path, allow_pickle=True) as data:
            image = data["image"]
            if image.size == 0:
                rel = str(data["image_relpath"].item())
                image = cv2.cvtColor(cv2.imread(str(path.parent / rel)), cv2.COLOR_BGR2RGB)
            xyz = np.asarray(data["xyz"], dtype=np.float32)
        map_path, rx, ry = load_scene_meta(str(path.parent))
        ref = load_map(map_path, self.map_downsample)
        # AnyVisLoc local coordinates use x/y in metres and map origins are 0.
        scale = self.map_downsample
        cx, cy = int(round(float(xyz[0]) / (rx * scale))), int(round(float(xyz[1]) / (ry * scale)))
        half = max(1, self.crop_size // (2 * scale))
        jx = random.randint(-self.jitter_px // scale, self.jitter_px // scale) if self.jitter_px else 0
        jy = random.randint(-self.jitter_px // scale, self.jitter_px // scale) if self.jitter_px else 0
        cx, cy = cx + jx, cy + jy
        x0, y0 = max(0, cx - half), max(0, cy - half)
        x1, y1 = min(ref.shape[1], cx + half), min(ref.shape[0], cy + half)
        crop = ref[y0:y1, x0:x1]
        if crop.size == 0:
            crop = np.zeros((self.crop_size, self.crop_size, 3), dtype=np.uint8)
        return self.transform(image), self.transform(crop), path.stem


class RetrievalNet(nn.Module):
    def __init__(self, embedding_dim: int = 512, pretrained: bool = True):
        super().__init__()
        weights = MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
        base = mobilenet_v3_large(weights=weights)
        self.features = base.features
        self.pool = base.avgpool
        self.projection = nn.Sequential(
            nn.Linear(base.classifier[0].in_features, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(1024, embedding_dim),
        )

    def forward(self, x):
        x = self.pool(self.features(x)).flatten(1)
        return F.normalize(self.projection(x), dim=1)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-root", default="D:/GD/Benchmark/Data/AnyVisLoc")
    p.add_argument("--train-scenes", default=",".join(f"Scene_{i:02d}" for i in range(1, 21)))
    p.add_argument("--val-scenes", default="Scene_21,Scene_22,Scene_23,Scene_24")
    p.add_argument("--crop-size", type=int, default=384)
    p.add_argument("--embedding-dim", type=int, default=512)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--temperature", type=float, default=0.07)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--device", default="cuda")
    p.add_argument("--output-dir", default="D:/GeoReg-CV/experiments/lightweight_backbone/mobilenetv3_large")
    p.add_argument("--no-pretrained", action="store_true")
    p.add_argument("--max-train-samples", type=int, default=None)
    p.add_argument("--max-val-samples", type=int, default=None)
    p.add_argument("--map-downsample", type=int, choices=[1, 2, 4, 8], default=4)
    return p.parse_args()


def main():
    args = parse_args()
    random.seed(1); np.random.seed(1); torch.manual_seed(1)
    device = torch.device(args.device if args.device == "cpu" or torch.cuda.is_available() else "cpu")
    train_set = AnyVisLocPairs(args.dataset_root, scene_list(args.train_scenes), args.crop_size, max_samples=args.max_train_samples, map_downsample=args.map_downsample)
    val_set = AnyVisLocPairs(args.dataset_root, scene_list(args.val_scenes), args.crop_size, jitter_px=0, max_samples=args.max_val_samples, map_downsample=args.map_downsample)
    # Samples are stored scene-by-scene and aerial maps are very large. Keep
    # scene order so the one-map cache is reused instead of decoding a map for
    # nearly every shuffled sample; crop jitter still changes each positive.
    train_loader = DataLoader(train_set, args.batch_size, shuffle=False, num_workers=args.workers, pin_memory=device.type == "cuda", drop_last=True)
    val_loader = DataLoader(val_set, args.batch_size, shuffle=False, num_workers=args.workers, pin_memory=device.type == "cuda")
    model = RetrievalNet(args.embedding_dim, pretrained=not args.no_pretrained).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scaler = torch.cuda.amp.GradScaler(enabled=device.type == "cuda")
    output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    history = []
    for epoch in range(1, args.epochs + 1):
        model.train(); total = 0.0
        for batch_index, (query, reference, _) in enumerate(train_loader, 1):
            query, reference = query.to(device, non_blocking=True), reference.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                q, r = model(query), model(reference)
                logits = q @ r.T / args.temperature
                labels = torch.arange(logits.shape[0], device=device)
                loss = (F.cross_entropy(logits, labels) + F.cross_entropy(logits.T, labels)) * 0.5
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
            total += loss.item() * query.shape[0]
            if batch_index % 10 == 0:
                print(f"Epoch {epoch}/{args.epochs} batch {batch_index}/{len(train_loader)} loss={loss.item():.4f}", flush=True)
        model.eval(); correct = 0; seen = 0
        with torch.inference_mode():
            for query, reference, _ in val_loader:
                q, r = model(query.to(device)), model(reference.to(device))
                rank = (q @ r.T).argmax(1)
                correct += int((rank == torch.arange(rank.numel(), device=device)).sum())
                seen += rank.numel()
        row = {"epoch": epoch, "train_loss": total / len(train_set), "val_batch_recall1": correct / max(seen, 1)}
        history.append(row); print(row)
        torch.save({"model": model.state_dict(), "args": vars(args), "epoch": epoch}, output / "last.pth")
    (output / "train_history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
