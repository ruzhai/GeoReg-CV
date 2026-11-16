"""把契约模型导出成 JSON Schema，供 MATLAB / 仿真软件校验。

改了 src/crossview/schema/ 之后跑一次，并把 docs/schema/ 的变化一起提交。
"""

from __future__ import annotations

from crossview.paths import docs_dir
from crossview.schema import Config, GeoRegistrationRecord, MetricsSummary
from crossview.schema.samples import ObserverReferenceSample, ObserverView, ReferenceView
from crossview.schema.serialization import export_schemas

MODELS = {
    "record": GeoRegistrationRecord,
    "metrics": MetricsSummary,
    "observer_view": ObserverView,
    "reference_view": ReferenceView,
    "sample": ObserverReferenceSample,
    "config": Config,
}


def main() -> None:
    written = export_schemas(MODELS, docs_dir() / "schema")
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
