---
name: sd-design-uat
description: 设计 UAT Test Case：从业务场景到验收用例 Excel
argument-hint: ""
status: draft
---

# /sd-design-uat — UAT Test Case 设计

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 基于 Tracking Plan 和业务需求，设计 UAT Test Case（uat-test-case.xlsx），并生成 AI 可执行的 uat_test_logic.yaml。
>
> **前置条件：**
> - 埋点方案已确认（`tracking-plan.xlsx` 存在）
> - 了解客户业务场景和验收指标
>
> **执行步骤概览：**
> 1. 读取 Tracking Plan，获取可验收的事件/属性清单
> 2. 与业务分析师确认 UAT 场景和指标
> 3. 生成 uat-test-case.xlsx 初稿
> 4. 自动推导指标计算公式（不确定的标记 needs_review）
> 5. 标记无法自动化的步骤为 manual
> 6. 生成 uat_test_logic.yaml（草稿）
> 7. 等待业务分析师确认后生效
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 工作流

### Step 1：读取 Tracking Plan

从 `tracking-plan.xlsx` 提取：
- 所有事件名和显示名
- 每个事件的属性清单（属性名、类型、枚举值、是否必填）
- 用户属性清单

输出事件/属性清单供后续步骤使用。

### Step 2：确认 UAT 场景

与业务分析师确认验收场景，场景类型包括：

| 场景类型 | 说明 | 示例 |
|----------|------|------|
| **指标验收** | 验证看板/报表指标能否正确计算 | 网站独立访客、页面浏览量、跳出率 |
| **ID-Mapping** | 验证用户 ID 打通是否正确 | 小程序/网站/CRM 的用户统一 |
| **权限验收** | 验证数据隔离和角色权限 | BU 隔离、Dashboard 权限 |
| **流程路径** | 验证核心用户路径 | 浏览→加购→下单→支付 |

### Step 3：生成 uat-test-case.xlsx

调用 `/sd-design-uat-cases` 从 Tracking Plan 自动生成 UAT Test Case Excel 初稿：

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

输出文件包含以下 sheets：

**Scenarios sheet** — 场景清单
| 列 | 说明 |
|----|------|
| scenario_id | 场景 ID |
| scenario_name | 场景名称 |
| scenario_type | indicator / id_mapping / permission / path |
| priority | P0/P1/P2 |
| precondition | 前置条件 |
| notes | 备注 |

**Indicators sheet** — 指标验收用例
| 列 | 说明 |
|----|------|
| scenario_id | 场景 ID |
| case_no | 用例编号 |
| indicator_name | 指标名称 |
| indicator_definition | 指标定义 |
| related_event | 涉及事件 |
| formula | 计算公式（AI 自动推导） |
| confidence | auto_derived / needs_review |
| expected_result | 期望结果 |
| test_status | Pass/Fail/Block |
| bug_remark | 问题备注 |

**IDMapping sheet** — ID 打通验收用例
**Permissions sheet** — 权限验收用例

### Step 4：自动推导指标公式

对于 indicator_type 的用例，AI 自动推导 SQL 计算公式：

```
"Website Unique Visitors"
  → COUNT DISTINCT distinct_id WHERE event='$pageview'

"Daily Active Users"
  → COUNT DISTINCT distinct_id WHERE event='$MPLaunch' per day
```

**推导规则**：
- 明确的事件 + 明确的聚合 → `auto_derived`
- 模糊的描述或需要自定义逻辑 → `needs_review`（标记需确认）
- 不要过度推断

### Step 5：标记手动执行用例

以下类型标记为 `manual`：
- 权限验收（需切换账号）
- 需要人工判断的 UI 验证
- 依赖外部系统的场景

### Step 6：生成 uat_test_logic.yaml

从 Excel 提取生成 AI 可执行的 YAML，结构参见 data-validation skill。

**注意**：YAML 中 `confirmed: false`，只有业务分析师确认后才改为 `true`。

### Step 7：等待确认

输出：
- `references/uat-test-case.xlsx`（由 `/sd-design-uat-cases` 生成，给业务分析师 review）
- `references/uat_test_logic.yaml`（草稿，待确认）
- 标记需要手动确认的项

**确认后**：
- 业务分析师将 `confirmed` 改为 `true`
- `/sd-validate-data` 可以执行 UAT 场景校验

## 完成建议

- "UAT Test Case 初稿已生成？→ 用 `/sd-design-uat-cases` 自动生成 Excel"
- "UAT Test Case 已确认？→ 执行 `/sd-run-uat`"
- "需要 SIT Test Case？→ `/sd-design-sit-cases`"
