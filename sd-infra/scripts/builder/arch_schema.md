# 架构事实层 Schema（arch.yaml）

## 设计原则

事实层只描述**是什么**，不描述**怎么画**：
- 节点的语义类型和属性（不含坐标、颜色）
- 节点之间的关系类型和数据属性（不含线型、颜色）
- 分组/边界（逻辑归属，不含视觉样式）

颜色、坐标、线型由渲染器根据**语义规则**自动推导：
- `type: sd_product` → 绿色
- `data.has_pii: true` + `flow: batch` → 红色虚线
- `status: future` → 灰色虚线节点

## 顶层结构

```yaml
meta:
  title: 图标题
  client: 客户名
  version: 事实层版本号（语义变更时递增）
  date: YYYY-MM-DD

nodes:
  - id: 唯一标识（snake_case）
    name: 显示名称
    type: 语义类型（见下方类型表）
    status: current | future   # 默认 current；future → 渲染为灰色虚线
    group: 所属分组 ID（可选）
    tags: [tag1, tag2]         # 自由标签，用于筛选和渲染决策
    props:                     # 类型特定属性
      ...

groups:
  - id: 唯一标识
    name: 分组显示名称
    type: 分组语义类型
    contains: [node_id, ...]   # 声明包含哪些节点

edges:
  - from: source_node_id
    to: target_node_id
    rel: 关系类型（见下方关系表）
    name: 连线标签（可选）
    data:                      # 数据属性
      has_pii: true | false
      fields: [字段名列表]     # 传输的字段
      protocol: HTTPS | SFTP | Kafka | SDK | API
      frequency: realtime | daily | weekly | on-demand
    status: current | future
```

## 节点类型（type）

| type | 语义 | 渲染颜色 |
|------|------|---------|
| `sd_product` | 神策产品（CDP/MAE/ETL/SDK） | 绿 `#d5e8d4` |
| `sd_module` | 神策内部功能模块（C1-C9） | 黄 `#fffde7` |
| `client_system` | 客户业务系统（CRM/ERP/TAS） | 紫 `#e1d5e7` |
| `client_frontend` | 客户前端渠道（小程序/网站/App） | 紫 `#e1d5e7` |
| `external_saas` | 外部 SaaS 服务（SendCloud 等） | 蓝 `#dae8fc` |
| `person` | 用户角色（终端用户/业务用户/运维） | 橙 人形图标 |
| `infra` | 基础设施（SFTP/JumpServer/RDS） | 绿 `#d5e8d4` |

## 分组类型（group.type）

| type | 语义 | 渲染样式 |
|------|------|---------|
| `data_sources` | 数据来源区域 | 绿色虚线大框 |
| `frontend` | 前端渠道区域 | 紫色框 |
| `client_systems` | 客户系统区域 | 紫色框 |
| `internet` | 互联网区域 | 蓝色虚线框 |
| `vpc` | VPC 网络区域 | 灰色虚线框 |
| `region` | 云区域（如 HK / SZ） | 虚线框，标注区域名 |

## 关系类型（edge.rel）

| rel | 语义 | 默认渲染 |
|-----|------|---------|
| `sdk_track` | SDK 埋点上报 | 按 has_pii 决定颜色；realtime→实线，batch→虚线 |
| `api_push` | API 实时推送 | 同上 |
| `sftp_export` | SFTP 文件导出 | 同上 |
| `kafka_subscribe` | Kafka 异步订阅 | 蓝色虚线 |
| `api_call` | API 调用（出站） | 按 has_pii 决定颜色 |
| `data_passthrough` | 数据透传（中转系统） | 按 has_pii 决定颜色 |
| `user_access` | 用户访问 | 灰色实线 |
| `ops_access` | 运维访问 | 灰色虚线 |
| `callback` | 回调（如邮件打开事件） | 绿色实线 |
| `deliver` | 消息投递（邮件/推送/SMS） | 按 has_pii 决定颜色 |

## 渲染规则（由渲染器执行，事实层不涉及）

```
边颜色：
  has_pii=true AND frequency=realtime  → 红色实线
  has_pii=true AND frequency=daily     → 红色虚线
  rel=kafka_subscribe                  → 蓝色虚线（覆盖 PII 规则）
  has_pii=false                        → 绿色实线
  status=future                        → 灰色虚线

节点样式：
  status=future                        → fillColor=#f5f5f5, dashed=1
  type=person                          → 人形图标
  type in [sd_product, sd_module, infra] → 绿色
  type in [client_system, client_frontend] → 紫色
  type=external_saas                   → 蓝色
```
