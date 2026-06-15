---
name: performance-testing
version: 1.1.0
description: |
  性能测试知识。对神策 CDP/MAE 系统进行压力测试和性能基准评估。
  与 server-sizing 配合：server-sizing 负责容量规划，performance-testing 负责验证规划是否达标。
  当讨论压测、性能测试、负载测试、Performance Test Plan、QPS/TPS/响应时间时自动加载。
allowed-tools:
  - Bash
  - Read
  - Write
---

## 适用场景

- 系统上线前，验证能否支撑预估负载
- 容量规划后，验证配置方案是否达标
- 版本升级后，确认性能无回退
- 需要量化 PII 加密、SFTP 导入等对性能的影响

## 测试流程

1. 明确测试目标（响应时间、吞吐量、并发数、资源上限）
2. 设计 Performance Test Plan（场景、数据、工具、环境、指标）
3. 执行基准测试
4. 执行负载测试（逐步加压）
5. 执行压力测试（极限容量）
6. 分析结果，输出 Performance Test Report

## 典型测试场景

| 模块 | 场景 | 关键指标 |
|------|------|----------|
| CDP | 实时导入 | QPS ≥ 1000、错误率、CPU/内存/磁盘 |
| CDP | 批量导入 | ≥ 100 万条/小时、加密耗时、磁盘 I/O |
| CDP | 事件分析查询 | 7 天/30 天响应时间 ≤ 5s |
| CDP | 漏斗分析查询 | 7 天/30 天响应时间 ≤ 5s |
| MAE | Canvas 执行 | 执行时间 ≤ 1min、规则/同步准确率 |
| MAE | Journey 邮件发送 | ≥ 1000 封/分钟、资源占用 |

## 输出

性能测试报告，包含测试环境、测试结果、瓶颈分析、优化建议。

## 关联 command

- `/sd-design-performance-test` — 设计性能测试方案
- `/sd-size-servers` — 容量规划
