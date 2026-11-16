from __future__ import annotations

import pytest
from pydantic import ValidationError

from crossview.schema import GeoRegistrationRecord


def make_record(**overrides):
    base = dict(
        scene_name="Scene_01",
        sample_id="L01_0001",
        observer_source="oblique.npz",
        reference_source="aerial_map.png",
        gt_x=1.0,
        gt_y=2.0,
        gt_z=0.0,
        pred_x=1.1,
        pred_y=2.0,
        pred_z=0.0,
        error_m=0.1,
    )
    base.update(overrides)
    return GeoRegistrationRecord(**base)


def test_defaults_carry_version_and_units():
    record = make_record()
    assert record.schema_version == "1.0"
    assert record.unit == "m"
    assert record.frame == "local_enu"
    assert record.failure == "none"


def test_to_dict_round_trip_preserves_all_fields():
    record = make_record(best_inliers=2966, adaptive_route="top1_fast_path")
    restored = GeoRegistrationRecord.from_dict(record.to_dict())
    assert restored == record


def test_record_is_immutable():
    record = make_record()
    with pytest.raises(ValidationError):
        record.error_m = 9.9


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        make_record(surprise=1)


def test_missing_required_field_is_rejected():
    with pytest.raises(ValidationError):
        GeoRegistrationRecord(scene_name="Scene_01")
