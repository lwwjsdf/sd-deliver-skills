---
name: sd-size-server
description: 信息收集 → 运行计算器 → 生成 Excel → 输出配置方案
argument-hint: ""
status: draft
---

# /sd-size-server — 服务器资源评估

> ⚠️ **执行前确认**
>
> **此 command 会做什么：**
> 根据客户业务数据评估服务器资源需求，输出配置方案 Excel。
>
> **前置条件：**
> - 项目已初始化（PROJECT.md 存在）
> - 了解客户的日活/事件量
>
> **执行步骤概览：**
> 1. 信息收集（日均事件量、日活、保留天数、服务器类型等）
> 2. 运行计算器（sizing_calc.py）
> 3. 选择部署模式（单机/Mini/标准集群）
> 4. 输出配置方案（gen_excel.py）
> 5. 方案确认（推荐模式、配置表、扩容路径）
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 前置条件

- 项目已初始化（PROJECT.md 存在）
- 了解客户的日活/事件量（可从 PROJECT.md 读取）

## 工作流

### Step 1：信息收集

向客户收集以下信息（已有 PROJECT.md 的先读取）：
- 日均事件量、日活（DAU）、历史总事件量
- 数据保留天数、12 个月增长预期
- 服务器类型（云主机/物理机）、CPU 架构（X86/ARM）、云厂商
- 是否需要 SF（MA/SFN）及 SF 专项信息

### Step 2：运行计算器

收集完立即运行：

```bash
python3 scripts/sizing_calc.py \
  --daily-events <日均事件量> \
  --dau <日活> \
  --retention-days <保留天数> \
  --history-events <历史存量> \
  --growth-multiplier <增长倍数> \
  --arch <x86|arm> \
  --addons <附加产品> \
  --data-nodes <数据节点数>
```

### Step 3：选择部署模式

根据计算结果选择单机/Mini 集群/标准集群。

### Step 4：输出配置方案

```bash
python3 scripts/gen_excel.py \
  --mode <single|mini|standard> \
  --cloud-vendor <云厂商> \
  --dau-range "<日活档位>" \
  --daily-import <日导入亿> \
  --output <输出路径.xlsx>
```

### Step 5：方案确认

输出包含：
- 推荐部署模式及理由
- 详细配置表（节点类型、数量、CPU、内存、磁盘）
- 扩容路径
- 注意事项（云厂商 IO 限制、ARM 说明）
