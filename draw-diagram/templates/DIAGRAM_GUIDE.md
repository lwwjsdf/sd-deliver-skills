# draw.io 架构图设计规范

基于 Westk TP1 CDP & MAE 项目实战沉淀。所有新项目的架构图应遵循本规范，保持视觉一致性。

---

## 1. 颜色规范

| 节点类型 | fillColor | strokeColor | 用途 |
|---------|-----------|-------------|------|
| 神策产品（CDP / MAE / ETL） | `#d5e8d4` | `#82b366` | 绿色：System of Interest，神策负责的组件 |
| 客户系统（CRM / TAS / 业务系统） | `#e1d5e7` | `#9673a6` | 紫色：External，客户现有系统 |
| 外部 SaaS（SendCloud / 第三方 API） | `#dae8fc` | `#6c8ebf` | 蓝色：External SaaS，第三方服务 |
| 内部功能模块（C1-C9 组件） | `#fff2cc` | `#d6b656` | 黄色：Internal Module，系统内部功能块 |
| Future Scope（Day 2+ 节点） | `#f5f5f5` | `#666666` | 灰色 + 虚线边框：未来规划，当前不在范围内 |
| 用户（End User / Employee） | 无填充 | — | 人形图标（shape=mxgraph.basic.person2） |
| 数据库/存储（Kafka / MySQL / SKV） | `#fff2cc` | `#d6b656` | 圆柱形（shape=mxgraph.flowchart.stored_data） |
| 分组框（VPC / Internet / 区域） | 无填充 / 浅色 | 虚线 | swimlane 或 group，用于划定边界 |

---

## 2. 连线规范

| 连线类型 | 颜色 | 线型 | 含义 |
|---------|------|------|------|
| 含 PII / 敏感数据的实时数据流 | `#FF0000`（红色） | 实线，粗 | 高敏感数据，需加密标注 |
| 含 PII / 敏感数据的批量数据流 | `#FF0000`（红色） | 虚线 | 批量 PII，如 SFTP T+1 |
| 内部数据流（非 PII） | `#82b366`（绿色） | 实线 | 系统内部，SoI 范围内 |
| Kafka 异步数据管道 | `#6c8ebf`（蓝色） | 虚线 | 异步消息队列 |
| 系统/配置数据（无 PII） | `#666666`（灰色） | 实线 | 配置、模板、规则等 |
| Future 连线 | `#666666`（灰色） | 虚线 | 未来规划的数据流 |

**连线标签格式：**
```
[协议] ([频率])
数据字段1 / 数据字段2 [PII] / 数据字段3 [Sensitive]
```
示例：`SDK / HTTPS (real-time)\nBehaviorEvent [PII] / DeviceID / SessionID`

---

## 3. 图层/分组规范

所有图使用以下标准分组结构（根据图类型选用）：

### 逻辑架构图（Logical Architecture）
```
Data Sources（绿色虚线大框）
  ├── WestK Systems（紫色框）
  │     ├── 核心系统（实线节点）
  │     └── Future 系统（灰色虚线节点）
  └── FrontEnd（紫色框）
        ├── Mini-Program（实线）
        └── Future 渠道（灰色虚线）
CDP（绿色大框）
  └── 功能模块（黄色圆角框）
MAE（绿色大框）
  └── 功能模块（黄色圆角框）
SendCloud（蓝色框）
ETL（绿色框）
Legend（图例框，右下角）
```

### 数据流图（Data Flow）
```
Internet（虚线框，左侧，含数据来源）
  ├── 中国大陆区域（虚线框，PIPL 标注）
  └── 香港区域（虚线框）
WestK Systems（紫色框）
CDP（绿色大框）
MAE（绿色大框）
SendCloud（蓝色框）
Internet（虚线框，右侧，含 End User）
Legend（图例框，含颜色说明）
```

