#!/usr/bin/env python3
"""
布局引擎：arch.yaml → 节点坐标（draw.io 像素）

使用 graphviz dot（Sugiyama 分层布局）。
核心策略：用不可见锚点链强制 group 定义顺序 = 列顺序，
保留 graphviz 的 Y 位置优化（Barycenter 启发式）。

arch.yaml 无需任何位置信息（row/col 字段已废弃）。
依赖：graphviz CLI（brew install graphviz）
"""
import subprocess, json, sys, shutil
from pathlib import Path

START_X  = 60
START_Y  = 60
DPI_SCALE = 1.4
NODE_SEP  = 0.8          # 同列节点间距加大（避免多线拥挤）
RANK_SEP  = 2.5          # 列间距加大（给长连线留走廊）
DEFAULT_W_INCH = 2.0
LINE_H_INCH    = 0.22
V_PAD_INCH     = 0.20


def _find_dot():
    for c in [shutil.which("dot"), "/opt/homebrew/bin/dot",
              "/usr/local/bin/dot", "/usr/bin/dot"]:
        if c and Path(c).exists():
            return c
    return None


def _node_size_inches(node):
    name  = node.get("name", "")
    lines = name.count("\n") + 1
    props = node.get("props") or {}
    h = float(props["h"]) / 72 / DPI_SCALE if props.get("h") else max(0.5, lines * LINE_H_INCH + V_PAD_INCH)
    max_chars = max((len(l) for l in name.split("\n")), default=8)
    w = float(props["w"]) / 72 / DPI_SCALE if props.get("w") else max(DEFAULT_W_INCH, max_chars * 0.095)
    return w, h


def _build_dot(arch):
    """
    生成 dot 源码。
    用不可见锚点链强制 group 定义顺序 = 列顺序，
    同时保留 graphviz 在列内的 Y 位置优化。
    """
    nodes  = arch.get("nodes", [])
    edges  = arch.get("edges", [])
    groups = arch.get("groups", [])

    node_ids = {n["id"] for n in nodes}
    node_to_group = {m: g["id"] for g in groups for m in g.get("contains", [])}
    ungrouped = [n for n in nodes if n["id"] not in node_to_group]

    # 有序列列表
    col_list = [(g["id"], [m for m in g.get("contains",[]) if m in node_ids]) for g in groups]
    if ungrouped:
        col_list.append(("_ungrouped", [n["id"] for n in ungrouped]))

    n_cols = len(col_list)

    lines = [
        "digraph G {",
        f"    graph [rankdir=LR, ranksep={RANK_SEP}, nodesep={NODE_SEP},",
        '           splines=ortho, margin="0.3,0.4"]',
        "    node  [shape=box, fixedsize=false]",
        "    edge  [arrowsize=0.8]",
        "",
        "    // 不可见锚点链：强制列顺序",
    ]

    for i in range(n_cols):
        lines.append(f'    _col{i}_a [style=invis, width=0.01, height=0.01, label=""]')
    if n_cols > 1:
        chain = " -> ".join(f"_col{i}_a" for i in range(n_cols))
        lines.append(f"    {chain} [style=invis]")
    lines.append("")

    # rank=same：每列锚点 + 该列节点
    for i, (gid, members) in enumerate(col_list):
        same = [f"_col{i}_a"] + members
        lines.append("    {rank=same; " + "; ".join(same) + "}")
    lines.append("")

    # 节点定义
    for n in nodes:
        nid   = n["id"]
        label = n["name"].replace('"', '\\"')
        w, h  = _node_size_inches(n)
        dashed = "style=dashed" if n.get("status") == "future" else ""
        lines.append(f'    {nid} [label="{label}", width={w:.2f}, height={h:.2f} {dashed}]')
    lines.append("")

    # 连线
    for e in edges:
        s, t = e.get("from"), e.get("to")
        if s and t and s in node_ids and t in node_ids:
            lines.append(f"    {s} -> {t}")

    lines.append("}")
    return "\n".join(lines)


