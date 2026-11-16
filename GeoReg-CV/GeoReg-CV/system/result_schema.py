from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class GeoRegistrationRecord:
    """Unified output record for observer-view to UAV/reference-view registration."""

    scene_name: str
    sample_id: str
    observer_source: str
    reference_source: str
    gt_x: float
    gt_y: float
    gt_z: float
    pred_x: float
    pred_y: float
    pred_z: float
    error_m: float
    success_1m: bool
    success_3m: bool
    success_5m: bool
    retrieval_method: str
    matching_method: str
    localization_method: str
    retrieval_gt_rank: Optional[int]
    recall_at_k: Optional[float]
    pdm_at_k: Optional[float]
    best_inliers: Optional[int]
    total_time_s: Optional[float]
    adaptive_route: str = ""
    top1_best_inliers: Optional[int] = None
    confidence_threshold: Optional[int] = None
    fallback_used: Optional[bool] = None
    source_method: str = ""

    def to_dict(self):
        return asdict(self)
