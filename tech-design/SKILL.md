---
name: sd-tech-design
version: 0.5.0
description: 根据项目背景和需求，生成 LLD PPT 框架、架构图（draw.io）和 Technical Specification 文档
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
- `HAS_PROJECT_MD: yes` → 读取 `PROJECT.md` 了解项目背景，避免重复询问

---

# 技术方案设计（LLD + Technical Specification）

## 概览

本 skill 覆盖三个核心交付物，按顺序生成：

```
Phase 1：信息收集
    ↓
Phase 2：LLD PPT 框架（先出骨架，逐节填充）
    ↓
Phase 3：架构图（draw.io，基于模板生成）
    ↓
Phase 4：Technical Specification（基于已确认的 LLD 生成）
```

| 交付物 | 格式 | 面向对象 | 参考模板 |
|--------|------|---------|---------|
| LLD PPT | PowerPoint | 客户 IT 治理审批 | `$SKILL_REPO/refrences/Architecture Low-Level Design_TP1_CDP_MAE_20260414.pptx` |
| 架构图 | draw.io XML | LLD 内嵌 / 独立交付 | `$SKILL_REPO/tech-design/diagram-templates/` |
| Tech Spec | Word / Markdown | 开发团队实施参考 | `$SKILL_REPO/refrences/TP1_Technical Specification_V1.0.docx` |

**LLD 与 Tech Spec 的根本区别：**
- LLD 写**做什么和为什么**（架构决策、选型理由、合规要求）
- Tech Spec 写**怎么做**（端口号、命令、配置参数、操作流程）
- Tech Spec 内容从 LLD 派生，不独立收集信息；LLD 未覆盖的实施细节在 Tech Spec 中补充

---

## 执行阶段

### Phase 1：信息收集

读取 PROJECT.md（如有），补充收集以下信息。信息收集分两组：**LLD 所需**（必须在 Phase 2 前完成）和 **Tech Spec 补充**（Phase 4 前补充）。

#### LLD 所需信息

| 类别 | 收集项 | 对应 LLD 章节 |
|------|--------|-------------|
| 项目基本信息 | 项目名称、客户名、IT PM、技术负责人、目标上线日期 | 封面 + Project Related Data |
| 业务背景 | 现有系统现状、痛点、建设目标、委托背景 | Section 1 |
| 服务范围 | 部署产品（CDP/MAE/ETL）、数据分类、业务归属部门 | Section 2 |
| 系统组件 | 各组件 As-Is/To-be 状态 | Section 3.1 |
| 架构约束 | 云厂商、部署区域、跨境数据要求、网络隔离要求 | Section 3.5.1 |
| 用户类型 | 最终用户/业务用户/运维用户的访问路径 | Section 3.4 |
| 数据来源 | 数据来源系统、采集方式（SDK/API/SFTP）、是否含 PII | Section 3.6 |
| 加密要求 | 传输加密方案、静态加密方案、PII 字段处理方式 | Section 3.5.2 |
| 技术选型 | Buy/Build/Reuse 决策、部署平台、身份认证方式（SSO） | Section 4 |
| 资源规格 | 各环境（PRD/DR/UAT/DEV）节点数量 | Section 5.1 |
| 软件版本 | CDP/MAE/Kafka/MySQL 等各组件版本号 | Section 5.2 |
| 容量规划 | 日活、日事件量、性能指标要求（响应时间/吞吐量） | Section 5.3 |
| 可用性 | HA 设计、扩容方式、RTO/RPO 目标 | Section 6/7 |
| 运维要求 | 监控工具、备份频率和保留期、维护窗口 | Section 8 |
| 接口系统 | 外部集成系统列表、接口方式、传输的关键数据 | Section 9 |
| 安全合规 | IAM 方案、数据安全要求、适用法规 | Section 10 |
| 假设与前提 | 已知假设、前置条件、待确认事项 | Section 11 |

#### Tech Spec 补充信息（Phase 4 前收集）

| 类别 | 收集项 |
|------|--------|
| 数据量估算 | DAU/日事件量/历史数据量/预期增长率 |
| 接口参数 | SFTP 路径、API 端点、文件格式、GPG 密钥管理方式 |
| 加密实施细节 | PII 字段清单、豁免字段清单及审批人、DEK 轮换策略 |
| 数据转换 | CRM 各表同步策略（全量/增量）、ETL 时间窗口 |
| 数据保留 | 每类数据的在线保留期和归档/清理方式 |
| DR 细节 | DR 触发条件、恢复顺序、演练频率和参与人 |

