"""Tests for project_context.py."""
import pytest

from project_context import (
    check_skill_context,
    get_context_value,
    set_context_value,
    _load_context,
    _save_context,
)


def test_load_context_creates_default(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    data = _load_context(path)
    assert data["version"] == "1.0"
    assert "facts" in data
    assert data["facts"] == {}


def test_set_and_get_context_value(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    set_context_value(path, "business.dau", 1000000, source="test")
    assert get_context_value(path, "business.dau") == 1000000


def test_set_parses_json_value(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    set_context_value(path, "infra.include_cdp", "true", source="test")
    assert get_context_value(path, "infra.include_cdp") is True


def test_set_refuses_overwrite_by_default(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    set_context_value(path, "business.dau", 1000000, source="test")
    ok = set_context_value(path, "business.dau", 2000000, source="test")
    assert not ok
    assert get_context_value(path, "business.dau") == 1000000


def test_set_overwrite(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    set_context_value(path, "business.dau", 1000000, source="test")
    ok = set_context_value(path, "business.dau", 2000000, source="test", overwrite=True)
    assert ok
    assert get_context_value(path, "business.dau") == 2000000


def test_check_skill_context_missing(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    result = check_skill_context(path, "sd-design-performance-test")
    assert "business.dau" in result["missing"]
    assert "business.daily_events" in result["missing"]


def test_check_skill_context_known(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    set_context_value(path, "business.dau", 1000000, source="test")
    set_context_value(path, "business.daily_events", 5000000, source="test")
    set_context_value(path, "business.retention_days", 365, source="test")
    set_context_value(path, "infra.cloud", "AWS", source="test")
    set_context_value(path, "infra.region", "ap-southeast-1", source="test")

    result = check_skill_context(path, "sd-design-performance-test")
    assert result["known"] == [
        "business.dau",
        "business.daily_events",
        "business.retention_days",
        "infra.cloud",
        "infra.region",
    ]
    assert result["missing"] == []


def test_check_unknown_skill(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    result = check_skill_context(path, "unknown-skill")
    assert result == {"known": [], "missing": [], "optional_present": [], "optional_missing": []}


def test_save_updates_last_updated(tmp_path):
    path = tmp_path / "PROJECT_CONTEXT.yaml"
    data = _load_context(path)
    original = data["last_updated"]
    _save_context(path, data)
    updated = _load_context(path)["last_updated"]
    assert updated != original
