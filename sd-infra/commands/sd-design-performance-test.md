---
name: sd-design-performance-test
description: 设计 CDP/MAE 性能测试方案：目标 → 场景 → 环境 → 指标 → 计划
argument-hint: ""
status: draft
---

# /sd-design-performance-test — 性能测试方案设计

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 基于业务规模、系统架构和验收要求，设计 CDP/MAE 性能测试方案（Performance Test Plan）。
>
> **前置条件：**
> - 已完成 server-sizing 评估或已知目标生产规模
> - 已了解核心业务流程（实时导入、批量导入、分析查询、MAE 发送等）
> - 已确认 UAT/性能测试环境配置
>
> **执行步骤概览：**
> 1. 确认测试目标与业务规模（用户数、事件量、并发指标）
> 2. 选择测试场景（实时导入、批量导入、事件分析、漏斗分析、Canvas、邮件发送等）
> 3. 设计每个场景的数据准备、测试步骤、预期指标
> 4. 确认测试环境、工具、监控方案
> 5. 输出 performance-test-plan.md
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 工作流

### Step 1：确认测试目标

与客户/PM 确认：
- 生产规模：基线用户数、历史事件总量、日增事件量
- 核心 SLA：
  - 实时导入 QPS
  - 批量导入吞吐量（条/小时）
  - 分析查询响应时间（7 天 / 30 天）
  - MAE 邮件发送吞吐（封/分钟）
- 加密影响评估：是否需量化 PII 加密对性能的影响

### Step 2：选择测试场景

典型场景矩阵：

| 模块 | 场景 | 数据准备 | 测试工具 | 核心指标 |
|------|------|----------|----------|----------|
| CDP | 实时导入 | N 用户 + 单事件属性 | JMeter | QPS、错误率、CPU/内存/磁盘 |
| CDP | 批量导入 | 1000 万事件 CSV/PGP | ETL + 同步工具 | 条/小时、加密耗时 |
| CDP | 事件分析查询 | ≥2 亿事件 | 浏览器/Grafana | 响应时间 ≤ 5s |
| CDP | 漏斗分析查询 | ≥2 亿事件 | 浏览器/Grafana | 响应时间 ≤ 5s |
| MAE | Canvas 执行 | 已导入用户/事件 | CDP UI | 执行时间、规则准确率、同步准确率 |
| MAE | Journey 邮件发送 | 模拟触发事件 | JMeter + Tianwen | 发送 QPS、资源占用 |

### Step 3：设计每个场景

每个场景包含：
- 场景编号（PT-001 ~ PT-XXX）
- 测试目标
- 数据准备（量级、格式、生成方式）
- 测试步骤
- 并发策略（逐步加压：10/20/30/1000/2000/3000...）
- 预期指标（QPS/TPS/响应时间/资源使用率）
- 监控项（Grafana：CPU、内存、磁盘 I/O、网络）

### Step 4：确认环境与工具

- 测试环境地址（CDP Login、数据接入端点、加密服务端口）
- 服务器硬件配置（SA/SF 节点、负载生成器）
- 组件版本（CDP、MAE）
- 压测工具（JMeter、浏览器）
- 监控工具（Grafana）
- SFTP / KMS / 邮件服务依赖

### Step 5：输出 Performance Test Plan

输出到 `references/performance-test-plan.md`：

```markdown
# Performance Test Plan — <client>

## 1. Introduction / Purpose
## 2. Objective
## 3. Scope of Testing
| No. | Module | Scenario | Data Preparation | Test Steps | Expected Metrics |
## 4. Expected Outcomes
## 5. Testing Environment
- Server Hardware
- Load Generator Hardware
- Component Versions
- Environment Addresses
- SFTP / Encryption Info
- Firewall Whitelist
## 6. Test Assumptions and Risks
## 7. Test Execution
- Entry Criteria
- Exit Criteria
- Suspension / Resumption Criteria
## 8. Roles and Responsibilities
## 9. Schedule
## 10. Appendix
```

## 完成建议

- "Performance Test Plan 已确认？→ 执行 `/sd-run-performance-test`"
- "需要先准备压测数据？→ `/sd-generate-mock-data`"
- "容量规划未完成？→ `/sd-size-servers`"
