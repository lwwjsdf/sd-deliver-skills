"""Tests for builder/diagram_builder.py."""
import re
import xml.etree.ElementTree as ET

import pytest

from diagram_builder import (
    build_diagram,
    edge_style,
    gen_id,
    node_style,
    xml_edge,
    xml_node,
)


def test_gen_id_format():
    nid = gen_id("node")
    assert nid.startswith("node_")
    assert len(nid) == len("node_") + 8


def test_node_style_contains_color():
    style = node_style("sd_product")
    assert "fillColor=#d5e8d4" in style
    assert "strokeColor=#82b366" in style
    assert "dashed=0" in style


def test_node_style_future_dashed():
    style = node_style("future")
    assert "dashed=1" in style


def test_edge_style_contains_color():
    style = edge_style("pii_realtime")
    assert "strokeColor=#FF0000" in style
    assert "dashed=0" in style


def test_xml_node_escapes_value():
    xml = xml_node("c1", "A & B < C", "style", 10, 20, 100, 50)
    assert "A &amp; B &lt; C" in xml
    assert 'id="c1"' in xml
    assert 'x="10"' in xml


def test_xml_edge_escapes_newline():
    xml = xml_edge("e1", "s", "t", "style", "line1\nline2")
    assert "e1" in xml
    assert "line1&#xa;line2" in xml


def test_build_diagram(tmp_path):
    arch = {
        "title": "Test Diagram",
        "layout": "lr",
        "columns": [
            {
                "id": "col1",
                "label": "Sources",
                "nodes": [{"id": "crm"}, {"id": "website"}],
            },
            {
                "id": "col2",
                "nodes": [{"id": "cdp"}],
            },
        ],
        "edges": [
            {"from": "crm", "to": "cdp", "style": "internal_flow", "label": "data"},
        ],
    }
    out = tmp_path / "test.drawio"
    build_diagram(arch, str(out))

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Test Diagram" in content
    assert "crm" in content
    assert "cdp" in content
    assert "data" in content

    # Should be valid XML
    root = ET.fromstring(content)
    assert root.tag == "mxfile"


def test_build_diagram_with_custom_node(tmp_path):
    arch = {
        "title": "Custom",
        "columns": [
            {
                "nodes": [
                    {
                        "id": "custom1",
                        "label": "My Node",
                        "custom": {"color": "external_saas", "w": 200, "h": 60},
                    }
                ]
            }
        ],
        "edges": [],
    }
    out = tmp_path / "custom.drawio"
    build_diagram(arch, str(out))
    content = out.read_text(encoding="utf-8")
    assert "My Node" in content
    assert "200" in content
