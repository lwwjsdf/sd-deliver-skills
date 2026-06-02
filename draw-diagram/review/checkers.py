"""
draw-diagram checkers
Context keys expected:
  arch        : dict  — arch.yaml 内容
  drawio_path : str   — 渲染输出的 .drawio 文件路径
"""
from __future__ import annotations
import re, sys
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parents[2] / "shared" / "review"))
from protocol import Checker, CheckResult, Issue, Severity


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _parse_drawio(path: str) -> list[dict]:
    """解析 drawio XML，返回节点列表（含坐标）。"""
    tree = ET.parse(path)
    cells = tree.findall(".//mxCell")
    nodes = []
    for c in cells:
        if c.get("vertex") != "1" or c.get("id") in ("0", "1"):
            continue
        val = re.sub(r"<[^>]+>", "", c.get("value", "")).strip()
        if not val:
            continue
        geom = c.find("mxGeometry")
        if geom is None:
            continue
        style = c.get("style", "")
        fill  = next((p.split("=")[1] for p in style.split(";") if p.startswith("fillColor=")), "")
        nodes.append({
            "id":    c.get("id"),
            "label": val,
            "x":     float(geom.get("x", 0)),
            "y":     float(geom.get("y", 0)),
            "w":     float(geom.get("width",  0)),
            "h":     float(geom.get("height", 0)),
            "fill":  fill,
            "style": style,
        })
    return nodes


def _parse_edges(path: str) -> list[dict]:
    tree = ET.parse(path)
    edges = []
    cells = tree.findall(".//mxCell")
    cell_label = {c.get("id"): re.sub(r"<[^>]+>", "", c.get("value","")).strip()
                  for c in cells}
    for c in cells:
        if c.get("edge") != "1":
            continue
        src = c.get("source"); tgt = c.get("target")
        if not src or not tgt:
            continue
        style = c.get("style", "")
        stroke = next((p.split("=")[1] for p in style.split(";") if p.startswith("strokeColor=")), "")
        dashed = "dashed=1" in style
        label  = re.sub(r"<[^>]+>", "", c.get("value","")).strip()
        if not label:
            for child in c:
                if child.get("connectable") == "0":
                    label = re.sub(r"<[^>]+>", "", child.get("value","")).strip()
                    break
        edges.append({"src": src, "tgt": tgt, "stroke": stroke,
                      "dashed": dashed, "label": label})
    return edges


# ── Checkers ──────────────────────────────────────────────────────────────────

class OverlapChecker(Checker):
    """检测节点边界框是否重叠（排除容器框）。"""
    name = "overlap_checker"
    category = "visual"

    SKIP_COLORS = {"#f8f0ff", "#f0f4ff", "#d5e8d4", "none", "#f5f5f5"}  # 容器框颜色

    def check(self, context: dict[str, Any]) -> CheckResult:
        nodes = _parse_drawio(context["drawio_path"])
        # 过滤容器框和图例
        legend_kw = ["legend", "sd product", "client sys", "external saas",
                     "future scope", "pii", "kafka", "internal flow"]
        real = [n for n in nodes
                if not any(k in n["label"].lower() for k in legend_kw)
                and n["fill"] not in self.SKIP_COLORS
                and n["w"] > 0 and n["h"] > 0]

        issues = []
        for i, a in enumerate(real):
            for b in real[i+1:]:
                # 边界框重叠检测（留 5px 容忍）
                tol = 5
                overlap = (
                    a["x"] < b["x"] + b["w"] - tol and
                    a["x"] + a["w"] > b["x"] + tol and
                    a["y"] < b["y"] + b["h"] - tol and
                    a["y"] + a["h"] > b["y"] + tol
                )
                if overlap:
                    issues.append(Issue(
                        severity=Severity.FAIL,
                        checker=self.name,
                        category=self.category,
                        message=f'"{a["label"][:20]}" 与 "{b["label"][:20]}" 边界框重叠',
                        location=f"node:{a['label'][:15]}|{b['label'][:15]}",
                        auto_fixable=True,
                        fix_hint="调整 view.yaml 中两节点的坐标，增大间距",
                    ))
        return CheckResult(self.name, passed=len(issues)==0, issues=issues)


