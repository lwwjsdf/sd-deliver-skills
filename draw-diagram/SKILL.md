---
name: sd-draw-diagram
version: 0.2.0
description: 为神策 CDP & MAE 项目生成 draw.io 架构图。支持两种模式：基于模板快速生成标准图，或基于自然语言描述生成自定义架构图
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

## 两种工作模式

```
模式 A：模板生成（标准架构，快速）
  用户描述 → 填写 diagram_config.json → gen_diagrams.py → 6 个标准图

模式 B：自定义生成（非标架构，灵活）
  用户描述架构 → LLM 理解意图 → 生成 arch.json → diagram_builder.py → 自定义图
```

**选择依据：**
- 客户架构与标准 Westk 结构基本一致（有 ETL、标准数据源）→ **模式 A**
- 客户有非标结构（无 ETL、有中间系统、特殊数据流）→ **模式 B**
- 先用模式 A，再针对特定图用模式 B 修改 → **混合使用**

---

## 模式 A：模板生成

### Step 1：填写客户配置

```json
{
  "CLIENT": "客户简称",
  "CLIENT_SYSTEMS": "客户系统总称",
  "BUSINESS_USER": "业务用户称呼",
  "EMAIL_SERVICE": "邮件服务商",
  "FRONTEND_1": "主要前端渠道",
  "FRONTEND_2": "次要前端渠道",
  "FRONTEND_3": "第三前端渠道",
  "FRONTEND_4": "其他渠道",
  "SOCIAL_MEDIA": "社交媒体平台",
  "SYSTEM_1": "核心业务系统1",
  "SYSTEM_2": "核心业务系统2",
  "SYSTEM_3": "核心业务系统3",
  "SYSTEM_4": "Future 系统1",
  "SYSTEM_5": "Future 系统2",
  "SYSTEM_6": "Future 系统3",
  "SYSTEM_7": "Future 系统4",
  "SYSTEM_8": "Future 系统5"
}
```

### Step 2：生成

```bash
python3 $SKILL_REPO/draw-diagram/templates/gen_diagrams.py \
  --config $PROJECT_DIR/diagrams/diagram_config.json \
  --output $PROJECT_DIR/diagrams/
```

生成 6 个文件：逻辑架构图、数据流图、系统流图（3种用户视角）、功能架构图。

### Step 3：必做调整（在 draw.io 中）

- 删除不涉及的 Future 节点（灰色虚线）
- 修改连线标签（字段名、协议、频率）
- 更新地域标注（HK/SZ → 客户实际区域）
- 按合规要求调整 PIPL/数据驻留标注

---

## 模式 B：自定义生成

### 工作原理

```
用户用自然语言描述架构
       ↓
LLM 理解意图，查询组件库，生成标准化 arch.json
       ↓
diagram_builder.py 读取 arch.json
  - 自动计算列布局和坐标
  - 按组件库样式渲染节点（颜色/尺寸/形状）
  - 按连线语义渲染边（颜色/虚实/箭头）
  - 自动添加图例
       ↓
输出 .drawio 文件
```

### 可用组件库

查看所有标准组件：

```bash
python3 $SKILL_REPO/draw-diagram/builder/components.py
```

**组件速查：**

| 组件 ID | 标签 | 颜色 | 说明 |
|---------|------|------|------|
| `cdp` | CDP | 绿 | 神策 CDP 主容器 |
| `mae` | MAE | 绿 | 神策 MAE 主容器 |
| `etl` | ETL | 绿 | ETL 批量处理节点 |
| `sftp` | SFTP Server | 绿 | SFTP 文件传输 |
| `cdp_ingest` | Data Ingestion & ETL | 黄 | CDP 内部模块 |
| `cdp_identity` | Identity Resolution | 黄 | CDP 内部模块 |
| `cdp_segment` | Segmentation & Tagging | 黄 | CDP 内部模块 |
| `cdp_analytics` | Analytics & Dashboard | 黄 | CDP 内部模块 |
| `mae_campaign` | Campaign Planning | 黄 | MAE 内部模块 |
| `mae_journey` | Journey Orchestration | 黄 | MAE 内部模块 |
| `mae_channel` | Channel Management | 黄 | MAE 内部模块 |
| `crm` | CRM | 紫 | 客户 CRM 系统 |
| `ticketing` | Ticketing System | 紫 | 票务系统 |
| `erp` | ERP | 紫 | ERP 系统 |
| `miniprogram` | Mini-Program | 紫 | 微信小程序 |
| `website` | Website | 紫 | 网站 |
| `app` | Mobile App | 紫 | 移动应用 |
| `sendcloud` | SendCloud | 蓝 | 邮件服务商 |
| `end_user` | End User | 橙 | 最终用户（人形） |
| `business_user` | Business User | 橙 | 业务用户（人形） |
| `custom_sd` | 自定义神策产品节点 | 绿 | 修改 label 使用 |
| `custom_client` | 自定义客户系统节点 | 紫 | 修改 label 使用 |
| `custom_external` | 自定义外部系统节点 | 蓝 | 修改 label 使用 |

