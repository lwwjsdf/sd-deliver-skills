# 神策数据交付 Skill 库设计文档

**日期：** 2026-05-20
**阶段：** v1 Startup

---

## 背景与目标

沉淀神策数据在客户项目交付过程中的常见 skill，帮助内部交付工程师/实施顾问将重复性工作标准化，从 copilot 模式进化到 end-to-end 自动完成交付任务。

Skill 遵循标准 skill 协议，可运行在 Claude Code、OpenCode、Cursor 等常见工具中，并可通过 agent-teams 中集成的 opencode 作为执行层实现自动化操作。

---

## 目录结构规范

```
deliver-skills/
  README.md                        # Skill 索引
  .env.example                     # 环境变量模板（不提交真实值）
  shared/                          # 跨 skill 共用工具
    cdp_client.py                  # 神策 CDP API 封装（认证、fetch）
    browse_auth.py                 # gstack/browse cookie 导入封装
    excel_parser.py                # 埋点方案 Excel 解析工具
  <skill-name>/
    SKILL.md                       # Skill 定义（AI 读取的核心文件）
    scripts/                       # 自动化脚本
      <action>.py
    templates/                     # 输出模板（报告、SOP 等）
      <template>.md
    examples/                      # 示例输入文件
      sample_tracking_plan.xlsx
  docs/
    superpowers/
      specs/                       # 设计文档
      plans/                       # 计划文档
```

**约定：**
- 每个 skill 目录只放该 skill 专属的内容
- 客户文件（Excel、JSON 等）不提交到仓库，放在 skill 目录外或 `.gitignore`
- 共用逻辑统一放 `shared/`，不在各 skill 里重复实现

---

## 环境变量规范

所有需要用户输入的连接信息统一通过 `.env` 文件管理，**不通过命令行参数传递**。

### `.env.example`（模板，提交到仓库）

```bash
# 神策 CDP 连接信息
SA_HOST=https://demo.sensorsdata.cn     # CDP 地址，不带末尾斜杠
SA_PROJECT=mpdev                        # 项目 ID
SA_TOKEN=                               # HTTP API token（用于数据导入）

# 客户项目信息
CLIENT_NAME=                            # 客户名称（用于输出文件命名）
TRACKING_PLAN_PATH=                     # 埋点方案 Excel 路径（绝对路径或相对路径）
```

### 变量输入时机

| 变量 | 输入时机 | 由谁输入 |
|------|----------|----------|
| `SA_HOST` | 项目启动时，一次性配置 | 交付工程师 |
| `SA_PROJECT` | 项目启动时，一次性配置 | 交付工程师 |
| `SA_TOKEN` | 需要数据导入时配置 | 交付工程师（从神策后台获取） |
| `CLIENT_NAME` | 项目启动时，一次性配置 | 交付工程师 |
| `TRACKING_PLAN_PATH` | 客户确认埋点方案后配置 | 交付工程师 |

**原则：变量只在项目开始时配置一次，后续所有 skill 自动读取，不再重复询问。**

### 脚本读取方式

```python
# shared/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  # 自动读取当前目录或父目录的 .env

SA_HOST = os.getenv("SA_HOST", "").rstrip("/")
SA_PROJECT = os.getenv("SA_PROJECT", "")
SA_TOKEN = os.getenv("SA_TOKEN", "")
TRACKING_PLAN_PATH = os.getenv("TRACKING_PLAN_PATH", "")

def validate(required: list[str]):
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"错误：缺少必要配置，请在 .env 中设置：{', '.join(missing)}")
        raise SystemExit(1)
```

---

## SKILL.md 规范

每个 SKILL.md 遵循统一结构：

```markdown
---
name: <skill-name>
description: <一句话，说明何时触发这个 skill>
---

# <Skill 标题>

## 适用场景（When to Use）
## 核心原则（Iron Law）
## 前置条件（Prerequisites）   ← 列出需要哪些 .env 变量已配置
## 执行阶段（Phases）
## 输出模板（Output Template）
## 常见问题（Common Pitfalls）
```

### 前置条件（Prerequisites）节规范

每个涉及自动化的 skill 必须声明所需的环境变量：

