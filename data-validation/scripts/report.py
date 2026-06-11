#!/usr/bin/env python3
"""
report.py — Phase 4: 将差异报告 JSON 渲染为 Markdown 报告

用法:
    python3 data-validation/scripts/report.py \
        --diff ./validation/diff_report.json \
        --output ./validation/validation_report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def _severity_icon(sev: str) -> str:
    return "❌" if sev == "error" else "⚠️"


def _status_badge(status: str) -> str:
    return {"pass": "✅ 通过", "anomaly": "⚠️ 异常", "missing": "❌ 缺失"}.get(status, status)


def generate_markdown(diff_data: dict) -> str:
    lines: List[str] = []

    # Header
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.extend([
        "# 埋点数据校验报告",
        "",
        f"**校验时间：** {now}",
        "",
    ])

    # Summary
    es = diff_data.get("summary", {}).get("events", {})
    us = diff_data.get("summary", {}).get("user_attributes", {})
    lines.extend([
        "## 汇总",
        "",
        "### 事件",
        f"- 通过：{es.get('pass', 0)} 个",
        f"- 异常：{es.get('anomaly', 0)} 个",
        f"- 缺失：{es.get('missing', 0)} 个",
        f"- 总计：{es.get('total', 0)} 个",
        "",
        "### 用户属性",
        f"- 通过：{us.get('pass', 0)} 个",
        f"- 异常：{us.get('anomaly', 0)} 个",
        f"- 缺失：{us.get('missing', 0)} 个",
        f"- 总计：{us.get('total', 0)} 个",
        "",
    ])

    # Events detail
    event_results = diff_data.get("events", [])
    anomaly_events = [r for r in event_results if r["status"] != "pass"]
    if anomaly_events:
        lines.extend([
            "## 异常事件详情",
            "",
        ])
        for r in anomaly_events:
            lines.append(f"### {r['event_name']} — {_status_badge(r['status'])} (样本数: {r['imported_count']})")
            lines.append("")
            for issue in r["issues"]:
                icon = _severity_icon(issue["severity"])
                lines.append(f"{icon} **{issue['category']}** | `{issue['field']}`")
                lines.append(f"  - 期望: {issue['expected']}")
                lines.append(f"  - 实际: {issue['actual']}")
                if issue["suggestion"]:
                    lines.append(f"  - 建议: {issue['suggestion']}")
                lines.append("")

    # User attributes detail
    attr_results = diff_data.get("user_attributes", [])
    anomaly_attrs = [r for r in attr_results if r["status"] != "pass"]
    if anomaly_attrs:
        lines.extend([
            "## 异常用户属性详情",
            "",
        ])
        for r in anomaly_attrs:
            lines.append(f"### {r['attr_name']} — {_status_badge(r['status'])} (样本数: {r['imported_count']})")
            lines.append("")
            for issue in r["issues"]:
                icon = _severity_icon(issue["severity"])
                lines.append(f"{icon} **{issue['category']}** | `{issue['field']}`")
                lines.append(f"  - 期望: {issue['expected']}")
                lines.append(f"  - 实际: {issue['actual']}")
                if issue["suggestion"]:
                    lines.append(f"  - 建议: {issue['suggestion']}")
                lines.append("")

    # Pass list (brief)
    pass_events = [r for r in event_results if r["status"] == "pass"]
    pass_attrs = [r for r in attr_results if r["status"] == "pass"]
    if pass_events or pass_attrs:
        lines.extend([
            "## 通过项清单",
            "",
        ])
        if pass_events:
            lines.append("**事件：** " + ", ".join(f"`{r['event_name']}`" for r in pass_events))
            lines.append("")
        if pass_attrs:
            lines.append("**用户属性：** " + ", ".join(f"`{r['attr_name']}`" for r in pass_attrs))
            lines.append("")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="将差异报告 JSON 渲染为 Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 %(prog)s --diff ./validation/diff_report.json --output ./validation/report.md
        """,
    )
    parser.add_argument("--diff", required=True, help="compare.py 输出的差异报告 JSON")
    parser.add_argument("--output", default="", help="Markdown 报告输出路径")
    args = parser.parse_args()

    if not Path(args.diff).exists():
        print(f"❌ 找不到差异报告: {args.diff}")
        sys.exit(1)

    with open(args.diff, "r", encoding="utf-8") as f:
        diff_data = json.load(f)

    md = generate_markdown(diff_data)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ 报告已生成: {output_path}")
    else:
        print(md)


if __name__ == "__main__":
    main()
