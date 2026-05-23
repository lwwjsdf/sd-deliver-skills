#!/usr/bin/env python3
"""
import_meta_data.py — 从埋点方案 Excel 自动导入元事件和用户属性到神策 CDP

用法：
    # 方式1：命令行参数（推荐）
    python3 tracking-setup-e2e/scripts/import_meta_data.py \
        --cdp-url https://demo.sensorsdata.cn \
        --project default \
        --api-key xxx \
        --tracking-plan ./plan.xlsx

    # 方式2：交互式提示（未传参时自动提示）
    python3 tracking-setup-e2e/scripts/import_meta_data.py

    # 方式3：使用 .env 配置
    python3 tracking-setup-e2e/scripts/import_meta_data.py

依赖：
    pip install openpyxl python-dotenv requests
"""

import argparse
import getpass
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

# 系统保留字段名（无法创建，自动跳过）
RESERVED_FIELD_NAMES = {"Id", "PersonEmail"}

# 公共属性（神策已内置，无需重复创建）
BUILTIN_FIELD_NAMES = {"platformType", "applicationName", "version"}


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

CONFIG_PROMPTS = {
    "cdp_url": {
        "env_key": "SA_HOST",
        "prompt": "CDP 地址",
        "example": "https://demo.sensorsdata.cn",
        "help": "神策 CDP 控制台地址，登录后在浏览器地址栏看到",
    },
    "project": {
        "env_key": "SA_PROJECT",
        "prompt": "项目 ID",
        "example": "default",
        "help": "登录神策后 URL 中 project= 后面的值",
    },
    "api_key": {
        "env_key": "API_KEY",
        "prompt": "Open API 密钥",
        "example": "#K-jHllJkcPOMeRke3Vi5Nokeuc1MDlRZls",
        "help": "神策后台 → 系统管理 → API 密钥 → 创建密钥",
        "secret": True,
    },
    "tracking_plan": {
        "env_key": "TRACKING_PLAN_PATH",
        "prompt": "埋点方案路径",
        "example": "./refrences/tracking-plan.xlsx",
        "help": "埋点方案 Excel 文件的路径",
    },
}


