# Property Enums Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在规则驱动造数模式中，让 `seatArea`、`seatRow`、`seatCol`、`ticketType`、`productShowSchedule`、`productOperatingSchedule` 等属性生成符合业务逻辑的值。

**Architecture:** 在 `business_logic.yaml` 新增 `property_enums` 区块定义业务枚举；`RuleEngine` 新增 `get_property_enums()` 读取该区块；`EventSequencer` 新增 `PropertyEnumResolver` 类，在 `_build_properties` 的 schema fallback 之前介入，用业务枚举值覆盖随机生成。

**Tech Stack:** Python 3.x, PyYAML, dataclasses, datetime

---

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `tracking-setup-e2e/rules/special/westk/business_logic.yaml` | 修改：新增 `property_enums` 区块 |
| `tracking-setup-e2e/scripts/rule_engine.py` | 修改：新增 `get_property_enums()` 方法 |
| `tracking-setup-e2e/scripts/event_sequencer.py` | 修改：新增 `PropertyEnumResolver` 类，修改 `_build_properties` |

---

### Task 1: 在 business_logic.yaml 新增 property_enums 区块

**Files:**
- Modify: `tracking-setup-e2e/rules/special/westk/business_logic.yaml`

- [ ] **Step 1: 在 `constraints:` 区块之前插入 `property_enums` 区块**

在文件 `failure_rate: 0.05` 这一行之前，添加以下内容：

```yaml
property_enums:
  seatArea: ["Stalls", "Balcony"]
  seatRow: ["A", "B", "C", "D", "E", "F", "G", "H"]
  seatCol: [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
  ticketType: ["标准票", "全馆通行票"]
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

- [ ] **Step 2: 验证 YAML 语法正确**

```bash
python3 -c "
import yaml
with open('tracking-setup-e2e/rules/special/westk/business_logic.yaml') as f:
    data = yaml.safe_load(f)
enums = data.get('property_enums', {})
print('property_enums keys:', list(enums.keys()))
assert 'seatArea' in enums
assert 'productShowSchedule' in enums
print('OK')
"
```

期望输出：
```
property_enums keys: ['seatArea', 'seatRow', 'seatCol', 'ticketType', 'productOperatingSchedule', 'productShowSchedule']
OK
```

- [ ] **Step 3: Commit**

```bash
git add tracking-setup-e2e/rules/special/westk/business_logic.yaml
git commit -m "feat(westk): add property_enums to business_logic.yaml"
```

---

### Task 2: rule_engine.py 新增 get_property_enums()

**Files:**
- Modify: `tracking-setup-e2e/scripts/rule_engine.py`

- [ ] **Step 1: 在 `get_preset_events()` 方法之后添加 `get_property_enums()`**

在 `rule_engine.py` 的 `get_preset_events` 方法（约第 179 行）之后插入：

```python
def get_property_enums(self) -> Dict[str, Any]:
    """Return the property_enums block, or empty dict if not defined."""
    return dict(self._data.get("property_enums", {}))
