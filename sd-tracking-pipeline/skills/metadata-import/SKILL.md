---
name: metadata-import
version: 1.0.0
description: |
  元数据导入知识。通过 Open API 将埋点方案中的事件和属性定义
  导入 CDP 系统。当讨论元数据创建、API 对接、事件属性管理时自动加载。
allowed-tools:
  - Bash
  - Read
---

## 前置条件

- `.env` 中配置了 `API_KEY`（Open API 密钥）
- 埋点方案 Excel 已确认（`TRACKING_PLAN_PATH` 已设置）

## 配置说明

| 配置项 | 环境变量 | 用途 | 获取方式 |
|--------|----------|------|----------|
| CDP 地址 | `SA_HOST` | API 请求的基础地址 | 浏览器地址栏 |
| 项目标识 | `SA_PROJECT` | URL 参数中的项目 ID | URL 中 `project=` 的值 |
| **项目显示名** | `SA_PROJECT_NAME` | `sensorsdata-project` header 的值 | CDP 界面中显示的项目名称（如 `uat`） |
| Open API 密钥 | `API_KEY` | API 认证 | 神策后台 → 项目管理 → 权限管理 → 创建 API Key |
| 数据接收地址 | `SA_TRACK_URL` | HTTP API 数据导入 | 神策后台 → 数据接入 → HTTP API |

**⚠️ 注意**：`SA_PROJECT` 和 `SA_PROJECT_NAME` 可能不同：
- `SA_PROJECT` 是 URL 中的参数名（如 `default`、`mpdev`）
- `SA_PROJECT_NAME` 是 CDP 界面显示的名称（如 `uat`、`生产环境`），用于 `sensorsdata-project` header

如果 `.env` 中只有 `SA_PROJECT`，尝试用它作为 `sensorsdata-project` header 的值；如果 404，询问用户正确的项目显示名。

## 导入脚本

```bash
python3 scripts/import_meta_data.py \
  --tracking-plan "$TRACKING_PLAN_PATH"
```

自动完成：
1. 检查 API 连接
2. 从 Excel 读取事件列表，逐个创建元事件
3. 读取事件属性，写入对应事件
4. 读取用户属性，批量写入

系统保留字段名（如 `Id`、`PersonEmail`）自动跳过。

## 元数据预检查

数据导入前，确认 JSONL 中所有事件和属性已在 CDP 中创建：

```bash
python3 scripts/check_metadata.py \
  --jsonl "./mock_data/<project>.jsonl"
```

## 常见问题

**字段创建报 ALREADY_EXISTS：** 正常，脚本自动跳过，不影响其他字段。

**元事件属性写入失败（10005 错误）：** 通常是事件上有特殊关联字段，脚本已自动处理常见情况。

**check_metadata.py 报缺少事件/属性：** 先运行 `import_meta_data.py` 补充元数据，再重新检查，通过后再导入数据。

**sdeliver init 找不到命令：** 运行 `<skill-repo>/setup` 安装，确认 `~/.local/bin` 在 PATH 中。
