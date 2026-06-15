---
name: sit-testing
version: 1.1.0
description: |
  系统集成测试知识。项目上线前执行 SIT，验证各模块间数据流转和功能集成正确性。
  当讨论系统集成测试、模块验证、数据流转、SIT Test Case 时自动加载。
allowed-tools:
  - Bash
  - Read
  - Write
---

## 核心原则

**必须先完成测试用例设计并确认覆盖范围，再开始执行。**

## 测试流程

### Phase 1：测试范围确认

- 本次测试覆盖的业务场景列表
- 每个场景的验收标准
- 测试环境信息（URL、账号、数据）
- 测试截止时间和上线条件

### Phase 2：测试用例设计

每条用例包含：
- Test Case ID（TC-001, TC-002...）
- Release Number
- Test Case Description
- Precondition
- Step Number and Description
- Expected Result
- 涉及事件/属性
- 优先级（P0/P1/P2）

优先级定义：
- P0：阻塞上线
- P1：重要功能
- P2：一般功能

### Phase 3：执行验证

按用例逐条执行，记录实际结果，标记通过/失败/阻塞。

### Phase 4：报告输出

汇总测试结果，输出测试报告（总用例数、通过率、失败清单、上线建议）。

## SIT Test Case Excel 结构

推荐一个场景一个 sheet，或统一 sheet：

| Release Number | Test Case Description | Test Case ID | Precondition | Step Number and Description | Expected Result | Priority | Status |
|----------------|----------------------|--------------|--------------|----------------------------|-----------------|----------|--------|
| 1.0.0 | Verify event capture | TC1.1 | Environment ready | 1. Trigger event on MP | Event appears in CDP within 5s | P0 | Pass |

## 常见问题

**客户要求跳过用例设计：** 解释没有用例无法出具正式测试报告。最少也要有一个场景清单。

**测试环境数据不足：** 使用 `/sd-generate-mock-data` 生成模拟数据。

**P0 用例失败但客户坚持上线：** 书面记录风险，要求客户签字确认。

## 关联 command

- `/sd-design-sit` — 设计 SIT Plan
- `/sd-generate-test-cases` — 从埋点方案生成 SIT/UAT test case Excel
- `/sd-run-sit` — 执行 SIT
