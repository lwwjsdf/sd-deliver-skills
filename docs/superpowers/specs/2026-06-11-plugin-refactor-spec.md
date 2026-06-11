# SDELIVER-SKILLS Plugin 架构重构 SPEC

**版本:** v1.0.0-draft  
**日期:** 2026-06-11  
**作者:** AI Agent (基于 pm-skills 模式适配)  
**状态:** 待评审

---

## 1. 设计目标

### 1.1 当前痛点

| 痛点 | 影响 | 根因 |
|------|------|------|
| Skill/Command 未分离 | 一个 SKILL.md 既教知识又走流程，AI 加载时消耗不必要 token | 扁平结构，无层级设计 |
| 无 Plugin 分组 | 14 个 skill 平铺，无法按需安装，新增 skill 时目录爆炸 | 缺乏领域分组 |
| 无声明式配置 | 没有 plugin.json，框架无法自动发现 skill 能力 | 元数据缺失 |
| Skill 间强耦合 | 硬编码引用其他 skill 路径，移动文件即断裂 | 无接口抽象 |
| 无验证器 | 新增 skill 容易 frontmatter 格式错误 | 缺乏 CI 检查 |
| Preamble 代码重复 | 7 个 SKILL.md 重复相同的环境检测逻辑 | 无共享机制 |

### 1.2 目标架构原则（借鉴 pm-skills）

- **Plugin = 可独立安装的功能域**（如埋点、基础设施、质量保障）
- **Skill = 知识单元（名词）** — 框架性知识，AI 自动匹配加载
- **Command = 工作流（动词）** — 用户触发 `/cmd`，串联同 Plugin 的 Skills
- **Progressive Disclosure** — frontmatter 精简（始终加载），body 详细（触发时加载）
- **Intra-plugin 引用 OK，Cross-plugin 不硬引用** — 通过自然语言建议下一步

---

## 2. 目标架构

### 2.1 目录结构

