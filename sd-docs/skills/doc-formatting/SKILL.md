---
name: doc-formatting
version: 1.0.0
description: |
  业务文档格式化知识。从 Markdown 或结构化数据生成专业格式的
  Word/PDF 交付文档。
  当讨论文档格式、Word 生成、PDF 输出时自动加载。
allowed-tools:
  - Bash
  - Read
  - Write
---

## 用途

将 AI 生成的 Markdown 文档转换为客户交付级的 Word/PDF 文档。

## 支持格式

- Markdown → Word（.docx）
- Markdown → PDF
- 结构化数据 → 文档

## 脚本

```bash
./venv/bin/python <skill-repo>/sd-docs/scripts/generate_business_doc.py \
  --input <input.md> \
  --output <output.docx> \
  --template <template.docx>
```
