"""Tests for render.py semantic → visual mapping rules."""
from render import edge_color, node_style_str, NODE_VISUAL, NODE_FUTURE_OVERRIDE


def test_edge_color_kafka_overrides_pii():
    """kafka_subscribe must be blue dashed regardless of PII."""
    edge = {"rel": "kafka_subscribe", "data": {"has_pii": True, "frequency": "realtime"}}
    color, dashed = edge_color(edge)
    assert color == "#6c8ebf"
    assert dashed is True


def test_edge_color_pii_realtime():
    """PII + realtime → red solid."""
    edge = {"rel": "sftp_export", "data": {"has_pii": True, "frequency": "realtime"}}
    color, dashed = edge_color(edge)
    assert color == "#FF0000"
    assert dashed is False


def test_edge_color_pii_daily():
    """PII + daily → red dashed."""
    edge = {"rel": "sftp_export", "data": {"has_pii": True, "frequency": "daily"}}
    color, dashed = edge_color(edge)
    assert color == "#FF0000"
    assert dashed is True


def test_edge_color_pii_weekly():
    """PII + weekly → red dashed."""
    edge = {"rel": "sftp_export", "data": {"has_pii": True, "frequency": "weekly"}}
    color, dashed = edge_color(edge)
    assert color == "#FF0000"
    assert dashed is True


def test_edge_color_non_pii():
    """Non-PII → green solid."""
    edge = {"rel": "api_call", "data": {"has_pii": False}}
    color, dashed = edge_color(edge)
    assert color == "#82b366"
    assert dashed is False


def test_edge_color_callback():
    """callback → green solid."""
    edge = {"rel": "callback", "data": {"has_pii": False}}
    color, dashed = edge_color(edge)
    assert color == "#82b366"
    assert dashed is False


def test_edge_color_future():
    """future status → grey dashed."""
    edge = {"rel": "sftp_export", "data": {"has_pii": True}, "status": "future"}
    color, dashed = edge_color(edge)
    assert color == "#bdbdbd"
    assert dashed is True


def test_node_style_future_override():
    """Future node should have grey fill and dashed border."""
    style = node_style_str("client_system", is_future=True)
    assert "fillColor=#f5f5f5" in style
    assert "strokeColor=#bdbdbd" in style
    assert "dashed=1" in style


def test_node_style_sd_product():
    """sd_product should be green."""
    style = node_style_str("sd_product", is_future=False)
    assert "fillColor=#d5e8d4" in style
    assert "strokeColor=#82b366" in style


def test_node_style_external_saas():
    """external_saas should be blue."""
    style = node_style_str("external_saas", is_future=False)
    assert "fillColor=#dae8fc" in style
    assert "strokeColor=#6c8ebf" in style
