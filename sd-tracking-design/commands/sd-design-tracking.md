---
name: sd-design-tracking
description: 从业务目标确认到输出埋点方案 Excel 的全流程设计
argument-hint: ""
status: draft
---

# /sd-design-tracking — 埋点方案设计

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 从业务目标确认到输出埋点方案 Excel（Events/Details/Users 三个 sheet），交付确认后供 `/setup-tracking` 使用。
>
> **前置条件：**
> - 项目已初始化（PROJECT.md 存在）
> - 了解客户业务场景
>
> **执行步骤概览：**
> 1. 业务目标确认（核心场景、关键问题、分析维度）
> 2. 采集方案设计（事件列表、属性定义、用户属性）
> 3. 输出 Excel（Events/Details/Users 三 sheet）
> 4. 客户确认（必须确认后才能进入 `/setup-tracking`）
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 前置条件

- 项目已初始化（PROJECT.md 存在）
- 了解客户业务场景（如已有 PROJECT.md 则自动读取）

## 工作流

### Step 1：业务目标确认

与用户确认以下四项：
- 核心业务场景
- 关键业务问题（3-5 个）
- 分析维度
- 数据消费方

输出业务目标确认单。

### Step 2：采集方案设计

基于业务目标，设计埋点方案：
1. 定义事件列表（事件名、中文名、触发时机）
2. 为每个事件定义属性（属性名、类型、示例值、是否必填）
3. 定义用户属性（属性名、类型）

### Step 3：输出 Excel

生成埋点方案 Excel，包含三个 sheet：
- Events — 事件列表
- Details — 每个事件的详细属性定义
- Users — 用户属性定义

输出到 `references/tracking-plan.xlsx`。

### Step 4：客户确认

**必须等待客户确认后才能进入 `/setup-tracking`。**

确认后在 `.env` 中设置 `TRACKING_PLAN_PATH`。

## 完成建议

- "方案已确认？接下来可以执行 `/setup-tracking` 进行数据导入"
