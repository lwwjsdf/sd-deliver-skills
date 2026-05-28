# WestK UAT 测试数据集生成 - 实施计划文档

## 1. 项目概述

### 1.1 目标
为 WestK CDP+MAE PoC 项目生成 UAT 测试数据集，支持复杂业务规则驱动的事件序列生成。

### 1.2 范围
- **Phase 1**: 8 个固定测试账号（UAT-X01~X08）的完整事件序列
- **Phase 2**: 批量生成（7500 用户，60 天）
- **Phase 3**: 抽象为通用规则系统

### 1.3 输入
- **埋点方案（Phase 1/2）**: `refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx`（小程序渠道）
- **埋点方案（Phase 3 扩展）**: `refrences/Annex 3 - Tracking Plan - eDM_V0.1.xlsx`（eDM 渠道，Salesforce 数据源，与 MP 生成逻辑不同，暂不纳入）
- **业务规则**: `refrences/UAT_TestDataset_BusinessLogic_v1.docx`
- **规则文件**: `rules/special/westk/business_logic.yaml`（由 `scripts/docx_to_yaml_skeleton.py` 生成骨架后人工补充）

### 1.4 输出
- 神策 JSONL 格式事件数据（每行一个 JSON 对象）
- 标准 batch import 格式（JSON 数组）
- Markdown 验证报告
- ID Mapping 验证文件

---

## 2. 架构设计

### 2.1 核心原则
- **代码通用化**: 代码文件不出现项目特定命名（如 westk）
- **规则驱动**: 所有业务逻辑通过 YAML 规则文件配置
- **可扩展**: 支持未来其他项目的规则文件

### 2.2 模块架构

```
┌─────────────────────────────────────────┐
│           generate_mock_data.py         │
│              (主入口/CLI)                │
├─────────────────────────────────────────┤
│            rule_engine.py               │
│      (通用规则引擎 - 解析YAML)            │
│  ├─ 用户分层管理                         │
│  ├─ ID 生成器                           │
│  ├─ 事件序列定义                         │
│  └─ 约束规则                             │
├─────────────────────────────────────────┤
│           tracking_plan.py              │
│      (埋点方案解析器 - 解析Excel)         │
│  ├─ 事件 schema 查询                    │
│  ├─ 公共属性                            │
│  └─ 用户属性字段                         │
├─────────────────────────────────────────┤
│      fixed_account_generator.py         │
│      (固定账号生成器)                     │
├─────────────────────────────────────────┤
│         event_sequencer.py              │
│       (事件序列引擎 - 状态机)             │
├─────────────────────────────────────────┤
│       constraint_validator.py           │
│         (约束验证器)                      │
├─────────────────────────────────────────┤
│        report_generator.py              │
│      (Markdown 报告生成器)               │
└─────────────────────────────────────────┘

scripts/docx_to_yaml_skeleton.py          # 一次性工具：从 docx 提取表格生成 YAML 骨架
```

---

## 3. 模块详细设计

### 3.1 rule_engine.py - 通用规则引擎

#### 职责
- 解析任意 YAML 规则文件
- 提供规则查询接口给其他模块

#### 核心类

```python
class RuleEngine:
    """通用规则引擎"""
    
    def __init__(self, rule_path: str):
        """加载并解析规则文件"""
        
    def get_user_segments(self) -> List[UserSegment]:
        """获取用户分层定义"""
        
    def get_identity_priority(self) -> List[IdentityDef]:
        """获取 ID 优先级定义"""
        
    def get_event_sequences(self) -> List[EventSequence]:
        """获取事件序列定义"""
        
    def get_fixed_accounts(self) -> List[FixedAccount]:
        """获取固定测试账号"""
        
    def get_constraints(self) -> List[Constraint]:
        """获取约束规则"""
        
    def get_enum_values(self, field_name: str) -> List[str]:
        """获取字段枚举值"""
```

#### 支持的数据结构

