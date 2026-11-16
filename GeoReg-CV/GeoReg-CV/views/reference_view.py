from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ReferenceView:
    """UAV/aerial/orthophoto reference view used for geo-position estimation."""

    map_path: Path
    dsm_path: Optional[Path] = None
    coordinate_system: str = "AnyVisLoc local scene coordinates"

