---
name: data-validation
version: 1.0.0
description: |
  数据全流程校验知识。覆盖导入前校验（基于历史反馈和基础规则）和
  导入后校验（基于 OpenAPI 查询 CDP 实际数据）。
  当讨论数据校验、数据质量、导入验证、Mock 数据验证时自动加载。
allowed-tools:
  - Bash
  - Read
---

## 校验体系

数据校验分为两个阶段，缺一不可：

```
┌─────────────────────────────────────────────────────────┐
│  Stage 1: 导入前校验（Pre-import Validation）            │
│  • 基础规则：事件名、属性、类型、枚举值                   │
│  • 历史反馈：基于 MOCK_DATA_ITERATIONS.md 检查           │
│  • 目的：确保生成的数据符合预期，避免导入错误数据         │
├─────────────────────────────────────────────────────────┤
│  [导入到 CDP]                                           │
├─────────────────────────────────────────────────────────┤
│  Stage 2: 导入后校验（Post-import Validation）           │
│  • 条数对比：导入条数 vs CDP 实际条数                     │
│  • 数据完整性：抽样检查属性、枚举值、时间戳               │
│  • 历史反馈验证：确认问题已修复                           │
│  • 目的：确认数据正确落库                                 │
└─────────────────────────────────────────────────────────┘
```

## 导入前校验（Pre-import）

### 校验内容

#### 1. 基础规则

| 检查项 | 方法 | 工具/脚本 |
|--------|------|-----------|
| 事件名一致性 | 对比 JSONL 中的事件名与 Tracking Plan | `validate_pre_import.py` |
| 必填属性完整性 | 检查每个事件是否包含所有必填属性 | `validate_pre_import.py` |
| 属性类型正确性 | 检查属性值类型与 Tracking Plan 定义一致 | `validate_pre_import.py` |
| 枚举值范围 | 检查属性值是否在允许的枚举列表中 | `validate_pre_import.py` |

#### 2. 历史反馈校验（关键）

读取 `references/MOCK_DATA_ITERATIONS.md`，针对每轮未关闭的问题：

**校验方法**：
- **枚举值不全** — 抽样 100 条记录，统计枚举值分布
- **比例失衡** — 统计用户分层（L0-L4）实际比例
- **数值类型错误** — 抽样检查数值字段（如 amount 是否为 float）
- **缺少事件** — 检查事件序列中是否存在新增事件
- **属性缺失** — 检查事件属性是否完整
- **时间异常** — 检查事件时间分布是否合理（不应集中在同一小时）

**覆盖报告**：
```
历史问题覆盖情况：
- Round 1 问题 #3: amount 字段包含小数 — ✅ 已覆盖
  抽样 10 条 OrderPaid 事件，amount 均为 float（10.50, 299.00, ...）
- Round 1 问题 #4: 退款事件存在 — ❌ 未覆盖
  RefundCompleted 事件未在 JSONL 中找到
```

### 脚本

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_pre_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --iterations "./references/MOCK_DATA_ITERATIONS.md"
```

参数：
- `--jsonl` — 模拟数据文件路径
- `--tracking-plan` — 埋点方案 Excel 路径
- `--iterations` — 迭代记录文档路径（可选，如有则进行历史反馈校验）
- `--sample-size` — 抽样大小（默认 100）

## 导入后校验（Post-import）

### 校验内容

#### 1. 条数对比

通过 OpenAPI 查询 CDP 中各事件的实际条数：

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --wait 60
```

**结果解读**：

| 状态 | 导入条数 | CDP 条数 | 说明 | 处理 |
|------|----------|----------|------|------|
| ✅ | 1000 | 1000 | 数据完全一致 | 正常 |
| ℹ️ | 1000 | 1200 | CDP 有历史数据 | 正常，差值为历史数据 |
| ⚠️ | 1000 | 800 | CDP 偏少 | 警告，可能部分数据未落库 |
| ❌ | 1000 | 0 | CDP 未找到 | 错误，导入失败或数据延迟 |

**常见问题**：
- **CDP 偏少**：数据导入后有处理延迟（通常 1-5 分钟），加 `--wait 60` 等待后重试
- **CDP 未找到**：检查元数据是否已导入（`import_meta_data.py`）
- **CDP 偏多**：正常，CDP 中可能有历史测试数据

#### 2. 数据完整性抽样

通过 OpenAPI 查询抽样数据，检查属性完整性：

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_post_import.py \
  --project "$SA_PROJECT" \
  --api-key "$API_KEY" \
  --events "OrderPaid,ProductViewed" \
  --sample-size 100 \
  --start-date "2024-01-01" \
  --end-date "2024-01-31"
```

检查项：
- 属性是否存在（与 Tracking Plan 对比）
- 属性值类型是否正确
- 枚举值是否在允许范围内
- 时间戳是否在合理范围
- 用户属性是否正确关联

#### 3. 历史反馈项验证

在 CDP 中验证迭代记录中的问题是否已修复：

```bash
# 查询特定事件的属性分布
python3 <skill-repo>/sd-tracking-pipeline/scripts/query_event_properties.py \
  --project "$SA_PROJECT" \
  --api-key "$API_KEY" \
  --event "OrderPaid" \
  --property "amount" \
  --sample-size 50
