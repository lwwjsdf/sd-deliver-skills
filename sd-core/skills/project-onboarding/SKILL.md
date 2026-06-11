---
name: project-onboarding
version: 1.0.0
description: |
  项目初始化与文档生成。读取 references/ 中的客户文档（SOW、里程碑表、技术方案），
  生成 PROJECT.md、CLARIFICATION.md、DELIVERY.md 等项目档案。
  当用户说"生成项目档案"、"onboard"、"读一下这些文档"时使用。
allowed-tools:
  - Bash
  - Read
---

## 概览

Onboard 流程读取客户文档，生成三份核心项目档案：

| 文件 | 内容 | 用途 |
|------|------|------|
| `PROJECT.md` | 项目背景、交付范围、里程碑、联系人 | AI 上下文，避免重复询问 |
| `CLARIFICATION.md` | 待确认信息跟踪表 | 持续维护直到信息补全 |
| `DELIVERY.md` | 交付物清单 + 进度跟踪 | 里程碑对齐，状态更新 |

## 文档读取方式

| 格式 | 读取方式 |
|------|---------|
| `.md` `.txt` | Read 工具直接读取 |
| `.docx` `.doc` | `python3 shared/read_doc.py <file>` |
| `.pdf` | Read 工具直接读取 |
| `.xlsx` | openpyxl 提取内容 |

## Excel 文件类型判断

| 关键词 | 文件用途 |
|--------|---------|
| Milestone, Deliverable, Phase, Acceptance | 里程碑/项目计划表 → 生成 DELIVERY.md |
| Event, Property, Tracking | 埋点方案 → 记录 TRACKING_PLAN_PATH |
| Cost, Fee, Payment, Budget | 预算表 → 提取付款节点 |

## 交付物 → Command 映射

| 交付物关键词 | 建议 Command |
|------------|-------------|
| 埋点、Tag、Data Collection、Tracking Plan | `/design-tracking` → `/setup-tracking` |
| Technical Solution、Architecture、Design Spec | `/design-tech` |
| SIT、UAT、Test Cases、Test Report | `/run-sit` |
| 数据校验、Data Validation | `/validate-data` |

## 信息澄清

CLARIFICATION.md 跟踪三类信息状态：
- 🔲 待确认 / 待补充 — 尚未处理
- ✅ 已确认 — 用户已核实或补充
- ❌ 不适用 — 确认后发现不需要

技术方案需要提取的澄清项建议使用系统化方法逐类整理。
