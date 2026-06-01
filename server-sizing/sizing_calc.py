#!/usr/bin/env python3
"""
神策服务器资源评估计算器
用途：将所有涉及数字计算的部分从大模型推理中剥离，保证计算准确性。
SKILL 调用此脚本，对输出结果进行 review 后再呈现给用户。

用法：
  python3 sizing_calc.py \
    --daily-events 5000万 \
    --dau 100万 \
    --retention-days 365 \
    --history-events 0 \
    --growth-multiplier 2 \
    --arch x86 \
    --addons sf,abtest \
    --data-nodes 3 \
    [--sf-dau 50万 --sf-daily-events 3000万 --sf-audience 2500万]
"""

import argparse
import math
import sys
import json
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# 单位解析
# ---------------------------------------------------------------------------

def parse_count(s: str) -> float:
    """将 '5000万'、'1.5亿'、'3亿'、'500' 等字符串统一转为数字（单位：万）。"""
    s = s.strip().replace(",", "").replace("，", "")
    if s.endswith("亿"):
        return float(s[:-1]) * 10000  # 转为万
    elif s.endswith("万"):
        return float(s[:-1])
    else:
        return float(s)  # 假设已经是万为单位


def wan_to_yi(n: float) -> str:
    """将万为单位的数字格式化为易读字符串。"""
    if n >= 10000:
        return f"{n / 10000:.2f}亿".rstrip("0").rstrip(".")
    return f"{n:.0f}万"


# ---------------------------------------------------------------------------
# 标准盘型向上取整
# ---------------------------------------------------------------------------

STANDARD_DISK_SIZES_GB = [500, 1000, 1500, 2000, 3000, 4000]  # GB

def ceil_to_standard_disk(size_gb: float) -> int:
    """将计算出的单块磁盘容量向上取整到标准盘型。"""
    for s in STANDARD_DISK_SIZES_GB:
        if size_gb <= s:
            return s
    # 超出最大标准盘，按 1000G 步进向上取整
    return math.ceil(size_gb / 1000) * 1000


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class DiskResult:
    total_event_storage_gb: float       # event 数据总存储量（含冗余）
    total_seq_disk_gb: float            # 顺序盘总估算（含 Kafka/Yarn 系数）
    per_node_seq_disk_gb: float         # 单数据节点顺序盘总容量
    per_disk_raw_gb: float              # 单块盘原始计算值（÷6）
    per_disk_recommended_gb: int        # 单块盘推荐规格（取整到标准盘型）
    disks_per_node: int                 # 每节点顺序盘数量（固定 6）
    data_nodes: int                     # 数据节点数
    arm_doubled: bool                   # 是否已 ARM double


@dataclass
class CDPTierResult:
    tier_name: str                      # 档位名称
    deploy_mode: str                    # 部署模式
    meta_cpu: str
    meta_mem: str
    meta_nodes: int
    data_cpu: str
    data_mem: str
    data_nodes: int
    reason: str                         # 选型理由


@dataclass
class AddonDelta:
    addon: str
    cpu_delta: int   # 核
    mem_delta: float # GB
    note: str


@dataclass
class SFTierResult:
    tier_name: str
    nodes: int
    node_types: str
    daily_events_range: str
    dau_range: str
    audience_limit: str
    matched: bool
    reason: str


@dataclass
class CalcResult:
    # 输入摘要
    inputs: dict

    # 顺序盘计算
    disk: DiskResult

    # CDP 选型
    cdp_tier: CDPTierResult

    # 附加资源叠加
    addon_deltas: list
    total_addon_cpu: int
    total_addon_mem: float
    final_data_cpu: str
    final_data_mem: str

    # SF 选型（可选）
    sf_tier: Optional[SFTierResult] = None

    # 警告列表
    warnings: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4：顺序盘容量计算
# ---------------------------------------------------------------------------

