"""检查数据集目录：场景、样本数、参考视图元数据。

用法：
    set CROSSVIEW_DATA_ROOT=D:\\桌面放置\\26年大创
    python scripts/inspect_dataset.py
    python scripts/inspect_dataset.py --root D:/桌面放置/26年大创 --mode satellite
"""

from __future__ import annotations

import argparse

from crossview.adaptors.datasets.anyvisloc import AnyVisLocAdapter
from crossview.paths import data_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None, help="数据集根目录；默认读 CROSSVIEW_DATA_ROOT")
    parser.add_argument("--mode", default="aerial", help="参考视图模式：aerial / satellite")
    args = parser.parse_args()

    root = args.root or data_root()
    adapter = AnyVisLocAdapter(root, mode=args.mode)

    scenes = adapter.scenes()
    if not scenes:
        print(f"{root} 下没有找到任何场景（需要 *_reference.json）")
        return 1

    print(f"数据集根：{root}")
    for scene in scenes:
        ref = adapter.reference(scene)
        count = sum(1 for _ in adapter.iter_scene_samples(scene))
        print(f"\n场景 {scene}  [{ref.mode}]")
        print(f"  参考图    : {ref.map_path}")
        print(f"  DSM       : {ref.dsm_path}")
        print(f"  地图分辨率: {ref.map_resolution}")
        print(f"  地图原点  : {ref.map_origin_local}")
        print(f"  样本数    : {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
