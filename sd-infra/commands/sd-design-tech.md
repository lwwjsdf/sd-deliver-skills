---
name: sd-design-tech
description: 全流程：信息收集 → LLD 框架 → 架构图 → Tech Spec
argument-hint: ""
status: draft
---

# /sd-design-tech — 技术方案设计

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 从信息收集到输出完整技术方案（LLD 框架、架构图、Technical Specification）。
>
> **前置条件：**
> - 项目已初始化（PROJECT.md 存在）
> - 如需架构图，可使用 `/draw-arch`
>
> **执行步骤概览：**
> 1. 信息收集（读取 PROJECT.md，补充 LLD 所需信息）
> 2. LLD 框架（输出完整章节结构，逐节确认）
> 3. 架构图（调用 `/draw-arch`）
> 4. Technical Specification（基于 LLD 生成实施细节）
> 5. 方案确认（标注待定项）
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 前置条件

- 项目已初始化（PROJECT.md 存在）
- 如需架构图，可使用 `/draw-arch`

## 工作流

### Step 1：信息收集

读取 PROJECT.md，补充收集 LLD 所需信息：
- 项目基本信息、业务背景、服务范围
- 系统组件、架构约束、用户类型
- 数据来源、加密要求、技术选型
- 资源规格、软件版本、容量规划

### Step 2：LLD 框架

输出完整章节结构，逐节确认后填充内容。不可省略的核心章节：
- Section 1/2：背景和目标
- Section 3：系统架构
- Section 5：资源需求
- Section 6/7：可用性和 SLA
- Section 10/11：安全和假设

### Step 3：架构图

调用 `/draw-arch` 生成对应的 draw.io 架构图。

### Step 4：Technical Specification

基于已确认的 LLD 生成 Tech Spec。LLD 写做什么，Tech Spec 写怎么做：
- 加密实施细节（DEK 格式、端口号）
- 数据保留策略
- 接口目录
- DR 恢复流程
- 数据转换架构

### Step 5：方案确认

输出最终文档，标注需要客户确认的待定项。

## 完成建议

- "需要画架构图？→ `/draw-arch`"
- "需要评估服务器？→ `/size-server`"
