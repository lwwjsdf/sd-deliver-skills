---
name: sd-draw-diagram
version: 0.3.0
description: 为神策 CDP & MAE 项目生成 draw.io 架构图。以 arch.yaml 为唯一事实层，渲染器严格从语义派生视觉，支持标准模板生成和自定义架构描述两种模式
allowed-tools:
  - Bash
  - Read
  - Write
---

## Preamble（每次调用时先执行）

```bash
_SKILL_REPO=$(sdeliver-config get skill_repo_path 2>/dev/null || echo "")
echo "SKILL_REPO: ${_SKILL_REPO:-(未设置)}"
_ENV_FILE=""
_DIR="$(pwd)"
while [ "$_DIR" != "/" ]; do
  [ -f "$_DIR/.env" ] && _ENV_FILE="$_DIR/.env" && break
  _DIR="$(dirname "$_DIR")"
done
[ -n "$_ENV_FILE" ] && _CLIENT=$(grep '^CLIENT_NAME=' "$_ENV_FILE" | cut -d= -f2-)
echo "CLIENT: ${_CLIENT:-unknown}"
```

**Preamble 输出处理：**
- `SKILL_REPO` 含"未设置" → 停止，提示重新运行 `./setup`

---

# 架构图生成（draw.io）

## 设计理念：事实层与渲染层分离

```
arch.yaml（事实层）          render.py（渲染层）
─────────────────            ─────────────────
节点的语义类型  ───────────→  颜色（绿/紫/蓝/灰）
关系类型       ───────────→  连线线型（实线/虚线）
has_pii + frequency ──────→  连线颜色（红/绿/蓝）
status: future ───────────→  灰色虚线节点
group 归属     ───────────→  容器框位置和尺寸
```

**arch.yaml 只描述"是什么"，render.py 决定"怎么画"。** 两者通过语义规则表耦合，规则表是唯一的视觉决策来源。这意味着：
- 修改客户架构 → 只改 arch.yaml
- 修改设计规范 → 只改 render.py 的规则表
- 两者互不干扰，可独立版本控制

---

## 两种工作模式

```
模式 A：模板生成（标准 Westk 架构，快速）
  填写 diagram_config.json → gen_diagrams.py → 6 个标准 drawio 图

模式 B：事实层生成（任意架构，准确）
  用自然语言描述架构 → LLM 生成 arch.yaml → render.py → drawio 图
```

**选择依据：**
- 架构与标准模板基本一致 → **模式 A**
- 有非标结构（无 ETL、中转系统、特殊数据流） → **模式 B**
- 先用 A 生成框架，针对非标部分用 B 重新生成 → **混合**

---

## 模式 A：模板生成

```bash
python3 $SKILL_REPO/draw-diagram/templates/gen_diagrams.py \
  --config diagram_config.json \
  --output $PROJECT_DIR/diagrams/
```

config 格式见 `$SKILL_REPO/draw-diagram/templates/DIAGRAM_GUIDE.md`。

---

## 模式 B：事实层生成

### Step 1：LLM 收集架构事实

收到用户描述后，先分析以下 6 个维度，输出一段确认摘要，再生成 arch.yaml：

1. **数据来源**：所有数据源系统（CRM/TAS/前端渠道），哪些是 future
2. **中间层**：有无 ETL、中转系统、消息队列（非标结构重点）
3. **核心产品**：CDP / MAE / 仅 CDP
4. **下游系统**：邮件服务商、推送平台、用户
5. **PII 流向**：哪些连线含 PII，哪些是批量（daily/weekly）
6. **合规约束**：跨境数据、数据驻留（影响区域节点和 PIPL 标注）

### Step 2：生成 arch.yaml

arch.yaml 是唯一事实来源，格式如下：

```yaml
meta:
  title: "图标题"
  client: "客户名"
  version: "1.0"
  date: "YYYY-MM-DD"

nodes:
  - id: crm                    # snake_case 唯一 ID
    name: "CRM"
    type: client_system        # 语义类型（见类型表）
    group: client_systems      # 所属分组（可选）
    status: current            # current | future（future→灰色虚线）
    props:
      note: "附加说明（可选）"

groups:
  - id: client_systems
    name: "Client Systems"
    type: client_systems       # 分组类型（见类型表）
    contains: [crm, tas]

edges:
  - from: crm
    to: system_a
    rel: sftp_export           # 关系类型（见关系表）
    name: "MemberInfo / Transaction"
    data:
      has_pii: true
      fields: [memberinfo, transaction]
      protocol: SFTP
      frequency: daily         # realtime | daily | weekly | on-demand
    status: current
```

#### 节点类型（type）→ 渲染颜色

| type | 语义 | 颜色 |
|------|------|------|
| `sd_product` | 神策产品（CDP/MAE/ETL） | 绿 `#d5e8d4` |
| `sd_module` | 神策内部功能模块 | 黄 `#fffde7` |
| `client_system` | 客户业务系统 | 紫 `#e1d5e7` |
| `client_frontend` | 客户前端渠道 | 紫 `#e1d5e7` |
| `external_saas` | 外部 SaaS 服务 | 蓝 `#dae8fc` |
| `person` | 用户角色 | 橙 + 人形图标 |
| `infra` | 基础设施（SFTP/RDS）| 绿 `#d5e8d4` |

