---
name: delivery-progress
version: 1.0.0
description: |
  交付进度跟踪知识。管理 DELIVERY.md 中的交付物清单，
  每次 skill 工作完成后更新对应条目状态，识别逾期风险和交付瓶颈。
allowed-tools:
  - Bash
  - Read
---

## 进度跟踪格式

DELIVERY.md 中的条目使用三种状态标记：

```
- [ ] 待启动    → 尚未开始
- [~] 进行中    → 正在执行
- [x] 已完成    → 已交付
```

## 自动诊断

每次调用任何 Command 时，Preamble 自动检测：

| 检测项 | 条件 | 严重度 |
|--------|------|--------|
| DELIVERY.md 超过 14 天未更新 | `stale-delivery` | low |
| business_logic.yaml 超过 30 天未更新 | `stale-business-logic` | low |
| 有模拟数据但无验证报告 | `unvalidated-mock-data` | medium |
| YAML 验证通过后 7 天未造数 | `outdated-yaml` | low |

检测到的问题自动写入 `~/.sdeliver/feedback/`，3 天内去重。

## 更新协议

每次工作流完成时，更新 DELIVERY.md 中对应交付物条目状态，并在摘要中输出当前进度。
