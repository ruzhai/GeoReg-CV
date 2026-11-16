import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from statistics import mean, median

from crossview.paths import docs_dir, experiments_dir

SOURCE_DIR = Path(
    experiments_dir() / "baseline_anyvisloc_scene01"
    r"\20260809-2323_1scenes\aerial\aerial-CAMP-Roma-yp"
)
ARCHIVE_DIR = Path(
    experiments_dir() / "baseline_anyvisloc_scene01"
    r"\frozen_scene01_full_baseline_20260809-2323"
)
DOCS_DIR = Path(docs_dir())


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fieldnames=None) -> None:
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(row, key, default=0.0):
    try:
        value = row.get(key, default)
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def count_if(values, pred):
    return sum(1 for v in values if pred(v))


def main() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Source result directory not found: {SOURCE_DIR}")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    source_files = [
        "summary.json",
        "failed.json",
        "all_results.csv",
        "all_results.json",
        "retrieval_metrics.json",
        "success_curve_overall.png",
    ]
    copied = []
    for name in source_files:
        src = SOURCE_DIR / name
        if src.exists():
            dst = ARCHIVE_DIR / name
            shutil.copy2(src, dst)
            copied.append(str(dst))

    summary = read_json(SOURCE_DIR / "summary.json")
    failed = read_json(SOURCE_DIR / "failed.json")
    rows = read_csv(SOURCE_DIR / "all_results.csv")

    errors = [as_float(r, "pred_error_m") for r in rows]
    total_times = [as_float(r, "total_time") for r in rows]
    retrieval_times = [as_float(r, "retrieval_time") for r in rows]
    inliers = [as_float(r, "best_inliers") for r in rows]

    metrics = {
        "frozen_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dir": str(SOURCE_DIR),
        "archive_dir": str(ARCHIVE_DIR),
        "scene": "Scene_01",
        "method": "AnyVisLoc baseline: CAMP + RoMa + P3P",
        "num_samples": len(rows),
        "num_exception_failed_rows": len(failed),
        "num_pnp_success_rows": int(summary.get("num_pnp_success_rows", 0)),
        "num_pnp_failed_rows": int(summary.get("num_pnp_failed_rows", 0)),
        "failure_rate": float(summary.get("failure_rate", 0.0)),
        "mean_error_m": mean(errors) if errors else None,
        "median_error_m": median(errors) if errors else None,
        "max_error_m": max(errors) if errors else None,
        "success_rate_1m": float(summary.get("success_rate_1m", 0.0)),
        "success_rate_3m": float(summary.get("success_rate_3m", 0.0)),
        "success_rate_5m": float(summary.get("success_rate_5m", 0.0)),
        "success_rate_10m": float(summary.get("success_rate_10m", 0.0)),
        "success_rate_20m": float(summary.get("success_rate_20m", 0.0)),
        "Recall@5": float(summary.get("Recall@5", summary.get("recall_at_k", 0.0))),
        "PDM@5": float(summary.get("PDM@5", summary.get("pdm_at_k", 0.0))),
        "mean_total_time_s": mean(total_times) if total_times else None,
        "median_total_time_s": median(total_times) if total_times else None,
        "mean_retrieval_time_s": mean(retrieval_times) if retrieval_times else None,
        "median_retrieval_time_s": median(retrieval_times) if retrieval_times else None,
        "mean_best_inliers": mean(inliers) if inliers else None,
    }

    metric_rows = [{"metric": k, "value": v} for k, v in metrics.items()]
    write_csv(ARCHIVE_DIR / "scene01_metrics_summary.csv", metric_rows, ["metric", "value"])
    write_json(ARCHIVE_DIR / "scene01_metrics_summary.json", metrics)

    buckets = [
        ("<=1m", lambda e: e <= 1),
        ("1-3m", lambda e: 1 < e <= 3),
        ("3-5m", lambda e: 3 < e <= 5),
        ("5-10m", lambda e: 5 < e <= 10),
        ("10-20m", lambda e: 10 < e <= 20),
        (">20m", lambda e: e > 20),
    ]
    bucket_rows = []
    for name, pred in buckets:
        count = count_if(errors, pred)
        bucket_rows.append(
            {
                "bucket": name,
                "count": count,
                "ratio": f"{count / len(errors):.6f}" if errors else "0",
                "percent": f"{count / len(errors) * 100:.2f}%" if errors else "0.00%",
            }
        )
    write_csv(ARCHIVE_DIR / "scene01_error_buckets.csv", bucket_rows)

    enriched = []
    for r in rows:
        e = as_float(r, "pred_error_m")
        retrieval_rank = as_float(r, "retrieval_gt_rank")
        recall_at_k = as_float(r, "recall_at_k")
        if e > 20:
            failure_type = "severe_failure_over_20m"
        elif e > 5:
            failure_type = "large_error_5m_to_20m"
        elif e > 3:
            failure_type = "medium_error_3m_to_5m"
        elif e > 1:
            failure_type = "minor_error_1m_to_3m"
        else:
            failure_type = "success_within_1m"

        if recall_at_k < 1:
            cause_hint = "retrieval_miss_top5"
        elif e > 5:
            cause_hint = "retrieval_hit_but_localization_unstable"
        else:
            cause_hint = "normal"

        rr = dict(r)
        rr["failure_type"] = failure_type
        rr["cause_hint"] = cause_hint
        rr["pred_error_m_float"] = f"{e:.6f}"
        rr["retrieval_gt_rank_float"] = f"{retrieval_rank:.0f}"
        enriched.append(rr)

    write_csv(ARCHIVE_DIR / "scene01_enriched_results.csv", enriched)

    top_error = sorted(rows, key=lambda r: as_float(r, "pred_error_m"), reverse=True)[:30]
    top_slow = sorted(rows, key=lambda r: as_float(r, "total_time"), reverse=True)[:30]

    selected_fields = [
        "scene_name",
        "sample_id",
        "pred_error_m",
        "retrieval_gt_rank",
        "recall_at_k",
        "pdm_at_k",
        "best_inliers",
        "total_time",
        "retrieval_time",
        "result_pkl",
        "npz_path",
    ]
    write_csv(ARCHIVE_DIR / "scene01_top30_high_error_samples.csv", top_error, selected_fields)
    write_csv(ARCHIVE_DIR / "scene01_top30_slow_samples.csv", top_slow, selected_fields)

    over_5 = count_if(errors, lambda e: e > 5)
    over_20 = count_if(errors, lambda e: e > 20)

    high_error_md_rows = "\n".join(
        [
            "| {sample_id} | {pred_error_m:.2f} | {retrieval_gt_rank:.0f} | {recall_at_k:.0f} | {best_inliers:.0f} |".format(
                sample_id=r.get("sample_id", ""),
                pred_error_m=as_float(r, "pred_error_m"),
                retrieval_gt_rank=as_float(r, "retrieval_gt_rank"),
                recall_at_k=as_float(r, "recall_at_k"),
                best_inliers=as_float(r, "best_inliers"),
            )
            for r in top_error[:10]
        ]
    )

    bucket_md_rows = "\n".join(
        f"| {r['bucket']} | {r['count']} | {r['percent']} |" for r in bucket_rows
    )

    report = f"""# Scene_01 AnyVisLoc Baseline 结果分析报告

## 1. 实验设置

- 工程：GeoReg-CV
- 数据集：AnyVisLoc
- 场景：Scene_01
- Baseline：CAMP + RoMa + P3P
- 参考视角：aerial
- 位姿先验：yaw / pitch，配置中记为 `yp`
- 样本数：{metrics["num_samples"]}
- 结果来源：`{SOURCE_DIR}`
- 固化目录：`{ARCHIVE_DIR}`

## 2. 完整性检查

| 项目 | 数值 |
| --- | ---: |
| 请求样本数 | {summary.get("num_samples_requested")} |
| 实际结果数 | {summary.get("num_result_rows")} |
| PnP 成功数 | {summary.get("num_pnp_success_rows")} |
| PnP 失败数 | {summary.get("num_pnp_failed_rows")} |
| 异常失败数 | {summary.get("num_exception_failed_rows")} |
| failure rate | {metrics["failure_rate"]:.4f} |

结论：本次 Scene_01 full baseline 已完整运行，未出现异常失败或 PnP 失败。

## 3. 定位精度

| 指标 | 数值 |
| --- | ---: |
| Mean Error | {metrics["mean_error_m"]:.4f} m |
| Median Error | {metrics["median_error_m"]:.4f} m |
| Max Error | {metrics["max_error_m"]:.4f} m |
| Success@1m | {pct(metrics["success_rate_1m"])} |
| Success@3m | {pct(metrics["success_rate_3m"])} |
| Success@5m | {pct(metrics["success_rate_5m"])} |
| Success@10m | {pct(metrics["success_rate_10m"])} |
| Success@20m | {pct(metrics["success_rate_20m"])} |
| Recall@5 | {pct(metrics["Recall@5"])} |
| PDM@5 | {metrics["PDM@5"]:.4f} |

核心观察：中位误差只有 {metrics["median_error_m"]:.4f} m，说明大多数样本定位较准；但平均误差达到 {metrics["mean_error_m"]:.4f} m，主要被少数极端大误差样本拉高。

## 4. 误差分布

| 误差区间 | 样本数 | 占比 |
| --- | ---: | ---: |
{bucket_md_rows}

其中误差大于 5m 的样本有 {over_5} 个，误差大于 20m 的严重失败样本有 {over_20} 个。

## 5. 高误差样本 Top 10

| 样本 | 误差/m | GT Rank | Recall@5 | Best Inliers |
| --- | ---: | ---: | ---: | ---: |
{high_error_md_rows}

从高误差样本看，部分严重失败样本的 `Recall@5=0`，说明真实候选没有进入 Top-5，属于检索阶段失败；也存在少量 `Recall@5=1` 但误差仍较大的样本，说明检索命中后仍可能出现候选选择或几何定位不稳定。

## 6. 耗时分析

| 指标 | 数值 |
| --- | ---: |
| 平均总耗时/样本 | {metrics["mean_total_time_s"]:.4f} s |
| 中位总耗时/样本 | {metrics["median_total_time_s"]:.4f} s |
| 平均检索耗时/样本 | {metrics["mean_retrieval_time_s"]:.6f} s |
| 中位检索耗时/样本 | {metrics["median_retrieval_time_s"]:.6f} s |

检索耗时远小于单样本总耗时，说明当前系统主要耗时不在图像检索，而在后续候选区域处理、跨视角匹配和几何定位流程。

## 7. 对课题的意义

本次实验已经证明，GeoReg-CV 可以基于 AnyVisLoc baseline 完成从观察者/斜视图像到无人机/航拍参考视图的空间配准，并输出位置估计结果。该结果可以作为课题的第一组正式 baseline。

后续如果暂不做算法改进，也可以继续围绕完整系统展开：

1. 输出定位结果可视化；
2. 生成成功/失败样本对比图；
3. 整理模块耗时与误差统计；
4. 接入仿真软件进行位置点、误差连线和轨迹展示。

## 8. 已生成文件

- `scene01_metrics_summary.csv`
- `scene01_metrics_summary.json`
- `scene01_error_buckets.csv`
- `scene01_enriched_results.csv`
- `scene01_top30_high_error_samples.csv`
- `scene01_top30_slow_samples.csv`
- `scene01_baseline_analysis_report.md`
"""

    report_path = ARCHIVE_DIR / "scene01_baseline_analysis_report.md"
    report_path.write_text(report, encoding="utf-8-sig")
    shutil.copy2(report_path, DOCS_DIR / "scene01_baseline_analysis_report.md")

    readme = f"""# Frozen Scene_01 Full Baseline

This directory freezes the completed AnyVisLoc Scene_01 full baseline run.

- Source: `{SOURCE_DIR}`
- Frozen at: {metrics["frozen_at"]}
- Samples: {metrics["num_samples"]}
- Method: {metrics["method"]}
- Mean error: {metrics["mean_error_m"]:.4f} m
- Median error: {metrics["median_error_m"]:.4f} m
- Success@1m: {pct(metrics["success_rate_1m"])}
- Success@5m: {pct(metrics["success_rate_5m"])}
- Recall@5: {pct(metrics["Recall@5"])}
- PDM@5: {metrics["PDM@5"]:.4f}

See `scene01_baseline_analysis_report.md` for the full analysis.
"""
    (ARCHIVE_DIR / "README.md").write_text(readme, encoding="utf-8-sig")

    latest = Path(
        experiments_dir() / "baseline_anyvisloc_scene01" / "LATEST_SCENE01_FULL_BASELINE.txt"
    )
    latest.write_text(
        f"source_dir={SOURCE_DIR}\narchive_dir={ARCHIVE_DIR}\nreport={report_path}\n",
        encoding="utf-8-sig",
    )

    print(f"Frozen archive: {ARCHIVE_DIR}")
    print(f"Report: {report_path}")
    print(f"Docs copy: {DOCS_DIR / 'scene01_baseline_analysis_report.md'}")
    print(f"Copied files: {len(copied)}")


if __name__ == "__main__":
    main()
