#!/usr/bin/env python3
"""
⚠️  已废弃（Deprecated）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
此文件为旧版 JSON 路径，不再维护。所有新项目必须使用 arch.yaml + render.py。
如需迁移旧项目，请使用 migrate.py：
  python3 migrate.py --input old_arch.json --output arch.yaml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

接收架构 JSON 描述，自动计算布局，生成 draw.io XML

架构 JSON 格式：
{
  "title": "图标题",
  "layout": "lr",          # lr=从左到右, tb=从上到下
  "columns": [             # 每列是一个组（自动计算 x 坐标）
    {
      "id": "col_sources",
      "label": "Data Sources",    # 可选，显示为泳道标签
      "container_style": "dashed_green",  # 可选，外框样式
      "nodes": [
        {
          "id": "crm",            # 组件 ID（来自 components.py）或自定义
          "label": "CRM System",  # 覆盖默认 label（可选）
          "future": false,        # 是否为 Future 节点
          "custom": {             # 自定义节点（不在组件库中时使用）
            "color": "client_system",
            "w": 160, "h": 40
          }
        }
      ]
    }
  ],
  "edges": [
    {
      "from": "crm",
      "to": "etl",
      "style": "sftp_batch",      # 来自 STANDARD_EDGES
      "label": "MemberInfo / Transaction",
      "has_pii": true
    }
  ]
}
"""

import json
import sys
import argparse
import uuid
from pathlib import Path
from components import STANDARD_COMPONENTS, COLORS, EDGE_COLORS, STANDARD_EDGES

# ── 布局常量 ─────────────────────────────────────────────────────────────────
COL_GAP = 100        # 列间距
ROW_GAP = 20         # 节点行间距
CONTAINER_PAD = 30   # 容器内边距
CANVAS_X = 40        # 画布起始 X
CANVAS_Y = 40        # 画布起始 Y
LEGEND_X = 1600      # 图例 X 位置


