# 神策数据交付 Skill 库

神策数据交付工程师的 AI skill 集合，覆盖客户项目交付全流程。

## 安装

### 全局安装（推荐）

在任意目录执行，安装后在所有项目中均可使用：

```bash
npx skills add sensorsdata/deliver-skills -g
```

支持的 agent：Claude Code、Hermes Agent、OpenCode、Cursor、Codex、GitHub Copilot

### 项目级安装

只在当前项目目录下生效：

```bash
npx skills add sensorsdata/deliver-skills
```

### 更新

```bash
npx skills update deliver-skills
```

## 初始化（每个新客户项目执行一次）

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入客户环境信息
# 必填：SA_HOST、SA_PROJECT、CLIENT_NAME
```

之后所有 skill 脚本自动读取 `.env`，无需重复传参。

## Skill 清单

| Skill | 触发场景 | 自动化程度 |
|-------|----------|------------|
| [tracking-setup-e2e](./tracking-setup-e2e/SKILL.md) | 客户新项目启动，需要完整的数据采集和分析能力 | Phase 3/4a/4b 全自动 |
| [event-validation](./event-validation/SKILL.md) | 埋点上线后验证数据正确性，或数据异常排查 | 全自动 |
| [cdp-operations](./cdp-operations/SKILL.md) | 在神策 CDP 中完成数据分析、同步、用户管理等操作 | browser automation |
| [server-sizing](./server-sizing/SKILL.md) | 新客户部署前或扩容时评估服务器资源 | 全自动（纯计算） |
| [sit-uat](./sit-uat/SKILL.md) | 项目上线前的系统集成测试或用户验收测试 | browser automation |
| [tech-design](./tech-design/SKILL.md) | 项目启动前输出技术方案和架构图 | 文档生成 |

## 使用方式

在 Claude Code、Hermes 或 OpenCode 中，直接描述工作场景，AI 自动匹配对应 skill：

> "客户新项目要做埋点，帮我走一遍流程"  
> "验证一下这批埋点数据是否正确"  
> "帮我评估一下服务器配置"

也可以显式调用：`/tracking-setup-e2e`、`/event-validation` 等。

## 依赖

- Python 3.10+
- `pip install openpyxl python-dotenv`
- [gstack/browse](https://github.com/gstack/browse)（browser automation，已包含在 gstack 中）

## 贡献新 Skill

1. 在项目根目录新建 `<skill-name>/` 目录
2. 按[设计规范](./docs/superpowers/specs/2026-05-20-deliver-skills-design.md)编写 `SKILL.md`
3. 脚本放在 `<skill-name>/scripts/`
4. 在本 README 添加索引条目
5. 提交 PR

## v2 规划

- `solution-recovery` — 常见技术方案恢复
- `issue-diagnosis` — 问题诊断与根因分析