def calc_disk(
    daily_events_wan: float,
    retention_days: int,
    history_events_wan: float,
    data_nodes: int,
    arch: str,
) -> DiskResult:
    """
    官方公式：
      event 存储量(GB) = (日导入量(亿) × 保留天数 + 历史存量(亿)) × 35 / 0.8
      顺序盘总估算     = event 存储量 × 1.1
      单节点总容量     = 顺序盘总估算 / 数据节点数
      单块盘           = 单节点总容量 / 6，向上取整到标准盘型
    """
    daily_yi = daily_events_wan / 10000
    history_yi = history_events_wan / 10000

    total_event_storage_gb = (daily_yi * retention_days + history_yi) * 35 / 0.8
    total_seq_disk_gb = total_event_storage_gb * 1.1
    per_node_seq_disk_gb = total_seq_disk_gb / data_nodes
    disks_per_node = 6
    per_disk_raw_gb = per_node_seq_disk_gb / disks_per_node

    arm_doubled = arch.lower() == "arm"
    if arm_doubled:
        per_disk_raw_gb *= 2

    per_disk_recommended_gb = ceil_to_standard_disk(per_disk_raw_gb)

    return DiskResult(
        total_event_storage_gb=round(total_event_storage_gb, 1),
        total_seq_disk_gb=round(total_seq_disk_gb, 1),
        per_node_seq_disk_gb=round(per_node_seq_disk_gb, 1),
        per_disk_raw_gb=round(per_disk_raw_gb, 1),
        per_disk_recommended_gb=per_disk_recommended_gb,
        disks_per_node=disks_per_node,
        data_nodes=data_nodes,
        arm_doubled=arm_doubled,
    )


# ---------------------------------------------------------------------------
# Phase 2/3：CDP 部署模式 + 配置档位选择
# ---------------------------------------------------------------------------

# 档位定义：(最大日事件量万, 最大总事件量亿, 档位名, 部署模式, 元数据节点数, 元数据CPU, 元数据内存, 数据节点数, 数据CPU, 数据内存)
CDP_TIERS = [
    # (max_daily_wan, max_total_yi, name, mode, meta_n, meta_cpu, meta_mem, data_n, data_cpu, data_mem)
    (1000,   30,   "单机标配",        "single",   0, "-",   "-",    1, "8C",  "64G"),
    (1500,   75,   "单机高配",        "single",   0, "-",   "-",    1, "16C", "128G"),
    (6500,   600,  "Mini集群标配",    "mini",     0, "-",   "-",    3, "8C",  "64G"),
    (15000,  1400, "Mini集群高配",    "mini",     0, "-",   "-",    3, "16C", "128G"),
    (42000,  3800, "标准集群3+3标配", "standard", 3, "8C",  "32G",  3, "16C", "128G"),
    (84000,  8000, "标准集群3+3高配", "standard", 3, "16C", "64G",  3, "32C", "128G"),
    (62000,  5700, "标准集群3+4标配", "standard", 3, "8C",  "32G",  4, "16C", "128G"),
    (100000, 9000, "标准集群3+4高配", "standard", 3, "16C", "64G",  4, "32C", "128G"),
    (131000, 10000,"标准集群3+5高配", "standard", 3, "16C", "64G",  5, "32C", "128G"),
    (160000, 12000,"标准集群3+6高配", "standard", 3, "16C", "64G",  6, "32C", "128G"),
]


def select_cdp_tier(
    daily_events_wan: float,
    retention_days: int,
    history_events_wan: float,
    growth_multiplier: float,
    dau_wan: float,
) -> CDPTierResult:
    """
    按日事件量（含增长预期）和总事件量选择 CDP 档位。
    增长预期：取 daily_events_wan × growth_multiplier 作为规划量。
    """
    planned_daily = daily_events_wan * growth_multiplier
    total_yi = (daily_events_wan * retention_days + history_events_wan) / 10000

    for (max_daily_wan, max_total_yi, name, mode, meta_n, meta_cpu, meta_mem, data_n, data_cpu, data_mem) in CDP_TIERS:
        if planned_daily <= max_daily_wan and total_yi <= max_total_yi:
            reason = (
                f"规划日事件量 {wan_to_yi(planned_daily)}（当前 {wan_to_yi(daily_events_wan)} × {growth_multiplier} 倍增长），"
                f"总存储量 {total_yi:.1f}亿，匹配 {name}"
            )
            return CDPTierResult(
                tier_name=name,
                deploy_mode=mode,
                meta_cpu=meta_cpu,
                meta_mem=meta_mem,
                meta_nodes=meta_n,
                data_cpu=data_cpu,
                data_mem=data_mem,
                data_nodes=data_n,
                reason=reason,
            )

    # 超出所有预设档位
    return CDPTierResult(
        tier_name="超出预设档位，需人工评估",
        deploy_mode="standard",
        meta_cpu="16C+",
        meta_mem="64G+",
        meta_nodes=3,
        data_cpu="32C+",
        data_mem="128G+",
        data_nodes=max(6, math.ceil(planned_daily / 30000)),
        reason=f"规划日事件量 {wan_to_yi(planned_daily)} 超出预设最大档位，建议联系 SaaS 运维评估",
    )


