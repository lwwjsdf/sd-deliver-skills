---
name: sd-design-uat-cases
description: 从 Tracking Plan 自动生成 UAT Test Case Excel 初稿
argument-hint: "[--tracking-plan path] [--output path]"
status: active
---

# /sd-design-uat-cases — 生成 UAT Test Case Excel

> **定位**：这是 `/sd-design-uat` 工作流中 **Step 3「生成 uat-test-case.xlsx」** 的自动化工具。
> 它只负责从 Tracking Plan 生成 UAT Test Case 的 Excel 初稿，不替代完整的 UAT 场景设计和指标公式确认。

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 读取 Tracking Plan，自动生成 UAT Test Case Excel 初稿（Indicators / ID-Mapping / Permissions / Paths）。
>
> **前置条件：**
> - 埋点方案已确认（tracking-plan.xlsx 存在）
> - 已与业务分析师确认 UAT 场景和验收指标（由 `/sd-design-uat` 负责）
>
> **执行步骤概览：**
> 1. 读取 Tracking Plan，提取事件、属性、用户属性
> 2. 按验收维度生成 UAT Test Case 初稿
> 3. 输出 `uat-test-case.xlsx`
> 4. 用 validator 校验结构
> 5. 等待业务分析师 review 公式和场景
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 用法

```bash
./venv/bin/python <skill-repo>/sd-quality/scripts/generate_test_cases.py \
  --type uat \
  --tracking-plan ./references/tracking-plan.xlsx \
  --output ./references/uat-test-case.xlsx
```

生成后校验结构：

```bash
./venv/bin/python <skill-repo>/sd-quality/scripts/validate_test_cases.py \
  --type uat \
  --input ./references/uat-test-case.xlsx
```

## 输出文件

- `references/uat-test-case.xlsx` — UAT Test Case 初稿
  - `Indicators`：从事件推导常用指标
  - `ID-Mapping`：跨端用户归并验证
  - `Permissions`：数据隔离和角色权限
  - `Paths`：核心业务流程

## 人工 Review 要求

AI 生成的是初稿，必须人工确认：
- 指标定义和计算公式
- 涉及事件和属性
- 期望结果是否可量化
- 手动执行标记

## 完成建议

- "UAT Test Case 已 review？→ 回到 `/sd-design-uat` 继续确认指标公式和 YAML"
- "UAT Test Case 已确认？→ 执行 `/sd-run-uat`"
- "需要 SIT Test Case？→ `/sd-design-sit-cases`"
