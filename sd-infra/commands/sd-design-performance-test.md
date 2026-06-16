---
name: sd-design-performance-test
description: 设计 CDP/MAE 性能测试方案：目标 → 场景 → 环境 → 指标 → 计划
argument-hint: ""
status: active
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
> 1. 读取 `PROJECT_CONTEXT.yaml`，自动填充已确认的业务规模和环境信息
> 2. 只询问缺失的关键信息（如有）
> 3. 将新确认的事实写回 `PROJECT_CONTEXT.yaml`
> 4. 选择测试场景（实时导入、批量导入、事件分析、漏斗分析、Canvas、邮件发送等）
> 5. 设计每个场景的数据准备、测试步骤、预期指标
> 6. 确认测试环境、工具、监控方案
> 7. **生成 Performance Test Plan 交付物（Word + Excel）**
> 8. 用 validator 校验计划结构
>
> **最终交付物：**
> - `references/performance-test-plan.docx` — 客户版 Performance Test Plan
> - `references/performance-test-plan.xlsx` — 场景矩阵与环境信息表
>
> 不会只输出 Markdown。Markdown 仅作为内部草稿（可选）。
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 工作流

### Step 0：读取项目上下文

执行前先检查 `PROJECT_CONTEXT.yaml` 中已确认的事实：

```bash
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py check \
  --skill sd-design-performance-test
```

如果已存在以下 key，直接复用，不再询问：
- `business.dau`
- `business.daily_events`
- `business.retention_days`
- `infra.cloud`
- `infra.region`
- `infra.include_cdp`
- `infra.include_ma`
- `sla.realtime_import_qps`
- `sla.batch_import_records_per_hour`
- `sla.analytics_query_p95_seconds`
- `sla.email_send_per_minute`
- `env.cdp_url`
- `env.has_pii_encryption`

如果缺失，向用户确认后写入：

```bash
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set \
  business.dau 1000000 \
  --source sd-design-performance-test
```

### Step 1：确认测试目标

基于 PROJECT_CONTEXT 中的事实，与用户确认：
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

### Step 5：输出 Performance Test Plan（Word + Excel）

**本 command 的最终交付物是 `.docx` 和 `.xlsx`，不是 Markdown。**

如果项目虚拟环境未就绪，先安装依赖：

```bash
./venv/bin/pip install -r <skill-repo>/requirements.txt
```

然后直接生成 Word/Excel（参数优先从 PROJECT_CONTEXT 读取）：

```bash
./venv/bin/python <skill-repo>/sd-infra/scripts/design_performance_test.py \
  --dau $(./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py get business.dau) \
  --daily-events $(./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py get business.daily_events) \
  --retention-days $(./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py get business.retention_days) \
  --cloud $(./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py get infra.cloud) \
  --region $(./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py get infra.region) \
  --output-word ./references/performance-test-plan.docx \
  --output-excel ./references/performance-test-plan.xlsx
```

如果只需要 Word：

```bash
./venv/bin/python <skill-repo>/sd-infra/scripts/design_performance_test.py \
  --dau 1000000 \
  --daily-events 5000000 \
  --output-word ./references/performance-test-plan.docx
```

如果只需要 Excel：

```bash
./venv/bin/python <skill-repo>/sd-infra/scripts/design_performance_test.py \
  --dau 1000000 \
  --daily-events 5000000 \
  --output-excel ./references/performance-test-plan.xlsx
```

生成后应先用 validator 校验：

```bash
./venv/bin/python <skill-repo>/sd-infra/scripts/validate_performance_test_plan.py \
  --format word \
  --input ./references/performance-test-plan.docx

./venv/bin/python <skill-repo>/sd-infra/scripts/validate_performance_test_plan.py \
  --format excel \
  --input ./references/performance-test-plan.xlsx
```

### Step 6：人工补充客户特定信息

脚本生成的是标准模板，必须人工填写：
- 客户名称、项目版本
- 具体环境地址和 IP
- 组件实际版本号
- 测试时间表和负责人
- 客户特定的风险假设

## Required Context

`/sd-design-performance-test` 依赖以下 `PROJECT_CONTEXT.yaml` keys：

| Key | 用途 | 是否必填 |
|-----|------|---------|
| `business.dau` | 日活跃用户 | required |
| `business.daily_events` | 日增事件量 | required |
| `business.retention_days` | 历史数据保留天数 | required |
| `infra.cloud` | 云厂商 | required |
| `infra.region` | 云 Region | required |
| `business.mau` | 月活跃用户 | optional |
| `business.peak_qps` | 峰值 QPS | optional |
| `infra.include_cdp` | 是否包含 CDP | optional |
| `infra.include_ma` | 是否包含 MA | optional |
| `sla.realtime_import_qps` | 实时导入目标 QPS | optional |
| `sla.batch_import_records_per_hour` | 批量导入目标 | optional |
| `sla.analytics_query_p95_seconds` | 分析查询 P95 | optional |
| `sla.email_send_per_minute` | 邮件发送吞吐 | optional |
| `env.cdp_url` | CDP 地址 | optional |
| `env.has_pii_encryption` | 是否 PII 加密 | optional |

## 完成建议

- "Performance Test Plan 已确认？→ 执行 `/sd-run-performance-test`"
- "需要先准备压测数据？→ `/sd-generate-mock-data`"
- "容量规划未完成？→ `/sd-size-servers`"