```python
@dataclass
class UserSegment:
    """用户分层"""
    name: str                          # L0/L1/L2/L3/L4
    ratio: float                       # 占比，所有 segment 的 ratio 之和应为 1.0
    identities: List[str]              # 拥有的 ID 类型列表
    has_registration: bool             # 是否有注册
    has_purchase: bool                 # 是否有购买
    has_membership: bool               # 是否有会员卡购买
    membership_activated: bool         # 是否已激活会员
    # 注：区域分布为全局配置，不在 segment 级别定义

    def __post_init__(self):
        """校验 ratio 合法性"""
        if not (0 < self.ratio <= 1.0):
            raise ValueError(f"Segment '{self.name}' ratio must be in (0, 1]")

@dataclass
class IdentityDef:
    """ID 定义（优先级）"""
    name: str                          # 如 "crm_master_id"
    priority: int                      # 优先级（0 最高）
    display: str                       # 显示名
    sa_key: str                        # 神策 identity key（如 $identity_login_id）

@dataclass
class EventDef:
    """单个事件定义（在序列中）"""
    event: str                         # 事件名
    required: bool                     # 是否必须生成
    time_after_prev: Optional[Dict]    # 与前一个事件的时间间隔 {min, max}（秒）
    conversion_rate: Optional[float]   # 转化率（非必须事件时生效）
    fields: Optional[Dict]             # 固定字段值
    profile_update: Optional[Dict]     # Profile 回写

@dataclass
class EventSequence:
    """事件序列定义"""
    name: str                          # 序列名
    events: List[EventDef]            # 事件列表（线性，互斥终态通过 conversion_rate 控制）
    condition: Optional[str]           # 生效条件字符串
    terminal_states: Optional[List[str]]  # 互斥终态事件名列表（如票务的 Transfer/Refund/Admission）
                                          # EventSequencer 从中随机选一个生成，其余跳过

# 说明：会员卡激活的3个分支（正常/第6-7天/超期）通过3个独立 EventSequence 表达，
# 各自有 condition 和 conversion_rate，由 EventSequencer 按权重选择执行哪条序列。
# 不引入嵌套 branches 结构，保持 EventSequence 扁平化。

@dataclass
class ConditionExpr:
    """
    条件表达式（从字符串解析而来）
    
    YAML 中的条件字符串支持以下语法：
    - "segment in [L1, L2, L3, L4]" → membership 判断
    - "has Product_Order_Payment" → 上下文状态判断
    - "not Ticket_Admission" → 否定判断
    
    解析策略：不使用自定义 DSL，而是将字符串映射为合理的 Python 函数。
    不做 AST 解析，而是在 RuleEngine 初始化时将已知的条件模式编译为
    lambda/函数，直接执行。
    """
    raw: str                           # 原始条件字符串
    evaluator: Callable[[dict], bool]  # 编译后的求值函数

@dataclass
class Constraint:
    """约束规则定义"""
    description: str                   # 约束描述
    constraint_type: str               # 类型: temporal_order | field_consistency | business_rule
    check_fn: Optional[str]            # 验证函数名（用于实时验证）

@dataclass
class FixedAccount:
    """固定测试账号"""
    id: str                            # 账号编号（如 UAT-X01）
    region: str                        # 区域（mainland/hongkong/overseas）
    identities: Dict[str, Optional[str]]  # 身份 ID 映射
    purpose: str                       # 测试目的
    split_identity: bool               # 是否拆分为多用户（如 UAT-X07 反例）
    
    # 当 split_identity=True 时，定义如何拆分
    # 每个 sub_account 是独立的 identity 子集，不共享 CRM ID
    split_groups: Optional[List[Dict[str, str]]]  # 拆分后的各组 identity
```
    
#### Ratio 校验

```python
class RuleEngine:
    def __init__(self, rule_path: str):
        # ... 解析 YAML ...
        self._validate_segment_ratios()

    def _validate_segment_ratios(self):
        """校验所有 segment 的 ratio 之和 ≈ 1.0"""
        total = sum(s.ratio for s in self.segments)
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Segment ratios sum to {total}, expected 1.0. "
                f"Ratios: {[(s.name, s.ratio) for s in self.segments]}"
            )
```

#### business_logic.yaml 结构定义

