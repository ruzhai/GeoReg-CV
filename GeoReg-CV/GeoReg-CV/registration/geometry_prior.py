from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GeometryPrior:
    yaw: Optional[float] = None
    pitch: Optional[float] = None
    height: Optional[float] = None


def geometry_guided_score(retrieval_score: float, inlier_count: int, reprojection_error: Optional[float] = None) -> float:
    """A simple scoring stub for future Top-K reranking experiments."""

    score = retrieval_score + 0.001 * inlier_count
    if reprojection_error is not None:
        score -= 0.01 * reprojection_error
    return score

