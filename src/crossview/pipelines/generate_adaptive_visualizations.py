import argparse
import csv
from pathlib import Path

from crossview.paths import data_root, outputs_dir
from crossview.visualization.sample_panel import render_sample_panel


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate CDA-FastReg adaptive sample visualization panels."
    )
    parser.add_argument(
        "--input",
        default=outputs_dir() / "scene01_cda_fastreg_demo" / "scene01_cda_demo_geo_positions.csv",
    )
    parser.add_argument("--dataset-root", default=data_root() / "Data" / "AnyVisLoc")
    parser.add_argument("--output", default=outputs_dir() / "scene01_cda_fastreg_visualizations")
    args = parser.parse_args()

    rows = read_csv(Path(args.input))
    output = Path(args.output)
    for row in rows:
        route = row.get("adaptive_route", "unknown") or "unknown"
        sample_id = row["sample_id"]
        render_sample_panel(
            row,
            rows,
            args.dataset_root,
            output / route / f"{sample_id}_cda_panel.png",
        )
    print(f"CDA-FastReg visualizations written to: {output}")


if __name__ == "__main__":
    main()
