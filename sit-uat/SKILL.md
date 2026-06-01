---
name: sd-sit-uat
version: 0.1.0
description: 项目上线前需要完成系统集成测试（SIT）或用户验收测试（UAT）时使用
allowed-tools:
  - Bash
  - Read
  - Write
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


# SIT/UAT 测试设计与执行

## 适用场景

- 神策系统与客户业务系统集成完成后的 SIT
- 客户上线前的 UAT，验证业务场景是否满足需求
- 版本升级后的回归测试

## 核心原则（Iron Law）

**必须先完成测试用例设计并确认覆盖范围，再开始执行。不允许跳过用例设计直接测试。**

没有用例的测试无法证明覆盖了什么，也无法复现问题。

## 执行阶段

### Phase 1：测试范围确认

与客户/项目经理确认：
- 本次测试覆盖的业务场景列表
- 每个场景的验收标准（什么情况算通过）
- 测试环境信息（URL、测试账号、测试数据）
- 测试截止时间和上线条件

### Phase 2：测试用例设计

每个业务场景拆解为若干测试用例，每条用例包含：

| 字段 | 说明 |
|------|------|
| 用例编号 | TC-001, TC-002... |
| 场景 | 所属业务场景 |
| 前置条件 | 执行前需要满足的状态 |
| 操作步骤 | 逐步操作描述 |
| 预期结果 | 通过的判断标准 |
| 优先级 | P0（阻塞上线）/ P1（重要）/ P2（一般） |

**等待客户/PM 确认用例覆盖范围后才能进入 Phase 3。**

### Phase 3：执行验证

按用例逐条执行：
- 记录实际结果
- 对每条用例截图（操作步骤截图 + 结果截图）
- 标记状态：通过 / 失败 / 阻塞（无法执行）
- 失败用例记录复现步骤和实际结果

### Phase 4：报告输出

汇总测试结果，输出测试报告。

## 输出模板

```
## SIT/UAT 测试报告

**项目：** ...
**测试时间：** YYYY-MM-DD
**测试环境：** ...
**执行人：** ...

### 汇总
- 总用例数：X
- 通过：X（X%）
- 失败：X
- 阻塞：X

### 上线建议
[ ] 可以上线（所有 P0 用例通过）
[ ] 不建议上线（存在 P0 失败用例）

### 失败用例清单

| 用例编号 | 场景 | 失败描述 | 优先级 | 负责人 |
|----------|------|----------|--------|--------|
| TC-XXX   | ...  | ...      | P0     | ...    |

### 附件
- 测试截图：[链接或附件]
- 完整用例表：[链接或附件]
```

## 常见问题

**客户要求跳过用例设计直接测试：** 解释没有用例无法出具正式测试报告，且无法证明覆盖了哪些场景。最少也要有一个场景清单。

**测试环境数据不足：** 使用 tracking-setup-e2e skill 生成模拟数据后再执行测试。

**P0 用例失败但客户坚持上线：** 书面记录风险，要求客户签字确认，在报告中注明"客户知情并接受风险"。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录，无需中断当前工作。
