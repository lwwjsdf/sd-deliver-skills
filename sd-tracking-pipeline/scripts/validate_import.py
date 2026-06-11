#!/usr/bin/env python3
"""
validate_import.py — 导入后通过 OpenAPI 自定义查询校验数据是否正确落库

用法：
    python3 tracking-setup-e2e/scripts/validate_import.py \
        --cdp-url https://demo.sensorsdata.cn \
        --project default \
        --api-key "#K-xxx" \
        --jsonl ./mock_data/westk.jsonl
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from config_helper import get_config

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared", "postman"))
from sensors_openapi import SensorsOpenAPI


def _parse_jsonl(jsonl_file: str):
    """返回 (event_counts, start_date, end_date)。"""
    event_counts: Counter = Counter()
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

            # 提取时间戳（毫秒 or 秒）
            props = record.get("properties", {})
            ts = props.get("$time") or record.get("time")
            if ts:
                ts = int(ts)
                if ts > 1e12:
                    ts = ts // 1000  # 毫秒转秒
                timestamps.append(ts)

    if timestamps:
        import datetime
        start_date = datetime.datetime.utcfromtimestamp(min(timestamps)).strftime("%Y-%m-%d")
        end_date = datetime.datetime.utcfromtimestamp(max(timestamps)).strftime("%Y-%m-%d")
    else:
        import datetime
        today = datetime.date.today()
        start_date = (today.replace(day=1)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

    return event_counts, start_date, end_date


def validate_import(
    cdp_url: str, project: str, api_key: str, jsonl_file: str, wait_seconds: int = 0
) -> bool:
    """
    查询 CDP 中各事件的条数，与 JSONL 文件中的条数对比。
    返回 True 表示数据一致，False 表示有差异或查询失败。
    """
    print(f"\n📂 解析数据文件: {Path(jsonl_file).name}")
    event_counts, start_date, end_date = _parse_jsonl(jsonl_file)

    if not event_counts:
        print("  ℹ️  未找到自定义事件，跳过校验")
        return True

    total_imported = sum(event_counts.values())
    print(f"  导入文件包含 {len(event_counts)} 种事件，共 {total_imported} 条")
    print(f"  数据时间范围: {start_date} ~ {end_date}")

    if wait_seconds > 0:
        print(f"\n⏳ 等待 {wait_seconds} 秒让数据完成处理...")
        time.sleep(wait_seconds)

    print(f"\n🔗 连接 CDP: {cdp_url}  项目: {project}")
    api = SensorsOpenAPI(cdp_url, api_key, project)

    event_names = list(event_counts.keys())
    print(f"\n🔎 执行自定义查询（事件数: {len(event_names)}，时间范围: {start_date} ~ {end_date}）")

    cdp_counts = api.query_event_counts(event_names, start_date, end_date)

    if not cdp_counts:
        print("\n⚠️  自定义查询未返回数据，可能原因：")
        print("   1. CDP 数据处理有延迟，请稍后重试（加 --wait 60）")
        print("   2. 当前账号无自定义查询权限")
        print("   3. 数据时间范围与查询范围不匹配")
        print("\n   建议：登录神策后台 → 分析 → 自定义查询，手动执行以下 SQL 验证：")
        names_sql = ", ".join(f"'{n}'" for n in event_names[:5])
        if len(event_names) > 5:
            names_sql += ", ..."
        print(f"   SELECT event, count(*) AS cnt FROM events")
        print(f"   WHERE date >= '{start_date}' AND date <= '{end_date}'")
        print(f"   AND event IN ({names_sql})")
        print(f"   GROUP BY event")
        return False

    # 对比结果
    print(f"\n{'='*65}")
    print(f"{'事件名':<35} {'导入条数':>8} {'CDP条数':>8} {'状态':>6}")
    print(f"{'='*65}")

    all_ok = True
    for event_name in sorted(event_counts):
        imported = event_counts[event_name]
        cdp_cnt = cdp_counts.get(event_name, 0)

        if cdp_cnt == 0:
            status = "❌ 未找到"
            all_ok = False
        elif cdp_cnt < imported:
            status = "⚠️  偏少"
            all_ok = False
        elif cdp_cnt > imported:
            status = "ℹ️  偏多"  # 可能有历史数据
        else:
            status = "✅"

        print(f"  {event_name:<33} {imported:>8} {cdp_cnt:>8}  {status}")

    print(f"{'='*65}")

    if all_ok:
        print(f"\n✅ 校验通过！所有事件数据均已正确落库")
    else:
        print(f"\n⚠️  部分事件数据异常，请检查上方标记项")
        print("   可能原因：CDP 数据处理延迟（建议等待 1-2 分钟后重试）")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="导入后通过 OpenAPI 自定义查询校验数据是否正确落库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 立即校验
  python3 %(prog)s \\
    --cdp-url https://demo.sensorsdata.cn \\
    --project default \\
    --api-key "#K-xxx" \\
    --jsonl ./mock_data/westk.jsonl

  # 等待 60 秒后再校验（数据处理有延迟时使用）
  python3 %(prog)s --wait 60 --jsonl ./mock_data/westk.jsonl
        """,
    )
    parser.add_argument("--cdp-url", dest="cdp_url", default="",
                        help="神策 CDP 地址")
    parser.add_argument("--project", dest="project", default="",
                        help="项目 ID")
    parser.add_argument("--api-key", dest="api_key", default="",
                        help="Open API 密钥")
    parser.add_argument("--jsonl", dest="jsonl", default="",
                        help="JSONL 数据文件路径")
    parser.add_argument("--wait", dest="wait", type=int, default=0,
                        help="查询前等待秒数（数据处理有延迟时使用）")
    args = parser.parse_args()

    print("=== 导入结果校验 ===")

    cdp_url = get_config("cdp_url", args.cdp_url)
    project = get_config("project", args.project)
    # OpenAPI 的 sensorsdata-project header 使用项目显示名，而非 URL 中的 project ID
    project_name = os.getenv("SA_PROJECT_NAME", "") or project
    api_key = get_config("api_key", args.api_key)

    print(f"使用项目: {project_name} (OpenAPI sensorsdata-project header)")

    if args.jsonl:
        jsonl_file = args.jsonl
    else:
        mock_data_dir = Path(__file__).parent.parent / "mock_data"
        jsonl_files = sorted(
            mock_data_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not jsonl_files:
            print("错误：找不到 jsonl 数据文件")
            sys.exit(1)
        jsonl_file = str(jsonl_files[0])
        print(f"自动选择最新数据文件: {Path(jsonl_file).name}")

    ok = validate_import(cdp_url, project_name, api_key, jsonl_file, wait_seconds=args.wait)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
