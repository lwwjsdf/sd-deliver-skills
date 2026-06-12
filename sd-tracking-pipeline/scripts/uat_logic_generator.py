#!/usr/bin/env python3
"""
uat_logic_generator.py — 从 uat-test-case.xlsx 生成 uat_test_logic.yaml

用法：
  python3 uat_logic_generator.py <uat-test-case.xlsx> [--output yaml] [--tracking-plan plan.xlsx]

生成的 YAML 中：
  - confidence: auto_derived — AI 自动推导，待确认
  - confidence: needs_review — 需要人工确认
  - automation: auto — 可自动化
  - automation: manual — 需手动执行
  - confirmed: false — 业务分析师确认前为 false
"""

import argparse
import os
import sys
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from uat_case_parser import parse_xlsx, guess_automation


# 已知的聚合模式映射
AGGREGATION_PATTERNS = {
    "unique visitor": ("count_distinct", "distinct_id"),
    "new user": ("count_distinct", "distinct_id", "WHERE $is_first_day = true"),
    "daily active": ("count_distinct", "distinct_id", "per day"),
    "page view": ("count", "*"),
    "bounce rate": ("ratio", "custom", "needs_review"),
    "average": ("avg", None),
    "conversion rate": ("ratio", "custom", "needs_review"),
    "retention": ("ratio", "custom", "needs_review"),
}


def detect_event_from_definition(definition: str, known_events: list) -> str:
    """从指标定义中检测涉及的事件."""
    for event in known_events:
        if event in definition or event.lower() in definition.lower():
            return event
    # 常见预设事件推断
    if "page" in definition.lower() or "browse" in definition.lower():
        return "$pageview"
    if "visit" in definition.lower() or "uv" in definition.lower():
        return "$pageview"
    if "launch" in definition.lower() or "mini program" in definition.lower():
        return "$MPLaunch"
    return "unknown"


def derive_sql(
    event: str,
    aggregation: str,
    entity: str,
    extra: str = "",
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
) -> str:
    """根据聚合信息生成 SQL."""
    if aggregation == "count_distinct":
        return (
            f"SELECT count(DISTINCT {entity}) AS cnt FROM events "
            f"WHERE event='{event}' AND date BETWEEN '{start_date}' AND '{end_date}'"
            + (f" AND {extra}" if extra else "")
        )
    elif aggregation == "count":
        return (
            f"SELECT count(*) AS cnt FROM events "
            f"WHERE event='{event}' AND date BETWEEN '{start_date}' AND '{end_date}'"
        )
    elif aggregation == "avg":
        return (
            f"SELECT avg({entity}) FROM events "
            f"WHERE event='{event}' AND date BETWEEN '{start_date}' AND '{end_date}'"
        )
    return ""


def derive_aggregation(definition: str, name: str) -> tuple:
    """从指标定义推导聚合方式和置信度."""
    text = f"{name} {definition}".lower()
    for pattern, result in AGGREGATION_PATTERNS.items():
        if pattern in text:
            if len(result) >= 3 and result[2] == "needs_review":
                return (result[0], result[1], "needs_review", "")
            return (result[0], result[1], "auto_derived", "")

    # 启发式推导
    if any(w in text for w in ("count", "number", "total", "cumulative")):
        if "unique" in text or "distinct" in text or "dedup" in text:
            return ("count_distinct", "distinct_id", "auto_derived", "")
        return ("count", "*", "auto_derived", "")
    if any(w in text for w in ("average", "mean", "avg")):
        return ("avg", "amount", "needs_review", "无法确认聚合字段，请手动指定")
    if any(w in text for w in ("rate", "ratio", "percent")):
        return ("ratio", "custom", "needs_review", "比率类型指标需要自定义公式")

    return ("unknown", "", "needs_review", "无法自动推导聚合方式")


