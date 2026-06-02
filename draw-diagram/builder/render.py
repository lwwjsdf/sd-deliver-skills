#!/usr/bin/env python3
"""
架构图渲染器：从 arch.yaml（+ 可选 view.yaml）生成 draw.io XML

用法：
  # 自动布局（初始生成）
  python3 render.py --arch arch.yaml --output diagram.drawio

  # 精确还原（完全幂等）
  python3 render.py --arch arch.yaml --view view.yaml --output diagram.drawio
"""

import yaml
import uuid
import argparse
import re
import sys
from pathlib import Path

# ── 语义 → 视觉映射规则（唯一视觉决策来源）──────────────────────────────────

NODE_VISUAL = {
    "sd_product":      {"fill": "#d5e8d4", "stroke": "#82b366", "font_size": 14},
    "sd_module":       {"fill": "#fffde7", "stroke": "#d6b656", "font_size": 12},
    "client_system":   {"fill": "#e1d5e7", "stroke": "#9673a6", "font_size": 12},
    "client_frontend": {"fill": "#e1d5e7", "stroke": "#9673a6", "font_size": 12},
    "external_saas":   {"fill": "#dae8fc", "stroke": "#6c8ebf", "font_size": 12},
    "person":          {"fill": "#FFCE9F", "stroke": "#d79b00", "font_size": 11,
                        "shape": "mxgraph.basic.person2", "w": 60, "h": 80},
    "infra":           {"fill": "#d5e8d4", "stroke": "#82b366", "font_size": 12},
}

NODE_FUTURE_OVERRIDE = {"fill": "#f5f5f5", "stroke": "#bdbdbd", "dashed": True}

GROUP_VISUAL = {
    "data_sources":    {"fill": "none", "stroke": "#82b366", "dashed": True},
    "frontend":        {"fill": "#f8f0ff", "stroke": "#9673a6", "dashed": False},
    "client_systems":  {"fill": "#f8f0ff", "stroke": "#9673a6", "dashed": False},
    "internet":        {"fill": "none",    "stroke": "#6c8ebf", "dashed": True},
    "vpc":             {"fill": "#f0f4ff", "stroke": "#6c8ebf", "dashed": True},
    "region":          {"fill": "none",    "stroke": "#aaaaaa", "dashed": True},
}

def edge_color(edge: dict) -> tuple[str, bool]:
    """
    严格从语义推导连线颜色和虚实。
    返回 (color_hex, is_dashed)
    规则优先级：
      1. kafka_subscribe → 蓝色虚线（覆盖 PII 规则）
      2. future → 灰色虚线
      3. has_pii=True + daily/weekly → 红色虚线
      4. has_pii=True + realtime → 红色实线
      5. callback → 绿色实线
      6. 其他 → 绿色实线
    """
    rel  = edge.get("rel", "")
    data = edge.get("data", {})
    status = edge.get("status", "current")
    has_pii   = data.get("has_pii", False)
    frequency = data.get("frequency", "realtime")

    if rel == "kafka_subscribe":
        return "#6c8ebf", True          # 蓝虚线
    if status == "future":
        return "#bdbdbd", True          # 灰虚线
    if has_pii and frequency in ("daily", "weekly"):
        return "#FF0000", True          # 红虚线
    if has_pii:
        return "#FF0000", False         # 红实线
    if rel == "callback":
        return "#82b366", False         # 绿实线
    return "#82b366", False             # 绿实线（默认）


# ── XML 生成辅助 ──────────────────────────────────────────────────────────────

def gid():
    return uuid.uuid4().hex[:10]

def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;").replace('"', "&quot;")
                  .replace("\n", "&#xa;"))

def node_xml(cell_id, label, style, x, y, w, h) -> str:
    return (f'        <mxCell id="{cell_id}" value="{esc(label)}" style="{style}" '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" '
            f'height="{h:.0f}" as="geometry"/>\n        </mxCell>\n')

def edge_xml(cell_id, src, tgt, style, label="") -> str:
    return (f'        <mxCell id="{cell_id}" value="{esc(label)}" style="{style}" '
            f'edge="1" source="{src}" target="{tgt}" parent="1">\n'
            f'          <mxGeometry relative="1" as="geometry"/>\n        </mxCell>\n')


