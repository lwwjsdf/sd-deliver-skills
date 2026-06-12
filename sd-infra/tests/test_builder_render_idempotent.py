"""Tests for view.yaml auto-export and idempotent restore."""
import xml.etree.ElementTree as ET

import yaml

from render import render


def _extract_positions(drawio_path: str) -> dict:
    """Parse drawio XML and return {label: (x, y)}."""
    tree = ET.parse(drawio_path)
    cells = tree.findall(".//mxCell")
    pos = {}
    for c in cells:
        if c.get("vertex") != "1":
            continue
        val = c.get("value", "").replace("&lt;b&gt;", "").replace("&lt;/b&gt;", "")
        if not val or val == "Legend":
            continue
        geom = c.find("mxGeometry")
        if geom is None:
            continue
        pos[val] = (float(geom.get("x", 0)), float(geom.get("y", 0)))
    return pos


def test_view_yaml_auto_export(sample_arch, tmp_path):
    """Auto-layout should produce a .view.yaml next to the drawio."""
    out = tmp_path / "test.drawio"
    render(sample_arch, str(out))
    view_path = tmp_path / "test.view.yaml"
    assert view_path.exists(), "view.yaml was not auto-generated"
    with open(view_path) as f:
        view = yaml.safe_load(f)
    assert "nodes" in view
    assert "groups" in view
    assert "canvas" in view
    for n in sample_arch["nodes"]:
        assert n["id"] in view["nodes"], f"Node {n['id']} missing from view.yaml"


def test_idempotent_restore(sample_arch, tmp_path):
    """Rendering with auto-generated view.yaml must produce identical coordinates."""
    out1 = tmp_path / "first.drawio"
    render(sample_arch, str(out1))

    view_path = tmp_path / "first.view.yaml"
    assert view_path.exists()
    with open(view_path) as f:
        view = yaml.safe_load(f)

    out2 = tmp_path / "second.drawio"
    render(sample_arch, str(out2), view=view)

    pos1 = _extract_positions(str(out1))
    pos2 = _extract_positions(str(out2))

    assert set(pos1.keys()) == set(pos2.keys())
    for label in pos1:
        x1, y1 = pos1[label]
        x2, y2 = pos2[label]
        assert abs(x1 - x2) < 0.5, f"{label} x diff: {x1} vs {x2}"
        assert abs(y1 - y2) < 0.5, f"{label} y diff: {y1} vs {y2}"


def test_view_yaml_not_overwritten_when_provided(sample_arch, tmp_path):
    """When --view is provided, render should NOT overwrite the view.yaml."""
    out = tmp_path / "test.drawio"
    render(sample_arch, str(out))
    view_path = tmp_path / "test.view.yaml"
    assert view_path.exists()

    # Load the generated view
    with open(view_path) as f:
        view = yaml.safe_load(f)

    # Modify view slightly
    view["nodes"]["crm"]["x"] = 999.0

    # Render again with the modified view
    out2 = tmp_path / "test2.drawio"
    render(sample_arch, str(out2), view=view)

    # The original view.yaml should NOT be overwritten
    with open(view_path) as f:
        original = yaml.safe_load(f)
    assert original["nodes"]["crm"]["x"] != 999.0, "view.yaml was incorrectly overwritten"