```
sd-deliver-skills/
├── AGENTS.md                          ← Agent 指导（single source of truth）
├── CLAUDE.md                          ← 指向 AGENTS.md（Claude 兼容）
├── validate_plugins.py                ← 结构验证器（检查 frontmatter、目录名匹配等）
├── README.md                          ← 公开文档（GitHub）
├── setup                              ← 安装脚本（安装所有 plugin 到 agent 框架）
│
├── sd-core/                           ← Plugin: 交付核心框架
│   ├── plugin.json                      ← 插件元数据
│   ├── skills/
│   │   ├── project-onboarding/        ← Skill: 项目初始化知识
│   │   │   └── SKILL.md
│   │   ├── delivery-progress/         ← Skill: 交付进度跟踪知识
│   │   │   └── SKILL.md
│   │   └── skill-dispatch/            ← Skill: Skill 调度逻辑
│   │       └── SKILL.md
│   ├── commands/
│   │   ├── onboard.md                 ← Command: /onboard
│   │   └── status.md                  ← Command: /status
│   └── scripts/
│       ├── sdeliver                   ← CLI 入口
│       ├── sdeliver-config            ← 配置管理
│       ├── sdeliver-auto-feedback     ← 自动诊断
│       └── sdeliver-sync-hermes       ← Hermes 同步
│
├── sd-tracking-design/                ← Plugin: 埋点方案设计
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   ├── tracking-plan-design/      ← Skill: 埋点方案设计知识（原 tracking-design）
│   │   │   └── SKILL.md
│   │   └── business-scoping/          ← Skill: 业务范围确认知识
│   │       └── SKILL.md
│   ├── commands/
│   │   └── design-tracking.md         ← Command: /design-tracking
│   └── scripts/
│       └── ...（tracking-design 相关脚本）
│
├── sd-tracking-pipeline/              ← Plugin: 数据管道执行
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   ├── data-pipeline/             ← Skill: 数据管道全流程知识（原 tracking-setup-e2e 知识部分）
│   │   │   └── SKILL.md
│   │   ├── mock-data/                 ← Skill: 模拟数据生成知识
│   │   │   └── SKILL.md
│   │   └── metadata-import/           ← Skill: 元数据导入知识
│   │       └── SKILL.md
│   ├── commands/
│   │   ├── setup-tracking.md          ← Command: /setup-tracking（E2E 工作流）
│   │   └── validate-data.md           ← Command: /validate-data
│   └── scripts/
│       ├── tracking_plan.py
│       ├── yaml_validator.py
│       ├── generate_mock_data.py
│       ├── import_meta_data.py
│       ├── import_mock_data.py
│       ├── check_metadata.py
│       ├── validate_import.py
│       ├── list_enum_values.py
│       ├── event_sequencer.py
│       ├── rule_engine.py
│       ├── constraint_validator.py
│       ├── fixed_account_generator.py
│       ├── config_helper.py
│       ├── mp_preset_builder.py
│       ├── report_generator.py
│       ├── crawl_web_pages.py
│       └── docx_to_yaml_skeleton.py
│
├── sd-infra/                          ← Plugin: 基础设施与技术方案
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   ├── server-sizing/             ← Skill: 服务器评估知识（原 server-sizing 知识部分）
│   │   │   └── SKILL.md
│   │   ├── tech-design/               ← Skill: 技术方案设计知识（原 tech-design 知识部分）
│   │   │   └── SKILL.md
│   │   ├── architecture-diagram/      ← Skill: 架构图绘制知识（原 draw-diagram 知识部分）
│   │   │   └── SKILL.md
│   │   └── performance-testing/       ← Skill: 性能测试知识（原 performance-test）
│   │       └── SKILL.md
│   ├── commands/
│   │   ├── size-server.md             ← Command: /size-server
│   │   ├── design-tech.md             ← Command: /design-tech
│   │   ├── draw-arch.md               ← Command: /draw-arch
│   │   └── run-perf-test.md           ← Command: /run-perf-test
│   └── scripts/
│       ├── sizing_calc.py
│       ├── gen_excel.py
│       └── ...（draw-diagram, performance-test 脚本）
│
├── sd-quality/                        ← Plugin: 质量保障
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   ├── sit-testing/               ← Skill: SIT 测试知识（原 sit-uat 知识部分）
│   │   │   └── SKILL.md
│   │   ├── uat-testing/               ← Skill: UAT 测试知识（原 sd-uat）
│   │   │   └── SKILL.md
│   │   └── data-validation/           ← Skill: 数据校验知识（原 data-validation）
│   │       └── SKILL.md
│   ├── commands/
│   │   ├── run-sit.md                 ← Command: /run-sit
│   │   └── run-uat.md                 ← Command: /run-uat
│   └── scripts/
│       └── ...（data-validation, sit-uat 脚本）
│
├── sd-docs/                           ← Plugin: 交付文档
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   └── doc-formatting/            ← Skill: 文档格式化知识（原 business-doc-formatting）
│   │       └── SKILL.md
│   ├── commands/
│   │   └── format-doc.md              ← Command: /format-doc
│   └── scripts/
│       └── generate_business_doc.py
│
├── sd-knowledge/                      ← Plugin: 交付知识库
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   └── delivery-faq/              ← Skill: 交付 FAQ 知识（原 faq）
│   │       └── SKILL.md
│   └── commands/
│       └── ask-faq.md                 ← Command: /ask-faq
│
└── shared/                            ← 跨 Plugin 共享模块（保留）
    ├── cdp_client.py
    ├── md2docx.py
    ├── read_doc.py
    └── ...
```

### 2.2 Plugin 分组逻辑

| Plugin | 覆盖域 | 原 Skill | 安装建议 |
|--------|--------|----------|----------|
| **sd-core** | 项目框架 | sdeliver, feedback | **必选** |
| **sd-tracking-design** | 埋点方案设计 | tracking-design | 埋点项目必选 |
| **sd-tracking-pipeline** | 数据管道执行 | tracking-setup-e2e, data-validation | 埋点项目必选 |
| **sd-infra** | 基础设施 | server-sizing, tech-design, draw-diagram, performance-test | 私有化部署必选 |
| **sd-quality** | 质量保障 | sit-uat, sd-uat | 上线前必选 |
| **sd-docs** | 文档工具 | business-doc-formatting | 按需 |
| **sd-knowledge** | 知识库 | faq | 建议安装 |

---

## 3. 详细迁移映射

### 3.1 文件迁移表

