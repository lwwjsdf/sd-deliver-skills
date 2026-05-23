# 神策 Open API 客户端模块设计方案

**版本**: v3 (Horizon Schema API)  
**认证**: api-key + sensorsdata-project Header  
**基础路径**: `{host}/api/v3/horizon/v1`

---

## 1. 模块结构

```
tracking-setup-e2e/scripts/
├── sa_openapi.py          # 新增：Open API HTTP 客户端
├── import_meta_data.py    # 修改：用 sa_openapi 替代 browse
└── ...
```

## 2. SAOpenAPI 类设计

```python
class SAOpenAPI:
    """神策 Schema Open API v3 客户端"""
    
    def __init__(self, host: str, api_key: str, project: str):
        """
        Args:
            host: 神策 CDP 地址，如 https://demo.sensorsdata.cn
            api_key: Open API 密钥
            project: 项目名
        """
        self.base_url = f"{host.rstrip('/')}/api/v3/horizon/v1"
        self.api_key = api_key
        self.project = project
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "api-key": api_key,
            "sensorsdata-project": project,
        })
    
    # ── 内部方法 ──
    def _request(self, method: str, path: str, json_data: dict = None) -> dict:
        """统一请求封装，含错误处理、重试、日志"""
        
    def _handle_response(self, resp: dict) -> dict:
        """处理响应，检查 code == 'SUCCESS'"""
        
    # ── 事件管理 (Event Schema) ──
    def create_event(self, original_name: str, display_name: str, 
                     physical_schema: str = "events",
                     custom_params: dict = None,
                     track_platforms: list = None) -> bool
        """创建元事件"""
        # POST /schema/event/create
        # Body: {physical_schema_name, schemas: [{original_name, display_name, custom_params, statistics}]}
        
    def get_event(self, original_name: str, physical_schema: str = "events") -> dict
        """获取事件定义"""
        # POST /schema/event/get
        # Body: {physical_schema_name, original_name}
        
    def update_event(self, schema_name: str, updates: dict, update_mask: str) -> bool
        """更新事件定义"""
        # POST /schema/event/update
        # Body: {schema: {name, ...}, update_mask}
        
    def list_events(self, physical_schema: str = "events", 
                    page_size: int = 100) -> list[dict]
        """获取事件列表"""
        # POST /schema/event/list
        # Body: {physical_schema_name, page_size}
        
    # ── 属性管理 (Schema Field) ──
    def list_event_fields(self, schema_name: str) -> list[dict]
        """获取事件属性列表"""
        # POST /schema/event/field/list
        # Body: {schema_name}
        
    def batch_create_fields(self, fields: list[dict]) -> dict
        """批量创建属性
        
        fields 格式: [
            {
                "schema_name": "events.ViewProduct",
                "field": {
                    "name": "product_id",
                    "display_name": "商品ID",
                    "data_type": {"type": "STRING"},
                    "data_mapping": {"source_type": "MAIN_TABLE_COLUMN"},
                    "custom_params": {"meta_desc": "备注"}
                }
            }
        ]
        """
        # POST /schema/field/batch-create
        
    def update_field(self, schema_name: str, field_name: str, 
                     updates: dict, update_mask: str) -> bool
        """更新属性"""
        # POST /schema/field/update
        
    # ── 用户属性 (User Schema) ──
    def create_user_fields(self, fields: list[dict]) -> dict
        """创建用户属性（schema_name = 'users'）"""
        # 复用 batch_create_fields，schema_name 固定为 "users"
        
    def list_user_fields(self) -> list[dict]
        """获取用户属性列表"""
        # POST /schema/field/list
        # Body: {schema_name: "users"}
```

## 3. 数据类型映射

| Excel 类型 | v2 Web API | v3 Open API (data_type) |
|-----------|-----------|------------------------|
| String | STRING | `{"type": "STRING"}` |
| Number | NUMBER | `{"type": "NUMBER"}` |
| Bool | BOOL | `{"type": "BOOL"}` |
| Datetime | DATETIME | `{"type": "DATETIME"}` |
| List | LIST | `{"type": "LIST", "element_data_types": "STRING"}` |

## 4. import_meta_data.py 重构要点

### 删除的内容
- `_find_browse()` / `BROWSE_BIN`
- `ensure_session()` - 不再需要 cookie 导入
- `_browse()` / `fetch()` - 不再需要 js fetch
- 所有 subprocess 调用

### 替换的内容
```python
# 旧：通过 browse 调用 web API
def create_meta_event(event, fields):
    resp = fetch("/api/v2/horizon/v1/web/event_schema/create?...", ...)
    
# 新：直接调用 Open API
from sa_openapi import SAOpenAPI

api = SAOpenAPI(SA_HOST, API_KEY, SA_PROJECT)

def create_meta_event(event, fields):
    # 1. 创建事件
    success = api.create_event(
        original_name=event["original_name"],
        display_name=event["display_name"],
        track_platforms=[{"platform": "MINI_APP", "has_data": False}]
    )
    if not success:
        return False
    
    # 2. 创建属性（如果有）
    if fields:
        field_descriptors = []
        for f in fields:
            field_descriptors.append({
                "schema_name": f"events.{event['original_name']}",
                "field": {
                    "name": f["name"],
                    "display_name": f["display_name"],
                    "data_type": map_data_type(f["data_type"]),
                    "data_mapping": {"source_type": "MAIN_TABLE_COLUMN"},
                }
            })
        result = api.batch_create_fields(field_descriptors)
        return result.get("code") == "SUCCESS"
    
    return True
```

## 5. 错误处理策略

```python
class SAOpenAPIError(Exception):
    """Open API 调用异常"""
    def __init__(self, message, code=None, request_id=None):
        self.code = code
        self.request_id = request_id
        super().__init__(message)

# 常见错误码处理
ERROR_HANDLERS = {
    "ALREADY_EXISTS": lambda resp: ("warning", "已存在，跳过"),
    "SCHEMA_NOT_FOUND": lambda resp: ("error", "Schema 不存在"),
    "FIELD_NOT_FOUND": lambda resp: ("error", "字段不存在"),
    "INVALID_ARGUMENT": lambda resp: ("error", f"参数错误: {resp.get('message')}"),
}
```

## 6. 与现有代码的兼容性

| 方面 | 处理方案 |
|------|---------|
| `.env` 配置 | 新增 `API_KEY`，保留 `SA_HOST`/`SA_PROJECT` |
| Excel 解析 | 不变，复用现有 `parse_events()`/`parse_event_fields()`/`parse_user_attrs()` |
| 数据类型映射 | 新增 `map_data_type()` 函数，v2→v3 转换 |
| 保留字段过滤 | 不变，复用 `RESERVED_FIELD_NAMES` |
| 输出格式 | 不变，保持相同的打印日志格式 |

## 7. 实施步骤

1. **创建 `sa_openapi.py`** - 实现 SAOpenAPI 类
2. **修改 `import_meta_data.py`** - 替换 browse 为 SAOpenAPI
3. **更新 `.env.example`** - 添加 `API_KEY` 说明
4. **测试** - 验证事件创建、属性创建、用户属性创建

## 8. 待验证事项

1. 用户属性是否通过 `schema/field/batch-create` + `schema_name="users"` 创建？
2. `MINI_APP` 平台标识在 v3 中是否有效？
3. 批量创建属性时，`data_mapping.source_type` 是否必须？
4. 事件更新时，`update_mask` 支持哪些字段？

---

**请 review 以上设计，确认后我开始实施。**