def generate_yaml(xlsx_path: str, tracking_plan_path: str = "") -> dict:
    """生成 uat_test_logic.yaml."""
    parsed = parse_xlsx(xlsx_path)

    # 读取 tracking plan 获取已知事件列表（如果有）
    known_events = []
    if tracking_plan_path:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from tracking_plan import TrackingPlan
            tp = TrackingPlan(tracking_plan_path)
            known_events = tp.list_events()
        except Exception:
            pass

    yaml_data = {
        "meta": {
            "project": "",
            "version": datetime.now().strftime("v%Y.%m.%d"),
            "source": parsed["meta"]["source"],
            "confirmed": False,
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
            "notes": "⚠️ 此文件由 AI 自动生成，需业务分析师确认后（confirmed: true）才能用于 sd-validate-data",
        },
        "indicators": [],
        "id_mapping": [],
        "permissions": [],
    }

    case_counter = 0
    for sheet_name, sheet_data in parsed["sheets"].items():
        role = sheet_data["role"]
        for row in sheet_data["rows"]:
            if not row.get("case_no") and not row.get("indicator_name"):
                continue
            case_counter += 1

            if role == "indicators":
                name = row.get("indicator_name", f"Case-{case_counter}")
                definition = row.get("indicator_definition", "")
                related_event = row.get("related_event", "")
                if not related_event:
                    related_event = detect_event_from_definition(definition, known_events)

                agg, entity, confidence, reason = derive_aggregation(definition, name)
                sql = derive_sql(related_event, agg, entity) if confidence == "auto_derived" else ""
                automation = "manual" if confidence == "needs_review" else guess_automation(role, row)

                yaml_data["indicators"].append({
                    "id": row.get("scenario_id", f"UAT-{case_counter:03d}"),
                    "scenario": row.get("scenario_name", sheet_name),
                    "name": name,
                    "definition": definition,
                    "event": related_event,
                    "aggregation": agg,
                    "entity": entity,
                    "sql": sql,
                    "confidence": confidence,
                    "confidence_reason": reason,
                    "automation": automation,
                    "expected": {
                        "min": row.get("threshold_min"),
                        "max": row.get("threshold_max"),
                    },
                })
            elif role == "id_mapping":
                yaml_data["id_mapping"].append({
                    "id": row.get("case_no", f"UAT-ID-{case_counter:03d}"),
                    "scenario": row.get("scenario", sheet_name),
                    "test_approach": row.get("test_approach", ""),
                    "expected_result": row.get("expected_result", ""),
                    "sample_user": row.get("sample_user", ""),
                    "automation": guess_automation(role, row),
                })
            elif role == "permissions":
                yaml_data["permissions"].append({
                    "id": row.get("case_no", f"UAT-PERM-{case_counter:03d}"),
                    "role": row.get("role", ""),
                    "bu": row.get("bu", ""),
                    "data_scope": row.get("data_scope", ""),
                    "automation": "manual",
                    "steps": row.get("steps", row.get("test_approach", "")),
                })

    return yaml_data


def main():
    parser = argparse.ArgumentParser(description="从 UAT Test Case Excel 生成 uat_test_logic.yaml")
    parser.add_argument("xlsx_file", help="uat-test-case.xlsx 路径")
    parser.add_argument("--output", "-o", default="", help="输出 YAML 文件路径")
    parser.add_argument("--tracking-plan", "-t", default="", help="Tracking Plan Excel 路径")
    args = parser.parse_args()

    if not os.path.exists(args.xlsx_file):
        print(f"文件不存在: {args.xlsx_file}")
        sys.exit(1)

    yaml_data = generate_yaml(args.xlsx_file, args.tracking_plan)

    output_path = args.output or args.xlsx_file.replace(".xlsx", "_logic.yaml")
    write_yaml(output_path, yaml_data)

    # 输出摘要
    print(f"\n生成完成: {output_path}")
    print(f"  Indicators: {len(yaml_data['indicators'])}")
    print(f"  ID-Mapping: {len(yaml_data['id_mapping'])}")
    print(f"  Permissions: {len(yaml_data['permissions'])}")
    print(f"  ⚠️ confirmed=false，需业务分析师确认后生效")


