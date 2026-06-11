---
name: sd-sit-uat
version: 0.3.0
description: |
  项目上线前执行系统集成测试（SIT），验证各模块间数据流转和功能集成正确性。
  UAT 请使用 sd-tracking-design（业务分析师）。
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


# SIT 测试设计与执行

## 适用场景

- 神策系统与客户业务系统集成完成后的 SIT
- 版本升级后的回归测试
- 数据链路端到端验证

## 核心原则（Iron Law）

**必须先完成测试用例设计并确认覆盖范围，再开始执行。不允许跳过用例设计直接测试。**

没有用例的测试无法证明覆盖了什么，也无法复现问题。

## 执行阶段

### Phase 1：测试计划

与客户/项目经理确认：
- 本次测试覆盖的业务场景列表
- 每个场景的验收标准（什么情况算通过）
- 测试环境信息（URL、测试账号、测试数据）
- 测试截止时间和上线条件
- 测试资源分配（执行人、评审人）

**输出物：**《SIT 测试计划》（Markdown，包含范围/标准/环境/排期/资源）

### Phase 2：用例评审

基于 Phase 1 确认的范围，使用模板 `$SKILL_REPO/sit-uat/templates/sit_test_case_template.xlsx` 设计测试用例。

每个业务场景拆解为若干测试用例，每条用例包含：

| 字段 | 说明 |
|------|------|
| 用例编号 | TC-001, TC-002... |
| 所属模块 | 数据接入/用户画像/分群/活动/旅程/报表/接口集成 |
| 场景 | 所属业务场景 |
| 前置条件 | 执行前需要满足的状态 |
| 操作步骤 | 逐步操作描述 |
| 预期结果 | 通过的判断标准 |
| 优先级 | P0（阻塞上线）/ P1（重要）/ P2（一般） |
| 实际结果 | 执行时填写 |
| 状态 | 未执行/通过/失败/阻塞 |
| 执行人 | 执行时填写 |
| 执行日期 | 执行时填写 |
| 备注 | 补充信息 |

**Traceability Matrix（可追溯矩阵）：**

每条用例必须关联到至少一个上游交付物，确保测试覆盖无遗漏：

| 用例编号 | 关联需求/设计文档 | 关联架构图 | 关联 server-sizing 规格 |
|----------|------------------|-----------|------------------------|
| TC-001 | tracking-plan.md Sec 3.1 | Logical_Architecture.drawio | 3+3 标准集群 |
| TC-002 | tech-spec.md Sec 7.1 | Data_Flow.drawio | 元数据节点 8C/32G |

关联规则：
- **tracking-design**：验证埋点方案中的事件/属性是否正确采集和存储
- **tech-design**：验证 LLD 中定义的组件功能、数据流、接口集成是否按设计实现
- **server-sizing**：验证部署规格是否满足性能要求（如数据节点顺序盘容量是否支撑日事件量）
- **draw-diagram**：验证架构图中的数据流路径、组件交互是否正确

**评审 checklist：**
- [ ] 所有 Phase 1 确认的场景都有对应用例
- [ ] 每条用例都有明确的预期结果（可判定通过/失败）
- [ ] P0 用例覆盖所有阻塞上线的核心链路
- [ ] Traceability Matrix 无空白项

**等待客户/PM 确认用例覆盖范围后才能进入 Phase 3。**

### Phase 3：执行验证

按用例逐条执行：
- 记录实际结果
- 对每条用例截图（操作步骤截图 + 结果截图）
- 标记状态：通过 / 失败 / 阻塞（无法执行）
- 失败用例记录复现步骤和实际结果

**执行规范：**
- 按优先级顺序执行：P0 → P1 → P2
- 每日结束时更新测试汇总页
- 阻塞用例 2 小时内必须升级给项目经理

### Phase 4：报告与签字

汇总测试结果，输出测试报告。

**报告模板：**

```markdown
## SIT 测试报告

**项目：** <CLIENT>
**测试时间：** YYYY-MM-DD
**测试环境：** <SA_HOST>/<SA_PROJECT>
**执行人：** ...

### 汇总
- 总用例数：X
- 通过：X（X%）
- 失败：X
- 阻塞：X

### 可追溯矩阵摘要
| 文档类型 | 覆盖用例数 | 未覆盖项 |
|----------|-----------|---------|
| tracking-plan | X | ... |
| tech-design LLD | X | ... |
| server-sizing | X | ... |
| draw-diagram | X | ... |

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
- Traceability Matrix：[链接或附件]
```

**签字流程：**
1. 测试报告发送给客户/项目经理
2. 所有 P0 通过 → 客户签字确认《SIT 验收确认书》
3. 存在 P0 失败 → 客户书面确认接受风险后签字
4. 签字版报告归档至 `$PROJECT_DIR/deliverables/sit/`

## 输出文件规范

```bash
$PROJECT_DIR/sit/
├── sit_test_plan.md              # Phase 1 测试计划
├── sit_test_cases.xlsx           # Phase 2 测试用例（基于模板）
├── sit_traceability_matrix.md    # Phase 2 可追溯矩阵
├── sit_execution_log/            # Phase 3 执行日志和截图
│   ├── TC-001/
│   ├── TC-002/
│   └── ...
├── sit_test_report.md            # Phase 4 测试报告
└── sit_signoff/                  # Phase 4 签字确认
    └── sit_acceptance_signoff_<CLIENT>_<日期>.pdf
```

## 常见问题

**客户要求跳过用例设计直接测试：** 解释没有用例无法出具正式测试报告，且无法证明覆盖了哪些场景。最少也要有一个场景清单。

**测试环境数据不足：** 使用 tracking-setup-e2e skill 生成模拟数据后再执行测试。

**P0 用例失败但客户坚持上线：** 书面记录风险，要求客户签字确认，在报告中注明"客户知情并接受风险"。

**Traceability Matrix 中某项无对应用例：** 说明该设计文档中的功能/规格未在 SIT 中验证，需在报告中明确标注"未覆盖"及理由（如"该功能在 UAT 阶段验证"或"该规格由性能测试覆盖"）。

## Feedback

使用过程中发现问题或有改进建议，随时调用 `/sd-feedback <描述>` 记录，无需中断当前工作。
