---
name: sd-setup-tracking
description: 从埋点方案到数据导入的全链路自动化执行
argument-hint: ""
---

# /sd-setup-tracking — 埋点全链路交付

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 从埋点方案到模拟数据生成、元数据导入、数据导入和结果校验的全链路自动化执行。包含多个脚本调用，可能会修改项目配置和 CDP 数据。
>
> **前置条件：**
> - 项目已初始化（`sdeliver init` 完成）
> - 埋点方案已确认（`.env` 中 `TRACKING_PLAN_PATH` 已设置）
> - **⚠️ 关键：需要 Open API 密钥（`API_KEY`）用于 Phase 5/7**
>
> **执行步骤概览：**
> 1. 前置检查（`.env` 完整性、历史数据扫描、迭代记录检查）
> 2. 生成 business_logic.yaml（从埋点方案提取业务逻辑）
> 3. 验证 YAML（检查格式和完整性）
> 4. 枚举值确认（向客户确认枚举值）
> 5. 生成模拟数据（可选择规模：小/中/大）
> 6. **导入前数据校验**（基于历史反馈 + 基础规则）
> 7. 元数据导入（导入到神策 CDP）
> 8. 数据导入（上传模拟数据）
> 9. **导入后数据校验**（基于 OpenAPI 查询 CDP 实际数据）
> 10. 更新迭代记录（交付反馈、问题记录、验证结果）
> 11. 历史数据清理（询问是否备份/清理旧数据）
>
> **⚠️ 注意：此 command 会调用多个脚本并修改 CDP 配置，每一步都需要你的确认。**
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 交互规则（AI 必须严格遵守）

### 规则 1：绝不自动执行

**严禁在未经用户明确确认的情况下执行任何脚本或命令。**

用户输入 `/setup-tracking` 后，AI 必须：
1. **先展示此页面**（目的、前置条件、步骤概览）
2. **等待用户回复** `确认` 或 `取消`
3. 用户输入 `确认` 后，进入 Step 1（前置检查）
4. **每个 Phase 执行前**，简要说明即将做什么，等待用户确认

### 规则 2：前置检查必须最先执行

Phase 1 之前，必须先检查：

| 检查项 | 通过标准 | 失败处理 |
|--------|----------|----------|
| `.env` 存在 | 文件存在 | 停止，提示运行 `sdeliver init` |
| `TRACKING_PLAN_PATH` | 已设置且文件存在 | 停止，提示先执行 `/design-tracking` |
| `SA_HOST` | 已设置 | 停止，提示填写 |
| `SA_PROJECT` | 已设置 | 停止，提示填写 |
| `SA_TOKEN` | 已设置 | 警告，Phase 6 需要 |
| `API_KEY` | 已设置 | **警告，Phase 5/7 需要** |
| `mock_data/` 历史文件 | 扫描并报告 | 询问是否清理/备份 |

### 规则 3：Phase 失败立即停止

如果任一 Phase 失败（error 或脚本 crash）：
1. **立即停止执行**
2. 报告失败原因
3. 询问：修复问题后重试 / 跳过此 Phase / 取消整个 command

### 规则 4：阶段间确认

每个 Phase 完成后：
1. 简要报告结果（成功/失败/警告）
2. 询问是否继续下一个 Phase，或跳过

用户可以说：
- `继续` — 进入下一 Phase
- `跳过` — 跳过下一 Phase（记录原因）
- `取消` — 终止整个 command

### 规则 5：数据量选择

Phase 4（造数）之前，必须询问数据规模：

| 规模 | 用户数 | 天数 | 预计事件量 | 适用场景 |
|------|--------|------|-----------|----------|
| **小** | 10 | 7 | ~1,000 条 | UAT 验证、快速测试 |
| **中** | 100 | 30 | ~15 万条 | 功能测试、漏斗分析 |
| **大** | 500 | 30 | ~150 万条 | 压测、大数据量验证 |
| **自定义** | 用户指定 | 用户指定 | - | 特殊需求 |

