import re
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class UserSegment:
    name: str
    ratio: float
    identities: List[str]
    has_registration: bool
    has_purchase: bool
    has_membership: bool
    membership_activated: bool


@dataclass
class IdentityDef:
    name: str
    priority: int
    display: str
    sa_key: str


@dataclass
class DeriveConfig:
    event: str
    count_ref: Optional[str] = None
    count: Optional[int] = None
    distribute_fields: Optional[Dict[str, Any]] = None
    prefix_fields: Optional[Dict[str, str]] = None
    carry_fields: Optional[List[str]] = None
    gap_seconds: int = 1


@dataclass
class EventDef:
    event: str
    required: bool = True
    time_after_prev: Optional[Dict] = None
    conversion_rate: Optional[float] = None
    fields: Optional[Dict] = None
    profile_update: Optional[Dict] = None
    repeat: Optional[str] = None
    derive: Optional[DeriveConfig] = None


@dataclass
class EventSequence:
    name: str
    events: List[EventDef]
    condition: Optional[str] = None
    conversion_rate: Optional[float] = None
    terminal_states: Optional[List[str]] = None
    repeatable: bool = False


@dataclass
class Constraint:
    description: str
    constraint_type: str
    rule: Optional[str] = None


@dataclass
class FixedAccount:
    id: str
    region: str
    segment: str
    identities: Dict[str, Any]
    purpose: str = ""
    split_identity: bool = False
    split_groups: Optional[List[Dict[str, str]]] = None
    note: str = ""


# Identity fields recognized in fixed_accounts entries
_IDENTITY_KEYS = {"crm_master_id", "email", "mobile", "unionid", "cookie_id", "cookie_ids"}


