"""
event_sequencer.py — Generate ordered event sequences for UAT test users.

Depends on:
  - rule_engine.py   : RuleEngine, EventSequence, EventDef, IdentityDef
  - tracking_plan.py : TrackingPlan
  - fixed_account_generator.py : User
"""

from __future__ import annotations

import random
import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rule_engine import RuleEngine, EventSequence, EventDef, IdentityDef
from tracking_plan import TrackingPlan
from fixed_account_generator import User
from mp_preset_builder import MpPresetBuilder


# ---------------------------------------------------------------------------
# Event dataclass
# ---------------------------------------------------------------------------


@dataclass
class Event:
    event_name: str
    user: User
    timestamp_ms: int
    properties: Dict[str, Any]
    platform: str = "MP"
    is_success: bool = True
    failure_reason: Optional[str] = None

    def to_track_record(self, project: str, identity_defs: List[IdentityDef]) -> dict:
        """Convert to Sensors Analytics batch import format."""
        identities = {}
        for idef in identity_defs:
            val = self.user.identities.get(idef.name)
            if val:
                identities[idef.sa_key] = val

        props: Dict[str, Any] = {}
        props.update(self.properties)
        # 公共属性默认值 — 仅在 property_enums 未覆盖时生效
        props["$lib"] = "python"
        props["$lib_version"] = "1.0.0"
        if "platformType" not in props:
            props["platformType"] = self.platform
        if "applicationName" not in props:
            props["applicationName"] = "WeChat" if self.platform == "MP" else "Web"
        if "version" not in props:
            props["version"] = "1.0.0"
        props["isSuccess"] = self.is_success
        if not self.is_success and self.failure_reason:
            props["failureReason"] = self.failure_reason

        # distinct_id: prefer crm_master_id, then first available identity
        distinct_id = self.user.identities.get("crm_master_id") or next(
            iter(self.user.identities.values()), self.user.user_id
        )

        return {
            "distinct_id": distinct_id,
            "login_id": distinct_id,
            "type": "track",
            "event": self.event_name,
            "time": self.timestamp_ms,
            "time_free": True,
            "$is_login_id": True,
            "project": project,
            "identities": identities,
            "properties": props,
        }


# ---------------------------------------------------------------------------
# EventSequencer
# ---------------------------------------------------------------------------

# Prefix that marks mutually-exclusive membership sequences
_MEMBERSHIP_PREFIX = "membership_"

# Regex to extract a field-reference from EventDef.repeat, e.g.
# "{Product_Order_Payment.ticketsQuantity}"
_REPEAT_REF_RE = re.compile(r"^\{([^}]+)\}$")


