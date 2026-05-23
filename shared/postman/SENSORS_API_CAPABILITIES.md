# 神策 OpenAPI 能力清单

**来源**: Postman Collection `Sensors.postman_collection.json`  
**总计**: 37 个 API  
**认证方式**: `api-key` + `sensorsdata-project` Header

---

## 认证方式

所有 API 使用相同的认证方式：
- **Header**: `api-key: {api_key}`
- **Header**: `sensorsdata-project: {project}`
- **Content-Type**: `application/json`

> **注意区分**：
> - **Open API 密钥** (`api-key`): 用于元数据管理，在「系统管理 → API 密钥」获取
> - **API Secret** (`token`): 部分旧版 API 使用，在「数据接入」获取

---

## 模块分类

### 1. SDH (Schema/Data Hub) - 元数据管理

**事件管理**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 获取事件属性列表 | `/api/v3/horizon/v1/schema/field/list` |
| POST | 修改属性 | `/api/v3/horizon/v1/schema/field/update` |
| POST | 查询属性 | `/api/v3/horizon/v1/schema/field/get` |
| POST | 创建事件 | `/api/v3/horizon/v1/schema/event/create` |
| POST | 获取事件详情 | `/api/v3/horizon/v1/schema/event/get` |
| POST | 更新事件 | `/api/v3/horizon/v1/schema/event/update` |
| POST | 事件列表 | `/api/v3/horizon/v1/schema/event/list` |

**分群管理**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 获取分群列表 | `/segment/segment_definition/list` |
| POST | 获取分群定义 | `/segment/definition/get` |
| POST | 触发分群计算 | `/segment/definition/evaluate` |
| POST | 获取分群计算任务 | `/segment/task/get` |
| POST | 取消分群计算任务 | `/segment/task/cancel` |
| POST | 获取分群 partition | `/segment/item/list` |

**标签管理**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 查询标签列表 | `/tag/definition/list` |
| POST | 获取标签元数据 | `/tag/tag_definition/create` |
| POST | 获取标签 partition | `/tag/tag_partition/get` |
| POST | 获取最新 partition | `/tag/tag_partition/latest` |
| POST | 检查标签执行状态 | `/tag/tag_task/get` |

### 2. SA (Sensors Analytics) - 分析平台

**业务集市**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 获取业务模型列表 | `/dataset/detail_list` |
| POST | 刷新业务模型数据 | `/dataset/refresh` |
| POST | 查询业务模型数据 | `/dataset/model/query` |
| GET | 查询业务模型详情 | `/dataset/detail` |
| GET | 查询业务模型分组 | `/dataset/group/list` |

**事件属性**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| GET | 获取所有事件属性 | `/property-meta/event-properties/all` |

### 3. SF (Sensors Focus) - 智能运营

**受众管理**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 获取受众列表(全部) | `/express-audience-meta/rule/query` |
| POST | 获取受众列表(传参) | `/web-sections/list` |

**资源位**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 获取资源位列表 | `/web-sections/list` |

**运营计划+画布**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 运营计划列表查询 | `/web/plan/list` |
| POST | 流程画布列表查询 | `/web/canvas/list` |
| GET | 运营计划单个查询 | `/web/plan/get` |
| GET | 流程画布单个查询 | `/web/canvas/get` |

**在线接口**
| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 单个用户获取多属性/标签 | `/express-attribute-online/get` |
| POST | 属性订阅状态查询 | `/express-attribute/status/query` |
| POST | 取消属性订阅 | `/express-attribute/unsubscribe` |
| POST | 属性标签订阅 | `/express-attribute/subscribe` |

### 4. SBP - 账号管理

| 方法 | 名称 | URL 路径 |
|------|------|----------|
| GET | 获取账号列表 | `/identity/account/list` |

### 5. Potal - 系统管理

| 方法 | 名称 | URL 路径 |
|------|------|----------|
| POST | 获取执行中的任务详情 | `/resource-management/query/task/executing` |
| POST | 获取项目信息 | `/identity-meta/schema-config/get` |

---

## 使用建议

### 对于 tracking-setup-e2e skill

**已使用的 API** (在 `sa_openapi.py` 中实现):
- ✅ Schema 事件创建/查询/更新
- ✅ Schema 属性批量创建
- ✅ 用户属性创建

**可扩展的 API**:
- 分群管理 (用于创建测试分群)
- 标签管理 (用于创建测试标签)
- 运营计划 (用于验证运营配置)

### 对于其他 skill

**cdp-operations skill** 可以使用:
- 业务集市 API (创建/刷新业务模型)
- 分群 API (创建分群)
- 标签 API (创建标签)

**tracking-setup-e2e skill** 可以使用:
- 事件属性 API (查询已有属性)
- 项目信息 API (验证项目配置)

---

## 变量说明

Postman Collection 中使用的变量:

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `host` | 神策主机地址 | `https://demo.sensorsdata.cn` |
| `api_key` | Open API 密钥 | `#K-jHllJkc...` |
| `project` | 项目 ID | `default` |
| `base_url` | API 基础路径 | `https://demo.sensorsdata.cn` |
| `horizon-base-url` | Horizon 模块路径 | `/api/v3/horizon/v1` |
| `sa-base-url` | SA 模块路径 | `/api/v3/analytics/v1` |
| `focus-base-url` | SF 模块路径 | `/api/v3/focus/v1` |
| `online_host` | 在线接口主机 | `https://online.sensorsdata.cn` |

---

## 注意事项

1. **API 版本**: 大部分 API 使用 `/api/v3/` 前缀
2. **项目标识**: 通过 `sensorsdata-project` Header 指定，不是 URL 参数
3. **响应格式**: 统一返回 `{code, request_id, data}` 结构
4. **错误处理**: `code != "SUCCESS"` 时表示失败

---

*文档生成时间: 2025-05-23*  
*基于 Postman Collection: Sensors.postman_collection.json*
