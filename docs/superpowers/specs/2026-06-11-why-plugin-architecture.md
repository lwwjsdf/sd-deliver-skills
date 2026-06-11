# 为什么需要 Plugin-Skill-Command 架构？

**tl;dr**: 当前的 sdeliver-skills 是**工具箱**，pm-skills 模式让它成为**操作系统**。

---

## 1. 我们当前的困境

### 现状：14 个 SKILL.md 平铺

```
tracking-setup-e2e/SKILL.md    ← 391 行：既教知识又走流程
server-sizing/SKILL.md         ← 661 行：既讲公式又做计算
tech-design/SKILL.md           ← 467 行：既讲架构又写文档
...
```

每个 SKILL.md 都是一个**巨型单体文件**：
- 前半部分讲"这是什么"
- 后半部分讲"怎么做"
- 中间还夹着一堆脚本调用

### 问题 1：AI 加载成本

当你调用 `/sdeliver` 时，AI 加载 `SKILL.md`。如果这是一个 400 行的文件，AI 需要：
- 解析 frontmatter
- 读取所有 Iron Law、前置条件、Phase 定义、脚本路径、常见问题...
- 即使只是想"看看项目状态"，也加载了"如何导入元数据"的全部细节

**结果**：token 浪费，上下文膨胀。

### 问题 2：知识无法复用

`tracking-setup-e2e/SKILL.md` 里有一段"数据导入的 5 种错误处理"，这段知识：
- 不能被 `data-validation` 引用
- 不能被 UAT 测试引用
- 只能复制粘贴

**结果**：知识碎片化，维护困难。

### 问题 3：工作流僵化

SKILL.md 里写死了 Phase 1→2→3→4→5。用户说"我直接造数"，AI 还是得从头读一遍 Iron Law 和前置条件。

**结果**：无法快速入口，无法灵活组合。

---

## 2. pm-skills 的洞察

Paweł Huryn（pm-skills 作者）是 PM 领域的专家，他把 PM 工作流抽象为三层：

### 三层架构

```
Plugin（领域）
  └── Skill（知识/框架）
        └── Command（工作流）
```

**类比：**
- **Plugin = 医院科室**（心内科、骨科、儿科）
- **Skill = 医学知识**（心脏解剖学、心电图判读、手术指征）
- **Command = 诊疗流程**（接诊→检查→诊断→治疗→随访）

### 关键洞察 1：Skill ≠ Command

**Skill 是"名词"** — 知识、框架、概念。
- `brainstorm-ideas`：如何脑暴创意
- `identify-assumptions`：如何识别假设
- `server-sizing`：如何评估服务器

**Command 是"动词"** — 动作、流程、剧本。
- `/discover`：端到端发现流程（串联 brainstorm → identify → prioritize → experiment）
- `/size-server`：评估服务器流程（串联 info-gather → calc → output）

**为什么分离？**

```
场景 A：用户问"服务器怎么评估？"
→ AI 自动加载 skill "server-sizing"
→ 给出知识性回答（公式、表格、决策树）

场景 B：用户说"评估一下这个项目的服务器"
→ 用户触发 command "/size-server"
→ AI 执行工作流（收集信息→运行计算器→输出方案）
```

同一份知识，两种使用方式。Skill 被复用，Command 被触发。

### 关键洞察 2：Plugin 是边界

**Plugin 内**可以硬引用：
- `/discover` Command 可以直接说"Apply brainstorm-ideas skill"
- 因为它们是同一个 Plugin，一起安装，一起卸载

**Plugin 间**不能硬引用：
- `/discover` 不能说"然后调用 /size-server"
- 因为用户可能没装 sd-infra Plugin

**替代方案：** 自然语言建议
```
"完成发现后，你可能需要评估服务器资源。可以说 '帮我评估服务器'。"
```

**为什么这样设计？**
- 插件可独立安装（按需加载，减少上下文）
- 避免引用断裂（移动文件不会破坏其他 Plugin）
- 鼓励松耦合（Plugin 之间通过项目目录和约定协作）

### 关键洞察 3：Progressive Disclosure（渐进式披露）

```
Skill 加载过程：

1. 匹配阶段：只读 frontmatter（name + description）
   → AI 判断"这个话题是否需要加载这个 skill"
   → 消耗 50 tokens

2. 加载阶段：读取 SKILL.md body
   → AI 获取完整知识
   → 消耗 500-2000 tokens

3. 执行阶段：用户触发 Command
   → AI 读取 Command.md
   → 执行具体工作流
   → 消耗 1000-3000 tokens
```

**对比当前：**
- 当前：调用 `/sdeliver` → 加载 400 行 SKILL.md → 即使只查状态也消耗 2000 tokens
- 新架构：调用 `/status` → 加载 50 行 Command.md → 消耗 200 tokens

### 关键洞察 4：框架无关

pm-skills 的 `skills/{skill}/SKILL.md` 可以在任何 agent 框架使用：
- Claude Code：通过 `.claude-plugin/marketplace.json` 安装
- Cursor：复制到 `.cursor/skills/`
- OpenCode：复制到 `.opencode/skills/`
- Gemini CLI：复制到 `.gemini/skills/`

Commands（`/` 触发）是 Claude 特有的，但 Skills 是通用的。

**这意味着：** 我们沉淀的交付知识可以被任何 AI 工具使用。

---

## 3. 这种设计是最佳实践吗？

### 为什么说是

1. **符合软件工程原则**
   - 单一职责：Skill 只做知识沉淀，Command 只做流程编排
   - 开闭原则：新增 Skill 不影响现有 Command，新增 Command 可以复用现有 Skill
   - 依赖倒置：Command 依赖 Skill 接口，不依赖具体实现

