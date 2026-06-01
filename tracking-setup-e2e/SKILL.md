---
name: sd-tracking-setup-e2e
version: 0.1.0
description: 客户新项目启动或新业务场景需要完整数据采集和分析能力时使用
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

## Preamble（每次调用时先执行）

```bash
_SKILL_REPO=$(sdeliver-config get skill_repo_path 2>/dev/null || echo "")
_PROACTIVE=$(sdeliver-config get proactive 2>/dev/null || echo "true")

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
  _API_KEY=$(grep '^API_KEY=' "$_ENV_FILE" | cut -d= -f2-)
  _TRACK_URL=$(grep '^SA_TRACK_URL=' "$_ENV_FILE" | cut -d= -f2-)
  _PROJECT_DIR="$(dirname "$_ENV_FILE")"
else
  _PROJECT_DIR="$(pwd)"
fi

_HAS_PLAN=$([ -n "$_TRACKING_PLAN" ] && [ -f "$_TRACKING_PLAN" ] && echo "yes" || echo "no")
_HAS_YAML=$([ -f "$_PROJECT_DIR/rules/business_logic.yaml" ] && echo "yes" || echo "no")
_HAS_DATA=$(ls "$_PROJECT_DIR/mock_data/"*.jsonl 2>/dev/null | head -1 | grep -q . && echo "yes" || echo "no")
_HAS_PROJECT=$([ -f "$_PROJECT_DIR/PROJECT.md" ] && echo "yes" || echo "no")
_HAS_CLARIFICATION=$([ -f "$_PROJECT_DIR/CLARIFICATION.md" ] && echo "yes" || echo "no")

echo "SKILL_REPO: ${_SKILL_REPO:-(未设置)}"
echo "ENV_FILE: ${_ENV_FILE:-none}"
echo "PROJECT_DIR: $_PROJECT_DIR"
echo "CLIENT: ${_CLIENT:-unknown}"
echo "SA_HOST: ${_SA_HOST:-(未填写)}"
echo "SA_PROJECT: ${_SA_PROJECT:-(未填写)}"
echo "TRACKING_PLAN: ${_TRACKING_PLAN:-(未设置)}"
echo "HAS_PROJECT_MD: $_HAS_PROJECT"
echo "HAS_CLARIFICATION: $_HAS_CLARIFICATION"
echo "HAS_TRACKING_PLAN: $_HAS_PLAN"
echo "HAS_BUSINESS_LOGIC: $_HAS_YAML"
echo "HAS_MOCK_DATA: $_HAS_DATA"
echo "HAS_API_KEY: $([ -n "$_API_KEY" ] && echo "yes" || echo "no")"
echo "HAS_TRACK_URL: $([ -n "$_TRACK_URL" ] && echo "yes" || echo "no")"
```

**Preamble 输出处理：**

- `ENV_FILE: none` → 停止，提示用户先运行 `sdeliver init <客户名>`
- `SKILL_REPO` 含"未设置" → 停止，提示重新运行 `./setup`
- `HAS_PROJECT_MD: yes` → 读取 `$PROJECT_DIR/PROJECT.md`，将项目背景纳入上下文
- `HAS_CLARIFICATION: yes` → 同时读取 `$PROJECT_DIR/CLARIFICATION.md`，了解哪些信息仍待确认，在交付过程中遇到相关信息时主动补充
- 否则，输出：`客户: <CLIENT> | 环境: <SA_HOST>/<SA_PROJECT> | 项目目录: <PROJECT_DIR>`

脚本调用时，将 `<skill-repo>` 替换为 `$SKILL_REPO` 的实际值，将 `<project-dir>` 替换为 `$PROJECT_DIR`。

# 埋点全链路交付

## 适用场景

- 客户新项目启动，需要从零建立数据采集体系
- 现有业务新增功能，需要补充埋点和分析看板
- 需要将测试环境配置迁移到客户生产环境

## 核心原则（Iron Law）

**必须先完成采集方案设计并经客户确认，再进行后续任何步骤。**

不允许在方案未确认的情况下造数或创建看板。违反此原则会导致返工。

**已有方案时的快速入口：**

