---
name: sd-tech-design
version: 0.3.0
description: 根据项目背景和需求，生成 LLD PPT 框架、架构图（draw.io XML）和 Technical Specification 文档
allowed-tools:
  - Bash
  - Read
  - Write
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
  _PROJECT_DIR="$(dirname "$_ENV_FILE")"
  [ -f "$_PROJECT_DIR/PROJECT.md" ] && echo "HAS_PROJECT_MD: yes" || echo "HAS_PROJECT_MD: no"
else
  _PROJECT_DIR="$(pwd)"
fi

echo "SKILL_REPO: ${_SKILL_REPO:-(未设置)}"
echo "ENV_FILE: ${_ENV_FILE:-none}"
echo "CLIENT: ${_CLIENT:-unknown}"
```

**Preamble 输出处理：**
- `SKILL_REPO` 含"未设置" → 停止，提示重新运行 `./setup`
- `HAS_PROJECT_MD: yes` → 读取 `PROJECT.md` 了解项目背景，避免重复询问已知信息

---

# 技术方案设计（LLD + Technical Specification）

## 背景知识

本 skill 覆盖三个核心交付物：

| 交付物 | 格式 | 用途 |
|--------|------|------|
| **LLD PPT** | PowerPoint（基于参考模板） | 客户架构评审、IT 治理审批 |
| **架构图** | draw.io XML | 嵌入 LLD PPT 或独立交付 |
| **Technical Specification** | Markdown / Word | 开发团队实施参考文档 |

**参考模板：**
```
$SKILL_REPO/refrences/Architecture Low-Level Design_TP1_CDP_MAE_20260414.pptx
```

---

## 执行阶段

### Phase 1：信息收集

读取 PROJECT.md（如有），补充收集以下信息：

| 类别 | 收集项 | 说明 |
|------|--------|------|
| 项目基本信息 | 项目名称、客户名、IT PM、技术负责人、目标上线日期 | 用于封面和 Project Related Data |
| 业务背景 | 客户现有系统现状、痛点、建设目标 | 用于 Section 1 |
| 服务范围 | 部署哪些产品（CDP/MAE/ETL）、数据分类、业务归属 | 用于 Section 2 |
| 系统组件 | 各组件 As-Is/To-be 状态 | 用于 Section 3.1 |
| 架构约束 | 云厂商、区域、网络隔离要求、跨境数据要求 | 用于 Section 3.5 |
| 用户类型 | 最终用户/业务用户/运维用户的访问方式 | 用于 Section 3.4 |
| 数据流 | 数据来源、采集方式（SDK/API/SFTP）、下游系统 | 用于 Section 3.6 |
| 加密要求 | 传输加密、静态加密、PII 处理方式 | 用于 Section 3.5.2 |
| 技术选型 | Buy/Build/Reuse 决策、部署平台、认证方式 | 用于 Section 4 |
| 资源规格 | 各环境（PRD/DR/UAT/DEV）节点数量 | 用于 Section 5.1 |
| 软件版本 | 各组件版本号 | 用于 Section 5.2 |
| 容量规划 | 日活、日事件量、性能指标要求 | 用于 Section 5.3 |
| 可用性要求 | HA 设计、扩容方式、RTO/RPO | 用于 Section 6/7 |
| 运维要求 | 监控指标、备份策略、维护窗口 | 用于 Section 8 |
| 接口系统 | 外部集成系统列表、接口方式、数据内容 | 用于 Section 9 |
| 安全合规 | 身份认证、数据安全、基础设施安全、合规要求 | 用于 Section 10 |
| 假设与前提 | 已知假设、前置条件、待确认事项 | 用于 Section 11 |

**信息不完整时的处理原则：**
- 有明确标准答案的（如神策软件版本）→ 直接填入，标注"待客户确认"
- 客户特定信息（如节点 IP、项目 PM）→ 留占位符 `<TBD>`
- 架构决策类（如加密方案）→ 先给出推荐方案，说明理由，请客户确认

---

### Phase 2：生成 LLD PPT 框架（Markdown 结构）

**工作方式：先输出完整框架，逐节确认后填充内容。**

按以下章节结构输出 LLD 框架，每节包含：标题、内容摘要、待填充的关键信息点。

#### LLD 完整章节结构

```
封面
  - 项目名称（含产品缩写，如 CDP and MAE）
  - 文档类型：Architecture Design Document – Low-Level Design (LLD)

