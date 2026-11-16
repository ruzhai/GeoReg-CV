from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class GeoPosition:
    xy: Optional[Tuple[float, float]]
    scene: str
    confidence: float
    method: str

