"""Tests for review/checkers.py."""
import xml.etree.ElementTree as ET

import pytest

from checkers import (
    ContainerChecker,
    EdgeLabelChecker,
    NodeTypeChecker,
    OrphanChecker,
    OverlapChecker,
    PiiColorChecker,
)


def _make_drawio(nodes_xml: str, edges_xml: str = "") -> str:
    return f'''<mxfile>
  <diagram name="Test">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        {nodes_xml}
        {edges_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''


def test_overlap_checker_detects_overlap(tmp_path):
    drawio = _make_drawio('''
        <mxCell id="a" value="A" style="fillColor=#dae8fc;" vertex="1" parent="1">          <mxGeometry x="10" y="10" width="100" height="50" as="geometry"/></mxCell>
        <mxCell id="b" value="B" style="fillColor=#dae8fc;" vertex="1" parent="1">          <mxGeometry x="50" y="30" width="100" height="50" as="geometry"/></mxCell>
    ''')
    path = tmp_path / "overlap.drawio"
    path.write_text(drawio, encoding="utf-8")

    checker = OverlapChecker()
    result = checker.check({"drawio_path": str(path), "arch": {}})
    assert not result.passed
    assert result.fail_count == 1


def test_overlap_checker_no_overlap(tmp_path):
    drawio = _make_drawio('''
        <mxCell id="a" value="A" style="fillColor=#dae8fc;" vertex="1" parent="1">          <mxGeometry x="10" y="10" width="100" height="50" as="geometry"/></mxCell>
        <mxCell id="b" value="B" style="fillColor=#dae8fc;" vertex="1" parent="1">          <mxGeometry x="200" y="10" width="100" height="50" as="geometry"/></mxCell>
    ''')
    path = tmp_path / "no_overlap.drawio"
    path.write_text(drawio, encoding="utf-8")

    checker = OverlapChecker()
    result = checker.check({"drawio_path": str(path), "arch": {}})
    assert result.passed


def test_orphan_checker_warns_isolated(tmp_path):
    drawio = _make_drawio('''
        <mxCell id="a" value="A" style="fillColor=#dae8fc;" vertex="1" parent="1">          <mxGeometry x="10" y="10" width="100" height="50" as="geometry"/></mxCell>
        <mxCell id="b" value="B" style="fillColor=#dae8fc;" vertex="1" parent="1">          <mxGeometry x="200" y="10" width="100" height="50" as="geometry"/></mxCell>
        <mxCell id="c" value="C" style="fillColor=#dae8fc;" vertex="1" parent="1">          <mxGeometry x="400" y="10" width="100" height="50" as="geometry"/></mxCell>
    ''', '''
        <mxCell id="e1" value="" style="strokeColor=#82b366;" edge="1" source="a" target="b" parent="1">          <mxGeometry relative="1" as="geometry"/></mxCell>
    ''')
    path = tmp_path / "orphan.drawio"
    path.write_text(drawio, encoding="utf-8")

    checker = OrphanChecker()
    result = checker.check({"drawio_path": str(path), "arch": {"nodes": [], "edges": []}})
    assert result.warn_count >= 1


def _empty_drawio(tmp_path) -> str:
    path = tmp_path / "empty.drawio"
    path.write_text(_make_drawio(''), encoding="utf-8")
    return str(path)


def test_pii_color_checker_warns_deliver_without_pii(tmp_path):
    arch = {
        "nodes": [],
        "edges": [
            {"from": "cdp", "to": "sendcloud", "rel": "deliver", "data": {"has_pii": False}},
        ],
    }
    checker = PiiColorChecker()
    result = checker.check({"drawio_path": _empty_drawio(tmp_path), "arch": arch})
    assert result.warn_count == 1


def test_pii_color_checker_no_issue_when_pii_correct(tmp_path):
    arch = {
        "nodes": [],
        "edges": [
            {"from": "cdp", "to": "sendcloud", "rel": "deliver", "data": {"has_pii": True}},
        ],
    }
    checker = PiiColorChecker()
    result = checker.check({"drawio_path": _empty_drawio(tmp_path), "arch": arch})
    assert result.passed


def test_container_checker_warns_node_outside(tmp_path):
    drawio = _make_drawio('''
        <mxCell id="c" value="Container" style="fillColor=#f8f0ff;" vertex="1" parent="1">          <mxGeometry x="10" y="10" width="200" height="200" as="geometry"/></mxCell>
        <mxCell id="a" value="A" style="fillColor=#d5e8d4;" vertex="1" parent="1">          <mxGeometry x="250" y="10" width="100" height="50" as="geometry"/></mxCell>
    ''')
    path = tmp_path / "container.drawio"
    path.write_text(drawio, encoding="utf-8")

    checker = ContainerChecker()
    result = checker.check({"drawio_path": str(path), "arch": {}})
    # No node is inside container, so no warning
    assert result.passed


def test_container_checker_detects_node_overflow(tmp_path):
    drawio = _make_drawio('''
        <mxCell id="c" value="Container" style="fillColor=#f8f0ff;" vertex="1" parent="1">          <mxGeometry x="10" y="10" width="200" height="200" as="geometry"/></mxCell>
        <mxCell id="a" value="A" style="fillColor=#d5e8d4;" vertex="1" parent="1">          <mxGeometry x="50" y="50" width="180" height="50" as="geometry"/></mxCell>
    ''')
    path = tmp_path / "container_overflow.drawio"
    path.write_text(drawio, encoding="utf-8")

    checker = ContainerChecker()
    result = checker.check({"drawio_path": str(path), "arch": {}})
    assert result.warn_count == 1


def test_edge_label_checker_warns_missing_name():
    arch = {
        "nodes": [],
        "edges": [
            {"from": "crm", "to": "cdp", "rel": "sdk_track"},
        ],
    }
    checker = EdgeLabelChecker()
    result = checker.check({"drawio_path": "", "arch": arch})
    assert result.warn_count == 1
    assert result.passed  # WARN only


def test_node_type_checker_warns_type_mismatch():
    arch = {
        "nodes": [
            {"id": "main_cdp", "name": "CDP", "type": "client_system"},
        ],
    }
    checker = NodeTypeChecker()
    result = checker.check({"drawio_path": "", "arch": arch})
    assert result.warn_count == 1
    assert "建议改为 sd_product" in result.issues[0].message
