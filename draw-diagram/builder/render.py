#!/usr/bin/env python3
"""
架构图渲染器：从 arch.yaml 严格生成 draw.io XML
所有视觉决策（颜色/线型/坐标）由语义规则推导，不接受外部视觉指令

用法：
  python3 render.py --arch arch.yaml --output diagram.drawio [--view logical]
"""

import yaml
import uuid
import argparse
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

DEFAULT_NODE_W = 160
DEFAULT_NODE_H = 44
COL_GAP = 100
ROW_GAP = 16
CONTAINER_PAD_X = 20
CONTAINER_PAD_Y = 40
START_X = 60
START_Y = 60


def compute_layout(nodes: list, groups: list) -> dict:
    """
    自动布局：
    - 有 group 的节点：按 group 聚合成列
    - 无 group 的节点：各自独立成列
    返回 {node_id: (x, y, w, h)}
    """
    # 建立 group → node 映射
    group_nodes: dict[str, list] = {}
    ungrouped = []
    node_map = {n["id"]: n for n in nodes}

    for n in nodes:
        gid_val = n.get("group")
        if gid_val:
            group_nodes.setdefault(gid_val, []).append(n["id"])
        else:
            ungrouped.append(n["id"])

    # 列顺序：按 groups 定义顺序 + ungrouped 各自追加
    group_order = [g["id"] for g in groups]
    # ungrouped 中每个 node 单独一列
    columns = [(g, group_nodes.get(g, [])) for g in group_order if g in group_nodes]
    for nid in ungrouped:
        columns.append((None, [nid]))

    positions = {}
    col_x = START_X

    for group_id, node_ids in columns:
        # 计算列宽
        col_w = max(
            (node_map[nid].get("props", {}).get("w") or DEFAULT_NODE_W for nid in node_ids),
            default=DEFAULT_NODE_W
        )

        node_y = START_Y + CONTAINER_PAD_Y
        for nid in node_ids:
            n = node_map[nid]
            vtype = n.get("type", "client_system")
            visual = NODE_VISUAL.get(vtype, NODE_VISUAL["client_system"])
            w = n.get("props", {}).get("w") or visual.get("w") or DEFAULT_NODE_W
            h = n.get("props", {}).get("h") or visual.get("h") or DEFAULT_NODE_H
            positions[nid] = (col_x + CONTAINER_PAD_X, node_y, w, h)
            node_y += h + ROW_GAP

        col_x += col_w + CONTAINER_PAD_X * 2 + COL_GAP

    return positions


# ── 样式字符串构建 ────────────────────────────────────────────────────────────

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

def render(arch: dict, output_path: str):
    nodes  = arch.get("nodes", [])
    groups = arch.get("groups", [])
    edges  = arch.get("edges", [])
    title  = arch.get("meta", {}).get("title", "Architecture")

    positions = compute_layout(nodes, groups)
    node_map  = {n["id"]: n for n in nodes}
    group_map = {g["id"]: g for g in groups}

    # node_id → draw.io cell_id
    id_map: dict[str, str] = {}
    cells_xml = ""

    # 渲染分组容器框
    for g in groups:
        gid_str = g["id"]
        gtype   = g.get("type", "data_sources")
        members = g.get("contains", [])
        if not members:
            continue

        # 计算容器边界（包住所有成员节点）
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
        x, y, w, h = pos

        style  = node_style_str(vtype, is_future, shape=shape)
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
    p = argparse.ArgumentParser(description="从 arch.yaml 生成 draw.io 架构图")
    p.add_argument("--arch",   required=True, help="arch.yaml 路径")
    p.add_argument("--output", required=True, help="输出 .drawio 文件路径")
    args = p.parse_args()

    with open(args.arch, encoding="utf-8") as f:
        arch = yaml.safe_load(f)
    render(arch, args.output)


if __name__ == "__main__":
    main()
