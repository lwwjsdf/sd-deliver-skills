"""Tests for docx_to_yaml_skeleton.py."""
import sys
from pathlib import Path

import pytest
import yaml

from docx_to_yaml_skeleton import build_template_data, try_parse_docx, main


def test_build_template_data_has_required_sections():
    data = build_template_data("demo")
    assert data["meta"]["project"] == "demo"
    assert "region_distribution" in data
    assert "user_segments" in data
    assert "identity_priority" in data
    assert "event_sequences" in data
    assert "constraints" in data
    assert "enums" in data
    assert "failure_rate" in data
    assert "fixed_accounts" in data


def test_build_template_data_segment_ratios_sum_to_one():
    data = build_template_data("demo")
    total = sum(s["ratio"] for s in data["user_segments"].values())
    assert abs(total - 1.0) < 0.001


def test_build_template_data_region_distribution_sum_to_one():
    data = build_template_data("demo")
    total = sum(data["region_distribution"].values())
    assert abs(total - 1.0) < 0.001


def test_try_parse_docx_nonexistent_returns_none():
    tables, paragraphs = try_parse_docx("/nonexistent/file.docx")
    assert tables is None
    assert paragraphs is None


def test_main_generates_yaml(tmp_path, capsys):
    output = tmp_path / "business_logic.yaml"
    sys.argv = ["docx_to_yaml_skeleton.py", "--output", str(output), "--project", "demo"]
    main()
    assert output.exists()
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert data["meta"]["project"] == "demo"
    captured = capsys.readouterr()
    assert "已生成" in captured.out


def test_main_uses_input_filename_in_comment(tmp_path, capsys):
    input_file = tmp_path / "input.docx"
    input_file.write_text("not a real docx", encoding="utf-8")
    output = tmp_path / "business_logic.yaml"
    sys.argv = [
        "docx_to_yaml_skeleton.py",
        "--input", str(input_file),
        "--output", str(output),
        "--project", "demo",
    ]
    main()
    text = output.read_text(encoding="utf-8")
    assert "input.docx" in text


def test_main_missing_output_argument():
    sys.argv = ["docx_to_yaml_skeleton.py"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
