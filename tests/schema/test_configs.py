from __future__ import annotations

import pytest
from pydantic import ValidationError

from crossview.schema import Config
from crossview.schema.configs import MissingEnvVar, expand_env

CONFIG_TEXT = """
data:
  root: ${CROSSVIEW_DATA_ROOT}
  scene: Scene_01
retriever:
  name: camp
  params:
    top_k: 5
routing:
  confidence_threshold: 1200
"""


def test_env_var_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("CROSSVIEW_DATA_ROOT", "D:/data")
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG_TEXT, encoding="utf-8")

    config = Config.load(path)
    assert str(config.data.root).replace("\\", "/") == "D:/data"
    assert config.retriever.name == "camp"
    assert config.routing.confidence_threshold == 1200


def test_missing_env_var_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.delenv("CROSSVIEW_DATA_ROOT", raising=False)
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG_TEXT, encoding="utf-8")

    with pytest.raises(MissingEnvVar):
        Config.load(path)


def test_unknown_section_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("CROSSVIEW_DATA_ROOT", "D:/data")
    path = tmp_path / "config.yaml"
    path.write_text("data:\n  root: ${CROSSVIEW_DATA_ROOT}\noops: 1\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        Config.load(path)


def test_expand_env_is_recursive():
    import os

    os.environ["CV_A"] = "alpha"
    assert expand_env({"k": ["${CV_A}", {"n": "${CV_A}"}]}) == {"k": ["alpha", {"n": "alpha"}]}
