---
name: sd-generate-mock-data
description: 基于 business_logic.yaml 和埋点方案生成模拟数据（JSONL）
argument-hint: "[--users 100 --days 30 --sessions-per-day 5]"
---

# /sd-generate-mock-data — 生成模拟数据

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 根据已确认的埋点方案和 business_logic.yaml 生成模拟事件数据，输出到 `mock_data/` 目录。
> 仅生成数据，**不会导入 CDP**。
>
> **前置条件：**
> - 项目已初始化（`.env` 存在）
> - `TRACKING_PLAN_PATH` 已设置且文件存在
> - `rules/business_logic.yaml` 已存在（可先用 `/sd-setup-tracking` 生成）
>
> **输出文件：**
> - `mock_data/<project>.jsonl` — 事件数据
> - `mock_data/<project>_identity_map.csv` — ID-Mapping 对照表
> - `mock_data/uat_validation_report.md` — 业务规则校验报告
>
> **1/y = 确认执行**
> **0/n = 取消**
> **2/s = 跳过**

## 交互规则

### 规则 1：绝不自动执行

用户输入 `/sd-generate-mock-data` 后，AI 必须：
1. 展示此页面说明
2. 检查 `.env` 和 `business_logic.yaml` 是否存在
3. 询问数据规模（小/中/大/自定义）
4. 等待用户确认后再执行脚本

### 规则 2：数据规模选择

| 规模 | 用户数 | 天数 | 预计事件量 | 适用场景 |
|------|--------|------|-----------|----------|
| **小** | 10 | 7 | ~1,000 条 | UAT 验证、快速测试 |
| **中** ⭐ | 100 | 30 | ~15 万条 | 功能测试、漏斗分析 |
| **大** | 500 | 30 | ~150 万条 | 压测、大数据量验证 |
| **自定义** | 用户指定 | 用户指定 | - | 特殊需求 |

### 规则 3：历史数据管理

执行前扫描 `mock_data/`：
- 发现历史文件时询问：备份 / 清理 / 保留
- 大规模生成前建议备份

## 工作流

### Step 1：前置检查

检查项：
- `.env` 存在
- `TRACKING_PLAN_PATH` 存在且有效
- `rules/business_logic.yaml` 存在
- 必要时询问数据规模

### Step 2：执行造数

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/generate_mock_data.py \
  --rules ./rules/business_logic.yaml \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --users <N> --days <D> --sessions-per-day <S>
```

### Step 3：报告结果

生成完成后报告：
- 输出文件路径
- 记录总数 / 用户数 / 事件类型数
- 业务规则违规数（如有）

## 下一步建议

- "生成完成。接下来可以："
  - "运行 `/sd-validate-mock-data` 进行导入前校验 →"
  - "或运行 `/sd-setup-tracking` 继续完整工作流"
