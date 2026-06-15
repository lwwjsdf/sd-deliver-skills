"""Tests for rule_engine.py."""
import pytest
import yaml

from rule_engine import RuleEngine


def _write_rules(tmp_path, data):
    path = tmp_path / "rules.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)
    return str(path)


def test_load_segments_and_identities(tmp_path):
    path = _write_rules(tmp_path, {
        "user_segments": {
            "L0": {"ratio": 0.3, "identities": ["mobile"], "has_registration": True},
            "L1": {"ratio": 0.7, "identities": ["mobile", "email"]},
        },
        "identity_priority": {
            "mobile": {"priority": 1, "display": "手机号", "sa_key": "$mobile"},
        },
        "event_sequences": [],
        "constraints": [],
        "enums": {},
        "property_enums": {},
        "preset_events": {},
        "region_distribution": {"CN": 1.0},
    })
    engine = RuleEngine(path)
    segments = engine.get_user_segments()
    assert len(segments) == 2
    assert segments[0].name == "L0"
    assert segments[0].has_registration is True


def test_segment_ratio_validation(tmp_path):
    path = _write_rules(tmp_path, {
        "user_segments": {
            "A": {"ratio": 0.5},
            "B": {"ratio": 0.3},
        },
    })
    with pytest.raises(ValueError):
        RuleEngine(path)


def test_get_event_sequences(tmp_path):
    path = _write_rules(tmp_path, {
        "user_segments": {"S": {"ratio": 1.0}},
        "event_sequences": [
            {
                "name": "seq1",
                "events": [
                    {"event": "Login"},
                    {"event": "Purchase", "time_after_prev": {"min": 1, "max": 2}},
                ],
                "condition": "segment in [S]",
                "conversion_rate": 0.8,
            }
        ],
    })
    engine = RuleEngine(path)
    seqs = engine.get_event_sequences()
    assert len(seqs) == 1
    assert seqs[0].name == "seq1"
    assert len(seqs[0].events) == 2
    assert seqs[0].events[1].event == "Purchase"


def test_get_fixed_accounts(tmp_path):
    path = _write_rules(tmp_path, {
        "user_segments": {"S": {"ratio": 1.0}},
        "fixed_accounts": [
            {"id": "U01", "region": "CN", "segment": "S", "mobile": "13800000000"}
        ],
    })
    engine = RuleEngine(path)
    accounts = engine.get_fixed_accounts()
    assert len(accounts) == 1
    assert accounts[0].id == "U01"
    assert accounts[0].identities["mobile"] == "13800000000"


def test_get_constraints_and_enums(tmp_path):
    path = _write_rules(tmp_path, {
        "user_segments": {"S": {"ratio": 1.0}},
        "constraints": [
            {"description": "A before B", "type": "temporal_order"},
        ],
        "enums": {
            "pay_method": ["alipay", {"value": "wechat"}],
        },
    })
    engine = RuleEngine(path)
    constraints = engine.get_constraints()
    assert constraints[0].constraint_type == "temporal_order"
    assert engine.get_enum_values("pay_method") == ["alipay", "wechat"]


@pytest.mark.parametrize("condition,context,expected", [
    (None, {}, True),
    ("", {}, True),
    ("segment in [L1, L2]", {"segment": "L1"}, True),
    ("segment in [L1, L2]", {"segment": "L3"}, False),
    ("has Login", {"completed_events": ["Login"]}, True),
    ("has Login", {"completed_events": []}, False),
    ("not Login", {"completed_events": []}, True),
    ("not Login", {"completed_events": ["Login"]}, False),
])
def test_evaluate_condition(condition, context, expected, tmp_path):
    path = _write_rules(tmp_path, {"user_segments": {"S": {"ratio": 1.0}}})
    engine = RuleEngine(path)
    assert engine.evaluate_condition(condition, context) is expected


def test_evaluate_condition_unknown(tmp_path):
    path = _write_rules(tmp_path, {"user_segments": {"S": {"ratio": 1.0}}})
    engine = RuleEngine(path)
    with pytest.raises(ValueError):
        engine.evaluate_condition("invalid expr", {})


def test_get_event_sequences_with_derive(tmp_path):
    path = _write_rules(tmp_path, {
        "user_segments": {"S": {"ratio": 1.0}},
        "event_sequences": [
            {
                "name": "purchase",
                "events": [
                    {
                        "event": "Order",
                        "fields": {"ticketsQuantity": 3, "paidAmount": 300},
                        "derive": {
                            "event": "OrderDetail",
                            "count_ref": "{Order.ticketsQuantity}",
                            "distribute_fields": {"ticketPaidAmount": {"source": "paidAmount", "strategy": "divide_evenly"}},
                            "prefix_fields": {"ticketID": "TK-{orderIndex:03d}-{detailIndex:03d}"},
                            "carry_fields": ["paymentMethod"],
                        },
                    },
                ],
            }
        ],
    })
    engine = RuleEngine(path)
    seqs = engine.get_event_sequences()
    assert len(seqs) == 1
    edef = seqs[0].events[0]
    assert edef.derive is not None
    assert edef.derive.event == "OrderDetail"
    assert edef.derive.count_ref == "{Order.ticketsQuantity}"
    assert edef.derive.distribute_fields == {"ticketPaidAmount": {"source": "paidAmount", "strategy": "divide_evenly"}}


def test_get_preset_events_and_property_enums(tmp_path):
    path = _write_rules(tmp_path, {
        "user_segments": {"S": {"ratio": 1.0}},
        "preset_events": {"page_routes": ["/a"]},
        "property_enums": {"applicationName": "App"},
    })
    engine = RuleEngine(path)
    assert engine.get_preset_events()["page_routes"] == ["/a"]
    assert engine.get_property_enums()["applicationName"] == "App"
