"""全项目共享的枚举。改名或新增只改这里。"""

from __future__ import annotations

from enum import Enum


class CoordinateFrame(str, Enum):
    """结果坐标所在的参考系。缺失时会 silently 用错单位，所以必须显式。"""

    LOCAL_ENU = "local_enu"
    WGS84 = "wgs84"
    PIXEL = "pixel"


class RegistrationRoute(str, Enum):
    """置信度驱动的自适应执行路径。"""

    TOP1_FAST_PATH = "top1_fast_path"
    FALLBACK_TOP2 = "fallback_top2"
    FALLBACK_TOP5 = "fallback_top5"
    FALLBACK_TOP5_AFTER_TOP2 = "fallback_top5_after_top2"
    DIRECT_CENTER = "direct_center"


class FailureReason(str, Enum):
    """失败要有结构化原因，否则只能靠日志猜。"""

    NONE = "none"
    RETRIEVAL_MISS = "retrieval_miss"
    TOO_FEW_MATCHES = "too_few_matches"
    PNP_FAILED = "pnp_failed"
    PHYSICAL_INVALID = "physical_invalid"
    LOW_CONFIDENCE = "low_confidence"
    UNKNOWN = "unknown"


class TargetClass(str, Enum):
    PERSON = "person"
    VEHICLE = "vehicle"
    UNKNOWN = "unknown"