# ---------------------------------------------------------------------------
# 附加资源叠加
# ---------------------------------------------------------------------------

ADDON_SPECS = {
    "sf":          AddonDelta("SF（MA）",    4,   8,    "SF 圈选用户，计算受众开销与运行中的计划数量相关"),
    "abtest":      AddonDelta("Abtest",      4,   8,    "选取受众条件计算开销较大，与运行中的试验数量相关"),
    "saas_sat":    AddonDelta("SaaS SAT",    2,   4,    "通过 Impala 读写 Kudu 表"),
    "report":      AddonDelta("报表",        8,   16,   "开销取决于业务模型方法、查询复杂度、数据量级"),
    "data_import": AddonDelta("数据导入",    2,   2.5,  "每种导入类型累加；涉及多种时需叠加"),
    "jdbc_export": AddonDelta("JDBC导出",    8,   16,   "开销取决于查询复杂度、数据量级、导出频次"),
}

def calc_addons(addon_list: list[str]) -> tuple[list[AddonDelta], int, float]:
    """计算附加资源增量，返回 (明细列表, 总CPU增量, 总内存增量)。"""
    deltas = []
    total_cpu = 0
    total_mem = 0.0
    for key in addon_list:
        key = key.strip().lower()
        if key in ADDON_SPECS:
            d = ADDON_SPECS[key]
            deltas.append(d)
            total_cpu += d.cpu_delta
            total_mem += d.mem_delta
    return deltas, total_cpu, total_mem


def apply_addon_to_spec(base_cpu_str: str, base_mem_str: str, delta_cpu: int, delta_mem: float) -> tuple[str, str]:
    """将附加资源增量叠加到基础规格上，返回新的 CPU/内存字符串。"""
    # 解析基础规格
    base_cpu = int(base_cpu_str.replace("C", "").replace("+", "").strip())
    base_mem = float(base_mem_str.replace("G", "").replace("+", "").strip())
    new_cpu = base_cpu + delta_cpu
    new_mem = base_mem + delta_mem
    return f"{new_cpu}C", f"{new_mem:.0f}G"


# ---------------------------------------------------------------------------
# Phase 8：SF 集群选型
# ---------------------------------------------------------------------------

SF_TIERS = [
    # (name, nodes, node_types, max_dau_wan, max_daily_wan, max_audience_wan)
    ("3节点集群低配",  3,  "混合节点×3",                    20,    2000,   1000),
    ("3节点集群中配",  3,  "混合节点×3",                    50,    5000,   2500),
    ("3节点集群高配",  3,  "混合节点×3",                    100,   10000,  5000),
    ("3+3集群",        6,  "元数据节点×3 + SF混合节点×3",   300,   30000,  10000),
    ("3+3+3集群",      9,  "元数据节点×3 + 数据节点×3 + SF在线节点×3", 1000, 50000, 10000),
    ("3+5+3集群",      11, "元数据节点×3 + 数据节点×5 + SF在线节点×3", 1000, 50000, 30000),
    ("3+8+3集群",      14, "元数据节点×3 + 数据节点×8 + SF在线节点×3", 2000, 100000, 50000),
]

def select_sf_tier(
    sf_dau_wan: float,
    sf_daily_events_wan: float,
    sf_audience_wan: float,
) -> SFTierResult:
    for (name, nodes, node_types, max_dau_wan, max_daily_wan, max_audience_wan) in SF_TIERS:
        if (sf_dau_wan <= max_dau_wan and
                sf_daily_events_wan <= max_daily_wan and
                sf_audience_wan <= max_audience_wan):
            return SFTierResult(
                tier_name=name,
                nodes=nodes,
                node_types=node_types,
                daily_events_range=f"≤{wan_to_yi(max_daily_wan)}",
                dau_range=f"≤{wan_to_yi(max_dau_wan)}",
                audience_limit=f"≤{wan_to_yi(max_audience_wan)}",
                matched=True,
                reason=(
                    f"SF 日活 {wan_to_yi(sf_dau_wan)}，"
                    f"日事件量 {wan_to_yi(sf_daily_events_wan)}，"
                    f"受众上限 {wan_to_yi(sf_audience_wan)}，"
                    f"匹配 {name}"
                ),
            )

    return SFTierResult(
        tier_name="超出预设档位（3+N+3集群）",
        nodes=-1,
        node_types="需联系 SaaS 运维单独评估",
        daily_events_range="10亿以上",
        dau_range="2000万以上",
        audience_limit="5亿以上",
        matched=False,
        reason="SF 规模超出预设档位，请联系 SaaS 运维单独评估集群配置",
    )


