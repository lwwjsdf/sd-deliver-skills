# 小程序预置事件场景值生成方案

**项目**：tracking-setup-e2e / westk  
**日期**：2026-05-22  
**状态**：待评审  

---

## 1. 需求背景

当前造数脚本生成 `$MPLaunch`、`$MPShow`、`$MPHide`、`$MPPageLeave` 等微信小程序预置事件时，属性值由 `TrackingPlan.generate_value()` 按类型随机生成，缺乏真实感。需要在所有 `$MP*` 预置事件中注入：

- **`$scene`**：场景值，按真实用户比例分布（参考 [微信场景值文档](https://developers.weixin.qq.com/miniprogram/dev/reference/scene-list.html)）
- **其他常用预置属性**：`$url`、`$referrer`、`$utm_source` 等

---

## 2. 目标

| 目标 | 说明 |
|------|------|
| 真实性 | 场景值按微信真实用户行为比例分布，而非均匀随机 |
| 完整性 | 覆盖所有 `$MP*` 预置事件（`$MPLaunch`、`$MPShow`、`$MPHide`、`$MPPageLeave`、`$MPPageShow`、`$MPClick` 等） |
| 可配置 | 支持在 `business_logic.yaml` 中自定义场景值分布和 URL 模式 |
| 向后兼容 | 不影响现有自定义事件的生成逻辑 |

---

## 3. 场景值分布设计

基于微信场景值列表（1000-1346），按真实用户行为频率分为 8 组：

| 场景分组 | 包含场景值 | 权重 | 说明 |
|---------|-----------|------|------|
| 下拉/最近使用 | 1001, 1089, 1103, 1104, 1271 | 25% | 微信主界面下拉、最近使用列表 |
| 分享/消息卡片 | 1007, 1008, 1044, 1073, 1074, 1096, 1185, 1202, 1207, 1208 | 20% | 单聊/群聊分享、订阅消息、聊天记录 |
| 搜索 | 1005, 1006, 1027, 1053, 1106, 1183, 1232, 1245, 1252, 1297 | 18% | 顶部搜索框、搜一搜、发现页搜索 |
| 扫码 | 1011, 1012, 1013, 1047, 1048, 1049, 1025, 1031, 1032, 1150 | 12% | 二维码、小程序码、一维码 |
| 公众号/文章 | 1035, 1043, 1058, 1067, 1091, 1157, 1158, 1184, 1261, 1305 | 10% | 公众号菜单、文章、模板消息 |
| 小程序互跳 | 1037, 1038, 1135, 1168, 1169 | 8% | 小程序打开小程序、App 分享 |
| 支付/卡包 | 1019, 1028, 1029, 1034, 1057, 1071, 1072, 1097 | 4% | 支付完成页、卡包、钱包 |
| 其他 | 1000, 1010, 1014, 1017, 1023, 1024, 1030, 1036, 1039, 1042, 1045, 1046, 1052, 1054, 1056, 1059, 1060, 1064, 1065, 1068, 1069, 1077, 1078, 1079, 1081, 1082, 1084, 1088, 1090, 1092, 1095, 1099, 1100, 1101, 1102, 1107, 1113, 1114, 1119, 1120, 1121, 1124, 1125, 1126, 1129, 1131, 1133, 1144, 1145, 1146, 1148, 1151, 1152, 1153, 1154, 1155, 1160, 1167, 1171, 1173, 1175, 1176, 1177, 1178, 1179, 1181, 1186, 1187, 1189, 1191, 1192, 1193, 1194, 1195, 1196, 1197, 1198, 1200, 1201, 1203, 1206, 1212, 1215, 1216, 1217, 1218, 1219, 1220, 1223, 1224, 1225, 1226, 1228, 1230, 1231, 1233, 1238, 1239, 1242, 1243, 1244, 1248, 1254, 1255, 1256, 1257, 1258, 1259, 1260, 1265, 1266, 1267, 1272, 1273, 1274, 1275, 1276, 1277, 1278, 1279, 1280, 1281, 1282, 1285, 1286, 1287, 1292, 1293, 1295, 1296, 1298, 1299, 1300, 1301, 1302, 1303, 1304, 1306, 1307, 1308, 1311, 1313, 1325, 1326, 1327, 1328, 1336, 1337, 1340, 1346 | 3% | 收藏、广告、企业微信、硬件设备等 |

**总计**：约 130+ 个有效场景值，覆盖微信所有入口。

---

## 4. 预置事件属性映射

不同 `$MP*` 事件注入不同属性组合：

| 事件 | 注入属性 | 说明 |
|------|---------|------|
| `$MPLaunch` | `$scene`, `$url`, `$referrer`, `$query`, `$utm_source`, `$utm_medium`, `$utm_campaign` | 小程序启动，场景值必选 |
| `$MPShow` | `$scene`, `$url`, `$referrer`, `$query`, `$utm_source`, `$utm_medium`, `$utm_campaign` | 小程序切前台，场景值必选 |
| `$MPHide` | `$url` | 切后台，保留当前页面 |
| `$MPPageLeave` | `$url`, `$referrer`, `$duration` | 页面离开，记录停留时长 |
| `$MPPageShow` | `$url`, `$referrer`, `$query` | 页面显示 |
| `$MPClick` | `$element_content`, `$element_type`, `$element_id`, `$url` | 元素点击 |
| `$MPShare` | `$scene`, `$url`, `$share_title`, `$share_path` | 分享事件 |

**属性生成规则**：

| 属性 | 生成规则 |
|------|---------|
| `$scene` | 按权重分组随机选取场景值（整数） |
| `$url` | 基于 `business_logic.yaml` 中配置的 `page_routes` 随机选取，或默认 `/pages/index/index` |
| `$referrer` | 上一个 `$url`，首次为空 |
| `$query` | 根据页面类型生成，如 `?id=123&source=search` |
| `$utm_source` | 根据 `$scene` 映射：`search` → 搜索，`share` → 分享，`qrcode` → 扫码 等 |
| `$utm_medium` | 细分来源：`wechat_search`、`friend_share`、`group_share`、`scan_qrcode` 等 |
| `$utm_campaign` | 可选，用于活动页：`spring_festival_2026`、`member_day` 等 |
| `$duration` | 页面停留时长（秒），随机 5-300 |
| `$element_content` | 点击元素文本，如 "立即购买"、"查看详情" |
| `$element_type` | 元素类型：`button`、`link`、`image`、`tab` |
| `$element_id` | 元素 ID，如 `btn_buy_001` |
| `$share_title` | 分享标题，如 "快来参加这个活动！" |
| `$share_path` | 分享路径，如 `/pages/event/detail?id=123` |

---

## 5. 技术实现方案

### 5.1 新增文件

#### `tracking-setup-e2e/refrences/mp_scene_values.yaml`

场景值参考数据，包含所有有效场景值及其分组权重。

```yaml
# 微信小程序场景值列表
# 来源：https://developers.weixin.qq.com/miniprogram/dev/reference/scene-list.html
# 权重基于真实用户行为频率估算

scene_groups:
  - name: "下拉/最近使用"
    weight: 0.25
    scenes:
      - { id: 1001, desc: "发现页小程序「最近使用」列表" }
      - { id: 1089, desc: "微信聊天主界面下拉「最近使用」栏" }
      - { id: 1103, desc: "发现页小程序「我的小程序」列表" }
      - { id: 1104, desc: "微信聊天主界面下拉「我的小程序」栏" }
      - { id: 1271, desc: "微信聊天主界面下拉「我的常用小程序」栏" }

  - name: "分享/消息卡片"
    weight: 0.20
    scenes:
      - { id: 1007, desc: "单人聊天会话中的小程序消息卡片" }
      - { id: 1008, desc: "群聊会话中的小程序消息卡片" }
      - { id: 1044, desc: "带 shareTicket 的小程序消息卡片" }
      - { id: 1073, desc: "客服消息列表下发的小程序消息卡片" }
      - { id: 1074, desc: "公众号会话下发的小程序消息卡片" }
      - { id: 1096, desc: "聊天记录，打开小程序" }
      - { id: 1185, desc: "群公告" }
      - { id: 1202, desc: "企微客服号会话打开小程序卡片" }
      - { id: 1207, desc: "企微客服号会话打开小程序文字链" }
      - { id: 1208, desc: "聊天打开商品卡片" }

  # ... 其他分组（详见完整文件）

# UTM 映射规则：根据场景值 ID 范围映射 utm_source/utm_medium
utm_mapping:
  search:
    scene_range: [1005, 1006, 1027, 1053, 1106, 1183, 1232, 1245, 1252, 1297]
    utm_source: "wechat_search"
    utm_medium: "mini_program_search"
  share:
    scene_range: [1007, 1008, 1044, 1073, 1074, 1096, 1185, 1202, 1207, 1208]
    utm_source: "wechat_share"
    utm_medium: "mini_program_card"
  qrcode:
    scene_range: [1011, 1012, 1013, 1047, 1048, 1049, 1025, 1031, 1032, 1150]
    utm_source: "qrcode"
    utm_medium: "scan"
  # ... 其他映射
```

#### `tracking-setup-e2e/scripts/mp_preset_builder.py`

核心模块，负责：
1. 加载 `mp_scene_values.yaml`
2. 按权重分组生成 `$scene` 值
3. 根据场景值映射 UTM 参数
4. 为不同 `$MP*` 事件生成配套属性

```python
class MpPresetBuilder:
    def __init__(self, scene_values_path: str, page_routes: Optional[List[str]] = None):
        # 加载场景值配置
        # 初始化页面路由（从 business_logic.yaml 或默认）
        
    def generate_scene(self) -> int:
        """按权重随机生成场景值"""
        
    def generate_utm(self, scene_id: int) -> Dict[str, str]:
        """根据场景值生成 UTM 参数"""
        
    def build_launch_props(self) -> Dict[str, Any]:
        """生成 $MPLaunch/$MPShow 属性"""
        
    def build_page_props(self, current_url: str, referrer: str = "") -> Dict[str, Any]:
        """生成页面相关属性"""
        
    def build_click_props(self, element_type: str = "button") -> Dict[str, Any]:
        """生成点击事件属性"""
```

### 5.2 修改文件

#### `event_sequencer.py`

在 `_build_properties` 方法中，检测事件名以 `$MP` 开头时，调用 `MpPresetBuilder` 注入预置属性：

```python
def _build_properties(self, edef: EventDef, user: User, context: dict) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    
    # 1. 固定字段（来自 YAML）
    if edef.fields:
        props.update(edef.fields)
    
    # 2. 预置事件属性注入（新增）
    if edef.event.startswith("$MP"):
        preset_props = self._build_preset_props(edef.event, context)
        # 预置属性优先级：YAML fields > 预置属性 > schema 随机值
        for k, v in preset_props.items():
            if k not in props:
                props[k] = v
    
    # 3. 填充剩余 schema 属性
    schema = self.tracking_plan.get_event_schema(edef.event)
    if schema:
        for prop_def in schema.properties:
            if prop_def.name not in props:
                props[prop_def.name] = self.tracking_plan.generate_value(prop_def)
    
    return props

def _build_preset_props(self, event_name: str, context: dict) -> Dict[str, Any]:
    """为预置事件生成真实属性"""
    if not hasattr(self, '_mp_builder'):
        self._mp_builder = MpPresetBuilder("refrences/mp_scene_values.yaml")
    
    if event_name in ("$MPLaunch", "$MPShow"):
        return self._mp_builder.build_launch_props()
    elif event_name in ("$MPPageShow", "$MPPageLeave"):
        current_url = context.get("current_url", "/pages/index/index")
        referrer = context.get("referrer", "")
        return self._mp_builder.build_page_props(current_url, referrer)
    elif event_name == "$MPClick":
        return self._mp_builder.build_click_props()
    # ... 其他预置事件
    return {}
```

同时需要在事件生成过程中维护 `context["current_url"]` 和 `context["referrer"]` 状态，确保页面流转真实。

#### `generate_mock_data.py`

在 `run_rules_mode` 中，初始化 `EventSequencer` 时传入 `MpPresetBuilder` 配置：

```python
# 在 run_rules_mode 中
sequencer = EventSequencer(engine, plan)
# 新增：传入预设事件配置
preset_config = engine.get_preset_events()  # 从 business_logic.yaml 读取
sequencer.set_preset_config(preset_config)
```

#### `business_logic.yaml`

新增可选的 `preset_events` 配置节：

```yaml
# 新增：预置事件配置（可选，不写则用默认值）
preset_events:
  scene_distribution:
    # 可覆盖默认权重
    下拉/最近使用: 0.30
    分享/消息卡片: 0.25
    搜索: 0.20
    扫码: 0.10
    公众号/文章: 0.08
    小程序互跳: 0.04
    支付/卡包: 0.02
    其他: 0.01
  
  page_routes:
    # 小程序页面路由池
    - /pages/index/index
    - /pages/event/list
    - /pages/event/detail
    - /pages/ticket/buy
    - /pages/member/center
    - /pages/search/result
    
  utm_campaigns:
    # 可选的营销活动
    - spring_festival_2026
    - member_day
    - new_user_gift
```

#### `rule_engine.py`

新增 `get_preset_events()` 方法：

```python
def get_preset_events(self) -> Dict[str, Any]:
    return dict(self._data.get("preset_events", {}))
```

### 5.3 数据流图

```
business_logic.yaml ──┬──> RuleEngine ──> get_preset_events()
                      │
mp_scene_values.yaml ─┴──> MpPresetBuilder ──> generate_scene()/build_*_props()
                                                  │
                                                  ▼
event_sequencer.py ──> _build_properties() ──> 注入 $scene/$url/$referrer/UTM
                                                  │
                                                  ▼
generate_mock_data.py ──> run_rules_mode() ──> 输出带真实预置属性的 JSONL
```

---

## 6. 示例输出

生成的事件记录示例：

```json
{
  "distinct_id": "CRM-UAT-X01",
  "event": "$MPLaunch",
  "time": 1717123456789,
  "properties": {
    "$scene": 1007,
    "$url": "/pages/event/detail?id=123",
    "$referrer": "/pages/event/list",
    "$query": "id=123&source=share",
    "$utm_source": "wechat_share",
    "$utm_medium": "mini_program_card",
    "$utm_campaign": "spring_festival_2026",
    "$lib": "python",
    "$lib_version": "1.0.0",
    "platformType": "MP",
    "applicationName": "WeChat",
    "version": "1.0.0",
    "isSuccess": true
  }
}
```

---

## 7. 实施步骤

| 步骤 | 文件 | 工作量 | 优先级 |
|------|------|--------|--------|
| 1 | 创建 `mp_scene_values.yaml` | 中（需整理 130+ 场景值） | P0 |
| 2 | 创建 `mp_preset_builder.py` | 中（核心逻辑） | P0 |
| 3 | 修改 `event_sequencer.py` | 小（注入逻辑） | P0 |
| 4 | 修改 `generate_mock_data.py` | 小（初始化逻辑） | P1 |
| 5 | 修改 `rule_engine.py` | 小（新增方法） | P1 |
| 6 | 更新 `business_logic.yaml` | 小（可选配置） | P2 |
| 7 | 测试验证 | 中（跑通造数流程） | P0 |

---

## 8. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 场景值权重不准确 | 数据分布不真实 | 提供可配置项，用户可调整 |
| 预置属性与 schema 冲突 | 属性被覆盖或重复 | 优先级：YAML fields > 预置属性 > schema 随机值 |
| 页面路由不匹配业务 | URL 不真实 | 支持在 business_logic.yaml 中自定义 page_routes |
| 新增模块引入 bug | 造数失败 | 充分测试，保持向后兼容 |

---

## 9. 待确认事项

1. **场景值权重**：当前权重基于经验估算，是否需要根据真实业务数据调整？
2. **页面路由**：westk 小程序的实际页面路径有哪些？是否需要从业务方获取？
3. **UTM 活动**：当前列出 3 个示例活动，是否需要更多？
4. **其他预置属性**：是否需要支持 `$screen_width`、`$screen_height`、`$network_type` 等设备属性？
5. **优先级**：是否需要优先实施某一部分（如先只做 `$scene`）？

---

**文档结束**
