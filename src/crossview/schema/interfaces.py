"""模块契约：各阶段的 Protocol。实现放在 adaptors/，决策放在 core/。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from crossview.schema.samples import ObserverReferenceSample, ReferenceView


class MatchResult:
    """匹配结果的形状占位说明。

    实现时请用 dataclass 提供以下字段，失败时 `reason` 非空：
    points_src, points_dst, scores, inliers, reason
    """


@runtime_checkable
class Retriever(Protocol):
    """从参考视图检索候选区域。"""

    def retrieve(self, sample: ObserverReferenceSample, top_k: int) -> list[str]: ...


@runtime_checkable
class Matcher(Protocol):
    """把观察者图像与参考切片对齐。"""

    def match(self, observer: np.ndarray, reference: np.ndarray) -> MatchResult: ...


@runtime_checkable
class Locator(Protocol):
    """从匹配结果反解地理位置。"""

    def locate(self, matches: MatchResult) -> np.ndarray | None: ...


@runtime_checkable
class TimeAligner(Protocol):
    """对齐异步到达的多源观测。"""

    def align(self, timestamps: np.ndarray, values: np.ndarray) -> np.ndarray: ...


@runtime_checkable
class ReferenceLoader(Protocol):
    """加载参考视图。"""

    def load(self) -> ReferenceView: ...