```

## OpenAPI 使用说明

### 凭证配置

```bash
# .env
SA_HOST=https://demo.sensorsdata.cn
SA_PROJECT=default
API_KEY=#K-xxx  # Open API 密钥
```

获取方式：神策后台 → 项目管理 → 权限管理 → 创建 API Key

**注意**：项目名（`sensorsdata-project` header 的值）是 CDP 中项目的显示名（如 `uat`），不是 URL 中的 `project=` 参数。

### 接口格式

**Base URL**: `{SA_HOST}/api/v3/analytics/v1`

**Headers**:
- `Content-Type: application/json`
- `api-key: {API_KEY}`
- `sensorsdata-project: {PROJECT_NAME}`（如 `uat`）

**Body**:
```json
{
  "sql": "SELECT ...",
  "limit": 1000
}
```

### 常用查询

```python
from sensors_openapi import SensorsOpenAPI

# 项目名是 CDP 中显示的 project 名称，如 "uat"
api = SensorsOpenAPI(SA_HOST, API_KEY, project="uat")

# 1. 查询事件条数
counts = api.query_event_counts(
    event_names=["OrderPaid", "ProductViewed"],
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# 2. 查询事件属性样本（用于完整性校验）
samples = api.query_event_properties_sample(
    event_name="OrderPaid",
    property_names=["amount", "pay_method", "product_id"],
    start_date="2024-01-01",
    end_date="2024-01-31",
    sample_size=100
)
# 返回: [{"amount": 299.00, "pay_method": "wechat", "product_id": "P001"}, ...]

# 3. 查询属性值分布（用于枚举值校验）
distribution = api.query_property_distribution(
    event_name="OrderPaid",
    property_name="pay_method",
    start_date="2024-01-01",
    end_date="2024-01-31",
    top_n=20
)
# 返回: {"wechat": 500, "alipay": 300, "card": 200}

# 4. 自定义 SQL 查询
resp = api.custom_query(
    sql="SELECT event, count(*) AS cnt FROM events WHERE date >= '2024-01-01' AND date <= '2024-01-31' GROUP BY event",
    limit=1000
)
```

### SQL 规范

- **表名**: `events`（事件表）、`users`（用户表）
- **时间字段**: `date`（DATE 类型，格式 `YYYY-MM-DD`）
- **属性字段**: 直接使用属性名，如 `amount`、`pay_method`
- **limit**: 必须提供，默认 1000，最大 10000

示例 SQL:
```sql
-- 查询事件条数
SELECT event, count(*) AS cnt FROM events
WHERE date >= '2024-01-01' AND date <= '2024-01-31'
AND event IN ('OrderPaid', 'ProductViewed')
GROUP BY event

-- 查询属性样本
SELECT amount, pay_method FROM events
WHERE date >= '2024-01-01' AND date <= '2024-01-31'
AND event = 'OrderPaid'
LIMIT 100

-- 查询枚举值分布
SELECT pay_method, count(*) AS cnt FROM events
WHERE date >= '2024-01-01' AND date <= '2024-01-31'
AND event = 'OrderPaid'
GROUP BY pay_method
ORDER BY cnt DESC
LIMIT 20
```

## 迭代记录文档

### 文档位置

```
references/MOCK_DATA_ITERATIONS.md
```

### 文档结构

每轮迭代记录包含：
1. **造数配置** — 用户数、天数、数据规模
2. **交付反馈** — 问题描述、涉及事件/属性、严重度、修复方案、状态
3. **验证结果** — 导入前校验结果、导入后校验结果
4. **下一轮 Action** — 待修复项清单

### 使用流程

1. **Round 1** 导入后，交付团队反馈问题 → AI 协助记录到迭代文档
2. **Round 2** 造数前，AI 读取迭代文档，检查历史问题是否已修复
3. **Round 2** 导入前，AI 基于迭代文档进行历史反馈校验
4. **Round 2** 导入后，AI 验证历史问题是否已解决

## 常见问题

**Q: 导入前校验和导入后校验有什么区别？**

A: 导入前校验检查的是生成的模拟数据（JSONL 文件）是否符合预期；导入后校验检查的是数据是否正确落库到 CDP 中。两个阶段缺一不可。

**Q: 为什么需要迭代记录？**

A: 造数通常需要多轮迭代。每轮交付团队会反馈问题（如枚举值不全、比例失衡等），这些问题必须在下一轮造数时修复。迭代记录确保历史反馈不会被遗漏。

**Q: 导入后校验发现条数偏少怎么办？**

A: 
1. 等待 1-2 分钟后重试（数据处理有延迟）
2. 检查元数据是否已导入（`import_meta_data.py`）
3. 查看导入日志（`import_mock_data.py` 输出）
4. 如果持续偏少，可能需要重新导入

**Q: OpenAPI 查询返回 404 怎么办？**

A: 检查 `.env` 中的 `API_KEY` 是否正确，以及 API Key 是否有自定义查询权限。

**Q: 迭代记录中的问题如何标记为已关闭？**

A: 在 `MOCK_DATA_ITERATIONS.md` 中，将问题状态从 `⏳ 待修复` 改为 `✅ 已修复`，并在验证结果中注明验证通过。