# ── 布局引擎 ─────────────────────────────────────────────────────────────────

DEFAULT_NODE_W      = 160
DEFAULT_NODE_H      = 44
LINE_H              = 20    # 每行文字高度，用于自动计算多行节点高度
NODE_V_PADDING      = 16    # 节点上下内边距合计
COL_GAP             = 100
ROW_GAP             = 24
CONTAINER_PAD_X     = 20
CONTAINER_PAD_Y     = 40
START_X             = 60
START_Y             = 60
MAX_GROUP_ROW_SPAN  = 1     # group 跨行超过此值时不画容器框


def node_height(n: dict) -> float:
    """自动计算节点高度：优先 props.h，否则按名称换行数估算。"""
    props = n.get("props") or {}
    if props.get("h"):
        return float(props["h"])
    lines = n.get("name", "").count("\n") + 1
    return max(DEFAULT_NODE_H, lines * LINE_H + NODE_V_PADDING)


def node_width(n: dict) -> float:
    props = n.get("props") or {}
    if props.get("w"):
        return float(props["w"])
    visual = NODE_VISUAL.get(n.get("type", "client_system"), NODE_VISUAL["client_system"])
    return float(visual.get("w") or DEFAULT_NODE_W)


def compute_layout(nodes: list, groups: list) -> dict:
    """
    布局入口：
    - 任何节点有 row 字段 → 使用行对齐布局（精确）
    - 否则 → 线性列堆叠布局（fallback）
    """
    if any(n.get("row") is not None for n in nodes):
        return compute_layout_with_rows(nodes, groups)
    return _linear_layout(nodes, groups)


def _linear_layout(nodes: list, groups: list) -> dict:
    """线性布局（fallback）：每列节点从顶部堆叠。"""
    node_map = {n["id"]: n for n in nodes}
    group_nodes: dict[str, list] = {}
    ungrouped = []
    for n in nodes:
        gv = n.get("group")
        if gv:
            group_nodes.setdefault(gv, []).append(n["id"])
        else:
            ungrouped.append(n["id"])
    group_order = [g["id"] for g in groups]
    columns = [(g, group_nodes.get(g, [])) for g in group_order if g in group_nodes]
    for nid in ungrouped:
        columns.append((None, [nid]))
    positions = {}
    col_x = START_X
    for _, node_ids in columns:
        col_w = max((node_map[nid].get("props", {}).get("w") or DEFAULT_NODE_W for nid in node_ids), default=DEFAULT_NODE_W)
        node_y = START_Y + CONTAINER_PAD_Y
        for nid in node_ids:
            n = node_map[nid]
            w = node_width(n)
            h = node_height(n)
            positions[nid] = (col_x + CONTAINER_PAD_X, node_y, w, h)
            node_y += h + ROW_GAP
        col_x += col_w + CONTAINER_PAD_X * 2 + COL_GAP
    return positions


