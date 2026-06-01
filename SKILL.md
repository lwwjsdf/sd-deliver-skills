---
name: sdeliver
version: 0.1.0
description: |
  神策数据交付 Skill 集合入口。感知当前客户项目状态，展示可用能力，
  引导用户选择合适的 skill。
  当用户说"帮我看看项目状态"、"我能做什么"、"下一步用哪个 skill"时使用。
  当用户描述交付工作场景时，匹配并推荐对应 skill，不直接执行交付步骤。
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

# sdeliver

## Preamble（每次调用时先执行）

```bash
_SKILL_REPO=$(sdeliver-config get skill_repo_path 2>/dev/null || echo "")
_PROACTIVE=$(sdeliver-config get proactive 2>/dev/null || echo "true")
_VERSION=$(sdeliver-config get version 2>/dev/null || echo "0.1.0")

_ENV_FILE=""
_DIR="$(pwd)"
while [ "$_DIR" != "/" ]; do
  [ -f "$_DIR/.env" ] && _ENV_FILE="$_DIR/.env" && break
  _DIR="$(dirname "$_DIR")"
done

if [ -n "$_ENV_FILE" ]; then
  _CLIENT=$(grep '^CLIENT_NAME=' "$_ENV_FILE" | cut -d= -f2-)
  _SA_HOST=$(grep '^SA_HOST=' "$_ENV_FILE" | cut -d= -f2-)
  _SA_PROJECT=$(grep '^SA_PROJECT=' "$_ENV_FILE" | cut -d= -f2-)
  _TRACKING_PLAN=$(grep '^TRACKING_PLAN_PATH=' "$_ENV_FILE" | cut -d= -f2-)
  _PROJECT_DIR="$(dirname "$_ENV_FILE")"
else
  _PROJECT_DIR="$(pwd)"
fi

_HAS_PLAN=$([ -n "$_TRACKING_PLAN" ] && [ -f "$_TRACKING_PLAN" ] && echo "yes" || echo "no")
_HAS_YAML=$([ -f "$_PROJECT_DIR/rules/business_logic.yaml" ] && echo "yes" || echo "no")
_HAS_DATA=$(ls "$_PROJECT_DIR/mock_data/"*.jsonl 2>/dev/null | head -1 | grep -q . && echo "yes" || echo "no")
_HAS_PROJECT=$([ -f "$_PROJECT_DIR/PROJECT.md" ] && echo "yes" || echo "no")
_HAS_CLARIFICATION=$([ -f "$_PROJECT_DIR/CLARIFICATION.md" ] && echo "yes" || echo "no")
_HAS_DELIVERY=$([ -f "$_PROJECT_DIR/DELIVERY.md" ] && echo "yes" || echo "no")
_DELIVERY_PROGRESS=""
if [ "$_HAS_DELIVERY" = "yes" ]; then
  _TOTAL=$(grep -c '^\- \[' "$_PROJECT_DIR/DELIVERY.md" 2>/dev/null; true)
  _DONE=$(grep -c '^\- \[x\]' "$_PROJECT_DIR/DELIVERY.md" 2>/dev/null; true)
  _DELIVERY_PROGRESS="${_DONE}/${_TOTAL}"
fi
_HAS_REFS=$(ls "$_PROJECT_DIR/references/" 2>/dev/null | grep -qv '^$' && echo "yes" || echo "no")
_REF_FILES=$(ls "$_PROJECT_DIR/references/" 2>/dev/null | tr '\n' ',' | sed 's/,$//')

echo "SDELIVER_VERSION: $_VERSION"
echo "SKILL_REPO: ${_SKILL_REPO:-(未设置，请重新运行 ./setup)}"
echo "PROACTIVE: $_PROACTIVE"
echo "ENV_FILE: ${_ENV_FILE:-none}"
echo "CLIENT: ${_CLIENT:-unknown}"
echo "SA_HOST: ${_SA_HOST:-(未填写)}"
echo "SA_PROJECT: ${_SA_PROJECT:-(未填写)}"
echo "HAS_PROJECT_MD: $_HAS_PROJECT"
echo "HAS_CLARIFICATION: $_HAS_CLARIFICATION"
echo "HAS_DELIVERY: $_HAS_DELIVERY"
echo "DELIVERY_PROGRESS: ${_DELIVERY_PROGRESS:--}"
echo "HAS_REFS: $_HAS_REFS"
echo "REF_FILES: ${_REF_FILES:-(空)}"
echo "HAS_TRACKING_PLAN: $_HAS_PLAN"
echo "HAS_BUSINESS_LOGIC: $_HAS_YAML"
echo "HAS_MOCK_DATA: $_HAS_DATA"

_FEEDBACK_DIR="$HOME/.sdeliver/feedback"
_PENDING_FEEDBACK=$(find "$_FEEDBACK_DIR" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "PENDING_FEEDBACK: $_PENDING_FEEDBACK"
[ "$_PENDING_FEEDBACK" -gt 0 ] && \
  echo "FEEDBACK_FILES: $(find "$_FEEDBACK_DIR" -name "*.md" 2>/dev/null | xargs -I{} basename {} | tr '\n' ',' | sed 's/,$//')"
```

