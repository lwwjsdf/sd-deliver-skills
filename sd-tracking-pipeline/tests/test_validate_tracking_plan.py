"""Tests for validate_tracking_plan.py."""
import json
from dataclasses import dataclass, field
from typing import List

import pytest

from validate_tracking_plan import (
    _parse_jsonl_records,
    _check_enum_compliance,
    _check_type_compliance,
    _check_null_rate,
    ValidationReport,
)


@dataclass
class FakeProp:
    name: str = "prop"
    value_type: str = "string"
    enum_values: List[str] = field(default_factory=list)


def _write_jsonl(tmp_path, records):
    path = tmp_path / "data.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_parse_jsonl_records_counts_and_records(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "time": 1700000000, "properties": {"amount": 100}},
        {"type": "track", "event": "OrderPaid", "time": 1700000100, "properties": {"amount": 200}},
        {"type": "track", "event": "$pageview", "time": 1700000200},
    ])
    counts, records, start, end = _parse_jsonl_records(path)
    assert counts["OrderPaid"] == 2
    assert len(records["OrderPaid"]) == 2
    assert "$pageview" not in counts
    assert start == "2023-11-14"


def test_check_enum_compliance_passes():
    prop = FakeProp(enum_values=["wechat", "alipay"])
    passed, violations = _check_enum_compliance(prop, ["wechat", "alipay", "wechat"])
    assert passed is True
    assert violations == []


def test_check_enum_compliance_fails():
    prop = FakeProp(enum_values=["wechat", "alipay"])
    passed, violations = _check_enum_compliance(prop, ["wechat", "cash"])
    assert passed is False
    assert "cash" in violations


def test_check_enum_compliance_no_enum_defined():
    prop = FakeProp()
    passed, violations = _check_enum_compliance(prop, ["anything"])
    assert passed is True


def test_check_type_compliance_string():
    prop = FakeProp(value_type="string")
    passed, errors = _check_type_compliance(prop, ["a", "b"])
    assert passed is True


def test_check_type_compliance_number():
    prop = FakeProp(value_type="number")
    passed, errors = _check_type_compliance(prop, [1, 2.5])
    assert passed is True


def test_check_type_compliance_number_rejects_bool():
    prop = FakeProp(value_type="number")
    passed, errors = _check_type_compliance(prop, [True])
    assert passed is False


def test_check_type_compliance_bool():
    prop = FakeProp(value_type="boolean")
    passed, errors = _check_type_compliance(prop, [True, False])
    assert passed is True


def test_check_null_rate_passes():
    passed, rate = _check_null_rate("amount", [1, 2, 3, None], threshold=0.5)
    assert passed is True
    assert rate == 0.25


def test_check_null_rate_fails():
    passed, rate = _check_null_rate("amount", [None, "", None], threshold=0.5)
    assert passed is False
    assert rate == 1.0


def test_validation_report_tracks_summary():
    report = ValidationReport("plan.xlsx", "data.jsonl")
    report.add_event_result("OrderPaid", 10, [
        {"prop_name": "amount", "enum_passed": True, "enum_violations": [],
         "type_passed": True, "type_errors": [],
         "null_passed": True, "null_rate": 0.0, "passed": True},
        {"prop_name": "pay_method", "enum_passed": False, "enum_violations": ["cash"],
         "type_passed": True, "type_errors": [],
         "null_passed": True, "null_rate": 0.0, "passed": False},
    ])
    assert report.summary["total_events"] == 1
    assert report.summary["passed_events"] == 0
    assert report.summary["enum_violations"] == 1
    assert report.summary["passed_props"] == 1


def test_validation_report_generate_contains_content():
    report = ValidationReport("plan.xlsx", "data.jsonl")
    report.add_event_result("OrderPaid", 10, [
        {"prop_name": "amount", "enum_passed": True, "enum_violations": [],
         "type_passed": True, "type_errors": [],
         "null_passed": True, "null_rate": 0.0, "passed": True},
    ])
    md = report.generate()
    assert "OrderPaid" in md
    assert "amount" in md
    assert "plan.xlsx" in md
