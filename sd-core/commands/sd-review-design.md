---
name: sd-review-design
description: 评审设计方案：埋点方案、技术架构、SIT/UAT/性能测试计划
argument-hint: "[--target tracking-plan|tech|sit|uat|performance] [--file path]"
status: draft
---

# /sd-review-design — 设计方案评审

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 基于神策交付规范和项目上下文，对指定设计方案进行结构化评审，输出 review-report.md。
>
> **可评审对象：**
> - `tracking-plan` — 埋点方案 Excel / YAML
> - `tech` — 技术设计文档 / LLD / 架构图
> - `sit` — SIT Plan / Test Case
> - `uat` — UAT Test Case / 验收规则
> - `performance` — Performance Test Plan
>
> **执行步骤概览：**
> 1. 确认评审对象和范围
> 2. 读取设计文档
> 3. 按检查清单逐条评审
> 4. 标记风险、缺失、需确认项
> 5. 输出 review-report.md
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过

## 用法

```bash
# 评审埋点方案
/sd-review-design --target tracking-plan --file ./references/tracking-plan.xlsx

# 评审技术设计
/sd-review-design --target tech --file ./references/tech-spec.md

# 评审 UAT
/sd-review-design --target uat --file ./references/uat-test-case.xlsx
```

## 评审维度

### Tracking Plan 评审

| 检查项 | 通过标准 |
|--------|----------|
| 事件命名 | 英文变量名统一、无空格、无特殊字符 |
| 公共属性 | platformType / applicationName / version 已定义 |
| 属性类型 | 数值/字符串/日期/布尔类型合理 |
| 必填属性 | 核心字段标记为必填 |
| ID-Mapping | 已明确 distinct_id、login_id、identities 设计 |
| 跨平台一致性 | MP / Web 同名事件属性定义一致 |
| 业务规则 | 派生事件、金额字段、时间顺序有说明 |

### Tech Design 评审

| 检查项 | 通过标准 |
|--------|----------|
| 架构图 | 有 draw.io / arch.yaml，组件边界清晰 |
| 部署模式 | 单机/Mini/标准集群选型有依据 |
| 容量规划 | 引用 server-sizing 输出，非凭空指定 |
| 数据流 | 采集 → 加密 → 导入 → 存储 → 查询链路完整 |
| 安全合规 | PII 加密、SFTP、KMS、防火墙白名单已考虑 |
| 监控告警 | CPU/内存/磁盘/QPS 监控和告警策略 |

### SIT / UAT 评审

| 检查项 | 通过标准 |
|--------|----------|
| 覆盖范围 | 与 Tracking Plan / 业务场景对应 |
| 用例结构 | ID、前置条件、步骤、预期结果完整 |
| 可执行性 | 步骤可独立执行，不依赖未交付功能 |
| 验收标准 | 通过/失败标准明确 |
| 数据准备 | 已明确 mock_data / 测试账号 |

### Performance Test Plan 评审

| 检查项 | 通过标准 |
|--------|----------|
| 目标 | QPS/吞吐/响应时间/资源上限明确 |
| 场景 | 覆盖实时导入、批量导入、分析查询、MAE 发送 |
| 数据规模 | 用户数、事件总量与生产对齐 |
| 环境 | UAT 与生产一致，资源独占 |
| 退出标准 | 所有指标达标或边界已确定 |

## 输出

`references/review-report.md`：

```markdown
# Design Review Report — <target>

## 基本信息
- 评审对象：tracking-plan
- 文件：./references/tracking-plan.xlsx
- 评审日期：YYYY-MM-DD

## 检查项结果
| 检查项 | 状态 | 说明 |
|--------|------|------|
| 事件命名 | ✅ | ... |
| 公共属性 | ⚠️ | version 字段未标记必填 |

## 风险与建议
1. ...

## 必须修复项
- [ ] ...

## 可优化项
- [ ] ...
```

## 完成建议

- "评审通过？→ 继续 `/sd-setup-tracking` 或 `/sd-run-sit`"
- "有必须修复项？→ 先修改设计文档后重新 `/sd-review-design`"