默认推荐：**中**（如果用户未指定）

### 规则 6：历史数据管理

Phase 1（前置检查）时扫描 `mock_data/` 目录：

**如果发现历史文件：**
1. 报告文件数量和总大小
2. 询问用户处理方式：
   - `备份` — 移动到 `mock_data/backup/YYYYMMDD/` 并压缩
   - `清理` — 直接删除（再次确认）
   - `保留` — 继续执行（但可能扫描变慢）

**Phase 8（所有导入完成后）再次询问：**
- 是否需要清理本次生成的临时文件（保留最终 `.jsonl`）

脚本工具：
```bash
# 扫描历史数据
python3 <skill-repo>/sd-tracking-pipeline/scripts/mock_data_manager.py scan

# 备份并压缩
python3 <skill-repo>/sd-tracking-pipeline/scripts/mock_data_manager.py backup --compress

# 清理（保留最终 jsonl）
python3 <skill-repo>/sd-tracking-pipeline/scripts/mock_data_manager.py clean

# 全部清理（⚠️ 包括最终 jsonl）
python3 <skill-repo>/sd-tracking-pipeline/scripts/mock_data_manager.py clean --remove-all
```

## 工作流

### Phase 0：前置检查

```
🔍 前置检查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[✓] .env 存在
[✓] TRACKING_PLAN_PATH: ./references/tracking-plan.xlsx
[✓] SA_HOST: https://demo.sensorsdata.cn
[✓] SA_PROJECT: mpdev
[✓] SA_TOKEN: 已设置
[✗] API_KEY: 未设置 ⚠️ Phase 5/7 需要
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 发现 1 个问题：
  - API_KEY 未设置，Phase 5（元数据导入）和 Phase 7（结果校验）将跳过

📦 mock_data/ 历史文件扫描：
  - 发现 12 个历史文件，共 6.5GB
  - 建议备份后清理以加速后续操作

请选择处理方式：
  [1] 备份到 mock_data/backup/20250611/
  [2] 直接清理（⚠️ 不可恢复）
  [3] 保留（继续执行）
```

### Phase 1：生成 business_logic.yaml

等待用户确认后执行。

两种情况：
- **有业务需求文档**：读取文档提取业务逻辑，结合 Tracking Plan 事件名
- **无业务文档**：使用默认模板，替换事件名和 `meta.project`

### Phase 2：验证 YAML

```bash
python3 scripts/yaml_validator.py \
  ./rules/business_logic.yaml \
  --tracking-plan "$TRACKING_PLAN_PATH"
```

- **error**：停止，报告问题，询问修复方式
- **warning**：逐条展示，询问是否继续
- **PASSED**：进入 Phase 3

### Phase 3：枚举值确认

```bash
python3 scripts/list_enum_values.py \
  --tracking-plan "$TRACKING_PLAN_PATH"
```

分四批向客户确认，所有批次确认完毕后更新 YAML。

### Phase 4：造数（数据量选择）

用户选择规模后执行：

```bash
# 小规模（示例）
python3 scripts/generate_mock_data.py \
  --rules ./rules/business_logic.yaml \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --users 100 --days 30 --sessions-per-day 5
```

生成完成后报告文件大小和记录数。

### Phase 5：导入前数据校验（关键）

**此步骤必须执行，不能跳过。**

基于历史反馈进行导入前校验：

1. **读取迭代记录** — 检查 `references/MOCK_DATA_ITERATIONS.md`
   - 如果有历史反馈，列出所有未关闭的问题项
   - 要求用户确认本轮是否已修复这些问题

2. **基础校验** — 运行导入前校验脚本：

```bash
python3 scripts/validate_pre_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --iterations "./references/MOCK_DATA_ITERATIONS.md"
```

校验内容：
- 事件名与 Tracking Plan 完全一致（大小写敏感）
- 必填属性全部存在，无缺失
- 属性类型与方案定义一致
- 枚举值在允许范围内
- **历史反馈项** — 覆盖迭代记录中所有未关闭的问题

