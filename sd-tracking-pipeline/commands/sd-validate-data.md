---
name: sd-validate-data
description: 数据全流程校验：导入前+导入后+UAT场景校验+双份报告+自动反馈
argument-hint: ""
status: draft
---

# /sd-validate-data — 数据全流程校验

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 执行数据全流程校验（导入前 + 导入后 + UAT 场景），输出技术报告和客户报告，自动收集反馈并生成下一轮 Checklist。
>
> **前置条件：**
> - 埋点方案存在（`TRACKING_PLAN_PATH` 已设置）
> - 导入后校验需要 `API_KEY`
> - UAT 校验需要 `uat_test_logic.yaml`（可选，无文件跳过）
>
> **执行步骤概览：**
> 1. 确认校验范围（全流程/仅导入前/仅导入后/仅UAT）
> 2. 确认模式（完整/快速）
> 3. 导入前校验
> 4. 导入后校验
> 5. UAT 场景校验（如 uat_test_logic.yaml 存在）
> 6. AI 自动判断问题并分类
> 7. 更新 MOCK_DATA_ITERATIONS.md + UAT_ITERATIONS.md
> 8. 生成技术报告 + 客户报告
> 9. 生成下一轮 Checklist
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 交互规则

### Step 1：确认校验范围

用户输入后，AI 展示选项：

```
选择校验范围：
  [1] 全流程校验（导入前 + 导入后 + UAT 场景）← 默认
  [2] 仅导入前校验（JSONL + Tracking Plan）
  [3] 仅导入后校验（CDP 数据）
  [4] 仅 UAT 场景校验
  [5] 自定义事件/属性深度校验
```

### Step 2：确认模式

```
选择校验模式：
  [1] 快速模式 — 条数 + 基础结构（约 2-5 分钟）
  [2] 完整模式 — 条数 + 结构 + 业务逻辑 + UAT 场景（约 10-30 分钟）← 默认
```

### Step 3：UAT 用例确认

如果 `references/uat_test_logic.yaml` 存在但 `confirmed: false`：

```
⚠️ UAT 用例未确认（confirmed=false）

是否仍然执行 UAT 校验？
  [1] 执行（报告将标注"UAT 用例未确认"）
  [2] 跳过 UAT 部分（仅执行数据校验）
```

## 校验阶段

### Stage 1：导入前校验

**脚本**：
```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_pre_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --iterations "./references/MOCK_DATA_ITERATIONS.md"
```

### Stage 2：导入后校验

**条数对比**：
```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --wait 60
```

**数据完整性抽样**：
```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_post_import.py \
  --events "OrderPaid,ProductViewed" \
  --properties "amount,pay_method" \
  --sample-size 100
```

**业务逻辑校验**：
```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_business.py \
  --logic "./rules/business_logic.yaml" \
  --start-date "2024-01-01" \
  --end-date "2024-01-31"
```

### Stage 3：UAT 场景校验

**Indicators + ID-Mapping 自动校验**：
```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_uat.py \
  --logic "./references/uat_test_logic.yaml" \
  --type indicators,id_mapping
```

**手动用例清单生成**：列出 `automation: manual` 的项。

### Stage 4：AI 自动判断与分类

| 现象 | 分类 | 严重度 | 写入文件 |
|------|------|--------|----------|
| 事件条数 = 0 | 导入失败 | P0 | MOCK_DATA_ITERATIONS |
| CDP 条数 < 导入条数 20% | 数据丢失 | P0 | MOCK_DATA_ITERATIONS |
| 必填属性空值率 > 10% | 数据质量 | P1 | MOCK_DATA_ITERATIONS |
| 枚举值非法 > 5% | 埋点/YAML | P1 | MOCK_DATA_ITERATIONS |
| 用户分层比例偏差 > 20% | 业务逻辑 | P1 | MOCK_DATA_ITERATIONS |
| 指标计算值异常 | UAT 指标 | P1 | UAT_ITERATIONS |
| ID-Mapping 字段缺失 | ID 打通 | P0 | UAT_ITERATIONS |
| 权限用例未执行 | 手动执行 | P2 | UAT_ITERATIONS |

### Stage 5：更新迭代记录

- 数据质量问题 → `references/MOCK_DATA_ITERATIONS.md`
- UAT 验收问题 → `references/UAT_ITERATIONS.md`
- 自动追加 Round 章节

### Stage 6：生成双份报告

**技术报告**：`reports/data_validation_tech_<timestamp>.md`
- 导入前/后校验详情
- 属性完整性
- 业务逻辑校验

**客户报告**：`reports/data_validation_business_<timestamp>.md`
- 验收结论
- 数据完整性（简单呈现）
- UAT 场景验证
- 待确认问题
- 下一步建议

### Stage 7：生成下一轮 Checklist

基于未关闭问题，自动生成下一轮校验清单。

## 完成建议

- "校验通过？→ 可上线或进入下一阶段"
- "校验未通过？→ 修复后重新 `/sd-setup-tracking`"
- "仅执行 UAT？→ `/sd-run-uat`"
- "需要设计 UAT 用例？→ `/sd-design-uat`"
