#!/usr/bin/env python3
"""
import_meta_data.py — 从埋点方案 Excel 自动导入元事件和用户属性到神策 CDP

用法：
    python3 tracking-setup-e2e/scripts/import_meta_data.py

前置条件（在项目根目录的 .env 中配置）：
    SA_HOST             神策 CDP 地址
    SA_PROJECT          项目 ID
    API_KEY             神策 Open API 密钥
    TRACKING_PLAN_PATH  埋点方案 Excel 路径

依赖：
    pip install openpyxl python-dotenv requests
"""

import os
import sys
from pathlib import Path

try:
    import openpyxl
    from dotenv import load_dotenv
    import requests
except ImportError:
    print("缺少依赖，请先运行: pip install openpyxl python-dotenv requests")
    sys.exit(1)

# .env 查找顺序：当前目录 → 父目录 → 祖父目录
for _p in [Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent]:
    if (_p / ".env").exists():
        load_dotenv(_p / ".env")
        break

sys.path.insert(0, os.path.dirname(__file__))
from tracking_plan import TrackingPlan
from sa_openapi import SAOpenAPI, map_data_type

SA_HOST = os.getenv("SA_HOST", "").rstrip("/")
SA_PROJECT = os.getenv("SA_PROJECT", "")
API_KEY = os.getenv("API_KEY", "")
TRACKING_PLAN_PATH = os.getenv("TRACKING_PLAN_PATH", "")

# 系统保留字段名（无法创建，自动跳过）
RESERVED_FIELD_NAMES = {"Id", "PersonEmail"}

# 公共属性（神策已内置，无需重复创建）
BUILTIN_FIELD_NAMES = {"platformType", "applicationName", "version"}


def validate_env():
    missing = [
        k
        for k in ["SA_HOST", "SA_PROJECT", "API_KEY", "TRACKING_PLAN_PATH"]
        if not os.getenv(k)
    ]
    if missing:
        print(f"错误：缺少必要配置，请在 .env 中设置：{', '.join(missing)}")
        sys.exit(1)


def import_events(api: SAOpenAPI, plan: TrackingPlan) -> list:
    event_names = plan.list_events()
    custom_events = [n for n in event_names if not n.startswith("$")]
    preset_count = len(event_names) - len(custom_events)
    print(
        f"  发现 {len(event_names)} 个事件，导入 {len(custom_events)} 个自定义事件"
        f"（跳过 {preset_count} 个预置事件）"
    )

    results = []
    for event_name in custom_events:
        print(f"\n  [{event_name}]")
        schema = plan.get_event_schema(event_name)

        # Step 1: 创建元事件
        success = api.create_event(
            original_name=event_name,
            display_name=event_name,
        )
        if not success:
            results.append({"name": event_name, "success": False, "fields": 0})
            continue

        # Step 2: 创建事件属性
        field_descriptors = []
        if schema:
            for prop in schema.properties:
                if (
                    prop.name in RESERVED_FIELD_NAMES
                    or prop.name in BUILTIN_FIELD_NAMES
                ):
                    print(f"    跳过: {prop.name}")
                    continue
                field_descriptors.append(
                    {
                        "schema_name": f"events.{event_name}",
                        "name": prop.name,
                        "display_name": prop.name,
                        "data_type": map_data_type(prop.value_type),
                    }
                )

        if field_descriptors:
            r = api.batch_create_fields(field_descriptors)
            total = len(field_descriptors)
            ok_n = len(r["ok"])
            fail_n = len(r["failed"])
            print(
                f"  ✓ 事件已创建，属性: {ok_n}/{total} 成功"
                + (f"，{fail_n} 失败" if fail_n else "")
            )
            for fname in r["failed"]:
                print(f"    ✗ {fname}")
        else:
            print(f"  ✓ 事件已创建（无自定义属性）")

        results.append(
            {
                "name": event_name,
                "success": True,
                "fields": len(field_descriptors),
            }
        )

    return results


def import_user_attrs(api: SAOpenAPI, plan: TrackingPlan) -> dict:
    user_attrs = plan.get_user_attributes()
    if not user_attrs:
        print("  未找到用户属性，跳过")
        return {}

    print(f"  发现 {len(user_attrs)} 个属性")
    ok, failed = [], []
    for attr in user_attrs:
        if attr.name in RESERVED_FIELD_NAMES or attr.name in BUILTIN_FIELD_NAMES:
            print(f"  跳过: {attr.name}")
            continue
        success = api.create_user_field(
            name=attr.name,
            display_name=attr.name,
            data_type=map_data_type(attr.value_type),
        )
        if success:
            ok.append(attr.name)
        else:
            failed.append(attr.name)

    print(f"  新增/已存在: {len(ok)}  失败: {len(failed)}")
    for name in failed:
        print(f"    ✗ {name}")
    return {"ok": ok, "failed": failed}


def main():
    validate_env()

    excel_path = Path(TRACKING_PLAN_PATH)
    if not excel_path.exists():
        print(f"错误：找不到埋点方案文件：{excel_path}")
        sys.exit(1)

    print(f"=== 神策 CDP 元数据导入 ===")
    print(f"文件: {excel_path.name}")
    print(f"目标: {SA_HOST}  项目: {SA_PROJECT}\n")

    api = SAOpenAPI(SA_HOST, API_KEY, SA_PROJECT)
    plan = TrackingPlan(str(excel_path))

    # ── 元事件 ──
    print("── 元事件导入 ──")
    event_results = import_events(api, plan)

    # ── 用户属性 ──
    print("\n── 用户属性导入 ──")
    user_result = import_user_attrs(api, plan)

    # ── 汇总 ──
    print("\n=== 导入完成 ===")
    if event_results:
        ok_n = sum(1 for e in event_results if e["success"])
        print(f"元事件: {ok_n}/{len(event_results)} 成功")
    if user_result:
        print(
            f"用户属性: {len(user_result.get('ok', []))} 成功，"
            f"{len(user_result.get('failed', []))} 失败"
        )


if __name__ == "__main__":
    main()
