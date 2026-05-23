# tracking-setup-e2e Skill 重构实施文档

**版本**: v2.0  
**日期**: 2026-05-23  
**状态**: 待评审

---

## 一、目标

将现有 `tracking-setup-e2e` skill 与 `shared/postman/sensors_openapi.py` 通用 SDK 整合，实现：

1. **统一 OpenAPI 客户端** - 所有 skill 共用 `shared/postman/sensors_openapi.py`
2. **更友好的配置系统** - 命令行参数 + 交互式提示，无需手动编辑 `.env`
3. **条件化小程序支持** - 仅在埋点方案包含小程序事件时触发预置属性生成
4. **更完善的错误处理** - 明确错误信息，防止 Agent 绕过

---

## 二、现状分析

### 2.1 当前文件结构

```
tracking-setup-e2e/
├── scripts/
│   ├── sa_openapi.py          # 当前 Schema API 客户端（需替换）
│   ├── import_meta_data.py    # 元数据导入（刚改进配置系统）
│   ├── import_mock_data.py    # 数据导入（刚改进配置系统）
│   ├── generate_mock_data.py  # 数据生成
│   ├── event_sequencer.py     # 事件序列生成
│   ├── mp_preset_builder.py   # 小程序预置属性
│   ├── tracking_plan.py       # 埋点方案解析
│   └── ...
```

### 2.2 当前问题

| 问题 | 影响 | 解决方案 |
|------|------|---------|
| `sa_openapi.py` 与 `shared/postman/sensors_openapi.py` 重复 | 维护成本高 | 统一使用 shared 版本 |
| 配置方式不统一 | Agent 使用困难 | 命令行参数 + 交互式提示 |
| 小程序属性无条件生成 | 非小程序项目产生垃圾数据 | 条件化触发 |
| 错误信息不够明确 | Agent 绕过错误 | 详细错误提示 + 解决步骤 |

---

## 三、实施计划

### Phase 1: 统一 OpenAPI 客户端（高优先级）

#### 3.1.1 评估 shared SDK 能力

**shared/postman/sensors_openapi.py 当前能力：**
- ✅ Schema 事件管理 (create/list/update/get)
- ✅ Schema 属性管理 (batch-create/update/get/list)
- ✅ 用户属性管理
- ✅ 分群管理
- ✅ 标签管理
- ✅ 业务集市
- ✅ 运营计划+画布

**tracking-setup-e2e/scripts/sa_openapi.py 当前能力：**
- ✅ Schema 事件管理 (create/list)
- ✅ Schema 属性管理 (batch-create)
- ✅ 用户属性管理
- ✅ 重试机制 (3次)
- ✅ ALREADY_EXISTS 自动处理

**差距分析：**
| 功能 | shared SDK | 当前 sa_openapi.py | 是否需要迁移 |
|------|-----------|-------------------|------------|
| 事件创建 | ✅ | ✅ | 是 |
| 事件列表 | ✅ | ✅ | 是 |
| 属性批量创建 | ✅ | ✅ | 是 |
| 用户属性创建 | ✅ | ✅ | 是 |
| 重试机制 | ❌ | ✅ | 需要添加 |
| ALREADY_EXISTS 处理 | ❌ | ✅ | 需要添加 |
| 日志记录 | ❌ | ✅ | 需要添加 |

#### 3.1.2 实施步骤

1. **增强 shared SDK**
   - 添加重试机制（3次，指数退避）
   - 添加 ALREADY_EXISTS 自动处理
   - 添加日志记录
   - 保持向后兼容

2. **替换 tracking-setup-e2e 中的客户端**
   - 删除 `tracking-setup-e2e/scripts/sa_openapi.py`
   - 修改 `import_meta_data.py` 导入 shared SDK
   - 修改 `import_mock_data.py` 导入 shared SDK（如有需要）

3. **验证**
   - 运行 `import_meta_data.py` 测试元数据导入
   - 确认事件创建、属性创建、用户属性创建正常

### Phase 2: 配置系统优化（已完成）

#### 3.2.1 已完成工作

✅ **import_meta_data.py**
- 支持 `--cdp-url`, `--project`, `--api-key`, `--tracking-plan` 参数
- 缺失参数时交互式提示（带示例）
- 优先级：命令行 > 环境变量 > 交互式提示

✅ **import_mock_data.py**
- 支持 `--data-url`, `--jsonl` 参数
- 自动查找最新 jsonl 文件
- 交互式提示数据接收地址