组件库不满足时，在节点中使用 `custom` 字段自定义：

```json
{
  "id": "system_a",
  "label": "System A\n(Integration Hub)",
  "custom": {"color": "client_system", "w": 200, "h": 80}
}
```

### arch.json 格式

```json
{
  "title": "图标题",
  "layout": "lr",
  "columns": [
    {
      "id": "col_sources",
      "label": "Data Sources",
      "container_style": "container",
      "nodes": [
        {"id": "crm", "label": "CRM System"},
        {"id": "miniprogram"},
        {"id": "pos", "future": true}
      ]
    },
    {
      "id": "col_cdp",
      "nodes": [{"id": "cdp"}]
    }
  ],
  "edges": [
    {
      "from": "crm", "to": "cdp",
      "style": "sftp_batch",
      "label": "MemberInfo [PII] / Transaction",
      "has_pii": true, "batch": true
    }
  ]
}
```

**edges 连线样式：**

| style | 颜色/线型 | 场景 |
|-------|---------|------|
| `sdk_realtime` | 红实线 | SDK 实时上报，含 PII |
| `sftp_batch` | 红虚线 | SFTP 批量传输 |
| `api_realtime` | 红实线 | HTTPS API 实时调用 |
| `kafka_async` | 蓝虚线 | Kafka 异步消费 |
| `internal_flow` | 绿实线 | 内部数据流（非 PII）|
| `config_flow` | 灰实线 | 配置/系统数据 |

`has_pii: true` → 红色；`batch: true` → 虚线；自动推断组合。

### Step 1：LLM 分析架构意图

收到用户描述后，先做以下分析再生成 arch.json：

1. **数据来源**：列举所有数据源（CRM/TAS/前端渠道等）
2. **中间层**：有无 ETL、中转系统、消息队列
3. **核心产品**：CDP / MAE / 仅 CDP
4. **下游系统**：邮件服务商、推送平台、用户
5. **非标结构**：与标准模板的差异点
6. **PII 流向**：哪些连线含 PII，哪些是批量

将分析结果用一段话回复确认，再生成 arch.json。

### Step 2：生成并运行

```bash
python3 $SKILL_REPO/draw-diagram/builder/diagram_builder.py \
  --arch $PROJECT_DIR/diagrams/arch.json \
  --output $PROJECT_DIR/diagrams/<图名>_<客户>.drawio
```

---

## 典型非标架构变体

### 变体 1：无 ETL，有统一中转系统

```
数据源 → System A（中转）→ CDP → MAE → 邮件 → 用户
前端渠道 → CDP（直接 SDK）
```

arch.json 差异：加入 `system_a` 自定义节点列，删除 `etl`，数据源连线指向 `system_a`。

### 变体 2：仅 CDP，无 MAE

```
数据源 → CDP → 业务用户（查询分析）
```

arch.json 差异：删除 `mae` 列和相关边，加入 `business_user`，CDP → business_user 用 `config_flow`。

### 变体 3：多区域，含大陆数据驻留

```
大陆用户 → CDP（HK）→ SFTP → ECS（SZ，大陆备份）
```

arch.json 差异：加入 `ecs_sz` 自定义节点（`custom_sd`），CDP → ecs_sz 用 `sftp_batch`，标注 "PIPL Daily Export [PII]"。

---

## 基础设施架构图（手动绘制）

基础设施架构图与云厂商强相关，不提供自动生成，在 draw.io 中手动绘制。

标准分区结构（阿里云）：
```
[互联网区]   DNS / GTM / CDN
[DMZ 区]     Cloud Firewall · WAF · ALB（公网）· SFTP Server · JumpHost
[应用区]     VPC
               ├── 公共子网：NAT Gateway / EIP
               ├── 应用子网：CDP 集群 / MAE 集群 / ETL 集群
               └── 数据子网：RDS（主备多可用区）
[DR 区域]    VPC（镜像，如 SG 区域）
[跨区域]     CEN（Cloud Enterprise Network）
[安全服务]   KMS · Anti-DDoS · SecurityCenter
```

绘制要点：用虚线框划定边界，标注流量路径，标注加密方式。
颜色规范：`$SKILL_REPO/draw-diagram/templates/DIAGRAM_GUIDE.md`

---

## 常见问题

**生成的图节点重叠：** 调整各列节点的 custom.w 统一宽度，或在 draw.io 中微调位置。

**CDP/MAE 内部子模块没有包含进大框：** 目前 builder 输出平铺布局，子模块需在 draw.io 中手动拖入容器。

**连线交叉太多：** 调整 columns 顺序，让主数据流尽量从左到右单向，避免回连。

**需要在 PPT 中使用：** draw.io → File → Export As → PNG（300dpi）或 SVG → 嵌入 PPT。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录。
