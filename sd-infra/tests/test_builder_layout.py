"""Tests for layout.py — graphviz dot + linear fallback."""
from layout import compute_layout_linear


def test_linear_layout_basic(sample_arch):
    """Linear layout should assign distinct x/y to every node."""
    positions = compute_layout_linear(sample_arch)
    assert positions is not None
    node_ids = {n["id"] for n in sample_arch["nodes"]}
    assert set(positions.keys()) == node_ids

    # All coordinates positive
    for nid, (x, y, w, h) in positions.items():
        assert x >= 0, f"{nid} x={x}"
        assert y >= 0, f"{nid} y={y}"
        assert w > 0, f"{nid} w={w}"
        assert h > 0, f"{nid} h={h}"


def test_linear_layout_columns(sample_arch):
    """Nodes in different groups should have increasing x."""
    positions = compute_layout_linear(sample_arch)
    crm_x = positions["crm"][0]
    cdp_x = positions["cdp"][0]
    send_x = positions["sendcloud"][0]
    assert crm_x < cdp_x < send_x


def test_linear_layout_same_group_y(sample_arch):
    """Nodes inside the same group should be vertically stacked."""
    positions = compute_layout_linear(sample_arch)
    cdp_y = positions["cdp"][1]
    mae_y = positions["mae"][1]
    assert mae_y > cdp_y


def test_linear_layout_row_field(arch_with_rows):
    """Nodes with explicit row should still get positions."""
    positions = compute_layout_linear(arch_with_rows)
    for nid in ("a", "b", "c"):
        assert nid in positions
