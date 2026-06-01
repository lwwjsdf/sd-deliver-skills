---
name: sd-data-validation
version: 0.1.0
description: 数据上线后验证数据正确性，覆盖事件数据、用户属性、分群结果等多种校验场景，或客户反馈数据异常时使用
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

## Preamble（每次调用时先执行）

```bash
_SKILL_REPO=$(sdeliver-config get skill_repo_path 2>/dev/null || echo "")
_PROACTIVE=$(sdeliver-config get proactive 2>/dev/null || echo "true")

_ENV_FILE=""
_DIR="$(pwd)"
while [ "$_DIR" != "/" ]; do
  [ -f "$_DIR/.env" ] && _ENV_FILE="$_DIR/.env" && break
  _DIR="$(dirname "$_DIR")"
done

if [ -n "$_ENV_FILE" ]; then
  _CLIENT=$(grep '^CLIENT_NAME=' "$_ENV_FILE" | cut -d= -f2-)
  _SA_HOST=$(grep '^SA_HOST=' "$_ENV_FILE" | cut -d= -f2-)
  _SA_PROJECT=$(grep '^SA_PROJECT=' "$_ENV_FILE" | cut -d= -f2-)
  _PROJECT_DIR="$(dirname "$_ENV_FILE")"
else
  _PROJECT_DIR="$(pwd)"
fi

echo "SKILL_REPO: ${_SKILL_REPO:-(未设置)}"
echo "ENV_FILE: ${_ENV_FILE:-none}"
echo "PROJECT_DIR: $_PROJECT_DIR"
echo "CLIENT: ${_CLIENT:-unknown}"
echo "SA_HOST: ${_SA_HOST:-(未填写)}"
echo "SA_PROJECT: ${_SA_PROJECT:-(未填写)}"
```

**Preamble 输出处理：**

- `ENV_FILE: none` → 停止，提示用户先运行 `sdeliver init <客户名>`
- `SKILL_REPO` 含"未设置" → 停止，提示重新运行 `./setup`
- 否则，输出：`客户: <CLIENT> | 环境: <SA_HOST>/<SA_PROJECT>`


# 埋点数据校验

## 适用场景

- 埋点代码上线后，验证数据是否按方案正确上报
- 客户反馈某个指标数据异常，需要定位是埋点问题还是分析问题
- 版本迭代后回归验证埋点未被破坏

## 核心原则（Iron Law）

**必须对比埋点方案文档与实际数据，不允许仅凭肉眼或印象判断数据是否正确。**

没有方案文档就无法校验。如果方案文档缺失，先用 tracking-setup-e2e skill 补充方案再校验。

## 执行阶段

### Phase 1：获取埋点方案

- 找到当前版本的埋点方案文档
- 确认方案版本与待验证的代码版本一致
- 列出本次需要校验的事件范围（全量或指定事件）

### Phase 2：抓取实际数据

从神策系统获取实际上报数据：
- 指定时间范围（建议取最近 24 小时）
- 按事件名过滤，逐个事件检查
- 记录每个事件的实际属性列表和示例值

### Phase 3：逐项比对

对每个事件执行以下检查：

| 检查项 | 通过标准 |
|--------|----------|
| 事件名 | 与方案完全一致（区分大小写） |
| 必填属性 | 全部存在，无缺失 |
| 属性类型 | 与方案定义一致 |
| 属性值范围 | 无明显异常值（空字符串、null、乱码） |
| 触发时机 | 与方案描述的触发条件一致 |

### Phase 4：输出差异报告

按三类汇总结果：
- **通过**：与方案完全一致
- **异常**：存在但有问题（属性缺失、类型错误、值异常）
- **缺失**：方案中有但实际未上报

每条异常和缺失附上修复建议。

## 输出模板

```
## 埋点校验报告

**校验时间：** YYYY-MM-DD
**校验范围：** XX 个事件
**数据时间范围：** 最近 24 小时

### 汇总
- 通过：X 个
- 异常：X 个
- 缺失：X 个

### 异常详情

| 事件名 | 问题描述 | 修复建议 |
|--------|----------|----------|
| ...    | ...      | ...      |

### 缺失详情

| 事件名 | 方案要求 | 可能原因 |
|--------|----------|----------|
| ...    | ...      | ...      |
```

## 常见问题

**找不到埋点方案文档：** 使用 tracking-setup-e2e skill 补充方案后再校验。

**数据量为零：** 先确认测试设备是否在神策的设备白名单内，再确认 SDK 初始化是否成功。

**属性值为 null：** 区分"代码未传值"和"业务场景确实无值"，前者是 bug，后者需要更新方案说明。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录，无需中断当前工作。
