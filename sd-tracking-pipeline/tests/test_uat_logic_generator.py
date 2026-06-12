"""Tests for uat_logic_generator.py."""
import sys
from pathlib import Path

import pytest

try:
    import openpyxl
except ImportError:
    openpyxl = None

from uat_logic_generator import (
    detect_event_from_definition,
    derive_aggregation,
    derive_sql,
    generate_yaml,
    main,
    write_yaml,
)


pytestmark = pytest.mark.skipif(openpyxl is None, reason="openpyxl not installed")


def _make_xlsx(tmp_path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name, rows in sheets.items():
        ws = wb.create_sheet(title=sheet_name)
        for row in rows:
            ws.append(row)
    path = tmp_path / "uat.xlsx"
    wb.save(path)
    return str(path)


def test_detect_event_from_definition_known_events():
    known = ["OrderPaid", "ProductViewed"]
    assert detect_event_from_definition("Count OrderPaid", known) == "OrderPaid"
    assert detect_event_from_definition("ProductViewed rate", known) == "ProductViewed"


def test_detect_event_from_definition_heuristics():
    assert detect_event_from_definition("page views", []) == "$pageview"
    assert detect_event_from_definition("daily UV", []) == "$pageview"
    assert detect_event_from_definition("mini program launch", []) == "$MPLaunch"
    assert detect_event_from_definition("unknown metric", []) == "unknown"


def test_derive_sql_count_distinct():
    sql = derive_sql("OrderPaid", "count_distinct", "distinct_id")
    assert "count(DISTINCT distinct_id)" in sql
    assert "event='OrderPaid'" in sql


def test_derive_sql_count():
    sql = derive_sql("OrderPaid", "count", "*")
    assert "count(*)" in sql
    assert "event='OrderPaid'" in sql


def test_derive_sql_avg():
    sql = derive_sql("OrderPaid", "avg", "amount")
    assert "avg(amount)" in sql


def test_derive_aggregation_patterns():
    assert derive_aggregation("unique visitors", "UV")[0] == "count_distinct"
    assert derive_aggregation("page views", "PV")[0] == "count"
    assert derive_aggregation("average order value", "AOV")[0] == "avg"
    assert derive_aggregation("bounce rate", "Bounce") == ("ratio", "custom", "needs_review", "")


def test_derive_aggregation_heuristics():
    assert derive_aggregation("total orders", "Orders")[0] == "count"
    assert derive_aggregation("unique visitor", "UV")[0] == "count_distinct"
    assert derive_aggregation("conversion rate", "CR") == ("ratio", "custom", "needs_review", "")
    assert derive_aggregation("some weird ratio", "Weird") == ("ratio", "custom", "needs_review", "比率类型指标需要自定义公式")
    assert derive_aggregation("some weird thing", "Weird")[2] == "needs_review"


def test_generate_yaml_indicators(tmp_path):
    path = _make_xlsx(
        tmp_path,
        {
            "Indicators": [
                ["case_no", "scenario_id", "scenario_name", "indicator_name", "indicator_definition", "related_event", "threshold_min", "threshold_max"],
                ["1", "S1", "Purchase", "Order Count", "count OrderPaid", "OrderPaid", "10", "100"],
                ["2", "S2", "Visit", "UV", "unique visitor", "", "", ""],
            ],
        },
    )
    result = generate_yaml(path)
    assert len(result["indicators"]) == 2
    assert result["indicators"][0]["aggregation"] == "count"
    assert result["indicators"][0]["event"] == "OrderPaid"
    assert result["indicators"][1]["aggregation"] == "count_distinct"
    assert result["meta"]["confirmed"] is False


def test_generate_yaml_id_mapping_and_permissions(tmp_path):
    path = _make_xlsx(
        tmp_path,
        {
            "ID Mapping": [
                ["case_no", "scenario", "test_approach", "expected_result", "sample_user"],
                ["ID-1", "Login", "check identity", "mapped", "user1"],
            ],
            "Permissions": [
                ["case_no", "role", "bu", "data_scope", "test_approach"],
                ["P-1", "admin", "BU1", "all", "login and check"],
            ],
        },
    )
    result = generate_yaml(path)
    assert len(result["id_mapping"]) == 1
    assert result["id_mapping"][0]["automation"] == "auto"
    assert len(result["permissions"]) == 1
    assert result["permissions"][0]["automation"] == "manual"


def test_write_yaml_creates_file(tmp_path):
    data = {
        "meta": {"project": "demo", "version": "v1", "source": "uat.xlsx", "confirmed": False, "generated_at": "2024-01-01", "notes": "test"},
        "indicators": [],
        "id_mapping": [],
        "permissions": [],
    }
    out = tmp_path / "out.yaml"
    write_yaml(str(out), data)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "confirmed: false" in text
    assert "indicators:" in text


def test_main_exits_on_missing_file(capsys):
    sys.argv = ["uat_logic_generator.py", "/nonexistent.xlsx"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    assert "文件不存在" in capsys.readouterr().out


def test_main_writes_default_output(tmp_path, capsys):
    path = _make_xlsx(
        tmp_path,
        {
            "Indicators": [
                ["case_no", "scenario_id", "scenario_name", "indicator_name", "indicator_definition"],
                ["1", "S1", "Purchase", "Count", "count"],
            ],
        },
    )
    sys.argv = ["uat_logic_generator.py", path]
    main()
    expected_output = path.replace(".xlsx", "_logic.yaml")
    assert Path(expected_output).exists()
    captured = capsys.readouterr()
    assert "生成完成" in captured.out
    assert "Indicators: 1" in captured.out
