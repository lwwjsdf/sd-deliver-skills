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
> - 埋点方案 Excel 放在 `references/` 目录，或通过 `--tracking-plan` 指定
> - 推荐同时存在 `references/MOCK_DATA_ITERATIONS.md`
>
> **校验内容：**
> - 事件名与 Tracking Plan 一致
> - 必填属性完整
> - 属性类型正确
> - 枚举值在允许范围内
> - 历史反馈项是否已覆盖
>
> **AI 行为约束：**
> - 必须先确认校验意图（导入前校验 / 问题定位）
> - 必须使用 `scan_jsonl.py` 和 `validate_pre_import.py` 脚本，禁止现场写大段 Python
> - JSONL > 10 MB 时默认抽样
> - 输出结构化结论，不要原始 Counter
>
> **1/y = 确认执行**
> **0/n = 取消**
> **2/s = 跳过**

## 交互规则

### 规则 1：先确认意图

用户输入 `/sd-validate-mock-data` 后，AI 先问：

```
请选择：
  [1] 标准导入前校验（对比 Tracking Plan + 历史反馈）← 默认
  [2] 快速概览（只看 JSONL 事件分布和属性样例）
  [3] 针对具体问题定位（请告诉我字段/事件名）
```

### 规则 2：必须使用封装脚本

| 任务 | 脚本 |
|------|------|
| 快速概览 | `scan_jsonl.py --jsonl <file>` |
| 导入前校验 | `validate_pre_import.py --jsonl <file> --tracking-plan <xlsx>` |
| 历史反馈覆盖 | `validate_pre_import.py --iterations <md>` |

**禁止现场写 10 行以上 Python 做扫描。**

### 规则 3：大数据量抽样

- 标准模式：`validate_pre_import.py` 默认每个事件抽样 1000 条
- 快速模式：`scan_jsonl.py --sample 1000`

### 规则 4：失败停止

如果校验未通过：
1. 列出关键问题（最多 5 条）
2. 建议修复路径：修改 `business_logic.yaml` → 重新 `/sd-generate-mock-data` → 重新校验
3. 询问：修复后重试 / 忽略警告继续 / 取消

## 工作流

### Step 1：前置检查

- 检查 `references/` 目录中是否存在埋点方案 `.xlsx`（或通过 `--tracking-plan` 显式指定）
- 查找最新生成的 `.jsonl` 文件
- 检查 `MOCK_DATA_ITERATIONS.md` 是否存在

### Step 2A：快速概览

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/scan_jsonl.py \
  --jsonl "./mock_data/<project>.jsonl"
```

### Step 2B：标准导入前校验

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_pre_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --tracking-plan "./references/<tracking-plan>.xlsx" \
  --iterations "./references/MOCK_DATA_ITERATIONS.md"
```

未指定 `--tracking-plan` 时，脚本自动选择 `references/` 下最新 `.xlsx`。

### Step 3：结果处理

输出结构化结论：
```
## 校验结论
- 状态：✅ 通过 / ❌ 未通过 / ⚠️ 有警告
- 检查项：事件名、属性完整性、类型、枚举值、历史反馈
- 关键问题：...
- 下一步：...
```

## 下一步建议

- "校验通过。是否继续导入？运行 `/sd-import-mock-data`"
- "或运行 `/sd-setup-tracking` 继续完整工作流"
