"""把一组配准记录压成指标。纯计算，不读文件。"""

from __future__ import annotations

from collections.abc import Sequence
from statistics import mean, median

from crossview.schema.records import GeoRegistrationRecord, MetricsSummary


def summarize(records: Sequence[GeoRegistrationRecord]) -> MetricsSummary:
    if not records:
        raise ValueError("没有记录可统计")

    errors = [record.error_m for record in records]
    count = len(errors)

    def success_rate(threshold: float) -> float:
        return sum(1 for error in errors if error <= threshold) / count

    return MetricsSummary(
        count=count,
        mean_error_m=mean(errors),
        median_error_m=median(errors),
        success_1m=success_rate(1.0),
        success_3m=success_rate(3.0),
        success_5m=success_rate(5.0),
        max_error_m=max(errors),
    )
