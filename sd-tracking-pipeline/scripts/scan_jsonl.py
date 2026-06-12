#!/usr/bin/env python3
"""
scan_jsonl.py — 快速扫描 JSONL 模拟数据文件，输出结构化元信息。

用于 Agent 在数据校验前快速了解数据概况，无需现场写 Python。

用法：
    python3 scan_jsonl.py --jsonl ./mock_data/westk.jsonl
    python3 scan_jsonl.py --jsonl ./mock_data/westk.jsonl --sample 1000
    python3 scan_jsonl.py --pattern './mock_data/westk_1k_part_*'
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from config_helper import get_config


def _iter_records(files: List[str]):
    """Yield records from one or more JSONL files."""
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def scan_jsonl(
    files: List[str],
    sample_size: Optional[int] = None,
    include_preset: bool = True,
) -> Dict:
    """
    Scan JSONL files and return a structured summary.

    Returns:
        {
            "files": [...],
            "total_rows": int,
            "record_types": {"track": ..., "profile_set": ...},
            "events": {
                "event_name": {
                    "count": int,
                    "sample_properties": ["prop1", "prop2", ...],
                    "property_samples": {"prop1": {"value": count, ...}},
                }
            },
            "users": {"distinct_ids": int, "sample": [...]},
            "time_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
        }
    """
    total_rows = 0
    record_types: Counter = Counter()
    event_counts: Counter = Counter()
    event_props: Dict[str, set] = defaultdict(set)
    event_prop_samples: Dict[str, Counter] = defaultdict(Counter)
    distinct_ids: set = set()
    timestamps: List[int] = []

    sampled = 0
    for record in _iter_records(files):
        total_rows += 1
        rtype = record.get("type", "unknown")
        record_types[rtype] += 1

        if sample_size and sampled >= sample_size:
            # Still count totals and collect distinct users/timestamps efficiently
            if rtype == "track":
                event_name = record.get("event", "")
                if include_preset or not event_name.startswith("$"):
                    event_counts[event_name] += 1
            did = record.get("distinct_id")
            if did:
                distinct_ids.add(did)
            ts = _extract_timestamp(record)
            if ts:
                timestamps.append(ts)
            continue

        sampled += 1

        did = record.get("distinct_id")
        if did:
            distinct_ids.add(did)

        ts = _extract_timestamp(record)
        if ts:
            timestamps.append(ts)

        if rtype == "track":
            event_name = record.get("event", "")
            if include_preset or not event_name.startswith("$"):
                event_counts[event_name] += 1
                props = record.get("properties", {})
                for k, v in props.items():
                    event_props[event_name].add(k)
                    # Limit sample values per property to avoid huge output
                    if len(event_prop_samples[(event_name, k)]) < 20:
                        event_prop_samples[(event_name, k)][str(v)[:100]] += 1

    events = {}
    for event_name, count in event_counts.most_common():
        prop_samples = {}
        for prop in sorted(event_props[event_name]):
            key = (event_name, prop)
            prop_samples[prop] = dict(event_prop_samples[key].most_common(10))
        events[event_name] = {
            "count": count,
            "sample_properties": sorted(event_props[event_name]),
            "property_samples": prop_samples,
        }

    time_range = {}
    if timestamps:
        import datetime

        time_range = {
            "start": datetime.datetime.utcfromtimestamp(min(timestamps)).strftime("%Y-%m-%d %H:%M:%S"),
            "end": datetime.datetime.utcfromtimestamp(max(timestamps)).strftime("%Y-%m-%d %H:%M:%S"),
        }

    user_sample = sorted(list(distinct_ids))[:10]

    return {
        "files": files,
        "total_rows": total_rows,
        "record_types": dict(record_types),
        "events": events,
        "users": {
            "distinct_id_count": len(distinct_ids),
            "sample": user_sample,
        },
        "time_range": time_range,
    }


def _extract_timestamp(record: dict) -> Optional[int]:
    """Extract timestamp in seconds from a record."""
    ts = record.get("time") or record.get("properties", {}).get("$time")
    if not ts:
        return None
    try:
        ts = int(ts)
    except (ValueError, TypeError):
        return None
    if ts > 1e12:
        ts = ts // 1000
    return ts


def _resolve_files(jsonl: Optional[str], pattern: Optional[str]) -> List[str]:
    """Resolve jsonl file or glob pattern to a list of files."""
    if jsonl:
        if not Path(jsonl).exists():
            print(f"❌ 文件不存在: {jsonl}")
            sys.exit(1)
        return [jsonl]

    if pattern:
        import glob as _glob

        files = sorted(_glob.glob(pattern))
        if not files:
            print(f"❌ 未匹配到文件: {pattern}")
            sys.exit(1)
        return files

    # Default: latest jsonl in mock_data/
    mock_data_dir = Path(__file__).parent.parent / "mock_data"
    jsonl_files = sorted(
        mock_data_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not jsonl_files:
        print("❌ 找不到 jsonl 数据文件，请先运行 generate_mock_data.py 生成数据")
        sys.exit(1)
    return [str(jsonl_files[0])]


def main():
    parser = argparse.ArgumentParser(
        description="快速扫描 JSONL 模拟数据文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 %(prog)s
  python3 %(prog)s --jsonl ./mock_data/westk.jsonl
  python3 %(prog)s --pattern './mock_data/westk_1k_part_*'
  python3 %(prog)s --jsonl ./mock_data/westk.jsonl --sample 1000 --no-preset
        """,
    )
    parser.add_argument("--jsonl", dest="jsonl", default="", help="JSONL 文件路径")
    parser.add_argument("--pattern", dest="pattern", default="", help="文件匹配模式（如 './mock_data/westk_1k_part_*'）")
    parser.add_argument("--sample", dest="sample", type=int, default=None,
                        help="每个事件最多抽样 N 条做属性分析（默认不限制）")
    parser.add_argument("--no-preset", dest="include_preset", action="store_false",
                        help="排除 $MP* / $Web* 等预设事件")
    parser.add_argument("--output-json", dest="output_json", action="store_true",
                        help="输出原始 JSON 而不是 Markdown 摘要")
    args = parser.parse_args()

    files = _resolve_files(args.jsonl or None, args.pattern or None)

    summary = scan_jsonl(files, sample_size=args.sample, include_preset=args.include_preset)

    if args.output_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print("# JSONL 扫描摘要")
    print(f"\n**文件**: {', '.join(Path(f).name for f in files)}")
    print(f"**总记录数**: {summary['total_rows']:,}")
    print(f"**记录类型**: {summary['record_types']}")
    print(f"**Distinct ID 数**: {summary['users']['distinct_id_count']}")
    if summary["time_range"]:
        print(f"**时间范围**: {summary['time_range']['start']} ~ {summary['time_range']['end']}")

    print("\n## 事件分布")
    print("| 事件名 | 条数 | 样例属性 |")
    print("|--------|------|----------|")
    for name, info in summary["events"].items():
        props = ", ".join(info["sample_properties"][:8])
        if len(info["sample_properties"]) > 8:
            props += "..."
        print(f"| {name} | {info['count']:,} | {props} |")

    print("\n## 属性样例（前 3 个事件）")
    for name, info in list(summary["events"].items())[:3]:
        print(f"\n### {name}")
        for prop, samples in list(info["property_samples"].items())[:5]:
            sample_str = ", ".join(f"{k[:30]}({v})" for k, v in list(samples.items())[:3])
            print(f"- `{prop}`: {sample_str}")


if __name__ == "__main__":
    main()