class PropertyEnumResolver:
    """Resolve property values from business_logic.yaml property_enums."""

    def __init__(self, enums: dict):
        self._enums = enums

    def resolve(self, name: str):
        """
        Return a business-compliant value for the given property name.
        Returns None if no enum is defined for this property.

        Supported formats:
          - list: random.choice(list)
          - {type: date_range, ...}: "YYYY.MM.DD - YYYY.MM.DD" string
          - {type: datetime, ...}: "YYYY/MM/DD HH:MM:SS" string
        """
        spec = self._enums.get(name)
        if spec is None:
            return None

        # Scalar value (e.g. applicationName: WestK)
        if not isinstance(spec, (list, dict)):
            return spec

        if isinstance(spec, list):
            if not spec:
                return None
            return random.choice(spec)

        if isinstance(spec, dict):
            t = spec.get("type")

            if t == "date_range":
                date_fmt = spec.get("date_format", "%Y.%m.%d")
                fmt = spec.get("format", "{start} - {end}")
                start_range = spec.get("start_range", ["2025-01-01", "2025-06-01"])
                duration_days = spec.get("duration_days", [60, 90])

                start_date = _dt.date.fromisoformat(start_range[0])
                end_start_date = _dt.date.fromisoformat(start_range[1])
                range_days = (end_start_date - start_date).days
                random_start = start_date + _dt.timedelta(days=random.randint(0, max(range_days, 0)))
                duration = random.randint(duration_days[0], duration_days[1])
                random_end = random_start + _dt.timedelta(days=duration)
                return fmt.format(start=random_start.strftime(date_fmt), end=random_end.strftime(date_fmt))

            if t == "date_relative_to_today":
                distribution = spec.get("distribution", {"active": 1.0})
                expired_range = spec.get("expired_range", [-365, -1])
                active_range = spec.get("active_range", [1, 365])
                date_fmt = spec.get("date_format", "%Y-%m-%d")

                roll = random.random()
                cumulative = 0.0
                chosen = "active"
                for bucket, weight in distribution.items():
                    cumulative += weight
                    if roll <= cumulative:
                        chosen = bucket
                        break

                if chosen == "expired":
                    days = random.randint(expired_range[0], expired_range[1])
                else:
                    days = random.randint(active_range[0], active_range[1])

                result = _dt.date.today() + _dt.timedelta(days=days)
                return result.strftime(date_fmt)

            if t == "weighted_int":
                values = spec.get("values", [])
                if not values:
                    return None
                population = [v["value"] for v in values]
                weights = [v.get("weight", 1.0) for v in values]
                return random.choices(population, weights=weights, k=1)[0]

            if t == "range":
                lo = spec.get("min", 1)
                hi = spec.get("max", 100)
                return round(random.uniform(lo, hi), 2)

            if t == "datetime":
                fmt = spec.get("format", "%Y/%m/%d %H:%M:%S")
                date_range = spec.get("range", ["2025-01-01", "2025-12-31"])
                start = _dt.datetime.fromisoformat(date_range[0])
                end = _dt.datetime.fromisoformat(date_range[1])
                delta = end - start
                random_seconds = random.randint(0, int(delta.total_seconds()))
                # Round to nearest 15 minutes for realistic show times
                random_seconds = (random_seconds // 900) * 900
                result = start + _dt.timedelta(seconds=random_seconds)
                return result.strftime(fmt)

        return None


class EventSequencer:
    def __init__(self, rule_engine: RuleEngine, tracking_plan: TrackingPlan):
        self.rule_engine = rule_engine
        self.tracking_plan = tracking_plan

        # Only initialise MpPresetBuilder if the tracking plan contains MP events
        self._mp_builder = None
        if tracking_plan.has_mp_events():
            preset_cfg = rule_engine.get_preset_events()
            self._mp_builder = MpPresetBuilder(
                page_routes=preset_cfg.get("page_routes"),
                utm_campaigns=preset_cfg.get("utm_campaigns"),
                scene_weights=preset_cfg.get("scene_distribution"),
            )

        # Initialise property enum resolver from rule engine
        self._prop_resolver = PropertyEnumResolver(rule_engine.get_property_enums())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all_events(
        self,
        user: User,
        start_time_ms: int,
        sessions_per_day: int = 1,
        days: int = 1,
    ) -> List[Event]:
        """
        Generate the complete ordered event sequence for a user.

        Steps:
          1. Run non-repeatable sequences once (lifecycle, purchase, membership).
          2. Run repeatable sequences (daily_activity, daily_search) once per session.
             Total sessions = sessions_per_day × days, spread across the time window.
          3. Handle membership_* sequences as a mutually-exclusive group.
          4. Apply conversion_rate probability for non-mandatory sequences.
          5. Append terminal-state events where configured.

        Returns events sorted by timestamp_ms.
        """
        all_events: List[Event] = []
        current_time_ms = start_time_ms

        context: Dict[str, Any] = {
            "segment": user.segment,
            "completed_events": [],
            "field_values": {},
        }

        sequences = self.rule_engine.get_event_sequences()

        # Partition sequences
        membership_seqs: List[EventSequence] = []
        repeatable_seqs: List[EventSequence] = []
        other_seqs: List[EventSequence] = []
        for seq in sequences:
            if seq.name.startswith(_MEMBERSHIP_PREFIX):
                membership_seqs.append(seq)
            elif seq.repeatable:
                repeatable_seqs.append(seq)
            else:
                other_seqs.append(seq)

        # --- Non-repeatable sequences (run once) ---
        for seq in other_seqs:
            if not self.rule_engine.evaluate_condition(seq.condition, context):
                continue
            if seq.conversion_rate is not None:
                if random.random() > seq.conversion_rate:
                    continue
            events = self._generate_sequence_events(seq, user, current_time_ms, context)
            if events:
                all_events.extend(events)
                current_time_ms = events[-1].timestamp_ms + 1
                for e in events:
                    if e.event_name not in context["completed_events"]:
                        context["completed_events"].append(e.event_name)
            if seq.terminal_states:
                terminal_event = self._pick_terminal_state(
                    seq.terminal_states, user, current_time_ms
                )
                if terminal_event:
                    all_events.append(terminal_event)
                    current_time_ms = terminal_event.timestamp_ms + 1
                    if terminal_event.event_name not in context["completed_events"]:
                        context["completed_events"].append(terminal_event.event_name)

        # --- Membership sequences (mutually exclusive, run once) ---
        applicable_membership: List[EventSequence] = [
            seq
            for seq in membership_seqs
            if self.rule_engine.evaluate_condition(seq.condition, context)
        ]
        if applicable_membership:
            chosen = self._weighted_choice(applicable_membership)
            if chosen is not None:
                events = self._generate_sequence_events(
                    chosen, user, current_time_ms, context
                )
                if events:
                    all_events.extend(events)
                    current_time_ms = events[-1].timestamp_ms + 1
                    for e in events:
                        if e.event_name not in context["completed_events"]:
                            context["completed_events"].append(e.event_name)
                if chosen.terminal_states:
                    terminal_event = self._pick_terminal_state(
                        chosen.terminal_states, user, current_time_ms
                    )
                    if terminal_event:
                        all_events.append(terminal_event)

        # --- Repeatable sequences (run sessions_per_day × days times) ---
        if repeatable_seqs:
            total_sessions = sessions_per_day * days
            window_ms = days * 86_400_000
            for session_idx in range(total_sessions):
                # Spread sessions evenly across the window with jitter
                slot_ms = window_ms // total_sessions
                session_base_ms = (
                    start_time_ms + session_idx * slot_ms + random.randint(0, slot_ms)
                )
                session_time_ms = session_base_ms

                for seq in repeatable_seqs:
                    if not self.rule_engine.evaluate_condition(seq.condition, context):
                        continue
                    if seq.conversion_rate is not None:
                        if random.random() > seq.conversion_rate:
                            continue
                    events = self._generate_sequence_events(
                        seq, user, session_time_ms, context
                    )
                    if events:
                        all_events.extend(events)
                        session_time_ms = events[-1].timestamp_ms + 1

        all_events.sort(key=lambda e: e.timestamp_ms)
        return all_events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_sequence_events(
        self,
        seq: EventSequence,
        user: User,
        base_time_ms: int,
        context: dict,
    ) -> List[Event]:
        """
        Generate events for a single EventSequence.

        - Timestamps accumulate via time_after_prev (seconds → ms).
        - EventDef.repeat resolves a field reference from context["field_values"]
          (default 2) and repeats the event N times, each 30 s apart.
        - EventDef.profile_update values are written into user.profile.
        - Properties not covered by EventDef.fields are filled via
          tracking_plan.generate_value().
        """
        events: List[Event] = []
        current_time_ms = base_time_ms

        for edef in seq.events:
            # Advance timestamp
            if edef.time_after_prev and events:
                lo = edef.time_after_prev.get("min", 0)
                hi = edef.time_after_prev.get("max", lo)
                delta_s = random.uniform(lo, hi)
                current_time_ms += int(delta_s * 1000)

            # Determine repeat count
            repeat_count = 1
            if edef.repeat:
                m = _REPEAT_REF_RE.match(str(edef.repeat))
                if m:
                    ref_key = m.group(1)
                    repeat_count = int(context["field_values"].get(ref_key, 2))
                else:
                    # Literal integer string
                    try:
                        repeat_count = int(edef.repeat)
                    except (ValueError, TypeError):
                        repeat_count = 2

            for rep_idx in range(repeat_count):
                ts = current_time_ms + rep_idx * 30_000  # 30 s between repeats

                props = self._build_properties(edef, user, context, ts=ts)

                event = Event(
                    event_name=edef.event,
                    user=user,
                    timestamp_ms=ts,
                    properties=props,
                )
                events.append(event)

                # Store field values for later reference (e.g. repeat counts)
                for k, v in props.items():
                    context["field_values"][f"{edef.event}.{k}"] = v

                # Generate derived events (e.g. payment details from an order)
                if edef.derive:
                    derived = self._generate_derived_events(
                        edef, event, user, context, rep_idx
                    )
                    events.extend(derived)

            # Advance past all repeats
            if repeat_count > 1:
                current_time_ms += (repeat_count - 1) * 30_000

            # Apply profile updates
            if edef.profile_update:
                for k, v in edef.profile_update.items():
                    user.profile[k] = v

        return events

    def _generate_derived_events(
        self,
        edef: EventDef,
        parent_event: Event,
        user: User,
        context: dict,
        parent_index: int = 0,
    ) -> List[Event]:
        """Generate child events from a parent event (e.g. order details)."""
        from datetime import datetime as _datetime

        derive = edef.derive
        if not derive:
            return []

        # Determine count
        count = derive.count or 1
        if derive.count_ref:
            m = _REPEAT_REF_RE.match(str(derive.count_ref))
            if m:
                ref_key = m.group(1)
                count = int(context["field_values"].get(ref_key, count))
            else:
                try:
                    count = int(derive.count_ref)
                except (ValueError, TypeError):
                    pass

        count = max(1, count)

        parent_props = parent_event.properties
        derived_events: List[Event] = []

        # Calculate distributed values (support both simple and mapped configs)
        distributed: Dict[str, Dict[str, Any]] = {}
        if derive.distribute_fields:
            for target_field, config in derive.distribute_fields.items():
                if isinstance(config, str):
                    # Simple form: field_name: strategy
                    source_field = target_field
                    strategy = config
                else:
                    # Mapped form: target_field: {source: source_field, strategy: strategy}
                    source_field = config.get("source", target_field)
                    strategy = config.get("strategy", "divide_evenly")

                total = parent_props.get(source_field, 0)
                if not isinstance(total, (int, float)):
                    total = 0

                if strategy == "divide_evenly":
                    base = round(total / count, 2)
                    distributed[target_field] = {
                        "source": source_field,
                        "base": base,
                        "total": total,
                        "strategy": strategy,
                    }

        import random as _random
        import time as _time

        for i in range(count):
            ts = parent_event.timestamp_ms + (i + 1) * derive.gap_seconds * 1000
            props: Dict[str, Any] = {}

            # Carry fields from parent
            if derive.carry_fields:
                for field in derive.carry_fields:
                    if field in parent_props:
                        props[field] = parent_props[field]

            # Apply distributed values
            for target_field, dist in distributed.items():
                if i == count - 1:
                    # Adjust last detail to ensure sum equals parent total
                    current_sum = sum(
                        distributed[f]["base"] for f in distributed if f != target_field
                    )
                    current_sum += sum(
                        distributed[target_field]["base"] for _ in range(count - 1)
                    )
                    props[target_field] = round(dist["total"] - current_sum, 2)
                else:
                    props[target_field] = dist["base"]

            # Apply prefix-generated fields
            if derive.prefix_fields:
                for field, template in derive.prefix_fields.items():
                    try:
                        props[field] = template.format(
                            orderIndex=parent_index,
                            detailIndex=i,
                            parentEvent=parent_event.event_name,
                            timestamp=int(_time.time() * 1000),
                            random="".join(_random.choices("0123456789ABCDEF", k=6)),
                        )
                    except (KeyError, ValueError):
                        props[field] = template

            # Fill remaining schema properties
            schema = self.tracking_plan.get_event_schema(derive.event)
            event_dt = _datetime.fromtimestamp(ts / 1000)
            if schema:
                for prop_def in schema.properties:
                    if prop_def.name not in props:
                        resolved = self._prop_resolver.resolve(prop_def.name)
                        if resolved is not None:
                            props[prop_def.name] = resolved
                        else:
                            props[prop_def.name] = self.tracking_plan.generate_value(prop_def, event_dt)

            derived_events.append(
                Event(
                    event_name=derive.event,
                    user=user,
                    timestamp_ms=ts,
                    properties=props,
                )
            )

        return derived_events

    def _build_properties(
        self, edef: EventDef, user: User, context: dict, ts: int = 0
    ) -> Dict[str, Any]:
        """
        Build the properties dict for a single event.

        Priority:
          1. Fixed values from edef.fields
          2. Preset event properties for $MP* events (scene, UTM, url, etc.)
          3. Schema-driven generated values for remaining properties
        """
        props: Dict[str, Any] = {}

        # 1. Fixed fields from YAML
        if edef.fields:
            props.update(edef.fields)

        # 2. Preset properties for $MP* events (only if MP preset builder is active)
        if edef.event.startswith("$") and self._mp_builder is not None:
            current_url = context.get("current_url", "")
            referrer = context.get("referrer", "")
            preset = self._mp_builder.build_props_for_event(
                edef.event, current_url=current_url, referrer=referrer
            )
            for k, v in preset.items():
                if k not in props:
                    props[k] = v
            # Inherit scene from current session for events that don't generate their own
            if "$scene" not in props or not props["$scene"]:
                session_scene = context.get("session_scene", "")
                if session_scene:
                    props["$scene"] = session_scene
            # Update page context for subsequent events
            new_url = props.get("$url", "")
            if new_url and edef.event not in ("$MPHide", "$MPPageLeave"):
                context["referrer"] = context.get("current_url", "")
                context["current_url"] = new_url
            # Track session scene for inheritance
            if "$scene" in props and props["$scene"]:
                context["session_scene"] = props["$scene"]

        # 3. Fill remaining schema properties, with property_enums taking priority
        from datetime import datetime as _datetime
        event_dt = _datetime.fromtimestamp(ts / 1000) if ts else None
        schema = self.tracking_plan.get_event_schema(edef.event)
        if schema:
            for prop_def in schema.properties:
                if prop_def.name not in props:
                    # Try business enum resolver first
                    resolved = self._prop_resolver.resolve(prop_def.name)
                    if resolved is not None:
                        props[prop_def.name] = resolved
                    else:
                        props[prop_def.name] = self.tracking_plan.generate_value(prop_def, event_dt)

        # 4. Allow property_enums to override hardcoded public fields (e.g. applicationName)
        for override_key in ("applicationName", "version", "platformType"):
            resolved = self._prop_resolver.resolve(override_key)
            if resolved is not None:
                props[override_key] = resolved

        return props

    def _pick_terminal_state(
        self,
        terminal_states: List[str],
        user: User,
        last_time_ms: int,
    ) -> Optional[Event]:
        """Pick one terminal-state event at random."""
        if not terminal_states:
            return None

        event_name = random.choice(terminal_states)
        # Small gap after the last event (1–5 minutes)
        gap_ms = random.randint(60, 300) * 1000
        ts = last_time_ms + gap_ms

        from datetime import datetime as _datetime
        event_dt = _datetime.fromtimestamp(ts / 1000)
        schema = self.tracking_plan.get_event_schema(event_name)
        props: Dict[str, Any] = {}
        if schema:
            for prop_def in schema.properties:
                resolved = self._prop_resolver.resolve(prop_def.name)
                if resolved is not None:
                    props[prop_def.name] = resolved
                else:
                    props[prop_def.name] = self.tracking_plan.generate_value(prop_def, event_dt)

        return Event(
            event_name=event_name,
            user=user,
            timestamp_ms=ts,
            properties=props,
        )

    @staticmethod
    def _weighted_choice(sequences: List[EventSequence]) -> Optional[EventSequence]:
        """
        Pick one sequence by conversion_rate weight.
        Sequences without a conversion_rate are treated as weight 1.0.
        Returns None if the total weight roll fails (i.e. all rates < 1 and
        the random draw exceeds the sum).
        """
        if not sequences:
            return None

        weights = [
            seq.conversion_rate if seq.conversion_rate is not None else 1.0
            for seq in sequences
        ]
        total = sum(weights)

        # Roll against total weight; if total < 1 there's a chance of no selection
        roll = random.random()
        if roll > total:
            return None

        # Weighted pick within the selected bucket
        cumulative = 0.0
        for seq, w in zip(sequences, weights):
            cumulative += w
            if roll <= cumulative:
                return seq

        return sequences[-1]


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
    from datetime import datetime

    engine = RuleEngine("rules/special/westk/business_logic.yaml")
    plan = TrackingPlan("refrences/Annex 6 - Tracking Plan - Mini Program_V0.1.xlsx")
    gen = FixedAccountGenerator(engine)
    users = gen.generate_accounts()
    sequencer = EventSequencer(engine, plan)

    start_ms = int(datetime(2026, 5, 1, 9, 0).timestamp() * 1000)
    for user in users[:3]:
        events = sequencer.generate_all_events(user, start_ms)
        print(f"{user.user_id} ({user.segment}): {len(events)} events")
        for e in events[:5]:
            ts = datetime.fromtimestamp(e.timestamp_ms / 1000).strftime("%H:%M:%S")
            print(f"  {ts} {e.event_name}")
        if len(events) > 5:
            print(f"  ... ({len(events) - 5} more)")
