#!/usr/bin/env python3
"""
旧 arch.json → 新 arch.yaml 迁移工具
将 diagram_builder.py 使用的 JSON 格式转换为 render.py 使用的 YAML 格式。

用法：
  python3 migrate.py --input old_arch.json --output arch.yaml
"""

import json
import yaml
import argparse
from datetime import datetime
from pathlib import Path

# ── 颜色键 → 语义类型映射（逆向自 diagram_builder.py / render.py）────────────────
COLOR_TO_TYPE = {
    "sd_product": "sd_product",
    "client_system": "client_system",
    "external_saas": "external_saas",
    "future": "client_system",  # future 是状态，不是类型
}

# ── 旧 edge style → (rel, frequency) 映射 ──────────────────────────────────────
STYLE_TO_REL = {
    "sftp_batch":     ("sftp_export",      "daily"),
    "sftp_realtime":  ("sftp_export",      "realtime"),
    "api_push":       ("api_push",         "realtime"),
    "api_realtime":   ("api_call",         "realtime"),
    "sdk_track":      ("sdk_track",        "realtime"),
    "sdk_realtime":   ("sdk_track",        "realtime"),   # 旧 JSON 的 sdk 变体
    "kafka_async":    ("kafka_subscribe",  "realtime"),
    "internal_flow":  ("data_passthrough", "realtime"),   # 需人工 review 是否应改为 deliver
    "callback":       ("callback",         "realtime"),
    "user_access":    ("user_access",      "realtime"),
    "deliver":        ("deliver",          "realtime"),
}


def migrate(arch_json: dict) -> dict:
    """将旧 JSON 架构描述转换为新 YAML 架构描述。"""

    # ── meta ─────────────────────────────────────────────────────────────────
    title = arch_json.get("title", "Architecture Diagram")
    arch_yaml = {
        "meta": {
            "title": title,
            "client": "Migrated",
            "version": "1.0",
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
    }

    # ── nodes & groups ───────────────────────────────────────────────────────
    nodes = []
    groups = []
    group_contains = {}  # group_id -> [node_ids]

    for col in arch_json.get("columns", []):
        col_id = col.get("id", "col")
        col_label = col.get("label", col_id)
        has_container = bool(col_label)

        # 创建 group（如果列有标签）
        if has_container:
            group_id = col_id
            groups.append({
                "id": group_id,
                "name": col_label,
                "type": col.get("container_style", "data_sources"),
                "contains": [],
            })
            group_contains[group_id] = []
        else:
            group_id = None

        for n in col.get("nodes", []):
            node_id = n["id"]
            custom = n.get("custom", {})
            comp_color = custom.get("color", "client_system")

            # 类型推断
            node_type = COLOR_TO_TYPE.get(comp_color, comp_color)

            # future 状态
            is_future = n.get("future", False)
            status = "future" if is_future else "current"

            node = {
                "id": node_id,
                "name": n.get("label", node_id),
                "type": node_type,
                "status": status,
            }

            if group_id:
                node["group"] = group_id
                group_contains[group_id].append(node_id)

            # 自定义尺寸放入 props
            props = {}
            if "w" in custom:
                props["w"] = custom["w"]
            if "h" in custom:
                props["h"] = custom["h"]
            if props:
                node["props"] = props

            nodes.append(node)

    # 回填 groups 的 contains
    for g in groups:
        g["contains"] = group_contains.get(g["id"], [])

    arch_yaml["nodes"] = nodes
    arch_yaml["groups"] = groups

    # ── edges ────────────────────────────────────────────────────────────────
    edges = []
    for e in arch_json.get("edges", []):
        style_key = e.get("style", "internal_flow")
        rel, frequency = STYLE_TO_REL.get(style_key, ("data_passthrough", "realtime"))

        edge = {
            "from": e["from"],
            "to": e["to"],
            "rel": rel,
        }

        if e.get("label"):
            edge["name"] = e["label"]

        # 数据属性
        data = {}
        if e.get("has_pii"):
            data["has_pii"] = True
        if frequency != "realtime":
            data["frequency"] = frequency

        if data:
            edge["data"] = data

        edges.append(edge)

    arch_yaml["edges"] = edges
    return arch_yaml


def main():
    parser = argparse.ArgumentParser(description="arch.json → arch.yaml 迁移工具")
    parser.add_argument("--input", required=True, help="旧 arch.json 文件路径")
    parser.add_argument("--output", required=True, help="输出 arch.yaml 文件路径")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        old_arch = json.load(f)

    new_arch = migrate(old_arch)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        yaml.dump(new_arch, f, allow_unicode=True, sort_keys=False)

    print(f"✓ Migrated: {args.input} → {args.output}")
    print(f"  Nodes: {len(new_arch['nodes'])}")
    print(f"  Groups: {len(new_arch['groups'])}")
    print(f"  Edges: {len(new_arch['edges'])}")


if __name__ == "__main__":
    main()
