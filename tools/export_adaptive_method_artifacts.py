import csv
import json
from pathlib import Path

from crossview.paths import docs_dir, experiments_dir

SIM_DIR = Path(experiments_dir() / "fast_baseline_ablation" / "adaptive_strategy_simulation")
OUT_DIR = Path(experiments_dir() / "fast_baseline_ablation" / "adaptive_method_artifacts")
DOCS_DIR = Path(docs_dir())
FIG_DIR = DOCS_DIR / "figures"
REPORTS_DIR = DOCS_DIR / "reports"


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def as_float(row, key):
    try:
        return float(row[key])
    except Exception:
        return 0.0


def make_paper_table(summary_rows):
    keep = {
        "Standard_Top5",
        "Fixed_Top2",
        "Fixed_Top1",
        "Adaptive_T1000_else_Top2",
        "Adaptive_T1500_else_Top2",
        "Adaptive_T1000_else_Top5",
    }
    table = []
    for row in summary_rows:
        if row["method"] not in keep:
            continue
        table.append(
            {
                "Method": row["method"],
                "Success@1m(%)": f"{as_float(row, 'success_1m_pct'):.2f}",
                "Success@3m(%)": f"{as_float(row, 'success_3m_pct'):.2f}",
                "Success@5m(%)": f"{as_float(row, 'success_5m_pct'):.2f}",
                "Mean Error(m)": f"{as_float(row, 'mean_error_m'):.2f}",
                "Median Error(m)": f"{as_float(row, 'median_error_m'):.3f}",
                "Mean Time(s)": f"{as_float(row, 'mean_time_s'):.2f}",
                "Speedup": f"{as_float(row, 'mean_speedup_vs_standard'):.2f}x",
                "Fallback Ratio(%)": f"{as_float(row, 'fallback_pct'):.2f}",
                ">20m": row["over20m"],
            }
        )
    return table


def md_table(rows):
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] + ["---:"] * (len(headers) - 1)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    return "\n".join(lines)


