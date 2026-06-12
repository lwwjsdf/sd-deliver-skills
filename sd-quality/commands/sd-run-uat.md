---
name: sd-run-uat
description: 执行 UAT：基于 uat_test_logic.yaml 执行验收，自动验证可自动化项，标记手动项
argument-hint: ""
status: draft
---

# /sd-run-uat — UAT 执行

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 基于 uat_test_logic.yaml 执行 UAT 验收，自动验证可自动化项（指标、ID-Mapping），标识需手动执行的项。
>
> **前置条件：**
> - uat-test-case.xlsx 已设计并确认
> - uat_test_logic.yaml 已生成（confirmed: true）
> - `.env` 配置了 `API_KEY`
>
> **执行步骤概览：**
> 1. 读取 uat_test_logic.yaml，检查确认状态
> 2. 执行自动化验收（Indicators + ID-Mapping）
> 3. 标识手动验收项
> 4. 记录验收结果到 UAT_ITERATIONS.md
> 5. 输出 UAT 验收报告
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 工作流

### Step 1：检查前置条件

检查 `uat_test_logic.yaml` 的 `confirmed` 字段：
- `true` → 开始执行
- `false` → 询问用户：是否仍要继续？报告将标注"UAT 用例未确认"

### Step 2：执行自动化验收

按 `automation: auto` 的用例执行：

**Indicators 验收**：
```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_uat.py \
  --logic "./references/uat_test_logic.yaml" \
  --type indicators
```

**ID-Mapping 验收**：
```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_uat.py \
  --logic "./references/uat_test_logic.yaml" \
  --type id_mapping
```

### Step 3：标识手动验收项

列出 `automation: manual` 的用例，生成手动执行清单。

### Step 4：记录验收结果

更新 `references/UAT_ITERATIONS.md`：
- 通过的自动用例
- 未通过的自动用例（问题描述、严重度）
- 已执行的用手动用例
- 待执行的手动用例

### Step 5：输出 UAT 验收报告

参见 `/sd-validate-data` 的客户报告模板。

## 完成建议

- "验收通过？→ 可以上线或进入下一阶段"
- "发现问题需要修复？→ 记录到 UAT_ITERATIONS.md，修复后重新执行"
- "需要全流程校验？→ `/sd-validate-data`"
