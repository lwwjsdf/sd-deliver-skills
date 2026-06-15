---
name: uat-testing
version: 1.1.0
description: |
  用户验收测试知识。验证埋点方案、看板指标、ID-Mapping、权限隔离是否被正确实施。
  由客户主导，业务分析师协助执行。前置依赖数据管道自动化校验报告。
  当讨论验收测试、UAT、UAT Test Case、客户验收时自动加载。
allowed-tools:
  - Bash
  - Read
  - Write
---

## 核心原则

**UAT 由客户主导，交付团队提供支持。**

## 前置依赖

- 埋点方案已确认（tracking-plan.xlsx）
- 数据管道已完成（/sd-setup-tracking 校验报告）
- 看板已创建

## 测试流程

### Phase 1：验收确认

- 确认验收范围（与埋点方案一致）
- 确认测试账号（固定账号 UAT-001 ~ UAT-N）
- 确认验收标准

### Phase 2：用例执行

用户按 UAT 脚本逐条验证：
- 事件触发是否符合方案
- 属性值是否正确
- 看板数据是否合理
- ID-Mapping 是否正确
- 权限隔离是否生效

### Phase 3：缺陷跟踪

- 记录缺陷（环境、步骤、预期、实际）
- 分类：数据问题 / 方案问题 / 开发问题

### Phase 4：上线建议

基于 UAT 结果给出上线建议。

## UAT Test Case Excel 结构

按验收维度分 sheet：

### Sheet: Indicators

| Scenario | Case No. | Indicator Name | Indicator Definition | Related Events | Formula | Expected Result | Tester | Test Date | Status |
|----------|----------|----------------|---------------------|----------------|---------|-----------------|--------|-----------|--------|
| Traffic | 1 | Website UV | Unique visitors | $pageview | COUNT DISTINCT distinct_id | One record | | | |

### Sheet: ID-Mapping

| Scenario | Case No. | Test Approach | Expected Result | Tester | Test Date | Status |
|----------|----------|---------------|-----------------|--------|-----------|--------|
| MP | 1 | Query by email in Users Look-Up | One record, $identity_email has value | | | |

### Sheet: Permissions

| BU | Data Role | Function Role | Dashboard | Case | Expected Result | Status |
|----|-----------|---------------|-----------|------|-----------------|--------|
| M+ | M+ Data Only | Dashboard Viewer | M+ All Dashboard | Data isolation | Only M+ data visible | |

## 关联 command

- `/sd-design-uat` — 设计 UAT Test Case
- `/sd-generate-test-cases` — 从埋点方案生成 UAT test case Excel
- `/sd-run-uat` — 执行 UAT
