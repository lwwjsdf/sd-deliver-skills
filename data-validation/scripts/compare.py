#!/usr/bin/env python3
"""
compare.py — Phase 3: 将埋点方案与实际数据逐项比对

用法:
    python3 data-validation/scripts/compare.py \
        --plan ./references/tracking-plan.xlsx \
        --actual ./validation/actual_data.json \
        --output ./validation/diff_report.json

输出 JSON 结构:
    {
      "summary": {"total_events": N, "pass": N, "anomaly": N, "missing": N},
      "events": [{"event_name": "...", "status": "pass|anomaly|missing", "issues": [...]}],
      "user_attributes": [...]
    }
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tracking-setup-e2e", "scripts"))
from tracking_plan import TrackingPlan


@dataclass
class Issue:
    category: str      # "missing_event" | "missing_property" | "type_mismatch" | "value_anomaly" | "null_value"
    field: str
    expected: str = ""
    actual: str = ""
    severity: str = "warning"   # "error" | "warning"
    suggestion: str = ""


@dataclass
class EventResult:
    event_name: str
    status: str        # "pass" | "anomaly" | "missing"
    imported_count: int = 0
    issues: List[Issue] = field(default_factory=list)


@dataclass
class UserAttrResult:
    attr_name: str
    status: str
    imported_count: int = 0
    issues: List[Issue] = field(default_factory=list)


# 异常值检测规则
_ANOMALY_PATTERNS = {
    "empty_string": re.compile(r"^\s*$"),
    "placeholder": re.compile(r"^(test|placeholder|example|sample|todo|tbd|xxx+|dummy|foo|bar|n/?a|null|none|undefined)\w*$", re.IGNORECASE),
    "garbled": re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]"),  # 控制字符
}


def _is_anomalous_value(val: Any) -> Optional[str]:
    """检测值是否异常，返回异常类型或 None。"""
    if val is None:
        return "null_value"
    if isinstance(val, str):
        if _ANOMALY_PATTERNS["empty_string"].match(val):
            return "empty_string"
        if _ANOMALY_PATTERNS["placeholder"].match(val):
            return "placeholder"
        if _ANOMALY_PATTERNS["garbled"].search(val):
            return "garbled"
    return None


def _type_match(expected_type: str, actual_val: Any) -> bool:
    """检查实际值是否符合期望类型。"""
    expected = (expected_type or "string").lower()
    if expected in ("string", "list"):
        return isinstance(actual_val, str)
    if expected in ("number", "int", "integer", "float", "double", "currency"):
        return isinstance(actual_val, (int, float))
    if expected in ("bool", "boolean", "checkbox"):
        return isinstance(actual_val, bool)
    if expected in ("datetime", "date/time", "date"):
        return isinstance(actual_val, str)  # ISO 格式字符串
    return True


def compare_event(
    event_name: str,
    schema_props: Dict[str, Dict],
    samples: List[dict],
) -> EventResult:
    """对比单个事件的方案定义与实际数据。"""
    result = EventResult(event_name=event_name, status="pass", imported_count=len(samples))

    if not samples:
        result.status = "missing"
        result.issues.append(Issue(
            category="missing_event",
            field=event_name,
            expected=f"事件应存在，方案定义了 {len(schema_props)} 个属性",
            actual="CDP 中最近时间范围内无数据",
            severity="error",
            suggestion="检查 SDK 是否正确初始化、事件触发条件是否满足、设备是否在白名单内",
        ))
        return result

    # 收集实际数据中出现的所有属性名
    actual_props: Set[str] = set()
    for sample in samples:
        for key in sample:
            if not key.startswith("$"):
                actual_props.add(key)

    # 检查缺失属性
    for prop_name, prop_def in schema_props.items():
        if prop_name not in actual_props:
            result.status = "anomaly"
            result.issues.append(Issue(
                category="missing_property",
                field=prop_name,
                expected=prop_def.get("type", "string"),
                actual="属性在所有样本中均未出现",
                severity="error",
                suggestion="检查属性名拼写是否一致、SDK 中是否正确传值、该属性是否在当前业务场景下有值",
            ))

    # 检查类型和异常值
    prop_samples: Dict[str, List[Any]] = {p: [] for p in schema_props}
    for sample in samples:
        for prop_name in schema_props:
            if prop_name in sample:
                prop_samples[prop_name].append(sample[prop_name])

    for prop_name, prop_def in schema_props.items():
        vals = prop_samples.get(prop_name, [])
        if not vals:
            continue

        expected_type = prop_def.get("type", "string")
        # 类型检查：如果超过 80% 样本类型不匹配，报 anomaly
        type_mismatches = sum(1 for v in vals if not _type_match(expected_type, v))
        if type_mismatches >= max(1, len(vals) * 0.8):
            result.status = "anomaly"
            result.issues.append(Issue(
                category="type_mismatch",
                field=prop_name,
                expected=expected_type,
                actual=f"{type_mismatches}/{len(vals)} 条类型不匹配，示例: {vals[0]!r}",
                severity="error",
                suggestion=f"检查 SDK 中该字段的传值类型，期望 {expected_type}",
            ))

        # 异常值检查
        anomaly_count = 0
        anomaly_examples = []
        for v in vals:
            anomaly_type = _is_anomalous_value(v)
            if anomaly_type:
                anomaly_count += 1
                if len(anomaly_examples) < 3:
                    anomaly_examples.append(f"{v!r}({anomaly_type})")
        if anomaly_count >= max(1, len(vals) * 0.3):
            result.status = "anomaly"
            result.issues.append(Issue(
                category="value_anomaly",
                field=prop_name,
                expected="正常业务值",
                actual=f"{anomaly_count}/{len(vals)} 条异常: {', '.join(anomaly_examples)}",
                severity="warning",
                suggestion="区分'代码未传值'(bug)和'业务场景确实无值'(需更新方案说明)",
            ))

        # 枚举值检查
        enum_values = prop_def.get("enum_values")
        if enum_values:
            invalid = [v for v in vals if v is not None and str(v) not in enum_values]
            if invalid:
                result.status = "anomaly"
                result.issues.append(Issue(
                    category="value_anomaly",
                    field=prop_name,
                    expected=f"枚举值: {enum_values}",
                    actual=f"出现非枚举值: {invalid[:3]!r}",
                    severity="warning",
                    suggestion="检查是否有新枚举值未更新到方案中，或代码传入了错误值",
                ))

    return result


def compare_user_attr(
    attr_name: str,
    attr_def: Dict,
    samples: List[dict],
) -> UserAttrResult:
    """对比单个用户属性的方案定义与实际数据。"""
    result = UserAttrResult(attr_name=attr_name, status="pass", imported_count=len(samples))

    if not samples:
        result.status = "missing"
        result.issues.append(Issue(
            category="missing_event",
            field=attr_name,
            expected="用户属性应存在",
            actual="CDP 中最近时间范围内无数据",
            severity="error",
            suggestion="检查 profile_set 调用是否正确、属性名拼写是否一致",
        ))
        return result

    expected_type = attr_def.get("type", "string")
    vals = [s.get(attr_name) for s in samples if attr_name in s]

    if not vals:
        result.status = "anomaly"
        result.issues.append(Issue(
            category="missing_property",
            field=attr_name,
            expected=expected_type,
            actual="样本中存在记录但该属性值为空",
            severity="error",
            suggestion="检查 profile_set 中是否传入了该属性",
        ))
        return result

    # 类型检查
    type_mismatches = sum(1 for v in vals if not _type_match(expected_type, v))
    if type_mismatches >= max(1, len(vals) * 0.8):
        result.status = "anomaly"
        result.issues.append(Issue(
            category="type_mismatch",
            field=attr_name,
            expected=expected_type,
            actual=f"{type_mismatches}/{len(vals)} 条类型不匹配",
            severity="error",
            suggestion=f"检查属性类型，期望 {expected_type}",
        ))

    # 异常值检查
    anomaly_count = 0
    anomaly_examples = []
    for v in vals:
        anomaly_type = _is_anomalous_value(v)
        if anomaly_type:
            anomaly_count += 1
            if len(anomaly_examples) < 3:
                anomaly_examples.append(f"{v!r}({anomaly_type})")
    if anomaly_count >= max(1, len(vals) * 0.3):
        result.status = "anomaly"
        result.issues.append(Issue(
            category="value_anomaly",
            field=attr_name,
            expected="正常业务值",
            actual=f"{anomaly_count}/{len(vals)} 条异常: {', '.join(anomaly_examples)}",
            severity="warning",
            suggestion="检查 profile_set 中该属性的赋值逻辑",
        ))

    return result


def main():
    parser = argparse.ArgumentParser(
        description="将埋点方案与实际数据逐项比对",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 %(prog)s --plan ./references/plan.xlsx --actual ./validation/actual_data.json --output ./validation/diff_report.json
        """,
    )
    parser.add_argument("--plan", required=True, help="埋点方案 Excel 路径")
    parser.add_argument("--actual", required=True, help="fetch_data.py 输出的实际数据 JSON")
    parser.add_argument("--output", default="", help="差异报告输出路径")
    args = parser.parse_args()

    if not Path(args.plan).exists():
        print(f"❌ 找不到埋点方案: {args.plan}")
        sys.exit(1)
    if not Path(args.actual).exists():
        print(f"❌ 找不到实际数据: {args.actual}")
        sys.exit(1)

    print("=== 数据比对 ===")

    # 加载实际数据
    with open(args.actual, "r", encoding="utf-8") as f:
        actual_data = json.load(f)

    actual_events = actual_data.get("actual", {}).get("events", {})
    actual_user_attrs = actual_data.get("actual", {}).get("user_attributes", {})
    schema_events = actual_data.get("schema", {}).get("events", {})
    schema_user_attrs = actual_data.get("schema", {}).get("user_attributes", {})

    # 对比事件
    event_results: List[EventResult] = []
    for event_name in sorted(schema_events):
        samples = actual_events.get(event_name, [])
        result = compare_event(event_name, schema_events[event_name]["properties"], samples)
        event_results.append(result)

    # 对比用户属性
    user_attr_results: List[UserAttrResult] = []
    for attr_name in sorted(schema_user_attrs):
        samples = actual_user_attrs.get(attr_name, [])
        result = compare_user_attr(attr_name, schema_user_attrs[attr_name], samples)
        user_attr_results.append(result)

    # 汇总
    pass_events = sum(1 for r in event_results if r.status == "pass")
    anomaly_events = sum(1 for r in event_results if r.status == "anomaly")
    missing_events = sum(1 for r in event_results if r.status == "missing")

    pass_attrs = sum(1 for r in user_attr_results if r.status == "pass")
    anomaly_attrs = sum(1 for r in user_attr_results if r.status == "anomaly")
    missing_attrs = sum(1 for r in user_attr_results if r.status == "missing")

    print(f"\n事件对比结果:")
    print(f"  通过: {pass_events}  异常: {anomaly_events}  缺失: {missing_events}")
    print(f"用户属性对比结果:")
    print(f"  通过: {pass_attrs}  异常: {anomaly_attrs}  缺失: {missing_attrs}")

    # 输出
    report = {
        "summary": {
            "events": {"total": len(event_results), "pass": pass_events, "anomaly": anomaly_events, "missing": missing_events},
            "user_attributes": {"total": len(user_attr_results), "pass": pass_attrs, "anomaly": anomaly_attrs, "missing": missing_attrs},
        },
        "events": [
            {
                "event_name": r.event_name,
                "status": r.status,
                "imported_count": r.imported_count,
                "issues": [
                    {"category": i.category, "field": i.field, "expected": i.expected,
                     "actual": i.actual, "severity": i.severity, "suggestion": i.suggestion}
                    for i in r.issues
                ],
            }
            for r in event_results
        ],
        "user_attributes": [
            {
                "attr_name": r.attr_name,
                "status": r.status,
                "imported_count": r.imported_count,
                "issues": [
                    {"category": i.category, "field": i.field, "expected": i.expected,
                     "actual": i.actual, "severity": i.severity, "suggestion": i.suggestion}
                    for i in r.issues
                ],
            }
            for r in user_attr_results
        ],
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 差异报告已保存: {output_path}")
    else:
        print("\n" + json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
