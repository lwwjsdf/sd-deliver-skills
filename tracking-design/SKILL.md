---
name: sd-tracking-design
version: 0.1.0
description: 负责埋点采集方案设计。从业务目标确认到输出埋点方案 Excel（含 Events/Details/Users 三个 sheet），交付确认后供 sd-tracking-setup-e2e 使用
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble（每次调用时先执行）

```bash
_SKILL_REPO=$(sdeliver-config get skill_repo_path 2>/dev/null || echo "")

_ENV_FILE=""
_DIR="$(pwd)"
while [ "$_DIR" != "/" ]; do
  [ -f "$_DIR/.env" ] && _ENV_FILE="$_DIR/.env" && break
  _DIR="$(dirname "$_DIR")"
done

if [ -n "$_ENV_FILE" ]; then
  _CLIENT=$(grep '^CLIENT_NAME=' "$_ENV_FILE" | cut -d= -f2-)
  _PROJECT_DIR="$(dirname "$_ENV_FILE")"
  _HAS_PROJECT=$([ -f "$_PROJECT_DIR/PROJECT.md" ] && echo "yes" || echo "no")
  _HAS_CLARIFICATION=$([ -f "$_PROJECT_DIR/CLARIFICATION.md" ] && echo "yes" || echo "no")
  _HAS_PLAN=$([ -n "$(grep '^TRACKING_PLAN_PATH=' "$_ENV_FILE" | cut -d= -f2-)" ] && [ -f "$(grep '^TRACKING_PLAN_PATH=' "$_ENV_FILE" | cut -d= -f2-)" ] && echo "yes" || echo "no")
else
  _PROJECT_DIR="$(pwd)"
fi

echo "SKILL_REPO: ${_SKILL_REPO:-(未设置)}"
echo "CLIENT: ${_CLIENT:-unknown}"
echo "HAS_PROJECT_MD: $_HAS_PROJECT"
echo "HAS_CLARIFICATION: $_HAS_CLARIFICATION"
echo "HAS_TRACKING_PLAN: $_HAS_PLAN"
```

**Preamble 输出处理：**
- `ENV_FILE: none` → 停止，提示用户先运行 `sdeliver init <客户名>`
- `SKILL_REPO` 含"未设置" → 停止，提示重新运行 `./setup`
- `HAS_PROJECT_MD: yes` → 读取 `$PROJECT_DIR/PROJECT.md`，了解项目背景
- `HAS_CLARIFICATION: yes` → 同时读取 `$PROJECT_DIR/CLARIFICATION.md`
- `HAS_TRACKING_PLAN: yes` → 已有埋点方案，询问用户是要重新设计还是沿用现有方案

# 埋点采集方案设计

## 适用场景

- 客户新项目启动，需要从零建立数据采集体系
- 现有业务新增功能/渠道，需要补充埋点
- 客户已有 Excel 模板需要规范化整理

## 核心原则

**方案必须经客户确认才能交付给下游（sd-tracking-setup-e2e）。** 方案变更后数据导入和看板需全部返工。

## 交付流程

### Step 1：业务目标确认

与客户/项目组沟通，收集以下信息：

| 问题 | 目的 |
|------|------|
| 核心业务场景是什么？ | 确定需要追踪的用户行为路径 |
| 需要回答哪些业务问题？ | 转化率、留存、活跃度、渠道效果等 |
| 分析维度有哪些？ | 渠道、用户分群、时间粒度 |
| 数据由谁消费？ | 运营/产品/数据分析师，影响方案详细程度 |

输出：业务目标确认单（一页 Markdown），写入 `$PROJECT_DIR/docs/business_goals.md`

### Step 2：设计采集方案

基于业务目标，设计以下内容：

**事件定义表：**
| 字段 | 说明 |
|------|------|
| Event Name | 英文事件名，snake_case |
| 中文名 | 业务可读名称 |
| 触发时机 | 什么操作/状态触发 |
| 属性列表 | 每个事件关联的事件属性 |

**用户属性表：**
| 字段 | 说明 |
|------|------|
| 属性名 | snake_case |
| 类型 | STRING/NUMBER/BOOL/DATETIME/LIST |
| 示例值 | 典型示例 |

**输出格式：** 埋点方案 Excel（包含 Events / Details（Event）/ Users 三个 sheet）

**模板生成工具（推荐）：**
```bash
python3 <skill-repo>/tracking-design/scripts/generate_tracking_plan_template.py \
  --format standard \
  --output ./references/tracking-plan.xlsx
```

支持两种格式：
- `standard`：Events / Details(Event) / Users（tracking-design 原生格式）
- `mp`：Custom Event / Preset Event / Public Property / User Attribute（tracking_plan.py parser 原生格式）

两种格式已被 `tracking_plan.py` 统一识别，无需手动转换。

### Step 3：客户确认

将 Excel 发给客户确认，收集反馈并迭代。确认后在 `.env` 中设置：

```
TRACKING_PLAN_PATH=./references/tracking-plan.xlsx
```

### Step 4：移交互交付工程师

确认后，通知 Lead 安排交付工程师进入 sd-tracking-setup-e2e 流程。

## 输出模板

```
## 交付物清单

- [ ] 业务目标确认单（docs/business_goals.md）
- [ ] 埋点方案表（references/tracking-plan.xlsx）
- [ ] 客户确认记录
```

## Feedback

如需改进建议，随时调用 `/sd-feedback <描述>`。