| 用户说 | 从哪里开始 |
|--------|-----------|
| 已有确认好的埋点方案 Excel | Phase 3a（生成 business_logic.yaml） |
| 已有 business_logic.yaml | Phase 3b（验证） |
| YAML 已验证通过，要确认枚举值 | Phase 3c（枚举值确认） |
| 枚举值已确认，要造数 | Phase 3d（造数） |
| 已造好数据，要导入 CDP | Phase 4b-1（先做元数据预检查） |
| 已导入元数据，要造数 | Phase 3 |
| 只需要迁移资产 | Phase 5 |

开始前直接问用户："你现在在哪个阶段？有没有已确认的埋点方案文件？"

## 前置条件

### 项目启动时（一次性）

每个新客户项目用 `sdeliver init` 初始化，在 skill repo **之外**创建独立的客户项目目录：

```bash
sdeliver init <client-name> ~/projects/<client-name>
cd ~/projects/<client-name>
```

生成的目录结构：

```
~/projects/<client-name>/
├── .env              ← 填写 CDP 连接信息（见下表）
├── references/       ← 放入客户提供的埋点方案 Excel
├── rules/            ← business_logic.yaml 生成位置
└── mock_data/        ← 模拟数据生成位置
```

填写 `.env` 后用 `sdeliver check` 验证配置是否完整。

### 配置说明

| 配置项 | 环境变量 | 示例 | 获取方式 |
|--------|----------|------|----------|
| **CDP 地址** | `SA_HOST` | `https://demo.sensorsdata.cn` | 登录神策后浏览器地址栏 |
| **项目 ID** | `SA_PROJECT` | `default` | 登录后 URL 中 `project=` 的值 |
| **Open API 密钥** | `API_KEY` | `#K-jHllJkc...` | 神策后台 → 系统管理 → API 密钥 |
| **数据接收地址** | `SA_TRACK_URL` | `https://demo.sensorsdata.cn/sa?project=default` | 神策后台 → 数据接入 → HTTP API |
| **埋点方案路径** | `TRACKING_PLAN_PATH` | `./references/tracking-plan.xlsx` | 客户提供的埋点方案 |

> **注意区分**：
> - **Open API 密钥**：用于元数据导入（创建事件、属性），在「系统管理 → API 密钥」获取
> - **数据接收地址**：用于数据导入，在「数据接入 → HTTP API」获取，是一个完整的 URL

### 脚本运行方式

所有脚本在**客户项目目录**下运行，自动读取 `.env`，无需重复传参：

```bash
cd ~/projects/<client-name>
python3 <skill-repo>/tracking-setup-e2e/scripts/<script>.py
```

也可以通过命令行参数覆盖 `.env` 中的值（适合 Agent 直接调用）。

## 执行阶段

### Phase 1：业务目标确认 👤

收集以下信息后才能进入 Phase 2：
- 核心业务场景（用户注册/购买/使用路径等）
- 需要回答的关键业务问题（转化率？留存？活跃度？）
- 分析维度（渠道、用户分群、时间粒度）
- 数据消费方（运营/产品/数据分析师）

输出：业务目标确认单（一页，列出以上四项）

### Phase 2：采集方案设计 👤

基于 Phase 1 输出，设计埋点方案：
- 事件列表（事件名、中文名、触发时机）
- 每个事件的属性列表（属性名、类型、示例值、是否必填）
- 用户属性列表（属性名、类型）

**等待客户确认后才能进入 Phase 3。确认后在 `.env` 中设置 `TRACKING_PLAN_PATH`。**

输出：埋点方案表（Excel，包含 Events / Details（Event） / Users 三个 sheet）

### Phase 3：模拟数据生成 🤖

Phase 3 分四步：生成业务规则 YAML → 验证 → 枚举值确认 → 造数。

#### Step 3a：生成 business_logic.yaml

**这一步由你（agent）完成，不是调脚本。**

读取 `<skill-repo>/tracking-setup-e2e/rules/YAML_GENERATION_PROMPT.md`，按其中的指南生成 YAML 文件，保存到客户项目目录：

```
~/projects/<client-name>/rules/business_logic.yaml
```

两种情况：
- **有业务需求文档**（docx/描述）：读文档提取业务逻辑，结合 Tracking Plan 事件名填写完整 YAML
- **无业务文档**：使用 `YAML_GENERATION_PROMPT.md` 中的默认模板，替换事件名和 `meta.project`

