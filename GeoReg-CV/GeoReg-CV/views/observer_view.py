from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class ObserverView:
    """Observer/platform oblique-view image and optional pose prior."""

    image_path: Optional[Path]
    source_path: Path
    yaw_pitch: Optional[Tuple[float, float]] = None
    height: Optional[float] = None
    note: str = "AnyVisLoc low-altitude oblique query is used as observer-view proxy."

