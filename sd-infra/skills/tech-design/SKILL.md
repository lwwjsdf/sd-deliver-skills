---
name: tech-design
version: 1.0.0
description: |
  技术方案设计知识。根据项目背景和需求，生成 LLD（Low-Level Design）PPT 框架、
  架构图和 Technical Specification 文档。
  当讨论技术方案、文档架构、LLD、Tech Spec、评审材料时自动加载。
allowed-tools:
  - Bash
  - Read
  - Write
---

## 交付物

| 交付物 | 格式 | 面向对象 |
|--------|------|---------|
| LLD PPT | PowerPoint | 客户 IT 治理审批 |
| 架构图 | draw.io XML | LLD 内嵌 / 独立交付 |
| Tech Spec | Word / Markdown | 开发团队实施参考 |

LLD 写做什么和为什么，Tech Spec 写怎么做。

## LLD 核心章节

1. Project Background and Objectives
2. Services Offering
3. System Architecture（逻辑架构、系统流、基础设施、加密、数据流）
4. Technical Methodologies（选型、部署、认证）
5. System Resource Requirements（硬件、软件、容量）
6. Availability and Scalability
7. Service Level Agreement（RTO/RPO）
8. Operational Requirements（监控、备份、维护）
9. Major Interfaced Systems
10. Technology Risk Management
11. Assumptions and Pre-requisites

## Tech Spec 核心章节

1. Introduction
2. Solution Description
3. Solution Design Principle（加密策略、架构决策）
4. Business Architecture Design
5. Components Catalogue
6. Logical Architecture Design
7. Data Architecture Design
8. Backup and Restore（含 DR 流程）
9. Data Conversion Architecture
10. Interface Catalogue
11. Cloud Infrastructure Design

## 关键设计原则

### 非标设计必须显式记录

任何偏离标准设计的决策，必须在 LLD Section 4.5 中记录四项：标准设计、非标设计、理由、补救措施。

### 加密方案分阶段

- 临时方案：HTTPS/TLS 全链路
- 中期方案：PII 字段 AES-256-GCM + KMS 信封加密

### 扩容路径

- 3 节点 → 最多 5 节点
- 超过 5 节点 → 迁移至 3+N 架构（有数据迁移成本）