#### Step 3b：验证 YAML

```bash
python3 <skill-repo>/tracking-setup-e2e/scripts/yaml_validator.py \
  ./rules/business_logic.yaml \
  --tracking-plan "$TRACKING_PLAN_PATH"
```

- 有 **error**：修复 YAML，重新验证，直到 PASSED
- 有 **warning**：逐条确认是否是真实问题，无误后继续
- **PASSED**：进入 Step 3c

#### Step 3c：枚举值确认 👤

**这一步需要客户参与确认，不能跳过。**

先运行检查脚本，获取问题清单和完整枚举值列表：

```bash
python3 <skill-repo>/tracking-setup-e2e/scripts/list_enum_values.py \
  --tracking-plan "$TRACKING_PLAN_PATH"
```

然后**分四批**向客户确认，每批聚焦一个主题，不要一次性抛出所有属性：

---

**批次 1：问题字段（优先处理）**

将脚本输出的「问题清单」展示给客户，针对严重/中等问题逐条确认：

> 脚本检测到以下字段存在问题，请确认处理方式：
> - `purchaseType`：枚举值末尾混入了说明文字，实际枚举项应该是哪几个？
> - `membershipNumber`：当前值是会员类型名称，实际应该是什么格式（如卡号 `M-2025-000001`）？

根据客户回复，在 `property_enums` 中覆盖对应字段。

---

**批次 2：格式类字段**

针对日期、时间、编号等有格式要求的字段，逐一确认格式和范围。

---

**批次 3：核心业务枚举**

展示影响漏斗/分群分析的核心维度值，请客户确认是否完整。

---

**批次 4：行为路径枚举**

展示影响路径分析的入口/来源值，请客户确认是否覆盖主要场景。

---

**所有批次确认完毕后，根据客户反馈更新 `rules/business_logic.yaml`，再进入 Step 3d。**

#### Step 3d：造数

先询问用户数据规模需求，然后运行：

```bash
# 固定测试账号（UAT 场景验证，默认）
python3 <skill-repo>/tracking-setup-e2e/scripts/generate_mock_data.py \
  --rules ./rules/business_logic.yaml \
  --tracking-plan "$TRACKING_PLAN_PATH"

# 批量随机用户（大数据量）
python3 <skill-repo>/tracking-setup-e2e/scripts/generate_mock_data.py \
  --rules ./rules/business_logic.yaml \
  --tracking-plan "$TRACKING_PLAN_PATH" \
  --users 100 --days 30 --sessions-per-day 5
```

**数据规模参考：**

| 场景 | 参数 | 约估事件量 |
|------|------|-----------|
| UAT 场景验证 | 默认（固定账号） | ~50–100 条 |
| 功能测试 | `--users 50 --days 7` | ~3,000 条 |
| 漏斗/留存分析 | `--users 100 --days 30 --sessions-per-day 5` | ~14 万条 |
| 压测 | `--users 500 --days 30 --sessions-per-day 10` | ~140 万条 |

输出文件（在 `./mock_data/` 下）：
- `<project>.jsonl` — 每行一条记录
- `<project>_batch.txt` — base64 编码，可直接 POST
- `<project>_identity_map.csv` — 用于校验 ID-Mapping 合并结果
- `uat_validation_report.md` — 业务规则违规报告

### Phase 4a：元数据导入 CDP 🤖

```bash
python3 <skill-repo>/tracking-setup-e2e/scripts/import_meta_data.py \
  --tracking-plan "$TRACKING_PLAN_PATH"
# 其余参数自动从 .env 读取
```

脚本自动完成：
1. 检查 API 连接
2. 从 Excel 读取事件列表，逐个创建元事件
3. 读取事件属性，写入对应事件
4. 读取用户属性，批量写入

注意：系统保留字段名（如 `Id`、`PersonEmail`）会自动跳过并在输出中列出。

### Phase 4b：模拟数据导入 🤖

Phase 4b 分三步：元数据预检查 → 数据导入 → 导入结果校验。

#### Step 4b-1：元数据预检查

**在导入数据前**，先确认 JSONL 中所有事件和属性已在 CDP 中创建，避免强校验导致导入失败：

