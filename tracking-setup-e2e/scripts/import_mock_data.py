#!/usr/bin/env python3
"""
import_mock_data.py — 将生成的模拟数据导入神策 CDP（使用官方 SDK）

用法：
    python tracking-setup-e2e/scripts/import_mock_data.py

前置条件（在项目根目录的 .env 中配置）：
    SA_TRACK_URL        神策数据接入 URL
    SA_HOST             神策 CDP 地址（用于校验）
    API_KEY             Open API 密钥（用于校验）
    SA_PROJECT          项目 ID
"""

import os
import sys
import json
import time
from pathlib import Path
from collections import Counter

try:
    from dotenv import load_dotenv
    import sensorsanalytics
except ImportError:
    print("缺少依赖，请先运行: pip install python-dotenv SensorsAnalyticsSDK")
    sys.exit(1)

# .env 查找顺序：当前目录 → 父目录 → 祖父目录 → 脚本所在目录的父目录
for _p in [
    Path.cwd(),
    Path.cwd().parent,
    Path.cwd().parent.parent,
    Path(__file__).parent.parent,
]:
    env_file = _p / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        break

SA_TRACK_URL = os.getenv("SA_TRACK_URL", "")
SA_HOST = os.getenv("SA_HOST", "")
API_KEY = os.getenv("API_KEY", "")
SA_PROJECT = os.getenv("SA_PROJECT", "default")


def validate_env():
    if not SA_TRACK_URL:
        print("❌ 错误：缺少 SA_TRACK_URL 配置，请在 .env 中设置")
        print("\n获取方式：")
        print("  神策后台 → 数据接入 → HTTP API → 复制接入地址")
        print("  格式如：https://<host>/sa?project=<project>")
        sys.exit(1)


def get_batch_info(batch_file: str) -> dict:
    """获取批次信息"""
    records = []
    with open(batch_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # 提取批次标识
    batch_ids = set()
    events = Counter()
    users = set()

    for r in records:
        props = r.get("properties", {})
        if "$batch_id" in props:
            batch_ids.add(props["$batch_id"])
        events[r.get("event", "unknown")] += 1
        users.add(r.get("distinct_id", ""))

    return {
        "total_records": len(records),
        "batch_ids": list(batch_ids),
        "unique_users": len(users),
        "event_types": len(events),
        "top_events": events.most_common(10),
    }


def verify_import(batch_info: dict, timeout: int = 60) -> dict:
    """验证导入结果（通过 Open API 查询）"""
    if not all([SA_HOST, API_KEY, SA_PROJECT]):
        print("⚠️  缺少 Open API 配置，跳过在线验证")
        return {}

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from sa_openapi import SAOpenAPI

        api = SAOpenAPI(SA_HOST, API_KEY, SA_PROJECT)

        # 等待数据写入
        print(f"⏳ 等待数据写入（{timeout}秒）...")
        time.sleep(min(timeout, 5))  # 至少等待 5 秒

        # 查询事件列表
        events = api.list_events()

        # 查询用户属性
        user_fields = api.list_user_fields()

        return {
            "total_events_in_system": len(events),
            "total_user_fields": len(user_fields),
            "status": "verified",
        }
    except Exception as e:
        print(f"⚠️  在线验证失败: {e}")
        return {"status": "failed", "error": str(e)}


def confirm_import(batch_info: dict, batch_file: str) -> bool:
    """二次确认导入内容"""
    print("\n" + "=" * 60)
    print("📋 导入确认")
    print("=" * 60)
    print(f"目标环境: {SA_TRACK_URL}")
    print(f"数据文件: {Path(batch_file).name}")
    print(f"\n即将导入:")
    print(f"  • 总记录数: {batch_info['total_records']} 条")
    print(f"  • 唯一用户: {batch_info['unique_users']} 个")
    print(f"  • 事件类型: {batch_info['event_types']} 种")
    if batch_info["batch_ids"]:
        print(f"  • 批次标识: {', '.join(batch_info['batch_ids'])}")

    print(f"\n事件分布 (前10):")
    for event, count in batch_info["top_events"]:
        print(f"    {event}: {count} 条")

    print("\n⚠️  注意: 重复导入会产生重复数据")
    print("=" * 60)

    while True:
        choice = input("确认导入以上数据? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no", ""):
            print("❌ 已取消导入")
            return False
        else:
            print("请输入 y 或 n")


def import_data(batch_file: str):
    """导入 batch 数据到神策"""
    if not Path(batch_file).exists():
        print(f"错误：找不到数据文件：{batch_file}")
        sys.exit(1)

    print(f"=== 数据导入 ===")
    print(f"文件: {batch_file}")
    print(f"目标: {SA_TRACK_URL}")

    # 获取批次信息
    batch_info = get_batch_info(batch_file)
    print(f"\n📊 批次信息:")
    print(f"  总记录数: {batch_info['total_records']}")
    print(f"  唯一用户: {batch_info['unique_users']}")
    print(f"  事件类型: {batch_info['event_types']}")
    if batch_info["batch_ids"]:
        print(f"  批次标识: {', '.join(batch_info['batch_ids'])}")
    print(f"  事件分布:")
    for event, count in batch_info["top_events"]:
        print(f"    {event}: {count}")

    # 二次确认
    if not confirm_import(batch_info, batch_file):
        sys.exit(0)

    # 使用 BatchConsumer 批量发送（每 100 条批量发送）
    consumer = sensorsanalytics.BatchConsumer(SA_TRACK_URL, max_size=100)
    sa = sensorsanalytics.SensorsAnalytics(consumer, enable_time_free=True)

    # 读取 JSONL 数据
    records = []
    with open(batch_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"\n🚀 开始导入 {len(records)} 条记录...")
    start_time = time.time()

    # 导入数据
    success_count = 0
    error_count = 0
    error_samples = []

    for i, record in enumerate(records):
        try:
            if record["type"] == "track":
                sa.track(
                    distinct_id=record["distinct_id"],
                    event_name=record["event"],
                    properties=record.get("properties", {}),
                    is_login_id=record.get("$is_login_id", True),
                )
                success_count += 1
            elif record["type"] == "profile_set":
                sa.profile_set(
                    distinct_id=record["distinct_id"],
                    properties=record.get("properties", {}),
                )
                success_count += 1
        except Exception as e:
            error_count += 1
            if len(error_samples) < 5:
                error_samples.append(f"第 {i} 条: {e}")

    # 关闭并刷新缓冲区
    sa.close()
    elapsed = time.time() - start_time

    print(f"\n✅ 导入完成:")
    print(f"  成功: {success_count} 条")
    print(f"  失败: {error_count} 条")
    print(f"  耗时: {elapsed:.1f} 秒")
    print(f"  速度: {success_count / elapsed:.0f} 条/秒")

    if error_samples:
        print(f"\n❌ 错误示例:")
        for err in error_samples:
            print(f"  {err}")

    # 验证导入结果
    print(f"\n🔍 验证导入结果...")
    verify_result = verify_import(batch_info)
    if verify_result:
        print(f"  系统中事件总数: {verify_result.get('total_events_in_system', 'N/A')}")
        print(f"  用户属性总数: {verify_result.get('total_user_fields', 'N/A')}")


def main():
    validate_env()

    # 查找最新的 jsonl 文件
    mock_data_dir = Path(__file__).parent.parent / "mock_data"
    jsonl_files = sorted(
        mock_data_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not jsonl_files:
        print("错误：找不到 jsonl 数据文件，请先运行 generate_mock_data.py 生成数据")
        sys.exit(1)

    batch_file = str(jsonl_files[0])
    import_data(batch_file)


if __name__ == "__main__":
    main()
