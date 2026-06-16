# sdeliver-skills — 神策数据交付 AI 操作系统

> 从工具箱到操作系统。不只是更快交付，而是更好的交付决策。

**7 个 Plugin，19 Skills，20 Commands，46 Scripts。** 覆盖项目 onboarding、埋点设计、数据管道、基础设施评估、质量保障、交付文档和知识库。

支持 Hermes、OpenCode、Cursor、Claude Code 等主流 Agent 框架。

---

## 我们解决什么问题？

### 交付工程师的日常

> "客户说埋点方案确认了，我开始造数。做到一半客户说方案要改。"  
> "服务器评估做了 3 遍，每次都用不同的公式。"  
> "UAT 测试用例写好了，但开发说逻辑不对，要重来。"  

### 根因：交付是知识密集型工作，但知识没有沉淀

- **Iron Law 藏在某个 SKILL.md 第 80 行** — 新手不知道，老手忘了
- **评估公式口头相传** — 每次都用不同版本
- **工作流没有标准** — 有人先做 SIT 再做 UAT，有人反过来

### sdeliver-skills 的解法

**把交付知识结构化，让 AI 自动加载、自动执行、自动校验。**

不是让 AI 帮你"写文档更快"，而是让 AI 帮你：
- **不犯低级错误**（自动检测配置问题，3 天去重提醒）
- **不遗漏关键步骤**（Command 工作流内置门禁）
- **不重复造轮子**（Skill 知识复用，一处更新全局生效）

---

## 架构：Plugin → Skill → Command