| 源文件 | 目标路径 | 迁移策略 |
|--------|----------|----------|
| `SKILL.md` | `sd-core/skills/skill-dispatch/SKILL.md` | **拆分** — 提取调度逻辑为 Skill，onboard/status 工作流拆为 Command |
| `tracking-design/SKILL.md` | `sd-tracking-design/skills/tracking-plan-design/SKILL.md` + `sd-tracking-design/commands/design-tracking.md` | **拆分** — 提取知识为 Skill，设计工作流拆为 Command |
| `tracking-setup-e2e/SKILL.md` | `sd-tracking-pipeline/skills/data-pipeline/SKILL.md` + `sd-tracking-pipeline/commands/setup-tracking.md` | **拆分** — Phase 1-2 知识进 Skill，Phase 3-5 工作流进 Command |
| `tracking-setup-e2e/scripts/*` | `sd-tracking-pipeline/scripts/*` | **移动** — 保持文件名不变 |
| `tracking-setup-e2e/rules/*` | `sd-tracking-pipeline/rules/*` | **移动** |
| `tracking-setup-e2e/docs/*` | `sd-tracking-pipeline/docs/*` | **移动** |
| `data-validation/SKILL.md` | `sd-quality/skills/data-validation/SKILL.md` | **拆分** |
| `server-sizing/SKILL.md` | `sd-infra/skills/server-sizing/SKILL.md` + `sd-infra/commands/size-server.md` | **拆分** |
| `server-sizing/*.py` | `sd-infra/scripts/*.py` | **移动** |
| `tech-design/SKILL.md` | `sd-infra/skills/tech-design/SKILL.md` + `sd-infra/commands/design-tech.md` | **拆分** |
| `draw-diagram/SKILL.md` | `sd-infra/skills/architecture-diagram/SKILL.md` + `sd-infra/commands/draw-arch.md` | **拆分** |
| `performance-test/SKILL.md` | `sd-infra/skills/performance-testing/SKILL.md` + `sd-infra/commands/run-perf-test.md` | **拆分** |
| `sit-uat/SKILL.md` | `sd-quality/skills/sit-testing/SKILL.md` + `sd-quality/commands/run-sit.md` | **拆分** |
| `sd-uat/SKILL.md` | `sd-quality/skills/uat-testing/SKILL.md` + `sd-quality/commands/run-uat.md` | **拆分** |
| `faq/SKILL.md` | `sd-knowledge/skills/delivery-faq/SKILL.md` + `sd-knowledge/commands/ask-faq.md` | **拆分** |
| `business-doc-formatting/SKILL.md` | `sd-docs/skills/doc-formatting/SKILL.md` + `sd-docs/commands/format-doc.md` | **拆分** |
| `feedback/SKILL.md` | **废弃** — 功能合并入 sd-core auto-feedback | 移除独立 skill |
| `bin/sdeliver*` | `sd-core/scripts/sdeliver*` | **移动** |
| `shared/*` | `shared/*` | **保留** — 跨 Plugin 共享 |
| `refrences/*` | `refrences/*` | **保留** — 全局参考文档 |

### 3.2 SKILL.md → Skill + Command 拆分原则

**原 SKILL.md 内容分类：**

```
原 SKILL.md
├── Frontmatter (name, version, description, allowed-tools)
├── Preamble (环境检测脚本)         → 保留在 Skill frontmatter 或 Command 中
├── 适用场景                        → Skill
├── 核心原则 (Iron Law)             → Skill
├── 前置条件                        → Skill
├── Phase 1: 信息收集               → Command (工作流步骤)
├── Phase 2: 方案设计               → Command (工作流步骤)
├── Phase 3: 执行步骤               → Command (工作流步骤)
├── 输出模板                        → Skill + Command
├── 常见问题                        → Skill
└── Feedback                        → 废弃，由 auto-feedback 替代
```

**Skill 的 SKILL.md 结构：**

```markdown
---
name: data-pipeline
version: 1.0.0
description: |
  神策数据管道全流程知识：从埋点方案解析到模拟数据生成、
  元数据导入、数据导入和结果校验。
  当讨论埋点数据导入、元数据管理、模拟数据生成时自动加载。
allowed-tools:
  - Bash
  - Read
---

## 核心原则

**Iron Law: 必须先完成采集方案设计并经客户确认，再进行后续任何步骤。**

...

## 关键概念

### 数据管道阶段
...

### 脚本依赖关系
...

## 常见问题
...
```

**Command 的 .md 结构：**

