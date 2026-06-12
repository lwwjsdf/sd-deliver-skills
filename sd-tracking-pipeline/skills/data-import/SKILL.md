---
name: data-import
version: 1.0.0
description: |
  数据导入 CDP 知识。覆盖 BatchConsumer 数据接入、元数据预检查、
  导入后 OpenAPI 校验、导入失败排查和历史数据清理。
  当讨论数据导入、BatchConsumer、导入后验证、CDP 落库问题时自动加载。
allowed-tools:
  - Bash
  - Read
---

## 前置条件

- 模拟数据已生成并通过本地校验
- `.env` 中配置了 `SA_HOST`、`SA_PROJECT`、`SA_TRACK_URL`、`API_KEY`
- 元数据导入需要 `API_KEY`
- 导入后校验需要 `API_KEY`

## 配置说明

| 配置项 | 环境变量 | 用途 | 获取方式 |
|--------|----------|------|----------|
| CDP 地址 | `SA_HOST` | API 请求基础地址 | 浏览器地址栏 |
| 项目标识 | `SA_PROJECT` | URL 参数中的项目 ID | URL 中 `project=` 的值 |
| 项目显示名 | `SA_PROJECT_NAME` | `sensorsdata-project` header | CDP 界面显示的项目名称（如 `uat`） |
| Open API 密钥 | `API_KEY` | 元数据导入 + 导入后查询 | 神策后台 → 项目管理 → 权限管理 → 创建 API Key |
| 数据接收地址 | `SA_TRACK_URL` | BatchConsumer 数据接入 | 神策后台 → 数据接入 → HTTP API |

## 导入三阶段

```
Step 1: 元数据导入（import_meta_data.py）
   ↓ 创建事件、事件属性、用户属性
Step 2: 元数据预检查（check_metadata.py）
   ↓ 确认 JSONL 中事件/属性已在 CDP 定义
Step 3: 数据导入（import_mock_data.py）
   ↓ BatchConsumer 批量写入
Step 4: 导入后校验（validate_import.py / validate_post_import.py）
   ↓ OpenAPI 查询落库条数和属性完整性
```

## 脚本

### 元数据导入

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/import_meta_data.py \
  --tracking-plan "./references/<tracking-plan>.xlsx"
```

未指定 `--tracking-plan` 时，脚本自动选择 `references/` 下最新 `.xlsx`。

### 元数据预检查

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/check_metadata.py \
  --jsonl "./mock_data/<project>.jsonl"
```

### 数据导入

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/import_mock_data.py \
  --jsonl "./mock_data/<project>.jsonl"
```

### 导入后校验

```bash
python3 <skill-repo>/sd-tracking-pipeline/scripts/validate_import.py \
  --jsonl "./mock_data/<project>.jsonl" \
  --wait 60
```

## 常见问题

**ALREADY_EXISTS：** 正常，脚本自动跳过。

**10005 错误：** 事件上有特殊关联字段，脚本已处理常见情况。

**导入后条数偏少：**
1. 等待 1-2 分钟（数据处理延迟）
2. 检查元数据是否已导入
3. 查看 `import_mock_data.py` 输出日志

**OpenAPI 404：** 检查 `API_KEY` 和 `SA_PROJECT_NAME`。

## 历史数据清理

```bash
# 扫描
python3 <skill-repo>/sd-tracking-pipeline/scripts/mock_data_manager.py scan

# 备份
python3 <skill-repo>/sd-tracking-pipeline/scripts/mock_data_manager.py backup --compress

# 清理临时文件
python3 <skill-repo>/sd-tracking-pipeline/scripts/mock_data_manager.py clean
```
