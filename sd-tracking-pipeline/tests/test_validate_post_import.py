"""Tests for validate_post_import.py."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from unittest.mock import MagicMock

from validate_post_import import validate_event_properties, validate_enum_values, main


def test_validate_event_properties_passes_when_complete():
    api = MagicMock()
    api.query_event_properties_sample.return_value = [
        {"amount": 100, "pay_method": "wechat"},
        {"amount": 200, "pay_method": "alipay"},
    ]
    result = validate_event_properties(
        api, "OrderPaid", ["amount", "pay_method"], "2024-01-01", "2024-01-31"
    )
    assert "✅ 通过" in result["status"]
    assert result["sample_count"] == 2
    assert result["property_completeness"]["amount"]["rate"] == "100.0%"


def test_validate_event_properties_warns_on_low_completeness():
    api = MagicMock()
    api.query_event_properties_sample.return_value = [
        {"amount": 100},
        {"amount": None},
        {"amount": ""},
        {"amount": 200},
        {"amount": 300},
        {"amount": 400},
        {"amount": 500},
        {"amount": 600},
        {"amount": 700},
        {"amount": 800},
    ]
    result = validate_event_properties(
        api, "OrderPaid", ["amount"], "2024-01-01", "2024-01-31"
    )
    assert "⚠️ 有问题" in result["status"]
    assert any("完整率过低" in issue for issue in result["issues"])


def test_validate_event_properties_no_data():
    api = MagicMock()
    api.query_event_properties_sample.return_value = []
    result = validate_event_properties(
        api, "OrderPaid", ["amount"], "2024-01-01", "2024-01-31"
    )
    assert "❌ 未找到数据" in result["status"]
    assert result["sample_count"] == 0


def test_validate_event_properties_detects_type_inconsistency():
    api = MagicMock()
    api.query_event_properties_sample.return_value = [
        {"amount": 100},
        {"amount": "not a number"},
    ]
    result = validate_event_properties(
        api, "OrderPaid", ["amount"], "2024-01-01", "2024-01-31"
    )
    assert any("类型不一致" in issue for issue in result["issues"])


def test_validate_enum_values_passes():
    api = MagicMock()
    api.query_property_distribution.return_value = {"wechat": 10, "alipay": 5}
    result = validate_enum_values(
        api, "OrderPaid", "pay_method", ["wechat", "alipay", "card"],
        "2024-01-01", "2024-01-31"
    )
    assert "✅ 通过" in result["status"]
    assert len(result["invalid_values"]) == 0


def test_validate_enum_values_finds_invalid():
    api = MagicMock()
    api.query_property_distribution.return_value = {"wechat": 10, "cash": 2}
    result = validate_enum_values(
        api, "OrderPaid", "pay_method", ["wechat", "alipay", "card"],
        "2024-01-01", "2024-01-31"
    )
    assert "⚠️ 有非法值" in result["status"]
    assert any(iv["value"] == "cash" for iv in result["invalid_values"])


def test_validate_enum_values_no_data():
    api = MagicMock()
    api.query_property_distribution.return_value = {}
    result = validate_enum_values(
        api, "OrderPaid", "pay_method", ["wechat"],
        "2024-01-01", "2024-01-31"
    )
    assert "❌ 未找到数据" in result["status"]


def test_main_exits_with_error_on_missing_config(monkeypatch):
    monkeypatch.delenv("SA_HOST", raising=False)
    monkeypatch.delenv("SA_PROJECT", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    sys.argv = ["validate_post_import.py", "--events", "OrderPaid", "--properties", "amount"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