```markdown
---
description: 执行埋点全链路交付——从方案解析到数据导入和校验
argument-hint: "<项目目录>"
---

# /setup-tracking — 埋点全链路交付

## 适用场景
...

## 工作流

### Step 1: 确认当前阶段
...

### Step 2: 执行对应 Phase
...

## 输出模板
...

## 完成建议
- "需要验证导入结果？ → /validate-data"
- "需要设计看板？ → ..."
```

---

## 4. 规范定义

### 4.1 Plugin 元数据 (plugin.json)

```json
{
  "name": "sd-tracking",
  "version": "1.0.0",
  "description": "神策埋点采集与数据管道：从方案设计到数据导入和校验的全链路交付能力。",
  "author": {
    "name": "SensorsData Delivery Team",
    "email": "delivery@sensorsdata.cn"
  },
  "keywords": [
    "sensorsdata",
    "tracking",
    "data-pipeline",
    "mock-data",
    "metadata-import"
  ],
  "homepage": "https://github.com/sensorsdata/sd-deliver-skills",
  "license": "MIT"
}
```

### 4.2 Skill 规范

| 字段 | 要求 | 说明 |
|------|------|------|
| `name` | 必填，匹配目录名 | 目录名必须等于 name |
| `version` | 必填，semver | 与所属 plugin 版本一致 |
| `description` | 必填 | 包含触发短语，便于 AI 自动加载 |
| `allowed-tools` | 可选 | 该 skill 需要的工具权限 |

**命名规范：**
- Skill 目录名：`kebab-case`，如 `tracking-plan-design`
- Skill name：与目录名一致
- 描述中包含触发场景关键词

### 4.3 Command 规范

| 字段 | 要求 | 说明 |
|------|------|------|
| `description` | 必填 | 简洁描述命令功能 |
| `argument-hint` | 可选 | 参数提示，如 `"<项目目录>"` |

**命名规范：**
- Command 文件名：`kebab-case.md`，如 `setup-tracking.md`
- 调用方式：`/setup-tracking`
- 一个 Command 可以引用同 Plugin 的多个 Skills
- Command 完成时通过自然语言建议下一步（不硬引用其他 Plugin）

### 4.4 市场清单 (marketplace.json)

```json
{
  "name": "sd-deliver-skills",
  "version": "1.0.0",
  "description": "神策数据交付 Skill 市场：覆盖项目 onboarding、埋点交付、基础设施评估、质量保障和交付知识库。",
  "plugins": [
    "sd-core",
    "sd-tracking",
    "sd-infra",
    "sd-quality",
    "sd-docs",
    "sd-knowledge"
  ]
}
```

---

## 5. 跨 Plugin 协作机制

### 5.1 设计原则

**禁止硬引用。** Command 不能硬编码其他 Plugin 的 Skill/Command 路径。协作通过以下方式：

1. **自然语言建议** — Command 完成时建议："需要评估服务器？可以说 `/size-server`"
2. **共享 shared/ 模块** — 纯工具函数，无业务逻辑
3. **项目目录约定** — 所有 Plugin 读写同一客户项目目录（通过 `.env` 桥接）

### 5.2 数据流

```
客户项目目录 (~/projects/<client>/)
├── .env                        ← 所有 Plugin 读取
├── PROJECT.md                  ← sd-core 生成，所有 Plugin 读取
├── DELIVERY.md                 ← sd-core 生成，所有 Plugin 更新进度
├── CLARIFICATION.md            ← sd-core 生成
├── references/                 ← 客户文档
├── rules/                      ← sd-tracking 生成/读取
├── mock_data/                  ← sd-tracking 生成
└── tech-design/                ← sd-infra 生成
```

### 5.3 Plugin 间依赖声明

在 Command 文档中用注释标注前置条件，但不硬编码：

```markdown
## 前置条件

> 本 Command 假设以下工作已完成：
> - 项目已 onboard（`PROJECT.md` 存在）→ 由 `/onboard` 完成
> - 埋点方案已确认（`rules/business_logic.yaml` 存在）→ 由 `/design-tracking` 完成
> - 如果上述条件不满足，本 Command 会提示用户先执行对应步骤
```

---

## 6. 共享机制

### 6.1 shared/ 目录（跨 Plugin）

保留 `shared/` 作为纯工具函数库，所有 Plugin 的 scripts 都可以 import：

```python
# sd-tracking/scripts/import_meta_data.py
import sys
sys.path.insert(0, '../../../shared')
from cdp_client import CDPClient
```

