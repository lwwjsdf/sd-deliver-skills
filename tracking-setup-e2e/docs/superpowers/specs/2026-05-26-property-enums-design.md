# 业务属性枚举值设计

**日期**: 2026-05-26  
**状态**: 已批准  
**范围**: tracking-setup-e2e 规则驱动造数模式

---

## 背景

UAT 造数反馈：部分属性值不符合业务逻辑，生成了随机字符串。根因是 Excel 埋点方案中这些属性的 description 列没有用枚举格式书写，导致 `_extract_enum_values` 无法解析，fallback 到随机值。

受影响属性：

| 属性名 | 问题 | 期望值 |
|--------|------|--------|
| `seatArea` | 随机字符串 | `Stalls` / `Balcony` |
| `seatRow` | 随机字符串 | `A`-`H` 排 |
| `seatCol` | 随机字符串 | 27-40 列号 |
| `ticketType` | 部分事件解析失败 | `标准票` / `全馆通行票` |
| `productShowSchedule` | 格式错误（ISO-8601） | `2025/08/26 19:45:00` |
| `productOperatingSchedule` | 随机字符串 | `2025.08.14 - 2025.10.21` |

---

## 设计

### 方案选择

采用方案 A：在 `business_logic.yaml` 新增 `property_enums` 区块集中管理业务枚举，通过 `RuleEngine` 读取后注入 `EventSequencer`。

理由：业务枚举属于 westk 项目规则，放在 YAML 里集中管理，改值不需要动代码。

### 数据结构

`business_logic.yaml` 新增 `property_enums` 区块，支持两种格式：

**简单列表**（直接 random.choice）：
```yaml
property_enums:
  seatArea: ["Stalls", "Balcony"]
  seatRow: ["A", "B", "C", "D", "E", "F", "G", "H"]
  seatCol: [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
  ticketType: ["标准票", "全馆通行票"]
```

**结构化生成器**（需要格式化逻辑）：
```yaml
property_enums:
  productOperatingSchedule:
    type: date_range
    format: "{start} - {end}"
    date_format: "%Y.%m.%d"
    start_range: ["2025-06-01", "2025-09-01"]
    duration_days: [60, 120]
  productShowSchedule:
    type: datetime
    format: "%Y/%m/%d %H:%M:%S"
    range: ["2025-06-01", "2025-12-31"]
```

### 组件设计

**`rule_engine.py`**  
新增 `get_property_enums() -> dict`，返回 `property_enums` 原始 dict（无则返回空 dict）。

**`event_sequencer.py`**  
新增 `PropertyEnumResolver` 类：
- `__init__(enums: dict)`：接收 `get_property_enums()` 返回值
- `resolve(name: str) -> Optional[Any]`：
  - 简单列表 → `random.choice(list)`
  - `type: date_range` → 随机 start（在 start_range 内）+ 随机 duration（在 duration_days 范围内），格式化为 `date_format`，拼接成 `"{start} - {end}"`
  - `type: datetime` → 随机日期时间（在 range 内），格式化为 `format`
  - 未匹配 → `None`（交给后续 tracking_plan.generate_value 处理）

`_build_properties` 更新后优先级：
1. `edef.fields`（YAML 固定值）
2. `$MP*` 预置属性
3. `PropertyEnumResolver.resolve(name)`（新增）
4. `tracking_plan.generate_value()`（原有 fallback）

### 数据流

```
business_logic.yaml (property_enums)
  └─ RuleEngine.get_property_enums()
       └─ EventSequencer.__init__ → PropertyEnumResolver
            └─ _build_properties step 3
                 └─ 业务合规属性值
```

### 影响范围

| 文件 | 改动类型 |
|------|---------|
| `rules/special/westk/business_logic.yaml` | 新增 `property_enums` 区块 |
| `scripts/rule_engine.py` | 新增 `get_property_enums()` 方法 |
| `scripts/event_sequencer.py` | 新增 `PropertyEnumResolver`，修改 `_build_properties` |

不改动 `tracking_plan.py`，不影响简单模式（非规则驱动路径）。

---

## 验收标准

- `Product_Payment_Detail` 事件的 `seatArea` 值为 `Stalls` 或 `Balcony`
- `seatRow` 值为 A-H 之一
- `seatCol` 值为 27-40 之间的整数
- `ticketType` 值为 `标准票` 或 `全馆通行票`
- `productShowSchedule` 格式为 `YYYY/MM/DD HH:MM:SS`
- `productOperatingSchedule` 格式为 `YYYY.MM.DD - YYYY.MM.DD`
