"""Evaluate MobileNetV3 query-to-reference-crop retrieval on AnyVisLoc pairs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent))
from train_lightweight_retrieval import AnyVisLocPairs, RetrievalNet, scene_list  # noqa: E402

from crossview.paths import data_root


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-root", default=data_root() / "Data" / "AnyVisLoc")
    p.add_argument("--scenes", default="Scene_21,Scene_22,Scene_23,Scene_24")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--crop-size", type=int, default=384)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--device", default="cuda")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    device = torch.device(
        args.device if args.device == "cpu" or torch.cuda.is_available() else "cpu"
    )
    ckpt = torch.load(args.checkpoint, map_location="cpu")
    dim = int(ckpt.get("args", {}).get("embedding_dim", 512))
    model = RetrievalNet(dim, pretrained=False).to(device).eval()
    model.load_state_dict(ckpt["model"])
    data = AnyVisLocPairs(
        args.dataset_root, scene_list(args.scenes), args.crop_size, jitter_px=0, training=False
    )
    loader = DataLoader(data, args.batch_size, shuffle=False, num_workers=args.workers)
    queries, refs = [], []
    with torch.inference_mode():
        for query, reference, _ in loader:
            queries.append(model(query.to(device)).cpu())
            refs.append(model(reference.to(device)).cpu())
    q, r = torch.cat(queries), torch.cat(refs)
    ranks = []
    for start in range(0, len(q), 256):
        sims = q[start : start + 256] @ r.T
        order = sims.argsort(dim=1, descending=True)
        target = torch.arange(start, min(start + 256, len(q))).unsqueeze(1)
        hit = (order == target).nonzero()
        ranks.extend((hit[:, 1] + 1).tolist())
    result = {
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "scenes": scene_list(args.scenes),
        "queries": len(q),
        "recall@1": 100.0 * sum(x <= 1 for x in ranks) / len(ranks),
        "recall@5": 100.0 * sum(x <= 5 for x in ranks) / len(ranks),
        "recall@10": 100.0 * sum(x <= 10 for x in ranks) / len(ranks),
        "protocol": "Each query's ground-truth reference crop is its paired gallery item; use for training sanity check, not final geo-localization benchmark.",
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
