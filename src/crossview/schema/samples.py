"""输入契约：数据集适配器必须产出这些形状。"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ObserverView(BaseModel):
    """观察者/低空斜视图像，可带姿态先验。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    image_path: Path | None = None
    source_path: Path
    yaw_pitch: tuple[float, float] | None = None
    height: float | None = None
    note: str = ""


class ReferenceView(BaseModel):
    """无人机/航拍/正射参考视图。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    map_path: Path
    dsm_path: Path | None = None
    coordinate_system: str = ""


class ObserverReferenceSample(BaseModel):
    """一个标准化样本：观察者视角 + 参考视角。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scene: str
    sample_id: str
    observer_npz: Path
    reference_map: Path
    reference_dsm: Path | None = None
