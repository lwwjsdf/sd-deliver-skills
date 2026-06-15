#!/usr/bin/env python3
"""
import_mock_data.py — 将生成的模拟数据导入神策 CDP（使用官方 SDK）

用法：
    # 方式1：命令行参数（推荐）
    python tracking-setup-e2e/scripts/import_mock_data.py \
        --data-url https://demo.sensorsdata.cn/sa?project=default \
        --jsonl ./mock_data/westk.jsonl

    # 方式2：交互式提示（未传参时自动提示）
    python tracking-setup-e2e/scripts/import_mock_data.py

    # 方式3：使用 .env 配置
    python tracking-setup-e2e/scripts/import_mock_data.py

依赖：
    pip install python-dotenv SensorsAnalyticsSDK
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

try:
    import sensorsanalytics
except ImportError:
    print("缺少依赖，请先运行: pip install python-dotenv SensorsAnalyticsSDK")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from config_helper import get_config


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------


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


def confirm_import(batch_info: dict, batch_file: str, data_url: str) -> bool:
    """二次确认导入内容"""
    print("\n" + "=" * 60)
    print("📋 导入确认")
    print("=" * 60)
    print(f"目标环境: {data_url}")
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


def import_data(batch_file: str, data_url: str, skip_confirm: bool = False):
    """导入 batch 数据到神策"""
    if not Path(batch_file).exists():
        print(f"错误：找不到数据文件：{batch_file}")
        sys.exit(1)

    print(f"=== 数据导入 ===")
    print(f"文件: {batch_file}")
    print(f"目标: {data_url}")

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
    if not skip_confirm and not confirm_import(batch_info, batch_file, data_url):
        sys.exit(0)

    # 使用 BatchConsumer 批量发送（每 100 条批量发送）
    consumer = sensorsanalytics.BatchConsumer(data_url, max_size=100)
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
                    profiles=record.get("properties", {}),
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="将模拟数据导入神策 CDP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用命令行参数
  python3 %(prog)s --data-url https://demo.sensorsdata.cn/sa?project=default --jsonl ./mock_data/westk.jsonl

  # 使用 .env 配置（无需传参）
  python3 %(prog)s

  # 交互式提示（未传参时自动提示）
  python3 %(prog)s
        """,
    )

    parser.add_argument(
        "--data-url",
        dest="data_url",
        default="",
        help="数据接收地址，示例：https://demo.sensorsdata.cn/sa?project=default",
    )
    parser.add_argument(
        "--jsonl",
        dest="jsonl",
        default="",
        help="JSONL 数据文件路径，示例：./mock_data/westk.jsonl",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="跳过确认提示，直接导入",
    )

    args = parser.parse_args()

    # Get configuration
    data_url = get_config("data_url", args.data_url)

    # Find jsonl file
    if args.jsonl:
        batch_file = args.jsonl
    else:
        # 查找最新的 jsonl 文件
        mock_data_dir = Path(__file__).parent.parent / "mock_data"
        jsonl_files = sorted(
            mock_data_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if not jsonl_files:
            print(
                "错误：找不到 jsonl 数据文件，请先运行 generate_mock_data.py 生成数据"
            )
            sys.exit(1)

        batch_file = str(jsonl_files[0])

    import_data(batch_file, data_url, skip_confirm=args.yes)


if __name__ == "__main__":
    main()
