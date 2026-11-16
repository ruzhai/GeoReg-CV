import csv
import json
from pathlib import Path
from typing import Iterable, List

from .result_schema import GeoRegistrationRecord


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


def _float_or_none(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except Exception:
        return None


def latest_archive_from_pointer(pointer_path: str | Path) -> Path:
    pointer_path = Path(pointer_path)
    values = {}
    for line in pointer_path.read_text(encoding="utf-8-sig").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    archive = values.get("archive_dir")
    if not archive:
        raise ValueError(f"archive_dir not found in {pointer_path}")
    return Path(archive)


def load_records_from_csv(csv_path: str | Path) -> List[GeoRegistrationRecord]:
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    records = []
    for row in rows:
        error_m = _float(row.get("pred_error_m"))
        records.append(
            GeoRegistrationRecord(
                scene_name=row.get("scene_name", ""),
                sample_id=row.get("sample_id", ""),
                observer_source=row.get("npz_path", ""),
                reference_source=row.get("reference_mode", "aerial"),
                gt_x=_float(row.get("gt_x")),
                gt_y=_float(row.get("gt_y")),
                gt_z=_float(row.get("gt_z")),
                pred_x=_float(row.get("pred_x")),
                pred_y=_float(row.get("pred_y")),
                pred_z=_float(row.get("pred_z")),
                error_m=error_m,
                success_1m=error_m <= 1,
                success_3m=error_m <= 3,
                success_5m=error_m <= 5,
                retrieval_method=row.get("retrieval_method", ""),
                matching_method=row.get("matching_method", ""),
                localization_method="PnP/P3P",
                retrieval_gt_rank=_int_or_none(row.get("retrieval_gt_rank")),
                recall_at_k=_float_or_none(row.get("recall_at_k")),
                pdm_at_k=_float_or_none(row.get("pdm_at_k")),
                best_inliers=_int_or_none(row.get("best_inliers")),
                total_time_s=_float_or_none(row.get("total_time")),
                adaptive_route=row.get("adaptive_route", ""),
                top1_best_inliers=_int_or_none(row.get("top1_best_inliers")),
                confidence_threshold=_int_or_none(row.get("confidence_threshold")),
                fallback_used=(
                    row.get("fallback_used", "").strip().lower() in {"true", "1", "yes"}
                    if isinstance(row.get("fallback_used", ""), str) and row.get("fallback_used", "") != ""
                    else None
                ),
                source_method=row.get("source_method", ""),
            )
        )
    return records


def save_records_json(records: Iterable[GeoRegistrationRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig") as f:
        json.dump([r.to_dict() for r in records], f, ensure_ascii=False, indent=2)


def save_records_csv(records: Iterable[GeoRegistrationRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r.to_dict() for r in records]
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