```yaml
meta:
  project: westk          # 项目标识（用于文件名前缀）
  version: "1.1"
  platforms: [MP, Web]    # 明确排除 Douyin/Rednote

# 全局区域分布（所有 segment 共用）
region_distribution:
  mainland: 0.60
  hongkong: 0.30
  overseas: 0.10

user_segments:
  - name: L0
    ratio: 0.60
    identities: [unionid, cookie_id]
    has_registration: false
    has_purchase: false
    has_membership: false
    membership_activated: false
  - name: L1
    ratio: 0.20
    identities: [mobile_or_email, unionid, cookie_id]  # 大陆用 mobile，港/海外用 email
    has_registration: true
    has_purchase: false
    has_membership: false
    membership_activated: false
  # L2/L3/L4 类似...

identity_priority:
  - name: crm_master_id
    priority: 0
    display: "CRM Master Customer ID"
    sa_key: $identity_login_id
  - name: email
    priority: 1
    display: "Email"
    sa_key: $identity_email
  - name: mobile
    priority: 1
    display: "Mobile"
    sa_key: $identity_mobile
  - name: unionid
    priority: 2
    display: "WeChat UnionID"
    sa_key: $identity_unionid
  - name: cookie_id
    priority: 2
    display: "CookieID"
    sa_key: $identity_anonymous_id

event_sequences:
  - name: user_lifecycle
    condition: null          # 所有用户
    events:
      - event: $MPShow
        required: true
      - event: Registration_Result
        required: true
        time_after_prev: {min: 60, max: 600}
        fields: {isSuccess: true}
        profile_update: {registerTime: "{timestamp}"}
      - event: Login_Result
        required: true
        time_after_prev: {min: 5, max: 30}
        fields: {isSuccess: true}

  - name: ticket_purchase
    condition: "segment in [L2, L3, L4]"
    events:
      - event: Product_Order_Payment
        required: true
        fields: {isSuccess: true}
      - event: Product_Payment_Detail
        required: true
        repeat: "{Product_Order_Payment.ticketsQuantity}"  # 按票数重复
    terminal_states: [Ticket_Transfer, Ticket_Refund, Ticket_Admission]

  # 会员卡激活3个分支：用3条独立序列 + conversion_rate 表达
  - name: membership_normal_activation
    condition: "segment in [L3, L4]"
    conversion_rate: 0.80
    events:
      - event: Membership_Purchase
        required: true
        fields: {isSuccess: true}
      - event: Membership_Activation
        required: true
        time_after_prev: {min: 86400, max: 432000}  # 1-5天内

  - name: membership_late_activation
    condition: "segment in [L3, L4]"
    conversion_rate: 0.10
    events:
      - event: Membership_Purchase
        required: true
        fields: {isSuccess: true}
      - event: Membership_Activation
        required: true
        time_after_prev: {min: 518400, max: 604800}  # 第6-7天

  - name: membership_expired
    condition: "segment in [L3, L4]"
    conversion_rate: 0.10
    events:
      - event: Membership_Purchase
        required: true
        fields: {isSuccess: true}
      - event: Membership_Refund
        required: true
        time_after_prev: {min: 604800, max: 691200}  # 超过7天
        fields: {refundType: "系统作废"}

constraints:
  - type: temporal_order
    description: "Registration 在 Login 前"
    rule: "Registration_Result.time < Login_Result.time"
  - type: temporal_order
    description: "Login 在 Purchase 前"
    rule: "Login_Result.time < Product_Order_Payment.time"
  - type: field_consistency
    description: "票数明细数量等于订单票数"
    rule: "count(Product_Payment_Detail, orderId) == Product_Order_Payment.ticketsQuantity"
  - type: field_consistency
    description: "明细金额之和不超过订单金额"
    rule: "sum(Product_Payment_Detail.ticketPaidAmount) <= Product_Order_Payment.orderPaidAmount"
  - type: business_rule
    description: "Admission 后不可 Refund"
    rule: "not (Ticket_Admission before Ticket_Refund)"
  - type: business_rule
    description: "Voucher 场景严格互斥"
    rule: "voucher.scenario == '项目订单' implies event == Product_Order_Payment"

enums:
  voucher_scenario:
    - value: "项目订单"
      applicable_events: [Product_Order_Payment]
    - value: "商品订单"
      applicable_events: [Merchandise_Order_Payment]

  business_unit:
    - code: M
      name: "M+博物馆"
      venues: ["M+博物馆", "M+地下大堂", "M+戏院", "M+学习中心"]
    - code: S
      name: "香港故宫文化博物馆"
      venues: ["香港故宫文化博物馆"]
    - code: P
      name: "西九演艺"
      venues: ["自由空间大盒", "自由空间小盒", "戏曲中心大剧院"]
    - code: D
      name: "西九文化区"
      venues: ["西九文化区公共空间"]

  voucher_get_type: ["直发", "扫码", "手动领取"]

failure_rate: 0.05   # 全局 isSuccess=false 比例

fixed_accounts:
  - id: UAT-X01
    region: mainland
    segment: L4
    identities:
      crm_master_id: CRM-UAT-X01
      email: x01@test.westk.hk
      mobile: "+86 138-000-0001"
      unionid: wxu_x01
      cookie_id: ck_x01_a
    purpose: "Full 4-ID merge"
    split_identity: false

  - id: UAT-X07
    region: mainland
    segment: L2
    identities:
      email: x07@test.westk.hk
      mobile: "+86 138-0000-0007"
      unionid: wxu_x07
      cookie_id: ck_x07_a
    purpose: "Counter-example: Mobile and Email NOT bound to same CRM ID"
    split_identity: true
    split_groups:
      - {mobile: "+86 138-0000-0007", unionid: wxu_x07}   # MP 用户
      - {email: x07@test.westk.hk, cookie_id: ck_x07_a}  # Web 用户
  # UAT-X02 ~ X06, X08 类似...
```

