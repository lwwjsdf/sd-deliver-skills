"""Tests for validate_import.py."""
import json
import sys
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

from validate_import import _parse_jsonl, validate_import


def _write_jsonl(tmp_path, records):
    path = tmp_path / "data.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_parse_jsonl_empty_file(tmp_path):
    path = _write_jsonl(tmp_path, [])
    counts, start, end = _parse_jsonl(path)
    assert len(counts) == 0
    assert start  # falls back to default date range
    assert end


def test_parse_jsonl_counts_custom_events(tmp_path):
    records = [
        {"type": "track", "event": "OrderPaid", "time": 1700000000, "properties": {"$time": 1700000100}},
        {"type": "track", "event": "OrderPaid", "time": 1700000200},
        {"type": "track", "event": "ProductViewed", "time": 1700000300},
        {"type": "profile_set", "event": "$profile_set", "time": 1700000400},
        {"type": "track", "event": "$pageview", "time": 1700000500},
    ]
    path = _write_jsonl(tmp_path, records)
    counts, start, end = _parse_jsonl(path)
    assert counts["OrderPaid"] == 2
    assert counts["ProductViewed"] == 1
    assert "$pageview" not in counts
    assert "$profile_set" not in counts


def test_parse_jsonl_millisecond_timestamp(tmp_path):
    ms = 1700000000000  # milliseconds
    path = _write_jsonl(tmp_path, [{"type": "track", "event": "A", "time": ms}])
    counts, start, end = _parse_jsonl(path)
    assert start == "2023-11-14"
    assert end == "2023-11-14"


def test_parse_jsonl_uses_properties_time(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "A", "time": 1700000000, "properties": {"$time": 1700001000}}
    ])
    counts, start, end = _parse_jsonl(path)
    # properties.$time takes precedence
    assert start == "2023-11-14"


@patch("validate_import.SensorsOpenAPI")
def test_validate_import_all_match(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "time": 1700000000},
        {"type": "track", "event": "OrderPaid", "time": 1700000100},
    ])
    mock_api = MagicMock()
    mock_api.query_event_counts.return_value = {"OrderPaid": 2}
    mock_api_cls.return_value = mock_api

    result = validate_import("https://demo.com", "default", "key", path)
    assert result is True
    mock_api.query_event_counts.assert_called_once()


@patch("validate_import.SensorsOpenAPI")
def test_validate_import_missing_event(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "time": 1700000000},
    ])
    mock_api = MagicMock()
    mock_api.query_event_counts.return_value = {"OrderPaid": 0}
    mock_api_cls.return_value = mock_api

    result = validate_import("https://demo.com", "default", "key", path)
    assert result is False


@patch("validate_import.SensorsOpenAPI")
def test_validate_import_partial_data(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "time": 1700000000},
    ])
    mock_api = MagicMock()
    mock_api.query_event_counts.return_value = {}  # empty response
    mock_api_cls.return_value = mock_api

    result = validate_import("https://demo.com", "default", "key", path)
    assert result is False


@patch("validate_import.SensorsOpenAPI")
def test_validate_import_skips_when_no_custom_events(mock_api_cls, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "$pageview", "time": 1700000000},
    ])
    result = validate_import("https://demo.com", "default", "key", path)
    assert result is True
    mock_api_cls.assert_not_called()


def test_validate_import_uses_wait_seconds(tmp_path):
    path = _write_jsonl(tmp_path, [{"type": "track", "event": "A", "time": 1700000000}])
    with patch("validate_import.SensorsOpenAPI") as mock_api_cls, \
         patch("validate_import.time.sleep") as mock_sleep:
        mock_api = MagicMock()
        mock_api.query_event_counts.return_value = {"A": 1}
        mock_api_cls.return_value = mock_api

        validate_import("https://demo.com", "default", "key", path, wait_seconds=5)
        mock_sleep.assert_called_once_with(5)
