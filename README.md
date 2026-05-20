# 神策数据交付 Skill 库

神策数据交付工程师的 AI skill 集合，覆盖客户项目交付全流程。

## Skill 清单

| Skill | 触发场景 |
|-------|----------|
| [tracking-setup-e2e](./tracking-setup-e2e/SKILL.md) | 客户新项目启动，需要完整的数据采集和分析能力 |
| [event-validation](./event-validation/SKILL.md) | 埋点上线后验证数据正确性，或数据异常排查 |
| [cdp-operations](./cdp-operations/SKILL.md) | 在神策 CDP 中完成数据分析、同步、用户管理等操作 |
| [server-sizing](./server-sizing/SKILL.md) | 新客户部署前或扩容时评估服务器资源 |
| [sit-uat](./sit-uat/SKILL.md) | 项目上线前的系统集成测试或用户验收测试 |
| [tech-design](./tech-design/SKILL.md) | 项目启动前输出技术方案和架构图 |

## 使用方式

在 Claude Code、OpenCode 或 Cursor 中，直接描述你的工作场景，AI 会自动匹配对应 skill。

也可以显式调用：`/tracking-setup-e2e`、`/event-validation` 等。

## 贡献新 Skill

1. 在项目根目录新建 `<skill-name>/` 目录
2. 按统一规范编写 `SKILL.md`（参考现有 skill）
3. 在本 README 中添加索引条目
4. 提交 PR

## v2 规划

- `solution-recovery` — 常见技术方案恢复
- `issue-diagnosis` — 问题诊断与根因分析
