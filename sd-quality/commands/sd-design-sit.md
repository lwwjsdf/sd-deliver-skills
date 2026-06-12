---
name: sd-design-sit
description: 设计 SIT Plan：测试范围 → 用例设计 → 数据准备 → 输出测试计划
argument-hint: ""
status: draft
---

# /sd-design-sit — SIT Plan 设计

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 基于系统状态和 Tracking Plan，设计 SIT（系统集成测试）Plan，包含测试范围、用例设计、数据准备要求。
>
> **前置条件：**
> - 系统已部署
> - 数据管道已完成（`/sd-setup-tracking`）
>
> **执行步骤概览：**
> 1. 确认测试范围（业务场景、验收标准）
> 2. 设计测试用例（按场景拆解 TC-001 ~ TC-XXX）
> 3. 确认数据准备和测试环境
> 4. 输出 sit-plan.md
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 工作流

### Step 1：测试范围确认

与客户/PM 确认：
- 业务场景列表
- 验收标准
- 环境信息（URL、测试账号）
- 测试截止时间

### Step 2：测试用例设计

每个业务场景拆解为若干测试用例（TC-001, TC-002...）：
- 前置条件
- 测试步骤
- 期望结果
- 涉及事件/属性
- 优先级（P0/P1/P2）

等待客户/PM 确认用例覆盖范围。

### Step 3：数据准备

- 确认 mock_data 是否就绪
- 确认测试账号可用
- 确认元数据已导入

### Step 4：输出 SIT Plan

输出到 `references/sit-plan.md`：

```markdown
# SIT Plan — <client>

## 测试环境
- CDP: <SA_HOST>
- 项目: <SA_PROJECT>
- 截止时间: YYYY-MM-DD

## 测试用例
| ID | 场景 | 前置条件 | 步骤 | 期望结果 | 优先级 |
|----|------|----------|------|----------|--------|
| TC-001 | ... | ... | ... | ... | P0 |

## 数据准备
- mock_data: ...
- 测试账号: ...

## 通过标准
- 所有 P0 通过
- P1 通过 ≥ 90%
```

## 完成建议

- "SIT Plan 设计完成？→ 执行 `/sd-run-sit`"
- "需要设计 UAT Test Case？→ `/sd-design-uat`"