```markdown
## 前置条件

运行本 skill 前，确认 `.env` 中已配置：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `SA_HOST` | 神策 CDP 地址 | 客户环境 URL |
| `SA_PROJECT` | 项目 ID | URL 中的 `project=` 参数 |
| `TRACKING_PLAN_PATH` | 埋点方案 Excel 路径 | 客户确认后的方案文件 |

浏览器登录态：脚本启动时自动通过 gstack/browse 导入，无需手动操作。
```

### 执行阶段中的自动化标注

Phase 中区分人工步骤和自动化步骤：

```markdown
### Phase 3：模拟数据生成 🤖

> 自动化执行，运行脚本即可。

\```bash
python3 tracking-setup-e2e/scripts/generate_mock_data.py
\```

### Phase 2：采集方案设计 👤

> 需要人工参与，AI 辅助输出，客户确认后才能继续。
```

- 🤖 = 全自动，脚本执行
- 👤 = 需要人工参与或确认

---

## v1 Skill 清单

### 1. tracking-setup-e2e — 埋点全链路交付

**触发：** 客户新项目启动、新业务场景需要完整的数据采集和分析能力

**Iron Law：** 必须先完成采集方案设计并经客户确认，再进行后续任何步骤。

**Phases：**

| Phase | 内容 | 类型 |
|-------|------|------|
| 1 | 业务目标确认 | 👤 |
| 2 | 采集方案设计，输出埋点方案表，客户确认 | 👤 |
| 3 | 模拟数据生成 | 🤖 |
| 4a | 元事件 + 用户属性导入 CDP | 🤖 |
| 4b | 模拟数据导入 | 🤖 |
| 4c | 看板创建 | 👤（待 API 支持后升级为 🤖）|
| 5 | 资产迁移 | 🤖 |

**所需 .env 变量：** `SA_HOST`, `SA_PROJECT`, `SA_TOKEN`, `TRACKING_PLAN_PATH`

---

### 2. event-validation — 埋点数据校验

**触发：** 埋点上线后验证数据是否正确、客户反馈数据异常

**Iron Law：** 必须对比方案文档与实际数据，不允许仅凭肉眼判断。

**Phases：**

| Phase | 内容 | 类型 |
|-------|------|------|
| 1 | 获取埋点方案 | 👤 |
| 2 | 抓取实际数据 | 🤖 |
| 3 | 逐项比对 | 🤖 |
| 4 | 输出差异报告 | 🤖 |

**所需 .env 变量：** `SA_HOST`, `SA_PROJECT`, `TRACKING_PLAN_PATH`

---

### 3. cdp-operations — CDP 系统操作

**触发：** 需要在神策 CDP 中完成数据分析、数据同步、用户管理、事件创建、运营计划等操作

**Iron Law：** 操作前必须确认客户的业务目标，不允许按模板照搬配置。

**所需 .env 变量：** `SA_HOST`, `SA_PROJECT`

---

### 4. server-sizing — 服务器资源评估

**触发：** 新客户部署前评估、现有客户扩容评估

**Iron Law：** 必须基于客户实际数据量和增长预期评估，不允许直接套用默认配置。

**所需 .env 变量：** 无（纯计算，不连接系统）

---

### 5. sit-uat — SIT/UAT 测试设计与执行

**触发：** 项目上线前需要完成系统集成测试或用户验收测试

**Iron Law：** 必须先完成测试用例设计并确认覆盖范围，再开始执行。

**所需 .env 变量：** `SA_HOST`, `SA_PROJECT`

---

### 6. tech-design — 技术方案设计

**触发：** 项目启动前需要输出技术方案、客户需要架构评审材料

**Iron Law：** 必须先理解业务约束和技术现状，再输出方案。

**所需 .env 变量：** 无（纯文档输出）

---

## 项目初始化流程

每个新客户项目开始时，执行一次：

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env，填入客户环境信息
#    SA_HOST, SA_PROJECT, CLIENT_NAME 是必填项

# 3. 验证连接
python3 shared/cdp_client.py --check
```

之后所有 skill 脚本直接读取 `.env`，无需再传参数。

---

## 迭代机制

- v1 Startup：6 个核心 skill，完成 SKILL.md 和核心脚本
- v2+：根据交付工程师实际使用反馈扩展
- 每个 skill 独立迭代，不影响其他 skill
- 新 skill 贡献：按统一规范新增目录，在 README 添加索引
