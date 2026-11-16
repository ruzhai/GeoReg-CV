import csv
from collections.abc import Iterable
from pathlib import Path

from crossview.core.routing.adaptive import (
    AdaptiveRegistrationPolicy,
    build_confidence_from_result_row,
)
from crossview.schema.records import GeoRegistrationRecord


def _float(value, default=0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def _int_or_none(value):
    try:
        if value in ("", None):
            return None
        return int(float(value))
    except Exception:
        return None


def _load_rows(csv_path: str | Path) -> dict[str, dict]:
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {row["sample_id"]: row for row in rows}


def build_adaptive_records(
    top1_csv: str | Path,
    fallback_csv: str | Path,
    threshold: int = 1000,
    fallback_topk: int = 2,
) -> list[GeoRegistrationRecord]:
    """Build final CDA-FastReg records from measured Top1 and fallback results.

    This is an offline system-demonstration builder. It uses measured result rows
    from the Top1 fast path and the fallback path to reproduce the decision that
    an online CDA-FastReg pipeline would make.
    """

    top1_rows = _load_rows(top1_csv)
    fallback_rows = _load_rows(fallback_csv)
    sample_ids = sorted(set(top1_rows).intersection(fallback_rows))
    policy = AdaptiveRegistrationPolicy(inlier_threshold=threshold, fallback_topk=fallback_topk)

    records: list[GeoRegistrationRecord] = []
    for sample_id in sample_ids:
        top1 = top1_rows[sample_id]
        fallback = fallback_rows[sample_id]
        confidence = build_confidence_from_result_row(top1)
        decision = policy.decide(confidence)
        chosen = top1 if decision.accepted_top1 else fallback
        error_m = _float(chosen.get("pred_error_m"))

        records.append(
            GeoRegistrationRecord(
                scene_name=chosen.get("scene_name", ""),
                sample_id=sample_id,
                observer_source=chosen.get("npz_path", ""),
                reference_source=chosen.get("reference_mode", "aerial"),
                gt_x=_float(chosen.get("gt_x")),
                gt_y=_float(chosen.get("gt_y")),
                gt_z=_float(chosen.get("gt_z")),
                pred_x=_float(chosen.get("pred_x")),
                pred_y=_float(chosen.get("pred_y")),
                pred_z=_float(chosen.get("pred_z")),
                error_m=error_m,
                success_1m=error_m <= 1,
                success_3m=error_m <= 3,
                success_5m=error_m <= 5,
                retrieval_method=chosen.get("retrieval_method", ""),
                matching_method=chosen.get("matching_method", ""),
                localization_method="PnP/P3P",
                retrieval_gt_rank=_int_or_none(chosen.get("retrieval_gt_rank")),
                recall_at_k=_float(chosen.get("recall_at_k")),
                pdm_at_k=_float(chosen.get("pdm_at_k")),
                best_inliers=_int_or_none(chosen.get("best_inliers")),
                total_time_s=_float(chosen.get("total_time")),
                adaptive_route=decision.route.value,
                top1_best_inliers=decision.best_inliers,
                confidence_threshold=decision.threshold,
                fallback_used=not decision.accepted_top1,
                source_method="CDA-FastReg",
            )
        )
    return records


def summarize_adaptive_records(records: Iterable[GeoRegistrationRecord]) -> dict:
    records = list(records)
    if not records:
        return {}
    errors = [r.error_m for r in records]
    times = [r.total_time_s or 0.0 for r in records]
    fallback_count = sum(bool(r.fallback_used) for r in records)
    route_counts = {}
    for r in records:
        route_counts[r.adaptive_route] = route_counts.get(r.adaptive_route, 0) + 1
    return {
        "num_records": len(records),
        "mean_error_m": sum(errors) / len(errors),
        "median_error_m": sorted(errors)[len(errors) // 2],
        "max_error_m": max(errors),
        "success_1m": sum(e <= 1 for e in errors) / len(errors),
        "success_3m": sum(e <= 3 for e in errors) / len(errors),
        "success_5m": sum(e <= 5 for e in errors) / len(errors),
        "mean_time_s": sum(times) / len(times),
        "median_time_s": sorted(times)[len(times) // 2],
        "fallback_count": fallback_count,
        "fallback_ratio": fallback_count / len(records),
        "route_counts": route_counts,
    }