Project Related Data
  - Project Name / IT PM / Technical Lead / ETA / Go-Live / Justification

1. Project Background and Objectives
  1.1 Project Background（现状痛点 + 建设目标 + 委托背景）
  1.2 Project Scope & Objectives（表格：领域/目标/成果）

2. Services Offering
  - Major Functions / Importance / Data Classification / Business Service / Service Group / Business Owner

3. System Architecture
  3.1 Major System/Logical Components（表格：组件/关键功能/As-Is/To-be/Action）
  3.3 Logical Architecture Diagram
      - 架构图（draw.io）
      - Scenario 说明（每个数据流场景 A/B/C/D/E...）
  3.4 System Flow（按用户类型分页）
      - End User 视角（图 + 文字说明）
      - Business User 视角（图 + 文字说明）
      - Maintenance User 视角（图 + 文字说明）
  3.5.1 Infrastructure Architecture Diagram
      - 云架构图（draw.io，含 VPC/子网/安全组件/流量路径）
      - 流量说明（各类用户流量路径）
      - 云组件说明表（组件/关键功能）
  3.5.2 Data Encryption
      - 临时方案（Temporary Solution）
      - 中期方案（Mid-term Solution）
      - 治理要求
  3.6 Data Flow
      - CDP 数据流图（draw.io）+ 说明
      - MAE 数据流图（draw.io）+ 说明

4. Technical Methodologies
  4.1 Reuse/Buy/Build Decision（表格：决策/组件/理由）
  4.2 Deployment/Platform Selection（表格：组件/部署位置/平台/理由）
  4.3 User Authentication（表格：组件/方案/理由）
  4.4 New Technology（表格：考虑事项/当前方案）
  4.5 Non-standard Design（表格：标准设计/非标设计/理由/补救措施）

5. System Resource Requirements
  5.1 Hardware Resource List
      - 计算节点（CDP/MAE/ETL/SFTP/JumpHost/RDS）× 各环境数量
      - 网络/安全组件（LB/GTM/DNS/WAF/Firewall/NAT/CEN/VPN/CDN/OSS/KMS）
  5.2 Software Resource List（表格：组件/厂商/版本/说明）
  5.3 Capacity and Sizing Estimation
      - CDP 性能指标（响应时间/处理速度/准确率/资源利用率）
      - MAE 性能指标（发送速度/执行时间/准确率）
      - 当前配置支撑规模说明

6. Availability and Scalability
  6.1 High Availability（表格：组件/HA 设计）
  6.2 Scalability（表格：组件/水平扩展/垂直扩展）
  注：说明 3 节点 → 3+N 架构扩容路径和数据迁移要求

7. Service Level Agreement
  7.1 System Recovery Objectives（表格：组件/RTO/RPO/可用性）
  7.2 Batch Processing（批处理窗口/输出要求/检查点机制）

8. Operational Requirements
  8.1 System Monitoring（表格：组件/监控指标/工具/方案）
  8.2 System/Data Backup（表格：组件/频率/保留期/方式）
  8.3 Maintenance Hour（各方维护窗口）
  8.4 Data Security（中期安全改造计划）

9. Major Interfaced Systems
  表格：接口系统/接口目的/触发方/接口方式/关键数据/关联动作

10. Technology Risk Management
  10.1 Identity & Access Security（IAM/特权账号/审计日志）
  10.2 Data Security（传输加密/静态加密/DLP）
  10.3 Infrastructure Security（系统加固/网络访问控制/IDS/移动安全）
  10.4 Application Security（数据加密/WAF/DevSecOps）
  10.5 SOC（SIEM 集成/漏洞扫描）
  10.6 Compliance（监管要求/PIA/SRAA）

