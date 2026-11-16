"""结果契约：一次跨视角配准的完整记录。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"


class GeoRegistrationRecord(BaseModel):
    """观察者视角到参考视角的一次配准结果。

    字段与旧 `system.result_schema.GeoRegistrationRecord` 保持兼容，
    新增了版本号、坐标系、单位与结构化失败原因。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = SCHEMA_VERSION
    frame: str = "local_enu"
    unit: str = "m"
    failure: str = "none"

    scene_name: str
    sample_id: str
    observer_source: str
    reference_source: str

    gt_x: float
    gt_y: float
    gt_z: float = 0.0
    pred_x: float
    pred_y: float
    pred_z: float = 0.0
    error_m: float

    success_1m: bool = False
    success_3m: bool = False
    success_5m: bool = False

    retrieval_method: str = ""
    matching_method: str = ""
    localization_method: str = ""

    retrieval_gt_rank: int | None = None
    recall_at_k: float | None = None
    pdm_at_k: float | None = None

    best_inliers: int | None = None
    total_time_s: float | None = None

    adaptive_route: str = ""
    top1_best_inliers: int | None = None
    confidence_threshold: int | None = None
    fallback_used: bool | None = None
    source_method: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeoRegistrationRecord:
        return cls.model_validate(data)


class MetricsSummary(BaseModel):
    """一组记录的聚合指标。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = SCHEMA_VERSION
    count: int = Field(ge=0)
    mean_error_m: float
    median_error_m: float
    success_1m: float = 0.0
    success_3m: float = 0.0
    success_5m: float = 0.0
    max_error_m: float = 0.0
