---
name: sd-remember
description: 将用户确认的项目事实写入 PROJECT_CONTEXT.yaml，供后续 skill 复用
argument-hint: "<key> <value> [--source <command>]"
status: active
---

# /sd-remember — 记录项目事实到上下文

> **定位**：通用记忆入口。任何 skill/command 都可以通过此命令将用户确认的事实写入 `PROJECT_CONTEXT.yaml`，避免下次重复询问。

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 把你确认的事实结构化写入项目根目录的 `PROJECT_CONTEXT.yaml`。
>
> **什么时候用：**
> - 用户在某次对话中补充了项目信息（DAU、Region、SLA 等）
> - 一个 skill 采集到的信息需要被其他 skill 复用
> - 你想手动修正或补充 PROJECT_CONTEXT
>
> 1/y = 确认写入
> 0/n = 取消
> 2/s = 跳过

## 用法

```bash
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set \
  business.dau 1000000 \
  --source sd-design-performance-test
```

支持的数据类型：

```bash
# number
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set business.dau 1000000

# string
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set infra.cloud AWS

# boolean
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set infra.include_cdp true

# list
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set business.products '["CDP","MA"]'
```

## 查询已记录的事实

```bash
# 列出所有
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py list

# 查询单个
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py get business.dau

# 检查某 skill 缺少哪些上下文
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py check \
  --skill sd-design-performance-test
```

## Agent 使用约定

1. **Skill 提问前**，先 `check` 该 skill 的 required keys，只问缺失的。
2. **用户回答后**，立即 `set` 写入 PROJECT_CONTEXT.yaml。
3. **同一事实 3 天内不要重复询问**，除非用户主动要求更新。
4. **敏感信息**（API key、密码、token）不要写入，保留在 `.env`。

## 完成建议

- "已记录。下次执行相关 skill 时会自动读取这些事实。"