11. Assumptions, Pre-requisites and Notes
  11.1 Assumptions
  11.2 Pre-requisites
  11.3 Notes

Appendix
  - Major System/Logical Components 详细子组件
  - DB Components
  - CDP & MAE System Overview Description
  - Cloud Infrastructure Architecture 补充说明
  - 加密方案补充
```

---

### Phase 3：架构图生成（draw.io）

**使用模板快速生成，不从零手写 XML。**

#### 3.1 准备客户配置文件

在项目目录创建 `diagram_config.json`，填写客户专有名词：

```json
{
  "CLIENT": "客户简称",
  "CLIENT_SYSTEMS": "客户系统总称（如 ACME Systems）",
  "BUSINESS_USER": "业务用户称呼（如 ACME Employee）",
  "EMAIL_SERVICE": "邮件服务商（如 SendCloud / Mailchimp）",
  "FRONTEND_1": "主要前端渠道（如 Mini-Program）",
  "FRONTEND_2": "次要前端渠道（如 Website）",
  "FRONTEND_3": "第三前端渠道（如 Mobile App）",
  "FRONTEND_4": "其他渠道（如 Other Channels）",
  "SOCIAL_MEDIA": "社交媒体平台名称",
  "SYSTEM_1": "核心业务系统1（如 CRM / Ticketing System）",
  "SYSTEM_2": "核心业务系统2（如 ERP / Business Data）",
  "SYSTEM_3": "核心业务系统3（如 CRM）",
  "SYSTEM_4": "Future 系统1（如 RSVP）",
  "SYSTEM_5": "Future 系统2（如 Retail System）",
  "SYSTEM_6": "Future 系统3（如 POS）",
  "SYSTEM_7": "Future 系统4",
  "SYSTEM_8": "Future 系统5"
}
```

#### 3.2 运行生成脚本

```bash
python3 $SKILL_REPO/tech-design/diagram-templates/gen_diagrams.py \
  --config diagram_config.json \
  --output $PROJECT_DIR/tech-design/diagrams/
```

一次生成 6 个文件：

| 文件 | 用途 | LLD 章节 |
|------|------|---------|
| `Logical_Architecture_<客户>.drawio` | 系统组件逻辑关系 | Section 3.3 |
| `Data_Flow_<客户>.drawio` | CDP & MAE 数据流（含 PII 标注） | Section 3.6 |
| `System_Flow_EndUser_<客户>.drawio` | 最终用户视角系统流 | Section 3.4 |
| `System_Flow_Employee_<客户>.drawio` | 业务用户视角系统流 | Section 3.4 |
| `System_Flow_Maintenance_<客户>.drawio` | 运维用户视角系统流 | Section 3.4 |
| `Functional_Architecture_<客户>.drawio` | 系统内部功能模块详图 | Appendix |

#### 3.3 生成后必做的调整

生成的文件是 Westk 结构的通用化版本，需要根据客户实际情况调整：

**必须调整：**
- 删除客户不涉及的 Future 节点（灰色虚线节点）
- 修改连线标签（数据字段名、协议、频率）
- 更新地域标注（HK/SZ → 客户实际云区域）
- 调整 Data Flow 图中的 PIPL/数据驻留标注（按客户合规要求）

**可选调整：**
- 增加客户特有的系统节点
- 调整 CDP/MAE 内部模块（如客户不用 MAE，删除 MAE 相关节点）
- 修改 Legend 中的颜色说明文字

**设计规范参考：**
```
$SKILL_REPO/tech-design/diagram-templates/DIAGRAM_GUIDE.md
```

#### 3.4 基础设施架构图（Infrastructure Architecture）

基础设施架构图（Section 3.5.1）与云厂商强相关，**不提供通用模板**，需根据客户云环境从头绘制。

标准分区结构（以阿里云为例）：
```
[互联网区]
  DNS / GTM / CDN

[DMZ 区]
  Cloud Firewall / WAF / ALB（公网）
  SFTP Server / JumpHost