def compute_layout_with_rows(nodes: list, groups: list) -> dict:
    """
    行对齐布局：节点有 row 字段时使用。

    arch.yaml 中每个节点可指定：
      row: 2    # 所在逻辑行（1 起始，同行节点 Y 中心对齐）
      col: 0    # 所在列（可选，优先于 group 顺序）

    规则：
    - 同列 + 同行有多个节点时，水平排列（目前按 group 定义顺序）
    - 行高 = 该行最高节点的高度
    - 同行节点 Y 中心对齐
    - 未指定 row 的节点自动按列内出现顺序分配行号
    """
    node_map = {n["id"]: n for n in nodes}
    group_col = {g["id"]: i for i, g in enumerate(groups)}

    def get_col(nid):
        n = node_map[nid]
        if "col" in n:
            return n["col"]
        gid = n.get("group")
        return group_col.get(gid, 99) if gid else 99

    # 补全缺 row 的节点
    col_row_counter = {}
    node_rows = {}
    for n in nodes:
        nid = n["id"]
        if n.get("row") is not None:
            node_rows[nid] = n["row"]
        else:
            col = get_col(nid)
            col_row_counter[col] = col_row_counter.get(col, 0) + 1
            node_rows[nid] = col_row_counter[col]

    # 每行最大高度
    row_max_h = {}
    for n in nodes:
        row = node_rows[n["id"]]
        h = node_height(n)
        row_max_h[row] = max(row_max_h.get(row, DEFAULT_NODE_H), h)

    # 每行 Y 基准
    row_y = {}
    y = START_Y + CONTAINER_PAD_Y
    for row in sorted(row_max_h.keys()):
        row_y[row] = y
        y += row_max_h[row] + ROW_GAP

    # 每列 X（按列序排列）
    all_cols = sorted(set(get_col(n["id"]) for n in nodes))
    col_x_map = {}
    x = START_X
    for col in all_cols:
        col_x_map[col] = x
        col_nodes = [n for n in nodes if get_col(n["id"]) == col]
        col_w = max((node_width(node_map[n["id"]]) for n in col_nodes), default=DEFAULT_NODE_W)
        x += col_w + CONTAINER_PAD_X * 2 + COL_GAP

    # 生成最终坐标
    positions = {}
    for n in nodes:
        nid = n["id"]
        col = get_col(nid)
        row = node_rows[nid]
        nm = node_map[nid]
        w = node_width(nm)
        h = node_height(nm)
        row_h = row_max_h.get(row, DEFAULT_NODE_H)
        y_pos = row_y[row] + (row_h - h) / 2   # 同行内垂直居中
        positions[nid] = (col_x_map[col] + CONTAINER_PAD_X, y_pos, w, h)

    return positions



def node_style_str(vtype: str, is_future: bool, shape: str = None,
                   is_container: bool = False, font_size: int = 12) -> str:
    visual = NODE_VISUAL.get(vtype, NODE_VISUAL["client_system"]).copy()
    if is_future:
        visual.update(NODE_FUTURE_OVERRIDE)

    fill   = visual.get("fill", "#ffffff")
    stroke = visual.get("stroke", "#666666")
    dashed = "1" if visual.get("dashed") else "0"
    fs     = visual.get("font_size") or font_size

    if shape:
        return (f"shape={shape};fillColor={fill};strokeColor={stroke};"
                f"fontSize={fs};dashed={dashed};")
    valign = "top" if is_container else "middle"
    return (f"rounded=0;whiteSpace=wrap;html=1;fillColor={fill};"
            f"strokeColor={stroke};strokeWidth=2;fontSize={fs};"
            f"dashed={dashed};verticalAlign={valign};")


def edge_style_str(color: str, dashed: bool) -> str:
    d = "1" if dashed else "0"
    return (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
            f"jettySize=auto;html=1;strokeColor={color};strokeWidth=2;"
            f"dashed={d};exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
            f"entryX=0;entryY=0.5;entryDx=0;entryDy=0;fontStyle=2;fontSize=10;")


def group_style_str(gtype: str) -> str:
    v = GROUP_VISUAL.get(gtype, GROUP_VISUAL["data_sources"])
    fill   = v.get("fill", "none")
    stroke = v.get("stroke", "#aaaaaa")
    d      = "1" if v.get("dashed") else "0"
    return (f"rounded=0;whiteSpace=wrap;html=1;fillColor={fill};"
            f"strokeColor={stroke};strokeWidth=2;dashed={d};"
            f"verticalAlign=top;fontSize=13;fontStyle=1;")


# ── 图例 ─────────────────────────────────────────────────────────────────────

