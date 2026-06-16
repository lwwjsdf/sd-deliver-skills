"""Tests for builder/components.py."""
import pytest

from components import (
    COLORS,
    EDGE_COLORS,
    STANDARD_COMPONENTS,
    STANDARD_EDGES,
    list_components,
)


def test_standard_components_has_cdp():
    assert "cdp" in STANDARD_COMPONENTS
    cdp = STANDARD_COMPONENTS["cdp"]
    assert cdp["label"] == "CDP"
    assert cdp["type"] == "container"
    assert "w" in cdp and "h" in cdp


def test_colors_keys():
    assert "sd_product" in COLORS
    assert "client_system" in COLORS
    assert "future" in COLORS
    assert COLORS["sd_product"]["fill"] == "#d5e8d4"


def test_edge_colors_keys():
    assert "pii_realtime" in EDGE_COLORS
    assert "internal" in EDGE_COLORS


def test_standard_edges_templates():
    edge = STANDARD_EDGES["sdk_realtime"]
    assert "{data_fields}" in edge["label_template"]
    assert edge["style"] == "pii_realtime"


def test_list_components_output(capsys):
    list_components()
    captured = capsys.readouterr()
    assert "神策标准组件库" in captured.out
    assert "cdp" in captured.out
    assert "mae" in captured.out