---

### 3.1.1 scripts/docx_to_yaml_skeleton.py - YAML 骨架生成器

#### 职责
- 一次性工具，从 `UAT_TestDataset_BusinessLogic_v1.docx` 提取表格数据
- 生成 `business_logic.yaml` 骨架，人工补充细节后使用
- 不需要维护，运行一次即可

#### 核心逻辑

```python
"""
从 docx 提取以下内容生成 YAML 骨架：
- Table 1: user_segments（L0-L4 的 ratio、identities）
- Table 2: region_distribution
- Table 3: fixed_accounts 的 IDM 场景（IDM-01~06）
- Table 4: enums.voucher_scenario
- Table 6: enums.business_unit（BU/venue 映射）
- Table 10: fixed_accounts（UAT-X01~X08 的完整 identity 配置）
- Table 11: 预期 SA 用户数（用于验收标准）
"""
import docx
import yaml

def extract_tables(docx_path: str) -> dict:
    doc = docx.Document(docx_path)
    # 按顺序提取所有表格，映射到 YAML 字段
    ...

def main():
    skeleton = extract_tables("refrences/UAT_TestDataset_BusinessLogic_v1.docx")
    with open("rules/special/westk/business_logic.yaml", "w") as f:
        yaml.dump(skeleton, f, allow_unicode=True, default_flow_style=False)
```

---

### 3.2 fixed_account_generator.py - 固定账号生成器

#### 职责
- 根据规则生成确定性测试账号
- 支持特殊规则（如 UAT-X07 的反例逻辑）

#### 核心逻辑

```python
class FixedAccountGenerator:
    """固定测试账号生成器"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine
        
    def generate_accounts(self) -> List[User]:
        """生成所有固定测试账号
        
        当 account_def.split_identity=True 时，按 split_groups 拆分
        为多个独立 User（不同 CRM ID），用于验证 ID Mapping 边界场景
        """
        accounts = []
        for account_def in self.rule_engine.get_fixed_accounts():
            if account_def.split_identity:
                # 通用拆分逻辑：按 split_groups 生成多个独立用户
                for group in account_def.split_groups:
                    user = self._create_user_from_group(account_def, group)
                    accounts.append(user)
            else:
                user = self._create_user(account_def)
                accounts.append(user)
        return accounts
    
    def _create_user(self, account_def: FixedAccount) -> User:
        """创建单个测试账号"""
        pass

    def _create_user_from_group(self, account_def: FixedAccount, 
                                 group: Dict[str, str]) -> User:
        """从拆分组创建测试账号（split_identity 场景）"""
        pass
```

---

### 3.2.1 tracking_plan.py - 埋点方案解析器

#### 职责
- 解析 Annex 6 Excel（Mini Program 渠道）
- 提供事件 schema 查询接口给 EventSequencer
- Phase 1/2 只处理 MP 渠道，eDM 渠道暂不纳入

#### 解析的 Sheet

