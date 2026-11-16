from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    candidate_id: str
    num_matches: int
    num_inliers: int
    score: float


class CrossViewMatcher:
    """Interface placeholder for cross-view feature matching."""

    def match(self, observer_view, reference_view) -> MatchResult:
        raise NotImplementedError("Use AnyVisLoc RoMa baseline first; custom matching comes later.")