### 系统流图（System Flow）
```
Internet（蓝色虚线框，顶部，含用户入口）
Data Sources（蓝色虚线框，左侧）
  ├── BackEnd / WestK Systems（紫色框）
  └── FrontEnd（紫色框）
CDP Cluster（绿色大框，含步骤编号模块）
MAE（绿色大框，含步骤编号模块）
SendCloud（蓝色框）
Legend（图例框）
```

### 功能架构图（Functional Architecture）
```
Data Sources（蓝色框）
Integration Methods（蓝色框）
CDP Cluster（绿色大框，System of Interest）
  ├── Data Model（EUI）
  ├── ID Mapping Engine
  ├── Functional Modules（C5）
  ├── Data Storage Layer（C3）
  └── Processing Components（C1/C2/C4/C9）
MAE Cluster（黄色大框）
  ├── Campaign Plan
  ├── Journeys
  └── Channel Management
SendCloud（紫色框，External ESP SaaS）
SFTP Server（紫色框，Mainland China VPC）
```

---

## 4. 节点命名规范

| 节点 | 命名格式 | 示例 |
|------|---------|------|
| 神策组件 | 英文全称 + 括号内简称 | `CDP (Customer Data Platform)` |
| 内部功能模块 | C编号: 功能名 | `C1: Data Ingestion ETL` |
| 数据库/存储 | 产品名（内部名） | `Kudu (Soku)` |
| 外部系统 | 系统名 / 产品名 | `Ticketing System / TAS` |
| Future 节点 | 名称 + `（Future）` | `Retail System（Future）` |
| 步骤节点 | `Step N: 描述` | `Step 2: Identity Resolution` |

---

## 5. 图例（Legend）规范

每张图右下角必须包含 Legend，说明颜色和线型含义：

```
Legend
├── 绿色框：神策产品 / System of Interest
├── 紫色框：客户系统 / External
├── 蓝色框：外部 SaaS
├── 灰色虚线框：Future Scope
├── 红色实线：含 PII 数据流
├── 红色虚线：批量 PII 数据流
├── 绿色实线：内部数据流（非 PII）
├── 蓝色虚线：Kafka 异步管道
└── 灰色虚线：Future 数据流
```

---

## 6. 五类标准图说明

| 图类型 | 文件名规范 | 主要用途 | 对应 LLD 章节 |
|--------|-----------|---------|--------------|
| 逻辑架构图 | `Logical_Architecture_<客户>_v<N>.drawio` | 展示系统组件逻辑关系 | Section 3.3 |
| 系统流图（End User） | `System_Flow_EndUser_<客户>_v<N>.drawio` | 最终用户视角的数据流 | Section 3.4 |
| 系统流图（Employee） | `System_Flow_Employee_<客户>_v<N>.drawio` | 业务用户视角 | Section 3.4 |
| 系统流图（Maintenance） | `System_Flow_Maintenance_<客户>_v<N>.drawio` | 运维用户视角 | Section 3.4 |
| 数据流图 | `Data_Flow_<客户>_v<N>.drawio` | CDP & MAE 数据流详情 | Section 3.6 |
| 功能架构图 | `Functional_Architecture_<客户>_v<N>.drawio` | 系统内部功能模块 | Appendix |
| DB 组件图 | `DB_Components_<客户>_v<N>.drawio` | 存储组件分布 | Appendix |

---

## 7. 修改新项目图的步骤

1. 复制对应的骨架模板（`_TEMPLATE.drawio`）
2. 按命名规范重命名
3. 修改以下内容：
   - 客户系统名称（WestK Systems → 客户实际系统名）
   - 数据来源（保留当前范围，灰色虚线标注 Future）
   - 外部 SaaS（SendCloud → 客户实际使用的邮件/推送服务商）
   - 连线标签（数据字段名、协议、频率）
   - 地域标注（HK/SZ → 客户实际云区域）
4. 保留不变的内容：
   - CDP / MAE 内部功能模块结构（C1-C9）
   - 颜色规范
   - Legend
   - Future 节点（除非客户明确不需要）