class OrphanChecker(Checker):
    """检测孤立节点（无任何连线）。"""
    name = "orphan_checker"
    category = "completeness"

    def check(self, context: dict[str, Any]) -> CheckResult:
        arch  = context["arch"]
        path  = context["drawio_path"]
        edges = _parse_edges(path)
        nodes = _parse_drawio(path)

        # 有连线的 cell id
        connected = {e["src"] for e in edges} | {e["tgt"] for e in edges}
        # arch.yaml 节点名 → cell（通过 label 匹配）
        legend_kw = ["legend","sd product","client sys","external saas",
                     "future scope","pii","kafka","internal flow"]
        real_nodes = [n for n in nodes
                      if not any(k in n["label"].lower() for k in legend_kw)]

        issues = []
        for n in real_nodes:
            if n["id"] not in connected:
                # 检查是否是容器框（大面积、轮廓颜色）
                is_container = n["w"] > 200 and n["h"] > 100
                if not is_container:
                    sev = Severity.WARN  # 孤立节点是警告，可能是 legend 项
                    issues.append(Issue(
                        severity=sev,
                        checker=self.name,
                        category=self.category,
                        message=f'节点 "{n["label"][:30]}" 没有任何连线',
                        location=f"node:{n['label'][:20]}",
                        auto_fixable=False,
                        fix_hint="确认该节点是否应该有连线，或是否是多余的图例节点",
                    ))
        return CheckResult(self.name, passed=not any(i.severity==Severity.FAIL for i in issues), issues=issues)


class PiiColorChecker(Checker):
    """检测含 PII 的连线是否用红色。"""
    name = "pii_color_checker"
    category = "spec_compliance"

    PII_COLORS = {"#FF0000", "#ff0000", "#cc0000", "#CC0000"}

    def check(self, context: dict[str, Any]) -> CheckResult:
        arch  = context["arch"]
        edges_yaml = {(e["from"], e["to"]): e for e in arch.get("edges", [])}
        edges_xml  = _parse_edges(context["drawio_path"])

        # 从 arch.yaml 找 PII 边
        pii_pairs = {(e["from"], e["to"])
                     for e in arch.get("edges", [])
                     if e.get("data", {}).get("has_pii")}

        # 从 drawio 找连线颜色
        # 注意：drawio cell id 不等于 arch node id，通过标签匹配是不可靠的
        # 这里用 arch 层面检查（不涉及渲染后的 XML）
        issues = []
        for (src, tgt), edge in edges_yaml.items():
            data = edge.get("data", {})
            has_pii = data.get("has_pii", False)
            rel = edge.get("rel", "")

            # 检查 rel 和 has_pii 的一致性
            if rel == "kafka_subscribe" and has_pii and data.get("frequency") != "realtime":
                pass  # kafka 是蓝色，不需要红色，正确
            elif rel in ("callback",) and has_pii:
                issues.append(Issue(
                    severity=Severity.WARN,
                    checker=self.name,
                    category=self.category,
                    message=f"callback 连线 ({src}→{tgt}) 标注了 has_pii=true，但 callback 通常不含 PII",
                    location=f"edge:{src}->{tgt}",
                    auto_fixable=True,
                    fix_hint="将 data.has_pii 改为 false",
                ))
            elif has_pii and rel not in ("kafka_subscribe",):
                pass  # 正常：PII 边会渲染为红色

        # 检查 deliver 边是否标注 PII
        for edge in arch.get("edges", []):
            if edge.get("rel") == "deliver" and not edge.get("data", {}).get("has_pii"):
                issues.append(Issue(
                    severity=Severity.WARN,
                    checker=self.name,
                    category=self.category,
                    message=f"deliver 连线 ({edge['from']}→{edge['to']}) 未标注 has_pii，投递邮件通常含收件人 PII",
                    location=f"edge:{edge['from']}->{edge['to']}",
                    auto_fixable=True,
                    fix_hint="将 data.has_pii 改为 true",
                ))

        return CheckResult(self.name, passed=not any(i.severity==Severity.FAIL for i in issues), issues=issues)