def legend_xml(x: float, y: float) -> str:
    xml = ""
    box_id = gid()
    xml += node_xml(box_id, "Legend",
                    "whiteSpace=wrap;fillColor=#f5f5f5;strokeColor=#666666;"
                    "verticalAlign=top;fontStyle=1;fontSize=12;",
                    x, y, 270, 220)
    items = [
        ("SD Product (CDP/MAE)", "sd_product"),
        ("Client System", "client_system"),
        ("External SaaS", "external_saas"),
        ("Future Scope (Day 2+)", "future"),
    ]
    cy = y + 30
    for label, vtype in items:
        nid = gid()
        style = (node_style_str(vtype, vtype == "future", font_size=11)
                 if vtype != "future"
                 else node_style_str("client_system", True, font_size=11))
        xml += node_xml(nid, label, style, x + 8, cy, 254, 22)
        cy += 28

    cy += 8
    edges_legend = [
        ("PII realtime",  "#FF0000", False),
        ("PII batch",     "#FF0000", True),
        ("Kafka async",   "#6c8ebf", True),
        ("Internal flow", "#82b366", False),
    ]
    for label, color, dashed in edges_legend:
        s_id, t_id = gid(), gid()
        xml += node_xml(s_id, "", f"fillColor={color};strokeColor={color};", x+8,  cy+5, 8, 8)
        xml += node_xml(t_id, "", f"fillColor={color};strokeColor={color};", x+65, cy+5, 8, 8)
        e_id = gid()
        xml += edge_xml(e_id, s_id, t_id,
                        f"edgeStyle=orthogonalEdgeStyle;strokeColor={color};"
                        f"strokeWidth=2;dashed={'1' if dashed else '0'};",
                        "")
        txt_id = gid()
        xml += node_xml(txt_id, label,
                        "text;html=1;fontSize=10;align=left;",
                        x+80, cy, 180, 18)
        cy += 22
    return xml


# ── 主渲染函数 ────────────────────────────────────────────────────────────────

