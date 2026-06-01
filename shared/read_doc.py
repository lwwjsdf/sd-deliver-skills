#!/usr/bin/env python3
"""
read_doc.py — 读取 .doc / .docx 文件内容，输出纯文本

用法：
    python3 read_doc.py <file.doc>
    python3 read_doc.py <file.docx>

支持：
    .docx — 使用 python-docx 解析
    .doc  — 使用 textutil (macOS) 解码 quoted-printable HTML
"""

import html
import quopri
import re
import subprocess
import sys
from pathlib import Path


def read_docx(path: str) -> str:
    try:
        import docx
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return _fallback_textutil(path)


def read_doc(path: str) -> str:
    """读取旧版 .doc 文件（含 Confluence 导出的 HTML-in-doc 格式）"""
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", path],
        capture_output=True,
    )
    if result.returncode != 0:
        return f"[无法读取 {Path(path).name}：textutil 不可用，请手动转换为 .txt]"

    raw = result.stdout
    # Decode quoted-printable encoding (common in Confluence exports)
    try:
        decoded = quopri.decodestring(raw).decode("utf-8", errors="ignore")
    except Exception:
        decoded = raw.decode("utf-8", errors="ignore")

    # Extract only the HTML body content, skip MIME headers
    # Find the actual HTML content after MIME boundaries
    html_match = re.search(r'<html[^>]*>(.*?)</html>', decoded, re.DOTALL | re.IGNORECASE)
    if html_match:
        decoded = html_match.group(0)

    # Strip all HTML tags
    text = re.sub(r"<style[^>]*>.*?</style>", " ", decoded, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    # Remove CSS/JS artifacts
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"#[A-Za-z0-9_-]+\{[^}]*\}", " ", text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove lines that are just numbers or single chars (image dimensions etc)
    lines = [l for l in text.split("\n") if len(l.strip()) > 3]
    return "\n".join(lines).strip()


def _fallback_textutil(path: str) -> str:
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", path],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else \
        f"[无法读取 {Path(path).name}]"


def read_document(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    elif suffix == ".doc":
        return read_doc(path)
    else:
        return f"[不支持的格式: {suffix}，请转换为 .txt 或 .md]"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 read_doc.py <file.doc|file.docx>")
        sys.exit(1)
    print(read_document(sys.argv[1]))
