"""Tests for report.py."""
from report import _severity_icon, _status_badge, generate_markdown


def test_severity_icon():
    assert _severity_icon("error") == "❌"
    assert _severity_icon("warning") == "⚠️"
    assert _severity_icon("info") == "⚠️"


def test_status_badge():
    assert "通过" in _status_badge("pass")
    assert "异常" in _status_badge("anomaly")
    assert "缺失" in _status_badge("missing")
    assert _status_badge("unknown") == "unknown"


def test_generate_markdown_includes_summary():
    diff_data = {
        "summary": {
            "events": {"total": 3, "pass": 2, "anomaly": 1, "missing": 0},
            "user_attributes": {"total": 1, "pass": 0, "anomaly": 0, "missing": 1},
        },
        "events": [],
        "user_attributes": [],
    }
    md = generate_markdown(diff_data)
    assert "埋点数据校验报告" in md
    assert "通过：2 个" in md
    assert "异常：1 个" in md
    assert "缺失：1 个" in md


def test_generate_markdown_shows_anomaly_events():
    diff_data = {
        "summary": {"events": {"total": 1, "pass": 0, "anomaly": 1, "missing": 0},
                    "user_attributes": {"total": 0, "pass": 0, "anomaly": 0, "missing": 0}},
        "events": [
            {
                "event_name": "OrderPaid",
                "status": "anomaly",
                "imported_count": 5,
                "issues": [
                    {"category": "missing_property", "field": "amount", "expected": "number",
                     "actual": "missing", "severity": "error", "suggestion": "check SDK"},
                ],
            }
        ],
        "user_attributes": [],
    }
    md = generate_markdown(diff_data)
    assert "OrderPaid" in md
    assert "missing_property" in md
    assert "amount" in md
    assert "check SDK" in md


def test_generate_markdown_shows_pass_list():
    diff_data = {
        "summary": {"events": {"total": 1, "pass": 1, "anomaly": 0, "missing": 0},
                    "user_attributes": {"total": 1, "pass": 1, "anomaly": 0, "missing": 0}},
        "events": [{"event_name": "Login", "status": "pass", "imported_count": 10, "issues": []}],
        "user_attributes": [{"attr_name": "user_type", "status": "pass", "imported_count": 10, "issues": []}],
    }
    md = generate_markdown(diff_data)
    assert "通过项清单" in md
    assert "`Login`" in md
    assert "`user_type`" in md


def test_generate_markdown_handles_empty_data():
    md = generate_markdown({})
    assert "埋点数据校验报告" in md
    assert "总计：0 个" in md
