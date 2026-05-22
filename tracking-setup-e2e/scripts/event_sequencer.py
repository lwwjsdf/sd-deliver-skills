"""
event_sequencer.py — Generate ordered event sequences for UAT test users.

Depends on:
  - rule_engine.py   : RuleEngine, EventSequence, EventDef, IdentityDef
  - tracking_plan.py : TrackingPlan
  - fixed_account_generator.py : User
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rule_engine import RuleEngine, EventSequence, EventDef, IdentityDef
from tracking_plan import TrackingPlan
from fixed_account_generator import User


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

        props: Dict[str, Any] = {
            "$lib": "python",
            "$lib_version": "1.0.0",
            "platformType": self.platform,
            "applicationName": "WeChat" if self.platform == "MP" else "Web",
            "version": "1.0.0",
            "isSuccess": self.is_success,
        }
        if not self.is_success and self.failure_reason:
            props["failureReason"] = self.failure_reason
        props.update(self.properties)

        # distinct_id: prefer crm_master_id, then first available identity
        distinct_id = (
            self.user.identities.get("crm_master_id")
            or next(iter(self.user.identities.values()), self.user.user_id)
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
_REPEAT_REF_RE = re.compile(r'^\{([^}]+)\}$')


class EventSequencer:
    def __init__(self, rule_engine: RuleEngine, tracking_plan: TrackingPlan):
        self.rule_engine = rule_engine
        self.tracking_plan = tracking_plan

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all_events(self, user: User, start_time_ms: int) -> List[Event]:
        """
        Generate the complete ordered event sequence for a user.

        Steps:
          1. Iterate all EventSequences from the rule engine.
          2. Evaluate seq.condition against the running context.
          3. Handle membership_* sequences as a mutually-exclusive group.
          4. For non-membership sequences apply conversion_rate probability.
          5. Generate events for each selected sequence, accumulating
             completed_events and field_values in context.
          6. Append a terminal-state event when seq.terminal_states is set.

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

        # Separate membership sequences from the rest
        membership_seqs: List[EventSequence] = []
        other_seqs: List[EventSequence] = []
        for seq in sequences:
            if seq.name.startswith(_MEMBERSHIP_PREFIX):
                membership_seqs.append(seq)
            else:
                other_seqs.append(seq)

        # Process non-membership sequences in order
        for seq in other_seqs:
            if not self.rule_engine.evaluate_condition(seq.condition, context):
                continue

            # Optional conversion rate gate
            if seq.conversion_rate is not None:
                if random.random() > seq.conversion_rate:
                    continue

            events = self._generate_sequence_events(seq, user, current_time_ms, context)
            if events:
                all_events.extend(events)
                current_time_ms = events[-1].timestamp_ms + 1
                # Update completed_events in context
                for e in events:
                    if e.event_name not in context["completed_events"]:
                        context["completed_events"].append(e.event_name)

            # Terminal state
            if seq.terminal_states:
                terminal_event = self._pick_terminal_state(
                    seq.terminal_states, user, current_time_ms
                )
                if terminal_event:
                    all_events.append(terminal_event)
                    current_time_ms = terminal_event.timestamp_ms + 1
                    if terminal_event.event_name not in context["completed_events"]:
                        context["completed_events"].append(terminal_event.event_name)

        # Process membership sequences — pick at most one by weighted random
        applicable_membership: List[EventSequence] = [
            seq for seq in membership_seqs
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

                props = self._build_properties(edef, user, context)

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

            # Advance past all repeats
            if repeat_count > 1:
                current_time_ms += (repeat_count - 1) * 30_000

            # Apply profile updates
            if edef.profile_update:
                for k, v in edef.profile_update.items():
                    user.profile[k] = v

        return events

    def _build_properties(
        self, edef: EventDef, user: User, context: dict
    ) -> Dict[str, Any]:
        """
        Build the properties dict for a single event.

        Priority:
          1. Fixed values from edef.fields
          2. Schema-driven generated values for remaining properties
        """
        props: Dict[str, Any] = {}

        # 1. Fixed fields
        if edef.fields:
            props.update(edef.fields)

        # 2. Fill remaining schema properties
        schema = self.tracking_plan.get_event_schema(edef.event)
        if schema:
            for prop_def in schema.properties:
                if prop_def.name not in props:
                    props[prop_def.name] = self.tracking_plan.generate_value(prop_def)

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

        schema = self.tracking_plan.get_event_schema(event_name)
        props: Dict[str, Any] = {}
        if schema:
            for prop_def in schema.properties:
                props[prop_def.name] = self.tracking_plan.generate_value(prop_def)

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

        weights = [seq.conversion_rate if seq.conversion_rate is not None else 1.0
                   for seq in sequences]
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
