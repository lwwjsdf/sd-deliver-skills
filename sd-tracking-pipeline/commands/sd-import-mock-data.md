---
name: sd-import-mock-data
description: 将已校验的模拟数据导入神策 CDP（元数据 + 数据 + 导入后校验）
argument-hint: "[--jsonl ./mock_data/<project>.jsonl --skip-metadata]"
---

# /sd-import-mock-data — 导入模拟数据到 CDP

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 将 `mock_data/<project>.jsonl` 中的数据导入神策 CDP，包括：
> 1. 元数据导入（事件、属性定义）
> 2. 元数据预检查
> 3. 数据导入（BatchConsumer）
> 4. 导入后校验（OpenAPI 查询）
>
> **前置条件：**
> - 模拟数据已生成并通过本地校验
> - `.env` 中配置了 `SA_HOST`、`SA_PROJECT`、`SA_TRACK_URL`
> - 元数据导入需要 `API_KEY`
> - 导入后校验需要 `API_KEY`
>
> **⚠️ 注意：此 command 会修改 CDP 配置和数据，执行前必须确认。**
>
> **1/y = 确认执行**
> **0/n = 取消**
> **2/s = 跳过当前步骤**

## 交互规则

### 规则 1：绝不自动执行

用户输入 `/sd-import-mock-data` 后，AI 必须：
1. 展示此页面说明
2. 检查 `.env` 和 `mock_data/*.jsonl`
3. 确认数据已通过本地校验（询问或检查报告）
4. 等待用户确认后再执行

### 规则 2：分阶段确认

导入分为 4 个阶段，每个阶段执行前简要说明并等待确认：
1. 元数据导入
2. 元数据预检查
3. 数据导入
4. 导入后校验

### 规则 3：缺少 API_KEY 的处理

如果 `API_KEY` 未设置：
- 元数据导入前：询问是否跳过（数据仍可导入，但 CDP 中无定义）
- 导入后校验前：询问是否跳过

## 工作流

### Step 1：前置检查

- `.env` 完整性
- `mock_data/*.jsonl` 存在
- 检查是否已有 `uat_validation_report.md` 或本地校验通过标记

### Step 2：元数据导入

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/import_meta_data.py \
  --tracking-plan "./references/<tracking-plan>.xlsx"
```

未指定 `--tracking-plan` 时，脚本自动选择 `references/` 下最新 `.xlsx`。

### Step 3：元数据预检查

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/check_metadata.py \
  --jsonl "./mock_data/<project>.jsonl"
```

### Step 4：数据导入

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/import_mock_data.py \
  --jsonl "./mock_data/<project>.jsonl"
```

### Step 5：导入后校验

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --wait 60
```

### Step 6：更新迭代记录

将本轮导入结果记录到 `references/MOCK_DATA_ITERATIONS.md`。

## 下一步建议

- "导入完成。需要执行 UAT 验收？→ `/sd-run-uat`"
- "需要查看项目状态？→ `/sd-status`"
