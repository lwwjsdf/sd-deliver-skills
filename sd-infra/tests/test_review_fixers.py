"""Tests for review/fixers.py."""
import pytest
import yaml

from fixers import OverlapFixer, PiiColorFixer
from protocol import Issue, Severity


def test_overlap_fixer_no_view_path():
    fixer = OverlapFixer()
    success, msg = fixer.fix([], {"arch": {}})
    assert not success
    assert "view.yaml" in msg


def test_overlap_fixer_adjusts_y(tmp_path):
    view_path = tmp_path / "view.yaml"
    view = {"nodes": {"node_a": {"x": 0, "y": 0}, "node_b": {"x": 0, "y": 10}}}
    view_path.write_text(yaml.dump(view), encoding="utf-8")

    issue = Issue(
        severity=Severity.FAIL,
        checker="overlap_checker",
        category="visual",
        message="overlap",
        location="node:node_a|node_b",
        auto_fixable=True,
    )
    fixer = OverlapFixer()
    success, msg = fixer.fix([issue], {"arch": {}, "view_path": str(view_path)})
    assert success

    updated = yaml.safe_load(view_path.read_text(encoding="utf-8"))
    assert updated["nodes"]["node_b"]["y"] == 30


def test_pii_color_fixer_sets_deliver_pii(tmp_path):
    arch = {
        "edges": [
            {"from": "cdp", "to": "sendcloud", "rel": "deliver", "data": {"has_pii": False}},
        ],
    }
    arch_path = tmp_path / "arch.yaml"
    arch_path.write_text(yaml.dump(arch), encoding="utf-8")

    issue = Issue(
        severity=Severity.WARN,
        checker="pii_color_checker",
        category="spec_compliance",
        message="deliver 连线未标注 has_pii",
        location="edge:cdp->sendcloud",
        auto_fixable=True,
    )
    fixer = PiiColorFixer()
    context = {"arch": arch, "arch_path": str(arch_path)}
    success, msg = fixer.fix([issue], context)
    assert success
    assert context["arch"]["edges"][0]["data"]["has_pii"] is True

    updated = yaml.safe_load(arch_path.read_text(encoding="utf-8"))
    assert updated["edges"][0]["data"]["has_pii"] is True


def test_pii_color_fixer_sets_callback_pii_false(tmp_path):
    arch = {
        "edges": [
            {"from": "sendcloud", "to": "cdp", "rel": "callback", "data": {"has_pii": True}},
        ],
    }
    arch_path = tmp_path / "arch.yaml"
    arch_path.write_text(yaml.dump(arch), encoding="utf-8")

    issue = Issue(
        severity=Severity.WARN,
        checker="pii_color_checker",
        category="spec_compliance",
        message="callback 连线标注了 has_pii=true",
        location="edge:sendcloud->cdp",
        auto_fixable=True,
    )
    fixer = PiiColorFixer()
    context = {"arch": arch, "arch_path": str(arch_path)}
    success, msg = fixer.fix([issue], context)
    assert success
    assert context["arch"]["edges"][0]["data"]["has_pii"] is False
