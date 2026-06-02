"""
draw-diagram fixers
每个 fixer 对应一个 checker，修改 context["arch"] 并写回文件。
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
import yaml

sys.path.insert(0, str(Path(__file__).parents[2] / "shared" / "review"))
from protocol import Fixer, Issue


class OverlapFixer(Fixer):
    """
    重叠修复：在 view.yaml 中调整重叠节点的 Y 坐标，增大间距。
    仅当使用 view.yaml 时有效；否则建议重新走 graphviz 布局。
    """
    name = "overlap_checker"

    def fix(self, issues: list[Issue], context: dict[str, Any]) -> tuple[bool, str]:
        view_path = context.get("view_path")
        if not view_path or not Path(view_path).exists():
            return False, "未找到 view.yaml，重叠问题需重新运行 graphviz 布局解决"

        with open(view_path) as f:
            view = yaml.safe_load(f)

        nodes_view = view.get("nodes", {})
        fixed = 0
        for issue in issues:
            # location 格式: "node:A|B"
            if "|" not in issue.location:
                continue
            parts = issue.location.replace("node:", "").split("|")
            if len(parts) != 2:
                continue
            # 找两个节点的 ID（通过 label 前缀匹配）
            a_label, b_label = parts[0].strip(), parts[1].strip()
            a_id = next((k for k in nodes_view if a_label.lower() in k.lower()), None)
            b_id = next((k for k in nodes_view if b_label.lower() in k.lower()), None)
            if not a_id or not b_id:
                continue
            a = nodes_view[a_id]; b = nodes_view[b_id]
            # 把 B 往下移 20px
            nodes_view[b_id]["y"] = b.get("y", 0) + 20
            fixed += 1

        if fixed:
            view["nodes"] = nodes_view
            with open(view_path, "w") as f:
                yaml.dump(view, f, default_flow_style=False, allow_unicode=True)
            return True, f"调整了 {fixed} 个节点的 Y 坐标"
        return False, "未能定位到重叠节点"


class PiiColorFixer(Fixer):
    """
    PII 标注修复：在 arch.yaml 中更新 edge 的 has_pii 字段。
    """
    name = "pii_color_checker"

    def fix(self, issues: list[Issue], context: dict[str, Any]) -> tuple[bool, str]:
        arch      = context["arch"]
        arch_path = context.get("arch_path")
        if not arch_path:
            return False, "未找到 arch_path，无法写回"

        fixed = 0
        for issue in issues:
            # location 格式: "edge:src->tgt"
            if not issue.location.startswith("edge:"):
                continue
            pair = issue.location.replace("edge:", "").split("->")
            if len(pair) != 2:
                continue
            src, tgt = pair[0].strip(), pair[1].strip()

            for edge in arch.get("edges", []):
                if edge.get("from") == src and edge.get("to") == tgt:
                    if "deliver 连线" in issue.message:
                        edge.setdefault("data", {})["has_pii"] = True
                    elif "callback 连线" in issue.message:
                        edge.setdefault("data", {})["has_pii"] = False
                    fixed += 1

        if fixed:
            with open(arch_path, "w") as f:
                yaml.dump(arch, f, default_flow_style=False, allow_unicode=True,
                          sort_keys=False, width=120)
            context["arch"] = arch  # 更新内存中的 arch
            return True, f"修复了 {fixed} 条边的 has_pii 标注"
        return False, "未能定位到需要修复的边"
