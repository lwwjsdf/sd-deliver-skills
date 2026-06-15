"""Tests for generate_mock_data.py."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from generate_mock_data import (
    _parse_options,
    _extract_prop,
    generate_value,
    generate_identities,
    build_track_record,
    build_profile_record,
    write_outputs,
    _JSONEncoder,
)


def test_parse_options_newline_separated():
    assert _parse_options("A\nB\nC") == ["A", "B", "C"]


def test_parse_options_semicolon_separated():
    assert _parse_options("A;B;C") == ["A", "B", "C"]


def test_parse_options_single_value_returns_empty():
    assert _parse_options("only one") == []


def test_parse_options_empty_returns_empty():
    assert _parse_options("") == []
    assert _parse_options(None) == []


def test_extract_prop_extracts_fields():
    row = ("Event", "prop_name", "Prop Display", "String", "sample", "remark")
    col = {
        "Event Variable Name": 0,
        "Event  Attribute Variable Name": 1,
        "Event  Attribute Variable Display Name": 2,
        "Date Type": 3,
        "Sample Data": 4,
        "Remark": 5,
    }
    prop = _extract_prop(
        row, col,
        "Event  Attribute Variable Name",
        "Event  Attribute Variable Display Name",
        "Date Type",
        "Sample Data",
        "Remark",
    )
    assert prop["name"] == "prop_name"
    assert prop["display_name"] == "Prop Display"
    assert prop["type"] == "String"
    assert prop["sample"] == "sample"


def test_extract_prop_missing_name_returns_empty():
    row = ("Event", None, "Display", "String", "sample", "remark")
    col = {
        "Event Variable Name": 0,
        "Event  Attribute Variable Name": 1,
    }
    assert _extract_prop(
        row, col,
        "Event  Attribute Variable Name",
        "Event  Attribute Variable Display Name",
        "Date Type",
        "Sample Data",
        "Remark",
    ) == {}


def test_generate_value_uses_options():
    prop = {"type": "String", "options": ["A", "B", "C"]}
    assert generate_value(prop) in ["A", "B", "C"]


def test_generate_value_uses_sample():
    prop = {"type": "String", "sample": "Hello", "options": []}
    assert generate_value(prop) == "Hello"


def test_generate_value_boolean():
    prop = {"type": "boolean"}
    assert generate_value(prop) in [True, False]


def test_generate_value_number():
    prop = {"type": "number"}
    val = generate_value(prop)
    assert isinstance(val, (int, float))


def test_generate_value_datetime():
    prop = {"type": "datetime"}
    val = generate_value(prop)
    assert isinstance(val, str)
    assert "T" in val


def test_generate_identities_with_defs():
    defs = [
        {"name": "$identity_login_id"},
        {"name": "$identity_email"},
        {"name": "$identity_mobile"},
        {"name": "$identity_anonymous_id"},
    ]
    ids = generate_identities(defs, "uid123", 1)
    assert ids["$identity_login_id"] == "uid123"
    assert "@example.com" in ids["$identity_email"]
    assert ids["$identity_mobile"].startswith("136")
    assert "anon_" in ids["$identity_anonymous_id"]


def test_generate_identities_empty_defs():
    ids = generate_identities([], "uid123", 1)
    assert ids["$identity_login_id"] == "uid123"


def test_build_track_record():
    event = {
        "name": "OrderPaid",
        "properties": [
            {"name": "amount", "type": "number"},
        ],
    }
    record = build_track_record(event, "uid1", 1700000000000, 1, "demo", [])
    assert record["event"] == "OrderPaid"
    assert record["distinct_id"] == "uid1"
    assert record["type"] == "track"
    assert record["project"] == "demo"
    assert "amount" in record["properties"]


def test_build_profile_record():
    attrs = [{"name": "user_type", "type": "string", "sample": "vip"}]
    record = build_profile_record(attrs, "uid1", 1, "demo", [])
    assert record["type"] == "profile_set"
    assert record["properties"]["user_type"] == "vip"


def test_json_encoder_datetime():
    data = {"ts": datetime(2024, 1, 1, 12, 0, 0)}
    encoded = json.dumps(data, cls=_JSONEncoder)
    assert "2024-01-01T12:00:00.000Z" in encoded


def test_write_outputs(tmp_path):
    records = [{"type": "track", "event": "A"}]
    jsonl_path, sample_path = write_outputs(records, str(tmp_path), "test")
    assert Path(jsonl_path).exists()
    assert Path(sample_path).exists()
    with open(jsonl_path) as f:
        assert json.loads(f.read()) == records[0]
    with open(sample_path) as f:
        assert json.load(f) == records


def test_write_outputs_creates_directory(tmp_path):
    output_dir = tmp_path / "nested" / "dir"
    records = [{"type": "track", "event": "A"}]
    write_outputs(records, str(output_dir), "test")
    assert output_dir.exists()
