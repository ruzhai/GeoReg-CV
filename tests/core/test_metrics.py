from __future__ import annotations

import pytest

from crossview.core.metrics.summary import summarize
from crossview.schema.records import GeoRegistrationRecord


def make_record(error_m: float) -> GeoRegistrationRecord:
    return GeoRegistrationRecord(
        scene_name="Scene_01",
        sample_id=f"S{error_m}",
        observer_source="obs",
        reference_source="ref",
        gt_x=0.0,
        gt_y=0.0,
        pred_x=0.0,
        pred_y=0.0,
        error_m=error_m,
    )


def test_summarize_computes_rates_and_errors():
    summary = summarize([make_record(e) for e in [0.5, 1.5, 4.0, 10.0]])

    assert summary.count == 4
    assert summary.mean_error_m == pytest.approx(4.0)
    assert summary.median_error_m == pytest.approx(2.75)
    assert summary.max_error_m == pytest.approx(10.0)
    assert summary.success_1m == pytest.approx(0.25)
    assert summary.success_3m == pytest.approx(0.50)
    assert summary.success_5m == pytest.approx(0.75)


def test_empty_input_is_an_error_not_a_zero():
    with pytest.raises(ValueError):
        summarize([])
