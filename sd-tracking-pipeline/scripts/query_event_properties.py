#!/usr/bin/env python3
"""
query_event_properties.py — 查询 CDP 中事件的属性分布

用于验证历史反馈问题是否已修复，或检查属性值分布是否符合预期。

用法：
    python3 query_event_properties.py \
        --cdp-url https://demo.sensorsdata.cn \
        --project uat \
        --api-key "#K-xxx" \
        --event "OrderPaid" \
        --property "amount" \
        --sample-size 50

    # 查询枚举值分布
    python3 query_event_properties.py \
        --cdp-url https://demo.sensorsdata.cn \
        --project uat \
        --api-key "#K-xxx" \
        --event "OrderPaid" \
        --property "pay_method" \
        --distribution \
        --top-n 10
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from config_helper import get_config

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared", "postman"))
from sensors_openapi import SensorsOpenAPI


def main():
    parser = argparse.ArgumentParser(
        description="查询 CDP 中事件的属性分布",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查询 amount 属性的样本值
  python3 %(prog)s --event "OrderPaid" --property "amount" --sample-size 50

  # 查询 pay_method 的枚举值分布
  python3 %(prog)s --event "OrderPaid" --property "pay_method" --distribution --top-n 10
        """,
    )
    parser.add_argument("--cdp-url", dest="cdp_url", default="",
                        help="神策 CDP 地址")
    parser.add_argument("--project", dest="project", default="",
                        help="项目 ID（sensorsdata-project header 的值）")
    parser.add_argument("--api-key", dest="api_key", default="",
                        help="Open API 密钥")
    parser.add_argument("--event", dest="event", required=True,
                        help="事件名")
    parser.add_argument("--property", dest="property", required=True,
                        help="属性名")
    parser.add_argument("--sample-size", dest="sample_size", type=int, default=50,
                        help="抽样条数（默认 50，最大 1000）")
    parser.add_argument("--start-date", dest="start_date", default="",
                        help="查询开始日期（YYYY-MM-DD），默认 7 天前")
    parser.add_argument("--end-date", dest="end_date", default="",
                        help="查询结束日期（YYYY-MM-DD），默认今天")
    parser.add_argument("--distribution", action="store_true",
                        help="查询属性值分布（枚举值统计）")
    parser.add_argument("--top-n", dest="top_n", type=int, default=20,
                        help="分布查询时返回最常见的 N 个值（默认 20）")
    args = parser.parse_args()

    cdp_url = get_config("cdp_url", args.cdp_url)
    project = get_config("project", args.project)
    api_key = get_config("api_key", args.api_key)

    # 日期范围
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = args.start_date or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"📅 查询时间范围: {start_date} ~ {end_date}")
    print(f"🔗 CDP: {cdp_url}  项目: {project}")
    print(f"🔍 事件: {args.event}  属性: {args.property}")

    api = SensorsOpenAPI(cdp_url, api_key, project)

    if args.distribution:
        # 查询分布
        print(f"\n📊 查询属性值分布（Top {args.top_n}）...")
        distribution = api.query_property_distribution(
            event_name=args.event,
            property_name=args.property,
            start_date=start_date,
            end_date=end_date,
            top_n=args.top_n,
        )
        
        if not distribution:
            print("❌ 未查询到数据")
            sys.exit(1)
        
        print(f"\n{'值':<30} {'次数':>10} {'占比':>8}")
        print("-" * 50)
        total = sum(distribution.values())
        for value, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            value_str = str(value)[:28]
            print(f"{value_str:<30} {count:>10} {pct:>7.1f}%")
        print(f"{'合计':<30} {total:>10} {100.0:>7.1f}%")
    else:
        # 查询样本
        print(f"\n📋 查询属性样本（{args.sample_size} 条）...")
        samples = api.query_event_properties_sample(
            event_name=args.event,
            property_names=[args.property],
            start_date=start_date,
            end_date=end_date,
            sample_size=args.sample_size,
        )
        
        if not samples:
            print("❌ 未查询到数据")
            sys.exit(1)
        
        print(f"\n{'#':<5} {'值':<40} {'类型':<10}")
        print("-" * 60)
        for i, sample in enumerate(samples[:20], 1):  # 只显示前 20 条
            value = sample.get(args.property, "N/A")
            value_type = type(value).__name__
            value_str = str(value)[:38]
            print(f"{i:<5} {value_str:<40} {value_type:<10}")
        
        if len(samples) > 20:
            print(f"... 共 {len(samples)} 条，显示前 20 条")
        
        # 类型统计
        type_counter = {}
        for sample in samples:
            value = sample.get(args.property)
            t = type(value).__name__
            type_counter[t] = type_counter.get(t, 0) + 1
        
        print(f"\n📊 类型分布:")
        for t, count in sorted(type_counter.items(), key=lambda x: x[1], reverse=True):
            print(f"   {t}: {count} ({count/len(samples)*100:.1f}%)")


if __name__ == "__main__":
    main()
