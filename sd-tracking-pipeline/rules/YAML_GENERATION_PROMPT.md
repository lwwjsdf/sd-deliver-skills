# business_logic.yaml 生成指南

你是一个数据工程 agent，任务是根据业务文档和埋点方案生成 `business_logic.yaml`。
这个文件驱动 UAT 测试数据生成，必须与 Tracking Plan 中的事件名完全一致。

---

## 第一步：读取 Tracking Plan，获取合法事件名

**这一步是必须的。** 在写任何 event_sequences 之前，先运行：

```bash
python3 scripts/yaml_validator.py <yaml_path> \
  --tracking-plan "<tracking_plan_xlsx_path>"
```

或直接用 Python 列出所有合法事件名：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from tracking_plan import TrackingPlan
plan = TrackingPlan('<tracking_plan_xlsx_path>')
for name in plan.list_events():
    print(name)
"
```

将输出的事件名列表记下来。**YAML 中所有 `event:` 字段的值必须来自这个列表，不能自行编造。**

---

## 第二步：判断输入情况，选择生成策略

### 情况 A：有业务需求文档（docx/pdf/文字描述）

读取文档，提取以下信息，映射到 YAML 对应字段：

| 文档中的信息 | 映射到 YAML 字段 |
|-------------|----------------|
| 用户分层定义（注册/购买/会员等） | `user_segments` 的 `has_registration/has_purchase/has_membership` |
| 各层用户占比 | `user_segments[*].ratio`（必须加总为 1.0） |
| 地区分布 | `region_distribution`（mainland/hongkong/overseas，加总为 1.0） |
| 核心业务流程（购票、注册、会员等） | `event_sequences` 中的非 repeatable 序列 |
| 转化率数据（如"80% 用户会激活会员"） | `event_sequences[*].conversion_rate` |
| 固定测试账号需求 | `fixed_accounts` |

### 情况 B：只有 Tracking Plan，无业务文档

直接使用下方的**默认模板**，只需替换 `meta.project` 和 `fixed_accounts`。
默认模板覆盖最常见的 L0-L4 用户分层和基础生命周期，开箱即用。

---

## 第三步：填写 event_sequences

每个 sequence 的 `events` 列表中，每个事件的 `fields` 只能使用该事件在 Tracking Plan 中定义的属性名。

验证方法：
```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from tracking_plan import TrackingPlan
plan = TrackingPlan('<tracking_plan_xlsx_path>')
schema = plan.get_event_schema('<EventName>')
print([p.name for p in schema.properties] if schema else 'not found')
"
```

**repeatable 序列的选取原则：**
- 选择用户每次打开 App/小程序都会触发的事件（页面浏览、搜索、点击）
- 不要把一次性事件（注册、购买、会员开通）放进 repeatable 序列

---

## 第四步：验证

生成 YAML 后必须运行验证，通过后才能造数：

```bash
python3 scripts/yaml_validator.py <yaml_path> \
  --tracking-plan "<tracking_plan_xlsx_path>"
```

- 有 **error**：必须修复，重新生成
- 有 **warning**：检查是否是真实问题，确认无误后可继续
- **PASSED**：可以进入造数步骤

---

## 默认模板

当用户输入不足时，使用此模板。替换 `YOUR_PROJECT` 和 `fixed_accounts` 部分。
`event_sequences` 中的 `event:` 值**必须替换为 Tracking Plan 中实际存在的事件名**。

```yaml
meta:
  project: YOUR_PROJECT
  version: '1.0'
  platforms:
    - MP

region_distribution:
  mainland: 0.6
  hongkong: 0.3
  overseas: 0.1

user_segments:
  L0:
    ratio: 0.6
    identities: [unionid, cookie_id]
    has_registration: false
    has_purchase: false
    has_membership: false
    membership_activated: false
  L1:
    ratio: 0.2
    identities: [mobile_or_email, unionid, cookie_id]
    has_registration: true
    has_purchase: false
    has_membership: false
    membership_activated: false
  L2:
    ratio: 0.1
    identities: [mobile_or_email, unionid, cookie_id]
    has_registration: true
    has_purchase: true
    has_membership: false
    membership_activated: false
  L3:
    ratio: 0.03
    identities: [mobile_or_email, unionid, cookie_id]
    has_registration: true
    has_purchase: true
    has_membership: true
    membership_activated: false
  L4:
    ratio: 0.07
    identities: [mobile_or_email, unionid, cookie_id]
    has_registration: true
    has_purchase: true
    has_membership: true
    membership_activated: true

identity_priority:
  crm_master_id:
    priority: 0
    display: CRM Master Customer ID
    sa_key: $identity_login_id
  email:
    priority: 1
    display: Email
    sa_key: $identity_email
  mobile:
    priority: 1
    display: Mobile
    sa_key: $identity_mobile
  unionid:
    priority: 2
    display: WeChat UnionID
    sa_key: $identity_unionid
  cookie_id:
    priority: 2
    display: CookieID
    sa_key: $identity_anonymous_id

event_sequences:
  # ── 生命周期（所有用户，只跑一次）──────────────────────────────
  - name: user_lifecycle
    condition: null
    repeatable: false
    events:
      - event: REPLACE_WITH_APP_OPEN_EVENT       # 替换为 Tracking Plan 中的小程序启动事件
        required: true
      - event: REPLACE_WITH_REGISTRATION_EVENT   # 替换为注册事件
        required: true
        time_after_prev: {min: 60, max: 600}
        fields:
          isSuccess: true
      - event: REPLACE_WITH_LOGIN_EVENT          # 替换为登录事件
        required: true
        time_after_prev: {min: 5, max: 30}
        fields:
          isSuccess: true

  # ── 日常浏览（所有用户，每 session 重复）──────────────────────
  - name: daily_activity
    condition: null
    repeatable: true
    events:
      - event: REPLACE_WITH_PAGE_VIEW_EVENT      # 替换为页面浏览事件
        required: true
      - event: REPLACE_WITH_DETAIL_VIEW_EVENT    # 替换为详情页事件
        required: true
        time_after_prev: {min: 5, max: 60}

  # ── 购买转化（L2/L3/L4，只跑一次）────────────────────────────
  - name: purchase
    condition: segment in [L2, L3, L4]
    repeatable: false
    events:
      - event: REPLACE_WITH_PAYMENT_EVENT        # 替换为支付事件
        required: true
        time_after_prev: {min: 300, max: 3600}
        fields:
          isSuccess: true

failure_rate: 0.05

fixed_accounts:
  - id: UAT-001
    region: mainland
    segment: L4
    email: uat001@test.example.com
    mobile: '+86 138-0000-0001'
    unionid: wxu_uat001
    cookie_id: ck_uat001
    split_identity: false
  - id: UAT-002
    region: hongkong
    segment: L2
    email: uat002@test.example.com
    unionid: wxu_uat002
    cookie_id: ck_uat002
    split_identity: false
```

---

## 常见错误和修复

| 错误信息 | 原因 | 修复方法 |
|---------|------|---------|
| `Event 'X' not found in Tracking Plan` | 事件名拼写错误或不在 Tracking Plan 中 | 用第一步的列表核对，替换为正确名称 |
| `Ratios sum to X, must equal 1.0` | segment 或 region 比例加总不为 1 | 调整各项比例，确保加总精确为 1.0 |
| `min (X) > max (Y)` | time_after_prev 的 min 大于 max | 交换两个值 |
| `Property 'X' not found in schema` | fields 中使用了该事件没有的属性 | 用第三步的方法查询该事件的合法属性列表 |
| `Duplicate sequence name` | 两个 sequence 同名 | 重命名其中一个 |
