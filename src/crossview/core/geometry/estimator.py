from dataclasses import dataclass


@dataclass(frozen=True)
class GeoPosition:
    xy: tuple[float, float] | None
    scene: str
    confidence: float
    method: str