✅ **.env.example**
- 更新注释，使用中文说明
- 添加示例值
- 区分 CDP 地址和数据接收地址

#### 3.2.2 待补充

- [ ] `generate_mock_data.py` 支持命令行参数覆盖 `.env`
- [ ] 统一所有脚本的配置获取逻辑（提取到公共模块）

### Phase 3: 条件化小程序支持（已完成）

#### 3.3.1 已完成工作

✅ **tracking_plan.py**
- 添加 `has_mp_events()` 方法
- 检测埋点方案是否包含 `$MP*` 预置事件

✅ **event_sequencer.py**
- 仅在 `has_mp_events()` 返回 True 时初始化 `MpPresetBuilder`
- 预置属性生成添加条件判断

#### 3.3.2 验证结果

- 包含小程序事件：生成 `$scene`, `$url`, UTM 属性 ✅
- 不包含小程序事件：不生成预置属性 ✅

### Phase 4: 错误处理增强（已完成）

#### 3.4.1 已完成工作

✅ **import_meta_data.py**
- API 连接失败时显示明确错误原因
- 区分 API 密钥错误、地址错误、网络错误
- Excel 解析失败时显示实际 sheet 名称

✅ **import_mock_data.py**
- 缺少配置时显示获取方式
- 导入前显示批次信息确认

---

## 四、详细实施步骤

### 步骤 1: 增强 shared SDK（2小时）

**文件**: `shared/postman/sensors_openapi.py`

**修改内容**:
```python
# 添加重试机制
class SensorsOpenAPI:
    def _request(self, method: str, path: str, json_data: dict = None, max_retries: int = 3) -> dict:
        url = f"{self.host}{path}"
        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, json=json_data, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code < 500:
                    return e.response.json()  # 客户端错误直接返回
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 * (attempt + 1))
            except requests.exceptions.RequestException:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 * (attempt + 1))

# 添加 ALREADY_EXISTS 处理
def create_event(self, original_name: str, display_name: str, **kwargs) -> bool:
    try:
        resp = self._request("POST", "/schema/event/create", {...})
        if resp.get("code") == "SUCCESS":
            return True
        if "ALREADY_EXISTS" in resp.get("code", ""):
            return True  # 已存在视为成功
        return False
    except Exception as e:
        logger.error(f"创建事件失败: {e}")
        return False
```

### 步骤 2: 替换 tracking-setup-e2e 客户端（1小时）

**删除文件**:
- `tracking-setup-e2e/scripts/sa_openapi.py`

**修改文件**:
- `tracking-setup-e2e/scripts/import_meta_data.py`
  ```python
  # 旧
  from sa_openapi import SAOpenAPI, map_data_type
  
  # 新
  import sys
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'postman'))
  from sensors_openapi import SensorsOpenAPI
  
  # data_type 映射函数保留在本地
  DATA_TYPE_MAP = {
      "String":   {"type": "STRING"},
      "Number":   {"type": "NUMBER"},
      "Bool":     {"type": "BOOL"},
      "Datetime": {"type": "DATETIME"},
      "List":     {"type": "LIST", "element_data_types": "STRING"},
  }
  
  def map_data_type(value_type: str) -> dict:
      key = (value_type or "String").strip().capitalize()
      return DATA_TYPE_MAP.get(key, {"type": "STRING"})
  ```

### 步骤 3: 提取公共配置模块（2小时）

**新建文件**: `tracking-setup-e2e/scripts/config_helper.py`

