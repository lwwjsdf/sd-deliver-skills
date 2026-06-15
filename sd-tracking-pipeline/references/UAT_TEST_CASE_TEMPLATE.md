# UAT Test Case 模板

复制到项目 `references/uat-test-case.xlsx`，按验收维度分 sheet。

## Sheet 1: Indicators

验证看板/报表指标能否正确计算。

| 列 | 说明 |
|----|------|
| Scenario | 场景分类，如 Traffic / Conversion / Membership |
| Case No. | 用例编号 |
| Indicator Name | 指标名称 |
| Indicator Definition | 指标定义 |
| Related Events | 涉及事件 |
| Formula | 计算公式（AI 推导或人工填写） |
| Expected Result | 期望结果 |
| Tester | 执行人 |
| Test Date | 执行日期 |
| Status | Pass / Fail / Block |
| Bug/Remark | 备注 |

## Sheet 2: ID-Mapping

验证跨端用户归并。

| 列 | 说明 |
|----|------|
| Scenario | 场景，如 MP / Website / Cross-platform |
| Test Case No. | 编号 |
| Test Approach | 测试步骤 |
| Expected Result | 期望结果 |
| Tester | 执行人 |
| Test Date | 执行日期 |
| Status | Pass / Fail / Block |
| Screencap File Name | 截图文件名 |
| Bug/Remark | 备注 |

## Sheet 3: Permissions

验证数据隔离和角色权限。

| 列 | 说明 |
|----|------|
| BU | 业务单元 |
| Data Role Permission | 数据角色 |
| Function Role Permission | 功能角色 |
| Dashboard Permission | 看板权限 |
| Case | 测试场景 |
| Expected Result | 期望结果 |
| Status | Pass / Fail / Block |

## Sheet 4: Paths

验证核心业务流程。

| 列 | 说明 |
|----|------|
| Scenario | 流程名称 |
| Case No. | 编号 |
| Path Steps | 步骤 |
| Expected Events | 期望事件序列 |
| Expected Result | 期望结果 |
| Status | Pass / Fail / Block |

## 示例数据

### Indicators

| Scenario | Case No. | Indicator Name | Indicator Definition | Related Events | Formula | Expected Result |
|----------|----------|----------------|---------------------|----------------|---------|-----------------|
| Traffic | 1 | Website Unique Visitors | UV within period | $pageview | COUNT DISTINCT distinct_id WHERE platformType=Web | Match expected count |
| Conversion | 2 | Purchase Conversion Rate | Orders / Visitors | $pageview, Product_Order_Payment | COUNT(Product_Order_Payment) / COUNT(DISTINCT $pageview.distinct_id) | Match expected rate |

### ID-Mapping

| Scenario | Test Case No. | Test Approach | Expected Result |
|----------|---------------|---------------|-----------------|
| Cross-platform | 1 | Same email logs in MP and Web; query by email | One user record contains both MP and Web events |
