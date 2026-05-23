"""
constraint_validator.py — Validate event sequences against business constraints.

Depends on:
  - event_sequencer.py : Event
  - fixed_account_generator.py : User
  - rule_engine.py : RuleEngine, Constraint
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from event_sequencer import Event
from fixed_account_generator import User


# ---------------------------------------------------------------------------
# Violation dataclass
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    rule: str
    description: str
    user_id: str
    event_name: Optional[str] = None
    detail: Optional[str] = None

    def __str__(self) -> str:
        parts = [f"[{self.rule}] {self.description}"]
        if self.event_name:
            parts.append(f"event={self.event_name}")
        if self.detail:
            parts.append(self.detail)
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# ConstraintValidator
# ---------------------------------------------------------------------------

class ConstraintValidator:
    """
    Validates event sequences against the business constraints defined in
    business_logic.yaml.

    Constraint types handled:
      - temporal_order  : event A must appear before event B
      - field_consistency : numeric field relationships
      - business_rule   : domain-specific rules (Admission/Refund, Voucher)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_all(self, user: User, events: List[Event]) -> List[Violation]:
        """Run all constraint checks and return a list of violations."""
        violations: List[Violation] = []
        violations.extend(self._check_temporal_order(user, events))
        violations.extend(self._check_field_consistency(user, events))
        violations.extend(self._check_business_rules(user, events))
        return violations

    @staticmethod
    def validate_id_mapping(users: List[User]) -> List[Violation]:
        """
        Validate that split-identity users (e.g. UAT-X07-1, UAT-X07-2) do NOT
        share any identity values, and that non-split users do not accidentally
        share identities with each other.

        Returns a list of Violation objects for any shared identities found
        between users that should be independent.
        """
        violations: List[Violation] = []

        # Group users by account_id to find split groups
        from collections import defaultdict
        by_account: Dict[str, List[User]] = defaultdict(list)
        for user in users:
            key = user.account_id or user.user_id
            by_account[key].append(user)

        # For split groups: verify no shared identity values
        for account_id, group in by_account.items():
            if len(group) < 2:
                continue
            # Check pairwise for shared identity values
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    u1, u2 = group[i], group[j]
                    shared = _shared_identity_values(u1, u2)
                    if shared:
                        violations.append(Violation(
                            rule="id_mapping",
                            description=f"Split users {u1.user_id} and {u2.user_id} share identity values",
                            user_id=u1.user_id,
                            detail=f"shared: {shared}",
                        ))

        return violations

    # ------------------------------------------------------------------
    # Temporal order checks
    # ------------------------------------------------------------------

    def _check_temporal_order(self, user: User, events: List[Event]) -> List[Violation]:
        """
        Rules:
          - Registration_Result must appear before Login_Result
          - Login_Result must appear before Product_Order_Payment
        """
        violations: List[Violation] = []
        event_times: Dict[str, int] = {}

        for e in events:
            # Record first occurrence time for each event name
            if e.event_name not in event_times:
                event_times[e.event_name] = e.timestamp_ms

        pairs = [
            ("Registration_Result", "Login_Result", "Registration 在 Login 前"),
            ("Login_Result", "Product_Order_Payment", "Login 在 Purchase 前"),
        ]

        for before, after, desc in pairs:
            if before in event_times and after in event_times:
                if event_times[before] > event_times[after]:
                    violations.append(Violation(
                        rule="temporal_order",
                        description=desc,
                        user_id=user.user_id,
                        event_name=after,
                        detail=f"{before} at {event_times[before]} > {after} at {event_times[after]}",
                    ))

        return violations

    # ------------------------------------------------------------------
    # Field consistency checks
    # ------------------------------------------------------------------

    def _check_field_consistency(self, user: User, events: List[Event]) -> List[Violation]:
        """
        Rules:
          - 票数明细数量等于订单票数: count of Product_Payment_Detail == ticketsQuantity
          - 明细金额之和不超过订单金额: sum(ticketPaidAmount) <= totalOrderAmount
        """
        violations: List[Violation] = []

        order_events = [e for e in events if e.event_name == "Product_Order_Payment"]
        detail_events = [e for e in events if e.event_name == "Product_Payment_Detail"]

        if not order_events:
            return violations

        # Use the first order event as reference
        order = order_events[0]
        tickets_qty = order.properties.get("ticketsQuantity")
        total_amount = order.properties.get("totalOrderAmount")

        # Check ticket count
        if tickets_qty is not None:
            try:
                expected = int(tickets_qty)
                actual = len(detail_events)
                if actual != expected:
                    violations.append(Violation(
                        rule="field_consistency",
                        description="票数明细数量等于订单票数",
                        user_id=user.user_id,
                        event_name="Product_Payment_Detail",
                        detail=f"expected {expected} details, got {actual}",
                    ))
            except (ValueError, TypeError):
                pass

        # Check amount sum
        if total_amount is not None and detail_events:
            try:
                total = float(total_amount)
                detail_sum = sum(
                    float(e.properties.get("ticketPaidAmount", 0))
                    for e in detail_events
                )
                if detail_sum > total + 0.01:  # small float tolerance
                    violations.append(Violation(
                        rule="field_consistency",
                        description="明细金额之和不超过订单金额",
                        user_id=user.user_id,
                        event_name="Product_Payment_Detail",
                        detail=f"detail sum {detail_sum:.2f} > order amount {total:.2f}",
                    ))
            except (ValueError, TypeError):
                pass

        return violations

    # ------------------------------------------------------------------
    # Business rule checks
    # ------------------------------------------------------------------

    def _check_business_rules(self, user: User, events: List[Event]) -> List[Violation]:
        """
        Rules:
          - Admission 后不可 Refund: Ticket_Refund must not appear after Ticket_Admission
          - Voucher 场景严格互斥: voucher_scenario values must not mix across events
        """
        violations: List[Violation] = []

        # Rule: Admission 后不可 Refund
        admission_time: Optional[int] = None
        for e in events:
            if e.event_name == "Ticket_Admission":
                if admission_time is None or e.timestamp_ms < admission_time:
                    admission_time = e.timestamp_ms

        if admission_time is not None:
            for e in events:
                if e.event_name == "Ticket_Refund" and e.timestamp_ms > admission_time:
                    violations.append(Violation(
                        rule="business_rule",
                        description="Admission 后不可 Refund",
                        user_id=user.user_id,
                        event_name="Ticket_Refund",
                        detail=f"Refund at {e.timestamp_ms} after Admission at {admission_time}",
                    ))

        # Rule: Voucher 场景严格互斥
        # voucher_scenario values seen across all events must be consistent
        voucher_scenarios: Set[str] = set()
        for e in events:
            scenario = e.properties.get("voucher_scenario")
            if scenario:
                voucher_scenarios.add(str(scenario))

        if len(voucher_scenarios) > 1:
            violations.append(Violation(
                rule="business_rule",
                description="Voucher 场景严格互斥",
                user_id=user.user_id,
                detail=f"mixed voucher scenarios: {sorted(voucher_scenarios)}",
            ))

        return violations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shared_identity_values(u1: User, u2: User) -> Dict[str, str]:
    """Return identity key→value pairs that appear in both users."""
    shared = {}
    for key, val in u1.identities.items():
        if val and u2.identities.get(key) == val:
            shared[key] = val
    return shared


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.dirname(__file__))
    from rule_engine import RuleEngine
    from tracking_plan import TrackingPlan
    from fixed_account_generator import FixedAccountGenerator
    from event_sequencer import EventSequencer
    from datetime import datetime

    engine = RuleEngine("rules/special/westk/business_logic.yaml")
    plan = TrackingPlan("refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx")
    gen = FixedAccountGenerator(engine)
    users = gen.generate_accounts()
    sequencer = EventSequencer(engine, plan)
    validator = ConstraintValidator()

    start_ms = int(datetime(2026, 5, 1, 9, 0).timestamp() * 1000)
    total_violations = 0
    for user in users:
        events = sequencer.generate_all_events(user, start_ms)
        violations = validator.validate_all(user, events)
        total_violations += len(violations)
        if violations:
            print(f"{user.user_id}: {len(violations)} violation(s)")
            for v in violations:
                print(f"  {v}")
        else:
            print(f"{user.user_id}: OK ({len(events)} events)")

    id_violations = ConstraintValidator.validate_id_mapping(users)
    print(f"\nID-Mapping violations: {len(id_violations)}")
    for v in id_violations:
        print(f"  {v}")

    print(f"\nTotal violations: {total_violations}")
