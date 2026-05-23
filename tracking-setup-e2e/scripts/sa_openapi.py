#!/usr/bin/env python3
"""
sa_openapi.py — 神策 Schema Open API v3 客户端

认证：api-key + sensorsdata-project Header
基础路径：{host}/api/v3/horizon/v1
"""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class SAOpenAPIError(Exception):
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


class SAOpenAPI:
    """神策 Schema Open API v3 客户端"""

    def __init__(self, host: str, api_key: str, project: str):
        self.base_url = f"{host.rstrip('/')}/api/v3/horizon/v1"
        self.project = project
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "api-key": api_key,
            "sensorsdata-project": project,
        })

    # ── 内部方法 ──────────────────────────────────────────────

    def _request(self, method: str, path: str, json_data: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        for attempt in range(3):
            try:
                resp = self._session.request(method, url, json=json_data, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code < 500:
                    try:
                        return e.response.json()
                    except Exception:
                        raise SAOpenAPIError(str(e))
                if attempt == 2:
                    raise SAOpenAPIError(str(e))
                time.sleep(2 * (attempt + 1))
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    raise SAOpenAPIError(str(e))
                time.sleep(2 * (attempt + 1))
        return {}

    def _ok(self, resp: dict) -> bool:
        return resp.get("code") == "SUCCESS"

    # ── 事件管理 ──────────────────────────────────────────────

    def create_event(
        self,
        original_name: str,
        display_name: str,
        physical_schema: str = "events",
        track_platforms: list = None,
    ) -> bool:
        """创建元事件。已存在时视为成功。"""
        if track_platforms is None:
            track_platforms = [{"platform": "MINI_APP", "has_data": False}]
        body = {
            "physical_schema_name": physical_schema,
            "schemas": [{
                "original_name": original_name,
                "display_name": display_name,
                "statistics": {"track_platforms": track_platforms},
            }],
        }
        resp = self._request("POST", "/schema/event/create", body)
        if self._ok(resp):
            return True
        code = resp.get("code", "")
        if "ALREADY_EXISTS" in code or "already" in str(resp.get("message", "")).lower():
            logger.debug("事件已存在，跳过: %s", original_name)
            return True
        logger.error("创建事件失败 [%s]: %s %s", original_name, code, resp.get("message", ""))
        return False

    def list_events(self, physical_schema: str = "events", page_size: int = 200) -> list:
        body = {"physical_schema_name": physical_schema, "page_size": page_size}
        resp = self._request("POST", "/schema/event/list", body)
        if not self._ok(resp):
            return []
        return resp.get("data", {}).get("schemas", [])

    # ── 属性管理 ──────────────────────────────────────────────

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
            "fields": [{
                "schema_name": schema_name,
                "field": {
                    "name": name,
                    "display_name": display_name,
                    "data_type": data_type,
                    "data_mapping": {"source_type": "MAIN_TABLE_COLUMN"},
                    "custom_params": {"meta_desc": remark} if remark else {},
                },
            }]
        }
        resp = self._request("POST", "/schema/field/batch-create", body)
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

        fields 格式: [{"schema_name": ..., "name": ..., "display_name": ...,
                        "data_type": ..., "remark": ""}]
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
            except SAOpenAPIError as e:
                logger.error("属性创建异常 [%s.%s]: %s", schema_name, name, e)
                success = False
            if success:
                ok.append(name)
            else:
                failed.append(name)
            time.sleep(0.2)
        return {"ok": ok, "skipped": skipped, "failed": failed}

    # ── 用户属性 ──────────────────────────────────────────────

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
        body = {"schema_name": "users"}
        resp = self._request("POST", "/schema/field/list", body)
        if not self._ok(resp):
            return []
        return resp.get("data", {}).get("fields", [])


def map_data_type(value_type: str) -> dict:
    """将 Excel 类型字符串映射为 v3 data_type 对象"""
    key = (value_type or "String").strip().capitalize()
    return DATA_TYPE_MAP.get(key, {"type": "STRING"})
