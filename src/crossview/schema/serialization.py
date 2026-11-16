"""序列化单独一层：格式要变时只动这一个文件。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


def dumps(model: BaseModel) -> str:
    return model.model_dump_json(indent=2)


def loads(model_cls: type[TModel], text: str) -> TModel:
    return model_cls.model_validate_json(text)


def write(model: BaseModel, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps(model) + "\n", encoding="utf-8")
    return target


def read(model_cls: type[TModel], path: str | Path) -> TModel:
    return loads(model_cls, Path(path).read_text(encoding="utf-8"))


def dump_json_schema(model_cls: type[BaseModel]) -> dict[str, Any]:
    """导出 JSON Schema，供 MATLAB、仿真软件等非 Python 消费者校验。"""

    return model_cls.model_json_schema()


def export_schemas(models: dict[str, type[BaseModel]], out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model_cls in models.items():
        path = out / f"{name}.schema.json"
        path.write_text(
            json.dumps(dump_json_schema(model_cls), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written
