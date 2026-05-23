#!/usr/bin/env python3
"""
sensors_openapi.py — 神策 OpenAPI 通用客户端

基于 Postman Collection 自动生成
支持模块: SDH(元数据), SA(分析), SF(运营), SBP(账号), Potal(系统)

用法:
    api = SensorsOpenAPI("https://demo.sensorsdata.cn", "your-api-key", "default")
    events = api.get_all_event_properties()
"""

import requests
from typing import Dict, List, Optional, Any


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

    def _request(self, method: str, path: str, json_data: dict = None) -> dict:
        """发送请求并处理响应"""
        url = f"{self.host}{path}"
        resp = self.session.request(method, url, json=json_data)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "SUCCESS":
            raise Exception(f"API Error: {data}")
        return data.get("data", {})

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

    def create_event(self, original_name: str, display_name: str, **kwargs) -> dict:
        """创建事件"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/schema/event/create",
            {
                "physical_schema_name": "events",
                "schemas": [
                    {
                        "original_name": original_name,
                        "display_name": display_name,
                        **kwargs,
                    }
                ],
            },
        )

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

    def list_events(self, page_size: int = 100) -> list:
        """事件列表"""
        return self._request(
            "POST",
            "/api/v3/horizon/v1/schema/event/list",
            {"physical_schema_name": "events", "page_size": page_size},
        )

    def batch_create_fields(self, fields: list) -> dict:
        """批量创建属性"""
        return self._request(
            "POST", "/api/v3/horizon/v1/schema/field/batch-create", {"fields": fields}
        )

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


# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    api = SensorsOpenAPI(
        host="https://demo.sensorsdata.cn", api_key="your-api-key", project="default"
    )

    # 示例1: 获取事件列表
    # events = api.list_events()
    # print(events)

    # 示例2: 获取分群列表
    # segments = api.list_segments()
    # print(segments)

    # 示例3: 获取运营计划列表
    # plans = api.list_plans()
    # print(plans)
