#!/usr/bin/env python3
"""
sensors_openapi.py — 神策 OpenAPI 通用客户端

基于 Postman Collection 自动生成
支持模块: SDH(元数据), SA(分析), SF(运营), SBP(账号), Potal(系统)

用法:
    api = SensorsOpenAPI("https://demo.sensorsdata.cn", "your-api-key", "default")
    events = api.get_all_event_properties()
"""

import logging
import time
import requests
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SensorsOpenAPIError(Exception):
    def __init__(self, message: str, code: str = None, request_id: str = None):
        self.code = code
        self.request_id = request_id
        super().__init__(message)


# v3 data_type 映射
DATA_TYPE_MAP = {
    "String":   {"type": "STRING"},
    "Number":   {"type": "NUMBER"},
    "Bool":     {"type": "BOOL"},
    "Datetime": {"type": "DATETIME"},
    "List":     {"type": "LIST", "element_data_types": "STRING"},
}


def map_data_type(value_type: str) -> dict:
    """将 Excel 类型字符串映射为 v3 data_type 对象"""
    key = (value_type or "String").strip().capitalize()
    return DATA_TYPE_MAP.get(key, {"type": "STRING"})


class SensorsOpenAPI:
    """神策 OpenAPI 通用客户端"""

    def __init__(self, host: str, api_key: str, project: str):
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.project = project
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "api-key": api_key,
                "sensorsdata-project": project,
            }
        )

    def _request(self, method: str, path: str, json_data: dict = None, max_retries: int = 3) -> dict:
        """发送请求，含重试（指数退避）和客户端错误直通"""
        url = f"{self.host}{path}"
        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, json=json_data, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code < 500:
                    try:
                        return e.response.json()
                    except Exception:
                        raise SensorsOpenAPIError(str(e))
                if attempt == max_retries - 1:
                    raise SensorsOpenAPIError(str(e))
                time.sleep(2 * (attempt + 1))
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise SensorsOpenAPIError(str(e))
                time.sleep(2 * (attempt + 1))
        return {}

    def _ok(self, resp: dict) -> bool:
        return resp.get("code") == "SUCCESS"

    # ── SDH 模块 (Schema/Data Hub) ──

    def list_event_fields(self, schema_name: str) -> dict:
        """获取事件属性列表"""
        return self._request(
            "POST", "/api/v3/horizon/v1/schema/field/list", {"schema_name": schema_name}
        )

    def update_field(self, schema_name: str, field: dict, update_mask: str) -> dict:
        """修改属性"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/schema/field/update",
            {"schema_name": schema_name, "field": field, "update_mask": update_mask},
        )

    def get_field(self, schema_name: str, field_name: str) -> dict:
        """查询属性"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/schema/field/get",
            {"schema_name": schema_name, "field_name": field_name},
        )

    def create_event(
        self,
        original_name: str,
        display_name: str,
        physical_schema: str = "events",
        track_platforms: list = None,
        **kwargs,
    ) -> bool:
        """创建元事件。已存在时视为成功。"""
        if track_platforms is None:
            track_platforms = [{"platform": "MINI_APP", "has_data": False}]
        body = {
            "physical_schema_name": physical_schema,
            "schemas": [
                {
                    "original_name": original_name,
                    "display_name": display_name,
                    "statistics": {"track_platforms": track_platforms},
                    **kwargs,
                }
            ],
        }
        resp = self._request("POST", "/api/v3/horizon/v1/schema/event/create", body)
        if self._ok(resp):
            return True
        code = resp.get("code", "")
        if "ALREADY_EXISTS" in code or "already" in str(resp.get("message", "")).lower():
            logger.debug("事件已存在，跳过: %s", original_name)
            return True
        logger.error("创建事件失败 [%s]: %s %s", original_name, code, resp.get("message", ""))
        return False

    def get_event(self, original_name: str) -> dict:
        """获取事件详情"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/schema/event/get",
            {"physical_schema_name": "events", "original_name": original_name},
        )

    def update_event(self, schema_name: str, updates: dict, update_mask: str) -> dict:
        """更新事件"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/schema/event/update",
            {"schema": {"name": schema_name, **updates}, "update_mask": update_mask},
        )

    def list_events(self, physical_schema: str = "events", page_size: int = 200) -> list:
        """事件列表"""
        resp = self._request(
            "POST",
            "/api/v3/horizon/v1/schema/event/list",
            {"physical_schema_name": physical_schema, "page_size": page_size},
        )
        if not self._ok(resp):
            return []
        return resp.get("data", {}).get("schemas", [])

    def create_field(
        self,
        schema_name: str,
        name: str,
        display_name: str,
        data_type: dict,
        remark: str = "",
    ) -> bool:
        """创建单个属性。已存在时视为成功。"""
        body = {
            "fields": [
                {
                    "schema_name": schema_name,
                    "field": {
                        "name": name,
                        "display_name": display_name,
                        "data_type": data_type,
                        "data_mapping": {"source_type": "MAIN_TABLE_COLUMN"},
                        "custom_params": {"meta_desc": remark} if remark else {},
                    },
                }
            ]
        }
        resp = self._request("POST", "/api/v3/horizon/v1/schema/field/batch-create", body)
        if self._ok(resp):
            return True
        code = resp.get("code", "")
        msg = str(resp.get("message", ""))
        if "ALREADY_EXISTS" in code or "already" in msg.lower():
            logger.debug("属性已存在，跳过: %s.%s", schema_name, name)
            return True
        logger.error("创建属性失败 [%s.%s]: %s %s", schema_name, name, code, msg)
        return False

    def batch_create_fields(self, fields: list) -> dict:
        """批量创建属性（逐个，避免单个失败影响全部）。

        fields 格式: [{"schema_name": ..., "name": ..., "display_name": ..., "data_type": ...}]
        返回: {"ok": [...], "skipped": [...], "failed": [...]}
        """
        ok, skipped, failed = [], [], []
        for f in fields:
            schema_name = f["schema_name"]
            name = f["name"]
            try:
                success = self.create_field(
                    schema_name=schema_name,
                    name=name,
                    display_name=f.get("display_name", name),
                    data_type=f["data_type"],
                    remark=f.get("remark", ""),
                )
            except SensorsOpenAPIError as e:
                logger.error("属性创建异常 [%s.%s]: %s", schema_name, name, e)
                success = False
            if success:
                ok.append(name)
            else:
                failed.append(name)
            time.sleep(0.2)
        return {"ok": ok, "skipped": skipped, "failed": failed}

    def create_user_field(
        self,
        name: str,
        display_name: str,
        data_type: dict,
        remark: str = "",
    ) -> bool:
        """创建用户属性（schema_name 固定为 'users'）"""
        return self.create_field(
            schema_name="users",
            name=name,
            display_name=display_name,
            data_type=data_type,
            remark=remark,
        )

    def list_user_fields(self) -> list:
        """获取用户属性列表"""
        resp = self._request(
            "POST", "/api/v3/horizon/v1/schema/field/list", {"schema_name": "users"}
        )
        if not self._ok(resp):
            return []
        return resp.get("data", {}).get("fields", [])

    # ── 分群管理 ──

    def list_segments(self, **kwargs) -> dict:
        """获取分群列表"""
        return self._request(
            "POST", "/api/v3/horizon/v1/segment/segment_definition/list", kwargs
        )

    def get_segment(self, segment_id: str) -> dict:
        """获取分群定义"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/segment/definition/get",
            {"segment_id": segment_id},
        )

    def evaluate_segment(self, segment_id: str) -> dict:
        """触发分群计算"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/segment/definition/evaluate",
            {"segment_id": segment_id},
        )

    # ── 标签管理 ──

    def list_tags(self, **kwargs) -> dict:
        """查询标签列表"""
        return self._request("POST", "/api/v3/horizon/v1/tag/definition/list", kwargs)

    def get_tag(self, tag_id: str) -> dict:
        """获取标签元数据"""
        return self._request(
            "POST", "/api/v3/horizon/v1/tag/tag_definition/create", {"tag_id": tag_id}
        )

    # ── SA 模块 (分析平台) ──

    def list_datasets(self, **kwargs) -> dict:
        """获取业务模型列表"""
        return self._request("POST", "/api/v3/analytics/v1/dataset/detail_list", kwargs)

    def refresh_dataset(self, dataset_id: str) -> dict:
        """刷新业务模型数据"""
        return self._request(
            "POST", "/api/v3/analytics/v1/dataset/refresh", {"dataset_id": dataset_id}
        )

    def query_dataset(self, dataset_id: str, **kwargs) -> dict:
        """查询业务模型数据"""
        return self._request(
            "POST",
            "/api/v3/analytics/v1/dataset/model/query",
            {"dataset_id": dataset_id, **kwargs},
        )

    def get_dataset_detail(self, dataset_id: str) -> dict:
        """查询业务模型详情"""
        return self._request(
            "GET", f"/api/v3/analytics/v1/dataset/detail?dataset_id={dataset_id}"
        )

    def get_all_event_properties(self) -> dict:
        """获取所有事件属性"""
        return self._request(
            "GET", "/api/v3/analytics/v1/property-meta/event-properties/all"
        )

    # ── SF 模块 (智能运营) ──

    def list_audiences(self, **kwargs) -> dict:
        """获取受众列表"""
        return self._request(
            "POST", "/api/v3/focus/v1/express-audience-meta/rule/query", kwargs
        )

    def list_web_sections(self, **kwargs) -> dict:
        """获取资源位列表"""
        return self._request("POST", "/api/v3/focus/v1/web-sections/list", kwargs)

    def list_plans(self, **kwargs) -> dict:
        """运营计划列表查询"""
        return self._request("POST", "/api/v3/focus/v1/web/plan/list", kwargs)

    def list_canvas(self, **kwargs) -> dict:
        """流程画布列表查询"""
        return self._request("POST", "/api/v3/focus/v1/web/canvas/list", kwargs)

    def get_plan(self, plan_id: int) -> dict:
        """运营计划单个查询"""
        return self._request("GET", f"/api/v3/focus/v1/web/plan/get?id={plan_id}")

    def get_canvas(self, canvas_id: int) -> dict:
        """流程画布单个查询"""
        return self._request("GET", f"/api/v3/focus/v1/web/canvas/get?id={canvas_id}")

    # ── 在线接口 ──

    def get_user_attributes(self, distinct_id: str, **kwargs) -> dict:
        """单个用户获取多属性/标签"""
        return self._request(
            "POST",
            "/api/v3/focus/v1/express-attribute-online/get",
            {"distinct_id": distinct_id, **kwargs},
        )

    def query_attribute_status(self, **kwargs) -> dict:
        """属性订阅状态查询"""
        return self._request(
            "POST", "/api/v3/focus/v1/express-attribute/status/query", kwargs
        )

    def subscribe_attribute(self, **kwargs) -> dict:
        """属性标签订阅"""
        return self._request(
            "POST", "/api/v3/focus/v1/express-attribute/subscribe", kwargs
        )

    def unsubscribe_attribute(self, **kwargs) -> dict:
        """取消属性订阅"""
        return self._request(
            "POST", "/api/v3/focus/v1/express-attribute/unsubscribe", kwargs
        )

    # ── SBP 模块 (账号管理) ──

    def list_accounts(self, page_index: int = 1, page_size: int = 20) -> dict:
        """获取账号列表"""
        return self._request(
            "GET",
            f"/api/v3/identity/account/list?page_index={page_index}&page_size={page_size}",
        )

    # ── Potal 模块 (系统管理) ──

    def get_project_info(self) -> dict:
        """获取项目信息"""
        return self._request("POST", "/api/v3/identity-meta/schema-config/get")

    def list_executing_tasks(self) -> dict:
        """获取执行中的任务详情列表"""
        return self._request("POST", "/api/v3/resource-management/query/task/executing")

    # ── 自定义查询 ──

    def custom_query(self, sql: str, limit: int = 1000, timeout: int = 60) -> dict:
        """执行自定义 SQL 查询（神策「自定义查询」功能）。

        sql: 标准 SQL，表名为 events / users，时间字段为 date（DATE 类型）。
        limit: 查询结果条数上限（默认 1000，最大 10000）。
        返回: {"columns": [...], "rows": [[...], ...]} 或错误信息。
        """
        return self._request(
            "POST",
            "/api/v3/analytics/v1/custom-query/query",
            {"sql": sql, "limit": limit},
        )

    def query_event_counts(self, event_names: list, start_date: str, end_date: str) -> dict:
        """查询指定事件在日期范围内的总条数。

        event_names: 事件名列表
        start_date / end_date: 'YYYY-MM-DD'
        返回: {event_name: count, ...}，查询失败时返回空 dict。
        """
        if not event_names:
            return {}
        names_sql = ", ".join(f"'{n}'" for n in event_names)
        sql = (
            f"SELECT event, count(*) AS cnt FROM events "
            f"WHERE date >= '{start_date}' AND date <= '{end_date}' "
            f"AND event IN ({names_sql}) "
            f"GROUP BY event"
        )
        try:
            resp = self.custom_query(sql)
            if not self._ok(resp):
                logger.warning("自定义查询失败: %s", resp.get("message", ""))
                return {}
            rows = resp.get("data", {}).get("rows", [])
            cols = resp.get("data", {}).get("columns", [])
            if not rows or not cols:
                return {}
            event_idx = next((i for i, c in enumerate(cols) if c.get("name") == "event"), 0)
            cnt_idx = next((i for i, c in enumerate(cols) if c.get("name") == "cnt"), 1)
            return {row[event_idx]: int(row[cnt_idx]) for row in rows}
        except Exception as e:
            logger.warning("查询事件条数失败: %s", e)
            return {}

    def query_event_properties_sample(
        self, event_name: str, property_names: list, start_date: str, end_date: str, sample_size: int = 100
    ) -> list:
        """查询指定事件的属性样本数据。

        event_name: 事件名
        property_names: 属性名列表，如 ["amount", "pay_method"]
        start_date / end_date: 'YYYY-MM-DD'
        sample_size: 抽样条数（默认 100，最大 1000）
        返回: [{property_name: value, ...}, ...] 格式的样本列表。
        """
        if not property_names:
            return []
        props_sql = ", ".join(f"{p}" for p in property_names)
        sql = (
            f"SELECT {props_sql} FROM events "
            f"WHERE date >= '{start_date}' AND date <= '{end_date}' "
            f"AND event = '{event_name}' "
            f"LIMIT {min(sample_size, 1000)}"
        )
        try:
            resp = self.custom_query(sql, limit=min(sample_size, 1000))
            if not self._ok(resp):
                logger.warning("查询事件属性失败 [%s]: %s", event_name, resp.get("message", ""))
                return []
            rows = resp.get("data", {}).get("rows", [])
            cols = resp.get("data", {}).get("columns", [])
            if not rows or not cols:
                return []
            col_names = [c.get("name", "") for c in cols]
            return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            logger.warning("查询事件属性失败 [%s]: %s", event_name, e)
            return []

    def query_property_distribution(
        self, event_name: str, property_name: str, start_date: str, end_date: str, top_n: int = 20
    ) -> dict:
        """查询指定属性的值分布（用于枚举值校验）。

        event_name: 事件名
        property_name: 属性名
        start_date / end_date: 'YYYY-MM-DD'
        top_n: 返回最常见的 N 个值（默认 20）
        返回: {value: count, ...} 格式的分布字典。
        """
        sql = (
            f"SELECT {property_name}, count(*) AS cnt FROM events "
            f"WHERE date >= '{start_date}' AND date <= '{end_date}' "
            f"AND event = '{event_name}' "
            f"GROUP BY {property_name} "
            f"ORDER BY cnt DESC "
            f"LIMIT {top_n}"
        )
        try:
            resp = self.custom_query(sql, limit=top_n)
            if not self._ok(resp):
                logger.warning("查询属性分布失败 [%s.%s]: %s", event_name, property_name, resp.get("message", ""))
                return {}
            rows = resp.get("data", {}).get("rows", [])
            cols = resp.get("data", {}).get("columns", [])
            if not rows or not cols:
                return {}
            prop_idx = next((i for i, c in enumerate(cols) if c.get("name") == property_name), 0)
            cnt_idx = next((i for i, c in enumerate(cols) if c.get("name") == "cnt"), 1)
            return {row[prop_idx]: int(row[cnt_idx]) for row in rows}
        except Exception as e:
            logger.warning("查询属性分布失败 [%s.%s]: %s", event_name, property_name, e)
            return {}

    def query_user_property_sample(
        self, property_names: list, sample_size: int = 100
    ) -> list:
        """查询用户属性样本数据。

        property_names: 属性名列表，如 ["user_level", "vip_status"]
        sample_size: 抽样条数（默认 100，最大 1000）
        返回: [{property_name: value, ...}, ...] 格式的样本列表。
        """
        if not property_names:
            return []
        props_sql = ", ".join(f"{p}" for p in property_names)
        sql = f"SELECT {props_sql} FROM users LIMIT {min(sample_size, 1000)}"
        try:
            resp = self.custom_query(sql, limit=min(sample_size, 1000))
            if not self._ok(resp):
                logger.warning("查询用户属性失败: %s", resp.get("message", ""))
                return []
            rows = resp.get("data", {}).get("rows", [])
            cols = resp.get("data", {}).get("columns", [])
            if not rows or not cols:
                return []
            col_names = [c.get("name", "") for c in cols]
            return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            logger.warning("查询用户属性失败: %s", e)
            return []


# 使用示例
if __name__ == "__main__":
    api = SensorsOpenAPI(
        host="https://demo.sensorsdata.cn", api_key="your-api-key", project="default"
    )
    # events = api.list_events()
    # print(events)

