#!/usr/bin/env python3
"""
draw.io → arch.yaml + view.yaml 提取器

arch.yaml：语义事实（节点类型/关系类型/PII/frequency）—— 有损推断
view.yaml：视觉信息（精确坐标/尺寸/例外样式）           —— 无损提取

arch.yaml + view.yaml → render.py → drawio  完全幂等还原

用法：
  python3 extract.py --input diagram.drawio --arch arch.yaml --view view.yaml
  python3 extract.py --input diagram.drawio --arch arch.yaml  # 只提取语义
  python3 extract.py --input diagram.drawio --arch arch.yaml --annotate
"""

import xml.etree.ElementTree as ET
import yaml
import argparse
import re
import sys
from pathlib import Path

# ── 颜色 → 节点类型的反向映射 ──────────────────────────────────────────────
# 注意：颜色是不完整的语义信号，置信度标注在旁边
FILL_TO_TYPE = {
    "#d5e8d4": ("sd_product",      "high"),   # 绿色 → 神策产品
    "#fffde7": ("sd_module",       "high"),   # 黄色 → 神策内部模块
    "#fff2cc": ("sd_module",       "high"),   # 黄色变体
    "#e1d5e7": ("client_system",   "medium"), # 紫色 → 客户系统或前端（需人工区分）
    "#dae8fc": ("external_saas",   "high"),   # 蓝色 → 外部 SaaS
    "#FFCE9F": ("person",          "high"),   # 橙色 → 用户
    "#FFCC99": ("person",          "high"),   # 橙色变体
    "#f5f5f5": ("client_system",   "low"),    # 灰色 → 可能是 future 节点（需看 dashed）
    "#e8e8e8": ("client_system",   "medium"), # 灰色变体（通常是 future）
    "none":    ("group_container", "low"),    # 无填充 → 通常是容器框
}

# ── 连线语义推断规则（从 label 关键词推断 rel）──────────────────────────────
# 格式：(正则模式, rel, has_pii, frequency, confidence)
EDGE_LABEL_RULES = [
    (r"kafka|topic|sub.*async",          "kafka_subscribe",  True,  "realtime", "high"),
    (r"sftp.*batch|batch.*daily|t\+1",   "sftp_export",      True,  "daily",    "high"),
    (r"sdk|tracking|behaviour|behavior", "sdk_track",        True,  "realtime", "high"),
    (r"callback|open.*click|click.*open|metrics.*email", "callback", False, "realtime", "high"),
    (r"deliver.*email|personalised.*email", "deliver",       True,  "on-demand","high"),
    (r"api.*call|https.*api",            "api_call",         False, "realtime", "medium"),
    (r"segment|audience|tag.*profile|profile.*tag", "kafka_subscribe", True, "realtime", "medium"),
    (r"passthrough|unified.*data|integration", "data_passthrough", True, "realtime", "medium"),
    (r"visit|access|login",              "user_access",      False, "on-demand","medium"),
]

# ── 节点 label → 语义 ID 的规范化 ─────────────────────────────────────────
LABEL_TO_ID = {
    "cdp": "cdp",
    "mae": "mae",
    "etl": "etl",
    "sftp": "sftp",
    "crm": "crm",
    "sendcloud": "sendcloud",
    "end user": "end_user",
    "end user / customer": "end_user",
    "business user": "business_user",
    "maintenance user": "ops_user",
}