### 6.2 Preamble 共享脚本

提取统一的 Preamble 逻辑到 `sd-core/scripts/sdeliver-preamble`：

```bash
#!/usr/bin/env bash
# sdeliver-preamble — 统一的环境检测脚本
# 用法: source sdeliver-preamble

sdeliver_preamble() {
  local project_dir="${1:-$(pwd)}"
  # 统一的环境检测逻辑...
}
```

各 Skill/Command 的 Preamble 简化为：

```bash
# 在 SKILL.md 或 Command.md 的 preamble 中
source "$(command -v sdeliver-preamble)"
sdeliver_preamble "$_PROJECT_DIR"
```

---

## 7. 实施计划

### Phase 1: 基础设施（Week 1）

**目标:** 建立新目录结构和验证工具，不迁移业务逻辑

- [ ] 创建 `AGENTS.md`（Agent 指导）
- [ ] 创建 `CLAUDE.md`（指向 AGENTS.md）
- [ ] 创建 `validate_plugins.py`
- [ ] 创建所有 Plugin 的目录骨架（空 plugin.json + 目录）
- [ ] 修改 `setup` 脚本支持 Plugin 级安装
- [ ] **验证:** `python3 validate_plugins.py` 通过

**不修改任何 SKILL.md 内容。**

### Phase 2: 试点迁移 — sd-core（Week 1-2）

**目标:** 迁移入口 skill，验证拆分模式

- [ ] 将 `SKILL.md` → 拆分为 `sd-core/skills/skill-dispatch/SKILL.md`
- [ ] 提取 onboard 工作流 → `sd-core/commands/onboard.md`
- [ ] 提取 status 工作流 → `sd-core/commands/status.md`
- [ ] 移动 `bin/*` → `sd-core/scripts/`
- [ ] 废弃 `feedback/SKILL.md`，功能合并入 auto-feedback
- [ ] **验证:** 在测试项目调用 `/status`，输出正确

### Phase 3: 核心迁移 — sd-tracking-design + sd-tracking-pipeline（Week 2-3）

**目标:** 迁移最复杂的 tracking 体系（拆分为设计 + 执行两个 Plugin）

**sd-tracking-design:**
- [ ] 迁移 `tracking-design/SKILL.md` → `sd-tracking-design/skills/tracking-plan-design/SKILL.md`
- [ ] 提取设计工作流 → `sd-tracking-design/commands/design-tracking.md`
- [ ] 迁移相关 scripts/
- [ ] **验证:** 端到端跑通埋点方案设计

**sd-tracking-pipeline:**
- [ ] 迁移 `tracking-setup-e2e/SKILL.md` → `sd-tracking-pipeline/skills/data-pipeline/SKILL.md`
- [ ] 拆分出 `mock-data` 和 `metadata-import` Skills
- [ ] 提取工作流 → `sd-tracking-pipeline/commands/setup-tracking.md` + `validate-data.md`
- [ ] 迁移所有 scripts/
- [ ] 更新脚本中的相对路径（`../../shared` 等）
- [ ] **验证:** 端到端跑通 setup-tracking

### Phase 4: 剩余迁移（Week 3-4）

**目标:** 迁移其余 5 个 Plugin

- [ ] `sd-infra/` — server-sizing, tech-design, draw-diagram, performance-test
- [ ] `sd-quality/` — sit-uat, sd-uat, data-validation
- [ ] `sd-docs/` — business-doc-formatting
- [ ] `sd-knowledge/` — faq
- [ ] **验证:** 所有 Plugin 通过 validate_plugins.py

### Phase 5: 清理与文档（Week 4）

**目标:** 清理旧文件，更新文档

- [ ] 删除旧目录（保留 git history）
- [ ] 更新 `README.md`
- [ ] 更新 `AGENTS.md` 操作指引
- [ ] 编写迁移指南（给团队其他成员）
- [ ] **验证:** `./setup` 全新安装后，所有 Command 可用

---

## 8. 验证方案

### 8.1 validate_plugins.py 检查项

