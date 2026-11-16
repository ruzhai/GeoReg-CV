"""AnyVisLoc 格式的数据集适配。

一个场景由三部分组成：
- 一份 ``*_reference.json``：描述参考视图（航拍 / 卫星）的路径、分辨率与原点
- 一张参考图 + 一份 DSM
- 许多 ``*.npz`` 查询样本：低空斜视图像 + 相机内参 + 位姿 + 世界坐标

不同来源的目录层级不完全一致，所以这里按"含 reference json"来找场景，
而不是按固定层数。
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from crossview.schema.samples import ObserverReferenceSample, SceneReference

REFERENCE_GLOB = "*_reference.json"


class SceneNotFound(FileNotFoundError):
    """场景目录不存在或不含 reference json。"""


class AnyVisLocAdapter:
    def __init__(self, dataset_root: str | Path, mode: str = "aerial") -> None:
        self.dataset_root = Path(dataset_root)
        self.mode = mode

    # ---------- 场景发现 ----------

    def _scene_dir(self, path: Path) -> Path | None:
        if path.is_dir() and any(path.glob(REFERENCE_GLOB)):
            return path
        for child in sorted(path.glob("*/")):
            if child.is_dir() and any(child.glob(REFERENCE_GLOB)):
                return child
        return None

    def scenes(self) -> list[str]:
        found = []
        for entry in sorted(self.dataset_root.iterdir()):
            if entry.is_dir() and self._scene_dir(entry) is not None:
                found.append(entry.name)
        return found

    def scene_dir(self, scene: str) -> Path:
        candidate = self.dataset_root / scene
        resolved = self._scene_dir(candidate) if candidate.is_dir() else None
        if resolved is None:
            raise SceneNotFound(f"{candidate} 下没有 {REFERENCE_GLOB}")
        return resolved

    # ---------- 参考视图 ----------

    def reference(self, scene: str, mode: str | None = None) -> SceneReference:
        mode = mode or self.mode
        scene_dir = self.scene_dir(scene)
        payload = json.loads(next(scene_dir.glob(REFERENCE_GLOB)).read_text(encoding="utf-8"))
        modes = payload.get("modes", {})
        if mode not in modes:
            raise KeyError(f"场景 {scene} 没有 {mode} 模式；可用：{sorted(modes)}")
        spec = modes[mode]

        dsm_name = spec.get("dsm_path") or spec.get("dsm_field")
        dsm_path = scene_dir / dsm_name if dsm_name else None

        return SceneReference(
            scene=scene,
            mode=mode,
            map_path=scene_dir / (spec.get("map_path") or spec.get("map_field")),
            dsm_path=dsm_path if dsm_path and dsm_path.exists() else None,
            map_resolution=_pair(spec.get("map_resolution")),
            dsm_resolution=_pair(spec.get("dsm_resolution")),
            map_origin_local=_pair(spec.get("map_origin_local")),
            dsm_origin_local=_pair(spec.get("dsm_origin_local")),
        )

    # ---------- 查询样本 ----------

    def iter_scene_samples(
        self, scene: str, limit: int | None = None, mode: str | None = None
    ) -> Iterator[ObserverReferenceSample]:
        scene_dir = self.scene_dir(scene)
        ref = self.reference(scene, mode)
        npz_files = sorted(p for p in scene_dir.glob("*.npz") if not p.name.startswith("."))
        if limit is not None:
            npz_files = npz_files[:limit]

        for npz_path in npz_files:
            yield ObserverReferenceSample(
                scene=scene,
                sample_id=npz_path.stem,
                observer_npz=npz_path,
                reference_map=ref.map_path,
                reference_dsm=ref.dsm_path,
            )

    def load_sample(self, sample: ObserverReferenceSample) -> dict[str, np.ndarray]:
        """读取一个查询样本的数组。缺字段时直接报错，不静默补默认值。"""

        with np.load(sample.observer_npz, allow_pickle=True) as data:
            missing = {"image", "K", "xyz", "euler_deg"} - set(data.files)
            if missing:
                raise KeyError(f"{sample.observer_npz.name} 缺少字段：{sorted(missing)}")
            return {key: data[key] for key in data.files}


def _pair(value) -> tuple[float, float] | None:
    if value is None:
        return None
    return (float(value[0]), float(value[1]))
