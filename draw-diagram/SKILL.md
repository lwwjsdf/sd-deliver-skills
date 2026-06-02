---
name: sd-draw-diagram
version: 0.1.0
description: 为神策 CDP & MAE 项目生成 draw.io 架构图，基于 Westk TP1 实战模板，支持逻辑架构图、数据流图、系统流图、功能架构图
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

## 可生成的图类型

| 图类型 | 文件名 | 用途 | LLD 章节 |
|--------|--------|------|---------|
| 逻辑架构图 | `Logical_Architecture_<客户>.drawio` | 系统组件逻辑关系 | Section 3.3 |
| 数据流图 | `Data_Flow_<客户>.drawio` | CDP & MAE 数据流，含 PII 标注 | Section 3.6 |
| 系统流图（终端用户） | `System_Flow_EndUser_<客户>.drawio` | 最终用户视角 | Section 3.4 |
| 系统流图（业务用户） | `System_Flow_Employee_<客户>.drawio` | 业务用户视角 | Section 3.4 |
| 系统流图（运维用户） | `System_Flow_Maintenance_<客户>.drawio` | 运维/维护用户视角 | Section 3.4 |
| 功能架构图 | `Functional_Architecture_<客户>.drawio` | 系统内部功能模块详图 | Appendix |

一次全部生成（推荐），或按需指定单张。

---

## 执行流程

### Step 1：收集客户信息

询问或从 PROJECT.md 读取以下映射关系，填入配置文件：

```json
{
  "CLIENT": "客户简称，如 ACME",
  "CLIENT_SYSTEMS": "客户系统总称，如 ACME Systems",
  "BUSINESS_USER": "业务用户称呼，如 ACME Employee",
  "EMAIL_SERVICE": "邮件/消息服务商，如 SendCloud",
  "FRONTEND_1": "主要前端渠道，如 Mini-Program",
  "FRONTEND_2": "次要前端渠道，如 Website",
  "FRONTEND_3": "第三前端渠道，如 Mobile App",
  "FRONTEND_4": "其他渠道，如 Other Channels",
  "SOCIAL_MEDIA": "社交媒体平台，如 Social Media",
  "SYSTEM_1": "核心业务系统1，如 CRM",
  "SYSTEM_2": "核心业务系统2，如 Ticketing System",
  "SYSTEM_3": "核心业务系统3，如 ERP",
  "SYSTEM_4": "Future 系统1，如 RSVP",
  "SYSTEM_5": "Future 系统2，如 Retail System",
  "SYSTEM_6": "Future 系统3，如 POS",
  "SYSTEM_7": "Future 系统4",
  "SYSTEM_8": "Future 系统5"
}
```

**信息不完整时：**
- 已知的填写，不确定的用合理默认值
- Future 系统（SYSTEM_4-8）如果客户没有，填 `<TBD>` 后在图中删除灰色虚线节点

### Step 2：生成配置文件并运行脚本

```bash
# 将配置写入项目目录
cat > $PROJECT_DIR/diagrams/diagram_config.json << 'EOF'
{ ...客户配置... }
EOF

# 生成所有图
python3 $SKILL_REPO/draw-diagram/templates/gen_diagrams.py \
  --config $PROJECT_DIR/diagrams/diagram_config.json \
  --output $PROJECT_DIR/diagrams/
```

### Step 3：告知后续调整事项

生成完成后，提示用户在 draw.io 中完成以下调整：

**必须调整（影响准确性）：**
- 删除客户不涉及的 Future 节点（灰色虚线节点）
- 修改连线标签：数据字段名、传输协议、频率（如 `SFTP Batch (daily, T+1)`）
- 更新地域标注：将 HK/SZ 替换为客户实际云区域

**按合规要求调整：**
- Data Flow 图中的 PIPL/数据驻留标注（非中国大陆客户可删除）
- 跨境数据流的标注

**可选调整：**
- 增加客户特有系统节点
- 如客户不用 MAE，删除 MAE 相关节点和连线
- 修改 Legend 颜色说明文字（如更换了 SendCloud 为其他服务商）

---

## 基础设施架构图（手动绘制）

基础设施架构图（LLD Section 3.5.1）与云厂商强相关，**不提供通用模板**，需在 draw.io 中按以下结构从头绘制。

### 标准分区结构

**阿里云：**
```
[互联网区]  DNS / GTM / CDN
[DMZ 区]    Cloud Firewall · WAF · ALB（公网）· SFTP Server · JumpHost
[应用区]    VPC
              ├── 公共子网：NAT Gateway / EIP
              ├── 应用子网：CDP 集群 / MAE 集群 / ETL 集群
              └── 数据子网：RDS（主备多可用区）
[DR 区域]   VPC（镜像结构，如 SG）
[跨区域]    CEN（Cloud Enterprise Network）
[安全服务]  KMS · Anti-DDoS · SecurityCenter
```

**其他云厂商参照此结构，替换对应服务名称。**

### 绘制要点
- 用虚线框划定 VPC 和子网边界
- 标注流量路径（终端用户流量 / 运维流量，区分颜色）
- 标注加密方式（HTTPS / VPC Traffic Encryption / TLS）
- 参考颜色规范：`$SKILL_REPO/draw-diagram/templates/DIAGRAM_GUIDE.md`

---

## 设计规范

完整的颜色规范、连线语义、图层结构、节点命名规范见：

```
$SKILL_REPO/draw-diagram/templates/DIAGRAM_GUIDE.md
```

核心规则速查：

| 节点颜色 | 含义 |
|---------|------|
| 绿色 `#d5e8d4` | 神策产品（CDP / MAE / ETL / SDK） |
| 紫色 `#e1d5e7` | 客户系统（CRM / 票务 / 业务系统） |
| 蓝色 `#dae8fc` | 外部 SaaS（SendCloud / 第三方 API） |
| 黄色 `#fff2cc` | 内部功能模块（C1-C9 组件） |
| 灰色虚线 `#f5f5f5` | Future Scope（Day 2+ 规划） |

| 连线颜色 | 含义 |
|---------|------|
| 红色实线 | 含 PII / 敏感数据的实时流 |
| 红色虚线 | 含 PII / 敏感数据的批量流 |
| 绿色实线 | 内部数据流（非 PII） |
| 蓝色虚线 | Kafka 异步管道 |
| 灰色虚线 | Future 数据流 |

---

## 常见问题

**客户没有 MAE，只有 CDP：**
生成所有图后，在 draw.io 中删除 MAE 大框及相关连线即可，不需要修改配置。

**客户有多个邮件服务商（如 SendCloud + 自建）：**
先用 `EMAIL_SERVICE=SendCloud` 生成，再手动在 draw.io 中复制节点并修改标签。

**图太复杂客户看不懂：**
准备两个版本：完整版（用于技术评审）+ 简化版（仅保留主干流程，用于业务汇报）。简化版从完整版复制后删减。

**需要在 PPT 中嵌入：**
draw.io 中调整完毕后，File → Export As → PNG（300dpi）或 SVG，嵌入 PPT。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录。