def write_yaml(output_path: str, data: dict):
    """写入 YAML 文件（手动格式化，保持可读性）."""
    import json

    def _format_value(v, indent=0):
        """格式化 YAML 值."""
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, dict):
            lines = []
            for kk, vv in v.items():
                if vv is None:
                    continue
                lines.append(f"{'  ' * indent}{kk}: {_format_value(vv, indent+1)}")
            return "\n" + "\n".join(lines) if lines else "{}"
        if isinstance(v, list):
            if not v:
                return "[]"
            lines = []
            for item in v:
                if isinstance(item, dict):
                    lines.append(f"{'  ' * indent}- ")
                    for kk, vv in item.items():
                        if vv is None:
                            continue
                        formatted = _format_value(vv, indent+1)
                        if formatted.startswith("\n"):
                            lines.append(f"  {'  ' * indent}{kk}:{formatted}")
                        else:
                            lines.append(f"    {'  ' * indent}{kk}: {formatted}")
                else:
                    lines.append(f"{'  ' * indent}- {item}")
            return "\n" + "\n".join(lines) if lines else "[]"
        # 字符串：检查是否需要引号
        s = str(v)
        if any(c in s for c in ":#{}[]&*!|>'\"%@`,") or s != s.strip():
            return f'"{s}"'
        return s

    lines = []
    lines.append(f"# UAT Test Logic — 自动生成于 {data['meta']['generated_at']}")
    lines.append(f"# ⚠️ confirmed=false，需业务分析师确认后生效")
    lines.append("")

    # Meta
    lines.append("meta:")
    for k, v in data["meta"].items():
        lines.append(f"  {k}: {_format_value(v, 1)}")

    # Indicators
    lines.append("\nindicators:")
    if not data["indicators"]:
        lines.append("  []")
    for item in data["indicators"]:
        lines.append(f"  - id: \"{item['id']}\"")
        lines.append(f"    scenario: \"{item['scenario']}\"")
        lines.append(f"    name: \"{item['name']}\"")
        lines.append(f"    definition: \"{item['definition']}\"")
        lines.append(f"    event: \"{item['event']}\"")
        lines.append(f"    aggregation: {item['aggregation']}")
        lines.append(f"    entity: \"{item['entity']}\"")
        lines.append(f"    sql: \"{item['sql']}\"")
        lines.append(f"    confidence: {item['confidence']}")
        if item.get("confidence_reason"):
            lines.append(f"    confidence_reason: \"{item['confidence_reason']}\"")
        lines.append(f"    automation: {item['automation']}")
        if item["expected"]["min"] or item["expected"]["max"]:
            lines.append(f"    expected:")
            if item["expected"]["min"]:
                lines.append(f"      min: {item['expected']['min']}")
            if item["expected"]["max"]:
                lines.append(f"      max: {item['expected']['max']}")

    # ID-Mapping
    lines.append("\nid_mapping:")
    if not data["id_mapping"]:
        lines.append("  []")
    for item in data["id_mapping"]:
        lines.append(f"  - id: \"{item['id']}\"")
        lines.append(f"    scenario: \"{item['scenario']}\"")
        lines.append(f"    test_approach: \"{item['test_approach'][:80]}\"")
        lines.append(f"    expected_result: \"{item['expected_result'][:80]}\"")
        lines.append(f"    automation: {item['automation']}")

    # Permissions
    lines.append("\npermissions:")
    if not data["permissions"]:
        lines.append("  []")
    for item in data["permissions"]:
        lines.append(f"  - id: \"{item['id']}\"")
        lines.append(f"    role: \"{item['role']}\"")
        lines.append(f"    automation: {item['automation']}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
