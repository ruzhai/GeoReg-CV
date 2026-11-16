from dataclasses import dataclass


@dataclass(frozen=True)
class GeometryPrior:
    yaw: float | None = None
    pitch: float | None = None
    height: float | None = None


def geometry_guided_score(
    retrieval_score: float, inlier_count: int, reprojection_error: float | None = None
) -> float:
    """A simple scoring stub for future Top-K reranking experiments."""

    score = retrieval_score + 0.001 * inlier_count
    if reprojection_error is not None:
        score -= 0.01 * reprojection_error
    return score