2. **符合 AI 交互模式**
   - 知识自动加载（Skill）：AI 在对话中自动匹配相关知识
   - 流程显式触发（Command）：用户明确要做什么，AI 执行

3. **符合交付场景**
   - 咨询场景："服务器怎么评估？" → Skill 自动加载
   - 执行场景："评估这个项目" → Command 触发工作流

### 局限性

1. **Claude 生态绑定**：Command（`/` 触发）是 Claude 特有的，其他框架需要适配
2. **学习成本**：开发者需要理解三层结构
3. **维护成本**：一个功能改动可能涉及 Skill + Command + Script 三个文件

### 结论

对于**有明确领域知识、有标准化工作流、需要多场景复用**的项目（如交付技能），这种设计是最佳实践。

对于**一次性脚本、简单工具**，这种设计是过度工程。

sd-deliver-skills 属于前者。

---

## 4. 对我们意味着什么？

### 从"工具箱"到"操作系统"

**当前：**
```
用户："帮我做埋点"
AI：打开 tracking-setup-e2e/SKILL.md（391 行）
     → 读取所有知识
     → 读取所有流程
     → 执行
```

**重构后：**
```
用户："帮我做埋点"
AI：1. 自动加载 skill "tracking-plan-design"（知识：什么是埋点方案）
   2. 用户触发 command "/design-tracking"（工作流：设计埋点方案）
   3. 完成后建议："需要生成数据？可以用 /generate-mock"
   4. 用户触发 command "/setup-tracking"（工作流：全链路交付）
   5. 执行中自动加载 skill "data-pipeline"（知识：数据导入细节）
```

### 具体收益

| 维度 | 当前 | 重构后 |
|------|------|--------|
| **加载速度** | 400 行 SKILL.md → 2000 tokens | 50 行 frontmatter → 100 tokens |
| **知识复用** | 复制粘贴 | Skill 被多个 Command 引用 |
| **灵活组合** | 固定 Phase 1→2→3 | Command 可以跳过、重排、组合 |
| **按需安装** | 全部安装 | 只装需要的 Plugin |
| **框架兼容** | 仅 Claude | Claude + Cursor + OpenCode + ... |
| **团队协作** | 一人维护一个巨大文件 | 多人分领域维护独立 Plugin |

---

## 5. 新架构的具体例子

### 场景：客户新项目启动

**当前交互：**
```
用户：/sdeliver
AI：加载 sdeliver/SKILL.md（393 行）
     输出：项目状态、可用 skill 列表
     
用户：/sd-tracking-setup-e2e
AI：加载 tracking-setup-e2e/SKILL.md（391 行）
     输出：全链路流程
     执行：Phase 1→2→3→4→5
```

**重构后交互：**
```
用户：/status
AI：加载 sd-core/commands/status.md（50 行）
     输出：项目状态 + 自动诊断结果
     
用户：帮我设计埋点方案
AI：自动加载 sd-tracking-design/skills/tracking-plan-design/SKILL.md
     输出：埋点方案知识
     
用户：/design-tracking
AI：加载 sd-tracking-design/commands/design-tracking.md
     执行：信息收集 → 方案设计 → 输出 Excel
     建议："方案已确认？可以用 /setup-tracking 执行数据导入"
     
用户：/setup-tracking
AI：加载 sd-tracking-pipeline/commands/setup-tracking.md
     执行：YAML 生成 → 验证 → 造数 → 导入 → 校验
     过程中自动加载 skills：
       - data-pipeline（数据导入知识）
       - mock-data（模拟数据知识）
       - metadata-import（元数据导入知识）
```

**差异：**
- 用户只在需要时加载对应知识
- 每个 Command 文件很小（50-100 行），只描述工作流
- Skills 可以被复用（如 "数据导入知识" 同时被 setup-tracking 和 validate-data 引用）
- AI 上下文更聚焦，不容易走偏

---

## 6. 术语表

| 术语 | 定义 | 类比 |
|------|------|------|
| **Plugin** | 可独立安装的功能域 | 医院科室 |
| **Skill** | 知识单元（框架、概念、最佳实践） | 医学知识 |
| **Command** | 工作流（端到端流程，串联 Skills） | 诊疗流程 |
| **Marketplace** | Plugin 集合（市场清单） | 医院科室列表 |
| **Frontmatter** | 文件头部元数据（YAML） | 药品说明书标签 |
| **Progressive Disclosure** | 渐进式加载（先轻后重） | 分级诊疗 |

---

## 7. 关键设计决策

### 决策 1：为什么 Skill 目录名必须等于 name？

**原因：** Agent 框架通过目录名发现 Skill。如果 `skills/server-sizing/` 里的 name 是 `sd-server-sizing`，框架无法匹配。

**例外：** Plugin 名带前缀（`sd-`），但 Skill 名不带。因为 Skill 是知识，不是产品名。

### 决策 2：为什么 Command 用 `.md` 而不是 `.md` + `.json`？

**原因：** Command 本质是一份给 AI 的"剧本"，用 Markdown 更自然。frontmatter 只存 description 和 argument-hint，足够简洁。

### 决策 3：为什么 Scripts 放在 Plugin 下而不是全局？

**原因：** Scripts 是 Command 的实现细节，与 Plugin 绑定。`shared/` 放跨 Plugin 的工具函数。

### 决策 4：为什么 Feedback 不做成独立 Skill？

**原因：** Feedback 是框架级能力，不是业务知识。合并入 sd-core 的 auto-feedback 机制。
