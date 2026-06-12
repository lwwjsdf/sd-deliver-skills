"""Tests for check_metadata.py."""
import json
import sys
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

from check_metadata import _parse_jsonl_events, check_metadata


def _write_jsonl(tmp_path, records):
    path = tmp_path / "data.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_parse_jsonl_events_extracts_custom_props(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "properties": {"amount": 100, "$lib": "python"}},
        {"type": "track", "event": "OrderPaid", "properties": {"pay_method": "wechat"}},
        {"type": "track", "event": "$pageview", "properties": {"$url": "/home"}},
    ])
    events = _parse_jsonl_events(path)
    assert events["OrderPaid"] == {"amount", "pay_method"}
    assert "$lib" not in events["OrderPaid"]
    assert "$pageview" not in events


def test_parse_jsonl_events_empty(tmp_path):
    path = _write_jsonl(tmp_path, [])
    events = _parse_jsonl_events(path)
    assert events == {}


@patch("check_metadata.SensorsOpenAPI")
def test_check_metadata_all_exist(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "properties": {"amount": 100}},
    ])
    mock_api = MagicMock()
    mock_api.list_events.return_value = [{"original_name": "OrderPaid"}]
    mock_api.list_event_fields.return_value = {"data": {"fields": [{"name": "amount"}]}}
    mock_api_cls.return_value = mock_api

    result = check_metadata("https://demo.com", "default", "key", path)
    assert result is True


@patch("check_metadata.SensorsOpenAPI")
def test_check_metadata_missing_event(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "properties": {"amount": 100}},
    ])
    mock_api = MagicMock()
    mock_api.list_events.return_value = [{"original_name": "OtherEvent"}]
    mock_api_cls.return_value = mock_api

    result = check_metadata("https://demo.com", "default", "key", path)
    assert result is False


@patch("check_metadata.SensorsOpenAPI")
def test_check_metadata_missing_property(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "properties": {"amount": 100}},
    ])
    mock_api = MagicMock()
    mock_api.list_events.return_value = [{"original_name": "OrderPaid"}]
    mock_api.list_event_fields.return_value = {"data": {"fields": []}}
    mock_api_cls.return_value = mock_api

    result = check_metadata("https://demo.com", "default", "key", path)
    assert result is False


@patch("check_metadata.SensorsOpenAPI")
def test_check_metadata_skips_when_only_system_events(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "$pageview", "properties": {"$url": "/home"}},
    ])
    result = check_metadata("https://demo.com", "default", "key", path)
    assert result is True
    mock_api_cls.assert_not_called()


@patch("check_metadata.SensorsOpenAPI")
def test_check_metadata_api_error(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "properties": {"amount": 100}},
    ])
    mock_api = MagicMock()
    mock_api.list_events.side_effect = Exception("connection error")
    mock_api_cls.return_value = mock_api

    result = check_metadata("https://demo.com", "default", "key", path)
    assert result is False
