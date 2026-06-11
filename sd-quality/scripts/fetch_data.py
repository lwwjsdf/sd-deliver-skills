#!/usr/bin/env python3
"""
fetch_data.py — Phase 2: 从神策 CDP 抓取实际上报数据

用法:
    python3 data-validation/scripts/fetch_data.py \
        --cdp-url https://demo.sensorsdata.cn \
        --project default \
        --api-key "#K-xxx" \
        --tracking-plan ./references/tracking-plan.xlsx \
        --hours 24 \
        --output ./validation/actual_data.json

依赖:
    pip install openpyxl python-dotenv requests
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

sys.path.insert(0, os.path.dirname(__file__))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared", "postman"))
from sensors_openapi import SensorsOpenAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tracking-setup-e2e", "scripts"))
from tracking_plan import TrackingPlan
from config_helper import get_config


# SDK 内置属性，不纳入校验范围
_SYSTEM_PROPS = {
    "$time", "$lib", "$lib_version", "$lib_method", "$lib_detail",
    "$screen_width", "$screen_height", "$wifi", "$carrier", "$network_type",
    "$app_version", "$os", "$os_version", "$manufacturer", "$model",
    "$device_id", "$anonymous_id", "$is_login_id", "$batch_id",
    "$ip", "$country", "$province", "$city", "$timezone_offset",
    "$latest_utm_source", "$latest_utm_medium", "$latest_utm_campaign",
    "$latest_utm_content", "$latest_utm_term", "$latest_referrer",
    "$latest_referrer_host", "$latest_search_keyword",
    "$latest_traffic_source_type", "$latest_scene",
    "$scene", "$share_depth", "$share_distinct_id", "$share_url_path",
    "$url_path", "$referrer", "$referrer_host", "$search_keyword",
    "$traffic_source_type", "$duration", "$url", "$title",
    "$element_type", "$element_content", "$element_id",
    "$share_title", "$share_path",
}


def _parse_tracking_plan(plan_path: str) -> TrackingPlan:
    if not Path(plan_path).exists():
        print(f"❌ 找不到埋点方案: {plan_path}")
        sys.exit(1)
    return TrackingPlan(plan_path)


def _build_event_schema_map(plan: TrackingPlan) -> Dict[str, Dict]:
    """返回 {event_name: {"properties": {prop_name: {"type": str, "required": bool}}, "trigger": str}}"""
    result = {}
    for event_name in plan.list_events():
        schema = plan.get_event_schema(event_name)
        if schema is None:
            continue
        props = {}
        for prop in schema.properties:
            if prop.name.startswith("$") or prop.name in _SYSTEM_PROPS:
                continue
            props[prop.name] = {
                "type": prop.value_type,
                "required": prop.required,
                "enum_values": prop.enum_values,
                "description": prop.description,
            }
        result[event_name] = {
            "properties": props,
            "trigger": schema.trigger,
        }
    return result


def _build_user_attr_map(plan: TrackingPlan) -> Dict[str, Dict]:
    """返回 {attr_name: {"type": str, "enum_values": list}}"""
    result = {}
    for attr in plan.get_user_attributes():
        result[attr.name] = {
            "type": attr.value_type,
            "enum_values": attr.enum_values,
            "description": attr.description,
        }
    return result


def fetch_event_samples(
    api: SensorsOpenAPI,
    event_name: str,
    start_date: str,
    end_date: str,
    limit: int = 100,
) -> List[dict]:
    """通过自定义查询获取最近 N 条事件样本。"""
    sql = (
        f"SELECT * FROM events "
        f"WHERE date >= '{start_date}' AND date <= '{end_date}' "
        f"AND event = '{event_name}' "
        f"ORDER BY time DESC "
        f"LIMIT {limit}"
    )
    try:
        resp = api.custom_query(sql)
        if resp.get("code") != "SUCCESS":
            return []
        data = resp.get("data", {})
        rows = data.get("rows", [])
        cols = data.get("columns", [])
        if not rows or not cols:
            return []
        col_names = [c.get("name", "") for c in cols]
        records = []
        for row in rows:
            record = {}
            for i, val in enumerate(row):
                if i < len(col_names):
                    record[col_names[i]] = val
            records.append(record)
        return records
    except Exception as e:
        print(f"  ⚠️ 查询事件 [{event_name}] 失败: {e}")
        return []


def fetch_user_attr_samples(
    api: SensorsOpenAPI,
    attr_name: str,
    limit: int = 100,
) -> List[dict]:
    """通过自定义查询获取用户属性样本。"""
    sql = (
        f"SELECT distinct_id, {attr_name} FROM users "
        f"WHERE {attr_name} IS NOT NULL "
        f"LIMIT {limit}"
    )
    try:
        resp = api.custom_query(sql)
        if resp.get("code") != "SUCCESS":
            return []
        data = resp.get("data", {})
        rows = data.get("rows", [])
        cols = data.get("columns", [])
        if not rows or not cols:
            return []
        col_names = [c.get("name", "") for c in cols]
        records = []
        for row in rows:
            record = {}
            for i, val in enumerate(row):
                if i < len(col_names):
                    record[col_names[i]] = val
            records.append(record)
        return records
    except Exception as e:
        print(f"  ⚠️ 查询用户属性 [{attr_name}] 失败: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="从神策 CDP 抓取实际上报数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 %(prog)s --tracking-plan ./references/plan.xlsx --hours 24 --output ./validation/actual_data.json
        """,
    )
    parser.add_argument("--cdp-url", dest="cdp_url", default="", help="神策 CDP 地址")
    parser.add_argument("--project", dest="project", default="", help="项目 ID")
    parser.add_argument("--api-key", dest="api_key", default="", help="Open API 密钥")
    parser.add_argument("--tracking-plan", dest="tracking_plan", required=True, help="埋点方案 Excel 路径")
    parser.add_argument("--hours", type=int, default=24, help="查询最近多少小时的数据 (默认: 24)")
    parser.add_argument("--limit", type=int, default=100, help="每个事件最多采样条数 (默认: 100)")
    parser.add_argument("--output", dest="output", default="", help="输出 JSON 文件路径")
    parser.add_argument("--events", dest="events", default="", help="只检查指定事件，逗号分隔")
    args = parser.parse_args()

    cdp_url = get_config("cdp_url", args.cdp_url)
    project = get_config("project", args.project)
    api_key = get_config("api_key", args.api_key)

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(hours=args.hours)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    print("=== 数据抓取 ===")
    print(f"时间范围: {start_date} ~ {end_date} (最近 {args.hours} 小时)")

    plan = _parse_tracking_plan(args.tracking_plan)
    event_schema = _build_event_schema_map(plan)
    user_attr_schema = _build_user_attr_map(plan)

    api = SensorsOpenAPI(cdp_url, api_key, project)

    # 测试连接
    try:
        events_list = api.list_events()
        print(f"✓ API 连接成功，CDP 中已有 {len(events_list)} 个事件")
    except Exception as e:
        print(f"❌ API 连接失败: {e}")
        sys.exit(1)

    # 确定要检查的事件范围
    target_events = list(event_schema.keys())
    if args.events:
        target_events = [e.strip() for e in args.events.split(",") if e.strip()]

    print(f"\n📖 埋点方案中定义 {len(event_schema)} 个事件，{len(user_attr_schema)} 个用户属性")
    print(f"本次检查事件: {len(target_events)} 个")

    # 抓取事件数据
    actual_events: Dict[str, List[dict]] = {}
    for event_name in target_events:
        if event_name not in event_schema:
            print(f"  ⚠️ 事件 [{event_name}] 不在埋点方案中，跳过")
            continue
        print(f"\n  [{event_name}] 采样中...")
        samples = fetch_event_samples(api, event_name, start_date, end_date, limit=args.limit)
        actual_events[event_name] = samples
        print(f"    获取 {len(samples)} 条样本")

    # 抓取用户属性数据
    actual_user_attrs: Dict[str, List[dict]] = {}
    if user_attr_schema:
        print(f"\n📖 用户属性采样中...")
        for attr_name in user_attr_schema:
            samples = fetch_user_attr_samples(api, attr_name, limit=args.limit)
            actual_user_attrs[attr_name] = samples
            print(f"    [{attr_name}] 获取 {len(samples)} 条样本")

    output_data = {
        "meta": {
            "fetch_time": datetime.now().isoformat(),
            "time_range": {"start_date": start_date, "end_date": end_date, "hours": args.hours},
            "cdp_url": cdp_url,
            "project": project,
            "tracking_plan": args.tracking_plan,
        },
        "schema": {
            "events": event_schema,
            "user_attributes": user_attr_schema,
        },
        "actual": {
            "events": actual_events,
            "user_attributes": actual_user_attrs,
        },
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 数据已保存: {output_path}")
    else:
        print("\n" + json.dumps(output_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
