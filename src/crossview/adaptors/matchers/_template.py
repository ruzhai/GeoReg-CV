"""新匹配器的起点。复制这个文件，改类名和名字，然后实现 match()。

不要从空白文件开始写：复制 → 改名 → 改实现 → 加配置，四步接入。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from crossview.registry import register


@dataclass(frozen=True)
class MatchOutput:
    """契约里要求的匹配结果形状。失败时 reason 必须非空。"""

    points_src: np.ndarray
    points_dst: np.ndarray
    scores: np.ndarray
    inliers: int
    reason: str = ""
    extra: dict = field(default_factory=dict)


@register("matcher", "template")
class TemplateMatcher:
    """复制本类，把 'template' 改成你的方法名。"""

    def __init__(self, max_points: int = 2000) -> None:
        self.max_points = max_points

    def match(self, observer: np.ndarray, reference: np.ndarray) -> MatchOutput:
        raise NotImplementedError(
            "在这里实现你的匹配逻辑。输入是 numpy 数组，不要在这里读文件——"
            "读文件属于 adaptors/datasets。"
        )
