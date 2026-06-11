---
name: sd-status
description: 查看当前客户项目状态，自动诊断配置问题
argument-hint: ""
---

# /sd-status — 查看项目状态

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 显示当前客户项目的整体状态，包括项目档案完整性、配置状态、自动诊断结果。
>
> **前置条件：**
> - 需要在已初始化的客户项目目录中执行（存在 .env 文件）
>
> **执行步骤概览：**
> 1. 检测环境（客户目录、CDP 连接信息）
> 2. 检查项目档案状态（PROJECT.md / CLARIFICATION.md / DELIVERY.md）
> 3. 运行自动诊断（配置问题、逾期项）
> 4. 输出状态卡片和可用 Command 列表
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过

## 前置条件

- 需要在已初始化的客户项目目录中执行（存在 .env 文件）

## 工作流

### Step 1：Preamble 环境检测

Preamble 自动检测以下内容：
- 客户项目目录位置
- CDP 连接信息（SA_HOST、SA_PROJECT）
- 项目档案状态（PROJECT.md / CLARIFICATION.md / DELIVERY.md）
- 交付进度（已完成/总数）
- 埋点方案路径
- 业务规则文件
- 模拟数据生成状态
- 待处理反馈数

### Step 2：文件系统诊断（替代 sdeliver-auto-feedback）

基于实际文件状态运行诊断，不依赖外部 `sdeliver-auto-feedback` 工具：

**必检项：**
- `.env` 中 `SA_HOST`、`SA_PROJECT`、`CLIENT_NAME` 是否配置
- `references/` 目录是否存在、是否为空
- `PROJECT.md` / `CLARIFICATION.md` / `DELIVERY.md` 是否存在及修改时间
- `rules/business_logic.yaml` 或 `business_logic.yaml` 是否存在
- `mock_data/` 目录是否存在、是否有数据文件
- `IMPORT_STATUS.md` 是否存在 → 提取导入进度、用户分层异常、转化事件样本量
- 埋点方案文件（`.env` 中 `TRACKING_PLAN_PATH` 或 `references/` 中 `.xlsx`）是否存在

**诊断规则：**
| 问题码 | 触发条件 | 严重程度 |
|--------|----------|----------|
| tracking-plan-not-found | TRACKING_PLAN_PATH 未配置且 references/ 无 .xlsx | 🔴 高 |
| business-logic-missing | 无 business_logic.yaml | 🔴 高 |
| import-stalled | IMPORT_STATUS.md 存在但进度 < 5% 且文件修改时间 > 24h | 🟡 中 |
| user-tier-anomaly | L0=0 或 L3=0（全量用户均触发注册/购买） | 🟡 中 |
| low-conversion-sample | 转化事件（购买/会员）< 500 条 | 🟡 中 |
| stale-delivery | DELIVERY.md 修改时间早于 references/ 中任何文件 | 🟡 中 |
| mock-data-empty | mock_data/ 存在但无 .jsonl 文件 | 🟡 中 |
| clarification-pending | CLARIFICATION.md 中存在 ⏳ 状态问题 | 🟡 中 |

### Step 3：输出状态卡片

标准格式：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 sdeliver v<VERSION>
 客户: <CLIENT>  |  <SA_HOST> / <SA_PROJECT>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 项目档案:    ✅ PROJECT.md / ✅ CLARIFICATION.md / ✅ DELIVERY.md  <DONE>/<TOTAL>
 埋点方案:    ✅ 已配置
 业务规则:    ✅ business_logic.yaml
 模拟数据:    ✅ 已生成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

如果诊断发现问题：
```
⚠️ 自动检测到 <N> 个问题：
  - tracking-plan-not-found → 埋点方案未配置
  - import-stalled → 导入进度 2.2%，预计剩余 15 小时
  - user-tier-anomaly → L0=0, L3=0，需修正 YAML
```

### Step 4：展示可用 Command

```
可用 Command（active）：
  /sd-onboard          初始化项目档案
  /sd-setup-tracking   执行埋点全链路
  /sd-ask-faq          查询交付知识库

待上线 Command（draft）：
  /sd-design-tracking  设计埋点方案
  /sd-size-server      评估服务器
  /sd-validate-data    数据全流程校验
  /sd-design-tech      技术方案设计
  /sd-draw-arch        架构图生成
  /sd-design-test      测试方案设计（SIT/UAT/Perf）
  /sd-run-test         测试执行（SIT/UAT/Perf）
```