class RuleEngine:
    def __init__(self, rule_path: str):
        with open(rule_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)
        self._validate_segment_ratios()

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_user_segments(self) -> List[UserSegment]:
        segments = []
        for name, cfg in self._data.get("user_segments", {}).items():
            segments.append(UserSegment(
                name=name,
                ratio=cfg.get("ratio", 0.0),
                identities=cfg.get("identities", []),
                has_registration=cfg.get("has_registration", False),
                has_purchase=cfg.get("has_purchase", False),
                has_membership=cfg.get("has_membership", False),
                membership_activated=cfg.get("membership_activated", False),
            ))
        return segments

    def get_region_distribution(self) -> Dict[str, float]:
        return dict(self._data.get("region_distribution", {}))

    def get_identity_priority(self) -> List[IdentityDef]:
        identities = []
        for name, cfg in self._data.get("identity_priority", {}).items():
            identities.append(IdentityDef(
                name=name,
                priority=cfg.get("priority", 99),
                display=cfg.get("display", name),
                sa_key=cfg.get("sa_key", ""),
            ))
        identities.sort(key=lambda x: x.priority)
        return identities

    def get_event_sequences(self) -> List[EventSequence]:
        sequences = []
        for seq in self._data.get("event_sequences", []):
            events = []
            for ev in seq.get("events", []):
                if isinstance(ev, dict):
                    derive_cfg = ev.get("derive")
                    derive = None
                    if derive_cfg:
                        derive = DeriveConfig(
                            event=derive_cfg.get("event", ""),
                            count_ref=derive_cfg.get("count_ref"),
                            count=derive_cfg.get("count"),
                            distribute_fields=derive_cfg.get("distribute_fields"),
                            prefix_fields=derive_cfg.get("prefix_fields"),
                            carry_fields=derive_cfg.get("carry_fields"),
                            gap_seconds=derive_cfg.get("gap_seconds", 1),
                        )
                    events.append(EventDef(
                        event=ev.get("event", ""),
                        required=ev.get("required", True),
                        time_after_prev=ev.get("time_after_prev"),
                        conversion_rate=ev.get("conversion_rate"),
                        fields=ev.get("fields"),
                        profile_update=ev.get("profile_update"),
                        repeat=ev.get("repeat"),
                        derive=derive,
                    ))
                elif isinstance(ev, str):
                    events.append(EventDef(event=ev))
            sequences.append(EventSequence(
                name=seq.get("name", ""),
                events=events,
                condition=seq.get("condition"),
                conversion_rate=seq.get("conversion_rate"),
                terminal_states=seq.get("terminal_states"),
                repeatable=seq.get("repeatable", False),
            ))
        return sequences

    def get_fixed_accounts(self) -> List[FixedAccount]:
        accounts = []
        for entry in self._data.get("fixed_accounts", []):
            identities: Dict[str, Any] = {}
            for key in _IDENTITY_KEYS:
                if key in entry:
                    identities[key] = entry[key]
            accounts.append(FixedAccount(
                id=entry.get("id", ""),
                region=entry.get("region", ""),
                segment=entry.get("segment", ""),
                identities=identities,
                purpose=entry.get("purpose", ""),
                split_identity=entry.get("split_identity", False),
                split_groups=entry.get("split_groups"),
                note=entry.get("note", ""),
            ))
        return accounts

    def get_constraints(self) -> List[Constraint]:
        constraints = []
        for c in self._data.get("constraints", []):
            constraints.append(Constraint(
                description=c.get("description", ""),
                constraint_type=c.get("type", ""),
                rule=c.get("rule"),
            ))
        return constraints

    def get_enum_values(self, field_name: str) -> List[str]:
        enums = self._data.get("enums", {})
        raw = enums.get(field_name, [])
        result = []
        for item in raw:
            if isinstance(item, dict):
                result.append(item.get("value", str(item)))
            else:
                result.append(str(item))
        return result

    def get_failure_rate(self) -> float:
        return float(self._data.get("failure_rate", 0.0))

    def get_preset_events(self) -> Dict[str, Any]:
        return dict(self._data.get("preset_events", {}))

    def get_property_enums(self) -> Dict[str, Any]:
        """Return the property_enums block, or empty dict if not defined."""
        return dict(self._data.get("property_enums", {}))

    def get_meta(self) -> Dict[str, Any]:
        return dict(self._data.get("meta", {}))

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    def evaluate_condition(self, condition: Optional[str], context: Dict) -> bool:
        """
        Evaluate a condition string against a context dict.

        Supported patterns:
          - None or ""                          → True
          - "segment in [L1, L2, L3]"          → segment membership test
          - "has SomeEvent"                     → event in completed_events
          - "not SomeEvent"                     → event not in completed_events

        Raises ValueError for unrecognised patterns.
        """
        if condition is None or condition.strip() == "":
            return True

        cond = condition.strip()

        # Pattern: segment in [L0, L1, ...]
        m = re.fullmatch(r"segment\s+in\s+\[([^\]]+)\]", cond)
        if m:
            allowed = [v.strip() for v in m.group(1).split(",")]
            return context.get("segment", "") in allowed

        # Pattern: has EventName
        m = re.fullmatch(r"has\s+(\S+)", cond)
        if m:
            event_name = m.group(1)
            return event_name in context.get("completed_events", [])

        # Pattern: not EventName
        m = re.fullmatch(r"not\s+(\S+)", cond)
        if m:
            event_name = m.group(1)
            return event_name not in context.get("completed_events", [])

        raise ValueError(f"Unrecognised condition pattern: {condition!r}")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_segment_ratios(self):
        segments = self._data.get("user_segments", {})
        total = sum(cfg.get("ratio", 0.0) for cfg in segments.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Segment ratios sum to {total:.4f}, expected 1.0 (tolerance 0.001)"
            )


if __name__ == "__main__":
    import sys

    yaml_path = sys.argv[1] if len(sys.argv) > 1 else "rules/special/westk/business_logic.yaml"
    engine = RuleEngine(yaml_path)
    print(f"Segments: {[s.name for s in engine.get_user_segments()]}")
    print(f"Region dist: {engine.get_region_distribution()}")
    print(f"Fixed accounts: {[a.id for a in engine.get_fixed_accounts()]}")
    print(f"Sequences: {[s.name for s in engine.get_event_sequences()]}")

    assert engine.evaluate_condition("segment in [L2, L3, L4]", {"segment": "L2"}) == True
    assert engine.evaluate_condition("segment in [L2, L3, L4]", {"segment": "L0"}) == False
    assert engine.evaluate_condition(None, {}) == True
    print("All assertions passed.")
