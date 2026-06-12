"""Tests for import_meta_data.py."""
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from import_meta_data import import_events, import_user_attrs, test_api_connection as _test_api_connection


@dataclass
class FakeProp:
    name: str
    value_type: str = "string"


@dataclass
class FakeSchema:
    properties: list = field(default_factory=list)


@dataclass
class FakeAttr:
    name: str
    value_type: str = "string"


class FakePlan:
    def __init__(self, events=None, attrs=None):
        self._events = events or []
        self._attrs = attrs or []

    def list_events(self):
        return self._events

    def get_event_schema(self, event_name):
        return FakeSchema(properties=[FakeProp("amount", "number"), FakeProp("status", "string")])

    def get_user_attributes(self):
        return self._attrs


def test_test_api_connection_success():
    with patch("import_meta_data.SensorsOpenAPI") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.list_events.return_value = [{"original_name": "EventA"}]
        mock_api_cls.return_value = mock_api
        assert _test_api_connection("https://demo.com", "key", "default") is True


def test_test_api_connection_failure():
    with patch("import_meta_data.SensorsOpenAPI") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.list_events.side_effect = Exception("connection error")
        mock_api_cls.return_value = mock_api
        assert _test_api_connection("https://demo.com", "key", "default") is False


def test_import_events_creates_custom_events_and_fields():
    plan = FakePlan(events=["OrderPaid", "$pageview"])
    api = MagicMock()
    api.create_event.return_value = True
    api.batch_create_fields.return_value = {"ok": ["amount", "status"], "failed": []}

    results = import_events(api, plan)
    assert len(results) == 1
    assert results[0]["name"] == "OrderPaid"
    assert results[0]["success"] is True
    assert results[0]["fields"] == 2
    api.create_event.assert_called_with(original_name="OrderPaid", display_name="OrderPaid")


def test_import_events_skips_reserved_and_builtin_fields():
    plan = FakePlan(events=["OrderPaid"])
    api = MagicMock()
    api.create_event.return_value = True
    api.batch_create_fields.return_value = {"ok": [], "failed": []}

    with patch.object(plan, "get_event_schema", return_value=FakeSchema(properties=[
        FakeProp("Id", "string"),
        FakeProp("platformType", "string"),
        FakeProp("amount", "number"),
    ])):
        results = import_events(api, plan)
        assert results[0]["fields"] == 1
        call_args = api.batch_create_fields.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["name"] == "amount"


def test_import_events_failed_create():
    plan = FakePlan(events=["OrderPaid"])
    api = MagicMock()
    api.create_event.return_value = False

    results = import_events(api, plan)
    assert results[0]["success"] is False
    assert results[0]["fields"] == 0


def test_import_user_attrs_creates_fields():
    plan = FakePlan(attrs=[FakeAttr("user_type", "string"), FakeAttr("age", "number")])
    api = MagicMock()
    api.create_user_field.return_value = True

    result = import_user_attrs(api, plan)
    assert "user_type" in result["ok"]
    assert "age" in result["ok"]
    assert len(result["failed"]) == 0


def test_import_user_attrs_skips_reserved():
    plan = FakePlan(attrs=[FakeAttr("Id", "string"), FakeAttr("platformType", "string")])
    api = MagicMock()

    result = import_user_attrs(api, plan)
    assert result["ok"] == []
    assert result["failed"] == []
    api.create_user_field.assert_not_called()