我们采用三层架构，灵感来自 [pm-skills](https://github.com/phuryn/pm-skills)：

```
Plugin（领域）
  ├── Skill（知识）        ← 框架、概念、最佳实践
  │      └── SKILL.md      ← AI 自动加载
  └── Command（工作流）    ← 端到端流程
         └── {cmd}.md      ← 用户触发 /cmd
```

**Skill = 名词 = 知识。**  
如 `server-sizing` Skill 包含：评估公式、决策树、硬件标准、常见问题。

**Command = 动词 = 动作。**  
如 `/size-server` Command 执行：信息收集 → 运行计算器 → 生成 Excel → 输出方案。

**为什么分离？**

```
用户问："服务器怎么评估？"
→ AI 自动加载 server-sizing Skill
→ 给出知识性回答（公式、表格、决策树）

用户说："评估一下这个项目的服务器"
→ 用户触发 /size-server Command
→ AI 执行工作流（收集信息→计算→输出）
```

同一份知识，两种使用方式。

---

## 安装

### 方式一：Git 克隆（推荐）

```bash
git clone https://github.com/sensorsdata/sd-deliver-skills.git ~/sd-deliver-skills
cd ~/sd-deliver-skills
./setup
```

### 方式二：npx 安装（无需克隆）

```bash
npx @sensorsdata/sd-deliver-skills setup --host opencode
```

### 方式三：npm 全局安装

```bash
npm install -g @sensorsdata/sd-deliver-skills
sd-deliver-setup --host all
```

### 安装选项

**指定框架：**

```bash
./setup --host claude    # 只安装到 Claude Code
./setup --host opencode  # 只安装到 OpenCode
./setup --host all       # 安装到所有框架
```

**包含草稿 Skill：**

默认跳过标记为 `status: draft` 或 `status: deprecated` 的 skill/command：

```bash
./setup --include-draft  # 也安装 draft/deprecated skill
```

**安装位置：**

| Agent | Skills 目录 |
|-------|------------|
| OpenCode | `~/.config/opencode/skills/` |
| Claude Code | `~/.claude/skills/` |

### 配置 PATH（首次安装）

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

---

## 使用方式

### 启动新项目

```bash
sdeliver init <client-name> [project-dir]
```

生成目录结构：

```
~/projects/<client-name>/
├── .env                  ← 填写 CDP 连接信息
├── .gitignore
├── references/           ← 放入 SOW、技术方案等文档
├── PROJECT.md            ← onboard 后自动生成（项目档案）
├── DELIVERY.md           ← 交付进度跟踪
├── CLARIFICATION.md      ← 信息澄清跟踪
├── rules/                ← business_logic.yaml 生成位置
└── mock_data/            ← 模拟数据生成位置
```

### 在 Agent 中使用

安装后，有两种使用方式：**Skills（知识自动加载）** 和 **Commands（工作流触发）**。

**Skills 示例（直接提问，AI 自动匹配知识）：**

> "服务器怎么评估？需要收集哪些信息？"  
> → 自动加载 `server-sizing` Skill，给出公式、决策树、配置表

> "埋点方案有哪些核心设计原则？"  
> → 自动加载 `tracking-plan-design` Skill，给出 Iron Law 和设计流程

> "客户要求信创环境，我们支持哪些国产 CPU？"  
> → 自动加载 `delivery-faq` Skill，给出信创支持清单

> "数据导入报 10005 错误是什么意思？"  
> → 自动加载 `metadata-import` Skill，给出错误码说明和解决方案

**Commands 示例（触发端到端工作流）：**

> 入门：
> ```
> /status                             查看项目状态
> /onboard                            初始化项目档案
> ```

> 埋点交付：
> ```
> /design-tracking                    设计埋点方案
> /setup-tracking                     执行埋点全链路（造数→导入→校验）
> ```

> 基础设施：
> ```
> /size-server                        评估服务器
> /design-tech                        输出技术方案
> /draw-arch                          生成架构图
> ```

> 质量保障：
> ```
> /run-sit                            执行 SIT 测试
> /run-uat                            执行 UAT 验收
> ```

> 知识查询：
> ```
> /ask-faq 服务器怎么评估？            问知识库
> ```

---

## Plugin 清单

### 1. sd-core — 交付核心框架

**必备 Plugin。** 项目 onboarding、状态感知、Skill 调度、自动反馈。

| Skill | 说明 |
|-------|------|
| `skill-dispatch` | Skill 调度逻辑：根据用户意图匹配最佳 Skill |
| `project-onboarding` | 项目初始化知识：文档读取、档案生成、澄清跟踪 |
| `delivery-progress` | 交付进度跟踪：里程碑对齐、状态更新、逾期提醒 |

| Command | 说明 |
|---------|------|
| `/onboard` | 读取 references/ 文档，生成 PROJECT.md、CLARIFICATION.md、DELIVERY.md |
| `/status` | 查看项目状态 + 自动诊断（检测配置问题、逾期项等） |

**使用示例：**

Skills:
- "帮我看看这个项目做到哪一步了？" → `/status`
- "读取 references/ 里的文档，生成项目档案" → `/onboard`
- "埋点方案已经确认了，接下来该做什么？" → 自动加载 `skill-dispatch`

Commands:
- `/onboard westk` — 读取 westk 项目文档，生成三份档案
- `/status` — 查看项目健康度和交付进度

---

### 2. sd-tracking-design — 埋点方案设计

从业务目标到埋点方案 Excel 的全流程设计。

| Skill | 说明 |
|-------|------|
| `tracking-plan-design` | 埋点方案设计知识：事件定义、属性设计、触发时机 |
| `business-scoping` | 业务范围确认：目标、场景、分析维度 |

| Command | 说明 |
|---------|------|
| `/design-tracking` | 业务目标确认 → 采集方案设计 → 输出 Excel（Events/Details/Users） |

**使用示例：**

Skills:
- "埋点方案的核心设计原则是什么？" → 自动加载 `tracking-plan-design`
- "你们怎么定义事件的？有什么规范？" → 自动加载 `tracking-plan-design`

Commands:
- `/design-tracking` — 从零开始设计一个埋点方案
- `/design-tracking 我们有个积分商城的业务场景` — 指定场景快速设计

---

### 3. sd-tracking-pipeline — 数据管道执行

从埋点方案到模拟数据、元数据导入、数据导入、结果校验的全链路自动化。

| Skill | 说明 |
|-------|------|
| `data-pipeline` | 数据管道全流程知识：YAML 规范、造数逻辑、导入流程 |
| `mock-data` | 模拟数据知识：数据规模、业务规则、验证方法 |
| `metadata-import` | 元数据导入知识：API 说明、错误码、重试策略 |
| `data-import` | 数据导入知识：BatchConsumer、导入后校验、落库排查 |

| Command | 说明 |
|---------|------|
| `/setup-tracking` | 方案确认 → YAML 生成 → 验证 → 造数 → 校验 → 导入（全自动工作流） |
| `/generate-mock-data` | 仅生成模拟数据 |
| `/validate-mock-data` | 仅对生成的 JSONL 做导入前校验 |
| `/import-mock-data` | 元数据导入 + 数据导入 + 导入后校验 |
| `/validate-data` | 数据校验：对比埋点方案与实际数据，输出差异报告 |

**使用示例：**

Skills:
- "数据导入报错了，怎么回事？" → 自动加载 `data-pipeline` / `metadata-import`
- "造数一般用多大的数据量？" → 自动加载 `mock-data`

Commands:
- `/setup-tracking` — 从确认好的埋点方案开始，走完全链路
- `/generate-mock-data` — 仅生成模拟数据
- `/validate-mock-data` — 仅做导入前校验
- `/import-mock-data` — 仅导入已校验的数据
- `方案已确认，帮我造500个用户的模拟数据` → `/setup-tracking`

---

### 4. sd-infra — 基础设施与技术方案

服务器评估、技术方案设计、架构图绘制、性能测试。

| Skill | 说明 |
|-------|------|
| `server-sizing` | 服务器评估知识：CDP/MA 档位、配置表、扩容路径 |
| `tech-design` | 技术方案知识：LLD 结构、Tech Spec 分工、合规要求 |
| `architecture-diagram` | 架构图知识：draw.io 模板、图层规范、标注标准 |
| `performance-testing` | 性能测试知识：测试策略、指标、报告模板 |

| Command | 说明 |
|---------|------|
| `/size-server` | 信息收集 → 运行计算器 → 生成 Excel → 输出方案 |
| `/design-tech` | 信息收集 → LLD 框架 → 架构图 → Tech Spec |
| `/draw-arch` | 读取配置 → 生成 draw.io → 审核调整 |
| `/run-perf-test` | 设计测试方案 → 执行压测 → 输出报告 |

**使用示例：**

Skills:
- "CDP 单机、Mini 集群、标准集群有什么区别？" → 自动加载 `server-sizing`
- "LLD 和 Tech Spec 有什么区别？" → 自动加载 `tech-design`

Commands:
- `/size-server` — 收集日活和事件量，输出配置方案
- `/design-tech` — 输出整套 LLD + Tech Spec
- `/draw-arch` — 从需求描述生成架构图

---

### 5. sd-quality — 质量保障

SIT、UAT、数据验证。

| Skill | 说明 |
|-------|------|
| `sit-testing` | SIT 测试知识：范围确认、用例设计、执行规范 |
| `uat-testing` | UAT 测试知识：验收标准、测试账号、缺陷管理 |
| `data-validation` | 数据校验知识：校验维度、比对方法、差异分析 |

| Command | 说明 |
|---------|------|
| `/run-sit` | 范围确认 → 用例执行 → 报告 |
| `/run-uat` | 验收确认 → 用例执行 → 缺陷跟踪 → 上线建议 |
| `/sd-design-sit-cases` | 从 Tracking Plan 自动生成 SIT Test Case Excel 初稿 |
| `/sd-design-uat-cases` | 从 Tracking Plan 自动生成 UAT Test Case Excel 初稿 |

**使用示例：**

Skills:
- "SIT 测试应该覆盖哪些场景？" → 自动加载 `sit-testing`
- "UAT 和 SIT 有什么区别？" → 自动加载 `uat-testing` / `sit-testing`

Commands:
- `/run-sit` — 设计用例并执行系统集成测试
- `/run-uat` — 配合客户执行验收测试

---

### 6. sd-docs — 交付文档

文档格式化与生成。

| Skill | 说明 |
|-------|------|
| `doc-formatting` | 文档格式化知识：Word/PDF 生成、样式规范、交付标准 |

| Command | 说明 |
|---------|------|
| `/format-doc` | 读取 Markdown → 生成专业格式文档 |

**使用示例：**

Commands:
- `/format-doc` — 将 Markdown 转为 Word/PDF 交付文档

---

### 7. sd-knowledge — 交付知识库

售前和交付常见问题、评估方法、设计规范、排查 SOP。

| Skill | 说明 |
|-------|------|
| `delivery-faq` | 交付 FAQ：容量评估、带宽计算、信创支持、ID3 规范、排查 SOP |

| Command | 说明 |
|---------|------|
| `/ask-faq` | 问答式知识检索 |

**使用示例：**

Skills:
- "信创环境支持哪些国产操作系统？" → 自动加载 `delivery-faq`
- "数据延迟高怎么排查？" → 自动加载 `delivery-faq`

Commands:
- `/ask-faq 服务器怎么评估？` — 直接问知识库
- `/ask-faq 4 台服务器够不够用？` — 容量评估咨询

---

## 自动反馈机制

每个 Command 执行时自动运行诊断，检测项目问题并静默记录：

| 检测项 | 触发条件 | 严重度 |
|--------|----------|--------|
| `tracking-plan-not-found` | TRACKING_PLAN_PATH 配置但文件不存在 | high |
| `sa-host-unreachable` | SA_HOST 无法连通（3 秒超时） | medium |
| `stale-business-logic` | business_logic.yaml 超过 30 天未更新 | low |
| `stale-delivery` | DELIVERY.md 超过 14 天未更新 | low |
| `empty-references` | PROJECT.md 存在但 references/ 为空 | low |
| `unvalidated-mock-data` | 有模拟数据但无验证报告 | medium |
| `missing-api-key` | 有数据但 API_KEY 未配置 | medium |
| `outdated-yaml` | YAML 验证通过后 7 天未造数 | low |

**去重机制：** 同一问题 3 天内只记录一次。

**手动反馈：** 随时使用 `/sd-feedback <描述>` 记录改进建议。

---

## 设计原则

### Iron Law（铁律）

**必须先完成采集方案设计并经客户确认，再进行后续任何步骤。**

不允许在方案未确认的情况下造数或创建看板。违反此原则会导致返工。

### 完成状态协议

每次工作流结束时报告：
- **DONE** — 完成，已提供依据
- **DONE_WITH_CONCERNS** — 完成，但有需关注的问题（逐条列出）
- **BLOCKED** — 无法继续，说明原因和已尝试的方法
- **NEEDS_CONTEXT** — 缺少必要信息，说明具体需要什么

### 知识复用

- Skill 是知识单元，可被多个 Command 复用
- 一处更新，全局生效
- 通过 `shared/` 目录共享跨 Plugin 工具函数

---

## 依赖

- Python 3.10+
- `pip install openpyxl python-dotenv requests sensorsanalytics`

---

## 贡献

### 新增 Skill

1. 在对应 Plugin 的 `skills/` 下新建目录
2. 编写 `SKILL.md`（必须包含 `name:` frontmatter，目录名等于 name）
3. 运行 `python3 validate_plugins.py` 验证
4. 更新 README.md Plugin 清单
5. 提交 PR

### 新增 Command

1. 在对应 Plugin 的 `commands/` 下新建 `{cmd}.md`
2. frontmatter 包含 `description` + `argument-hint`
3. 描述工作流步骤，引用同 Plugin 的 Skills
4. 完成时建议下一步（自然语言，不硬引用其他 Plugin）
5. 运行 `python3 validate_plugins.py` 验证

---

## License

MIT — 见 [LICENSE](LICENSE)。

---

## 关于

sd-deliver-skills 是神策数据交付团队的 AI 技能市场。  
基于 [pm-skills](https://github.com/phuryn/pm-skills) 架构模式设计。

**维护：** SensorsData Delivery Team  
**问题反馈：** [GitHub Issues](https://github.com/sensorsdata/sd-deliver-skills/issues)
