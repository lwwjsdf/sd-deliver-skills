---
name: mock-data
version: 1.0.0
description: |
  模拟数据生成知识。基于 business_logic.yaml 和埋点方案生成测试数据，
  支持固定测试账号（UAT 场景）和批量随机用户（大数据量）。
  当讨论造数、模拟数据、测试数据生成、mock data 时自动加载。
allowed-tools:
  - Bash
  - Read
---

## 数据规模选择

Phase 4（造数）前必须询问用户选择规模：

| 规模 | 参数 | 预计事件量 | 适用场景 | 生成时间 |
|------|------|-----------|----------|----------|
| **小** | `--users 10 --days 7` | ~1,000 条 | UAT 验证、快速测试 | ~30 秒 |
| **中** ⭐ 默认 | `--users 100 --days 30 --sessions-per-day 5` | ~15 万条 | 功能测试、漏斗分析 | ~5 分钟 |
| **大** | `--users 500 --days 30 --sessions-per-day 10` | ~150 万条 | 压测、大数据量验证 | ~30 分钟 |
| **自定义** | 用户指定 | - | 特殊需求 | 视参数而定 |

**推荐默认选择「中」**，除非用户明确要求大规模压测。

## 数据量过大的风险

- **生成时间**：大规模数据（500 用户 × 30 天 × 10 session）可能需要 30 分钟以上
- **磁盘空间**：可能生成数 GB 的 jsonl 文件
- **导入时间**：数据导入到 CDP 可能需要数小时（按 160 条/秒计算，150 万条约 2.6 小时）
- **CDP 存储**：大量测试数据会占用客户 CDP 存储配额

**建议**：
- 首次测试选择「小」或「中」
- 确认流程正确后再选择「大」进行压测
- 导入完成后及时清理不需要的测试数据

## YAML 生成

业务规则 YAML（`rules/business_logic.yaml`）驱动数据生成，包含：
- 用户分层（L0-L4）和分布比例
- 地区分布
- 事件序列（生命周期、日常活动、购买转化）
- 转化率和失败率
- 固定测试账号

生成 YAML 时必须先读取 Tracking Plan 获取合法事件名，不能自行编造。

## 造数脚本

```bash
# 小规模（UAT 验证）
./venv/bin/python <skill-repo>/sd-tracking-pipeline/scripts/generate_mock_data.py \
  --rules ./rules/business_logic.yaml \
  --tracking-plan "./references/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx" \
  --users 10 --days 7

# 中规模（默认，功能测试）
./venv/bin/python <skill-repo>/sd-tracking-pipeline/scripts/generate_mock_data.py \
  --rules ./rules/business_logic.yaml \
  --tracking-plan "./references/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx" \
  --users 100 --days 30 --sessions-per-day 5

# 大规模（压测）
./venv/bin/python <skill-repo>/sd-tracking-pipeline/scripts/generate_mock_data.py \
  --rules ./rules/business_logic.yaml \
  --tracking-plan "./references/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx" \
  --users 500 --days 30 --sessions-per-day 10
```

**注意**：
- `--tracking-plan` 建议显式指定，避免多端方案混淆
- 未指定时，脚本自动选择 `references/` 下最新 `.xlsx`

## 输出文件

输出到 `./mock_data/`：
- `<project>.jsonl` — 每行一条记录（最终文件）
- `<project>_sample.json` — 100 条样本，方便人工快速检查
- `<project>_identity_map.csv` — 用于校验 ID-Mapping 合并结果
- `uat_validation_report.md` — 业务规则违规报告
- `<project>_1k_part_*` — 数据分片（用于分批导入）

## 历史数据管理

### 扫描

```bash
# 查看 mock_data/ 占用
ls -lh mock_data/
du -sh mock_data/
```

### 备份

```bash
# 备份到日期目录
backup_dir="mock_data/backup/$(date +%Y%m%d)"
mkdir -p "$backup_dir"
mv mock_data/*.jsonl mock_data/*_part_* "$backup_dir/" 2>/dev/null || true
tar czf "${backup_dir}.tar.gz" "$backup_dir/"
rm -rf "$backup_dir/"
echo "已备份到 ${backup_dir}.tar.gz"
```

### 清理

```bash
# 仅保留最终 jsonl 和样本，删除分片和临时文件
find mock_data/ -name "*_part_*" -delete
find mock_data/ -name "*_identity_map.csv" -delete
# 保留 <project>.jsonl 和 <project>_sample.json
```

**注意**：清理前务必确认已不需要历史数据，或已备份。
