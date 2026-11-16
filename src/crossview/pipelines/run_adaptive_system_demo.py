import argparse
import json
from pathlib import Path

from crossview.adaptors.io.results import save_records_csv, save_records_json
from crossview.adaptors.io.simulation import export_simulation_json
from crossview.core.metrics.selection import select_demo_records
from crossview.core.routing.builder import build_adaptive_records, summarize_adaptive_records
from crossview.paths import experiments_dir, outputs_dir
from crossview.visualization.svg_map import render_position_svg


def find_latest_result_csv(run_root: Path) -> Path:
    candidates = sorted(
        run_root.glob("*_1scenes/aerial/aerial-CAMP-Roma-yp/all_results.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No all_results.csv found under {run_root}")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CDA-FastReg adaptive system demo outputs.")
    parser.add_argument("--threshold", type=int, default=1000)
    parser.add_argument("--fallback-topk", type=int, default=2, choices=[2, 5])
    parser.add_argument(
        "--top1-root",
        default=experiments_dir() / "fast_baseline_ablation" / "fast_v2_top1_k1500_r03_limit120",
    )
    parser.add_argument(
        "--top2-root",
        default=experiments_dir()
        / "fast_baseline_ablation"
        / "fast_v3_true_top2_k1500_r03_limit120",
    )
    parser.add_argument(
        "--top5-root",
        default=experiments_dir() / "fast_baseline_ablation" / "standard_top5_k3000_r04_limit120",
    )
    parser.add_argument("--output", default=outputs_dir() / "scene01_cda_fastreg_demo")
    args = parser.parse_args()

    top1_csv = find_latest_result_csv(Path(args.top1_root))
    fallback_root = Path(args.top2_root if args.fallback_topk == 2 else args.top5_root)
    fallback_csv = find_latest_result_csv(fallback_root)

    records = build_adaptive_records(
        top1_csv=top1_csv,
        fallback_csv=fallback_csv,
        threshold=args.threshold,
        fallback_topk=args.fallback_topk,
    )
    selected = select_demo_records(records)
    demo_records = (
        selected["success_within_1m"] + selected["boundary_1m_to_5m"] + selected["failure_over_5m"]
    )

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_records_csv(records, output_dir / "scene01_cda_all_geo_positions.csv")
    save_records_json(records, output_dir / "scene01_cda_all_geo_positions.json")
    save_records_csv(demo_records, output_dir / "scene01_cda_demo_geo_positions.csv")
    save_records_json(demo_records, output_dir / "scene01_cda_demo_geo_positions.json")
    export_simulation_json(demo_records, output_dir / "scene01_cda_simulation_points.json")
    render_position_svg(demo_records, output_dir / "scene01_cda_demo_position_map.svg")

    summary = summarize_adaptive_records(records)
    summary.update(
        {
            "method": "CDA-FastReg",
            "threshold": args.threshold,
            "fallback_topk": args.fallback_topk,
            "top1_csv": str(top1_csv),
            "fallback_csv": str(fallback_csv),
            "output_dir": str(output_dir),
            "demo_selection": {
                key: [r.sample_id for r in value] for key, value in selected.items()
            },
        }
    )
    with (output_dir / "system_demo_summary.json").open("w", encoding="utf-8-sig") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    readme = f"""# Scene_01 CDA-FastReg 系统演示包

本目录展示 CDA-FastReg 自适应快速空间配准策略的系统输出。

## 策略

```text
先执行 Top1 快速路径；
若 Top1 best_inliers >= {args.threshold}，直接输出；
否则回退到 Top{args.fallback_topk} 精配准。
```

## 指标

- 样本数：{summary["num_records"]}
- Success@1m：{summary["success_1m"] * 100:.2f}%
- Success@3m：{summary["success_3m"] * 100:.2f}%
- Success@5m：{summary["success_5m"] * 100:.2f}%
- Mean Error：{summary["mean_error_m"]:.4f} m
- Mean Time：{summary["mean_time_s"]:.4f} s
- Fallback Ratio：{summary["fallback_ratio"] * 100:.2f}%

## 输出文件

- `scene01_cda_all_geo_positions.csv/json`：全部 CDA-FastReg 样本输出；
- `scene01_cda_demo_geo_positions.csv/json`：展示样本输出；
- `scene01_cda_simulation_points.json`：含自适应路径的仿真点位数据；
- `scene01_cda_demo_position_map.svg`：真实位置与估计位置对比图；
- `system_demo_summary.json`：系统摘要。
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8-sig")

    print(f"CDA-FastReg demo written to: {output_dir}")
    print(f"All records: {output_dir / 'scene01_cda_all_geo_positions.csv'}")
    print(f"Simulation JSON: {output_dir / 'scene01_cda_simulation_points.json'}")


if __name__ == "__main__":
    main()