[应用区 - 主区域]
  VPC
  ├── 公共子网：NAT Gateway / EIP
  ├── 应用子网：CDP 集群 / MAE 集群 / ETL 集群
  └── 数据子网：RDS（主备多可用区）

[DR 区域]
  VPC（镜像结构）

[跨区域连接]
  CEN / VPN

[安全服务]
  KMS / Anti-DDoS / SecurityCenter
```

绘制要点：
- 用虚线框划定 VPC 和子网边界
- 用不同颜色区分 DMZ / 应用区 / 数据区
- 标注流量路径（HK 用户流量 / 大陆用户流量 / 运维流量）
- 标注加密方式（HTTPS / VPC Traffic Encryption / TLS）

---

### Phase 4：Technical Specification 文档生成

**在 LLD PPT 框架确认后，生成对应的 Technical Specification Markdown 文档。**

Tech Spec 是 LLD 的技术实施细化版本，面向开发和运维团队，包含 LLD 中没有的实施细节。

#### Tech Spec 与 LLD 的关系

| LLD（客户审批用） | Tech Spec（实施参考用） |
|-----------------|----------------------|
| 架构决策和理由 | 具体配置参数和命令 |
| 组件列表和版本 | 安装步骤和依赖关系 |
| 性能指标要求 | 调优参数和基准测试方法 |
| 安全要求 | 具体安全配置（防火墙规则、加密密钥管理） |
| 接口系统列表 | API 端点、认证方式、数据格式 |
| 运维要求 | 监控告警规则、备份脚本、故障处理流程 |

#### Tech Spec 章节结构

```markdown
# [项目名] Technical Specification

**版本：** vX.X
**日期：** YYYY-MM-DD
**基于 LLD 版本：** vX.X（YYYY-MM-DD）

## 1. 文档目的与范围

## 2. 系统组件详细规格
  ### 2.1 CDP 集群
    - 节点规格（CPU/内存/磁盘）
    - 操作系统和内核版本
    - 网络配置（IP 段、安全组规则）
  ### 2.2 MAE 集群
  ### 2.3 ETL 集群
  ### 2.4 数据库（RDS）
  ### 2.5 网络组件（LB/WAF/Firewall）

## 3. 数据采集规格
  ### 3.1 SDK 集成规格（前端）
    - SDK 版本、初始化参数
    - 事件命名规范
    - 用户标识规范（ID 类型优先级）
  ### 3.2 API 集成规格（后端）
    - 端点地址、认证方式
    - 请求格式、字段映射
    - 错误处理和重试策略
  ### 3.3 SFTP 批量导入规格
    - 文件格式、字段定义
    - 传输时间窗口、文件命名规范
    - 数据质量校验规则

## 4. 身份解析规格
  - ID 类型定义和优先级
  - 合并规则和冲突处理
  - 隐私合规处理（匿名化、删除）

## 5. 数据加密实施规格
  ### 5.1 传输加密
    - TLS 版本要求
    - 证书管理（颁发机构、轮换周期）
    - VPC 内部加密配置
  ### 5.2 静态加密
    - PII 字段清单（需加密的字段列表）
    - 加密算法（AES-256）和密钥管理（KMS）
    - 豁免字段清单及理由（需正式审批）

## 6. 接口规格
  ### 6.x [接口系统名]
    - 接口方式（API/SDK/SFTP）
    - 认证方式
    - 数据格式和字段映射
    - 频率限制和错误处理

## 7. 安全配置规格
  ### 7.1 网络访问控制
    - 安全组规则（入站/出站）
    - IP 白名单
    - WAF 规则集
  ### 7.2 身份认证
    - SSO 配置（Azure AD / Entra ID）
    - 角色权限矩阵
  ### 7.3 审计日志
    - 日志类型和保留策略
    - SIEM 集成配置

## 8. 监控告警规格
  - 监控指标清单（含阈值）
  - 告警规则和通知渠道
  - Dashboard 配置

