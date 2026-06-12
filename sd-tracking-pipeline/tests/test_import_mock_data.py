"""Tests for import_mock_data.py."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from import_mock_data import get_batch_info, import_data, main


def _write_jsonl(tmp_path, records):
    path = tmp_path / "data.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_get_batch_info(tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "distinct_id": "u1", "properties": {"$batch_id": "b1"}},
        {"type": "track", "event": "OrderPaid", "distinct_id": "u1", "properties": {"$batch_id": "b1"}},
        {"type": "track", "event": "ProductViewed", "distinct_id": "u2", "properties": {"$batch_id": "b1"}},
        {"type": "profile_set", "distinct_id": "u1", "properties": {}},
    ])
    info = get_batch_info(path)
    assert info["total_records"] == 4
    assert info["unique_users"] == 2
    assert info["event_types"] == 3  # OrderPaid, ProductViewed, profile_set
    assert info["batch_ids"] == ["b1"]
    assert dict(info["top_events"])["OrderPaid"] == 2


@patch("import_mock_data.sensorsanalytics")
def test_import_data_tracks_and_profiles(mock_sdk, tmp_path):
    path = _write_jsonl(tmp_path, [
        {"type": "track", "event": "OrderPaid", "distinct_id": "u1",
         "properties": {"amount": 100}, "$is_login_id": True},
        {"type": "profile_set", "distinct_id": "u1", "properties": {"level": "vip"}},
    ])

    mock_consumer = MagicMock()
    mock_sa = MagicMock()
    mock_sdk.BatchConsumer.return_value = mock_consumer
    mock_sdk.SensorsAnalytics.return_value = mock_sa

    import_data(path, "https://demo.com/sa?project=default", skip_confirm=True)

    mock_sa.track.assert_called_once()
    mock_sa.profile_set.assert_called_once()
    mock_sa.close.assert_called_once()


@patch("import_mock_data.sensorsanalytics")
def test_import_data_missing_file_exits(mock_sdk, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        import_data(str(tmp_path / "missing.jsonl"), "https://demo.com", skip_confirm=True)
    assert exc_info.value.code == 1


def test_main_exits_when_missing_config(monkeypatch):
    monkeypatch.delenv("SA_TRACK_URL", raising=False)
    sys.argv = ["import_mock_data.py", "--yes"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