def get_config_value(key: str, args_value: str = "", interactive: bool = True) -> str:
    """Get config value with priority: args > env > interactive prompt > error"""
    config = CONFIG_PROMPTS[key]
    env_key = config["env_key"]

    # Priority 1: command line argument
    if args_value:
        return args_value

    # Priority 2: environment variable
    env_value = os.getenv(env_key, "")
    if env_value:
        return env_value

    # Priority 3: interactive prompt
    if interactive and sys.stdin.isatty():
        print(f"\n{config['prompt']}:")
        print(f"  示例: {config['example']}")
        print(f"  获取: {config['help']}")

        if config.get("secret"):
            value = getpass.getpass("  请输入: ").strip()
        else:
            value = input("  请输入: ").strip()

        if value:
            return value

    # Priority 4: error
    print(f"\n❌ 错误：缺少 {config['prompt']}")
    print(f"  请通过以下方式之一提供：")
    print(f"  1. 命令行参数: --{key.replace('_', '-')} <值>")
    print(f"  2. 环境变量: {env_key}=<值>")
    print(f"  3. .env 文件: {env_key}=<值>")
    print(f"  4. 交互式提示（直接运行脚本）")
    print(f"\n  示例值: {config['example']}")
    print(f"  获取方式: {config['help']}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------


def test_api_connection(cdp_url: str, api_key: str, project: str) -> bool:
    """Test API connectivity before import to fail fast."""
    try:
        api = SAOpenAPI(cdp_url, api_key, project)
        events = api.list_events()
        print(f"✓ API 连接成功，系统中已有 {len(events)} 个事件")
        return True
    except Exception as e:
        print(f"\n❌ API 连接失败: {e}")
        print("\n可能原因：")
        print("  1. API 密钥错误 - 请确认使用的是 Open API 密钥")
        print("     获取位置：神策后台 → 系统管理 → API 密钥")
        print("  2. CDP 地址错误 - 请确认是控制台地址（不是数据接收地址）")
        print("  3. 网络问题 - 请检查能否访问神策环境")
        print("\n当前配置：")
        print(f"  CDP 地址: {cdp_url}")
        print(f"  项目 ID:  {project}")
        print(
            f"  API 密钥: {api_key[:10]}..."
            if len(api_key) > 10
            else f"  API 密钥: {api_key}"
        )
        return False


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


def confirm_import(
    excel_path: Path, plan: TrackingPlan, cdp_url: str, project: str
) -> bool:
    """二次确认导入内容"""
    event_names = plan.list_events()
    custom_events = [n for n in event_names if not n.startswith("$")]
    user_attrs = plan.get_user_attributes()

    print("\n" + "=" * 60)
    print("📋 导入确认")
    print("=" * 60)
    print(f"目标环境: {cdp_url}")
    print(f"项目:     {project}")
    print(f"文件:     {excel_path.name}")
    print(f"\n即将导入:")
    print(f"  • 自定义事件: {len(custom_events)} 个")
    print(f"  • 用户属性:   {len(user_attrs)} 个")

    if custom_events:
        print(f"\n事件列表 (前10个):")
        for name in custom_events[:10]:
            print(f"    - {name}")
        if len(custom_events) > 10:
            print(f"    ... 等共 {len(custom_events)} 个")

    print("\n" + "=" * 60)

    while True:
        choice = input("确认导入以上元数据? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no", ""):
            print("❌ 已取消导入")
            return False
        else:
            print("请输入 y 或 n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="从埋点方案 Excel 导入元事件和用户属性到神策 CDP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用命令行参数
  python3 %(prog)s --cdp-url https://demo.sensorsdata.cn --project default --api-key xxx --tracking-plan ./plan.xlsx

  # 使用 .env 配置（无需传参）
  python3 %(prog)s

  # 交互式提示（未传参时自动提示）
  python3 %(prog)s
        """,
    )

    parser.add_argument(
        "--cdp-url",
        dest="cdp_url",
        default="",
        help="神策 CDP 地址，示例：https://demo.sensorsdata.cn",
    )
    parser.add_argument(
        "--project",
        dest="project",
        default="",
        help="项目 ID，示例：default",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default="",
        help="Open API 密钥，示例：#K-jHllJkcPOMeRke3Vi5Nokeuc1MDlRZls",
    )
    parser.add_argument(
        "--tracking-plan",
        dest="tracking_plan",
        default="",
        help="埋点方案 Excel 路径，示例：./refrences/tracking-plan.xlsx",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="跳过确认提示，直接导入",
    )

    args = parser.parse_args()

    print("=== 神策 CDP 元数据导入 ===")

    # Get configuration
    cdp_url = get_config_value("cdp_url", args.cdp_url)
    project = get_config_value("project", args.project)
    api_key = get_config_value("api_key", args.api_key)
    tracking_plan_path = get_config_value("tracking_plan", args.tracking_plan)

    excel_path = Path(tracking_plan_path)
    if not excel_path.exists():
        print(f"\n❌ 错误：找不到埋点方案文件：{excel_path}")
        print(f"  请确认路径是否正确")
        print(f"  示例: ./refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx")
        sys.exit(1)

    # Step 1: Test API connectivity
    print("\n🔍 检查 API 连接...")
    if not test_api_connection(cdp_url, api_key, project):
        sys.exit(1)

    # Step 2: Parse tracking plan
    print("\n📖 解析埋点方案...")
    plan = TrackingPlan(str(excel_path))

    event_names = plan.list_events()
    custom_events = [n for n in event_names if not n.startswith("$")]
    user_attrs = plan.get_user_attributes()

    print(f"  发现 {len(custom_events)} 个自定义事件")
    print(f"  发现 {len(user_attrs)} 个用户属性")

    if not custom_events and not user_attrs:
        print("\n❌ 错误：未能从 Excel 中解析到任何事件或属性")
        print("可能原因：")
        print("  1. Sheet 名称不匹配 - 请检查 Excel 中的 sheet 名是否为以下之一：")
        print("     自定义事件: Events / Custom Event / Event")
        print("     用户属性: Users / User Attribute / User Traits")
        print("  2. Excel 格式错误 - 请确认是标准的埋点方案模板")
        print(
            f"\n实际 sheet 名称: {', '.join(openpyxl.load_workbook(excel_path, data_only=True).sheetnames)}"
        )
        sys.exit(1)

    api = SAOpenAPI(cdp_url, api_key, project)

    # Step 3: Confirm import
    if not args.yes:
        if not confirm_import(excel_path, plan, cdp_url, project):
            sys.exit(0)

    print(f"\n目标: {cdp_url}  项目: {project}\n")

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
