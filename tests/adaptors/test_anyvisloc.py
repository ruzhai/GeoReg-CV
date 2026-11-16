from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from crossview.adaptors.datasets.anyvisloc import AnyVisLocAdapter, SceneNotFound

REFERENCE = {
    "format_version": "anyvisloc_ref_png_npy_json_v1",
    "scene_name": "Scene_01",
    "scene_id": 1,
    "modes": {
        "aerial": {
            "map_path": "aerial_map.png",
            "dsm_path": "aerial_dsm.npy",
            "map_resolution": [0.32, 0.32],
            "dsm_resolution": [1.98, 1.98],
            "map_origin_local": [0.0, 0.0],
            "dsm_origin_local": [-1.769, -0.896],
        },
        "satellite": {
            "map_path": "satellite_map.png",
            "dsm_path": "satellite_dsm.npy",
            "map_resolution": [0.55, 0.55],
        },
    },
}


def build_scene(root: Path, nested: bool = True, samples: int = 2) -> Path:
    scene = root / "Scene_01" / ("Scene_01" if nested else "")
    scene.mkdir(parents=True)
    (scene / "L01_reference.json").write_text(json.dumps(REFERENCE), encoding="utf-8")
    (scene / "aerial_map.png").write_bytes(b"fake-png")
    np.save(scene / "aerial_dsm.npy", np.zeros((2, 2), dtype=np.float32))
    for index in range(1, samples + 1):
        np.savez(
            scene / f"L01_{index:04d}.npz",
            image=np.zeros((4, 4, 3), dtype=np.uint8),
            K=np.eye(3, dtype=np.float32),
            xyz=np.zeros(3, dtype=np.float32),
            euler_deg=np.zeros(3, dtype=np.float32),
            sample_id=f"L01_{index:04d}",
        )
    return root


def test_discovers_nested_scene(tmp_path):
    build_scene(tmp_path)
    assert AnyVisLocAdapter(tmp_path).scenes() == ["Scene_01"]


def test_reference_reads_resolution_and_origin(tmp_path):
    build_scene(tmp_path)
    ref = AnyVisLocAdapter(tmp_path).reference("Scene_01")

    assert ref.mode == "aerial"
    assert ref.map_resolution == pytest.approx((0.32, 0.32))
    assert ref.map_origin_local == pytest.approx((0.0, 0.0))
    assert ref.dsm_path is not None and ref.dsm_path.exists()


def test_samples_respect_limit(tmp_path):
    build_scene(tmp_path, samples=3)
    adapter = AnyVisLocAdapter(tmp_path)

    all_ids = [s.sample_id for s in adapter.iter_scene_samples("Scene_01")]
    assert all_ids == ["L01_0001", "L01_0002", "L01_0003"]
    assert len(list(adapter.iter_scene_samples("Scene_01", limit=2))) == 2


def test_load_sample_returns_arrays(tmp_path):
    build_scene(tmp_path)
    adapter = AnyVisLocAdapter(tmp_path)
    sample = next(adapter.iter_scene_samples("Scene_01"))

    data = adapter.load_sample(sample)
    assert data["image"].shape == (4, 4, 3)
    assert data["K"].shape == (3, 3)


def test_missing_field_is_reported(tmp_path):
    scene = tmp_path / "Scene_01"
    scene.mkdir()
    (scene / "L01_reference.json").write_text(json.dumps(REFERENCE), encoding="utf-8")
    np.savez(scene / "L01_0001.npz", image=np.zeros((2, 2, 3), dtype=np.uint8))

    adapter = AnyVisLocAdapter(tmp_path)
    sample = next(adapter.iter_scene_samples("Scene_01"))
    with pytest.raises(KeyError, match="缺少字段"):
        adapter.load_sample(sample)


def test_unknown_scene_raises(tmp_path):
    build_scene(tmp_path)
    with pytest.raises(SceneNotFound):
        AnyVisLocAdapter(tmp_path).scene_dir("Scene_99")


def test_unknown_mode_raises(tmp_path):
    build_scene(tmp_path)
    with pytest.raises(KeyError, match="没有"):
        AnyVisLocAdapter(tmp_path).reference("Scene_01", mode="infrared")
