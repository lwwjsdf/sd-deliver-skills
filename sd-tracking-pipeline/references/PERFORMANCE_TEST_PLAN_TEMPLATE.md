# Performance Test Case 模板

复制到项目 `references/performance-test-plan.md`，作为 Performance Test Plan 骨架。

## 1. Introduction / Purpose

定义本次性能测试的总体计划和验收标准。

## 2. Objective

- 验证核心业务指标是否满足设计要求
- 评估 PII 加密对性能的影响
- 确认系统并发处理能力和资源上限

## 3. Scope of Testing

| No. | Module | Scenario | Data Preparation | Test Steps | Expected Metrics | Notes |
|-----|--------|----------|------------------|------------|------------------|-------|
| PT-001 | CDP | Real-time Import | 1M users, 58 attrs, 1 event | JMeter incremental concurrency 10/20/30/1000/2000/3000, 10 min each | QPS ≥ 1000, CPU ≤ 80%, Memory ≤ 80%, Disk I/O ≤ 70% | With encryption |
| PT-002 | CDP | Batch Import | 10M events CSV/PGP | ETL download + encrypt + import | ≥ 1M records/hour | |
| PT-003 | CDP | Event Analysis - 7 Days | ≥ 200M events | Query with no global filter, group by daily | Response time ≤ 5s | Cache disabled |
| PT-004 | CDP | Event Analysis - 30 Days | ≥ 200M events | Query with no global filter, group by daily | Response time ≤ 5s | Cache disabled |
| PT-005 | CDP | Funnel Analysis - 7 Days | ≥ 200M events | 3-step funnel, no filter | Response time ≤ 5s | Cache disabled |
| PT-006 | MAE | Canvas Execution | Prepared users/events | Publish one-time Canvas | Execution ≤ 1min, accuracy ≥ 99% | |
| PT-007 | MAE | Journey Email Sending | Prepared users/events | JMeter trigger 1000/2000/3000/6000 events | ≥ 1000 emails/min | |

## 4. Expected Outcomes

- 完整的 Performance Test Report
- 明确系统是否满足上线要求
- 量化 PII 加密对核心链路的影响

## 5. Testing Environment

### 5.1 Server Hardware

| Environment | IP | Configuration | Network | Description |
|-------------|-----|---------------|---------|-------------|
| UAT | ... | 8C64G, 2TB | Gigabit | CDP SA nodes |
| UAT | ... | 8C64G, 1.5TB | Gigabit | CDP SF nodes |

### 5.2 Load Generator

| Name | Configuration | Quantity | Description |
|------|---------------|----------|-------------|
| Load Generator | 8C32G | 3 | Deploy JMeter |

### 5.3 Component Versions

| Component | Version |
|-----------|---------|
| CDP | 3.0.4 |
| MAE | 4.5.2 |

### 5.4 Environment Addresses

| System | Address |
|--------|---------|
| CDP Login | https://... |
| Data Ingestion | https://.../sa?project=... |
| Encryption Service | port 9755 |

## 6. Test Assumptions and Risks

| # | Assumption | Risk if Invalid |
|---|------------|-----------------|
| 1 | UAT env matches production | Results may not reflect production |
| 2 | Dataset matches production characteristics | Query/import results biased |
| 3 | UAT resources exclusively used | Metrics lower than actual capability |
| 4 | JMeter/Grafana stable and accurate | Bottlenecks missed |

## 7. Test Execution

### 7.1 Entry Criteria
- Platform installed and deployed
- Test data ready
- Load generators ready
- Network and monitoring ready
- Plan reviewed and approved

### 7.2 Exit Criteria
- All scenarios executed
- All metrics meet requirements or boundary determined
- Report submitted

### 7.3 Suspension / Resumption
- Suspension: critical bug, environment issue, strategy change
- Resumption: issue resolved or environment restored

## 8. Roles and Responsibilities

| Role | Responsibilities |
|------|-----------------|
| SD Application Team | Plan, scripts, execution, analysis, report |
| WKCDA System/Network Team | System/network support |
| WKCDA Support Team | Review plan and results |
| PjMT | Approve plan and report |

## 9. Schedule

| Activity | Responsible | Start | End |
|----------|-------------|-------|-----|
| Submit Performance Test Plan | SD | | |
| Review Plan | WKCDA | | |
| Execute Testing | SD | | |
| Submit Report | SD | | |
| Approve Report | PjMT | | |

## 10. Appendix

- Acronym List
- Reference Documents
