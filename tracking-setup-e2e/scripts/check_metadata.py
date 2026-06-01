#!/usr/bin/env python3
"""
check_metadata.py — 导入前检查 CDP 中是否已创建所需元数据

在执行 import_mock_data.py 之前运行，确保 CDP 开启强校验时不会因元数据缺失导致导入失败。

用法：
    python3 tracking-setup-e2e/scripts/check_metadata.py \
        --cdp-url https://demo.sensorsdata.cn \
        --project default \
        --api-key "#K-xxx" \
        --jsonl ./mock_data/westk.jsonl
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from config_helper import get_config

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared", "postman"))
from sensors_openapi import SensorsOpenAPI

# SDK 内置的系统属性，不需要在元数据中创建
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
    "$traffic_source_type",
}


def _parse_jsonl_events(jsonl_file: str) -> dict:
    """返回 {event_name: set_of_custom_props}，只含自定义事件。"""
    events: dict[str, set] = defaultdict(set)
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
            props = record.get("properties", {})
            custom_props = {k for k in props if k not in _SYSTEM_PROPS}
            events[event_name].update(custom_props)
    return dict(events)


def check_metadata(cdp_url: str, project: str, api_key: str, jsonl_file: str) -> bool:
    """
    检查 JSONL 中所有自定义事件及其属性是否已在 CDP 中创建。
    返回 True 表示全部通过，False 表示有缺失。
    """
    print(f"\n🔍 解析数据文件: {Path(jsonl_file).name}")
    events_in_data = _parse_jsonl_events(jsonl_file)

    if not events_in_data:
        print("  ℹ️  未找到自定义事件（只有预置事件或 profile_set），跳过检查")
        return True

    print(f"  发现 {len(events_in_data)} 个自定义事件，"
          f"{sum(len(v) for v in events_in_data.values())} 个自定义属性")

    print(f"\n🔗 连接 CDP: {cdp_url}  项目: {project}")
    api = SensorsOpenAPI(cdp_url, api_key, project)

    try:
        existing_list = api.list_events()
        existing_events = {e["original_name"] for e in existing_list}
        print(f"  CDP 中已有 {len(existing_events)} 个事件")
    except Exception as e:
        print(f"  ❌ 获取事件列表失败: {e}")
        return False

    missing_events = []
    missing_props: dict[str, list] = {}
    ok_events = []

    for event_name in sorted(events_in_data):
        props = events_in_data[event_name]
        if event_name not in existing_events:
            missing_events.append(event_name)
            continue

        try:
            fields_resp = api.list_event_fields(f"events.{event_name}")
            existing_fields = {
                f["name"]
                for f in fields_resp.get("data", {}).get("fields", [])
            }
            missing = sorted(props - existing_fields)
            if missing:
                missing_props[event_name] = missing
            else:
                ok_events.append(event_name)
        except Exception as e:
            print(f"  ⚠️  获取事件 [{event_name}] 属性失败: {e}")

    print(f"\n{'='*60}")
    print("📊 元数据检查结果")
    print(f"{'='*60}")

    if not missing_events and not missing_props:
        print(f"✅ 全部通过！{len(ok_events)} 个事件的元数据均已在 CDP 中创建")
        return True

    if missing_events:
        print(f"\n❌ 缺少事件 ({len(missing_events)} 个):")
        for name in missing_events:
            print(f"   - {name}")
        print("   → 请先运行 import_meta_data.py 创建这些事件")

    if missing_props:
        total_missing = sum(len(v) for v in missing_props.values())
        print(f"\n⚠️  缺少属性 ({total_missing} 个):")
        for event_name, props in missing_props.items():
            print(f"   [{event_name}]")
            for p in props:
                print(f"     - {p}")
        print("   → 请先运行 import_meta_data.py 补充这些属性")

    print(f"\n{'='*60}")
    print("⛔ 检查未通过，建议先完成元数据导入再导入数据")
    print("   若 CDP 未开启强校验，可忽略此警告继续导入")
    print(f"{'='*60}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="导入前检查 CDP 中是否已创建所需元数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 %(prog)s \\
    --cdp-url https://demo.sensorsdata.cn \\
    --project default \\
    --api-key "#K-xxx" \\
    --jsonl ./mock_data/westk.jsonl
        """,
    )
    parser.add_argument("--cdp-url", dest="cdp_url", default="",
                        help="神策 CDP 地址，示例：https://demo.sensorsdata.cn")
    parser.add_argument("--project", dest="project", default="",
                        help="项目 ID，示例：default")
    parser.add_argument("--api-key", dest="api_key", default="",
                        help="Open API 密钥")
    parser.add_argument("--jsonl", dest="jsonl", default="",
                        help="JSONL 数据文件路径")
    parser.add_argument("--warn-only", action="store_true",
                        help="有缺失时只警告，不以非零退出码退出")
    args = parser.parse_args()

    print("=== 元数据预检查 ===")

    cdp_url = get_config("cdp_url", args.cdp_url)
    project = get_config("project", args.project)
    api_key = get_config("api_key", args.api_key)

    if args.jsonl:
        jsonl_file = args.jsonl
    else:
        mock_data_dir = Path(__file__).parent.parent / "mock_data"
        jsonl_files = sorted(
            mock_data_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not jsonl_files:
            print("错误：找不到 jsonl 数据文件，请先运行 generate_mock_data.py")
            sys.exit(1)
        jsonl_file = str(jsonl_files[0])
        print(f"自动选择最新数据文件: {Path(jsonl_file).name}")

    ok = check_metadata(cdp_url, project, api_key, jsonl_file)
    if not ok and not args.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
