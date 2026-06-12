"""pytest fixtures for draw-diagram tests."""
import pytest


@pytest.fixture
def sample_arch():
    """Minimal arch.yaml dict for smoke tests."""
    return {
        "meta": {"title": "Test", "client": "T", "version": "1.0", "date": "2026-06-11"},
        "nodes": [
            {"id": "crm", "name": "CRM", "type": "client_system", "group": "client_systems"},
            {"id": "cdp", "name": "CDP", "type": "sd_product", "group": "sd_products"},
            {"id": "mae", "name": "MAE", "type": "sd_product", "group": "sd_products"},
            {"id": "sendcloud", "name": "SendCloud", "type": "external_saas", "group": "external"},
        ],
        "groups": [
            {"id": "client_systems", "name": "Client Systems", "type": "client_systems", "contains": ["crm"]},
            {"id": "sd_products", "name": "SD Products", "type": "data_sources", "contains": ["cdp", "mae"]},
            {"id": "external", "name": "External", "type": "internet", "contains": ["sendcloud"]},
        ],
        "edges": [
            {"from": "crm", "to": "cdp", "rel": "sftp_export", "name": "MemberInfo",
             "data": {"has_pii": True, "fields": ["memberinfo"], "protocol": "SFTP", "frequency": "daily"}},
            {"from": "cdp", "to": "mae", "rel": "kafka_subscribe", "name": "Events",
             "data": {"has_pii": False, "frequency": "realtime"}},
            {"from": "mae", "to": "sendcloud", "rel": "deliver", "name": "Email",
             "data": {"has_pii": True, "frequency": "realtime"}},
        ],
    }


@pytest.fixture
def arch_with_rows():
    """arch.yaml with explicit row/col for row-layout tests."""
    return {
        "meta": {"title": "RowTest", "client": "T", "version": "1.0", "date": "2026-06-11"},
        "nodes": [
            {"id": "a", "name": "A", "type": "client_system", "group": "g1", "row": 1, "col": 0},
            {"id": "b", "name": "B", "type": "sd_product", "group": "g1", "row": 2, "col": 0},
            {"id": "c", "name": "C", "type": "sd_product", "group": "g2", "row": 1, "col": 1},
        ],
        "groups": [
            {"id": "g1", "name": "G1", "type": "client_systems", "contains": ["a", "b"]},
            {"id": "g2", "name": "G2", "type": "data_sources", "contains": ["c"]},
        ],
        "edges": [
            {"from": "a", "to": "b", "rel": "api_call", "data": {"has_pii": False}},
            {"from": "b", "to": "c", "rel": "kafka_subscribe", "data": {"has_pii": False}},
        ],
    }
