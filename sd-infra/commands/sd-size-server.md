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
> 根据客户业务数据（DAU/MAU、日事件量、保留周期、产品范围）评估 CDP/MA/ETL 云资源需求，输出配置方案 Excel/Word。
>
> **前置条件：**
> - 项目已初始化（PROJECT.md 存在）
> - 了解客户的日活/事件量、数据保留周期、云厂商
>
> **执行步骤概览：**
> 1. 信息收集（MAU/DAU、日事件量、保留天数、产品范围、云厂商）
> 2. 按 DAU/日事件量选择基础 CDP/MA 集群
> 3. 按保留周期计算 CDP 顺序盘容量
> 4. 按云厂商磁盘规则校验并调整
> 5. 输出配置方案（Excel/Word）
> 6. 方案确认（推荐模式、配置表、扩容路径）
>
> 1/y = 确认执行
> 0/n = 取消
> 2/s = 跳过
>
> 每一步执行前我会再次确认。

## 前置条件

- 项目已初始化（PROJECT.md 存在）
- 了解客户的 DAU/MAU、日事件量（可从 PROJECT.md 读取）

## 工作流

### Step 1：信息收集

向客户收集以下信息：
- MAU / DAU（DAU 优先；无 DAU 时用 MAU × 行业比例估算）
- 单用户日事件数 或 真实日事件量
- 数据保留周期（默认 1 年）
- 产品范围（CDP / MA / ETL）
- 云厂商（AWS/Azure/GCP/阿里云/华为云）
- 区域
- 行业场景（用于默认 DAU/MAU 比例）

### Step 2：选择基础集群

按 DAU / 日事件量 / MA 每天受众上限匹配：

| 产品 | 配置档次 | 边界 |
|------|----------|------|
| CDP | Mini 标配/高配 | <100万/<500万 DAU |
| CDP | 标准 3+3 标配/高配 | <800万/<1400万 DAU |
| CDP | 标准 3+4/3+5/3+6 | 更高 |
| MA | 按 DAU/日事件/受众上限 | 见 server-sizing skill |
| ETL | 默认 3 × 8C/32G | 按数据源调整 |

### Step 3：存储容量计算

```
周期内事件量（亿）= 日事件量 × 保留天数 / 1亿
估算实际使用容量 = 周期内事件量 × 35 GB × 1.1
需配置容量 = 估算实际使用容量 / 0.8
```

### Step 4：云厂商磁盘校验

校验项：
- 单盘容量 ≤ 云厂商单盘上限
- 数据盘数量 ≤ 实例挂载限制
- 顺序盘 IOPS/吞吐 ≥ 120/120
- 元数据盘/随机盘 IOPS/吞吐 ≥ 5000/150
- 不满足时：增大单盘、增加节点、升级盘型或专项评估

### Step 5：输出配置方案

运行脚本生成配置表：

```bash
./venv/bin/python <skill-repo>/sd-infra/scripts/sizing_calc.py \
  --mau <MAU> \
  --dau <DAU> \
  --daily-events <日事件量> \
  --retention-days <保留天数> \
  --include-ma \
  --include-etl \
  --cloud <AWS|Azure|GCP|Alibaba|Huawei> \
  --output <输出路径.xlsx>
```

输出包含：
- 客户/云厂商/区域摘要
- CDP/MA/ETL 节点配置明细
- 磁盘用途、数量、单盘容量、云盘类型
- 存储估算说明
- 内部边界说明（不写入客户版）

### Step 6：方案确认

确认项：
- 推荐部署模式及理由
- 详细配置表（节点类型、数量、CPU、内存、磁盘）
- 扩容路径
- 注意事项（云厂商 IO 限制、区域规格可用性）

## 完成建议

- "配置方案已确认？→ 执行 `/sd-design-tech` 输出 LLD"
- "需要验证性能？→ `/sd-design-performance-test`"
- "需要架构图？→ `/sd-draw-arch`"
