"""Edge-case tests for draw-diagram rendering."""
from render import render


def test_empty_arch(tmp_path):
    """Empty arch should still produce valid XML."""
    arch = {"meta": {"title": "Empty"}, "nodes": [], "groups": [], "edges": []}
    out = tmp_path / "empty.drawio"
    render(arch, str(out))
    assert out.exists()
    content = out.read_text()
    assert "mxfile" in content


def test_single_node_no_edges(tmp_path):
    """Single node with no edges should render without error."""
    arch = {
        "meta": {"title": "Single"},
        "nodes": [{"id": "only", "name": "Only", "type": "sd_product"}],
        "groups": [],
        "edges": [],
    }
    out = tmp_path / "single.drawio"
    render(arch, str(out))
    assert out.exists()
    content = out.read_text()
    assert "Only" in content


def test_future_node_grey_dashed(tmp_path):
    """Future node must have grey dashed styling in XML."""
    arch = {
        "meta": {"title": "Future"},
        "nodes": [
            {"id": "curr", "name": "Current", "type": "sd_product", "status": "current"},
            {"id": "fut", "name": "Future", "type": "sd_product", "status": "future"},
        ],
        "groups": [],
        "edges": [],
    }
    out = tmp_path / "future.drawio"
    render(arch, str(out))
    content = out.read_text()
    # Future node should have dashed=1 and grey colors
    assert "dashed=1" in content
    assert "#f5f5f5" in content
    assert "#bdbdbd" in content


def test_backward_edge_waypoints(tmp_path):
    """Backward edge (right-to-left) should produce waypoints."""
    arch = {
        "meta": {"title": "Back"},
        "nodes": [
            {"id": "left", "name": "Left", "type": "sd_product"},
            {"id": "right", "name": "Right", "type": "client_system"},
        ],
        "groups": [],
        "edges": [
            {"from": "right", "to": "left", "rel": "callback", "data": {"has_pii": False}},
        ],
    }
    out = tmp_path / "back.drawio"
    render(arch, str(out))
    content = out.read_text()
    # Waypoints are represented as mxPoint elements inside Array
    assert "mxPoint" in content


def test_group_row_span_threshold(tmp_path):
    """Group with row span <= MAX_GROUP_ROW_SPAN should have container."""
    arch = {
        "meta": {"title": "Span"},
        "nodes": [
            {"id": "n1", "name": "N1", "type": "sd_product", "group": "g1", "row": 1},
            {"id": "n2", "name": "N2", "type": "sd_product", "group": "g1", "row": 2},
            {"id": "n3", "name": "N3", "type": "sd_product", "group": "g1", "row": 3},
        ],
        "groups": [
            {"id": "g1", "name": "G1", "type": "data_sources", "contains": ["n1", "n2", "n3"]},
        ],
        "edges": [],
    }
    out = tmp_path / "span.drawio"
    render(arch, str(out))
    content = out.read_text()
    # Container should exist (group name in bold)
    assert "&lt;b&gt;G1&lt;/b&gt;" in content
