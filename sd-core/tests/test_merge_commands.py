"""Tests for merge_commands.py."""
import json
import sys
from pathlib import Path

import pytest

from merge_commands import main


def test_main_merges_commands_into_existing_config(tmp_path):
    commands = {
        "sd-foo": {"template": "do foo", "description": "Foo command"},
        "sd-bar": {"template": "do bar", "description": "Bar command"},
    }
    cmd_file = tmp_path / "commands.json"
    cmd_file.write_text(json.dumps(commands), encoding="utf-8")

    config_file = tmp_path / "opencode.jsonc"
    config_file.write_text(
        json.dumps({"command": {"old-cmd": {"template": "old"}}}, indent=2),
        encoding="utf-8",
    )

    sys.argv = ["merge_commands.py", str(cmd_file), str(config_file)]
    main()

    result = json.loads(config_file.read_text(encoding="utf-8"))
    assert result["command"]["old-cmd"]["template"] == "old"
    assert result["command"]["sd-foo"]["template"] == "do foo"
    assert result["command"]["sd-bar"]["description"] == "Bar command"


def test_main_creates_command_section_when_missing(tmp_path):
    commands = {"sd-foo": {"template": "do foo"}}
    cmd_file = tmp_path / "commands.json"
    cmd_file.write_text(json.dumps(commands), encoding="utf-8")

    config_file = tmp_path / "opencode.jsonc"
    config_file.write_text("{}", encoding="utf-8")

    sys.argv = ["merge_commands.py", str(cmd_file), str(config_file)]
    main()

    result = json.loads(config_file.read_text(encoding="utf-8"))
    assert "command" in result
    assert result["command"]["sd-foo"]["template"] == "do foo"


def test_main_handles_jsonc_comments_and_trailing_commas(tmp_path):
    commands = {"sd-foo": {"template": "do foo"}}
    cmd_file = tmp_path / "commands.json"
    cmd_file.write_text(json.dumps(commands), encoding="utf-8")

    config_file = tmp_path / "opencode.jsonc"
    config_file.write_text(
        '{\n  // comment\n  "command": {\n    "old": {"template": "old"},\n  },\n}',
        encoding="utf-8",
    )

    sys.argv = ["merge_commands.py", str(cmd_file), str(config_file)]
    main()

    result = json.loads(config_file.read_text(encoding="utf-8"))
    assert "old" in result["command"]
    assert "sd-foo" in result["command"]


def test_main_falls_back_to_fresh_config_on_bad_jsonc(tmp_path):
    commands = {"sd-foo": {"template": "do foo"}}
    cmd_file = tmp_path / "commands.json"
    cmd_file.write_text(json.dumps(commands), encoding="utf-8")

    config_file = tmp_path / "opencode.jsonc"
    config_file.write_text('{"$schema": "schema.json", not valid}', encoding="utf-8")

    sys.argv = ["merge_commands.py", str(cmd_file), str(config_file)]
    main()

    result = json.loads(config_file.read_text(encoding="utf-8"))
    assert result.get("$schema") == "schema.json"
    assert result["command"]["sd-foo"]["template"] == "do foo"


def test_main_exits_when_args_missing():
    sys.argv = ["merge_commands.py"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