```bash
python3 <skill-repo>/tracking-setup-e2e/scripts/check_metadata.py \
  --jsonl "./mock_data/<project>.jsonl"
# CDP 连接信息自动从 .env 读取
```

- 输出 `✅ 全部通过`：直接进入 Step 4b-2
- 输出 `❌ 缺少事件/属性`：先回到 Phase 4a 补充元数据，再重新检查
- CDP 未开启强校验时可加 `--warn-only` 跳过退出码拦截

#### Step 4b-2：数据导入

```bash
python3 <skill-repo>/tracking-setup-e2e/scripts/import_mock_data.py \
  --jsonl "./mock_data/<project>.jsonl"
# 数据接收地址自动从 .env 读取
```

#### Step 4b-3：导入结果校验

导入完成后，通过 OpenAPI 自定义查询校验数据是否正确落库：

```bash
python3 <skill-repo>/tracking-setup-e2e/scripts/validate_import.py \
  --jsonl "./mock_data/<project>.jsonl"
# CDP 连接信息自动从 .env 读取
```

CDP 数据处理有延迟时，加 `--wait 60` 等待 60 秒后再查询。

脚本输出各事件的「导入条数 vs CDP条数」对比表：
- `✅`：数量一致
- `⚠️ 偏少`：部分数据未落库，可能是处理延迟，稍后重试
- `❌ 未找到`：事件完全未入库，检查元数据是否存在、数据接收地址是否正确

### Phase 4c：看板创建 👤

按业务目标创建看板，参考 cdp-operations skill。截图存档。

### Phase 5：资产迁移 🤖

使用神策资产项工具将配置元数据从测试环境迁移到客户生产环境：
1. 导出测试环境资产（看板、标签、事件定义）
2. 检查资产依赖关系
3. 导入客户生产环境
4. 验证迁移结果

输出：资产迁移记录（迁移项清单 + 验证截图）

## 输出模板

```
## 交付物清单

- [ ] 业务目标确认单
- [ ] 埋点方案表（已客户确认）
- [ ] 模拟数据文件（mock_data/<project>.jsonl）
- [ ] 元数据导入确认（import_meta_data.py 输出日志）
- [ ] 导入结果校验报告（validate_import.py 输出）
- [ ] 看板截图
- [ ] 资产迁移记录
```

## 常见问题

**客户说"先做再确认"：** 坚持 Phase 2 确认门。方案变更后造数和看板全部作废，返工成本远高于等待确认的时间。

**sdeliver init 找不到命令：** 运行 `<skill-repo>/setup` 安装，并确认 `~/.local/bin` 在 PATH 中。

**import_meta_data.py 报"缺少必要配置"：** 在客户项目目录下运行 `sdeliver check`，确认 `.env` 中必填项已填写。

**字段创建报 ALREADY_EXISTS：** 正常，脚本自动跳过，不影响其他字段。

**元事件属性写入失败（10005 错误）：** 通常是事件上有特殊关联字段，脚本已自动处理常见情况。如仍报错，检查事件是否有虚拟字段依赖。

**check_metadata.py 报缺少事件/属性：** 先运行 `import_meta_data.py` 补充元数据，再重新执行预检查，通过后再导入数据。

**validate_import.py 自定义查询无数据：** 数据处理有延迟，加 `--wait 60` 等待后重试。若仍无数据，检查账号是否有自定义查询权限，或登录神策后台手动执行脚本输出的 SQL。

**validate_import.py 显示条数偏多：** 正常，CDP 中可能有历史数据，只要不是 0 或偏少即可。

**模拟数据不够真实：** 向客户要 1-2 个真实业务场景的描述，更新 `rules/business_logic.yaml` 中的 `event_sequences`，重新验证后造数。

**yaml_validator.py 报 event not found：** YAML 中的事件名与 Tracking Plan 不一致。运行 `python3 -c "import sys; sys.path.insert(0,'<skill-repo>/tracking-setup-e2e/scripts'); from tracking_plan import TrackingPlan; [print(e) for e in TrackingPlan('$TRACKING_PLAN_PATH').list_events()]"` 获取合法事件名列表。

**yaml_validator.py 报 ratios sum to X：** 检查 `user_segments` 或 `region_distribution` 各项比例，确保加总精确为 1.0。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录，无需中断当前工作。