## Preamble 输出处理

**① `ENV_FILE: none`：**
停止，告知用户：
```
当前目录没有找到客户项目，请先初始化：
  sdeliver init <客户名> ~/projects/<客户名>
```

**② `SKILL_REPO` 含"未设置"：**
停止，提示重新运行 `./setup`。

**③ 正常情况，输出项目状态卡片：**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 sdeliver v<VERSION>
 客户: <CLIENT>  |  <SA_HOST> / <SA_PROJECT>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 项目档案:    <HAS_PROJECT_MD == yes ? "✅ PROJECT.md" : "⚠️  未生成">
 信息澄清:    <HAS_CLARIFICATION == yes ? "✅ CLARIFICATION.md" : "— 未生成">
 交付进度:    <HAS_DELIVERY == yes ? "✅ DELIVERY.md  <DONE>/<TOTAL> 完成" : "— 未生成">
 埋点方案:    <HAS_TRACKING_PLAN == yes ? "✅ 已配置" : "— 未配置">
 业务规则:    <HAS_BUSINESS_LOGIC == yes ? "✅ business_logic.yaml" : "— 未生成">
 模拟数据:    <HAS_MOCK_DATA == yes ? "✅ 已生成" : "— 未生成">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

如果 `PENDING_FEEDBACK` > 0，在状态卡片后追加：
```
🔧 有 <PENDING_FEEDBACK> 条 skill 改进反馈待处理（在 Claude Code 中查看）：
   <FEEDBACK_FILES>
```
这是给 skill 开发者看的提示，不影响当前交付工作。

然后展示可用 skill 列表（始终展示，不管当前阶段）：

```
可用 skill：
  /sd-tracking-setup-e2e   埋点全链路交付（方案设计 → 造数 → 导入）
  /sd-event-validation     埋点数据校验与异常排查
  /sd-server-sizing        服务器资源评估与扩容建议
  /sd-sit-uat              上线前 SIT/UAT 测试设计与执行
  /sd-tech-design          技术方案与架构图输出
  /sd-faq                  交付知识库（容量评估、信创、ID3、排查 SOP）

你想做什么？
```

**④ 如果 `HAS_REFS: yes` 且 `HAS_PROJECT_MD: no`，在状态卡片后额外提示：**
```
💡 检测到 references/ 有文档（<REF_FILES>），建议先生成项目档案：
   直接说"生成项目档案"或"onboard"即可
```

## Onboard 工作流

当用户说"生成项目档案"、"onboard"、"读一下这些文档"时触发。

### Step 1：确认文档清单

列出 `references/` 中的所有文件，告知用户将要读取的内容，确认后继续。

### Step 2：逐个读取文档

按文件格式选择读取方式：

| 格式 | 读取方式 |
|------|---------|
| `.md` `.txt` | Read 工具直接读取 |
| `.docx` | `python3 $SKILL_REPO/shared/read_doc.py <file>` |
| `.doc` | `python3 $SKILL_REPO/shared/read_doc.py <file>` |
| `.pdf` | Read 工具直接读取 |
| `.xlsx` `.xls` | 用 openpyxl dump 原始内容后由 AI 解析（见下方说明） |

**Excel 文件处理方式：**

```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('$FILE', data_only=True)
print('Sheets:', wb.sheetnames)
for sheet in wb.sheetnames:
    ws = wb[sheet]
    print(f'\n=== {sheet} ({ws.max_row}行 x {ws.max_column}列) ===')
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        if any(v is not None for v in row):
            print(row)
"
```

读取后判断文件用途：
- **里程碑/项目计划表**（含 Milestone、Deliverable、Phase 等关键词）→ 标记为 `milestone_file`，Step 5 用于生成 DELIVERY.md
- **埋点方案**（含 Event、Property、Tracking 等关键词）→ 记录路径，提示用户设置 `TRACKING_PLAN_PATH`
- **其他**（预算、人员等）→ 提取关键信息纳入 PROJECT.md

从每个文档中提取（有则提取，无则留空，不编造）：
- 客户背景（行业、规模、核心业务）
- 本期交付范围（目标、功能模块、不在范围内的内容）
- 关键里程碑和时间节点
- 技术约束（CDP 版本、合规要求、集成系统）
- 关键联系人

### Step 3：生成 PROJECT.md

写入 `$PROJECT_DIR/PROJECT.md`：

```markdown
# 项目档案：<CLIENT_NAME>

> 由 sdeliver onboard 自动生成 · 来源：<文件列表> · <日期>

## 客户背景
- **行业**：
- **核心业务**：
- **数据现状**：

## 本期交付范围

### 目标

### 功能模块

### 不在范围内

## 关键里程碑

| 里程碑 | 计划日期 | 说明 |
|--------|---------|------|

## 技术约束
- **CDP 版本**：
- **数据合规**：
- **集成系统**：
- **特殊要求**：

## 关键联系人

| 角色 | 姓名 | 联系方式 |
|------|------|---------|
| 客户负责人 | | |
| 交付负责人 | | |

## 参考文档
<列出 references/ 中的文件>
```