def render_flow_svg(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="760" viewBox="0 0 1500 760">
  <defs>
    <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
      <path d="M2,2 L10,6 L2,10 Z" fill="#334155"/>
    </marker>
    <style>
      .title{font:700 34px 'Microsoft YaHei', Arial; fill:#0f172a}
      .sub{font:400 18px 'Microsoft YaHei', Arial; fill:#475569}
      .box{fill:#f8fafc; stroke:#334155; stroke-width:2.2; rx:18}
      .fast{fill:#ecfeff; stroke:#0891b2}
      .judge{fill:#fff7ed; stroke:#ea580c}
      .fallback{fill:#fef2f2; stroke:#dc2626}
      .out{fill:#f0fdf4; stroke:#16a34a}
      .txt{font:600 22px 'Microsoft YaHei', Arial; fill:#0f172a}
      .small{font:400 17px 'Microsoft YaHei', Arial; fill:#475569}
      .edge{stroke:#334155; stroke-width:2.4; fill:none; marker-end:url(#arrow)}
      .yes{stroke:#16a34a}
      .no{stroke:#dc2626}
      .badge{font:600 18px 'Microsoft YaHei', Arial}
    </style>
  </defs>
  <rect width="1500" height="760" fill="#ffffff"/>
  <text x="55" y="58" class="title">CDA-FastReg：置信度驱动的自适应快速空间配准策略</text>
  <text x="55" y="92" class="sub">先走 Top1 快速路径；若匹配内点数不足，则回退到 Top2/Top5 精配准路径，兼顾速度与稳健性。</text>

  <rect x="80" y="170" width="220" height="110" class="box"/>
  <text x="190" y="215" text-anchor="middle" class="txt">观察者视角图像</text>
  <text x="190" y="248" text-anchor="middle" class="small">oblique query</text>

  <rect x="370" y="170" width="250" height="110" class="box fast"/>
  <text x="495" y="207" text-anchor="middle" class="txt">Top1 快速路径</text>
  <text x="495" y="238" text-anchor="middle" class="small">检索 + RoMa 匹配 + PnP</text>
  <text x="495" y="263" text-anchor="middle" class="small">平均 16.42 s</text>

  <rect x="710" y="155" width="270" height="140" class="box judge"/>
  <text x="845" y="205" text-anchor="middle" class="txt">置信度判断</text>
  <text x="845" y="238" text-anchor="middle" class="small">best_inliers ≥ T ?</text>
  <text x="845" y="265" text-anchor="middle" class="small">推荐 T=1000</text>

  <rect x="1080" y="105" width="280" height="115" class="box out"/>
  <text x="1220" y="150" text-anchor="middle" class="txt">高置信：直接输出</text>
  <text x="1220" y="183" text-anchor="middle" class="small">估计地理位置</text>

  <rect x="1080" y="330" width="280" height="130" class="box fallback"/>
  <text x="1220" y="374" text-anchor="middle" class="txt">低置信：回退</text>
  <text x="1220" y="407" text-anchor="middle" class="small">Top2 / Top5 精配准</text>
  <text x="1220" y="434" text-anchor="middle" class="small">回退比例约 8.33%</text>

  <rect x="710" y="560" width="360" height="115" class="box out"/>
  <text x="890" y="604" text-anchor="middle" class="txt">最终空间位置输出</text>
  <text x="890" y="637" text-anchor="middle" class="small">Pred(x,y,z) + Error + 可视化/仿真数据</text>

  <path d="M300 225 L365 225" class="edge"/>
  <path d="M620 225 L705 225" class="edge"/>
  <path d="M980 205 C1020 180 1040 165 1075 162" class="edge yes"/>
  <text x="1012" y="168" class="badge" fill="#16a34a">Yes</text>
  <path d="M980 255 C1035 295 1040 360 1075 386" class="edge no"/>
  <text x="1015" y="329" class="badge" fill="#dc2626">No</text>
  <path d="M1220 220 L1220 510 C1220 590 1135 618 1075 618" class="edge yes"/>
  <path d="M1080 420 C990 455 925 505 900 555" class="edge no"/>

  <rect x="85" y="405" width="500" height="210" rx="18" fill="#f8fafc" stroke="#cbd5e1"/>
  <text x="115" y="445" class="txt">实验观察（Scene_01 limit=120）</text>
  <text x="115" y="482" class="small">Standard Top5：Success@5m 98.33%，Mean Time 23.72s</text>
  <text x="115" y="514" class="small">Fixed Top1：Success@5m 91.67%，Mean Time 16.42s</text>
  <text x="115" y="546" class="small">Adaptive Top1→Top2：Success@5m 99.17%，Mean Time 17.43s</text>
  <text x="115" y="578" class="small">结论：保留稳健性，同时获得约 1.36× 平均加速</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    summary_path = SIM_DIR / "adaptive_strategy_summary.csv"
    rows = read_csv(summary_path)
    paper_rows = make_paper_table(rows)

    table_csv = OUT_DIR / "table_cda_fastreg_ablation.csv"
    write_csv(table_csv, paper_rows)

    flow_svg = FIG_DIR / "cda_fastreg_flow.svg"
    render_flow_svg(flow_svg)

    best = next(r for r in rows if r["method"] == "Adaptive_T1000_else_Top2")
    report = f"""# CDA-FastReg 自适应快速空间配准方法

## 方法名称

- 中文：置信度驱动的自适应快速空间配准方法
- 英文：Confidence-Driven Adaptive Fast Registration
- 简写：CDA-FastReg

## 方法动机

AnyVisLoc 标准 Top5 流程定位较稳健，但单样本平均耗时较长。固定 Top1 快速路径可以降低耗时，但严重失败样本明显增加。因此，本文采用自适应策略：优先使用 Top1 快速路径，并利用匹配内点数评估定位置信度；当置信度不足时，自动回退到 Top2 或 Top5 精配准路径。

## 在线策略

```text
1. 输入观察者视角图像；
2. 执行 Top1 快速配准；
3. 读取 Top1 的 best_inliers；
4. 若 best_inliers >= T，则接受 Top1 输出；
5. 否则回退到 Top2 / Top5 精配准；
6. 输出最终空间位置。
```

当前推荐配置：

```text
T = 1000
fallback = Top2
```

## 实验结果表

{md_table(paper_rows)}

## 推荐方法结果

`Adaptive_T1000_else_Top2`：

- Success@5m：{float(best["success_5m_pct"]):.2f}%
- Mean Error：{float(best["mean_error_m"]):.2f} m
- Median Error：{float(best["median_error_m"]):.3f} m
- Mean Time：{float(best["mean_time_s"]):.2f} s
- Speedup：{float(best["mean_speedup_vs_standard"]):.2f}×
- Fallback Ratio：{float(best["fallback_pct"]):.2f}%

## 论文表述建议

针对固定 Top1 策略速度快但鲁棒性不足、固定 TopK 策略鲁棒但耗时较高的问题，本文设计了一种置信度驱动的自适应快速空间配准方法 CDA-FastReg。该方法首先执行 Top1 快速配准，并根据匹配内点数判断定位结果可靠性；当内点数低于阈值时，系统自动回退至 Top2 精配准路径。实验表明，该策略在保持较高定位成功率的同时显著降低平均运行时间。

## 相关文件

- 实验表：`{table_csv}`
- 方法流程图：`{flow_svg}`
- 原始模拟结果：`{SIM_DIR / "adaptive_strategy_summary.csv"}`
"""
    report_path = OUT_DIR / "cda_fastreg_method_report.md"
    report_path.write_text(report, encoding="utf-8-sig")
    (REPORTS_DIR / "cda_fastreg_method_report.md").write_text(report, encoding="utf-8-sig")

    manifest = {
        "method": "CDA-FastReg",
        "recommended_strategy": "Adaptive_T1000_else_Top2",
        "report": str(report_path),
        "paper_table": str(table_csv),
        "flow_svg": str(flow_svg),
        "source_summary": str(summary_path),
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8-sig"
    )

    print(f"Report: {report_path}")
    print(f"Docs copy: {REPORTS_DIR / 'cda_fastreg_method_report.md'}")
    print(f"Paper table: {table_csv}")
    print(f"Flow SVG: {flow_svg}")


if __name__ == "__main__":
    main()
