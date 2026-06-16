"""Tests for templates/gen_diagrams.py."""
import json

import pytest

from gen_diagrams import apply_config, generate, output_name


def test_output_name_replaces_template_suffix():
    assert output_name("Logical_Architecture_TEMPLATE.drawio", "Acme") == "Logical_Architecture_Acme.drawio"


def test_apply_config_replaces_placeholders():
    content = "CLIENT: {{CLIENT}}, SYSTEM: {{SYSTEM_1}}"
    config = {"CLIENT": "Acme", "SYSTEM_1": "CRM"}
    assert apply_config(content, config) == "CLIENT: Acme, SYSTEM: CRM"


def test_generate_from_real_templates(tmp_path):
    config = {
        "CLIENT": "Acme",
        "CLIENT_SYSTEMS": "Acme Systems",
        "BUSINESS_USER": "Acme Employee",
        "EMAIL_SERVICE": "SendCloud",
        "FRONTEND_1": "Mini-Program",
        "FRONTEND_2": "Website",
        "FRONTEND_3": "Mobile App",
        "FRONTEND_4": "Other Channels",
        "SOCIAL_MEDIA": "Social Media",
        "SYSTEM_1": "CRM System",
        "SYSTEM_2": "Business Data",
        "SYSTEM_3": "CRM",
        "SYSTEM_4": "RSVP",
        "SYSTEM_5": "Retail System",
        "SYSTEM_6": "POS",
        "SYSTEM_7": "Other System 1",
        "SYSTEM_8": "Other System 2",
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    out_dir = tmp_path / "out"
    generate(str(config_path), str(out_dir))

    files = list(out_dir.iterdir())
    assert len(files) > 0
    for f in files:
        assert "Acme" in f.name
        content = f.read_text(encoding="utf-8")
        assert "{{CLIENT}}" not in content


def test_generate_warns_unreplaced_placeholders(tmp_path, capsys):
    config = {"CLIENT": "Acme"}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    out_dir = tmp_path / "out"
    generate(str(config_path), str(out_dir))
    captured = capsys.readouterr()
    assert "未替换的占位符" in captured.out
