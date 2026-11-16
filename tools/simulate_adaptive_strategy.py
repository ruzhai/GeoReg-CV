import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

from crossview.paths import experiments_dir

ROOT = Path(experiments_dir() / "fast_baseline_ablation")
OUTPUT_DIR = ROOT / "adaptive_strategy_simulation"

RUNS = {
    "standard_top5": ROOT / "standard_top5_k3000_r04_limit120",
    "top2": ROOT / "fast_v3_true_top2_k1500_r03_limit120",
    "top1": ROOT / "fast_v2_top1_k1500_r03_limit120",
}


@dataclass(frozen=True)
class Strategy:
    name: str
    threshold: int
    fallback: str


STRATEGIES = [
    Strategy("Adaptive_T1000_else_Top2", 1000, "top2"),
    Strategy("Adaptive_T1500_else_Top2", 1500, "top2"),
    Strategy("Adaptive_T2000_else_Top2", 2000, "top2"),
    Strategy("Adaptive_T2500_else_Top2", 2500, "top2"),
    Strategy("Adaptive_T1000_else_Top5", 1000, "standard_top5"),
    Strategy("Adaptive_T1500_else_Top5", 1500, "standard_top5"),
    Strategy("Adaptive_T2000_else_Top5", 2000, "standard_top5"),
    Strategy("Adaptive_T2500_else_Top5", 2500, "standard_top5"),
]