| Sheet | 用途 |
|-------|------|
| Custom Event | 30+ 自定义事件的属性定义（必填/选填、类型） |
| Preset Event | $MPShow/$MPLaunch 等预置事件属性 |
| Public Property | platformType、applicationName、version（每个事件都带） |
| User Attribute | 31 个用户属性字段（用于 profile 回写） |

#### 核心类

```python
@dataclass
class PropertyDef:
    name: str
    required: bool
    value_type: str        # string / boolean / number / list
    trigger: str           # MP / Server / Web
    enum_values: Optional[List[str]]  # 有枚举约束时非空

@dataclass
class EventSchema:
    event_name: str
    trigger: str           # MP / Server / Web
    properties: List[PropertyDef]

class TrackingPlan:
    """解析埋点方案 Excel，提供事件 schema 查询"""

    def __init__(self, excel_path: str):
        wb = openpyxl.load_workbook(excel_path)
        self._custom_events = self._parse_custom_events(wb["Custom Event"])
        self._preset_events = self._parse_preset_events(wb["Preset Event"])
        self._public_props = self._parse_public_props(wb["Public Property"])
        self._user_attrs = self._parse_user_attrs(wb["User Attribute"])

    def get_event_schema(self, event_name: str) -> EventSchema:
        """返回事件的完整属性定义，包含公共属性"""

    def get_public_properties(self) -> List[PropertyDef]:
        """platformType, applicationName, version"""

    def get_user_attributes(self) -> List[PropertyDef]:
        """31 个用户属性字段"""

    def list_events(self) -> List[str]:
        """返回所有已定义事件名，用于 YAML 校验"""
```

#### Excel 解析注意事项
- Custom Event sheet 的列结构：事件名 | 属性名 | 是否必填 | 类型 | 触发端 | 说明
- 同一事件占多行（每个属性一行），需按事件名分组
- 属性名为空的行是事件标题行，跳过
- `get_event_schema` 返回的属性列表自动合并公共属性

---

### 3.3 event_sequencer.py - 事件序列引擎

#### 职责
- 根据规则生成事件序列
- 管理事件间的时序关系
- 填充事件属性

#### 核心类

```python
class EventSequencer:
    """事件序列引擎"""
    
    def __init__(self, rule_engine: RuleEngine, tracking_plan: TrackingPlan):
        self.rule_engine = rule_engine
        self.tracking_plan = tracking_plan
        
    def generate_sequence(self, user: User, sequence_name: str) -> List[Event]:
        """为用户生成指定事件序列"""
        
    def _apply_temporal_constraints(self, events: List[Event]):
        """应用时间约束"""
        
    def _fill_properties(self, event: Event, user: User):
        """填充事件属性"""
        
    def _apply_correlation_rules(self, events: List[Event]):
        """应用跨事件关联规则"""
```

#### 事件序列类型

1. **用户生命周期序列**
   - $MPShow → Registration → Login → Search/Browse → Order → Payment

2. **会员卡生命周期序列**
   - Membership_Purchase → [Activation | Refund]

3. **票务生命周期序列**
   - Product_Order_Payment → [Transfer → Receive | Refund | Admission]

4. **表单操作序列**
   - Form_Operate × N（每个字段一条）

---

### 3.4 constraint_validator.py - 约束验证器

#### 职责
- 实时验证（生成时）
- 事后验证（生成后）
- 支持多种约束类型

#### 验证类型

```python
class ConstraintValidator:
    """约束验证器"""
    
    def validate_temporal_order(self, events: List[Event]) -> bool:
        """验证事件时序"""
        # Registration 在 Login 前
        # Login 在 Purchase 前
        # Purchase 在 Admission 前
        
    def validate_field_consistency(self, events: List[Event]) -> List[Violation]:
        """验证字段一致性"""
        # 订单明细数量 = 票数
        # 明细金额之和 <= 订单金额
        # 退款金额 <= 订单金额
        
    def validate_business_rules(self, events: List[Event]) -> List[Violation]:
        """验证业务规则"""
        # Admission 后不可 Refund
        # Transfer 过期后不可 Receive
        # Voucher 场景严格匹配
        
    def validate_id_mapping(self, users: List[User]) -> List[Violation]:
        """验证 ID Mapping"""
        # 同一用户的所有 ID 应归并到同一 P0
        # UAT-X07 应识别为 2 个用户
```

