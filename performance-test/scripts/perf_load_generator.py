#!/usr/bin/env python3
"""
perf_load_generator.py — 神策 CDP HTTP API 数据写入压测脚本

梯度加压：25% → 50% → 75% → 100% → 120%
记录：TPS、错误率、P50/P95/P99 响应时间

用法：
    # 使用 .env 配置
    python3 performance-test/scripts/perf_load_generator.py --jsonl ./mock_data/westk.jsonl

    # 指定目标 TPS
    python3 performance-test/scripts/perf_load_generator.py --jsonl ./mock_data/westk.jsonl --target-tps 5000

    # 自定义梯度
    python3 performance-test/scripts/perf_load_generator.py --jsonl ./mock_data/westk.jsonl --gradients 50 100 150

依赖：
    pip install python-dotenv SensorsAnalyticsSDK
"""

import argparse
import json
import os
import statistics
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tracking-setup-e2e/scripts"))
from config_helper import get_config


try:
    import sensorsanalytics
except ImportError:
    print("缺少依赖，请先运行: pip install python-dotenv SensorsAnalyticsSDK")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class MetricsCollector:
    """线程安全的指标收集器"""

    def __init__(self):
        self._lock = threading.Lock()
        self.latencies: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.success_count = 0
        self.error_count = 0

    def record(self, latency: float, success: bool, error_msg: str = ""):
        with self._lock:
            self.latencies.append(latency)
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
                if error_msg:
                    self.errors.append({"msg": error_msg, "time": time.time()})

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            total = self.success_count + self.error_count
            latencies = sorted(self.latencies)
            n = len(latencies)

            result = {
                "total": total,
                "success": self.success_count,
                "error": self.error_count,
                "error_rate": round(self.error_count / total * 100, 2) if total > 0 else 0,
                "avg_latency_ms": round(statistics.mean(latencies) * 1000, 2) if n > 0 else 0,
                "p50_ms": round(self._percentile(latencies, 0.50) * 1000, 2) if n > 0 else 0,
                "p95_ms": round(self._percentile(latencies, 0.95) * 1000, 2) if n > 0 else 0,
                "p99_ms": round(self._percentile(latencies, 0.99) * 1000, 2) if n > 0 else 0,
                "min_ms": round(min(latencies) * 1000, 2) if n > 0 else 0,
                "max_ms": round(max(latencies) * 1000, 2) if n > 0 else 0,
                "tps": 0,
            }
            return result

    @staticmethod
    def _percentile(sorted_data: List[float], p: float) -> float:
        if not sorted_data:
            return 0
        k = (len(sorted_data) - 1) * p
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        if f == c:
            return sorted_data[f]
        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


# ---------------------------------------------------------------------------
# Load Generator
# ---------------------------------------------------------------------------

def load_records(jsonl_path: str, max_records: int = 0) -> List[Dict]:
    """加载 JSONL 数据"""
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
                if max_records > 0 and len(records) >= max_records:
                    break
    return records


def send_batch(
    data_url: str,
    batch: List[Dict],
    metrics: MetricsCollector,
    enable_time_free: bool = True,
) -> None:
    """发送一批数据并记录指标"""
    consumer = sensorsanalytics.BatchConsumer(data_url, max_size=len(batch))
    sa = sensorsanalytics.SensorsAnalytics(consumer, enable_time_free=enable_time_free)

    start = time.time()
    try:
        for record in batch:
            if record["type"] == "track":
                sa.track(
                    distinct_id=record["distinct_id"],
                    event_name=record["event"],
                    properties=record.get("properties", {}),
                    is_login_id=record.get("$is_login_id", True),
                )
            elif record["type"] == "profile_set":
                sa.profile_set(
                    distinct_id=record["distinct_id"],
                    properties=record.get("properties", {}),
                )
        sa.close()
        latency = time.time() - start
        metrics.record(latency, success=True)
    except Exception as e:
        latency = time.time() - start
        metrics.record(latency, success=False, error_msg=str(e))
    finally:
        try:
            sa.close()
        except Exception:
            pass