# ---------------------------------------------------------------------------
# 主计算入口
# ---------------------------------------------------------------------------

def run_calc(
    daily_events_str: str,
    dau_str: str,
    retention_days: int,
    history_events_str: str,
    growth_multiplier: float,
    arch: str,
    addons: list[str],
    data_nodes: int,
    sf_dau_str: Optional[str] = None,
    sf_daily_events_str: Optional[str] = None,
    sf_audience_str: Optional[str] = None,
) -> CalcResult:

    daily_wan = parse_count(daily_events_str)
    dau_wan = parse_count(dau_str)
    history_wan = parse_count(history_events_str)

    inputs = {
        "daily_events": wan_to_yi(daily_wan),
        "dau": wan_to_yi(dau_wan),
        "retention_days": retention_days,
        "history_events": wan_to_yi(history_wan),
        "growth_multiplier": growth_multiplier,
        "arch": arch,
        "addons": addons,
        "data_nodes": data_nodes,
    }

    # 顺序盘计算
    disk = calc_disk(daily_wan, retention_days, history_wan, data_nodes, arch)

    # CDP 选型
    cdp_tier = select_cdp_tier(daily_wan, retention_days, history_wan, growth_multiplier, dau_wan)

    # 附加资源
    addon_deltas, total_addon_cpu, total_addon_mem = calc_addons(addons)
    final_data_cpu, final_data_mem = apply_addon_to_spec(
        cdp_tier.data_cpu, cdp_tier.data_mem, total_addon_cpu, total_addon_mem
    )

    # ARM double 对 CPU/内存
    if arch.lower() == "arm":
        def double_spec(s: str) -> str:
            val = float(s.replace("C", "").replace("G", "").replace("+", ""))
            return f"{int(val * 2)}{'C' if 'C' in s else 'G'}"
        final_data_cpu = double_spec(final_data_cpu)
        final_data_mem = double_spec(final_data_mem)

    # SF 选型
    sf_tier = None
    if sf_dau_str and sf_daily_events_str and sf_audience_str:
        sf_tier = select_sf_tier(
            parse_count(sf_dau_str),
            parse_count(sf_daily_events_str),
            parse_count(sf_audience_str),
        )
        inputs["sf_dau"] = wan_to_yi(parse_count(sf_dau_str))
        inputs["sf_daily_events"] = wan_to_yi(parse_count(sf_daily_events_str))
        inputs["sf_audience"] = wan_to_yi(parse_count(sf_audience_str))

    # 警告
    warnings = []
    planned_daily = daily_wan * growth_multiplier
    if cdp_tier.deploy_mode == "mini" and planned_daily > 30000:
        warnings.append(
            f"⚠️  Mini 集群最多扩至 5 节点，规划日事件量 {wan_to_yi(planned_daily)} 超过 3亿/天，"
            "建议直接选标准集群，避免后续数据迁移。"
        )
    if disk.per_disk_recommended_gb >= 2000:
        warnings.append(
            f"⚠️  单块顺序盘推荐 {disk.per_disk_recommended_gb}G，容量较大，"
            "建议与客户确认云厂商单盘上限，或增加数据节点数分摊。"
        )
    if arch.lower() == "arm":
        warnings.append("⚠️  ARM 架构：CPU、内存、顺序盘容量已 ×2，请确认客户 ARM 机型可用。")
    if sf_tier and not sf_tier.matched:
        warnings.append("⚠️  SF 规模超出预设档位，需联系 SaaS 运维单独评估。")

    return CalcResult(
        inputs=inputs,
        disk=disk,
        cdp_tier=cdp_tier,
        addon_deltas=[asdict(d) for d in addon_deltas],
        total_addon_cpu=total_addon_cpu,
        total_addon_mem=total_addon_mem,
        final_data_cpu=final_data_cpu,
        final_data_mem=final_data_mem,
        sf_tier=sf_tier,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_result(r: CalcResult) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("神策服务器资源评估 — 计算结果")
    lines.append("=" * 60)

    lines.append("\n【输入参数】")
    for k, v in r.inputs.items():
        lines.append(f"  {k}: {v}")

    lines.append("\n【顺序盘容量计算（Phase 4）】")
    d = r.disk
    lines.append(f"  event 数据总存储量（含冗余）: {d.total_event_storage_gb:.1f} GB")
    lines.append(f"  顺序盘总估算（×1.1 系数）  : {d.total_seq_disk_gb:.1f} GB")
    lines.append(f"  数据节点数                 : {d.data_nodes}")
    lines.append(f"  单节点顺序盘总容量         : {d.per_node_seq_disk_gb:.1f} GB")
    lines.append(f"  单块盘原始计算值（÷6）     : {d.per_disk_raw_gb:.1f} GB")
    if d.arm_doubled:
        lines.append(f"  ARM double 已应用          : 是（容量已 ×2）")
    lines.append(f"  单块盘推荐规格（取整）     : {d.per_disk_recommended_gb} G")
    lines.append(f"  每节点顺序盘数量           : {d.disks_per_node} 块")
    lines.append(f"  → 推荐配置: {d.per_disk_recommended_gb}G × {d.disks_per_node} / 数据节点")

    lines.append("\n【CDP 部署模式 + 配置档位（Phase 2/3）】")
    t = r.cdp_tier
    lines.append(f"  推荐档位  : {t.tier_name}")
    lines.append(f"  部署模式  : {t.deploy_mode}")
    if t.meta_nodes > 0:
        lines.append(f"  元数据节点: {t.meta_nodes} 台，{t.meta_cpu} / {t.meta_mem}")
    lines.append(f"  数据节点  : {t.data_nodes} 台，{t.data_cpu} / {t.data_mem}（基础规格）")
    lines.append(f"  选型理由  : {t.reason}")

    if r.addon_deltas:
        lines.append("\n【附加资源叠加（Phase 3 附加说明）】")
        for d in r.addon_deltas:
            lines.append(f"  + {d['addon']}: CPU +{d['cpu_delta']}C，内存 +{d['mem_delta']}G  ({d['note']})")
        lines.append(f"  合计增量  : CPU +{r.total_addon_cpu}C，内存 +{r.total_addon_mem}G")
        lines.append(f"  数据节点最终规格: {r.final_data_cpu} / {r.final_data_mem}")

    if r.sf_tier:
        lines.append("\n【SF（SFN/MA）集群选型（Phase 8）】")
        s = r.sf_tier
        lines.append(f"  推荐档位  : {s.tier_name}")
        lines.append(f"  节点数    : {s.nodes if s.nodes > 0 else '待评估'}")
        lines.append(f"  节点构成  : {s.node_types}")
        lines.append(f"  选型理由  : {s.reason}")

    if r.warnings:
        lines.append("\n【注意事项】")
        for w in r.warnings:
            lines.append(f"  {w}")

    lines.append("\n" + "=" * 60)
    lines.append("以上为脚本计算结果，请 SKILL 对照配置表进行 review 后输出给用户。")
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="神策服务器资源评估计算器")
    parser.add_argument("--daily-events",      required=True,  help="日均事件量，如 '5000万'、'1.5亿'")
    parser.add_argument("--dau",               required=True,  help="日活用户数，如 '100万'")
    parser.add_argument("--retention-days",    type=int, default=365, help="数据保留天数（默认 365）")
    parser.add_argument("--history-events",    default="0",    help="历史存量事件数，如 '0'、'500亿'")
    parser.add_argument("--growth-multiplier", type=float, default=1.0, help="未来 12 个月增长倍数（默认 1.0）")
    parser.add_argument("--arch",              default="x86",  help="CPU 架构：x86 或 arm（默认 x86）")
    parser.add_argument("--addons",            default="",     help="附加产品，逗号分隔：sf,abtest,saas_sat,report,data_import,jdbc_export")
    parser.add_argument("--data-nodes",        type=int, default=3, help="数据节点数（用于顺序盘计算，默认 3）")
    parser.add_argument("--sf-dau",            default=None,   help="SF 日活，如 '50万'")
    parser.add_argument("--sf-daily-events",   default=None,   help="SF 日事件量，如 '3000万'")
    parser.add_argument("--sf-audience",       default=None,   help="SF 每天受众上限，如 '2500万'")
    parser.add_argument("--json",              action="store_true", help="以 JSON 格式输出（供程序解析）")

    args = parser.parse_args()
    addons = [a.strip() for a in args.addons.split(",") if a.strip()]

    result = run_calc(
        daily_events_str=args.daily_events,
        dau_str=args.dau,
        retention_days=args.retention_days,
        history_events_str=args.history_events,
        growth_multiplier=args.growth_multiplier,
        arch=args.arch,
        addons=addons,
        data_nodes=args.data_nodes,
        sf_dau_str=args.sf_dau,
        sf_daily_events_str=args.sf_daily_events,
        sf_audience_str=args.sf_audience,
    )

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(format_result(result))


if __name__ == "__main__":
    main()