```python
"""公共配置获取模块

支持优先级：命令行参数 > 环境变量 > 交互式提示
"""

import os
import sys
import getpass
from typing import Optional

CONFIG_SCHEMA = {
    "cdp_url": {
        "env_key": "SA_HOST",
        "prompt": "CDP 地址",
        "example": "https://demo.sensorsdata.cn",
        "help": "神策 CDP 控制台地址，登录后在浏览器地址栏看到",
    },
    "project": {
        "env_key": "SA_PROJECT",
        "prompt": "项目 ID",
        "example": "default",
        "help": "登录神策后 URL 中 project= 后面的值",
    },
    "api_key": {
        "env_key": "API_KEY",
        "prompt": "Open API 密钥",
        "example": "#K-jHllJkcPOMeRke3Vi5Nokeuc1MDlRZls",
        "help": "神策后台 → 系统管理 → API 密钥 → 创建密钥",
        "secret": True,
    },
    "data_url": {
        "env_key": "SA_TRACK_URL",
        "prompt": "数据接收地址",
        "example": "https://demo.sensorsdata.cn/sa?project=default",
        "help": "神策后台 → 数据接入 → HTTP API → 复制接入地址",
    },
    "tracking_plan": {
        "env_key": "TRACKING_PLAN_PATH",
        "prompt": "埋点方案路径",
        "example": "./refrences/tracking-plan.xlsx",
        "help": "埋点方案 Excel 文件的路径",
    },
}

def get_config(key: str, args_value: str = "", interactive: bool = True) -> str:
    """获取配置值"""
    schema = CONFIG_SCHEMA[key]
    
    # 1. 命令行参数
    if args_value:
        return args_value
    
    # 2. 环境变量
    env_value = os.getenv(schema["env_key"], "")
    if env_value:
        return env_value
    
    # 3. 交互式提示
    if interactive and sys.stdin.isatty():
        print(f"\n{schema['prompt']}:")
        print(f"  示例: {schema['example']}")
        print(f"  获取: {schema['help']}")
        
        if schema.get("secret"):
            value = getpass.getpass("  请输入: ").strip()
        else:
            value = input("  请输入: ").strip()
        
        if value:
            return value
    
    # 4. 报错
    raise ValueError(f"缺少必要配置: {schema['prompt']}")
```

**修改脚本导入**:
```python
from config_helper import get_config

cdp_url = get_config("cdp_url", args.cdp_url)
project = get_config("project", args.project)
api_key = get_config("api_key", args.api_key)
```

### 步骤 4: 统一 generate_mock_data.py 配置（1小时）

**修改**: `tracking-setup-e2e/scripts/generate_mock_data.py`

- 添加命令行参数支持 `--cdp-url`, `--project`, `--tracking-plan`
- 使用 `config_helper.get_config()` 获取配置
- 保持向后兼容（支持 .env）

### 步骤 5: 测试验证（2小时）

**测试场景**:
1. **命令行参数模式**
   ```bash
   python scripts/import_meta_data.py \
     --cdp-url https://westkdemo.sensorsdata.cn \
     --project default \
     --api-key xxx \
     --tracking-plan "refrences/Annex 6.xlsx"
   ```

2. **交互式提示模式**
   ```bash
   python scripts/import_meta_data.py
   # 按提示输入各项配置
   ```

3. **.env 模式**
   ```bash
   # 配置 .env
   python scripts/import_meta_data.py
   ```

4. **小程序条件触发**
   - 包含 `$MP*` 事件：验证生成 `$scene` 属性
   - 不包含 `$MP*` 事件：验证不生成预置属性

---

## 五、文件变更清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `shared/postman/sensors_openapi.py` | 通用 OpenAPI SDK（已创建，需增强） |
| `tracking-setup-e2e/scripts/config_helper.py` | 公共配置获取模块 |

### 修改文件
| 文件 | 修改内容 |
|------|---------|
| `shared/postman/sensors_openapi.py` | 添加重试、错误处理、日志 |
| `tracking-setup-e2e/scripts/import_meta_data.py` | 使用 shared SDK 和 config_helper |
| `tracking-setup-e2e/scripts/import_mock_data.py` | 使用 config_helper |
| `tracking-setup-e2e/scripts/generate_mock_data.py` | 添加命令行参数支持 |

### 删除文件
| 文件 | 说明 |
|------|------|
| `tracking-setup-e2e/scripts/sa_openapi.py` | 被 shared SDK 替代 |

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| shared SDK 与现有代码不兼容 | 导入失败 | 保留 `map_data_type()` 在本地 |
| 配置系统变更导致 Agent 混乱 | 使用错误 | 保持 .env 兼容，渐进式迁移 |
| 删除 sa_openapi.py 影响其他功能 | 造数失败 | 全面测试后再删除 |

---

## 七、验收标准

- [ ] `import_meta_data.py` 使用 shared SDK 成功导入元数据
- [ ] `import_mock_data.py` 支持三种配置方式
- [ ] `generate_mock_data.py` 支持命令行参数
- [ ] 包含小程序事件时生成 `$scene` 等属性
- [ ] 不包含小程序事件时不生成预置属性
- [ ] 所有脚本错误提示明确，Agent 不会绕过

---

**请评审以上实施文档，确认后开始执行。**
