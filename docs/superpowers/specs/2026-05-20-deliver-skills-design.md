# 神策数据交付 Skill 库设计文档

**日期：** 2026-05-20
**阶段：** v1 Startup

## 背景与目标

沉淀神策数据在客户项目交付过程中的常见 skill，帮助内部交付工程师/实施顾问将重复性工作标准化，从 copilot 模式进化到 end-to-end 自动完成交付任务。

Skill 遵循标准 skill 协议，可运行在 Claude Code、OpenCode、Cursor 等常见工具中，并可通过 agent-teams 中集成的 opencode 作为执行层实现自动化操作。

## 范围

v1 包含 6 个核心 skill，聚焦交付侧高频场景。运维工单类（问题诊断、方案恢复）列入 v2 规划。

## 目录结构

```
deliver-skills/
  tracking-setup-e2e/
    SKILL.md
  event-validation/
    SKILL.md
  cdp-operations/
    SKILL.md
  server-sizing/
    SKILL.md
  sit-uat/
    SKILL.md
  tech-design/
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
- 涉及 browser automation 的 skill 当前阶段输出操作 SOP，待神策系统 API 可用后升级为自动化

## v1 Skill 清单

### 1. tracking-setup-e2e — 埋点全链路交付

**触发：** 客户新项目启动、新业务场景需要完整的数据采集和分析能力

**Iron Law：** 必须先完成采集方案设计并经客户确认，再进行后续任何步骤。不允许在方案未确认的情况下造数或创建看板。

**Phases：**
1. 业务目标确认 — 理解分析需求，确定关键指标
2. 采集方案设计 — 输出标准埋点方案表，人工确认
3. 模拟数据生成 — 根据方案造数，覆盖主要业务场景
4. 环境导入与看板创建 — 导入数据，输出看板创建操作 SOP（待 API 可用后升级为自动化）
5. 资产迁移 — 使用神策资产项工具将配置元数据迁移到客户生产环境

**输出：**
- 埋点方案文档（事件名、触发时机、属性列表、示例值）
- 模拟数据文件
- 看板创建操作 SOP
- 资产迁移记录

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

### 3. cdp-operations — CDP 系统操作

**触发：** 需要在神策 CDP 中完成数据分析、数据同步任务、用户管理、事件创建、运营计划创建等操作

**Iron Law：** 操作前必须确认客户的业务目标，不允许按模板照搬配置而不理解业务含义。

**Phases：**
1. 需求确认（明确操作类型和业务目标）
2. 数据源/前置条件检查
3. 通过 browser automation 执行操作
4. 验证结果并截图存档

**输出：** 操作完成确认单（操作项、截图验证结果、注意事项）

**Browser Automation 覆盖范围：**
- 数据分析配置
- 数据同步任务创建
- 用户管理
- 事件创建
- 运营计划创建

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

### 5. sit-uat — SIT/UAT 测试设计与执行

**触发：** 项目上线前需要完成系统集成测试或用户验收测试

**Iron Law：** 必须先完成测试用例设计并确认覆盖范围，再开始执行。不允许跳过用例设计直接测试。

**Phases：**
1. 测试范围确认（业务场景、验收标准）
2. 测试用例设计（用例编号、步骤、预期结果）
3. 执行验证（browser automation 执行，截图记录）
4. 报告输出（通过/失败/阻塞，附截图证据）

**输出：**
- 测试用例文档
- 执行截图集
- 测试报告（通过率、问题清单、上线建议）

---

### 6. tech-design — 技术方案设计

**触发：** 项目启动前需要输出技术方案、客户需要架构评审材料

**Iron Law：** 必须先理解业务约束和技术现状，再输出方案。不允许在不了解客户环境的情况下直接套用标准架构。

**Phases：**
1. 需求与约束收集（业务规模、技术栈、集成要求）
2. 方案设计（架构选型、数据流设计）
3. Diagram 生成（架构图、数据流图，使用 Mermaid/Graphviz）
4. 技术方案文档输出

**输出：**
- 架构图（Mermaid/Graphviz 格式，可渲染）
- 数据流图
- 技术方案文档（背景、方案说明、部署要求、风险点）

---

## Browser Automation 说明

`tracking-setup-e2e`、`cdp-operations`、`sit-uat` 三个 skill 涉及神策系统的 browser automation 操作，依赖 gstack/browse 能力。当前阶段（神策系统无 API）输出操作 SOP 作为兜底；待神策系统 API 可用后，可将 SOP 步骤升级为直接 API 调用，skill 流程结构不变。

## v2 规划（运维工单侧）

以下 skill 因偏运维工单场景，列入 v2：
- `solution-recovery` — 常见技术方案恢复
- `issue-diagnosis` — 问题诊断与根因分析

## 迭代机制

- v1 Startup：6 个核心 skill，完成 SKILL.md 初稿
- v2+：根据交付工程师实际使用反馈扩展 skill 数量和深度
- 每个 skill 独立迭代，不影响其他 skill
- 新 skill 贡献：按统一规范新增目录和 SKILL.md 即可

## 后续步骤

1. 为每个 skill 编写完整的 SKILL.md
2. 编写 README.md skill 索引
3. 在 agent-teams 中部署验证至少一个 skill
4. 收集工程师使用反馈，进入 v2 迭代