## 9. 备份与恢复规格
  - 备份策略（频率/保留期/存储位置）
  - 恢复流程（RTO/RPO 验证步骤）
  - DR 切换操作手册

## 10. 部署流程
  - 环境准备检查清单
  - 部署顺序（依赖关系）
  - 验证测试步骤

## 11. 已知限制和风险
  - 当前方案的技术限制
  - 待解决的技术债务
  - 升级路径

## Appendix
  - 配置文件模板
  - 网络拓扑详图
  - 数据字典
```

---

### Phase 5：输出与交付

**输出顺序：**

1. **LLD 框架确认**（Markdown 格式，逐节列出待填内容）
   → 用户确认框架结构和各节重点

2. **逐节填充 LLD 内容**
   → 每次填充 2-3 节，用户 review 后继续

3. **架构图生成**（draw.io XML）
   → 输出可导入 draw.io 的 XML 文件
   → 说明图中各元素含义和需要客户确认的部分

4. **Tech Spec 生成**（Markdown）
   → 基于已确认的 LLD 内容生成
   → 标注需要实施团队补充的技术细节

**文件输出位置：**
```bash
# LLD 内容（Markdown，用于转换为 PPT）
$PROJECT_DIR/tech-design/LLD_<客户名>_<版本>_<日期>.md

# 架构图 XML
$PROJECT_DIR/tech-design/diagrams/logical_architecture.xml
$PROJECT_DIR/tech-design/diagrams/infrastructure_architecture.xml
$PROJECT_DIR/tech-design/diagrams/data_flow_cdp.xml
$PROJECT_DIR/tech-design/diagrams/data_flow_mae.xml

# Technical Specification
$PROJECT_DIR/tech-design/TechSpec_<客户名>_<版本>_<日期>.md
```

---

## 关键设计原则

### 1. 非标设计必须显式记录

任何偏离标准设计的决策，必须在 Section 4.5 Non-standard Design 中记录：
- 标准设计是什么
- 非标设计是什么
- 为什么这样做（业务/技术理由）
- 补救措施（如何降低风险）

### 2. 加密方案分阶段处理

神策当前版本的端到端应用层加密有限制，标准处理方式：
- **临时方案**：HTTPS/TLS 全链路 + VPC 内部加密
- **中期方案**：应用层 PII 字段 AES-256 加密 + 非 PII 字段豁免（需正式审批）
- **豁免字段**：必须文档化，列明字段名、理由、审批人

### 3. 扩容路径必须说明

Section 6.2 必须说明：
- 当前 3 节点集群的扩容上限（5 节点）
- 超过 5 节点后的 3+N 架构迁移路径
- 数据迁移成本和停机时间估算

### 4. 多环境资源表必须完整

Section 5.1 必须覆盖 PRD / DR / UAT / DEV 四个环境，DR 环境的资源配置不能遗漏。

### 5. 合规要求按客户所在地区填写

Section 10.6 的监管要求根据客户业务地区选择：
- 香港：PDPO（Cap. 486）
- 中国大陆：PIPL / CSL / DSL
- 欧盟：GDPR
- 跨境数据：同时适用多个法规时全部列出

---

## 常见问题

**客户不提供节点 IP 等具体信息：**
在 Section 5.1 填写节点数量，IP 等信息留 `<TBD>`，在 Section 11.2 Pre-requisites 中列为前置条件。

**客户要求简化 LLD（不需要所有章节）：**
核心章节不可省略：Section 1/2/3/5/6/7/10/11。可以合并或简化的：Section 4（技术选型简单时）、Section 8（运维要求由厂商负责时）。

**架构图客户要求用 PPT 内嵌图而非 draw.io：**
先输出 draw.io XML，客户在 draw.io 中调整后导出为 PNG/SVG，再嵌入 PPT。

**Tech Spec 和 LLD 内容重复：**
LLD 写"做什么和为什么"，Tech Spec 写"怎么做"。重复的部分在 Tech Spec 中用"参见 LLD Section X.X"引用，不重复写。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录，无需中断当前工作。