**信息不完整时的处理原则：**
- 有神策标准答案的（软件版本、默认端口）→ 直接填入，标注"待客户确认"
- 客户特定信息（节点 IP、PM 姓名）→ 留占位符 `<TBD>`
- 架构决策类（加密方案、DR 模式）→ 给出推荐方案和理由，请客户确认

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

**在 LLD PPT 框架确认后，生成对应的 Technical Specification Word 文档。**

Tech Spec 是 LLD 的技术实施细化版本，面向开发和运维团队。

#### LLD 与 Tech Spec 的精确分工

基于 Westk TP1 实战经验，两份文档的内容边界如下：

| 章节 | LLD 写什么 | Tech Spec 写什么 |
|------|-----------|----------------|
| 加密方案 | 临时/中期方案决策、AES-256 + KMS 选型理由 | DEK 存储格式（`<version>::<IV>::<ciphertext>`）、RAM 角色权限配置、加密/解密点（含端口号）、异常处理流程 |
| 数据流 | 架构图 + Scenario A-E 场景描述 | 接口目录（INT-ID/协议/频率/触发时间/字段清单）、PII 标注 |
| 备份恢复 | RTO/RPO 数字、备份频率 | 8步恢复流程、各组件恢复时间估算、DR 演练计划、合规标准（如 GB/T 20988-2007）对照表 |
| 数据保留 | 无（LLD 不涉及） | 每类数据的在线保留期和清理方式（完整表格） |
| 性能 | 指标要求（响应时间/吞吐量） | ALB 监听规则（端口/调度算法）、加密方案查询性能对比测试结果 |
| 系统组件 | 组件列表（C1-C9）+ 关键功能 | 每个组件的子模块、技术实现（如 Flink/Netty/Kafka 的具体用途） |
| 数据转换 | 无（LLD 不涉及） | CRM 七张表的同步策略（Override/Delta append）、ETL 处理时间窗口、文件格式规范 |
| 安全配置 | 安全要求和合规框架 | Nginx TLS 配置要求（密钥长度/有效期/禁用密码套件/HSTS）、VPC 流量加密实施步骤 |

#### Tech Spec 完整章节结构

基于 Westk TP1 实战版本：

