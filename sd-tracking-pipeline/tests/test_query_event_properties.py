"""Tests for query_event_properties.py."""
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from query_event_properties import main


def test_main_sample_query(capsys, monkeypatch):
    monkeypatch.setenv("SA_HOST", "https://demo.com")
    monkeypatch.setenv("SA_PROJECT", "uat")
    monkeypatch.setenv("API_KEY", "key")
    sys.argv = [
        "query_event_properties.py",
        "--event", "OrderPaid",
        "--property", "amount",
        "--sample-size", "10",
        "--start-date", "2025-01-01",
        "--end-date", "2025-01-02",
    ]

    with patch("query_event_properties.SensorsOpenAPI") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.query_event_properties_sample.return_value = [
            {"amount": 100},
            {"amount": 200.5},
        ]
        mock_api_cls.return_value = mock_api

        main()

    mock_api.query_event_properties_sample.assert_called_once()
    captured = capsys.readouterr()
    assert "OrderPaid" in captured.out
    assert "amount" in captured.out


def test_main_distribution_query(capsys, monkeypatch):
    monkeypatch.setenv("SA_HOST", "https://demo.com")
    monkeypatch.setenv("SA_PROJECT", "uat")
    monkeypatch.setenv("API_KEY", "key")
    sys.argv = [
        "query_event_properties.py",
        "--event", "OrderPaid",
        "--property", "pay_method",
        "--distribution",
        "--top-n", "5",
    ]

    with patch("query_event_properties.SensorsOpenAPI") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.query_property_distribution.return_value = {"alipay": 3, "wechat": 2}
        mock_api_cls.return_value = mock_api

        main()

    mock_api.query_property_distribution.assert_called_once()
    captured = capsys.readouterr()
    assert "alipay" in captured.out


def test_main_exits_when_no_data(capsys, monkeypatch):
    monkeypatch.setenv("SA_HOST", "https://demo.com")
    monkeypatch.setenv("SA_PROJECT", "uat")
    monkeypatch.setenv("API_KEY", "key")
    sys.argv = [
        "query_event_properties.py",
        "--event", "OrderPaid",
        "--property", "amount",
    ]

    with patch("query_event_properties.SensorsOpenAPI") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.query_event_properties_sample.return_value = []
        mock_api_cls.return_value = mock_api

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
