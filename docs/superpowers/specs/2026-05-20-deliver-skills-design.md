# 神策数据交付 Skill 库设计文档

**日期：** 2026-05-20
**阶段：** v1 Startup

## 背景与目标

沉淀神策数据在客户项目交付过程中的常见 skill，帮助内部交付工程师/实施顾问将重复性工作标准化，从 copilot 模式进化到 end-to-end 自动完成交付任务。

Skill 遵循标准 skill 协议，可运行在 Claude Code、OpenCode、Cursor 等常见工具中，并可通过 agent-teams 中集成的 opencode 作为执行层实现自动化操作。

## 范围

v1 包含 6 个核心 skill，覆盖交付全流程的高频场景。后续版本可在此基础上扩展。

## 目录结构

```
deliver-skills/
  event-schema-gen/
    SKILL.md
  event-validation/
    SKILL.md
  cdp-config/
    SKILL.md
  server-sizing/
    SKILL.md
  solution-recovery/
    SKILL.md
  issue-diagnosis/
    SKILL.md
  README.md
  docs/
    superpowers/
      specs/
        2026-05-20-deliver-skills-design.md
```

## Skill 规范

每个 SKILL.md 遵循统一结构：

```markdown
---
name: <skill-name>
description: <一句话，说明何时触发这个 skill>
---

# <Skill 标题>

## 适用场景（When to Use）
## 核心原则（Iron Law）
## 执行阶段（Phases）
## 输出模板（Output Template）
## 常见问题（Common Pitfalls）
```

**设计约定：**
- 触发条件用中文写，贴近工程师实际用语
- Iron Law 每个 skill 至少一条，防止 AI 跳过关键步骤
- Phases 强制顺序执行
- 输出模板标准化交付物格式，保证不同工程师产出一致

## v1 Skill 清单

### 1. event-schema-gen — 埋点方案生成

**触发：** 客户需要制定埋点方案、新功能上线前规划埋点

**Iron Law：** 先理解业务目标，再设计事件。不允许在不了解分析需求的情况下直接输出埋点表。

**Phases：**
1. 业务目标确认
2. 关键路径梳理
3. 事件/属性设计
4. 方案文档输出

**输出：** 标准埋点方案表（事件名、触发时机、属性列表、示例值）

---

### 2. event-validation — 埋点数据校验

**触发：** 埋点上线后验证数据是否正确、客户反馈数据异常

**Iron Law：** 必须对比方案文档与实际数据，不允许仅凭肉眼判断数据是否正确。

**Phases：**
1. 获取埋点方案
2. 抓取实际数据
3. 逐项比对
4. 输出差异报告

**输出：** 校验报告（通过/异常/缺失三类，附修复建议）

---

### 3. cdp-config — CDP 常规配置

**触发：** 需要在神策 CDP 中配置看板、标签、报表等标准功能

**Iron Law：** 配置前必须确认客户的分析目标，不允许按模板照搬配置而不理解业务含义。

**Phases：**
1. 需求确认
2. 数据源检查
3. 配置执行
4. 验证结果

**输出：** 配置完成确认单（配置项、截图/验证结果、注意事项）

---

### 4. server-sizing — 服务器资源评估

**触发：** 新客户部署前评估、现有客户扩容评估

**Iron Law：** 必须基于客户实际数据量和增长预期评估，不允许直接套用默认配置。

**Phases：**
1. 数据规模收集
2. 增长预期确认
3. 资源计算
4. 方案输出

**输出：** 资源评估报告（推荐配置、最低配置、扩容触发条件）

---

### 5. solution-recovery — 常见技术方案恢复

**触发：** 客户环境出现已知问题需要恢复、标准方案需要重新部署

**Iron Law：** 执行恢复操作前必须确认当前环境状态，不允许在未诊断的情况下直接执行恢复步骤。

**Phases：**
1. 环境状态确认
2. 匹配已知方案
3. 执行恢复
4. 验证恢复结果

**输出：** 恢复操作记录（执行步骤、验证结果、后续建议）

---

### 6. issue-diagnosis — 问题诊断

**触发：** 客户反馈异常、数据问题、系统故障

**Iron Law：** 必须找到根因再给解决方案，不允许在未复现问题的情况下直接给修复步骤。

**Phases：**
1. 问题复现
2. 信息收集
3. 根因定位
4. 解决方案输出

**输出：** 诊断报告（问题描述、根因、解决步骤、预防建议）

## 迭代机制

- v1 Startup：6 个核心 skill，今晚完成 SKILL.md 初稿
- v2+：根据交付工程师实际使用反馈扩展 skill 数量和深度
- 每个 skill 独立迭代，不影响其他 skill
- 新 skill 贡献：按统一规范新增目录和 SKILL.md 即可

## 后续步骤

1. 为每个 skill 编写完整的 SKILL.md
2. 编写 README.md skill 索引
3. 在 agent-teams 中部署验证至少一个 skill
4. 收集工程师使用反馈，进入 v2 迭代