```
封面 + 版本历史

1. Introduction
   1.1 Document Purpose（文档目的：作为实施蓝图，确保各方共同理解）

2. Solution Description
   2.1 Platform Capabilities Overview（能力域表格：Portal/数据接入/身份解析/分群/活动/渠道/旅程）
   2.2 Integration with External Systems（PoC 阶段已完成的集成清单）
   2.3 Data Sources & Channel Rollout Plan（数据源表 + 触达渠道表，含上线时间）

3. Solution Design Principle
   3.1 Design Considerations
       3.1.1 Scalability（水平扩展/HA/负载均衡 + ALB 监听规则表）
       3.1.2 Extensibility（4种集成模式：API/SFTP/SDK/Webhook）
       3.1.3 Performance（批处理/实时查询/QPS 限速）
       3.1.4 Upgradability（产品原生方法/配置优于定制/依赖管理）
       3.1.5 Security
           3.1.5.1 Data Encryption Strategy（加密原则 + CDP 功能影响评估表）
           3.1.5.2 Encryption Architecture（KMS 信封加密 + 密钥层级表 + DEK 存储格式）
           3.1.5.3 Encryption and Decryption Points（加密点表 + 解密点表 + IAM 角色配置表）
           3.1.5.4 ID-Mapping Field Treatment（哈希 + 加密双重方法）
           3.1.5.5 Exception Handling（异常场景处理表）
           3.1.5.6 Compliance Position
   3.2 Assumptions（数据量估算 + 资源供应 + 外部系统假设）
   3.3 Constraints（网络/存储/外部依赖/安全约束）

4. Business Architecture Design
   4.1 Business Capability / Functions（业务能力矩阵：能力/描述/对应平台功能/对应业务目标）
   4.2 Business Process Diagrams（Scenario A/B/C/D 详细描述）
   4.3 System Flow - End User（9步流程）
   4.4 System Flow - Business User
   4.5 Solution Design for Data Encryption
       4.5.1 Background & Goal
       4.5.2 Query Performance Comparison（三种加密方案对比表）
       4.5.3 Real-World Performance（实测数据）
       4.5.4 Actual Business Impact by Functional Module（各模块影响表）
   4.6 Security Architecture Design
       4.6.1 Nginx HTTP → HTTPS Migration（实施步骤表 + 性能影响）
       4.6.2 VPC Traffic Encryption Solution（两层加密架构 + 实施步骤表）
   4.7 Application-Level Field Encryption（批量/实时加密模块详细流程）

5. Components Catalogue
   5.1 Core CDP Layer（Portal/数据接入/身份解析/分群/分析 详细描述）
   5.2 Core MAE Layer（活动规划/旅程编排/渠道管理 详细描述）

6. Logical Architecture Design
   6.1 Logical Architecture Diagram（引用图）
   6.2 Components（每个组件的技术实现细节）
       6.2.1 Portal（SSO + RBAC）
       6.2.2 Data Ingestion & ETL（Nginx + Edge + Flink + Kafka 四子组件）
       6.2.3 Identity Resolution（跨渠道 ID 映射规则）
       6.2.4 Segmentation & Tagging（多条件组合 + 自动标签触发规则）
       6.2.5 Analytics & Dashboard（10种分析模型）
       6.2.6 Campaign Planning（时间触发 + 事件触发两种模式）
       6.2.7 Journey Orchestration（触发判断/定时控制/DND/重入控制）
       6.2.8 Channel Management（预设渠道 + Webhook 自定义渠道）

7. Data Architecture Design
   7.1 Application Data Flow Diagram（接口表：源/目标/方法/协议/实时批量/数据类型/PII字段）
   7.2 Data Specification（数据模型字段映射，引用 Tracking Plan）
   7.3 Data Retention and Archive（完整数据保留表：每类数据/在线保留期/清理方式）

8. Backup and Restore
   8.1 Backup
       8.1.1 Regular Backup（CDP Image Backup + MAE DTS 跨区域同步）
           - 备份范围表（Kafka/Kudu/HDFS/SKV/MySQL/系统级）
           - 备份保留策略表（每日/每周/每月/最新）
           - 备份传输机制
           - 备份验证和失败处理
       8.1.2 Backup Component Summary（汇总表：组件/方法/频率/RPO/存储位置）
   8.2 Restore
       8.2.1 DR 模式（冷备 vs 热备对比表 + 选择理由）
       8.2.2 RTO/RPO Targets（含 GB/T 20988-2007 合规性对照表）
       8.2.3 Disaster Scenario Definition（触发条件 + 范围外说明）
       8.2.4 Restore Procedure（8步顺序流程 + CDP 各组件恢复时间表）
       8.2.5 Recovery Time Breakdown（各阶段时间估算表）
       8.2.6 Failback Procedure（回切步骤 + 预计时间）
       8.2.7 DR Drill Plan（演练频率/范围/环境/参与人）
       8.2.8 Constraints and Risk Factors（风险/影响/缓解措施表）

9. Data Conversion Architecture
   9.1 Inclusion（CRM 七张表同步策略表 + SDK 实时采集 + 大陆数据导出）
   9.2 Exclusion（PII 最小化原则 + 排除的数据类型）
   9.3 Conversion Approach（ETL 时间窗口/文件格式/加密流程/错误处理）

10. Interface Catalogue
    接口表（INT-ID/标题/描述/发送方/接收方/触发/频率/接口方式/关键数据）

11. Cloud Infrastructure Design
    （云资源拓扑、VPC 配置、安全组规则等）

Appendix
    - Annex 1: Glossary（术语表）
    - Annex 2: Reference Documents
    - Annex 3: Tracking Plan（数据字典，字段映射详情）
```

#### 生成 Tech Spec 的工作流

1. **从 LLD 直接复用的内容**（不需要重写，引用或简化）：
   - Section 1 背景目标 → Tech Spec Chapter 1/2
   - Section 3.1 组件表 → Tech Spec Chapter 5
   - Section 3.3 逻辑架构图 → Tech Spec Chapter 6.1
   - Section 3.6 数据流 → Tech Spec Chapter 7.1（补充接口 ID 和字段）
   - Section 5.1 硬件资源表 → Tech Spec Chapter 11
   - Section 6/7 HA/SLA → Tech Spec Chapter 8.2.2

