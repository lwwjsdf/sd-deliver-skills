---
name: sd-generate-test-cases
description: 从埋点方案/业务规则生成 SIT 或 UAT Test Case Excel
description: 从埋点方案/业务规则生成 SIT 或 UAT Test Case Excel
argument-hint: "[--type sit|uat] [--tracking-plan path] [--output path]"
status: draft
---

# /sd-generate-test-cases — 生成 SIT/UAT Test Case Excel

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 读取 Tracking Plan 和业务规则文档，自动生成 SIT 或 UAT Test Case Excel 初稿。
>
> **前置条件：**
> - 埋点方案已确认（tracking-plan.xlsx 存在）
> - 已明确测试类型（SIT / UAT）
>
> **执行步骤概览：**
> 1. 读取 Tracking Plan，提取事件、属性、用户属性
> 2. 根据测试类型选择模板结构
> 3. 按事件/属性/场景生成 Test Case 初稿
> 4. 输出 Excel 文件
> 5. 等待人工 review 和补充业务场景
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 用法

```bash
# SIT Test Case
./venv/bin/python <skill-repo>/sd-quality/scripts/generate_test_cases.py \
  --type sit \
  --tracking-plan ./references/tracking-plan.xlsx \
  --output ./references/sit-test-case.xlsx

# UAT Test Case
./venv/bin/python <skill-repo>/sd-quality/scripts/generate_test_cases.py \
  --type uat \
  --tracking-plan ./references/tracking-plan.xlsx \
  --output ./references/uat-test-case.xlsx
```

生成后应先用 validator 校验结构：

```bash
./venv/bin/python <skill-repo>/sd-quality/scripts/validate_test_cases.py \
  --type sit \
  --input ./references/sit-test-case.xlsx

./venv/bin/python <skill-repo>/sd-quality/scripts/validate_test_cases.py \
  --type uat \
  --input ./references/uat-test-case.xlsx
```

## 工作流

### Step 1：读取 Tracking Plan

提取：
- Custom Event 列表
- Preset Event 列表
- Public Property 列表
- User Attribute 列表

### Step 2：生成 Test Case

#### SIT 模式

每个事件生成至少一条用例：
- 验证事件可被触发
- 验证事件属性内容/格式/类型/值域
- 验证公共属性携带正确

每个公共属性生成一条用例：
- 验证所有事件均携带该公共属性

每个用户属性生成一条用例：
- 验证用户属性正确上报

#### UAT 模式

按验收维度生成多 sheet：
- **Indicators**：从事件推导常用指标（UV、PV、转化漏斗等）
- **ID-Mapping**：验证跨端用户归并
- **Permissions**：验证 BU/角色/看板权限
- **Paths**：验证核心业务流程

### Step 3：输出 Excel

文件结构：
- SIT：`sit-test-case.xlsx`（单 sheet 或多 sheet）
- UAT：`uat-test-case.xlsx`（多 sheet：Indicators / ID-Mapping / Permissions / Paths）

### Step 4：人工 Review

AI 生成的是初稿，必须人工补充：
- 业务场景描述
- 具体的前置条件
- 详细的操作步骤
- 明确的期望结果
- 优先级

## 输出示例

### SIT Test Case

| Release Number | Test Case Description | Test Case ID | Precondition | Step Number and Description | Expected Result | Priority |
|----------------|----------------------|--------------|--------------|----------------------------|-----------------|----------|
| 1.0.0 | Verify Product_Order_Payment event capture | TC-CUST-001 | MP SDK integrated | 1. Trigger order payment on MP | Event appears in CDP with correct properties | P0 |
| 1.0.0 | Verify ticketsQuantity data type | TC-CUST-002 | Event exists | 1. Check event property type | ticketsQuantity is integer | P0 |

### UAT Test Case

| Scenario | Case No. | Indicator Name | Indicator Definition | Related Events | Formula | Expected Result |
|----------|----------|----------------|---------------------|----------------|---------|-----------------|
| Traffic | 1 | Website UV | Unique visitors within period | $pageview | COUNT DISTINCT distinct_id | Match expected count |

## 完成建议

- "SIT Test Case 已 review？→ 执行 `/sd-run-sit`"
- "UAT Test Case 已 review？→ 执行 `/sd-run-uat`"
- "需要补充性能测试？→ `/sd-design-performance-test`"
