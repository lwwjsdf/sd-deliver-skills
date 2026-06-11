---
name: sd-onboard
description: 读取 references/ 文档，生成 PROJECT.md、CLARIFICATION.md、DELIVERY.md
argument-hint: "[client-name]"
---

# /sd-onboard — 初始化项目档案

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 读取客户 reference 文档，自动生成 PROJECT.md（项目档案）、CLARIFICATION.md（澄清跟踪）、DELIVERY.md（交付进度）三个文件。
>
> **前置条件：**
> - 已通过 `sdeliver init <client-name>` 创建客户项目目录
> - 客户文档已放入 `~/projects/<client-name>/references/`
>
> **执行步骤概览：**
> 1. 列出并确认 references/ 中的文档清单
> 2. 读取文档并分类（里程碑、埋点方案、预算等）
> 3. 生成 PROJECT.md（项目背景、范围、里程碑）
> 4. 生成 CLARIFICATION.md（待确认信息清单）
> 5. 生成 DELIVERY.md（交付物清单 + 进度跟踪）
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 前置条件

- 项目目录中存在 `.env` 文件（以 `.env` 所在目录为项目根目录，不强制要求 `~/projects/<client-name>` 路径）
- 客户文档已放入 `<project-root>/references/`
- `.env` 中 `CLIENT_NAME` 已填写

## 工作流

### Step 0：检测现有档案（防重复）

执行前先检查项目根目录是否已存在 PROJECT.md / CLARIFICATION.md / DELIVERY.md：
- 若三文件均已存在且较新（与 references/ 文档相比），直接输出当前档案状态，询问是否重新生成
- 若部分存在，提示用户并询问覆盖策略
- 若不存在，进入 Step 1

**避免在文件已存在时仍走完整确认流程。**

### Step 1：确认文档清单

列出 `references/` 中的所有文件，告知用户将要读取的内容，确认后继续。

### Step 2：读取文档并分类

按文件格式选择读取方式（见 project-onboarding Skill），判断每个文件用途：
- 里程碑/项目计划表 → 提取里程碑和交付物
- 埋点方案 → 记录路径
- 预算表 → 提取付款节点

### Step 3：生成 PROJECT.md

写入 PROJECT.md（项目背景、交付范围、里程碑、技术约束、联系人）。

### Step 4：生成 CLARIFICATION.md

同步生成 CLARIFICATION.md（信息澄清跟踪表），输出澄清列表给用户确认。

### Step 5：生成 DELIVERY.md

基于里程碑表生成 DELIVERY.md（交付物清单 + 进度跟踪），包含交付物 → Command 映射。

### Step 6：输出摘要

```
项目档案已生成：
  - PROJECT.md → 项目背景、交付范围
  - CLARIFICATION.md → <N> 项待确认信息
  - DELIVERY.md → <N> 个交付物条目
```

建议下一步：`/status` 查看项目状态。