2. **Tech Spec 独有内容**（需要额外收集信息）：
   - 加密实施细节（DEK 格式、端口号、RAM 角色）
   - 数据保留策略（每类数据的具体保留期）
   - 接口目录（INT-ID 编号、触发时间、文件格式）
   - DR 恢复流程（8步流程、各组件恢复时间）
   - 数据转换架构（CRM 表同步策略、ETL 时间窗口）
   - 业务能力矩阵（能力/功能/业务目标对应关系）

3. **需要客户/实施团队确认的内容**：
   - 数据量估算（DAU/日事件量/历史数据量）
   - 外部系统接口参数（SFTP 路径、API 端点、GPG 密钥管理方式）
   - 合规标准（适用的法规：PDPO/PIPL/GDPR/GB/T 20988）
   - DR 演练计划（频率、参与人）

---

---

## 关键设计原则（所有 Phase 通用）

执行任何 Phase 时，以下原则优先级高于具体步骤。

### 1. 非标设计必须显式记录（LLD Section 4.5）

任何偏离标准设计的决策，必须在 Section 4.5 Non-standard Design 中记录四项：标准设计是什么、非标设计是什么、为什么这样做、补救措施。

### 2. 加密方案分阶段处理

神策应用层端到端加密有版本限制，标准分两阶段：
- **临时方案**：HTTPS/TLS 全链路 + VPC 内部加密（立即可用）
- **中期方案**：PII 字段 AES-256-GCM + KMS 信封加密；非 PII 字段豁免需正式审批并文档化

豁免字段必须列明：字段名、理由、审批人。这是合规审查的核心材料。

### 3. 扩容路径必须说明（LLD Section 6.2）

- 当前 3 节点集群上限：5 节点（水平扩展）
- 超过 5 节点：需迁移至 3+N 架构（3 元数据节点 + N 数据节点），有数据迁移成本
- 必须在文档中说明迁移触发条件和预估停机时间

### 4. 多环境资源表必须完整（LLD Section 5.1）

PRD / DR / UAT / DEV 四个环境都要填，DR 环境节点数不能遗漏。

### 5. 合规要求按客户所在地区填写（LLD Section 10.6）

| 地区 | 适用法规 |
|------|---------|
| 香港 | PDPO（Cap. 486） |
| 中国大陆 | PIPL / CSL / DSL |
| 欧盟 | GDPR |
| 跨境数据 | 以上全部列出 |

---

## 输出文件规范

```bash
$PROJECT_DIR/tech-design/
├── LLD_<客户名>_v<N>_<日期>.md          # LLD 内容（Markdown，转 PPT 用）
├── TechSpec_<客户名>_v<N>_<日期>.md     # Technical Specification
└── diagrams/
    ├── diagram_config.json               # 客户配置（gen_diagrams.py 输入）
    ├── Logical_Architecture_<客户>.drawio
    ├── Data_Flow_<客户>.drawio
    ├── System_Flow_EndUser_<客户>.drawio
    ├── System_Flow_Employee_<客户>.drawio
    ├── System_Flow_Maintenance_<客户>.drawio
    └── Functional_Architecture_<客户>.drawio
```

---

## 常见问题

**客户不提供节点 IP 等具体信息：**
Section 5.1 填节点数量，IP 留 `<TBD>`，在 Section 11.2 Pre-requisites 中列为前置条件。

**客户要求简化 LLD：**
不可省略的核心章节：Section 1/2/3/5/6/7/10/11。可简化：Section 4（选型简单时）、Section 8（运维由厂商负责时）。

**客户要求用 PPT 内嵌图而非独立 draw.io 文件：**
先用模板生成 draw.io 文件，客户调整后导出 PNG/SVG 嵌入 PPT。

**Tech Spec 和 LLD 内容重复时：**
Tech Spec 用"参见 LLD Section X.X"引用，不重复写正文，只补充 LLD 没有的实施细节。

**客户对某节 LLD 反复修改：**
每次修改在文档版本历史中记录（修改内容 + 修改原因 + 审批人），这是合规审计的证据链。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录，无需中断当前工作。