def run_gradient(
    data_url: str,
    records: List[Dict],
    gradient_pct: float,
    target_tps: int,
    duration_sec: int,
    workers: int,
    enable_time_free: bool = True,
) -> Dict[str, Any]:
    """执行单个梯度的压测"""

    gradient_tps = int(target_tps * gradient_pct)
    batch_size = max(1, min(100, gradient_tps // 10))
    total_records_needed = gradient_tps * duration_sec

    # 循环使用数据
    cycled_records = []
    while len(cycled_records) < total_records_needed:
        cycled_records.extend(records)
    cycled_records = cycled_records[:total_records_needed]

    # 分批次
    batches = [
        cycled_records[i:i + batch_size]
        for i in range(0, len(cycled_records), batch_size)
    ]

    print(f"\n  梯度 {gradient_pct*100:.0f}%: 目标 TPS={gradient_tps}, 批次={len(batches)}, 批次大小={batch_size}, 持续时间={duration_sec}s")

    metrics = MetricsCollector()
    start_time = time.time()
    interval = 1.0 / gradient_tps if gradient_tps > 0 else 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i, batch in enumerate(batches):
            # 控制发送速率
            expected_time = start_time + i * interval * batch_size
            now = time.time()
            if expected_time > now:
                time.sleep(expected_time - now)

            future = executor.submit(send_batch, data_url, batch, metrics, enable_time_free)
            futures.append(future)

            # 超时检查
            if time.time() - start_time >= duration_sec:
                break

        # 等待所有任务完成或超时
        for future in as_completed(futures):
            try:
                future.result(timeout=30)
            except Exception as e:
                metrics.record(0, success=False, error_msg=f"Future error: {e}")

    elapsed = time.time() - start_time
    summary = metrics.summary()
    summary["target_tps"] = gradient_tps
    summary["actual_tps"] = round(summary["total"] / elapsed, 2) if elapsed > 0 else 0
    summary["duration_sec"] = round(elapsed, 2)
    summary["gradient_pct"] = gradient_pct
    return summary


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(results: List[Dict[str, Any]], target_tps: int) -> None:
    """打印压测报告"""
    print("\n" + "=" * 80)
    print(" 性能压测报告")
    print("=" * 80)
    print(f" 目标峰值 TPS: {target_tps}")
    print()

    headers = ["梯度", "目标TPS", "实际TPS", "总请求", "成功", "失败", "错误率%", "P50(ms)", "P95(ms)", "P99(ms)", "耗时(s)"]
    print(" | ".join(f"{h:>10}" for h in headers))
    print("-" * 120)

    for r in results:
        print(
            f" {r['gradient_pct']*100:>8.0f}% |"
            f" {r['target_tps']:>10} |"
            f" {r['actual_tps']:>10} |"
            f" {r['total']:>10} |"
            f" {r['success']:>10} |"
            f" {r['error']:>10} |"
            f" {r['error_rate']:>10.2f} |"
            f" {r['p50_ms']:>10.2f} |"
            f" {r['p95_ms']:>10.2f} |"
            f" {r['p99_ms']:>10.2f} |"
            f" {r['duration_sec']:>10.2f}"
        )

    print("=" * 80)

    # 结论
    all_pass = all(r["error_rate"] < 1.0 for r in results)
    max_gradient = max(r["gradient_pct"] for r in results)
    max_actual_tps = max(r["actual_tps"] for r in results)

    print(f"\n 结论:")
    if all_pass:
        print(f"   ✅ 所有梯度错误率 < 1%，压测通过")
    else:
        print(f"   ❌ 存在梯度错误率 >= 1%，需排查")
    print(f"   最大加压梯度: {max_gradient*100:.0f}%")
    print(f"   实测最大 TPS: {max_actual_tps}")


def save_report(results: List[Dict[str, Any]], target_tps: int, output_path: str) -> None:
    """保存 JSON 格式报告"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target_tps": target_tps,
        "gradients": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n 报告已保存: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="神策 CDP HTTP API 数据写入压测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Default gradients 25pct 50pct 75pct 100pct 120pct
    python3 perf_load_generator.py --jsonl ./mock_data/westk.jsonl
  Custom target TPS
    python3 perf_load_generator.py --jsonl ./mock_data/westk.jsonl --target-tps 5000
  Custom gradients
    python3 perf_load_generator.py --jsonl ./mock_data/westk.jsonl --gradients 0.5 1.0 1.5
  Shorter duration for quick validation
    python3 perf_load_generator.py --jsonl ./mock_data/westk.jsonl --duration 30
        """,
    )

    parser.add_argument(
        "--jsonl",
        required=True,
        help="JSONL 数据文件路径",
    )
    parser.add_argument(
        "--data-url",
        default="",
        help="数据接收地址（默认从 .env 读取 SA_TRACK_URL）",
    )
    parser.add_argument(
        "--target-tps",
        type=int,
        default=1000,
        help="目标峰值 TPS（默认 1000）",
    )
    parser.add_argument(
        "--gradients",
        type=float,
        nargs="+",
        default=[0.25, 0.50, 0.75, 1.00, 1.20],
        help="加压梯度列表（默认 0.25 0.50 0.75 1.00 1.20）",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="每梯度持续时间（秒，默认 60）",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="并发线程数（默认 8）",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="最大加载记录数（0=不限制）",
    )
    parser.add_argument(
        "--output",
        default="perf_load_report.json",
        help="报告输出路径（默认 perf_load_report.json）",
    )
    parser.add_argument(
        "--no-time-free",
        action="store_true",
        help="禁用 enable_time_free（默认启用）",
    )

    args = parser.parse_args()

    # 获取配置
    data_url = get_config("data_url", args.data_url)

    # 加载数据
    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        print(f"❌ 错误：找不到数据文件: {jsonl_path}")
        sys.exit(1)

    print(f"=== 压测配置 ===")
    print(f"  数据文件: {jsonl_path}")
    print(f"  目标地址: {data_url}")
    print(f"  目标 TPS: {args.target_tps}")
    print(f"  加压梯度: {[f'{g*100:.0f}%' for g in args.gradients]}")
    print(f"  每梯度时长: {args.duration}s")
    print(f"  并发线程: {args.workers}")

    print(f"\n 加载数据...")
    records = load_records(str(jsonl_path), max_records=args.max_records)
    print(f" 加载完成: {len(records)} 条记录")

    if len(records) < 10:
        print("❌ 错误：数据量过少，至少需要 10 条记录")
        sys.exit(1)

    # 执行压测
    results = []
    for gradient in args.gradients:
        print(f"\n{'='*60}")
        print(f" 开始梯度: {gradient*100:.0f}%")
        print(f"{'='*60}")

        result = run_gradient(
            data_url=data_url,
            records=records,
            gradient_pct=gradient,
            target_tps=args.target_tps,
            duration_sec=args.duration,
            workers=args.workers,
            enable_time_free=not args.no_time_free,
        )
        results.append(result)

        # 每梯度后短暂冷却
        if gradient != args.gradients[-1]:
            print(f" 冷却 5 秒...")
            time.sleep(5)

    # 输出报告
    print_report(results, args.target_tps)
    save_report(results, args.target_tps, args.output)


if __name__ == "__main__":
    main()