# ── ID 生成 ───────────────────────────────────────────────────────────────────
def gen_id(prefix="node"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ── 样式构建 ─────────────────────────────────────────────────────────────────
def node_style(color_key: str, dashed: bool = False, is_container: bool = False,
               font_size: int = 12, shape: str = None) -> str:
    c = COLORS.get(color_key, COLORS["client_system"])
    fill = c["fill"]
    stroke = c["stroke"]
    dashed_val = "1" if dashed or c.get("dashed") else "0"
    base = (f"rounded=0;whiteSpace=wrap;html=1;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth=2;"
            f"fontSize={font_size};dashed={dashed_val};")
    if is_container:
        base += "verticalAlign=top;"
    if shape:
        base = f"shape={shape};fillColor={fill};strokeColor={stroke};fontSize={font_size};"
    return base


def edge_style(style_key: str, dashed: bool = False) -> str:
    color = EDGE_COLORS.get(style_key, "#666666")
    dash = "1" if dashed else "0"
    return (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
            f"jettySize=auto;html=1;strokeColor={color};strokeWidth=2;"
            f"dashed={dash};exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
            f"entryX=0;entryY=0.5;entryDx=0;entryDy=0;")


# ── XML 元素生成 ──────────────────────────────────────────────────────────────
def xml_node(cell_id: str, value: str, style: str, x: float, y: float,
             w: float, h: float, parent: str = "1") -> str:
    value_escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return (f'        <mxCell id="{cell_id}" value="{value_escaped}" style="{style}" '
            f'vertex="1" parent="{parent}">\n'
            f'          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n'
            f'        </mxCell>\n')


def xml_edge(cell_id: str, source: str, target: str, style: str, label: str = "") -> str:
    label_escaped = label.replace("&", "&amp;").replace("\n", "&#xa;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'        <mxCell id="{cell_id}" value="{label_escaped}" style="{style}" '
            f'edge="1" source="{source}" target="{target}" parent="1">\n'
            f'          <mxGeometry relative="1" as="geometry"/>\n'
            f'        </mxCell>\n')


# ── 图例生成 ─────────────────────────────────────────────────────────────────
def build_legend(x: float, y: float) -> str:
    xml = ""
    legend_items = [
        ("SD Product (CDP/MAE/ETL)", "sd_product", False),
        ("Client System", "client_system", False),
        ("External SaaS", "external_saas", False),
        ("Future Scope (Day 2+)", "future", True),
    ]
    edge_items = [
        ("PII Data Flow (real-time)", "pii_realtime", False),
        ("PII Data Flow (batch)", "pii_batch", True),
        ("Internal Flow (non-PII)", "internal", False),
        ("Kafka Async", "kafka_async", True),
        ("Config / System Data", "config", False),
    ]

    # 图例框
    box_id = gen_id("legend")
    total_h = 30 + len(legend_items) * 28 + 20 + len(edge_items) * 24 + 10
    xml += xml_node(box_id, "Legend",
                    "whiteSpace=wrap;fillColor=#f5f5f5;strokeColor=#666666;verticalAlign=top;fontStyle=1;fontSize=12;",
                    x, y, 260, total_h)

    cy = y + 30
    for label, color_key, dashed in legend_items:
        nid = gen_id("leg")
        xml += xml_node(nid, label, node_style(color_key, dashed, font_size=11), x + 5, cy, 250, 22)
        cy += 28

    cy += 10
    for label, estyle, dashed in edge_items:
        eid = gen_id("legedge")
        color = EDGE_COLORS.get(estyle, "#666666")
        dash = "1" if dashed else "0"
        src_id = gen_id("ls")
        tgt_id = gen_id("lt")
        xml += xml_node(src_id, "", f"fillColor={color};strokeColor={color};", x + 5, cy + 6, 10, 10)
        xml += xml_node(tgt_id, "", f"fillColor={color};strokeColor={color};", x + 65, cy + 6, 10, 10)
        line_id = gen_id("ll")
        xml += (f'        <mxCell id="{line_id}" value="" '
                f'style="edgeStyle=orthogonalEdgeStyle;strokeColor={color};strokeWidth=2;dashed={dash};" '
                f'edge="1" source="{src_id}" target="{tgt_id}" parent="1">\n'
                f'          <mxGeometry relative="1" as="geometry"/>\n'
                f'        </mxCell>\n')
        txt_id = gen_id("lt2")
        xml += xml_node(txt_id, label, "text;html=1;fontSize=11;align=left;", x + 80, cy, 175, 22)
        cy += 24

    return xml


# ── 主构建函数 ────────────────────────────────────────────────────────────────
def build_diagram(arch: dict, output_path: str):
    title = arch.get("title", "Architecture Diagram")
    columns = arch.get("columns", [])
    edges_def = arch.get("edges", [])

    # ID 映射：用户定义的 node id → draw.io cell id
    id_map = {}   # node_id → cell_id
    cells_xml = ""

    # ── 布局计算 ──────────────────────────────────────────────────────────────
    col_x = CANVAS_X
    max_diagram_h = 0

    for col in columns:
        col_nodes = col.get("nodes", [])
        col_label = col.get("label", "")
        has_container = bool(col_label)

        # 计算列宽（取该列最宽节点）
        node_widths = []
        for n in col_nodes:
            comp = STANDARD_COMPONENTS.get(n["id"]) or {}
            custom = n.get("custom", {})
            w = custom.get("w") or comp.get("w") or 160
            node_widths.append(w)
        col_w = max(node_widths) if node_widths else 160
        container_w = col_w + CONTAINER_PAD * 2

        # 计算列内节点 y 坐标
        node_y = CANVAS_Y + (50 if has_container else 0) + CONTAINER_PAD
        node_positions = []
        for n in col_nodes:
            comp = STANDARD_COMPONENTS.get(n["id"]) or {}
            custom = n.get("custom", {})
            h = custom.get("h") or comp.get("h") or 40
            node_positions.append((node_y, h))
            node_y += h + ROW_GAP

        col_h = node_y - CANVAS_Y - ROW_GAP + CONTAINER_PAD
        max_diagram_h = max(max_diagram_h, col_h)

        # 生成容器框
        if has_container:
            container_id = gen_id("col")
            c_style = col.get("container_style", "container")
            cells_xml += xml_node(container_id, f"<b>{col_label}</b>",
                                   node_style(c_style, is_container=True, font_size=15),
                                   col_x, CANVAS_Y, container_w, col_h)

        # 生成节点
        for i, n in enumerate(col_nodes):
            node_id = n["id"]
            comp = STANDARD_COMPONENTS.get(node_id) or {}
            custom = n.get("custom", {})

            label = n.get("label") or comp.get("label") or node_id
            color_key = custom.get("color") or comp.get("color_key") or "client_system"
            w = custom.get("w") or comp.get("w") or 160
            h = custom.get("h") or comp.get("h") or 40
            shape = comp.get("shape")
            is_future = n.get("future") or comp.get("future") or False
            font_size = comp.get("font_size") or custom.get("font_size") or 13
            is_container_node = comp.get("type") == "container"

            node_y_pos, _ = node_positions[i]
            nx = col_x + CONTAINER_PAD
            ny = node_y_pos

            style = node_style(color_key, dashed=is_future,
                               is_container=is_container_node,
                               font_size=font_size, shape=shape)

            cell_id = gen_id(node_id)
            id_map[node_id] = cell_id
            cells_xml += xml_node(cell_id, label, style, nx, ny, w, h)

        col_x += container_w + COL_GAP

    # ── 连线生成 ──────────────────────────────────────────────────────────────
    for e in edges_def:
        from_id = e["from"]
        to_id = e["to"]
        style_key = e.get("style", "internal_flow")
        label = e.get("label", "")
        has_pii = e.get("has_pii", False)
        is_batch = e.get("batch", False)

        # 推断连线样式
        if has_pii and is_batch:
            estyle = "pii_batch"
            dashed = True
        elif has_pii:
            estyle = "pii_realtime"
            dashed = False
        elif style_key == "kafka_async":
            estyle = "kafka_async"
            dashed = True
        else:
            estyle = STANDARD_EDGES.get(style_key, {}).get("style", "internal")
            dashed = STANDARD_EDGES.get(style_key, {}).get("dashed", False)

        src_cell = id_map.get(from_id, from_id)
        tgt_cell = id_map.get(to_id, to_id)
        edge_id = gen_id("edge")
        cells_xml += xml_edge(edge_id, src_cell, tgt_cell,
                               edge_style(estyle, dashed), label)

    # ── 图例 ──────────────────────────────────────────────────────────────────
    legend_xml = build_legend(col_x + 50, CANVAS_Y)

    # ── 组装 XML ──────────────────────────────────────────────────────────────
    xml = f"""<mxfile host="app.diagrams.net">
  <diagram name="{title}" id="{gen_id('diag')}">
    <mxGraphModel dx="1920" dy="1080" grid="1" gridSize="10" guides="1"
                  tooltips="1" connect="1" arrows="1" fold="1" page="1"
                  pageScale="1" pageWidth="1900" pageHeight="1050" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{cells_xml}{legend_xml}      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"✓ Generated: {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    import warnings
    warnings.warn(
        "diagram_builder.py 已废弃。请使用 render.py + arch.yaml。"
        "迁移工具: python3 migrate.py --input old_arch.json --output arch.yaml",
        DeprecationWarning,
        stacklevel=2
    )
    parser = argparse.ArgumentParser(description="draw.io 架构图构建器 [已废弃]")
    parser.add_argument("--arch", required=True, help="架构 JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 .drawio 文件路径")
    args = parser.parse_args()

    with open(args.arch, encoding="utf-8") as f:
        arch = json.load(f)

    build_diagram(arch, args.output)


if __name__ == "__main__":
    main()