```

- [ ] **Step 2: 验证方法可调用且返回正确数据**

```bash
cd tracking-setup-e2e && python3 -c "
import sys; sys.path.insert(0, 'scripts')
from rule_engine import RuleEngine
engine = RuleEngine('rules/special/westk/business_logic.yaml')
enums = engine.get_property_enums()
print('seatArea:', enums.get('seatArea'))
print('productShowSchedule:', enums.get('productShowSchedule'))
assert enums['seatArea'] == ['Stalls', 'Balcony']
assert enums['productShowSchedule']['type'] == 'datetime'
print('OK')
" && cd ..
```

期望输出：
```
seatArea: ['Stalls', 'Balcony']
productShowSchedule: {'type': 'datetime', 'format': '%Y/%m/%d %H:%M:%S', 'range': ['2025-06-01', '2025-12-31']}
OK
```

- [ ] **Step 3: Commit**

```bash
git add tracking-setup-e2e/scripts/rule_engine.py
git commit -m "feat: add get_property_enums() to RuleEngine"
```

---

### Task 3: event_sequencer.py 新增 PropertyEnumResolver

**Files:**
- Modify: `tracking-setup-e2e/scripts/event_sequencer.py`

- [ ] **Step 1: 在文件顶部 import 区块中补充 datetime 导入**

找到文件顶部的 import 区块（约第 1-20 行），确认有以下导入，如没有则添加：

```python
import datetime as _dt
```

放在 `import random` 之后。

- [ ] **Step 2: 在 `_REPEAT_REF_RE` 常量之后（约第 86 行）插入 `PropertyEnumResolver` 类**

```python
class PropertyEnumResolver:
    """Resolve property values from business_logic.yaml property_enums."""

    def __init__(self, enums: dict):
        self._enums = enums

    def resolve(self, name: str):
        """
        Return a business-compliant value for the given property name.
        Returns None if no enum is defined for this property.

        Supported formats:
          - list: random.choice(list)
          - {type: date_range, ...}: "YYYY.MM.DD - YYYY.MM.DD" string
          - {type: datetime, ...}: "YYYY/MM/DD HH:MM:SS" string
        """
        spec = self._enums.get(name)
        if spec is None:
            return None

        if isinstance(spec, list):
            return random.choice(spec)

        if isinstance(spec, dict):
            t = spec.get("type")

            if t == "date_range":
                date_fmt = spec.get("date_format", "%Y.%m.%d")
                start_range = spec.get("start_range", ["2025-01-01", "2025-06-01"])
                duration_days = spec.get("duration_days", [60, 90])

                start_date = _dt.date.fromisoformat(start_range[0])
                end_start_date = _dt.date.fromisoformat(start_range[1])
                range_days = (end_start_date - start_date).days
                random_start = start_date + _dt.timedelta(days=random.randint(0, max(range_days, 0)))
                duration = random.randint(duration_days[0], duration_days[1])
                random_end = random_start + _dt.timedelta(days=duration)
                return f"{random_start.strftime(date_fmt)} - {random_end.strftime(date_fmt)}"

            if t == "datetime":
                fmt = spec.get("format", "%Y/%m/%d %H:%M:%S")
                date_range = spec.get("range", ["2025-01-01", "2025-12-31"])
                start = _dt.datetime.fromisoformat(date_range[0])
                end = _dt.datetime.fromisoformat(date_range[1])
                delta = end - start
                random_seconds = random.randint(0, int(delta.total_seconds()))
                # Round to nearest 15 minutes for realistic show times
                random_seconds = (random_seconds // 900) * 900
                result = start + _dt.timedelta(seconds=random_seconds)
                return result.strftime(fmt)

        return None
```

- [ ] **Step 3: 在 `EventSequencer.__init__` 中初始化 `PropertyEnumResolver`**

找到 `EventSequencer.__init__` 方法（约第 90 行），在 `self._mp_builder = None` 之后添加：

```python
        # Initialise property enum resolver from rule engine
        self._prop_resolver = PropertyEnumResolver(rule_engine.get_property_enums())
```

完整的 `__init__` 方法应如下：

```python
    def __init__(self, rule_engine: RuleEngine, tracking_plan: TrackingPlan):
        self.rule_engine = rule_engine
        self.tracking_plan = tracking_plan

        # Only initialise MpPresetBuilder if the tracking plan contains MP events
        self._mp_builder = None
        if tracking_plan.has_mp_events():
            preset_cfg = rule_engine.get_preset_events()
            self._mp_builder = MpPresetBuilder(
                page_routes=preset_cfg.get("page_routes"),
                utm_campaigns=preset_cfg.get("utm_campaigns"),
                scene_weights=preset_cfg.get("scene_distribution"),
            )

        # Initialise property enum resolver from rule engine
        self._prop_resolver = PropertyEnumResolver(rule_engine.get_property_enums())
```

- [ ] **Step 4: 修改 `_build_properties` 方法，在 step 3 插入枚举解析**

找到 `_build_properties` 方法（约第 302 行），将 `# 3. Fill remaining schema properties` 这段替换为：

```python
        # 3. Fill remaining schema properties, with property_enums taking priority
        schema = self.tracking_plan.get_event_schema(edef.event)
        if schema:
            for prop_def in schema.properties:
                if prop_def.name not in props:
                    # Try business enum resolver first
                    resolved = self._prop_resolver.resolve(prop_def.name)
                    if resolved is not None:
                        props[prop_def.name] = resolved
                    else:
                        props[prop_def.name] = self.tracking_plan.generate_value(prop_def)

        return props
```

- [ ] **Step 5: 验证 PropertyEnumResolver 独立运行正确**

```bash
cd tracking-setup-e2e && python3 -c "
import sys, random
sys.path.insert(0, 'scripts')
random.seed(42)

import datetime as _dt

# Inline test of PropertyEnumResolver logic
from event_sequencer import PropertyEnumResolver

enums = {
    'seatArea': ['Stalls', 'Balcony'],
    'seatRow': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
    'seatCol': [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
    'ticketType': ['标准票', '全馆通行票'],
    'productOperatingSchedule': {
        'type': 'date_range',
        'format': '{start} - {end}',
        'date_format': '%Y.%m.%d',
        'start_range': ['2025-06-01', '2025-09-01'],
        'duration_days': [60, 120],
    },
    'productShowSchedule': {
        'type': 'datetime',
        'format': '%Y/%m/%d %H:%M:%S',
        'range': ['2025-06-01', '2025-12-31'],
    },
}

resolver = PropertyEnumResolver(enums)

seat_area = resolver.resolve('seatArea')
assert seat_area in ['Stalls', 'Balcony'], f'Bad seatArea: {seat_area}'

seat_row = resolver.resolve('seatRow')
assert seat_row in list('ABCDEFGH'), f'Bad seatRow: {seat_row}'

seat_col = resolver.resolve('seatCol')
assert 27 <= seat_col <= 40, f'Bad seatCol: {seat_col}'

ticket_type = resolver.resolve('ticketType')
assert ticket_type in ['标准票', '全馆通行票'], f'Bad ticketType: {ticket_type}'

op_sched = resolver.resolve('productOperatingSchedule')
parts = op_sched.split(' - ')
assert len(parts) == 2, f'Bad productOperatingSchedule: {op_sched}'
_dt.datetime.strptime(parts[0], '%Y.%m.%d')  # validates format
print('productOperatingSchedule:', op_sched)

show_sched = resolver.resolve('productShowSchedule')
_dt.datetime.strptime(show_sched, '%Y/%m/%d %H:%M:%S')  # validates format
print('productShowSchedule:', show_sched)

none_val = resolver.resolve('unknownProp')
assert none_val is None

print('All assertions passed.')
" && cd ..
```

期望输出（值随机，格式固定）：
```
productOperatingSchedule: 2025.XX.XX - 2025.XX.XX
productShowSchedule: 2025/XX/XX XX:XX:00
All assertions passed.
```

- [ ] **Step 6: 端到端验证：运行规则驱动造数，检查生成数据中的属性值**

```bash
cd tracking-setup-e2e && python3 scripts/generate_mock_data.py \
  --rules rules/special/westk/business_logic.yaml \
  --tracking-plan "refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx" \
  --users 5 \
  --output /tmp/test_enum_output && cd ..
```

然后验证生成的 JSONL 中属性值符合业务逻辑：

```bash
python3 -c "
import json

with open('/tmp/test_enum_output/westk.jsonl') as f:
    records = [json.loads(l) for l in f if l.strip()]

target_props = ['seatArea', 'seatRow', 'seatCol', 'ticketType',
                'productShowSchedule', 'productOperatingSchedule']

found = {p: set() for p in target_props}
for r in records:
    for p in target_props:
        v = r.get('properties', {}).get(p)
        if v is not None:
            found[p].add(str(v))

for prop, values in found.items():
    if values:
        print(f'{prop}: {sorted(values)[:5]}')
    else:
        print(f'{prop}: (not found in output)')
"
```

- [ ] **Step 7: Commit**

```bash
git add tracking-setup-e2e/scripts/event_sequencer.py
git commit -m "feat: add PropertyEnumResolver for business-compliant property values"
```
