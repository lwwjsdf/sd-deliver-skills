#!/usr/bin/env python3
"""
validate_post_import.py — 导入后数据完整性抽样校验

通过 OpenAPI 查询 CDP 实际数据，抽样检查属性完整性、枚举值合规性等。

用法：
    python3 validate_post_import.py \
        --cdp-url https://demo.sensorsdata.cn \
        --project uat \
        --api-key "#K-xxx" \
        --events "OrderPaid,ProductViewed" \
        --properties "amount,pay_method,product_id" \
        --sample-size 100 \
        --start-date 2024-01-01 \
        --end-date 2024-01-31
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from config_helper import get_config

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared", "postman"))
from sensors_openapi import SensorsOpenAPI


def validate_event_properties(
    api: SensorsOpenAPI,
    event_name: str,
    properties: list,
    start_date: str,
    end_date: str,
    sample_size: int = 100,
) -> dict:
    """校验单个事件的属性完整性和类型。"""
    print(f"\n  📊 校验事件: {event_name}")
    
    # 查询属性样本
    samples = api.query_event_properties_sample(
        event_name=event_name,
        property_names=properties,
        start_date=start_date,
        end_date=end_date,
        sample_size=sample_size,
    )
    
    if not samples:
        return {
            "event": event_name,
            "status": "❌ 未找到数据",
            "sample_count": 0,
            "property_completeness": {},
            "issues": ["CDP 中未查询到该事件数据"],
        }
    
    # 计算属性完整率
    total = len(samples)
    completeness = {}
    issues = []
    
    for prop in properties:
        present_count = sum(1 for s in samples if s.get(prop) is not None and s.get(prop) != "")
        rate = present_count / total if total > 0 else 0
        completeness[prop] = {
            "present": present_count,
            "total": total,
            "rate": f"{rate:.1%}",
        }
        if rate < 0.9:  # 完整率低于 90% 告警
            issues.append(f"属性 {prop} 完整率过低: {rate:.1%} ({present_count}/{total})")
    
    # 检查数值类型（简单启发式）
    for prop in properties:
        values = [s.get(prop) for s in samples if s.get(prop) is not None]
        if not values:
            continue
        # 检查是否应该是数值但包含了非数值
        numeric_count = sum(1 for v in values if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit()))
        if numeric_count > 0 and numeric_count < len(values):
            issues.append(f"属性 {prop} 类型不一致: 包含数值和非数值")
    
    status = "✅ 通过" if not issues else "⚠️ 有问题"
    
    return {
        "event": event_name,
        "status": status,
        "sample_count": total,
        "property_completeness": completeness,
        "issues": issues,
    }


def validate_enum_values(
    api: SensorsOpenAPI,
    event_name: str,
    property_name: str,
    allowed_values: list,
    start_date: str,
    end_date: str,
    top_n: int = 20,
) -> dict:
    """校验属性枚举值是否在允许范围内。"""
    print(f"\n  📋 校验枚举值: {event_name}.{property_name}")
    
    distribution = api.query_property_distribution(
        event_name=event_name,
        property_name=property_name,
        start_date=start_date,
        end_date=end_date,
        top_n=top_n,
    )
    
    if not distribution:
        return {
            "event": event_name,
            "property": property_name,
            "status": "❌ 未找到数据",
            "invalid_values": [],
            "issues": ["CDP 中未查询到该属性数据"],
        }
    
    # 检查是否有不在允许列表中的值
    invalid_values = []
    for value, count in distribution.items():
        if value not in allowed_values:
            invalid_values.append({"value": value, "count": count})
    
    issues = []
    if invalid_values:
        issues.append(f"发现 {len(invalid_values)} 个非法枚举值")
    
    status = "✅ 通过" if not invalid_values else "⚠️ 有非法值"
    
    return {
        "event": event_name,
        "property": property_name,
        "status": status,
        "distribution": distribution,
        "invalid_values": invalid_values,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(
        description="导入后数据完整性抽样校验（基于 OpenAPI）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 校验 OrderPaid 事件的属性完整性
  python3 %(prog)s \
    --cdp-url https://demo.sensorsdata.cn \
    --project uat \
    --api-key "#K-xxx" \
    --events "OrderPaid" \
    --properties "amount,pay_method,product_id" \
    --sample-size 100

  # 校验枚举值
  python3 %(prog)s \
    --cdp-url https://demo.sensorsdata.cn \
    --project uat \
    --api-key "#K-xxx" \
    --events "OrderPaid" \
    --properties "pay_method" \
    --enum-values "wechat,alipay,card" \
    --sample-size 100
        """,
    )
    parser.add_argument("--cdp-url", dest="cdp_url", default="",
                        help="神策 CDP 地址")
    parser.add_argument("--project", dest="project", default="",
                        help="项目 ID（sensorsdata-project header 的值）")
    parser.add_argument("--api-key", dest="api_key", default="",
                        help="Open API 密钥")
    parser.add_argument("--events", dest="events", required=True,
                        help="要校验的事件名，逗号分隔，如 'OrderPaid,ProductViewed'")
    parser.add_argument("--properties", dest="properties", required=True,
                        help="要校验的属性名，逗号分隔，如 'amount,pay_method'")
    parser.add_argument("--sample-size", dest="sample_size", type=int, default=100,
                        help="抽样条数（默认 100，最大 1000）")
    parser.add_argument("--start-date", dest="start_date", default="",
                        help="查询开始日期（YYYY-MM-DD），默认 7 天前")
    parser.add_argument("--end-date", dest="end_date", default="",
                        help="查询结束日期（YYYY-MM-DD），默认今天")
    parser.add_argument("--enum-values", dest="enum_values", default="",
                        help="枚举值允许列表，逗号分隔（如 'wechat,alipay,card'）")
    parser.add_argument("--output", dest="output", default="",
                        help="输出报告文件路径（默认输出到控制台）")
    args = parser.parse_args()

    print("=== 导入后数据完整性校验 ===")

    cdp_url = get_config("cdp_url", args.cdp_url)
    project = get_config("project", args.project)
    api_key = get_config("api_key", args.api_key)

    # 日期范围
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = args.start_date or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"\n📅 查询时间范围: {start_date} ~ {end_date}")
    print(f"🔗 CDP: {cdp_url}  项目: {project}")

    api = SensorsOpenAPI(cdp_url, api_key, project)

    events = [e.strip() for e in args.events.split(",")]
    properties = [p.strip() for p in args.properties.split(",")]
    enum_values = [v.strip() for v in args.enum_values.split(",")] if args.enum_values else []

    results = []

    # 1. 属性完整性校验
    for event_name in events:
        result = validate_event_properties(
            api=api,
            event_name=event_name,
            properties=properties,
            start_date=start_date,
            end_date=end_date,
            sample_size=args.sample_size,
        )
        results.append(result)

    # 2. 枚举值校验（如果提供了允许列表）
    if enum_values and len(properties) == 1:
        for event_name in events:
            result = validate_enum_values(
                api=api,
                event_name=event_name,
                property_name=properties[0],
                allowed_values=enum_values,
                start_date=start_date,
                end_date=end_date,
            )
            results.append(result)

    # 输出报告
    report = {
        "校验时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CDP": cdp_url,
        "项目": project,
        "时间范围": f"{start_date} ~ {end_date}",
        "抽样大小": args.sample_size,
        "校验事件": events,
        "校验属性": properties,
        "结果": results,
    }

    print("\n" + "="*65)
    print("📊 校验结果汇总")
    print("="*65)
    
    all_passed = True
    for r in results:
        print(f"\n{r['status']} {r.get('event', '')} {r.get('property', '')}")
        if r.get("issues"):
            for issue in r["issues"]:
                print(f"   ⚠️ {issue}")
            all_passed = False

    if all_passed:
        print("\n✅ 所有校验通过！")
    else:
        print("\n⚠️ 部分校验未通过，请检查上方问题项")

    # 保存报告
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📝 报告已保存: {args.output}")
    else:
        # 默认保存到 reports 目录
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        report_file = reports_dir / f"post_import_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📝 报告已保存: {report_file}")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
