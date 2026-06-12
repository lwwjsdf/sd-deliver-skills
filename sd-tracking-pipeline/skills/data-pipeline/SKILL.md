---
name: data-pipeline
version: 1.0.0
description: |
  数据管道全流程知识。从埋点方案解析（business_logic.yaml）到模拟数据生成、
  元数据导入、数据导入和结果校验。
  当讨论数据流水线、导入流程、YAML 规范、CDP 对接时自动加载。
allowed-tools:
  - Bash
  - Read
---

## 核心原则

**Iron Law: 必须先完成采集方案设计并经客户确认，再进行后续任何步骤。**

## AI 交互规则（关键）

当用户触发 `/setup-tracking` command 时，AI **必须** 遵守以下规则：

### 1. 绝不自动执行
- 先展示 command 说明和前置条件
- 等待用户输入 `确认`
- 每个 Phase 执行前再次确认

### 2. 前置检查优先
Phase 1 之前检查 `.env` 完整性：
- `TRACKING_PLAN_PATH` 必须存在
- `SA_HOST`、`SA_PROJECT` 必须设置
- `SA_TOKEN`（Phase 6 需要）
- `API_KEY`（Phase 5/7 需要）— **如果缺失，警告但不阻塞，询问是否跳过相关 Phase**
- `mock_data/` 历史文件 — **扫描并询问是否清理/备份**

### 3. Phase 失败立即停止
- 任一 Phase 失败（error 或脚本 crash）→ 停止执行
- 报告失败原因
- 询问：修复后重试 / 跳过 / 取消

### 4. 阶段间确认
每个 Phase 完成后：
- 简要报告结果
- 询问：继续 / 跳过 / 取消

### 5. 数据量选择
Phase 4（造数）前询问规模：
- **小**：10 用户 × 7 天，~1,000 条（UAT 验证）
- **中**：100 用户 × 30 天，~15 万条（功能测试）⭐ 默认
- **大**：500 用户 × 30 天，~150 万条（压测）
- **自定义**：用户指定

### 6. 历史数据管理
- Phase 0 扫描 `mock_data/` 历史文件，询问备份/清理/保留
- Phase 8 完成后询问是否清理临时文件

## 多轮迭代流程

造数通常需要多轮迭代，每轮收集交付团队反馈并修复：

```
Round 1: 初始造数 → 导入 → 收集反馈 → 记录到 MOCK_DATA_ITERATIONS.md
Round 2: 读取反馈 → 修复 YAML → 重新造数 → 导入前校验（覆盖历史问题） → 导入 → 验证
Round 3+: 重复直到交付团队满意
```

**关键要求**：
- 每轮导入后必须收集交付团队反馈
- 所有反馈必须记录到 `references/MOCK_DATA_ITERATIONS.md`
- 下一轮造数前必须检查迭代记录，确认历史问题已修复
- 导入前校验必须覆盖迭代记录中所有未关闭的问题

## 数据管道阶段

```
Phase 0 前置检查 → Phase 1 YAML 生成 → Phase 2 验证 → Phase 3 枚举确认 → Phase 4 造数
  → Phase 5 导入前校验 → Phase 6 元数据导入 → Phase 7 数据导入
  → Phase 8 导入后校验（OpenAPI） → Phase 9 更新迭代记录 → Phase 10 清理
```

快速入口（已有方案时）：

| 用户说 | 从哪里开始 |
|--------|-----------|
| 已有确认好的埋点方案 Excel | Phase 1（生成 business_logic.yaml） |
| 已有 business_logic.yaml | Phase 2（验证） |
| YAML 已验证通过，要确认枚举值 | Phase 3（枚举值确认） |
| 枚举值已确认，要造数 | Phase 4（造数） |
| 已造好数据，要导入 CDP | Phase 6（先做 Phase 5 元数据预检查） |
| 已导入元数据，要造数 | Phase 4 |

## 目录约定

所有脚本在**客户项目目录**下运行，自动读取 `.env`：

```
~/projects/<client-name>/
├── .env
├── rules/business_logic.yaml    ← Phase 1 生成
├── mock_data/*.jsonl            ← Phase 4 生成
│   └── backup/YYYYMMDD/         ← 历史数据备份
├── references/
│   ├── tracking-plan.xlsx       ← Phase 0 准备
│   └── MOCK_DATA_ITERATIONS.md  ← 迭代记录（每轮更新）
```

## 脚本路径

脚本位于 `sd-tracking-pipeline/scripts/`，在客户项目目录下调用的通用方式：

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/<script>.py
```

其中 `<skill-repo>` 由 Preamble 自动获取（`sdeliver-config get skill_repo_path`）。

## 依赖管理

脚本采用**按需自动安装**策略：
- 每个脚本在运行时自动检查所需 Python 依赖
- 缺失时自动调用 `pip install` 安装
- 安装失败时给出手动安装命令

**常见依赖：**
| 脚本 | 依赖 |
|------|------|
| `generate_mock_data.py` | `openpyxl`, `python-dotenv` |
| `import_meta_data.py` | `openpyxl`, `python-dotenv`, `requests` |
| `crawl_web_pages.py` | `requests`, `beautifulsoup4` |
| `tracking_plan.py` | `openpyxl` |

**注意**：首次运行某个脚本时可能需要等待依赖安装完成。

## 凭证说明

| 凭证 | 用途 | 获取方式 |
|------|------|----------|
| `SA_TOKEN` | HTTP API 数据导入（Phase 6） | 神策后台 → 数据接入 → HTTP API |
| `API_KEY` | Open API 元数据管理 + 数据查询（Phase 5/7） | 神策后台 → 项目管理 → 权限管理 → 创建 API Key |

**注意**：Phase 5/7 需要 `API_KEY`，如果缺失可以跳过，但元数据不会导入到 CDP，校验也无法执行。

## 常见问题

**yaml_validator.py 报 event not found：** YAML 中的事件名与 Tracking Plan 不一致。用 `tracking_plan.py` 查询合法事件名列表。

**yaml_validator.py 报 ratios sum to X：** 检查 `user_segments` 或 `region_distribution` 各项比例，确保加总精确为 1.0。

**yaml_validator.py crash（identity_priority）：** 已修复。如果 `identity_priority` 的值是列表格式（如 `[- unionid, - mobile]`），验证器现在会正确处理。

**import_meta_data.py 报 ALREADY_EXISTS：** 正常，脚本自动跳过，不影响其他字段。

**validate_import.py 显示条数偏多：** 正常，CDP 中可能有历史数据，只要不是 0 或偏少即可。

**模拟数据不够真实：** 向客户要 1-2 个真实业务场景的描述，更新 YAML 后重新造数。

**历史数据太多，扫描慢：** 在 Phase 0 时选择 `备份` 或 `清理`，将旧数据移到 `mock_data/backup/YYYYMMDD/`。

**如何记录迭代反馈：** 每轮导入后，在 `references/MOCK_DATA_ITERATIONS.md` 中添加新的 Round 章节，记录交付团队反馈的问题、验证结果和待修复项。

**导入前校验发现历史问题未修复：** 停止导入，修复 YAML 后重新造数。不能带着已知问题导入数据。

**导入后校验条数偏少：** 可能原因：1) 数据处理延迟（等 1-2 分钟重试）；2) 元数据未导入；3) 部分数据导入失败。查看导入日志排查。
