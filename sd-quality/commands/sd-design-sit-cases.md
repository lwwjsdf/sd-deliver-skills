---
name: sd-design-sit-cases
description: 从 Tracking Plan 自动生成 SIT Test Case Excel 初稿
argument-hint: "[--tracking-plan path] [--output path]"
status: active
---

# /sd-design-sit-cases — 生成 SIT Test Case Excel

> **定位**：这是 `/sd-design-sit` 工作流中 **Step 2「测试用例设计」** 的自动化工具。
> 它只负责从 Tracking Plan 生成 SIT Test Case 的 Excel 初稿，不替代完整的 SIT Plan 设计。

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 读取 Tracking Plan，自动生成 SIT Test Case Excel 初稿（事件覆盖、属性覆盖、公共属性覆盖）。
>
> **前置条件：**
> - 埋点方案已确认（tracking-plan.xlsx 存在）
> - 已完成 SIT 范围和场景确认（由 `/sd-design-sit` 负责）
>
> **执行步骤概览：**
> 1. 读取 Tracking Plan，提取事件、属性、公共属性
> 2. 按事件/属性生成 SIT Test Case 初稿
> 3. 输出 `sit-test-case.xlsx`
> 4. 用 validator 校验结构
> 5. 等待人工补充业务场景和具体步骤
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 用法

```bash
./venv/bin/python <skill-repo>/sd-quality/scripts/generate_test_cases.py \
  --type sit \
  --tracking-plan ./references/tracking-plan.xlsx \
  --output ./references/sit-test-case.xlsx
```

生成后校验结构：

```bash
./venv/bin/python <skill-repo>/sd-quality/scripts/validate_test_cases.py \
  --type sit \
  --input ./references/sit-test-case.xlsx
```

## 输出文件

- `references/sit-test-case.xlsx` — SIT Test Case 初稿
  - 单 sheet：`SIT Test Cases`
  - 每事件至少一条用例
  - 每事件属性一条用例（区分 P0/P1）
  - 每公共属性一条用例

## 人工 Review 要求

AI 生成的是初稿，必须人工补充：
- 业务场景和具体前置条件
- 详细的操作步骤
- 明确的期望结果
- 最终优先级

## 完成建议

- "SIT Test Case 已 review？→ 回到 `/sd-design-sit` 继续设计完整 Plan"
- "SIT Plan 已确认？→ 执行 `/sd-run-sit`"
- "需要 UAT Test Case？→ `/sd-design-uat-cases`"
