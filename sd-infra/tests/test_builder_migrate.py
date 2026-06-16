"""Tests for builder/migrate.py."""
import pytest

from migrate import migrate


def test_migrate_basic():
    old = {
        "title": "Old Arch",
        "columns": [
            {
                "id": "sources",
                "label": "Data Sources",
                "nodes": [
                    {"id": "crm", "label": "CRM", "custom": {"color": "client_system"}},
                    {"id": "website", "label": "Website", "future": True},
                ],
            },
            {
                "id": "sd",
                "label": "SensorsData",
                "container_style": "dashed_green",
                "nodes": [
                    {"id": "cdp", "label": "CDP", "custom": {"color": "sd_product", "w": 420}},
                ],
            },
        ],
        "edges": [
            {"from": "crm", "to": "cdp", "style": "sdk_realtime", "has_pii": True, "label": "events"},
            {"from": "cdp", "to": "crm", "style": "callback", "label": "metrics"},
        ],
    }

    new = migrate(old)

    assert new["meta"]["title"] == "Old Arch"
    assert new["meta"]["client"] == "Migrated"

    nodes = {n["id"]: n for n in new["nodes"]}
    assert "crm" in nodes
    assert nodes["crm"]["type"] == "client_system"
    assert nodes["crm"]["group"] == "sources"
    assert nodes["website"]["status"] == "future"
    assert nodes["cdp"]["type"] == "sd_product"
    assert nodes["cdp"]["props"]["w"] == 420

    groups = {g["id"]: g for g in new["groups"]}
    assert "sources" in groups
    assert "crm" in groups["sources"]["contains"]

    edges = new["edges"]
    assert len(edges) == 2
    assert edges[0]["rel"] == "sdk_track"
    assert edges[0]["data"]["has_pii"] is True
    assert edges[1]["rel"] == "callback"


def test_migrate_no_container():
    old = {
        "title": "No Container",
        "columns": [
            {"id": "", "label": "", "nodes": [{"id": "crm"}]}
        ],
        "edges": [],
    }
    new = migrate(old)
    assert len(new["groups"]) == 0
    assert len(new["nodes"]) == 1
    assert "group" not in new["nodes"][0]
