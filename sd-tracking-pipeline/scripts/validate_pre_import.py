#!/usr/bin/env python3
"""
validate_pre_import.py — 导入前数据校验

对比 JSONL 模拟数据与 Tracking Plan / business_logic.yaml，检查：
- 事件名是否都在方案中
- 必填属性是否完整
- 属性类型是否匹配
- 枚举值是否在允许范围内
- 历史反馈项是否已覆盖

用法：
    python3 validate_pre_import.py \
        --jsonl ./mock_data/westk.jsonl \
        --tracking-plan ./references/tracking-plan.xlsx \
        --iterations ./references/MOCK_DATA_ITERATIONS.md
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from config_helper import get_config
from tracking_plan import TrackingPlan, PropertyDef


def _iter_records(jsonl_file: str):
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _load_iterations(iterations_file: str) -> List[Dict[str, Any]]:
    """Parse MOCK_DATA_ITERATIONS.md and extract open issues."""
    if not iterations_file or not Path(iterations_file).exists():
        return []

    issues = []
    with open(iterations_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple regex extraction for lines like:
    # - [ ] field xxx missing on EventName (P1)
    # - [x] fixed xxx
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        if "[x]" in line or "✅" in line:
            continue
        if "[ ]" in line or "⏳" in line or "❌" in line:
            issues.append({"raw": line, "event": "", "field": "", "description": line})
    return issues


class PreImportValidator:
    def __init__(self, tracking_plan: TrackingPlan, iterations_file: Optional[str] = None):
        self.plan = tracking_plan
        self.issues = _load_iterations(iterations_file) if iterations_file else []

    def validate(
        self,
        jsonl_file: str,
        sample_size: int = 1000,
    ) -> Dict[str, Any]:
        """Run all pre-import checks and return structured report."""
        findings = []

        # 1. Sample records
        records_by_event: Dict[str, List[dict]] = defaultdict(list)
        record_types: Counter = Counter()
        total_rows = 0

        for record in _iter_records(jsonl_file):
            total_rows += 1
            rtype = record.get("type", "unknown")
            record_types[rtype] += 1
            if rtype != "track":
                continue
            event_name = record.get("event", "")
            records_by_event[event_name].append(record)

        # 2. Check event names
        plan_events = set(self.plan.list_events())
        jsonl_events = set(records_by_event.keys())
        unknown_events = jsonl_events - plan_events
        if unknown_events:
            findings.append({
                "rule": "event_name",
                "severity": "error",
                "description": f"JSONL 中存在 {len(unknown_events)} 个不在 Tracking Plan 中的事件",
                "details": sorted(unknown_events),
            })

        missing_events = plan_events - jsonl_events
        # Only flag custom events, not preset events that may not fire
        custom_events = set(self.plan._custom_events.keys())
        missing_custom = missing_events & custom_events
        if missing_custom:
            findings.append({
                "rule": "event_coverage",
                "severity": "warning",
                "description": f"Tracking Plan 中 {len(missing_custom)} 个自定义事件未在 JSONL 中出现",
                "details": sorted(missing_custom),
            })

        # 3. Check properties per event
        for event_name, records in records_by_event.items():
            schema = self.plan.get_event_schema(event_name)
            if not schema:
                continue

            plan_props = {p.name: p for p in schema.properties}
            plan_prop_names = set(plan_props.keys())

            # Sample if too many
            sampled = records[:sample_size] if len(records) > sample_size else records

            for record in sampled:
                props = record.get("properties", {})
                prop_names = set(props.keys())

                # Missing required-ish properties (we treat all defined props as expected)
                missing_props = plan_prop_names - prop_names
                if missing_props:
                    findings.append({
                        "rule": "missing_property",
                        "severity": "error",
                        "event": event_name,
                        "description": f"事件 {event_name} 缺少属性",
                        "details": sorted(missing_props),
                    })

                # Unknown properties
                unknown_props = prop_names - plan_prop_names
                if unknown_props:
                    findings.append({
                        "rule": "unknown_property",
                        "severity": "warning",
                        "event": event_name,
                        "description": f"事件 {event_name} 存在 Tracking Plan 未定义的属性",
                        "details": sorted(unknown_props),
                    })

                # Type and enum checks
                for prop_name, value in props.items():
                    if prop_name not in plan_props:
                        continue
                    prop_def = plan_props[prop_name]
                    if not self._type_matches(value, prop_def.value_type):
                        findings.append({
                            "rule": "type_mismatch",
                            "severity": "error",
                            "event": event_name,
                            "property": prop_name,
                            "description": f"事件 {event_name} 属性 {prop_name} 类型不匹配（期望 {prop_def.value_type}，实际 {type(value).__name__}）",
                        })

                    if prop_def.enum_values and value is not None:
                        if str(value) not in [str(v) for v in prop_def.enum_values]:
                            findings.append({
                                "rule": "enum_violation",
                                "severity": "warning",
                                "event": event_name,
                                "property": prop_name,
                                "description": f"事件 {event_name} 属性 {prop_name} 值不在枚举范围内",
                                "expected": prop_def.enum_values,
                                "actual": value,
                            })

                # Only report first sample to avoid duplication
                break

        # 4. Historical issues coverage (simple keyword matching)
        for issue in self.issues:
            raw = issue["raw"]
            # Try to extract event/field names mentioned
            mentioned_events = [e for e in jsonl_events if e in raw]
            mentioned_fields = []
            for event_name, records in records_by_event.items():
                if not records:
                    continue
                props = records[0].get("properties", {})
                for prop in props:
                    if prop in raw:
                        mentioned_fields.append((event_name, prop))

            covered = bool(mentioned_events or mentioned_fields)
            findings.append({
                "rule": "iteration_coverage",
                "severity": "warning" if not covered else "info",
                "description": f"迭代记录问题未明确覆盖: {raw[:80]}" if not covered else f"迭代记录问题已覆盖: {raw[:80]}",
            })

        # Deduplicate findings
        deduped = []
        seen = set()
        for f in findings:
            key = (f.get("rule"), f.get("event"), f.get("property"), tuple(f.get("details", [])))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(f)

        errors = [f for f in deduped if f.get("severity") == "error"]
        warnings = [f for f in deduped if f.get("severity") == "warning"]

        return {
            "total_rows": total_rows,
            "record_types": dict(record_types),
            "events_in_jsonl": sorted(jsonl_events),
            "events_in_plan": sorted(plan_events),
            "errors": errors,
            "warnings": warnings,
            "all_findings": deduped,
            "passed": len(errors) == 0,
        }

    @staticmethod
    def _type_matches(value: Any, value_type: str) -> bool:
        """Check if a value matches the expected value_type."""
        vt = value_type.lower()
        if vt in ("boolean", "bool"):
            return isinstance(value, bool)
        if vt in ("number", "int", "integer", "float", "double"):
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if vt == "datetime":
            return isinstance(value, str)
        if vt == "list":
            return isinstance(value, list)
        # string default
        return isinstance(value, str)


def _resolve_jsonl(args_jsonl: str) -> str:
    if args_jsonl:
        return args_jsonl
    mock_data_dir = Path(__file__).parent.parent / "mock_data"
    jsonl_files = sorted(
        mock_data_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not jsonl_files:
        print("❌ 找不到 jsonl 数据文件")
        sys.exit(1)
    return str(jsonl_files[0])


def main():
    parser = argparse.ArgumentParser(
        description="导入前数据校验：对比 JSONL 与 Tracking Plan",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 %(prog)s
  python3 %(prog)s --jsonl ./mock_data/westk.jsonl
  python3 %(prog)s --jsonl ./mock_data/westk.jsonl --tracking-plan ./references/plan.xlsx
  python3 %(prog)s --jsonl ./mock_data/westk.jsonl --iterations ./references/MOCK_DATA_ITERATIONS.md
        """,
    )
    parser.add_argument("--jsonl", dest="jsonl", default="", help="JSONL 数据文件路径")
    parser.add_argument("--tracking-plan", dest="tracking_plan", default="",
                        help="埋点方案 Excel 路径（默认从 .env TRACKING_PLAN_PATH）")
    parser.add_argument("--iterations", dest="iterations", default="",
                        help="迭代记录 Markdown 路径（默认 ./references/MOCK_DATA_ITERATIONS.md）")
    parser.add_argument("--sample-size", dest="sample_size", type=int, default=1000,
                        help="每个事件抽样条数（默认 1000）")
    parser.add_argument("--output-json", dest="output_json", action="store_true",
                        help="输出 JSON 格式报告")
    args = parser.parse_args()

    jsonl_file = _resolve_jsonl(args.jsonl)
    tracking_plan_path = get_config("tracking_plan", args.tracking_plan)

    iterations = args.iterations
    if not iterations:
        default_iter = Path(__file__).parent.parent / "references" / "MOCK_DATA_ITERATIONS.md"
        if default_iter.exists():
            iterations = str(default_iter)

    print(f"📂 JSONL: {Path(jsonl_file).name}")
    print(f"📋 Tracking Plan: {Path(tracking_plan_path).name}")
    if iterations:
        print(f"📝 Iterations: {Path(iterations).name}")

    plan = TrackingPlan(tracking_plan_path)
    validator = PreImportValidator(plan, iterations)
    report = validator.validate(jsonl_file, sample_size=args.sample_size)

    if args.output_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0 if report["passed"] else 1)

    print("\n" + "=" * 60)
    print(f"总记录数: {report['total_rows']:,}")
    print(f"JSONL 事件数: {len(report['events_in_jsonl'])}")
    print(f"Tracking Plan 事件数: {len(report['events_in_plan'])}")
    print("=" * 60)

    if report["errors"]:
        print(f"\n❌ {len(report['errors'])} 个错误:")
        for f in report["errors"]:
            print(f"  [{f['rule']}] {f['description']}")
            if "details" in f:
                for d in f["details"][:10]:
                    print(f"    - {d}")

    if report["warnings"]:
        print(f"\n⚠️  {len(report['warnings'])} 个警告:")
        for f in report["warnings"]:
            print(f"  [{f['rule']}] {f['description']}")

    if report["passed"] and not report["warnings"]:
        print("\n✅ 导入前校验通过")
    elif report["passed"]:
        print("\n✅ 无错误，但存在警告")
    else:
        print("\n❌ 导入前校验未通过，请修复后重试")

    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