### Step 4：生成 CLARIFICATION.md 并输出澄清列表

生成 PROJECT.md 后，同步生成 `$PROJECT_DIR/CLARIFICATION.md`，格式如下：

```markdown
# 信息澄清跟踪：<CLIENT_NAME>

> 由 sdeliver onboard 自动生成 · 最后更新：<日期>
> 用途：跟踪项目信息的确认状态，持续维护直到所有 high 优先级信息补全

## ⚠️ 待确认（AI 推断，需用户核实）

| # | 内容 | 推断依据 | 状态 |
|---|------|---------|------|
| 1 | <推断内容> | <依据> | 🔲 待确认 |

## ❓ 信息缺失

| # | 缺失信息 | 优先级 | 状态 |
|---|---------|--------|------|
| 1 | <缺失项> | high | 🔲 待补充 |
| 2 | <缺失项> | medium | 🔲 待补充 |

## ✅ 已确认归档

> 用户确认或补充后，从上方移入此处

| 信息 | 值 | 来源 | 确认日期 |
|------|-----|------|---------|
```

**状态说明：**
- `🔲 待确认 / 待补充` — 尚未处理
- `✅ 已确认` — 用户已核实或补充
- `❌ 不适用` — 确认后发现不需要

**生成后立即在对话中输出澄清列表摘要**（同 CLARIFICATION.md 内容），询问用户：
```
以上信息是否准确？有需要补充或修正的，直接告诉我，我会同步更新 PROJECT.md 和 CLARIFICATION.md。
```

**用户补充信息后：**
1. 更新 PROJECT.md 对应字段
2. 在 CLARIFICATION.md 中将该条状态改为 `✅ 已确认`，移入"已确认归档"区
3. 更新文件头部的"最后更新"日期

### Step 5：生成 DELIVERY.md

如果 Step 2 中识别到里程碑/项目计划表（`milestone_file`），基于解析内容生成 `$PROJECT_DIR/DELIVERY.md`。

**生成逻辑（由 AI 执行，不依赖固定脚本）：**

1. 理解表格结构：识别里程碑、交付物、验收节点、时间节点等字段，不同项目格式不同，用语义理解而非固定列名匹配
2. 按里程碑分组，每个里程碑下列出交付物条目
3. 根据交付物内容推断建议使用的 skill（见下方映射）
4. 验收节点（付款触发点）用 ⭐ 标注

**交付物 → skill 映射参考：**

| 交付物关键词 | 建议 skill |
|------------|-----------|
| 埋点、Tag、Data Collection、Tracking Plan、URS、FRS | `/sd-tracking-setup-e2e` |
| Technical Solution、Architecture、Design Spec、IaC | `/sd-tech-design` |
| SIT、UAT、Test Cases、Test Report、Acceptance Report | `/sd-sit-uat` |
| 数据校验、Data Validation | `/sd-event-validation` |

**DELIVERY.md 格式：**

```markdown
# 交付进度：<CLIENT_NAME>

> 来源：<文件名> · 生成日期：<日期> · 整体进度：0/<总数>

---

## <Year / Phase 1>

### <Category>

#### M<n>: <Milestone Name> [⭐ _<验收节点说明>_]

- [ ] <交付物>  `→ /sd-<skill>`
- [ ] <交付物>

...

---

## 说明

- `[ ]` 待启动 · `[~]` 进行中 · `[x]` 已完成
- ⭐ 标注的里程碑为合同验收节点
- skill 标注为建议，实际执行时按需调整
- 每次 skill 工作完成后更新对应条目状态
```

**如果没有里程碑文件：**
生成一个基于 PROJECT.md 交付范围的最简版 DELIVERY.md，只包含通用交付物框架，提示用户后续补充里程碑计划表。

**生成后告知用户：**
```
DELIVERY.md 已生成，共 <N> 个交付物条目，与项目计划表里程碑对齐。
后续每个 skill 完成工作后会自动更新对应条目状态。
```

## Skill 调度

当用户描述工作场景时，匹配并推荐对应 skill，**不直接执行交付步骤**：

| 用户描述 | 推荐 |
|---------|------|
| 埋点、数据采集、tracking、造数、模拟数据、元数据导入 | `/sd-tracking-setup-e2e` |
| 数据异常、校验、验证、埋点上线后 | `/sd-event-validation` |
| 服务器、资源评估、扩容、部署配置 | `/sd-server-sizing` |
| SIT、UAT、测试、上线验收 | `/sd-sit-uat` |
| 技术方案、架构图、评审材料 | `/sd-tech-design` |
| 容量评估、带宽、信创、ID3、排查 SOP | `/sd-faq` |

如果 `PROACTIVE` 为 `false`，不主动推荐，等用户明确要求后再说。

## 完成状态协议

每次工作流结束时报告：
- **DONE** — 完成，已提供依据
- **DONE_WITH_CONCERNS** — 完成，但有需关注的问题（逐条列出）
- **BLOCKED** — 无法继续，说明原因和已尝试的方法
- **NEEDS_CONTEXT** — 缺少必要信息，说明具体需要什么
