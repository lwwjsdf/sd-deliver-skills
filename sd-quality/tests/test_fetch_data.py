"""Tests for fetch_data.py."""
from unittest.mock import MagicMock, patch

import pytest

from fetch_data import (
    _build_event_schema_map,
    _build_user_attr_map,
    fetch_event_samples,
    fetch_user_attr_samples,
)


class _FakeSchema:
    def __init__(self, name, value_type, required=False, enum_values=None, description="", trigger=""):
        self.name = name
        self.value_type = value_type
        self.required = required
        self.enum_values = enum_values or []
        self.description = description
        self.trigger = trigger


class _FakeEventSchema:
    def __init__(self, properties, trigger):
        self.properties = properties
        self.trigger = trigger


class _FakeTrackingPlan:
    def list_events(self):
        return ["Login", "OrderPaid"]

    def get_event_schema(self, name):
        if name == "Login":
            return _FakeEventSchema(
                properties=[
                    _FakeSchema("isSuccess", "boolean", required=True),
                    _FakeSchema("platform", "string", enum_values=["MP", "Web"]),
                ],
                trigger="MP",
            )
        return None

    def get_user_attributes(self):
        return [_FakeSchema("registerTime", "datetime")]


def test_build_event_schema_map():
    plan = _FakeTrackingPlan()
    schema = _build_event_schema_map(plan)
    assert "Login" in schema
    assert schema["Login"]["properties"]["isSuccess"]["type"] == "boolean"
    assert schema["Login"]["properties"]["isSuccess"]["required"] is True


def test_build_user_attr_map():
    plan = _FakeTrackingPlan()
    attrs = _build_user_attr_map(plan)
    assert "registerTime" in attrs
    assert attrs["registerTime"]["type"] == "datetime"


def test_fetch_event_samples_success():
    api = MagicMock()
    api.custom_query.return_value = {
        "code": "SUCCESS",
        "data": {
            "columns": [{"name": "event"}, {"name": "distinct_id"}],
            "rows": [["Login", "u1"], ["Login", "u2"]],
        },
    }
    samples = fetch_event_samples(api, "Login", "2025-01-01", "2025-01-02", limit=10)
    assert len(samples) == 2
    assert samples[0]["event"] == "Login"
    assert "Login" in api.custom_query.call_args[0][0]


def test_fetch_event_samples_failure():
    api = MagicMock()
    api.custom_query.return_value = {"code": "ERROR"}
    samples = fetch_event_samples(api, "Login", "2025-01-01", "2025-01-02")
    assert samples == []


def test_fetch_event_samples_exception():
    api = MagicMock()
    api.custom_query.side_effect = Exception("network error")
    samples = fetch_event_samples(api, "Login", "2025-01-01", "2025-01-02")
    assert samples == []


def test_fetch_user_attr_samples_success():
    api = MagicMock()
    api.custom_query.return_value = {
        "code": "SUCCESS",
        "data": {
            "columns": [{"name": "distinct_id"}, {"name": "registerTime"}],
            "rows": [["u1", "2025-01-01"]],
        },
    }
    samples = fetch_user_attr_samples(api, "registerTime")
    assert len(samples) == 1
    assert samples[0]["registerTime"] == "2025-01-01"


def test_fetch_user_attr_samples_failure():
    api = MagicMock()
    api.custom_query.return_value = {"code": "ERROR"}
    samples = fetch_user_attr_samples(api, "registerTime")
    assert samples == []


def test_main_with_mocked_api(tmp_path, monkeypatch):
    """Integration test for main() with mocked API and tracking plan."""
    import fetch_data

    plan = _FakeTrackingPlan()
    monkeypatch.setattr(fetch_data, "_parse_tracking_plan", lambda p: plan)
    monkeypatch.setattr(fetch_data, "get_config", lambda key, default: {
        "cdp_url": "https://demo.sensorsdata.cn",
        "project": "default",
        "api_key": "test-key",
    }.get(key, default))

    mock_api = MagicMock()
    mock_api.list_events.return_value = ["Login", "OrderPaid"]
    mock_api.custom_query.return_value = {
        "code": "SUCCESS",
        "data": {
            "columns": [{"name": "event"}],
            "rows": [["Login"]],
        },
    }
    monkeypatch.setattr(fetch_data, "SensorsOpenAPI", lambda *a, **k: mock_api)

    output = tmp_path / "actual.json"

    import sys
    old_argv = sys.argv
    try:
        sys.argv = [
            "fetch_data.py",
            "--tracking-plan", str(tmp_path / "plan.xlsx"),
            "--hours", "24",
            "--output", str(output),
            "--events", "Login",
        ]
        fetch_data.main()
    finally:
        sys.argv = old_argv

    assert output.exists()
    import json
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["meta"]["time_range"]["hours"] == 24
    assert "Login" in data["actual"]["events"]
