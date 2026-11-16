from __future__ import annotations

import json

from crossview.schema import GeoRegistrationRecord, dumps, export_schemas, loads, read, write
from tests.schema.test_records import make_record


def test_json_round_trip():
    record = make_record()
    restored = loads(GeoRegistrationRecord, dumps(record))
    assert restored == record


def test_write_and_read_file(tmp_path):
    record = make_record()
    path = write(record, tmp_path / "nested" / "record.json")
    assert path.exists()
    assert read(GeoRegistrationRecord, path) == record


def test_export_schema_produces_valid_json(tmp_path):
    written = export_schemas({"record": GeoRegistrationRecord}, tmp_path)
    assert len(written) == 1
    data = json.loads(written[0].read_text(encoding="utf-8"))
    assert "properties" in data
    assert "schema_version" in data["properties"]
