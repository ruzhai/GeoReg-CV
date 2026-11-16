"""Benchmark a lightweight retrieval backbone without changing AnyVisLoc.

This is an engineering benchmark only. It measures the candidate encoder
before retrieval fine-tuning; it must not be reported as a localization result.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large

from crossview.paths import experiments_dir


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input-size", type=int, default=384)
    p.add_argument("--embedding-dim", type=int, default=512)
    p.add_argument("--device", default="cuda")
    p.add_argument("--warmup", type=int, default=20)
    p.add_argument("--iterations", type=int, default=100)
    p.add_argument("--no-pretrained", action="store_true", help="Do not download ImageNet weights.")
    p.add_argument(
        "--output",
        default=experiments_dir() / "lightweight_backbone" / "mobilenetv3_large" / "benchmark.json",
    )
    return p.parse_args()


class MobileNetV3Retrieval(torch.nn.Module):
    def __init__(self, embedding_dim: int = 512, pretrained: bool = True):
        super().__init__()
        weights = MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
        net = mobilenet_v3_large(weights=weights)
        self.features = net.features
        self.pool = net.avgpool
        self.projection = torch.nn.Linear(net.classifier[0].in_features, embedding_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.pool(x).flatten(1)
        x = torch.nn.functional.normalize(self.projection(x), dim=1)
        return x


def main() -> None:
    args = parse_args()
    requested = args.device
    device = torch.device(requested if requested == "cpu" or torch.cuda.is_available() else "cpu")
    model = MobileNetV3Retrieval(pretrained=not args.no_pretrained).eval().to(device)
    x = torch.randn(1, 3, args.input_size, args.input_size, device=device)
    with torch.inference_mode():
        for _ in range(args.warmup):
            model(x)
        if device.type == "cuda":
            torch.cuda.synchronize()
        start = time.perf_counter()
        for _ in range(args.iterations):
            model(x)
        if device.type == "cuda":
            torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    result = {
        "model": "mobilenet_v3_large",
        "input_size": args.input_size,
        "embedding_dim": args.embedding_dim,
        "device": str(device),
        "parameters": sum(p.numel() for p in model.parameters()),
        "latency_ms": elapsed * 1000.0 / args.iterations,
        "fps": args.iterations / elapsed,
        "note": "Encoder-only benchmark; retrieval fine-tuning and localization are not included.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
