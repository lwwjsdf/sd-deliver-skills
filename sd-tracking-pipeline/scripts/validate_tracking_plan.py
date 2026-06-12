#!/usr/bin/env python3
"""
validate_tracking_plan.py — Phase 4d UAT 数据校验（基于 validate_import.py 扩展）

在 validate_import.py 的「事件条数对比」基础上，增加：
  1. 属性枚举值校验 — 实际值是否在埋点方案定义的枚举范围内
  2. 数据类型匹配校验 — 实际值类型是否与埋点方案定义一致

用法：
    python3 tracking-setup-e2e/scripts/validate_tracking_plan.py \
        --tracking-plan ./references/tracking-plan.xlsx \
        --jsonl ./mock_data/westk.jsonl \
        --output ./reports/uat_data_validation_report.md

依赖：
    pip install openpyxl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from config_helper import get_config
from tracking_plan import TrackingPlan, PropertyDef


def _parse_jsonl_records(jsonl_file: str) -> Tuple[Counter, Dict[str, List[dict]], str, str]:
    """
    解析 JSONL，返回：
      - event_counts: Counter
      - event_records: {event_name: [record, ...]}
      - start_date, end_date
    """
    event_counts: Counter = Counter()
    event_records: Dict[str, List[dict]] = defaultdict(list)
    timestamps = []

    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("type") != "track":
                continue
            event_name = record.get("event", "")
            if not event_name or event_name.startswith("$"):
                continue
            event_counts[event_name] += 1
            event_records[event_name].append(record)

            props = record.get("properties", {})
            ts = props.get("$time") or record.get("time")
            if ts:
                ts = int(ts)
                if ts > 1e12:
                    ts = ts // 1000
                timestamps.append(ts)

    if timestamps:
        start_date = datetime.utcfromtimestamp(min(timestamps)).strftime("%Y-%m-%d")
        end_date = datetime.utcfromtimestamp(max(timestamps)).strftime("%Y-%m-%d")
    else:
        today = datetime.date.today()
        start_date = (today.replace(day=1)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

    return event_counts, dict(event_records), start_date, end_date


def _check_enum_compliance(
    prop: PropertyDef, actual_values: List[object]
) -> Tuple[bool, List[str]]:
    """
    检查实际值是否在枚举范围内。
    返回 (是否通过, [违规值, ...])。
    """
    if not prop.enum_values:
        return True, []

    allowed = set(str(v).strip() for v in prop.enum_values)
    violations = []
    for val in actual_values:
        val_str = str(val).strip()
        if val_str not in allowed:
            violations.append(val_str)

    # 去重，保留前 10 个示例
    unique_violations = list(dict.fromkeys(violations))[:10]
    passed = len(unique_violations) == 0
    return passed, unique_violations


def _check_type_compliance(
    prop: PropertyDef, actual_values: List[object]
) -> Tuple[bool, List[str]]:
    """
    检查实际值类型是否与定义一致。
    返回 (是否通过, [错误描述, ...])。
    """
    expected_type = prop.value_type.lower()
    errors = []

    for val in actual_values:
        if val is None:
            continue  # null 值单独处理，不在这里报类型错误

        ok = False
        if expected_type in ("string",):
            ok = isinstance(val, str)
        elif expected_type in ("number", "int", "integer", "float", "double"):
            ok = isinstance(val, (int, float)) and not isinstance(val, bool)
        elif expected_type in ("bool", "boolean"):
            ok = isinstance(val, bool)
        elif expected_type == "datetime":
            ok = isinstance(val, str)  # datetime 在 JSON 中通常是字符串
        elif expected_type == "list":
            ok = isinstance(val, list)

        if not ok:
            errors.append(f"'{val}' ({type(val).__name__}) 不符合 {expected_type}")

    unique_errors = list(dict.fromkeys(errors))[:10]
    passed = len(unique_errors) == 0
    return passed, unique_errors


def _check_null_rate(
    prop_name: str, actual_values: List[object], threshold: float = 0.5
) -> Tuple[bool, float]:
    """
    检查属性空值率是否超过阈值。
    返回 (是否通过, 空值率)。
    """
    if not actual_values:
        return True, 0.0
    null_count = sum(1 for v in actual_values if v is None or v == "")
    null_rate = null_count / len(actual_values)
    passed = null_rate <= threshold
    return passed, null_rate


class ValidationReport:
    """收集校验结果并生成 Markdown 报告。"""

    def __init__(self, tracking_plan_path: str, jsonl_path: str):
        self.tracking_plan_path = tracking_plan_path
        self.jsonl_path = jsonl_path
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.sections: List[str] = []
        self.summary = {
            "total_events": 0,
            "checked_events": 0,
            "passed_events": 0,
            "total_props": 0,
            "passed_props": 0,
            "enum_violations": 0,
            "type_violations": 0,
            "null_violations": 0,
        }

    def add_section(self, title: str, content: str):
        self.sections.append(f"## {title}\n\n{content}\n")

    def add_event_result(
        self,
        event_name: str,
        imported_count: int,
        prop_results: List[dict],
    ):
        self.summary["total_events"] += 1
        self.summary["checked_events"] += 1
        self.summary["total_props"] += len(prop_results)

        event_passed = all(r["passed"] for r in prop_results)
        if event_passed:
            self.summary["passed_events"] += 1

        lines = [f"### {event_name}（{imported_count} 条）\n"]
        lines.append("| 属性 | 枚举校验 | 类型校验 | 空值率 | 状态 |")
        lines.append("|------|:--------:|:--------:|:------:|:----:|")

        for r in prop_results:
            prop_name = r["prop_name"]
            enum_ok = "✅" if r["enum_passed"] else f"❌ ({', '.join(r['enum_violations'][:3])})"
            type_ok = "✅" if r["type_passed"] else f"❌ ({len(r['type_errors'])}项)"
            null_ok = f"{r['null_rate']*100:.0f}%" if r["null_passed"] else f"❌ {r['null_rate']*100:.0f}%"
            status = "✅" if r["passed"] else "❌"

            if not r["enum_passed"]:
                self.summary["enum_violations"] += 1
            if not r["type_passed"]:
                self.summary["type_violations"] += 1
            if not r["null_passed"]:
                self.summary["null_violations"] += 1
            if r["passed"]:
                self.summary["passed_props"] += 1

            lines.append(f"| {prop_name} | {enum_ok} | {type_ok} | {null_ok} | {status} |")

        lines.append("")
        self.sections.append("\n".join(lines))

    def generate(self) -> str:
        total_issues = (
            self.summary["enum_violations"]
            + self.summary["type_violations"]
            + self.summary["null_violations"]
        )

        header = f"""# UAT 数据校验报告