def compute_layout_graphviz(arch):
    dot_bin = _find_dot()
    if not dot_bin:
        print("⚠️  graphviz 未安装，回退线性布局  (brew install graphviz)", file=sys.stderr)
        return None

    dot_src = _build_dot(arch)
    try:
        result = subprocess.run([dot_bin, "-Tjson"], input=dot_src.encode(),
                                capture_output=True, timeout=10)
        if result.returncode != 0:
            print(f"⚠️  dot 报错: {result.stderr.decode()[:200]}", file=sys.stderr)
            return None
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"⚠️  dot 调用失败: {e}", file=sys.stderr)
        return None

    dot_nodes = {o["name"]: o for o in data.get("objects", []) if "pos" in o}
    if not dot_nodes:
        return None

    max_y = max(float(n["pos"].split(",")[1]) for n in dot_nodes.values())

    positions = {}
    for node in arch.get("nodes", []):
        nid = node["id"]
        dn  = dot_nodes.get(nid)
        if not dn:
            continue
        cx, cy = map(float, dn["pos"].split(","))
        w_dot = float(dn.get("width", DEFAULT_W_INCH)) * 72
        h_dot = float(dn.get("height", 0.5)) * 72
        positions[nid] = (
            (cx - w_dot / 2) * DPI_SCALE + START_X,
            (max_y - cy - h_dot / 2) * DPI_SCALE + START_Y,
            w_dot * DPI_SCALE,
            h_dot * DPI_SCALE,
        )

    # ── 后处理：强连接节点水平排列 ────────────────────────────────────────
    _horizontalize_connected_pairs(arch, positions)

    return positions


def _horizontalize_connected_pairs(arch, positions):
    """
    后处理：把同组内类型相同的核心产品节点水平排列。
    规则：组内同一类型的节点数 ≥ 2 且 ≤ 3 → 水平对齐。
    常见场景：product_internal 组内的多个 sd_product（CDP + SF）。
    """
    nodes  = arch.get("nodes", [])
    groups = arch.get("groups", [])
    node_map = {n["id"]: n for n in nodes}

    for g in groups:
        members = [m for m in g.get("contains", []) if m in positions]
        if len(members) < 2:
            continue

        # 按类型分组
        type_groups = {}
        for m in members:
            if m not in node_map:
                continue
            t = node_map[m]["type"]
            type_groups.setdefault(t, []).append(m)

        # 对核心类型（sd_product / sd_module）的子集进行水平化
        for t, sub_members in type_groups.items():
            if t not in ("sd_product", "sd_module"):
                continue
            if len(sub_members) < 2 or len(sub_members) > 4:
                continue

            # 计算平均 y 坐标
            avg_y = sum(positions[m][1] + positions[m][3]/2 for m in sub_members) / len(sub_members)

            # 按原始 x 排序
            sorted_members = sorted(sub_members, key=lambda m: positions[m][0])

            # 计算总宽度
            total_w = sum(positions[m][2] for m in sorted_members)
            gap = 40
            total_w += gap * (len(sorted_members) - 1)

            # 保持子集中心不变
            min_x = min(positions[m][0] for m in sub_members)
            max_x = max(positions[m][0] + positions[m][2] for m in sub_members)
            center_x = (min_x + max_x) / 2
            start_x = center_x - total_w / 2

            # 重新分配 x,y
            curr_x = start_x
            for m in sorted_members:
                w, h = positions[m][2], positions[m][3]
                positions[m] = (curr_x, avg_y - h/2, w, h)
                curr_x += w + gap


def compute_layout_linear(arch):
    """线性列布局（fallback，graphviz 不可用时）。"""
    nodes  = arch.get("nodes", [])
    groups = arch.get("groups", [])
    PAD_X=20; PAD_Y=40; ROW_GAP=24; COL_GAP=100; DW=160; DH=44

    def h(n):
        p = n.get("props") or {}
        return float(p["h"]) if p.get("h") else max(DH, (n.get("name","").count("\n")+1)*20+16)
    def w(n):
        p = n.get("props") or {}
        return float(p["w"]) if p.get("w") else DW

    nm = {n["id"]: n for n in nodes}
    gn = {}
    ug = []
    for n in nodes:
        gv = n.get("group")
        if gv: gn.setdefault(gv, []).append(n["id"])
        else:  ug.append(n["id"])

    cols = [(g["id"], gn.get(g["id"],[])) for g in groups if g["id"] in gn]
    for nid in ug: cols.append((None, [nid]))

    positions = {}
    cx = START_X
    for _, nids in cols:
        cw = max((w(nm[nid]) for nid in nids), default=DW)
        ny = START_Y + PAD_Y
        for nid in nids:
            positions[nid] = (cx + PAD_X, ny, w(nm[nid]), h(nm[nid]))
            ny += h(nm[nid]) + ROW_GAP
        cx += cw + PAD_X*2 + COL_GAP
    return positions