def render(arch: dict, output_path: str, view: dict = None):
    """
    arch: arch.yaml 内容
    view: view.yaml 内容（可选）
      - 提供 → 使用 view 中的精确坐标，实现完全幂等还原
      - 不提供 → 使用自动布局算法，用于初始生成
    """
    nodes  = arch.get("nodes", [])
    groups = arch.get("groups", [])
    edges  = arch.get("edges", [])
    title  = arch.get("meta", {}).get("title", "Architecture")

    # 坐标决策：view.yaml 优先，否则自动布局
    view_nodes  = (view or {}).get("nodes", {})
    view_groups = (view or {}).get("groups", {})
    view_edges  = (view or {}).get("edges", {})
    use_view    = bool(view_nodes)

    if use_view:
        # 从 view.yaml 读取精确坐标
        positions = {}
        for n in nodes:
            nid = n["id"]
            vn = view_nodes.get(nid, {})
            visual = NODE_VISUAL.get(n.get("type","client_system"), NODE_VISUAL["client_system"])
            x = float(vn.get("x", 0))
            y = float(vn.get("y", 0))
            w = float(vn.get("w", visual.get("w", DEFAULT_NODE_W)))
            h = float(vn.get("h", visual.get("h", DEFAULT_NODE_H)))
            positions[nid] = (x, y, w, h)
    else:
        positions = compute_layout(nodes, groups)

    node_map  = {n["id"]: n for n in nodes}

    # node_id → draw.io cell_id
    id_map: dict[str, str] = {}
    cells_xml = ""

    # 渲染分组容器框
    node_rows_in_render = {}
    for n in nodes:
        node_rows_in_render[n["id"]] = n.get("row", 1)

    for g in groups:
        gtype   = g.get("type", "data_sources")
        members = g.get("contains", [])
        if not members:
            continue

        # 跨行保护：group 内节点跨行超过阈值，不画容器框（避免容器框撑穿整个画布）
        if not use_view:
            member_rows = [node_rows_in_render.get(m, 1) for m in members if m in node_rows_in_render]
            if member_rows:
                row_span = max(member_rows) - min(member_rows)
                if row_span > MAX_GROUP_ROW_SPAN:
                    # 跨行太多：跳过容器框，但节点仍然渲染
                    continue

        if use_view and g["id"] in view_groups:
            # view.yaml 提供了精确坐标
            vg = view_groups[g["id"]]
            cx = float(vg["x"]); cy = float(vg["y"])
            cw = float(vg["w"]); ch = float(vg["h"])
        else:
            # 自动计算包围盒
            xs = [positions[nid][0] for nid in members if nid in positions]
            ys = [positions[nid][1] for nid in members if nid in positions]
            ws = [positions[nid][2] for nid in members if nid in positions]
            hs = [positions[nid][3] for nid in members if nid in positions]
            if not xs:
                continue
            pad = CONTAINER_PAD_X
            cx  = min(xs) - pad
            cy  = min(ys) - CONTAINER_PAD_Y
            cw  = max(x + w for x, w in zip(xs, ws)) - cx + pad
            ch  = max(y + h for y, h in zip(ys, hs)) - cy + pad + 10

        c_id = gid()
        cells_xml += node_xml(c_id, f"<b>{g['name']}</b>",
                               group_style_str(gtype), cx, cy, cw, ch)

    # 渲染节点
    for n in nodes:
        nid   = n["id"]
        vtype = n.get("type", "client_system")
        is_future = n.get("status") == "future"
        visual = NODE_VISUAL.get(vtype, NODE_VISUAL["client_system"])
        shape  = visual.get("shape")
        pos    = positions.get(nid)
        if not pos:
            continue
        # 从 positions 取坐标，但用 node_height/node_width 确保高度正确
        x, y = pos[0], pos[1]
        w = node_width(n)
        h = node_height(n)

        # 检查 view.yaml 中是否有例外视觉 override
        vn = view_nodes.get(nid, {})
        override = vn.get("override", {})

        style = node_style_str(vtype, is_future, shape=shape)
        # 应用 override（只修改有 override 的属性）
        if override:
            if "stroke_color" in override:
                style = re.sub(r'strokeColor=[^;]+', f'strokeColor={override["stroke_color"]}', style)
            if "stroke_width" in override:
                style = re.sub(r'strokeWidth=[^;]+', f'strokeWidth={override["stroke_width"]}', style)
            if "fill_color" in override:
                style = re.sub(r'fillColor=[^;]+', f'fillColor={override["fill_color"]}', style)

        cell_id = gid()
        id_map[nid] = cell_id
        cells_xml += node_xml(cell_id, n["name"], style, x, y, w, h)

    # 渲染连线
    for e in edges:
        src = id_map.get(e["from"])
        tgt = id_map.get(e["to"])
        if not src or not tgt:
            print(f"⚠️  Edge skipped: {e.get('from')} → {e.get('to')} (node not found)",
                  file=sys.stderr)
            continue

        color, dashed = edge_color(e)
        # 连线标签：name + 字段列表（可选）
        data   = e.get("data", {})
        fields = data.get("fields", [])
        label  = e.get("name", "")
        if fields:
            label = f"{label}\n{' / '.join(fields)}" if label else " / ".join(fields)

        e_id = gid()
        cells_xml += edge_xml(e_id, src, tgt, edge_style_str(color, dashed), label)

    # 图例位置
    max_x = max((x + w for x, _, w, _ in positions.values()), default=800)
    legend = legend_xml(max_x + 80, START_Y)

    xml = f"""<mxfile host="app.diagrams.net">
  <diagram name="{esc(title)}" id="{gid()}">
    <mxGraphModel dx="1920" dy="1080" grid="1" gridSize="10" guides="1"
                  tooltips="1" connect="1" arrows="1" fold="1" page="1"
                  pageScale="1" pageWidth="1900" pageHeight="1050" math="0" shadow="0">
      <root>
        <mxCell id="0" /><mxCell id="1" parent="0" />
{cells_xml}{legend}      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"✓ {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="从 arch.yaml（+ view.yaml）生成 draw.io 架构图")
    p.add_argument("--arch",   required=True, help="arch.yaml 路径")
    p.add_argument("--view",   default=None,  help="view.yaml 路径（可选，提供则精确还原坐标）")
    p.add_argument("--output", required=True, help="输出 .drawio 文件路径")
    args = p.parse_args()

    with open(args.arch, encoding="utf-8") as f:
        arch = yaml.safe_load(f)

    view = None
    if args.view:
        with open(args.view, encoding="utf-8") as f:
            view = yaml.safe_load(f)

    render(arch, args.output, view=view)


if __name__ == "__main__":
    main()
