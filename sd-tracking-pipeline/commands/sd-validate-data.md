---
name: sd-validate-data
description: 数据全流程校验：导入前基于历史反馈检查 + 导入后基于 OpenAPI 查询 CDP 实际数据
argument-hint: ""
status: draft
---

# /sd-validate-data — 数据全流程校验

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 执行数据的全流程校验，包含两个阶段：
> 1. **导入前校验** — 基于历史反馈和基础规则，检查生成的模拟数据是否符合预期
> 2. **导入后校验** — 基于 OpenAPI 查询 CDP 实际落库数据，确认数据正确导入
>
> **前置条件：**
> - 埋点方案文档存在（`TRACKING_PLAN_PATH` 已设置）
> - 神策环境可连接（`SA_HOST`、`SA_PROJECT` 已配置）
> - 导入后校验需要 `API_KEY`（OpenAPI 密钥）
>
> **执行步骤概览：**
> 1. 检查是否有迭代记录（`MOCK_DATA_ITERATIONS.md`）
> 2. 导入前校验（事件名、属性、枚举值、历史反馈项）
> 3. 导入后校验（OpenAPI 查询 CDP 条数对比、数据完整性）
> 4. 输出校验报告（通过/异常/缺失/历史问题覆盖情况）
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 校验阶段

### Stage 1：导入前校验（Pre-import Validation）

**目的**：在数据导入 CDP 之前，确保生成的模拟数据符合要求，避免导入错误数据。

**输入**：
- `mock_data/<project>.jsonl` — 生成的模拟数据
- `references/tracking-plan.xlsx` — 埋点方案
- `references/MOCK_DATA_ITERATIONS.md` — 迭代记录（如有）

**校验内容**：

#### 1.1 基础规则校验

| 检查项 | 通过标准 | 失败处理 |
|--------|----------|----------|
| 事件名 | 与 Tracking Plan 完全一致（大小写敏感） | ❌ 停止，修复 YAML |
| 必填属性 | 全部存在，无缺失 | ❌ 停止，修复 YAML |
| 属性类型 | 与方案定义一致（string/int/float/bool/datetime/list） | ❌ 停止，修复 YAML |
| 枚举值 | 在允许范围内 | ⚠️ 警告，询问是否继续 |

#### 1.2 历史反馈校验（关键）

如果存在 `MOCK_DATA_ITERATIONS.md`：

1. 读取所有未关闭的问题项
2. 针对每个问题，在模拟数据中抽样验证：
   - **枚举值不全** — 抽样 100 条，检查枚举值分布是否符合修复后的配置
   - **比例失衡** — 统计用户分层比例，验证是否在预期范围内
   - **数值类型错误** — 抽样检查数值字段类型（int vs float）
   - **缺少事件** — 检查事件序列中是否存在新增事件
   - **属性缺失** — 检查事件属性是否完整
   - **时间异常** — 检查事件时间分布是否合理

3. **覆盖报告**：
   ```
   历史问题覆盖情况：
   - Round 1 问题 #3: amount 字段包含小数 — ✅ 已覆盖（抽样 10/10 为 float）
   - Round 1 问题 #4: 退款事件存在 — ❌ 未覆盖（RefundCompleted 未找到）
   ```

#### 1.3 脚本

```bash
python3 scripts/validate_pre_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --iterations "./references/MOCK_DATA_ITERATIONS.md"
```

**结果处理**：
- **全部通过**：进入 Stage 2（如果数据已导入）或提示可以导入
- **历史问题未覆盖**：⚠️ 警告，询问是否继续（记录到迭代记录）
- **基础规则失败**：❌ 停止，修复后重新造数

---

### Stage 2：导入后校验（Post-import Validation）

**目的**：通过 OpenAPI 查询 CDP 实际数据，确认数据已正确落库。

**前置条件**：
- 数据已导入 CDP（`/setup-tracking` Phase 7 完成）
- `.env` 中配置了 `API_KEY`

**校验内容**：

#### 2.1 条数对比

查询 CDP 中各事件的实际条数，与导入文件对比：

```bash
python3 scripts/validate_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --wait 60
```

| 状态 | 说明 | 处理 |
|------|------|------|
| ✅ | 导入条数 = CDP 条数 | 正常 |
| ℹ️ 偏多 | CDP 条数 > 导入条数 | 正常（可能有历史数据） |
| ⚠️ 偏少 | CDP 条数 < 导入条数 | 警告（可能有数据丢失） |
| ❌ 未找到 | CDP 条数 = 0 | 错误（导入失败或延迟） |

#### 2.2 数据完整性抽样检查

通过 OpenAPI 查询抽样数据，检查：
- 属性是否存在（与 Tracking Plan 对比）
- 属性值类型是否正确
- 枚举值是否在允许范围内
- 时间戳是否在合理范围

```bash
python3 scripts/validate_post_import.py \
  --project "$SA_PROJECT" \
  --api-key "$API_KEY" \
  --events "EventName1,EventName2" \
  --sample-size 100
```

#### 2.3 历史反馈项验证

如果迭代记录中有未关闭的问题，在 CDP 数据中验证：
- 查询特定事件的属性分布
- 检查新增事件是否落库
- 验证数值字段类型

#### 2.4 结果处理

- **全部通过**：✅ 数据校验完成，更新迭代记录
- **条数异常**：等待后重试 / 检查导入日志 / 重新导入
- **数据不完整**：检查元数据导入 / 修复 YAML 重新造数

---

## 校验报告模板

```markdown
## 数据校验报告 — Round N

**校验时间：** YYYY-MM-DD HH:MM
**校验范围：** XX 个事件，XX 条记录
**校验人：** AI / 交付团队

### Stage 1：导入前校验

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 事件名一致性 | ✅/❌ | ... |
| 必填属性完整性 | ✅/❌ | ... |
| 属性类型正确性 | ✅/❌ | ... |
| 枚举值范围 | ✅/⚠️ | ... |

**历史问题覆盖：**
- Round X 问题 #Y: [问题描述] — ✅ 已覆盖 / ❌ 未覆盖

**结论：** [通过/未通过]

### Stage 2：导入后校验

| 事件名 | 导入条数 | CDP 条数 | 状态 | 备注 |
|--------|----------|----------|------|------|
| EventName1 | 1000 | 1000 | ✅ | ... |
| EventName2 | 500 | 480 | ⚠️ 偏少 | ... |

**数据完整性抽样：**
- 抽样 100 条，属性完整率：XX%
- 枚举值合规率：XX%

**历史问题验证：**
- Round X 问题 #Y: [问题描述] — ✅ 已验证 / ❌ 未通过

**结论：** [通过/未通过]

### 待办 Action

- [ ] ...
```

## 完成建议

- "校验未通过？需要重新造数和导入？→ `/setup-tracking`"
- "需要记录反馈到迭代文档？→ 我会帮你更新 `MOCK_DATA_ITERATIONS.md`"
