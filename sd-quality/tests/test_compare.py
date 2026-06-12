"""Tests for compare.py."""
import pytest

from compare import (
    _is_anomalous_value,
    _type_match,
    compare_event,
    compare_user_attr,
)


@pytest.mark.parametrize("value,expected", [
    (None, "null_value"),
    ("", "empty_string"),
    ("   ", "empty_string"),
    ("test", "placeholder"),
    ("placeholder", "placeholder"),
    ("TODO", "placeholder"),
    ("xxx", "placeholder"),
    ("foo", "placeholder"),
    ("bar123", "placeholder"),
    ("\x01garbled", "garbled"),
    ("valid value", None),
    (123, None),
])
def test_is_anomalous_value(value, expected):
    assert _is_anomalous_value(value) == expected


@pytest.mark.parametrize("expected_type,value,result", [
    ("string", "hello", True),
    ("string", 123, False),
    ("number", 123, True),
    ("number", 12.5, True),
    ("number", "123", False),
    ("boolean", True, True),
    ("boolean", "true", False),
    ("datetime", "2024-01-01", True),
    ("unknown_type", "anything", True),
])
def test_type_match(expected_type, value, result):
    assert _type_match(expected_type, value) == result


def test_compare_event_passes_when_all_properties_present_and_valid():
    schema = {
        "name": {"type": "string"},
        "amount": {"type": "number"},
    }
    samples = [
        {"name": "Alice", "amount": 100},
        {"name": "Bob", "amount": 200},
    ]
    result = compare_event("OrderPaid", schema, samples)
    assert result.status == "pass"
    assert result.imported_count == 2


def test_compare_event_missing_when_no_samples():
    result = compare_event("OrderPaid", {"name": {"type": "string"}}, [])
    assert result.status == "missing"
    assert any(i.category == "missing_event" for i in result.issues)


def test_compare_event_anomaly_when_property_missing():
    schema = {"name": {"type": "string"}, "amount": {"type": "number"}}
    samples = [{"name": "Alice"}]
    result = compare_event("OrderPaid", schema, samples)
    assert result.status == "anomaly"
    assert any(i.category == "missing_property" and i.field == "amount" for i in result.issues)


def test_compare_event_anomaly_on_type_mismatch():
    schema = {"amount": {"type": "number"}}
    samples = [{"amount": "not a number"}]
    result = compare_event("OrderPaid", schema, samples)
    assert result.status == "anomaly"
    assert any(i.category == "type_mismatch" for i in result.issues)


def test_compare_event_anomaly_on_placeholder_values():
    schema = {"name": {"type": "string"}}
    samples = [{"name": "test"}]
    result = compare_event("OrderPaid", schema, samples)
    assert result.status == "anomaly"
    assert any(i.category == "value_anomaly" for i in result.issues)


def test_compare_event_anomaly_on_invalid_enum():
    schema = {"status": {"type": "string", "enum_values": ["paid", "pending"]}}
    samples = [{"status": "cancelled"}]
    result = compare_event("OrderPaid", schema, samples)
    assert result.status == "anomaly"
    assert any(i.category == "value_anomaly" for i in result.issues)


def test_compare_user_attr_passes():
    result = compare_user_attr("user_type", {"type": "string"}, [{"user_type": "vip"}])
    assert result.status == "pass"


def test_compare_user_attr_missing_when_no_samples():
    result = compare_user_attr("user_type", {"type": "string"}, [])
    assert result.status == "missing"


def test_compare_user_attr_anomaly_when_attr_empty():
    result = compare_user_attr("user_type", {"type": "string"}, [{}])
    assert result.status == "anomaly"
    assert any(i.category == "missing_property" for i in result.issues)