---

### 3.5 report_generator.py - 报告生成器

#### 职责
- 生成 Markdown 格式的验证报告
- 包含每个账号的详细检查

#### 报告结构

```markdown
# UAT 测试数据集验证报告

## 1. 生成概览
- 生成时间: 2026-05-22
- 规则文件: rules/special/westk/business_logic.yaml
- 埋点方案: refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx

### 1.1 统计信息
| 指标 | 数值 |
|------|------|
| 总用户数 | 8 |
| 总事件数 | xxx |
| 成功事件 | xxx |
| 失败事件 | xxx |

## 2. 固定测试账号验证

### 2.1 UAT-X01
**身份配置**:
- CRM Master ID: CRM-UAT-X01
- Email: x01@test.westk.hk
- Mobile: +86 138-0000-0001
- UnionID: wxu_x01
- CookieID: ck_x01_a

**事件序列检查**:
| 序号 | 事件 | 时间 | 状态 |
|------|------|------|------|
| 1 | $MPShow | 2026-05-01 09:00 | ✅ |
| 2 | Registration_Result | 2026-05-01 09:05 | ✅ |
| ... | ... | ... | ... |

**约束验证**:
- [x] Registration 在 Login 前
- [x] Login 在 Purchase 前
- [x] 订单金额计算正确

### 2.2 UAT-X02
...

### 2.7 UAT-X07（反例验证）
**预期**: 识别为 2 个独立用户
**验证结果**: ✅ 符合预期

### 2.8 UAT-X08（企业用户）
...

## 3. 业务规则验证

### 3.1 会员卡激活窗口
- 测试场景: 第 6-7 天激活
- 验证结果: ✅

### 3.2 票务生命周期
- Admission 后不可 Refund: ✅
- Transfer 过期后不可 Receive: ✅

### 3.3 优惠券场景
- 项目订单/商品订单严格互斥: ✅

## 4. 边界值测试

| 场景 | 预期 | 实际 | 状态 |
|------|------|------|------|
| 第 6 天激活 | 成功 | 成功 | ✅ |
| 第 7 天激活 | 成功 | 成功 | ✅ |
| 超期未激活 | 自动退卡 | 自动退卡 | ✅ |
| 开场前 1 分钟退票 | 成功 | 成功 | ✅ |

## 5. 问题与建议

...
```

---

## 4. 命令行接口

### 4.1 参数设计

```bash
python3 scripts/generate_mock_data.py \
  --rules <rule_file> \              # 规则文件路径（必填）
  --tracking-plan <excel_file> \     # 埋点方案 Excel（可选，支持交互选择）
  --mode <mode> \                    # 生成模式: fixed-accounts | batch
  --output <directory> \             # 输出目录（默认: mock_data/）
  --prefix <prefix> \                # 文件名前缀（默认: 从规则文件提取）
  --verbose                          # 详细输出
```

### 4.2 交互式选择

```bash
# 未指定 --tracking-plan 时，自动扫描目录
$ python3 scripts/generate_mock_data.py --rules rules/special/westk/business_logic.yaml

发现以下埋点方案文件，请选择：
1. refrences/Annex 3 - Tracking Plan - eDM_V0.1.xlsx
2. refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx
> 2

已选择: refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx
```

---

## 5. 数据结构

### 5.1 用户对象

```python
@dataclass
class User:
    user_id: str                    # 内部用户标识
    segment: str                    # 分层（L0/L1/L2/L3/L4）
    region: str                     # 区域（mainland/hongkong/overseas）
    identities: Dict[str, str]      # ID 映射（遵循优先级）
    profile: Dict[str, Any]         # 用户属性
    created_at: datetime            # 创建时间
```

### 5.2 事件对象 → 神策数据格式映射

内部 `Event` 对象通过 `to_track_record()` 方法转换为神策 batch import 格式。

**神策 data_format=2（batch import）的 track 记录格式：**
```json
{
  "distinct_id": "...",
  "login_id": "...",
  "type": "track",
  "event": "EventName",
  "time": 1234567890000,
  "time_free": true,
  "$is_login_id": true,
  "project": "default",
  "identities": {
    "$identity_login_id": "...",
    "$identity_email": "...",
    "$identity_mobile": "..."
  },
  "properties": {
    "$app_version": "1.0.0",
    "$lib": "python",
    "$lib_version": "1.0.0",
    "platformType": "MP",
    "applicationName": "WeChat",
    "version": "1.0.0",
    "isSuccess": true,
    ...
  }
}
```