def _float(value, default=0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def _int(value, default=0) -> int:
    try:
        if value in ("", None):
            return default
        return int(float(value))
    except Exception:
        return default


def find_method_dir(run_root: Path) -> Path:
    candidates = sorted(
        run_root.glob("*_1scenes/aerial/aerial-CAMP-Roma-yp"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No method result directory found under {run_root}")
    return candidates[0]


def load_rows(run_root: Path) -> dict[str, dict]:
    method_dir = find_method_dir(run_root)
    csv_path = method_dir / "all_results.csv"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["sample_id"]: r for r in rows}


def summarize_rows(
    name: str,
    rows: list[dict],
    standard_mean_time: float,
    standard_median_time: float,
    fallback_count=0,
) -> dict:
    errors = [_float(r["pred_error_m"]) for r in rows]
    times = [_float(r["total_time"]) for r in rows]
    n = len(rows)
    return {
        "method": name,
        "samples": n,
        "mean_error_m": round(mean(errors), 6),
        "median_error_m": round(median(errors), 6),
        "max_error_m": round(max(errors), 6),
        "success_1m_pct": round(sum(e <= 1 for e in errors) / n * 100, 4),
        "success_3m_pct": round(sum(e <= 3 for e in errors) / n * 100, 4),
        "success_5m_pct": round(sum(e <= 5 for e in errors) / n * 100, 4),
        "success_10m_pct": round(sum(e <= 10 for e in errors) / n * 100, 4),
        "success_20m_pct": round(sum(e <= 20 for e in errors) / n * 100, 4),
        "over5m": sum(e > 5 for e in errors),
        "over20m": sum(e > 20 for e in errors),
        "mean_time_s": round(mean(times), 6),
        "median_time_s": round(median(times), 6),
        "mean_speedup_vs_standard": round(standard_mean_time / mean(times), 6) if times else 0,
        "median_speedup_vs_standard": round(standard_median_time / median(times), 6)
        if times
        else 0,
        "fallback_count": fallback_count,
        "fallback_pct": round(fallback_count / n * 100, 4) if n else 0,
    }


def save_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    loaded = {name: load_rows(path) for name, path in RUNS.items()}
    sample_ids = sorted(set.intersection(*(set(v.keys()) for v in loaded.values())))
    if not sample_ids:
        raise RuntimeError("No overlapping sample IDs found.")

    standard_rows = [loaded["standard_top5"][sid] for sid in sample_ids]
    top1_rows = [loaded["top1"][sid] for sid in sample_ids]
    top2_rows = [loaded["top2"][sid] for sid in sample_ids]
    standard_mean_time = mean([_float(r["total_time"]) for r in standard_rows])
    standard_median_time = median([_float(r["total_time"]) for r in standard_rows])

    summaries = []
    summaries.append(
        summarize_rows("Standard_Top5", standard_rows, standard_mean_time, standard_median_time)
    )
    summaries.append(
        summarize_rows("Fixed_Top2", top2_rows, standard_mean_time, standard_median_time)
    )
    summaries.append(
        summarize_rows("Fixed_Top1", top1_rows, standard_mean_time, standard_median_time)
    )

    all_decisions = []
    for strategy in STRATEGIES:
        chosen_rows = []
        fallback_count = 0
        decisions = []
        for sid in sample_ids:
            top1 = loaded["top1"][sid]
            fallback = loaded[strategy.fallback][sid]
            inliers = _int(top1.get("best_inliers"))
            if inliers >= strategy.threshold:
                chosen = top1
                route = "top1_fast_path"
            else:
                chosen = fallback
                route = f"fallback_{strategy.fallback}"
                fallback_count += 1
            chosen_rows.append(chosen)
            decisions.append(
                {
                    "strategy": strategy.name,
                    "sample_id": sid,
                    "route": route,
                    "top1_best_inliers": inliers,
                    "chosen_error_m": _float(chosen["pred_error_m"]),
                    "chosen_time_s": _float(chosen["total_time"]),
                    "top1_error_m": _float(top1["pred_error_m"]),
                    "fallback_error_m": _float(fallback["pred_error_m"]),
                    "standard_error_m": _float(loaded["standard_top5"][sid]["pred_error_m"]),
                }
            )
        summaries.append(
            summarize_rows(
                strategy.name, chosen_rows, standard_mean_time, standard_median_time, fallback_count
            )
        )
        all_decisions.extend(decisions)

    save_csv(OUTPUT_DIR / "adaptive_strategy_summary.csv", summaries)
    save_csv(OUTPUT_DIR / "adaptive_strategy_decisions.csv", all_decisions)
    with (OUTPUT_DIR / "adaptive_strategy_summary.json").open("w", encoding="utf-8-sig") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    best_success5 = sorted(
        summaries,
        key=lambda r: (-r["success_5m_pct"], -r["mean_speedup_vs_standard"], r["mean_error_m"]),
    )[:5]
    best_speed = sorted(
        summaries,
        key=lambda r: (-r["mean_speedup_vs_standard"], -r["success_5m_pct"], r["mean_error_m"]),
    )[:5]

    def md_table(rows):
        lines = [
            "| 方法 | Success@5m | Mean Error | Mean Time | Speedup | Fallback | >20m |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for r in rows:
            lines.append(
                f"| {r['method']} | {r['success_5m_pct']:.2f}% | {r['mean_error_m']:.2f}m | "
                f"{r['mean_time_s']:.2f}s | {r['mean_speedup_vs_standard']:.2f}x | "
                f"{r['fallback_pct']:.2f}% | {r['over20m']} |"
            )
        return "\n".join(lines)

    report = f"""# 置信度驱动自适应快速配准策略离线模拟

## 实验说明

本实验不重新运行模型，而是利用已有三组 limit=120 结果进行离线模拟：

- Standard_Top5：标准 Top5 精配准路径；
- Fixed_Top2：固定 Top2 路径；
- Fixed_Top1：固定 Top1 快速路径；
- Adaptive：先使用 Top1，如果 Top1 的 `best_inliers` 低于阈值，则回退到 Top2 或 Top5。

注意：该模拟中的时间为“选择路径对应的已测运行时间”，用于估计自适应策略的潜在速度收益。

## 全部策略结果

{md_table(summaries)}

## 按 Success@5m 优先排序的 Top 5

{md_table(best_success5)}

## 按速度优先排序的 Top 5

{md_table(best_speed)}

## 初步结论

固定 Top1 速度最快，但严重失败样本较多；固定 Top2/Top5 更稳，但耗时较高。自适应策略通过内点数阈值判断是否接受 Top1，可以在速度与精度之间形成折中。

推荐优先关注：

- `Adaptive_T1000_else_Top2` 或 `Adaptive_T1500_else_Top2`：更偏速度；
- `Adaptive_T1000_else_Top5` 或 `Adaptive_T1500_else_Top5`：更偏稳健。
"""
    (OUTPUT_DIR / "adaptive_strategy_report.md").write_text(report, encoding="utf-8-sig")

    print(f"Saved summary: {OUTPUT_DIR / 'adaptive_strategy_summary.csv'}")
    print(f"Saved decisions: {OUTPUT_DIR / 'adaptive_strategy_decisions.csv'}")
    print(f"Saved report: {OUTPUT_DIR / 'adaptive_strategy_report.md'}")
    for r in summaries:
        print(
            f"{r['method']}: S@5={r['success_5m_pct']:.2f}% "
            f"mean_time={r['mean_time_s']:.2f}s speedup={r['mean_speedup_vs_standard']:.2f}x "
            f"fallback={r['fallback_pct']:.2f}% >20m={r['over20m']}"
        )


if __name__ == "__main__":
    main()
