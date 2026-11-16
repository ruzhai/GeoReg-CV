"""路径解析：仓库内路径自推导，数据路径只来自环境变量。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


class MissingDataRoot(RuntimeError):
    """没有设置 CROSSVIEW_DATA_ROOT。"""


@lru_cache(maxsize=1)
def project_root() -> Path:
    """向上找 pyproject.toml 定位仓库根，换机器不用改代码。"""

    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("找不到仓库根：向上没有 pyproject.toml")


def data_root() -> Path:
    value = os.environ.get("CROSSVIEW_DATA_ROOT")
    if not value:
        raise MissingDataRoot(
            "请先设置环境变量 CROSSVIEW_DATA_ROOT，例如 export CROSSVIEW_DATA_ROOT='D:/GD/Benchmark'"
        )
    return Path(value)


def data_path(*parts: str) -> Path:
    return data_root().joinpath(*parts)


def experiments_dir() -> Path:
    return project_root() / "experiments"


def outputs_dir() -> Path:
    return project_root() / "outputs"


def configs_dir() -> Path:
    return project_root() / "configs"


def docs_dir() -> Path:
    return project_root() / "docs"