#### 关系类型（rel）→ 渲染连线

| rel | 语义 |
|-----|------|
| `sdk_track` | SDK 埋点上报 |
| `api_push` | API 实时推送 |
| `sftp_export` | SFTP 文件导出 |
| `kafka_subscribe` | Kafka 异步订阅 → **强制蓝色虚线** |
| `api_call` | API 调用 |
| `data_passthrough` | 数据透传（中转系统） |
| `user_access` | 用户访问 |
| `callback` | 回调（邮件事件等）→ **绿色实线** |
| `deliver` | 消息投递（邮件/推送） |

#### 渲染规则（render.py 执行，arch.yaml 不涉及）

```
连线颜色优先级：
  1. rel=kafka_subscribe        → 蓝色虚线（最高优先，覆盖 PII）
  2. status=future              → 灰色虚线
  3. has_pii=true, daily/weekly → 红色虚线
  4. has_pii=true, realtime     → 红色实线
  5. rel=callback               → 绿色实线
  6. 其余                       → 绿色实线

节点颜色：由 type 字段查规则表，status=future 覆盖为灰色
```

### Step 3：运行渲染器

```bash
python3 $SKILL_REPO/draw-diagram/builder/render.py \
  --arch $PROJECT_DIR/diagrams/arch.yaml \
  --output $PROJECT_DIR/diagrams/<图名>_<客户>.drawio
```

渲染器自动完成：坐标计算、容器框生成、颜色/线型渲染、图例添加。

### Step 4：检查和微调

渲染结果直接可用，以下情况需在 draw.io 中微调：
- CDP/MAE 大框内的子模块需手动拖入容器内部（平铺布局）
- 节点间距不均匀时，拖动调整

---

## 典型非标架构变体

### 无 ETL，有统一中转系统

```yaml
nodes:
  - id: system_a
    name: "System A\n(Integration Hub)"
    type: client_system   # 客户自有，紫色
    props:
      note: "替代标准 ETL，聚合多系统数据后统一推入 CDP"

edges:
  - from: crm
    to: system_a
    rel: sftp_export
    data: {has_pii: true, frequency: daily}
  - from: system_a
    to: cdp
    rel: data_passthrough
    data: {has_pii: true, frequency: realtime}
```

### 仅 CDP，无 MAE

删除 `mae` 节点和所有 `from/to: mae` 的边，加入 `business_user` 节点（`type: person`），CDP → business_user 用 `rel: user_access`。

### 多区域，含大陆数据驻留

```yaml
nodes:
  - id: ecs_sz
    name: "ECS (SZ)\nMainland Backup"
    type: infra
    props:
      note: "大陆数据驻留节点，PIPL 合规"
edges:
  - from: cdp
    to: ecs_sz
    rel: sftp_export
    name: "PIPL Daily Export"
    data: {has_pii: true, frequency: daily, protocol: SFTP}
```

---

## 基础设施架构图（手动绘制）

基础设施架构图（LLD Section 3.5.1）与云厂商强相关，不提供自动生成。
绘制规范见：`$SKILL_REPO/draw-diagram/templates/DIAGRAM_GUIDE.md`

---

## 常见问题

**arch.yaml 中 future 节点是否需要连线？**
可以有 future 连线（`status: future`），渲染为灰色虚线，表示规划中的数据流。

**字段名应该用中文还是英文？**
fields 列表用英文 snake_case（渲染成连线标签的一部分）；name 用英文短语（客户审阅用）。

**需要在 PPT 中使用：**
draw.io → File → Export As → PNG（300dpi）或 SVG → 嵌入 PPT。

## Feedback

使用过程中发现问题，随时调用 `/sd-feedback <描述>` 记录。

---

## Review Loop（自动质量保障）

生成图后，运行 review loop 自动检查并修复问题，直到通过或达到最大轮次：

```bash
python3 $SKILL_REPO/draw-diagram/review_loop.py \
  --arch $PROJECT_DIR/diagrams/arch.yaml \
  --output $PROJECT_DIR/diagrams/<图名>.drawio \
  --max-rounds 5 \
  --verbose
```

**六个内置 Checker：**

| Checker | 类别 | 检查内容 | 可自动修复 |
|---------|------|---------|-----------|
| `overlap_checker` | visual | 节点边界框重叠 | ✓ 调整 view.yaml 坐标 |
| `orphan_checker` | completeness | 孤立节点（无连线） | 需确认 |
| `pii_color_checker` | spec_compliance | deliver/callback 边的 PII 标注一致性 | ✓ 更新 arch.yaml |
| `container_checker` | visual | group 成员节点超出容器框 | ✓ 扩大容器框 |
| `edge_label_checker` | completeness | 主要数据流连线缺少 name 标签 | 需确认 |
| `node_type_checker` | semantic | 节点名称与 type 字段不一致 | 需确认 |

**终止条件：** 无 FAIL（WARN 可接受）即通过。语义类问题需人工确认后才自动修复。

**Review Framework 位置（被所有 skill 复用）：**
```
$SKILL_REPO/shared/review/protocol.py   ← Checker/Fixer/ReviewLoop 接口定义
$SKILL_REPO/draw-diagram/review/        ← draw-diagram 专属 checker/fixer 实现
```
