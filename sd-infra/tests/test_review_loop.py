"""Tests for review_loop.py."""
from unittest.mock import MagicMock

import pytest

from review_loop import main


def test_review_loop_passes_after_one_round(tmp_path, monkeypatch):
    arch_path = tmp_path / "arch.yaml"
    arch_path.write_text("""
meta:
  title: Test
nodes: []
edges: []
""", encoding="utf-8")

    out_path = tmp_path / "out.drawio"
    out_path.write_text("<mxfile></mxfile>", encoding="utf-8")

    # Mock render to avoid full builder dependency
    mock_render = MagicMock()
    monkeypatch.setattr("review_loop.render", mock_render)

    # Run with sys.argv
    import sys
    old_argv = sys.argv
    try:
        sys.argv = [
            "review_loop.py",
            "--arch", str(arch_path),
            "--output", str(out_path),
            "--max-rounds", "2",
        ]
        rc = main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    assert mock_render.called