3. **结果处理**：
   - **通过**：进入 Phase 6
   - **未通过**：
     - 列出所有未通过项
     - 询问：修复 YAML → 重新造数 / 忽略警告继续 / 取消
     - 如果选择修复，记录问题到迭代记录文档

### Phase 6：元数据导入

**需要 `API_KEY`。**

```bash
python3 scripts/import_meta_data.py \
  --tracking-plan "$TRACKING_PLAN_PATH"
```

如果缺少 `API_KEY`：
- 询问是否跳过（记录原因）
- 或暂停，提示用户获取 API_KEY 后重试

### Phase 7：数据导入

```bash
# 元数据预检查
python3 scripts/check_metadata.py \
  --jsonl "./mock_data/<project>.jsonl"

# 导入数据
python3 scripts/import_mock_data.py \
  --jsonl "./mock_data/<project>.jsonl"
```

报告导入进度和预计完成时间。

### Phase 8：导入后数据校验（基于 OpenAPI）

**需要 `API_KEY`。此步骤必须执行。**

通过 OpenAPI 查询 CDP 实际落库数据，与导入文件对比：

```bash
python3 scripts/validate_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --wait 60
```

校验内容：
- **条数对比** — 各事件导入条数 vs CDP 实际条数
- **事件存在性** — CDP 中是否能查询到所有导入的事件
- **数据完整性** — 抽样检查属性是否完整落库
- **时间范围** — 确认数据时间范围正确

**结果处理**：
- **通过**：进入 Phase 9
- **未通过**：
  - 可能原因：CDP 数据处理延迟、元数据未导入、导入失败
  - 询问：等待后重试 / 检查元数据 / 查看导入日志 / 取消

### Phase 9：更新迭代记录

导入完成后，必须更新迭代记录文档：

```
references/MOCK_DATA_ITERATIONS.md
```

记录内容：
1. **本轮造数配置** — 用户数、天数、数据规模
2. **交付反馈** — 用户/交付团队发现的问题（表格形式）
3. **验证结果** — 导入前校验结果、导入后校验结果
4. **下一轮 Action** — 待修复项清单

AI 协助用户填写此文档，或根据用户反馈自动生成条目。

### Phase 10：历史数据清理

所有 Phase 完成后询问：

```
✅ 所有 Phase 执行完毕。

是否需要清理本次生成的临时文件？
  - 保留：mock_data/westk.jsonl（最终文件，369MB）
  - 删除：mock_data/westk_*.jsonl（中间文件，共 2.1GB）
  - 删除：mock_data/westk_1k_part_*（分片文件，共 1.6GB）

[1] 清理临时文件（保留最终 jsonl）
[2] 全部保留
[3] 全部清理（包括最终文件）⚠️
```

## 多轮迭代流程

造数通常需要多轮迭代。每轮流程：

```
Round N:
  1. 读取迭代记录（MOCK_DATA_ITERATIONS.md）
  2. 修复上一轮反馈的问题
  3. 重新生成数据
  4. 导入前校验（必须覆盖历史反馈项）
  5. 导入 CDP
  6. 导入后校验（OpenAPI 查询）
  7. 收集交付团队反馈
  8. 更新迭代记录
  9. 如有问题 → Round N+1
```

### 迭代记录文档

**位置**：`references/MOCK_DATA_ITERATIONS.md`

**每轮必须记录**：
- 造数配置（用户数、天数、规模）
- 交付反馈（问题描述、涉及事件/属性、严重度）
- 验证结果（导入前/后校验结果）
- 待修复项（下一轮 Action）

### 校验要求

**导入前**：必须检查迭代记录中的所有未关闭问题，确认已修复
**导入后**：必须通过 OpenAPI 查询 CDP，验证条数和数据完整性

## 完成建议

- "需要验证数据正确性？→ `/validate-data`（包含导入前 + 导入后校验）"
- "需要查看历史反馈？→ 检查 `references/MOCK_DATA_ITERATIONS.md`"
- "需要执行 UAT 验收？→ `/run-uat`"
