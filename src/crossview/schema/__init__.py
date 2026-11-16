"""契约层：只定义数据形状，不 import 任何业务模块。"""

from crossview.schema.configs import Config, DataConfig, RoutingConfig, expand_env
from crossview.schema.enums import CoordinateFrame, FailureReason, RegistrationRoute, TargetClass
from crossview.schema.records import SCHEMA_VERSION, GeoRegistrationRecord, MetricsSummary
from crossview.schema.samples import (
    ObserverReferenceSample,
    ObserverView,
    ReferenceView,
    SceneReference,
)
from crossview.schema.serialization import dumps, export_schemas, loads, read, write

__all__ = [
    "SCHEMA_VERSION",
    "Config",
    "CoordinateFrame",
    "DataConfig",
    "FailureReason",
    "GeoRegistrationRecord",
    "MetricsSummary",
    "ObserverReferenceSample",
    "ObserverView",
    "ReferenceView",
    "RegistrationRoute",
    "SceneReference",
    "RoutingConfig",
    "TargetClass",
    "dumps",
    "expand_env",
    "export_schemas",
    "loads",
    "read",
    "write",
]