**生成时间:** {self.timestamp}
**埋点方案:** {self.tracking_plan_path}
**数据文件:** {self.jsonl_path}

## 汇总

| 指标 | 数值 |
|------|------|
| 校验事件数 | {self.summary['checked_events']} |
| 通过事件数 | {self.summary['passed_events']} |
| 校验属性数 | {self.summary['total_props']} |
| 通过属性数 | {self.summary['passed_props']} |
| 枚举违规 | {self.summary['enum_violations']} |
| 类型违规 | {self.summary['type_violations']} |
| 空值超标 | {self.summary['null_violations']} |
| **总问题数** | **{total_issues}** |

## 结论

{'✅ 所有校验项通过，数据符合埋点方案定义。' if total_issues == 0 else '⚠️ 发现数据质量问题，详见下方明细。'}

---

"""
        return header + "\n".join(self.sections)


def validate_tracking_plan(
    tracking_plan_path: str,
    jsonl_file: str,
    output_path: Optional[str] = None,
    sample_size: int = 100,
) -> bool:
    """
    主校验逻辑。
    返回 True 表示全部通过，False 表示有问题。
    """
    print(f"📋 加载埋点方案: {Path(tracking_plan_path).name}")
    plan = TrackingPlan(tracking_plan_path)
    all_events = plan.list_events()
    print(f"  发现 {len(all_events)} 个事件")

    print(f"\n📂 解析数据文件: {Path(jsonl_file).name}")
    event_counts, event_records, start_date, end_date = _parse_jsonl_records(jsonl_file)
    print(f"  数据时间范围: {start_date} ~ {end_date}")
    print(f"  自定义事件种类: {len(event_counts)}")

    report = ValidationReport(tracking_plan_path, jsonl_file)

    all_ok = True
    for event_name in sorted(all_events):
        imported_count = event_counts.get(event_name, 0)
        if imported_count == 0:
            report.add_section(
                f"{event_name}",
                f"⚠️ 该事件在数据文件中 **未找到**（期望有数据，实际 0 条）。",
            )
            all_ok = False
            continue

        schema = plan.get_event_schema(event_name)
        if not schema:
            continue

        records = event_records.get(event_name, [])
        # 采样，避免大数据量时过慢
        if len(records) > sample_size:
            import random

            sampled = random.sample(records, sample_size)
        else:
            sampled = records

        prop_results = []
        for prop in schema.properties:
            prop_name = prop.name
            actual_values = [
                r.get("properties", {}).get(prop_name) for r in sampled
            ]

            enum_passed, enum_violations = _check_enum_compliance(prop, actual_values)
            type_passed, type_errors = _check_type_compliance(prop, actual_values)
            null_passed, null_rate = _check_null_rate(prop_name, actual_values)

            passed = enum_passed and type_passed and null_passed
            if not passed:
                all_ok = False

            prop_results.append(
                {
                    "prop_name": prop_name,
                    "enum_passed": enum_passed,
                    "enum_violations": enum_violations,
                    "type_passed": type_passed,
                    "type_errors": type_errors,
                    "null_passed": null_passed,
                    "null_rate": null_rate,
                    "passed": passed,
                }
            )

        report.add_event_result(event_name, imported_count, prop_results)

    # 检查数据文件中有但埋点方案中没有的事件
    extra_events = set(event_counts.keys()) - set(all_events)
    if extra_events:
        report.add_section(
            "额外事件",
            f"以下事件在数据文件中出现，但埋点方案中未定义：\n\n"
            + "\n".join(f"- `{e}` ({event_counts[e]} 条)" for e in sorted(extra_events)),
        )

    markdown = report.generate()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        print(f"\n📝 报告已保存: {out}")
    else:
        print("\n" + "=" * 65)
        print(markdown)

    if all_ok:
        print("\n✅ UAT 数据校验全部通过")
    else:
        print("\n⚠️  UAT 数据校验发现问题，请查看报告")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Phase 4d UAT 数据校验：对比埋点方案与已导入数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础校验
  python3 %(prog)s \\
    --tracking-plan ./references/tracking-plan.xlsx \\
    --jsonl ./mock_data/westk.jsonl

  # 输出报告到指定路径
  python3 %(prog)s \\
    --tracking-plan ./references/tracking-plan.xlsx \\
    --jsonl ./mock_data/westk.jsonl \\
    --output ./reports/uat_data_validation_report.md
        """,
    )
    parser.add_argument(
        "--tracking-plan",
        dest="tracking_plan",
        default="",
        help="埋点方案 Excel 路径",
    )
    parser.add_argument(
        "--jsonl",
        dest="jsonl",
        default="",
        help="JSONL 数据文件路径",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output",
        default="",
        help="报告输出路径（默认打印到 stdout）",
    )
    parser.add_argument(
        "--sample",
        dest="sample",
        type=int,
        default=100,
        help="每事件采样条数（默认 100，大数据量时调小）",
    )
    args = parser.parse_args()

    print("=== UAT 数据校验（Phase 4d）===")

    tracking_plan = args.tracking_plan
    if not tracking_plan:
        refs_dir = Path.cwd() / "references"
        if refs_dir.exists():
            xlsx_files = sorted(
                refs_dir.glob("*.xlsx"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if xlsx_files:
                tracking_plan = str(xlsx_files[0])
                print(f"⚠️  未指定 --tracking-plan，自动选择最新方案: {xlsx_files[0].name}")

    if not tracking_plan:
        print("错误：缺少 --tracking-plan 参数，且 references/ 目录未找到 .xlsx 方案文件")
        sys.exit(1)

    jsonl_file = args.jsonl
    if not jsonl_file:
        mock_data_dir = Path(__file__).parent.parent / "mock_data"
        jsonl_files = sorted(
            mock_data_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not jsonl_files:
            print("错误：找不到 jsonl 数据文件")
            sys.exit(1)
        jsonl_file = str(jsonl_files[0])
        print(f"自动选择最新数据文件: {Path(jsonl_file).name}")

    ok = validate_tracking_plan(
        tracking_plan,
        jsonl_file,
        output_path=args.output or None,
        sample_size=args.sample,
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
