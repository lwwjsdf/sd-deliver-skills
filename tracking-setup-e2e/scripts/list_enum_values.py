"""
list_enum_values.py — Quality-check and list enum values from the Tracking Plan.

Outputs:
  1. 问题清单 — issues grouped by severity (严重 / 中等 / 轻微)
  2. 关键结论 + 建议行动 (选项 A/B/C)
  3. 完整枚举值清单 — for client confirmation

Usage:
    python3 tracking-setup-e2e/scripts/list_enum_values.py \
        --tracking-plan <xlsx_path>
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from tracking_plan import TrackingPlan, PropertyDef


@dataclass
class EnumIssue:
    severity: str   # 严重 / 中等 / 轻微
    field: str
    context: str    # event name, "公共属性", or "用户属性"
    description: str
    impact: str


_SEVERITY_ORDER = {"严重": 0, "中等": 1, "轻微": 2}

_PLACEHOLDER_RE = re.compile(
    r"^(test\w*|placeholder\w*|example\w*|sample\w*|todo|tbd|xxx+|dummy\w*|foo|bar|n/?a|null|none|undefined)$",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")
_PHONE_RE = re.compile(r"^\+?\d[\d\s\-]{6,}$")
_DATE_RE = re.compile(r"^\d{4}[-/]\d{2}([-/]\d{2})?$")
_PURE_NUM_RE = re.compile(r"^\d{4,}$")
_ID_FIELD_RE = re.compile(r"(number|id|code|no\b)", re.IGNORECASE)


def _is_placeholder(v: str) -> bool:
    return bool(_PLACEHOLDER_RE.match(v.strip()))


def _is_long_description(v: str) -> bool:
    s = v.strip()
    return len(s) > 60 or (len(s) > 30 and s.count(" ") >= 4)


def _is_example_value(v: str) -> bool:
    s = v.strip()
    return bool(
        _EMAIL_RE.match(s) or _PHONE_RE.match(s)
        or _DATE_RE.match(s) or _PURE_NUM_RE.match(s)
    )


def _has_chinese(v: str) -> bool:
    return bool(re.search(r"[一-鿿]", v))


def analyze_property(
    field_name: str, enum_values: List[str], context: str = ""
) -> List[EnumIssue]:
    issues: List[EnumIssue] = []
    vals = [str(v).strip() for v in enum_values if str(v).strip()]
    if not vals:
        return issues

    placeholder_vals = [v for v in vals if _is_placeholder(v)]
    long_vals = [v for v in vals if _is_long_description(v)]

    if placeholder_vals:
        if len(placeholder_vals) == len(vals):
            issues.append(EnumIssue("严重", field_name, context,
                f"{vals} — 纯占位符", "造数时该字段将生成无意义的测试值"))
        else:
            issues.append(EnumIssue("中等", field_name, context,
                f"包含占位符值: {placeholder_vals}", "部分枚举值无意义"))

    if long_vals:
        issues.append(EnumIssue("严重", field_name, context,
            "枚举值是整段说明文字，不是枚举项",
            "无法作为枚举使用，造数脚本可能取到整段描述"))

    if _ID_FIELD_RE.search(field_name):
        chinese_vals = [v for v in vals if _has_chinese(v)]
        if len(chinese_vals) >= max(1, len(vals) * 0.6):
            issues.append(EnumIssue("严重", field_name, context,
                f"值是 {vals} — 字段名暗示应为 ID/编号格式，但值为中文名称",
                "字段语义与值域不符，可能填错了其他字段的值"))

    if not placeholder_vals and not long_vals:
        example_vals = [v for v in vals if _is_example_value(v)]
        if len(example_vals) >= max(1, len(vals) * 0.6):
            issues.append(EnumIssue("中等", field_name, context,
                f"{vals} — 示例值而非枚举项",
                "该字段可能不是真正的枚举约束，造数多样性不足"))

    if not issues:
        if len(vals) == 1:
            issues.append(EnumIssue("中等", field_name, context,
                f"只有 {vals} 一项", "枚举多样性不足"))
        elif len(vals) == 2:
            issues.append(EnumIssue("轻微", field_name, context,
                f"只有 {len(vals)} 个枚举值", "多样性较低"))

    return issues


def check_cross_event_consistency(
    event_sections: Dict[str, List[Tuple]]
) -> List[EnumIssue]:
    """Flag fields that appear in multiple events with different value sets."""
    field_map: Dict[str, Dict[str, frozenset]] = {}
    for event_name, rows in event_sections.items():
        for prop_name, _, enum_values, _ in rows:
            field_map.setdefault(prop_name, {})[event_name] = frozenset(str(v) for v in enum_values)

    issues = []
    for field_name, event_vals in field_map.items():
        if len(event_vals) < 2:
            continue
        if len(set(event_vals.values())) > 1:
            events_str = " / ".join(sorted(event_vals.keys()))
            issues.append(EnumIssue("轻微", field_name, events_str,
                "同一字段在不同事件中值域不一致",
                "跨事件分析时可能出现值不匹配"))
    return issues


def _dedup_issues(issues: List[EnumIssue]) -> List[EnumIssue]:
    """Merge duplicate (field, description) rows that differ only in context."""
    seen: Dict[tuple, EnumIssue] = {}
    for issue in issues:
        key = (issue.field, issue.description)
        if key in seen:
            existing = seen[key]
            if existing.context != issue.context:
                seen[key] = EnumIssue(
                    issue.severity, issue.field,
                    f"{existing.context} 等多个来源",
                    issue.description, issue.impact,
                )
        else:
            seen[key] = issue
    return list(seen.values())


def _print_issues_table(issues: List[EnumIssue]) -> None:
    if not issues:
        print("✅ 未发现枚举质量问题。\n")
        return
    print("| 问题等级 | 字段 | 来源 | 问题描述 | 影响 |")
    print("|----------|------|------|----------|------|")
    for i in sorted(issues, key=lambda x: _SEVERITY_ORDER[x.severity]):
        print(f"| {i.severity} | `{i.field}` | {i.context} | {i.description} | {i.impact} |")
    print()


def _print_conclusions(issues: List[EnumIssue]) -> None:
    critical = [i for i in issues if i.severity == "严重"]
    medium = [i for i in issues if i.severity == "中等"]
    minor = [i for i in issues if i.severity == "轻微"]

    print("**关键结论：**\n")
    shown = critical + medium if (critical or medium) else minor
    for idx, issue in enumerate(shown, 1):
        print(f"{idx}. `{issue.field}` — {issue.description}")
    print()

    print("**建议行动：**\n")
    if critical:
        print("- **选项 A（推荐）**：修复 Tracking Plan Excel 中上述严重问题字段的枚举值，重新运行本脚本验证后再造数")
        print("- **选项 B**：在 `business_logic.yaml` 的 `fields` 中显式覆盖这些字段的值，绕过 Tracking Plan 的坏数据")
        print("- **选项 C**：直接造数，接受部分字段值为占位符/无意义值（UAT 功能验证通常够用，但数据质量演示不适用）")
    elif medium:
        print("- **选项 A（推荐）**：补充 Tracking Plan 中枚举值较少的字段，提升造数多样性")
        print("- **选项 B**：在 `business_logic.yaml` 的 `fields` 中为关键字段指定更丰富的值")
        print("- **选项 C**：直接造数，接受当前枚举多样性")
    else:
        print("- 问题均为轻微级别，可直接造数，或按需在 `business_logic.yaml` 中微调。")
    print()


def _print_enum_listing(
    pub_rows: List[Tuple],
    event_sections: Dict[str, List[Tuple]],
    user_rows: List[Tuple],
) -> None:
    print("---\n")
    print("## 完整枚举值清单（供客户确认）\n")
    print("> ✅ 确认正确 / ❌ 有误请告知修改 / ➕ 需新增值 / 🎯 需指定权重\n")

    def _table(rows: List[Tuple]) -> None:
        print("| 属性名 | 类型 | 枚举值 | 备注 |")
        print("|--------|------|--------|------|")
        for prop_name, value_type, enum_values, description in rows:
            enum_str = " / ".join(f"`{v}`" for v in enum_values)
            desc = description.replace("\n", " ")
            if len(desc) > 50:
                desc = desc[:50] + "…"
            print(f"| `{prop_name}` | {value_type} | {enum_str} | {desc} |")
        print()

    if pub_rows:
        print("### 公共属性（所有事件共享）\n")
        _table(pub_rows)
    if event_sections:
        print("### 事件专属属性\n")
        for event_name in sorted(event_sections):
            print(f"#### `{event_name}`\n")
            _table(event_sections[event_name])
    if user_rows:
        print("### 用户属性\n")
        _table(user_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quality-check and list enum values from Tracking Plan"
    )
    parser.add_argument("--tracking-plan", required=True, help="Path to Tracking Plan Excel (.xlsx)")
    args = parser.parse_args()

    plan = TrackingPlan(args.tracking_plan)
    pub_names: set = set()
    all_issues: List[EnumIssue] = []

    pub_rows: List[Tuple] = []
    for prop in plan.get_public_properties():
        pub_names.add(prop.name)
        if prop.enum_values:
            pub_rows.append((prop.name, prop.value_type, prop.enum_values, prop.description))
            all_issues.extend(analyze_property(prop.name, prop.enum_values, "公共属性"))

    event_sections: Dict[str, List[Tuple]] = {}
    for event_name in plan.list_events():
        schema = plan.get_event_schema(event_name)
        if schema is None:
            continue
        for prop in schema.properties:
            if prop.enum_values and prop.name not in pub_names:
                event_sections.setdefault(event_name, []).append(
                    (prop.name, prop.value_type, prop.enum_values, prop.description)
                )
                all_issues.extend(analyze_property(prop.name, prop.enum_values, event_name))

    all_issues.extend(check_cross_event_consistency(event_sections))

    user_rows: List[Tuple] = []
    for prop in plan.get_user_attributes():
        if prop.enum_values:
            user_rows.append((prop.name, prop.value_type, prop.enum_values, prop.description))
            all_issues.extend(analyze_property(prop.name, prop.enum_values, "用户属性"))

    all_issues = _dedup_issues(all_issues)
    critical_count = sum(1 for i in all_issues if i.severity == "严重")
    total_fields = len(pub_rows) + sum(len(v) for v in event_sections.values()) + len(user_rows)

    print("# 枚举值检查结果\n")
    if all_issues:
        print("## 问题清单\n")
        _print_issues_table(all_issues)
        _print_conclusions(all_issues)
    else:
        print("✅ 所有枚举值质量检查通过，未发现问题。\n")

    _print_enum_listing(pub_rows, event_sections, user_rows)
    print(f"共 **{total_fields}** 个枚举属性，发现 **{len(all_issues)}** 个问题（严重 {critical_count} 个）。")


if __name__ == "__main__":
    main()