**内部 Event 对象：**
```python
@dataclass
class Event:
    event_name: str                 # 事件名
    user: User                      # 关联用户
    timestamp_ms: int               # 事件时间戳（毫秒）
    properties: Dict[str, Any]      # 事件属性
    platform: str                   # 平台（MP/Web）
    is_success: bool                # 是否成功
    failure_reason: Optional[str]   # 失败原因（isSuccess=false 时必填）
    
    def to_track_record(self, project: str, identity_defs: List[IdentityDef]) -> dict:
        """将 Event 对象转换为神策 track 记录格式
        
        复用 generate_mock_data.py 中已有的 build_track_record()
        和 generate_identities() 逻辑。
        """
```

**关键映射关系：**

| 内部字段 | 神策字段 | 说明 |
|---------|---------|------|
| `user.user_id` | `distinct_id`, `login_id`, `identities.$identity_login_id` | 主标识 |
| `user.region` + `user.identities` | `identities.$identity_email`, `identities.$identity_mobile` | 多 ID |
| `event_name` | `event` | 事件名 |
| `timestamp_ms` | `time` | 毫秒时间戳 |
| `properties` + `platform` | `properties` | 合并公共属性 |

注：与现有 `generate_mock_data.py` 中的 `build_track_record()` 和 `build_profile_record()` 保持一致。

---

## 6. 实施步骤

### Phase 1: 固定测试账号（当前）

| 步骤 | 模块 | 工作量 | 依赖 |
|------|------|--------|------|
| 0 | docx_to_yaml_skeleton.py（一次性） | 1h | python-docx |
| 1 | business_logic.yaml 人工补充完善 | 2h | 步骤0输出 |
| 2 | rule_engine.py | 2h | 步骤1 |
| 3 | tracking_plan.py | 2h | openpyxl |
| 4 | fixed_account_generator.py | 2h | rule_engine |
| 5 | event_sequencer.py | 6h | rule_engine, tracking_plan |
| 6 | constraint_validator.py | 3h | event_sequencer |
| 7 | report_generator.py | 2h | constraint_validator |
| 8 | generate_mock_data.py 改造 | 2h | 所有模块 |
| 9 | 集成测试 | 2h | 所有模块 |

**总计**: 约 24 小时

### Phase 2: 批量生成

基于 Phase 1 验证通过的逻辑扩展。

### Phase 3: 通用规则系统

提取 Common Rules，支持其他项目。

---

## 7. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 埋点方案 Excel 格式变化 | 高 | 封装 Excel 解析器，支持多格式 |
| 业务规则过于复杂 | 中 | 分阶段实现，先核心后边缘 |
| 性能问题（大数据量） | 中 | 支持流式生成，分批写入 |
| 规则文件维护 | 低 | 版本控制，文档化 |

---

## 8. 验收标准

### 8.1 功能验收
- [ ] 8 个固定测试账号生成成功
- [ ] 每个账号包含完整事件序列
- [ ] UAT-X07 正确识别为 2 个用户
- [ ] 验证报告生成成功

### 8.2 规则验收
- [ ] 用户分层比例正确（L0:60%, L1:20%, L2:10%, L3:3%, L4:7%）
- [ ] ID 优先级遵循（CRM > Email/Mobile > UnionID/CookieID）
- [ ] 事件时序约束满足
- [ ] 跨事件字段一致性满足

### 8.3 质量验收
- [ ] 代码通用化（无项目特定命名）
- [ ] 单元测试覆盖核心逻辑
- [ ] 文档完整

---

## 9. 附录

### 9.1 依赖库
- `openpyxl`: Excel 解析（TrackingPlan）
- `pyyaml`: YAML 解析（RuleEngine）
- `python-docx`: docx 解析（docx_to_yaml_skeleton.py，一次性）
- `python-dotenv`: 环境变量

### 9.2 参考文档
- `UAT_TestDataset_BusinessLogic_v1.docx`: 业务规则
- `Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx`: 埋点方案

---

**请 review 以上计划，确认后可以开始执行。**
