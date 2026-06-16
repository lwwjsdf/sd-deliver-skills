"""Tests for builder/extract.py."""
import xml.etree.ElementTree as ET

import pytest

from extract import (
    clean_html,
    extract_style,
    infer_edge,
    infer_type,
    normalize_id,
)


def test_clean_html_removes_tags():
    assert clean_html("<b>Hello</b>") == "Hello"


def test_clean_html_decodes_entities():
    assert clean_html("A &amp; B") == "A & B"
    assert clean_html("A &lt; B") == "A < B"
    assert clean_html("A &gt; B") == "A > B"


def test_extract_style():
    style = "fillColor=#d5e8d4;strokeColor=#82b366;dashed=1"
    props = extract_style(style)
    assert props["fillColor"] == "#d5e8d4"
    assert props["strokeColor"] == "#82b366"
    assert props["dashed"] == "1"


def test_infer_type_from_label():
    assert infer_type("", "CDP Platform", False)[0] == "sd_product"
    assert infer_type("", "MAE", False)[0] == "sd_product"
    assert infer_type("", "End User", False)[0] == "person"


def test_infer_type_from_fill():
    assert infer_type("#d5e8d4", "", False)[0] == "sd_product"
    assert infer_type("#dae8fc", "", False)[0] == "external_saas"


def test_infer_type_future_gray():
    ntype, conf = infer_type("#f5f5f5", "", True)
    assert ntype == "client_system"


def test_infer_edge_by_label():
    result = infer_edge("SFTP Batch daily", "client_system", "sd_product")
    assert result["rel"] == "sftp_export"
    assert result["frequency"] == "daily"


def test_infer_edge_by_node_types():
    result = infer_edge("", "client_system", "sd_product")
    assert result["rel"] == "sdk_track"


def test_normalize_id():
    used = set()
    assert normalize_id("CRM System", used) == "crm"
    used.add("crm")
    assert normalize_id("CRM System", used) == "crm_1"


def test_normalize_id_long_label():
    used = set()
    nid = normalize_id("A" * 50, used)
    assert len(nid) <= 30


def test_extract_end_to_end(tmp_path):
    """Build a minimal drawio file and extract arch.yaml from it."""
    from extract import extract

    xml = '''<mxfile>
  <diagram name="Test">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="n1" value="CRM" style="fillColor=#e1d5e7;" vertex="1" parent="1">
          <mxGeometry x="10" y="10" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="n2" value="CDP" style="fillColor=#d5e8d4;" vertex="1" parent="1">
          <mxGeometry x="200" y="10" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="e1" value="SDK data" style="strokeColor=#FF0000;" edge="1" source="n1" target="n2" parent="1">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    drawio = tmp_path / "test.drawio"
    drawio.write_text(xml, encoding="utf-8")

    arch_out = tmp_path / "arch.yaml"
    view_out = tmp_path / "view.yaml"
    extract(str(drawio), str(arch_out), str(view_out))

    assert arch_out.exists()
    content = arch_out.read_text(encoding="utf-8")
    assert "crm" in content
    assert "cdp" in content
    assert "sdk_track" in content or "sdk" in content.lower()

    assert view_out.exists()
    view_content = view_out.read_text(encoding="utf-8")
    assert "crm" in view_content
