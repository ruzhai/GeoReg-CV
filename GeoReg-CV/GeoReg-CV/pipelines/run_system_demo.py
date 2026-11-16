import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from system.result_loader import (
    latest_archive_from_pointer,
    load_records_from_csv,
    save_records_csv,
    save_records_json,
)
from system.sample_selector import select_demo_records
from system.simulation_exporter import export_simulation_json
from visualization.svg_map import render_position_svg


def summarize(records):
    errors = [r.error_m for r in records]
    return {
        "num_records": len(records),
        "mean_error_m": sum(errors) / len(errors) if errors else 0,
        "max_error_m": max(errors) if errors else 0,
        "success_1m": sum(r.success_1m for r in records) / len(records) if records else 0,
        "success_3m": sum(r.success_3m for r in records) / len(records) if records else 0,
        "success_5m": sum(r.success_5m for r in records) / len(records) if records else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a GeoReg-CV system demo package from frozen baseline results.")
    parser.add_argument(
        "--latest",
        default=r"D:\GeoReg-CV\experiments\baseline_anyvisloc_scene01\LATEST_SCENE01_FULL_BASELINE.txt",
        help="Pointer file containing archive_dir=...",
    )
    parser.add_argument(
        "--output",
        default=r"D:\GeoReg-CV\outputs\scene01_system_demo",
        help="Output directory for system-level geo-position and visualization files.",
    )
    args = parser.parse_args()

    archive_dir = latest_archive_from_pointer(args.latest)
    records = load_records_from_csv(archive_dir / "all_results.csv")
    selected = select_demo_records(records)
    demo_records = selected["success_within_1m"] + selected["boundary_1m_to_5m"] + selected["failure_over_5m"]

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    save_records_csv(records, output_dir / "scene01_all_geo_positions.csv")
    save_records_json(records, output_dir / "scene01_all_geo_positions.json")
    save_records_csv(demo_records, output_dir / "scene01_demo_geo_positions.csv")
    save_records_json(demo_records, output_dir / "scene01_demo_geo_positions.json")
    export_simulation_json(demo_records, output_dir / "scene01_simulation_points.json")
    render_position_svg(demo_records, output_dir / "scene01_demo_position_map.svg")

    summary = {
        "source_archive": str(archive_dir),
        "output_dir": str(output_dir),
        "overall": summarize(records),
        "demo_selection": {key: [r.sample_id for r in value] for key, value in selected.items()},
    }
    with (output_dir / "system_demo_summary.json").open("w", encoding="utf-8-sig") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    report = f"""# GeoReg-CV Scene_01 系统演示包

## 系统功能闭环

```text
观察者视角图像
  -> 无人机/航拍参考视图
  -> 跨视角检索与匹配
  -> PnP 几何定位
  -> 地理位置输出
  -> 可视化/仿真展示数据
```

## 输出文件

- `scene01_all_geo_positions.csv/json`：全部样本的位置估计结果；
- `scene01_demo_geo_positions.csv/json`：用于展示的成功、边界和失败样本；
- `scene01_simulation_points.json`：后续仿真软件可读取的位置点数据；
- `scene01_demo_position_map.svg`：真实位置与估计位置对比图；
- `system_demo_summary.json`：系统演示包摘要。

## 总体指标

- 样本数：{summary['overall']['num_records']}
- Mean Error：{summary['overall']['mean_error_m']:.4f} m
- Max Error：{summary['overall']['max_error_m']:.4f} m
- Success@1m：{summary['overall']['success_1m'] * 100:.2f}%
- Success@3m：{summary['overall']['success_3m'] * 100:.2f}%
- Success@5m：{summary['overall']['success_5m'] * 100:.2f}%

## 说明

该演示包不改变 AnyVisLoc baseline 的算法结果，只把 baseline 输出转化为课题系统需要的统一地理位置格式、展示样本和仿真数据格式。
"""
    (output_dir / "README.md").write_text(report, encoding="utf-8-sig")

    print(f"System demo package written to: {output_dir}")
    print(f"Demo map: {output_dir / 'scene01_demo_position_map.svg'}")
    print(f"Simulation JSON: {output_dir / 'scene01_simulation_points.json'}")


if __name__ == "__main__":
    main()
