---
name: sd-performance-test
version: 0.2.0
description: |
  负责性能测试。对神策 CDP/MAE 系统进行压力测试和性能基准评估，输出性能测试报告。
  与 sd-server-sizing 配合：server-sizing 负责容量规划，performance-test 负责验证规划是否达标。
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
  _SA_HOST=$(grep '^SA_HOST=' "$_ENV_FILE" | cut -d= -f2-)
  _PROJECT_DIR="$(dirname "$_ENV_FILE")"
else
  _PROJECT_DIR="$(pwd)"
fi

echo "SKILL_REPO: ${_SKILL_REPO:-(未设置)}"
echo "CLIENT: ${_CLIENT:-unknown}"
echo "SA_HOST: ${_SA_HOST:-(未填写)}"
```

**Preamble 输出处理：**
- `ENV_FILE: none` → 停止，提示用户先运行 `sdeliver init <客户名>`
- `SKILL_REPO` 含"未设置" → 停止，提示重新运行 `./setup`

## 适用范围

- 客户上线前的容量验证
- 系统压测，评估 TPS/QPS 上限
- 数据导入吞吐量测试
- 查询响应时间基准

## 与 sd-server-sizing 的关系

| 阶段 | 负责 Skill | 输出 |
|------|-----------|------|
| 容量规划 | sd-server-sizing | 服务器配置方案、资源预估 |
| 容量验证 | sd-performance-test（本 Skill）| 实测性能指标、瓶颈定位 |

**执行顺序：** 先 server-sizing 规划 → 部署 → 再 performance-test 验证。

## 执行流程

### Step 1：明确性能基线指标

与客户确认：

| 指标 | 说明 | 来源 |
|------|------|------|
| 峰值 TPS | 每秒最大事件写入量 | server-sizing 规划值或客户业务预估 |
| 日数据量 | 日均新增事件量 | server-sizing 规划值 |
| 查询 P99 响应时间 | 看板/自定义查询最大容忍延迟 | 客户 SLA 要求 |
| 并发用户数 | 同时使用系统的人数 | 客户业务预估 |
| 数据保留周期 | 数据保留时长 | server-sizing 规划值 |

输出：`$PROJECT_DIR/docs/performance_baseline.md`

### Step 2：数据准备

基于 sd-tracking-setup-e2e 生成的 mock 数据或客户真实数据构造测试数据集。

| 测试类型 | 数据规模建议 | 数据来源 |
|---------|-------------|---------|
| 数据写入压测 | 目标日数据量的 10%～20% | mock 数据 / 真实数据脱敏 |
| 查询性能测试 | 覆盖典型看板的 30 天数据 | 已导入 CDP 的 mock 数据 |
| 并发测试 | 模拟目标并发用户数 | 脚本生成虚拟用户 |

### Step 3：执行测试

分别测试以下场景：

1. **数据写入压测** — HTTP API 批量导入，逐步增加并发
   - 工具：import_tool.py（多线程）或自定义 locust/jmeter 脚本
   - 梯度：25% → 50% → 75% → 100% → 120%（过载测试）
   - 记录：TPS、错误率、响应时间 P50/P95/P99

2. **查询性能测试** — 典型看板/自定义查询的响应时间
   - 选取 5～10 个典型查询场景
   - 记录：首次加载时间、刷新时间、P99 延迟

3. **并发测试** — 模拟多用户同时操作
   - 工具：浏览器自动化 / API 并发脚本
   - 记录：系统是否出现排队、超时、连接拒绝

### Step 4：输出报告

性能测试报告包含：
- 测试环境配置（与 server-sizing 方案对比）
- 测试方法和工具
- 各项指标结果（含 P50/P95/P99）
- 与 server-sizing 规划指标的对比（达标 / 未达标 / 超预期）
- 瓶颈分析和优化建议

## 输出模板

```markdown
## 性能测试报告

**客户：** <CLIENT>
**测试时间：** YYYY-MM-DD
**测试环境：** <与 server-sizing 方案对比>
**执行人：** <测试工程师>

### 测试目标（来自 server-sizing 规划）

| 指标 | 规划值 | 实测值 | 状态 |
|------|--------|--------|------|
| 峰值 TPS | X | Y | ✅/❌ |
| 日数据量 | X | Y | ✅/❌ |
| 查询 P99 | X | Y | ✅/❌ |
| 并发用户 | X | Y | ✅/❌ |

### 测试环境

| 组件 | 配置 | 与规划差异 |
|------|------|-----------|
| CDP 节点 | ... | ... |
| SF 节点 | ... | ... |

### 测试结果详情

#### 1. 数据写入压测

| 并发度 | TPS | 错误率 | P50 | P95 | P99 |
|--------|-----|--------|-----|-----|-----|
| 25% | ... | ... | ... | ... | ... |
| 50% | ... | ... | ... | ... | ... |
| 100% | ... | ... | ... | ... | ... |
| 120% | ... | ... | ... | ... | ... |

#### 2. 查询性能测试

| 查询场景 | 首次加载 | 刷新 | P99 | 状态 |
|---------|---------|------|-----|------|
| ... | ... | ... | ... | ✅/❌ |

#### 3. 并发测试

| 并发用户数 | 操作场景 | 结果 |
|-----------|---------|------|
| ... | ... | ... |

### 瓶颈分析

1. ...
2. ...

### 优化建议

1. ...
2. ...

### 结论

[ ] 性能达标，可以上线
[ ] 性能未达标，需优化后再验证
[ ] 性能超预期，可考虑降配以节省成本
```

## Feedback

使用时发现问题或有改进建议，随时调用 `/sd-feedback <描述>`。
