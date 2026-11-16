"""配置契约：加载即校验，路径只能来自环境变量。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class MissingEnvVar(KeyError):
    """配置引用了未设置的环境变量。"""


def expand_env(value: Any, extra: dict[str, str] | None = None) -> Any:
    """递归展开 ${VAR}。缺失的变量直接报错，不静默留空。

    extra 提供内置变量（例如 CROSSVIEW_PROJECT_ROOT），优先于环境变量。
    """

    if isinstance(value, str):

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if extra and name in extra:
                return extra[name]
            if name not in os.environ:
                raise MissingEnvVar(f"配置引用了未设置的环境变量：{name}")
            return os.environ[name]

        return _ENV_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: expand_env(v, extra) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v, extra) for v in value]
    return value


class DataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: Path
    dataset: str = "anyvisloc"
    scene: str | None = None


class ComponentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class RoutingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_threshold: int = Field(default=1000, ge=0)
    fallback_topk: int = Field(default=2, ge=1)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: DataConfig
    retriever: ComponentConfig | None = None
    matcher: ComponentConfig | None = None
    locator: ComponentConfig | None = None
    routing: RoutingConfig = Field(default_factory=RoutingConfig)

    @classmethod
    def load(cls, path: str | Path) -> Config:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.model_validate(expand_env(raw))
