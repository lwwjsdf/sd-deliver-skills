"""Tests for config_helper.py."""
import sys

import pytest

from config_helper import get_config, CONFIG_SCHEMA


def test_get_config_returns_args_value_first(monkeypatch):
    monkeypatch.delenv("SA_HOST", raising=False)
    assert get_config("cdp_url", args_value="https://args.com", interactive=False) == "https://args.com"


def test_get_config_returns_env_value_when_no_args(monkeypatch):
    monkeypatch.setenv("SA_HOST", "https://env.com")
    assert get_config("cdp_url", args_value="", interactive=False) == "https://env.com"


def test_get_config_args_overrides_env(monkeypatch):
    monkeypatch.setenv("SA_HOST", "https://env.com")
    assert get_config("cdp_url", args_value="https://args.com", interactive=False) == "https://args.com"


def test_get_config_exits_when_missing(monkeypatch):
    monkeypatch.delenv("SA_HOST", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        get_config("cdp_url", args_value="", interactive=False)
    assert exc_info.value.code == 1


def test_config_schema_has_required_keys():
    for key, schema in CONFIG_SCHEMA.items():
        assert "env_key" in schema
        assert "prompt" in schema
        assert "example" in schema
        assert "help" in schema


def test_get_config_non_interactive_skips_prompt(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        get_config("api_key", args_value="", interactive=False)
    assert exc_info.value.code == 1
