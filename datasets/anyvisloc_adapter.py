from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class ObserverReferenceSample:
    """A normalized sample description for observer-view to reference-view registration."""

    scene: str
    sample_id: str
    observer_npz: Path
    reference_map: Path
    reference_dsm: Optional[Path]


class AnyVisLocAdapter:
    """Lightweight filesystem adapter for AnyVisLoc.

    AnyVisLoc stores each scene as one aerial reference map, one DSM file, and many
    low-altitude query `.npz` files. In this project, those query files are treated
    as observer-view samples, while the aerial map is treated as the UAV/reference view.
    """

    def __init__(self, dataset_root: str | Path):
        self.dataset_root = Path(dataset_root)

    def scenes(self) -> List[str]:
        return sorted(p.name for p in self.dataset_root.iterdir() if p.is_dir() and p.name.startswith("Scene_"))

    def iter_scene_samples(self, scene: str, limit: Optional[int] = None) -> Iterable[ObserverReferenceSample]:
        scene_dir = self.dataset_root / scene
        reference_map = scene_dir / "aerial_map.png"
        reference_dsm = scene_dir / "aerial_dsm.npy"
        npz_files = sorted(scene_dir.glob("*.npz"))
        if limit is not None:
            npz_files = npz_files[:limit]

        for npz_path in npz_files:
            yield ObserverReferenceSample(
                scene=scene,
                sample_id=npz_path.stem,
                observer_npz=npz_path,
                reference_map=reference_map,
                reference_dsm=reference_dsm if reference_dsm.exists() else None,
            )

