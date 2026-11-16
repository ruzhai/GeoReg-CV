"""Summarize direct-center, PnP-ray, and hybrid center errors for one batch."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def metrics(values):
    valid = [v for v in values if v is not None]
    return {
        "valid_samples": len(valid),
        "mean_error_m": statistics.fmean(valid) if valid else None,
        "median_error_m": statistics.median(valid) if valid else None,
        "max_error_m": max(valid) if valid else None,
        "success_1m_pct": 100.0 * sum(v <= 1.0 for v in valid) / len(valid) if valid else None,
        "success_3m_pct": 100.0 * sum(v <= 3.0 for v in valid) / len(valid) if valid else None,
        "success_5m_pct": 100.0 * sum(v <= 5.0 for v in valid) / len(valid) if valid else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_dir")
    args = parser.parse_args()
    batch_dir = Path(args.batch_dir)
    csv_path = batch_dir / "batch_records.csv"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    pnp = [number(row.get("pnp_center_error_m")) for row in rows]
    direct = [number(row.get("direct_center_error_m")) for row in rows]
    hybrid = [number(row.get("hybrid_center_error_m")) for row in rows]
    paired = [(d, p) for d, p in zip(direct, pnp, strict=False) if d is not None and p is not None]
    methods = {}
    for row in rows:
        method = row.get("center_method") or "unknown"
        methods[method] = methods.get(method, 0) + 1
    summary = {
        "batch_dir": str(batch_dir),
        "samples": len(rows),
        "pnp_ray": metrics(pnp),
        "direct_local_homography": metrics(direct),
        "confidence_hybrid": metrics(hybrid),
        "method_counts": methods,
        "paired_samples": len(paired),
        "direct_better_count": sum(d < p for d, p in paired),
        "direct_equal_count": sum(abs(d - p) <= 1e-9 for d, p in paired),
        "direct_worse_count": sum(d > p for d, p in paired),
        "mean_direct_minus_pnp_m": statistics.fmean(d - p for d, p in paired) if paired else None,
        "note": "Initial Scene_01 feasibility subset; thresholds are not final benchmark settings.",
    }
    threshold_sweep = []
    for threshold in (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90):
        selected = []
        direct_count = 0
        for row, direct_error, pnp_error in zip(rows, direct, pnp, strict=False):
            confidence = number(row.get("center_confidence"))
            if direct_error is not None and confidence is not None and confidence >= threshold:
                selected.append(direct_error)
                direct_count += 1
            else:
                selected.append(pnp_error)
        item = metrics(selected)
        item.update({"threshold": threshold, "direct_count": direct_count})
        threshold_sweep.append(item)
    summary["confidence_threshold_sweep"] = threshold_sweep
    summary["development_default_threshold"] = 0.70
    policy_rows = []
    for row, direct_error, pnp_error in zip(rows, direct, pnp, strict=False):
        confidence = number(row.get("center_confidence"))
        use_direct = bool(
            direct_error is not None and confidence is not None and confidence >= 0.70
        )
        policy_rows.append(
            {
                "sample_id": row.get("sample_id"),
                "center_confidence": confidence,
                "direct_center_error_m": direct_error,
                "pnp_center_error_m": pnp_error,
                "selected_method": "direct_local_homography" if use_direct else "pnp_ray_fallback",
                "selected_center_error_m": direct_error if use_direct else pnp_error,
            }
        )
    policy_path = batch_dir / "direct_center_policy_t070.csv"
    with policy_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(policy_rows[0].keys()))
        writer.writeheader()
        writer.writerows(policy_rows)
    policy_metrics = metrics([row["selected_center_error_m"] for row in policy_rows])
    policy_metrics["direct_count"] = sum(
        row["selected_method"] == "direct_local_homography" for row in policy_rows
    )
    policy_metrics["pnp_fallback_count"] = len(policy_rows) - policy_metrics["direct_count"]
    policy_metrics["records_csv"] = str(policy_path)
    summary["development_policy_t070"] = policy_metrics
    output = batch_dir / "direct_center_feasibility_summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
