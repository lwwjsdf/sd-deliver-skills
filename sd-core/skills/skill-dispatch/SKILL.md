---
name: skill-dispatch
version: 1.0.0
description: |
  神策数据交付 Skill 调度逻辑。感知当前客户项目状态，匹配用户意图到对应 skill。
  当用户说"帮我看看项目状态"、"我能做什么"、"下一步用哪个 skill"时使用。
  当用户描述交付工作场景时（埋点、服务器、SIT、UAT、FAQ），匹配并推荐对应 skill。
allowed-tools:
  - Bash
  - Read
---

## Skill 调度映射

当用户描述工作场景时，匹配并推荐对应 skill，**不直接执行交付步骤**：

| 用户描述 | 推荐 Command |
|---------|-------------|
| 项目状态、项目档案、onboard、初始化 | `/sd-onboard` / `/sd-status` |
| 埋点、数据采集、tracking、造数、模拟数据、元数据导入 | `/sd-setup-tracking` |
| 数据异常、校验、验证、数据上线后、数据质量 | `/sd-validate-data` |
| 服务器、资源评估、扩容、部署配置 | `/sd-size-server` |
| 技术方案、架构图、评审材料 | `/sd-design-tech` |
| SIT、UAT、测试、上线验收 | `/sd-run-sit` |
| 容量评估、带宽、信创、ID3、排查 SOP | `/sd-ask-faq` |

## 故障排查

### Skill 加载失败

如果用户报告 `[Failed to load skill: xxx]`：

1. **先手动验证**：直接调用 skill 看是否能加载
2. **手动加载成功** → 告知用户是临时问题，直接继续任务
3. **手动加载也失败** → 检查 SKILL.md 格式（YAML frontmatter 是否完整、是否有语法错误）
4. **文件存在但加载失败** → 检查 skill 目录权限问题

常见原因：
- YAML frontmatter 中 `allowed-tools` 格式错误（应为列表格式 `- Bash`）
- 文件编码问题（应为 UTF-8）
- 目录名与 SKILL.md 中的 `name` 字段不匹配

### 大文档读取

对于 >1MB 的 `.doc`/`.docx` 文件，避免一次性加载全部内容。使用 `shared/` 中的工具读取。

### 完成状态协议

每次工作流结束时报告：
- **DONE** — 完成，已提供依据
- **DONE_WITH_CONCERNS** — 完成，但有需关注的问题（逐条列出）
- **BLOCKED** — 无法继续，说明原因和已尝试的方法
- **NEEDS_CONTEXT** — 缺少必要信息，说明具体需要什么
