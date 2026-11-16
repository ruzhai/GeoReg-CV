import json
from collections.abc import Iterable
from pathlib import Path

from crossview.schema.records import GeoRegistrationRecord


def export_simulation_json(records: Iterable[GeoRegistrationRecord], path: str | Path) -> None:
    """Export neutral simulation-ready points.

    The output intentionally uses generic observer/reference/estimated-position wording
    so it can be consumed by later simulation software without binding to a specific
    military or civilian platform.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "coordinate_system": "AnyVisLoc Scene local metric coordinate",
        "entities": [],
    }
    for r in records:
        payload["entities"].append(
            {
                "scene": r.scene_name,
                "sample_id": r.sample_id,
                "observer_view": {
                    "source": r.observer_source,
                    "gt_position": {"x": r.gt_x, "y": r.gt_y, "z": r.gt_z},
                },
                "uav_reference_view": {
                    "source": r.reference_source,
                },
                "estimated_geo_position": {
                    "x": r.pred_x,
                    "y": r.pred_y,
                    "z": r.pred_z,
                    "error_m": r.error_m,
                },
                "status": {
                    "success_1m": r.success_1m,
                    "success_3m": r.success_3m,
                    "success_5m": r.success_5m,
                },
                "runtime": {
                    "total_time_s": r.total_time_s,
                },
                "adaptive_strategy": {
                    "route": r.adaptive_route,
                    "top1_best_inliers": r.top1_best_inliers,
                    "confidence_threshold": r.confidence_threshold,
                    "fallback_used": r.fallback_used,
                    "source_method": r.source_method,
                },
            }
        )
    with path.open("w", encoding="utf-8-sig") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
