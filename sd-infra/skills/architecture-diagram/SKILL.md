---
name: architecture-diagram
version: 1.0.0
description: |
  架构图绘制知识。为神策 CDP & MAE 项目生成 draw.io 架构图。
  以 arch.yaml 为唯一事实层，支持标准模板生成和自定义架构描述两种模式。
  当讨论架构图、draw.io、数据流图、系统流图时自动加载。
allowed-tools:
  - Bash
  - Read
  - Write
---

## 与 LLD 的对应关系

| 图类型 | LLD 章节 |
|--------|---------|
| 逻辑架构图 | Section 3.3 |
| 系统流图（3 种用户视角） | Section 3.4 |
| 基础设施架构图 | Section 3.5.1 |
| 数据流图 | Section 3.6 |
| 功能架构图 | Appendix |

## 工作方式

1. 确认架构描述（从 PROJECT.md 或用户输入提取）
2. 生成 arch.yaml（事实层）
3. 运行渲染器生成 draw.io XML
4. 审核调整
5. 输出最终架构图

## 参考模板

存储在 `references/` 目录中：
- Logical_Architecture.drawio
- CDP&MAE Data Flow.drawio
- System Flow-*.drawio
- Functional_Architecture.drawio
- db_components.drawio
