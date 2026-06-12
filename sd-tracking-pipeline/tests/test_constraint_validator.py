"""Tests for constraint_validator.py."""
from dataclasses import dataclass
from typing import Dict, List, Optional

import pytest

from constraint_validator import ConstraintValidator, Violation, _shared_identity_values
from fixed_account_generator import User
from event_sequencer import Event


def _user(user_id="u1", segment="L1", region="mainland", identities=None, account_id=None):
    return User(
        user_id=user_id,
        segment=segment,
        region=region,
        identities=identities or {},
        profile={},
        created_at=None,
        account_id=account_id,
    )


def _event(name, ts, props=None):
    return Event(event_name=name, user=None, timestamp_ms=ts, properties=props or {})


def test_temporal_order_passes():
    user = _user()
    events = [
        _event("Registration_Result", 1000),
        _event("Login_Result", 2000),
        _event("Product_Order_Payment", 3000),
    ]
    validator = ConstraintValidator()
    assert validator._check_temporal_order(user, events) == []


def test_temporal_order_registration_after_login_fails():
    user = _user()
    events = [
        _event("Login_Result", 1000),
        _event("Registration_Result", 2000),
    ]
    validator = ConstraintValidator()
    violations = validator._check_temporal_order(user, events)
    assert len(violations) == 1
    assert violations[0].rule == "temporal_order"


def test_field_consistency_ticket_count_matches():
    user = _user()
    events = [
        _event("Product_Order_Payment", 1000, {"ticketsQuantity": 2, "totalOrderAmount": 200}),
        _event("Product_Payment_Detail", 1100, {"ticketPaidAmount": 100}),
        _event("Product_Payment_Detail", 1200, {"ticketPaidAmount": 100}),
    ]
    validator = ConstraintValidator()
    assert validator._check_field_consistency(user, events) == []


def test_field_consistency_wrong_ticket_count():
    user = _user()
    events = [
        _event("Product_Order_Payment", 1000, {"ticketsQuantity": 3, "totalOrderAmount": 300}),
        _event("Product_Payment_Detail", 1100, {"ticketPaidAmount": 100}),
    ]
    validator = ConstraintValidator()
    violations = validator._check_field_consistency(user, events)
    assert any("订单票数" in v.description for v in violations)


def test_field_consistency_detail_sum_exceeds_total():
    user = _user()
    events = [
        _event("Product_Order_Payment", 1000, {"ticketsQuantity": 2, "totalOrderAmount": 150}),
        _event("Product_Payment_Detail", 1100, {"ticketPaidAmount": 100}),
        _event("Product_Payment_Detail", 1200, {"ticketPaidAmount": 100}),
    ]
    validator = ConstraintValidator()
    violations = validator._check_field_consistency(user, events)
    assert any("明细金额" in v.description for v in violations)


def test_business_rule_refund_after_admission_fails():
    user = _user()
    events = [
        _event("Ticket_Admission", 1000),
        _event("Ticket_Refund", 2000),
    ]
    validator = ConstraintValidator()
    violations = validator._check_business_rules(user, events)
    assert len(violations) == 1
    assert "Admission 后不可 Refund" in violations[0].description


def test_business_rule_refund_before_admission_ok():
    user = _user()
    events = [
        _event("Ticket_Refund", 1000),
        _event("Ticket_Admission", 2000),
    ]
    validator = ConstraintValidator()
    assert validator._check_business_rules(user, events) == []


def test_business_rule_mixed_voucher_scenarios():
    user = _user()
    events = [
        _event("A", 1000, {"voucher_scenario": "项目订单"}),
        _event("B", 2000, {"voucher_scenario": "商品订单"}),
    ]
    validator = ConstraintValidator()
    violations = validator._check_business_rules(user, events)
    assert any("Voucher 场景严格互斥" in v.description for v in violations)


def test_validate_id_mapping_split_users_must_not_share_identity():
    users = [
        _user("u1-1", identities={"mobile": "13800000001"}, account_id="ACC-SPLIT"),
        _user("u1-2", identities={"mobile": "13800000001"}, account_id="ACC-SPLIT"),
    ]
    violations = ConstraintValidator.validate_id_mapping(users)
    assert len(violations) == 1
    assert "share identity values" in violations[0].description


def test_validate_id_mapping_non_split_users_can_share():
    # Non-split users are grouped by user_id (each is its own group), sharing is allowed
    users = [
        _user("u1", identities={"mobile": "13800000001"}),
        _user("u2", identities={"mobile": "13800000001"}),
    ]
    violations = ConstraintValidator.validate_id_mapping(users)
    assert len(violations) == 0


def test_shared_identity_values():
    u1 = _user("u1", identities={"a": "1", "b": "2"})
    u2 = _user("u2", identities={"a": "1", "b": "3"})
    assert _shared_identity_values(u1, u2) == {"a": "1"}