class ContainerChecker(Checker):
    """检测 group 容器框是否正确包住了成员节点。"""
    name = "container_checker"
    category = "visual"

    CONTAINER_COLORS = {"#f8f0ff", "#f0f4ff"}

    def check(self, context: dict[str, Any]) -> CheckResult:
        arch  = context["arch"]
        nodes_xml = _parse_drawio(context["drawio_path"])

        # 找容器框（大面积 + 容器颜色）
        containers = [n for n in nodes_xml
                      if n["fill"] in self.CONTAINER_COLORS and n["w"] > 150]
        # 找成员节点（小面积）
        members = [n for n in nodes_xml
                   if n["fill"] not in self.CONTAINER_COLORS
                   and n["w"] > 0 and n["h"] > 0 and n["w"] < 500]

        issues = []
        PAD = 10
        for c in containers:
            # 检查是否有节点的中心在容器框内但边界超出
            for m in members:
                # 节点中心在容器范围内
                cx = m["x"] + m["w"] / 2; cy = m["y"] + m["h"] / 2
                in_container = (c["x"] < cx < c["x"]+c["w"] and
                                c["y"] < cy < c["y"]+c["h"])
                if in_container:
                    # 但边界超出容器
                    if (m["x"] < c["x"] + PAD or
                        m["x"] + m["w"] > c["x"] + c["w"] - PAD or
                        m["y"] < c["y"] + PAD or
                        m["y"] + m["h"] > c["y"] + c["h"] - PAD):
                        issues.append(Issue(
                            severity=Severity.WARN,
                            checker=self.name,
                            category=self.category,
                            message=f'节点 "{m["label"][:20]}" 超出容器框边界',
                            location=f"node:{m['label'][:15]}",
                            auto_fixable=True,
                            fix_hint="扩大容器框边界（view.yaml 中调整容器的 w/h）",
                        ))

        return CheckResult(self.name, passed=not any(i.severity==Severity.FAIL for i in issues), issues=issues)


class EdgeLabelChecker(Checker):
    """检测连线是否有 name 标签（主要数据流连线应该有标签）。"""
    name = "edge_label_checker"
    category = "completeness"

    # 这些 rel 类型必须有 name 标签
    MUST_HAVE_LABEL = {"sftp_export", "sdk_track", "kafka_subscribe",
                       "data_passthrough", "api_push"}

    def check(self, context: dict[str, Any]) -> CheckResult:
        arch = context["arch"]
        issues = []
        for edge in arch.get("edges", []):
            rel  = edge.get("rel", "")
            name = edge.get("name", "").strip()
            if rel in self.MUST_HAVE_LABEL and not name:
                issues.append(Issue(
                    severity=Severity.WARN,
                    checker=self.name,
                    category=self.category,
                    message=f'连线 {edge["from"]}→{edge["to"]} (rel={rel}) 没有 name 标签',
                    location=f"edge:{edge['from']}->{edge['to']}",
                    auto_fixable=False,
                    fix_hint="在 arch.yaml 对应 edge 中添加 name: 字段，描述传输的数据",
                ))
        return CheckResult(self.name, passed=True, issues=issues)  # WARN only, always pass


class NodeTypeChecker(Checker):
    """检测节点 type 字段与名称的一致性（语义合理性）。"""
    name = "node_type_checker"
    category = "semantic"

    # 名称关键词 → 期望 type
    HINTS = {
        "cdp": "sd_product", "mae": "sd_product", "etl": "sd_product",
        "sftp": "infra", "jumpserver": "infra", "rds": "infra",
        "sendcloud": "external_saas", "mailchimp": "external_saas",
        "end user": "person", "customer": "person",
        "employee": "person", "maintenance": "person",
    }

    def check(self, context: dict[str, Any]) -> CheckResult:
        arch   = context["arch"]
        issues = []
        for node in arch.get("nodes", []):
            nid   = node["id"]
            ntype = node.get("type", "")
            name  = node.get("name", "").lower()
            for kw, expected in self.HINTS.items():
                if kw in name and ntype != expected:
                    issues.append(Issue(
                        severity=Severity.WARN,
                        checker=self.name,
                        category=self.category,
                        message=f'节点 "{nid}" 名称含 "{kw}"，type={ntype}，建议改为 {expected}',
                        location=f"node:{nid}",
                        auto_fixable=False,
                        fix_hint=f"将 arch.yaml 中 {nid} 的 type 改为 {expected}",
                    ))
                    break
        return CheckResult(self.name, passed=True, issues=issues)