```python
# 伪代码
def validate_plugin(plugin_dir):
    assert exists(f"{plugin_dir}/plugin.json")
    assert plugin_json_has_fields(["name", "version", "description"])
    
    for skill_dir in plugin_dir/skills/*:
        assert exists(f"{skill_dir}/SKILL.md")
        assert skill_frontmatter_has(["name", "description"])
        assert basename(skill_dir) == skill_frontmatter.name
    
    for cmd_file in plugin_dir/commands/*.md:
        assert cmd_frontmatter_has(["description"])
    
    # 检查 cross-plugin 硬引用
    for cmd_file in plugin_dir/commands/*.md:
        content = read(cmd_file)
        assert not contains_hard_ref_to_other_plugin(content)

def validate_marketplace():
    assert marketplace_json_lists_all_plugins()
    assert all_plugin_versions_match_marketplace()
```

### 8.2 集成测试清单

| 测试项 | 命令 | 期望结果 |
|--------|------|----------|
| 安装验证 | `./setup` | 所有 Plugin 注册到 agent 框架的 skills 目录 |
| Skill 加载 | `/skill-dispatch` | 正确加载，显示项目状态 |
| Command 执行 | `/onboard test-client` | 生成 PROJECT.md |
| 自动诊断 | `/status` | 检测到未配置项并记录 feedback |
| Tracking 流程 | `/design-tracking` → `/setup-tracking` | 完成埋点设计和数据导入 |
| Infra 流程 | `/size-server` | 输出配置方案 |

---

## 9. 风险与回滚

### 9.1 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 迁移期间新旧结构并存导致混乱 | 高 | 中 | Phase 1-4 保留旧目录，Phase 5 才删除；setup 脚本支持新旧双模式 |
| 脚本路径变更导致执行失败 | 中 | 高 | 所有脚本路径统一从 `sd-*/scripts/` 计算；添加兼容性 shim |
| Skill 拆分后 AI 加载行为变化 | 中 | 中 | 渐进迁移，先试点 sd-core；保留旧 SKILL.md 作为 fallback |
| Hermes 框架不支持 Plugin 模式 | 低 | 高 | 验证 setup 脚本在 Hermes 的行为；如不支持，fallback 到扁平 skill 模式 |

### 9.2 回滚方案

**如果发现严重问题，可快速回滚到旧结构：**

1. `git checkout main -- tracking-setup-e2e/ server-sizing/ ...` 恢复旧目录
2. `git checkout main -- setup` 恢复旧安装脚本
3. 删除新 Plugin 目录
4. 重新运行 `./setup`

**保留旧目录直到 Phase 5 完成。**

---

## 10. 附录

### 10.1 命名对照表

| 旧名称 | 新 Plugin | 新 Skill/Command |
|--------|-----------|------------------|
| sdeliver | sd-core | skill-dispatch / onboard, status |
| tracking-design | sd-tracking-design | tracking-plan-design / design-tracking |
| tracking-setup-e2e | sd-tracking-pipeline | data-pipeline, mock-data, metadata-import / setup-tracking, validate-data |
| data-validation | sd-quality | data-validation / validate-data |
| server-sizing | sd-infra | server-sizing / size-server |
| tech-design | sd-infra | tech-design / design-tech |
| draw-diagram | sd-infra | architecture-diagram / draw-arch |
| performance-test | sd-infra | performance-testing / run-perf-test |
| sit-uat | sd-quality | sit-testing / run-sit |
| sd-uat | sd-quality | uat-testing / run-uat |
| faq | sd-knowledge | delivery-faq / ask-faq |
| business-doc-formatting | sd-docs | doc-formatting / format-doc |
| feedback | — | 合并入 sd-core auto-feedback |

### 10.2 参考

- [pm-skills CLAUDE.md](https://github.com/phuryn/pm-skills/blob/main/CLAUDE.md)
- [pm-skills plugin.json 示例](https://github.com/phuryn/pm-skills/blob/main/pm-product-discovery/.claude-plugin/plugin.json)
- [pm-skills Skill 示例](https://github.com/phuryn/pm-skills/blob/main/pm-product-discovery/skills/brainstorm-ideas-existing/SKILL.md)
- [pm-skills Command 示例](https://github.com/phuryn/pm-skills/blob/main/pm-product-discovery/commands/discover.md)

---

## 评审清单

- [ ] Plugin 分组是否合理？（7 个 Plugin 是否过多/过少？）
- [ ] Skill/Command 拆分是否清晰？
- [ ] 跨 Plugin 协作机制是否可行？
- [ ] 实施计划时间线是否合理？
- [ ] 是否有遗漏的 skill 或文件？