def clean_html(text: str) -> str:
    """去掉 HTML 标签和占位符，保留纯文本。"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#xa;', '\n', text)
    text = re.sub(r'\{\{[^}]+\}\}', '<PLACEHOLDER>', text)
    return text.strip()

def extract_style(style: str) -> dict:
    """解析 style 字符串，提取关键视觉属性。"""
    props = {}
    for part in (style or "").split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            props[k.strip()] = v.strip()
    return props

def infer_type(fill: str, label: str, dashed: bool) -> tuple[str, str]:
    """
    从 fillColor、label、dashed 推断节点语义类型。
    返回 (type, confidence)
    """
    # 先从 label 关键词判断（更可靠）
    label_lower = label.lower()
    if any(k in label_lower for k in ["cdp", "customer data platform"]):
        return "sd_product", "high"
    if any(k in label_lower for k in ["mae", "marketing automation"]):
        return "sd_product", "high"
    if any(k in label_lower for k in ["etl"]):
        return "sd_product", "high"
    if any(k in label_lower for k in ["sftp server"]):
        return "infra", "high"
    if any(k in label_lower for k in ["sendcloud", "mailchimp", "esp"]):
        return "external_saas", "high"
    if any(k in label_lower for k in ["end user", "customer", "employee", "maintenance"]):
        return "person", "high"
    if any(k in label_lower for k in ["mini-program", "miniprogram", "website", "app", "frontend"]):
        return "client_frontend", "medium"

    # 再从颜色判断
    fill_lower = (fill or "").lower().replace(" ", "")
    for color, (ntype, conf) in FILL_TO_TYPE.items():
        if color.lower() == fill_lower:
            # 灰色 + dashed → future
            if fill_lower in ("#e8e8e8", "#f5f5f5") and dashed:
                return "client_system", conf  # type 不变，由 status=future 表达
            return ntype, conf

    return "client_system", "low"  # 默认

def infer_edge(label: str, src_type: str, tgt_type: str) -> dict:
    """
    从 edge label、源节点类型、目标节点类型推断 rel、has_pii、frequency。
    返回 {rel, has_pii, frequency, confidence}
    """
    label_lower = (label or "").lower()

    for pattern, rel, has_pii, freq, conf in EDGE_LABEL_RULES:
        if re.search(pattern, label_lower):
            return {"rel": rel, "has_pii": has_pii, "frequency": freq, "confidence": conf}

    # 基于节点类型组合推断
    if src_type in ("client_system", "client_frontend") and tgt_type == "sd_product":
        return {"rel": "sdk_track", "has_pii": True, "frequency": "realtime", "confidence": "low"}
    if src_type == "sd_product" and tgt_type == "sd_product":
        return {"rel": "kafka_subscribe", "has_pii": True, "frequency": "realtime", "confidence": "low"}
    if src_type == "sd_product" and tgt_type == "external_saas":
        return {"rel": "api_call", "has_pii": True, "frequency": "realtime", "confidence": "low"}
    if src_type == "external_saas" and tgt_type == "person":
        return {"rel": "deliver", "has_pii": True, "frequency": "on-demand", "confidence": "low"}

    return {"rel": "api_call", "has_pii": False, "frequency": "realtime", "confidence": "low"}

def normalize_id(label: str, existing_ids: set) -> str:
    """将 label 转成合法的 snake_case ID，处理重复。"""
    label_clean = re.sub(r'[^a-z0-9\s]', '', label.lower())
    label_clean = re.sub(r'\s+', '_', label_clean.strip())
    label_clean = label_clean[:30].strip('_') or "node"

    # 检查常见标准 ID
    for known_label, known_id in LABEL_TO_ID.items():
        if known_label in label.lower():
            label_clean = known_id
            break

    base = label_clean
    suffix = 1
    while label_clean in existing_ids:
        label_clean = f"{base}_{suffix}"
        suffix += 1
    return label_clean


def extract(drawio_path: str, arch_output: str, view_output: str = None,
            annotate: bool = False):
    """主提取函数。"""
    with open(drawio_path, encoding="utf-8") as f:
        content = f.read()

    root = ET.fromstring(content)
    cells = root.findall(".//mxCell")
    diagram_name = root.find(".//diagram")
    title = diagram_name.get("name", Path(drawio_path).stem) if diagram_name is not None else Path(drawio_path).stem

    nodes_out = []
    edges_out = []
    skipped = []

    # 第一遍：解析所有 vertex
    cell_map = {}  # draw.io cell id → parsed node info
    used_ids = set()

    for cell in cells:
        if cell.get("vertex") != "1":
            continue
        cell_id = cell.get("id", "")
        if cell_id in ("0", "1"):
            continue

        value = cell.get("value", "")
        label = clean_html(value)
        style = extract_style(cell.get("style", ""))

        fill = style.get("fillColor", "none")
        dashed = style.get("dashed") == "1"
        is_edge_label = cell.get("connectable") == "0"

        geom = cell.find("mxGeometry")
        w = float(geom.get("width", 0)) if geom is not None else 0
        h = float(geom.get("height", 0)) if geom is not None else 0

        # 过滤：图例项、edgeLabel、无内容、小尺寸装饰节点
        if is_edge_label:
            continue
        if not label or label == "<PLACEHOLDER>" and not value:
            continue
        if w < 30 or h < 10:  # 太小的节点，可能是图标
            skipped.append({"id": cell_id, "reason": "too_small", "label": label})
            continue
        if any(k in label for k in ["Legend", "legend"]):
            skipped.append({"id": cell_id, "reason": "legend", "label": label})
            continue
        # 过滤图例中的示意节点（label 是描述性文字或颜色示例）
        if any(k in label.lower() for k in [
            "sd's product", "future scope", "data flow containing",
            "batch data flow", "internal data flow", "kafka async",
            "pii realtime", "pii batch", "internal flow",          # render.py 图例
            "sd product", "client system", "external saas",         # render.py 图例节点
        ]):
            skipped.append({"id": cell_id, "reason": "legend_item", "label": label})
            continue

        ntype, conf = infer_type(fill, label, dashed)

        # 跳过纯容器框（无 fill 且面积很大，通常是分组框）
        if ntype == "group_container" or (fill in ("none", "") and w > 200 and h > 150):
            # 作为 group 处理
            cell_map[cell_id] = {
                "is_group": True, "label": label,
                "w": w, "h": h, "dashed": dashed
            }
            continue

        node_id = normalize_id(label, used_ids)
        used_ids.add(node_id)
        status = "future" if dashed and fill in ("#e8e8e8", "#f5f5f5") else "current"

        # 记录坐标（用于 view.yaml）
        geom = cell.find("mxGeometry")
        x = float(geom.get("x", 0)) if geom is not None else 0
        y = float(geom.get("y", 0)) if geom is not None else 0

        node_entry = {
            "id": node_id,
            "name": label.replace("<PLACEHOLDER>", "{{TBD}}"),
            "type": ntype,
            "status": status,
            "_cell_id": cell_id,
            "_x": x, "_y": y, "_w": w, "_h": h,  # 内部用于 view.yaml
        }
        if annotate and conf != "high":
            node_entry["_type_confidence"] = conf
        cell_map[cell_id] = {"node_id": node_id, "type": ntype, "is_group": False}
        nodes_out.append(node_entry)

    # 第二遍：解析所有 edge
    for cell in cells:
        if cell.get("edge") != "1":
            continue
        src_cell = cell.get("source")
        tgt_cell = cell.get("target")

        # 过滤：无 source 或 target（图例中的示意线）
        if not src_cell or not tgt_cell:
            skipped.append({"id": cell.get("id"), "reason": "no_source_or_target"})
            continue

        src_info = cell_map.get(src_cell, {})
        tgt_info = cell_map.get(tgt_cell, {})

        # 跳过指向/来自 group 容器的边（通常是布局辅助线）
        if src_info.get("is_group") or tgt_info.get("is_group"):
            continue

        src_node = src_info.get("node_id")
        tgt_node = tgt_info.get("node_id")
        if not src_node or not tgt_node:
            skipped.append({"id": cell.get("id"), "reason": "node_not_found",
                             "src_cell": src_cell, "tgt_cell": tgt_cell})
            continue

        # 获取 edge label（直接 value 或子 edgeLabel cell）
        edge_label = clean_html(cell.get("value", ""))
        if not edge_label:
            # 找子 cell 中的 edgeLabel
            for child in cell:
                if child.get("connectable") == "0" and child.get("value"):
                    edge_label = clean_html(child.get("value", ""))
                    break

        src_type = src_info.get("type", "client_system")
        tgt_type = tgt_info.get("type", "client_system")

        inferred = infer_edge(edge_label, src_type, tgt_type)

        edge_entry = {
            "from": src_node,
            "to": tgt_node,
            "rel": inferred["rel"],
        }
        if edge_label:
            edge_entry["name"] = edge_label
        edge_entry["data"] = {
            "has_pii": inferred["has_pii"],
            "frequency": inferred["frequency"],
        }
        if annotate and inferred["confidence"] != "high":
            edge_entry["_rel_confidence"] = inferred["confidence"]

        edges_out.append(edge_entry)

    # 构建 view.yaml 数据（从节点坐标提取，无损）
    view_nodes_data = {}
    for n in nodes_out:
        nid = n["id"]
        vx = n.pop("_x", 0); vy = n.pop("_y", 0)
        vw = n.pop("_w", 160); vh = n.pop("_h", 44)
        view_nodes_data[nid] = {"x": round(vx), "y": round(vy),
                                 "w": round(vw), "h": round(vh)}

    # 清理内部字段
    for n in nodes_out:
        n.pop("_cell_id", None)

    arch = {
        "meta": {
            "title": title,
            "client": "{{CLIENT}}",
            "version": "1.0",
            "date": "{{DATE}}",
            "_extraction_note": (
                f"Extracted from {Path(drawio_path).name}. "
                "Review nodes/edges marked with _*_confidence=low/medium."
            ),
        },
        "nodes": nodes_out,
        "edges": edges_out,
    }
    if skipped and annotate:
        arch["_skipped"] = skipped

    with open(arch_output, "w", encoding="utf-8") as f:
        yaml.dump(arch, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=120)
    print(f"✓ arch.yaml → {arch_output}")
    print(f"  nodes: {len(nodes_out)}, edges: {len(edges_out)}, skipped: {len(skipped)}")

    # 输出 view.yaml（可选）
    if view_output:
        view = {
            "meta": {
                "arch": Path(arch_output).name,
                "version": "1.0",
                "last_modified": "{{DATE}}",
                "_note": "Extracted from drawio. Coordinates are exact — do not edit manually.",
            },
            "nodes": view_nodes_data,
            "canvas": {"width": 1900, "height": 1050, "grid": True, "grid_size": 10},
        }
        with open(view_output, "w", encoding="utf-8") as f:
            yaml.dump(view, f, default_flow_style=False, allow_unicode=True,
                      sort_keys=False, width=120)
        print(f"✓ view.yaml → {view_output}")

    # 置信度摘要
    low_conf  = [n for n in nodes_out if n.get("_type_confidence") in ("low", "medium")]
    low_edges = [e for e in edges_out if e.get("_rel_confidence") in ("low", "medium")]
    if low_conf or low_edges:
        print(f"\n  ⚠️  需人工 review（语义推断置信度不足）：")
        for n in low_conf:
            print(f"    node [{n['_type_confidence']}] {n['id']}: type={n['type']}")
        for e in low_edges:
            print(f"    edge [{e['_rel_confidence']}] {e['from']}→{e['to']}: rel={e['rel']}")


def main():
    p = argparse.ArgumentParser(description="draw.io → arch.yaml + view.yaml 提取器")
    p.add_argument("--input",    required=True,  help="输入 .drawio 文件路径")
    p.add_argument("--arch",     required=True,  help="输出 arch.yaml 路径")
    p.add_argument("--view",     default=None,   help="输出 view.yaml 路径（可选，提供则输出精确坐标）")
    p.add_argument("--annotate", action="store_true", help="在 arch.yaml 中标注推断置信度")
    args = p.parse_args()
    extract(args.input, args.arch, view_output=args.view, annotate=args.annotate)


if __name__ == "__main__":
    main()
