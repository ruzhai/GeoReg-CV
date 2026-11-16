import argparse
from pathlib import Path

from crossview.visualization.sample_panel import render_from_selection


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate success/failure sample visualization panels."
    )
    parser.add_argument(
        "--archive",
        default=r"D:\GeoReg-CV\experiments\baseline_anyvisloc_scene01\frozen_scene01_full_baseline_20260809-2323",
        help="Frozen baseline archive directory containing all_results.csv.",
    )
    parser.add_argument(
        "--selection",
        default=r"D:\GeoReg-CV\outputs\scene01_system_demo\system_demo_summary.json",
        help="System demo summary containing selected sample IDs.",
    )
    parser.add_argument(
        "--dataset-root",
        default=r"D:\GD\Benchmark\Data\AnyVisLoc",
        help="AnyVisLoc dataset root.",
    )
    parser.add_argument(
        "--output",
        default=r"D:\GeoReg-CV\outputs\scene01_sample_visualizations",
        help="Output directory.",
    )
    args = parser.parse_args()

    render_from_selection(
        Path(args.archive) / "all_results.csv",
        args.selection,
        args.dataset_root,
        args.output,
    )
    print(f"Sample visualizations written to: {args.output}")


if __name__ == "__main__":
    main()
