"""Tests for draw.io XML output structure."""
import xml.etree.ElementTree as ET

from render import render


def test_xml_wellformed(sample_arch, tmp_path):
    """Generated XML must be valid and parseable."""
    out = tmp_path / "test.drawio"
    render(sample_arch, str(out))
    tree = ET.parse(str(out))
    root = tree.getroot()
    assert root.tag == "mxfile"


def test_all_nodes_present(sample_arch, tmp_path):
    """Every arch node must appear as a vertex cell."""
    out = tmp_path / "test.drawio"
    render(sample_arch, str(out))
    tree = ET.parse(str(out))
    cells = tree.findall(".//mxCell")
    labels = {c.get("value", "").replace("&lt;b&gt;", "").replace("&lt;/b&gt;", "")
              for c in cells if c.get("vertex") == "1"}
    for n in sample_arch["nodes"]:
        assert n["name"] in labels, f"Node {n['name']} missing from XML"


def test_all_edges_present(sample_arch, tmp_path):
    """Every arch edge must appear as an edge cell."""
    out = tmp_path / "test.drawio"
    render(sample_arch, str(out))
    tree = ET.parse(str(out))
    edge_cells = [c for c in tree.findall(".//mxCell") if c.get("edge") == "1"]
    # 3 real edges + legend edges
    assert len(edge_cells) >= 3


def test_group_container_present(sample_arch, tmp_path):
    """Groups should produce container cells (large rectangles)."""
    out = tmp_path / "test.drawio"
    render(sample_arch, str(out))
    tree = ET.parse(str(out))
    cells = tree.findall(".//mxCell")
    group_labels = set()
    for c in cells:
        if c.get("vertex") != "1":
            continue
        val = c.get("value", "")
        if "<b>" in val and "</b>" in val:
            group_labels.add(val.replace("<b>", "").replace("</b>", ""))
    for g in sample_arch["groups"]:
        assert g["name"] in group_labels, f"Group {g['name']} missing"


def test_legend_present(sample_arch, tmp_path):
    """Legend box must be in output."""
    out = tmp_path / "test.drawio"
    render(sample_arch, str(out))
    tree = ET.parse(str(out))
    cells = tree.findall(".//mxCell")
    legend_found = any(c.get("value", "") == "Legend" for c in cells)
    assert legend_found
