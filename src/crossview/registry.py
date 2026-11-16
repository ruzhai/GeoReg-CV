"""组件注册表：让"换一个方法"只改配置，不改代码。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

_REGISTRY: dict[str, dict[str, Any]] = {}


def register(kind: str, name: str) -> Callable[[T], T]:
    """把实现登记到某个类别下，例如 @register("matcher", "roma")。"""

    def decorator(obj: T) -> T:
        bucket = _REGISTRY.setdefault(kind, {})
        if name in bucket:
            raise ValueError(f"重复注册：{kind}:{name}")
        bucket[name] = obj
        return obj

    return decorator


def get(kind: str, name: str) -> Any:
    try:
        return _REGISTRY[kind][name]
    except KeyError as exc:
        known = ", ".join(available(kind)) or "（空）"
        raise KeyError(f"未注册 {kind}:{name}；可用：{known}") from exc


def build(kind: str, name: str, **kwargs: Any) -> Any:
    return get(kind, name)(**kwargs)


def available(kind: str) -> list[str]:
    return sorted(_REGISTRY.get(kind, {}))


def clear() -> None:
    """仅供测试使用。"""
    _REGISTRY.clear()
