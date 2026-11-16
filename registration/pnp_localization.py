from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class PnPResult:
    success: bool
    position_xy: Optional[Tuple[float, float]]
    error_m: Optional[float]
    inliers: int


class PnPLocalizer:
    """Interface placeholder for PnP-based spatial localization."""

    def localize(self, match_result) -> PnPResult:
        raise NotImplementedError("Use AnyVisLoc P3P baseline first; custom PnP wrapper comes later.")

