---
name: sd-validate-mock-data
description: 对生成的模拟数据进行导入前校验（事件名、属性、枚举值、历史反馈）
argument-hint: "[--jsonl ./mock_data/<project>.jsonl]"
---

# /sd-validate-mock-data — 导入前数据校验

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 对 `mock_data/<project>.jsonl` 进行本地校验，检查数据是否符合埋点方案、业务规则和迭代记录中的历史反馈。
> **不访问 CDP，不导入数据。**
>
> **前置条件：**
> - 模拟数据已生成（`mock_data/*.jsonl` 存在）
> - `TRACKING_PLAN_PATH` 已设置
> - 推荐同时存在 `references/MOCK_DATA_ITERATIONS.md`
>
> **校验内容：**
> - 事件名与 Tracking Plan 一致
> - 必填属性完整
> - 属性类型正确
> - 枚举值在允许范围内
> - 历史反馈项是否已覆盖
>
> **1/y = 确认执行**
> **0/n = 取消**
> **2/s = 跳过**

## 交互规则

### 规则 1：绝不自动执行

AI 必须先展示校验范围，等待用户确认后再运行脚本。

### 规则 2：校验失败必须停止

如果校验未通过：
1. 列出所有违规项
2. 建议修复路径：修改 `business_logic.yaml` → 重新 `/sd-generate-mock-data` → 重新校验
3. 询问：修复后重试 / 忽略警告继续 / 取消

### 规则 3：迭代记录检查

如果 `references/MOCK_DATA_ITERATIONS.md` 存在：
- 读取未关闭问题
- 校验本轮数据是否已覆盖这些问题
- 输出覆盖情况报告

## 工作流

### Step 1：前置检查

- 检查 `.env` 中 `TRACKING_PLAN_PATH`
- 查找最新生成的 `.jsonl` 文件
- 检查 `MOCK_DATA_ITERATIONS.md` 是否存在

### Step 2：执行校验

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_pre_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --iterations "./references/MOCK_DATA_ITERATIONS.md"
```

如果脚本不存在，使用等价的 `validate_import.py --pre-only` 或 `check_metadata.py` 组合。

### Step 3：结果处理

- **通过**：提示可以进入导入阶段
- **未通过**：列出问题，建议修复

## 下一步建议

- "校验通过。是否继续导入？运行 `/sd-import-mock-data`"
- "或运行 `/sd-setup-tracking` 继续完整工作流"
