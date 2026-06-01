# sdeliver — 神策数据交付 Skill 库

神策数据交付工程师的 AI skill 集合，覆盖客户项目交付全流程。

支持 Claude Code、Cursor、Hermes、OpenCode 等主流 agent 框架。

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/sensorsdata/sd-deliver-skills.git ~/sd-deliver-skills
cd ~/sd-deliver-skills
```

### 2. 运行安装脚本

```bash
./setup
```

自动检测本机已安装的 agent 框架，将 skill 注册到对应目录，并安装 `sdeliver` CLI。

**指定框架安装：**

```bash
./setup --host claude    # 只安装到 Claude Code
./setup --host hermes    # 只安装到 Hermes
./setup --host cursor    # 只安装到 Cursor
./setup --host opencode  # 只安装到 OpenCode
./setup --host all       # 安装到所有框架
```

**安装位置：**

| Agent | Skills 目录 |
|-------|------------|
| Claude Code | `~/.claude/skills/` |
| Hermes | `~/.hermes/skills/` |
| Cursor | `~/.cursor/skills/` |
| OpenCode | `~/.config/opencode/skills/` |

### 3. 配置 PATH（首次安装）

`sdeliver` CLI 安装到 `~/.local/bin/`，如果该目录不在 PATH 中：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 更新

```bash
cd ~/sd-deliver-skills
git pull
./setup
```

## 新客户项目初始化

每个新客户项目执行一次，在 skill 仓库**之外**创建独立的项目目录：

```bash
sdeliver init <client-name> [project-dir]
```

**示例：**

```bash
sdeliver init westk ~/projects/westk
```

生成的目录结构：

```
~/projects/westk/
├── .env              ← 填写 CDP 连接信息
├── .gitignore
├── references/       ← 放入客户提供的埋点方案 Excel
├── rules/            ← business_logic.yaml 生成位置
└── mock_data/        ← 模拟数据生成位置
```

填写 `.env` 后验证配置：

```bash
cd ~/projects/westk
sdeliver check
```

`.env` 配置项说明：

| 变量 | 说明 | 何时填写 |
|------|------|----------|
| `SA_HOST` | 神策 CDP 地址 | 项目启动时 |
| `SA_PROJECT` | 项目 ID | 项目启动时 |
| `CLIENT_NAME` | 客户名称 | 项目启动时 |
| `TRACKING_PLAN_PATH` | 埋点方案 Excel 路径 | 客户确认方案后 |
| `API_KEY` | Open API 密钥 | 元数据导入前 |
| `SA_TRACK_URL` | 数据接收地址 | 数据导入前 |

## 使用方式

在 agent 中直接描述工作场景，AI 自动匹配对应 skill：

> "客户新项目要做埋点，帮我走一遍流程"
> "验证一下这批埋点数据是否正确"
> "帮我评估一下服务器配置"

也可以显式调用：

```
/tracking-setup-e2e
/event-validation
/cdp-operations
```

## Skill 清单

| Skill | 触发场景 | 自动化程度 |
|-------|----------|------------|
| [tracking-setup-e2e](./tracking-setup-e2e/SKILL.md) | 客户新项目启动，需要完整的数据采集和分析能力 | Phase 3/4a/4b 全自动 |
| [event-validation](./event-validation/SKILL.md) | 埋点上线后验证数据正确性，或数据异常排查 | 全自动 |
| [cdp-operations](./cdp-operations/SKILL.md) | 在神策 CDP 中完成数据分析、同步、用户管理等操作 | browser automation |
| [server-sizing](./server-sizing/SKILL.md) | 新客户部署前或扩容时评估服务器资源 | 全自动（纯计算） |
| [sit-uat](./sit-uat/SKILL.md) | 项目上线前的系统集成测试或用户验收测试 | browser automation |
| [tech-design](./tech-design/SKILL.md) | 项目启动前输出技术方案和架构图 | 文档生成 |

## 依赖

- Python 3.10+
- `pip install openpyxl python-dotenv requests sensorsanalytics`

## 贡献新 Skill

1. 在仓库根目录新建 `<skill-name>/` 目录
2. 按[设计规范](./docs/superpowers/specs/2026-05-20-deliver-skills-design.md)编写 `SKILL.md`（需包含 `name:` frontmatter）
3. 脚本放在 `<skill-name>/scripts/`
4. 在本 README 的 Skill 清单中添加条目
5. 运行 `./setup` 注册新 skill
6. 提交 PR
