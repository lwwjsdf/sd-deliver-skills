"""
yaml_validator.py — Static validation of business_logic.yaml before mock data generation.

Three validation layers:
  1. Structure   — required fields, correct types, known enum values
  2. References  — event names exist in Tracking Plan, field keys are valid properties
  3. Business    — segment ratios sum to 1, conversion_rate in [0,1], condition syntax
"""

from __future__ import annotations

import re
import sys
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    level: str          # "error" | "warning"
    layer: str          # "structure" | "reference" | "business"
    path: str           # YAML path, e.g. "event_sequences[2].events[0].event"
    message: str

    def __str__(self):
        icon = "✗" if self.level == "error" else "⚠"
        return f"  {icon} [{self.layer}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self):
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i.level == "warning"]

    @property
    def passed(self):
        return len(self.errors) == 0

    def add_error(self, layer: str, path: str, message: str):
        self.issues.append(ValidationIssue("error", layer, path, message))

    def add_warning(self, layer: str, path: str, message: str):
        self.issues.append(ValidationIssue("warning", layer, path, message))

    def summary(self) -> str:
        if self.passed:
            return f"✓ PASSED  ({len(self.warnings)} warnings, {len(self.errors)} errors)"
        return f"✗ FAILED  ({len(self.errors)} errors, {len(self.warnings)} warnings)"


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

_VALID_REGIONS = {"mainland", "hongkong", "overseas"}
_VALID_SEGMENTS = {"L0", "L1", "L2", "L3", "L4"}
_CONDITION_PATTERNS = [
    re.compile(r"^segment\s+in\s+\[([^\]]+)\]$"),
    re.compile(r"^has\s+\S+$"),
    re.compile(r"^not\s+\S+$"),
]


class YamlValidator:
    def __init__(self, yaml_path: str, tracking_plan=None):
        """
        tracking_plan: optional TrackingPlan instance for reference validation.
        If None, reference checks are skipped with a warning.
        """
        with open(yaml_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)
        self._plan = tracking_plan
        self._known_events: Set[str] = set(tracking_plan.list_events()) if tracking_plan else set()

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        self._check_meta(result)
        self._check_region_distribution(result)
        self._check_user_segments(result)
        self._check_identity_priority(result)
        self._check_event_sequences(result)
        self._check_fixed_accounts(result)
        if not self._plan:
            result.add_warning("reference", "tracking_plan", "No Tracking Plan provided — reference checks skipped")
        return result

    # ------------------------------------------------------------------
    # Layer 1: Structure checks
    # ------------------------------------------------------------------

    def _check_meta(self, r: ValidationResult):
        meta = self._data.get("meta")
        if not meta:
            r.add_error("structure", "meta", "Missing required section")
            return
        if not meta.get("project"):
            r.add_error("structure", "meta.project", "Missing required field")
        if not meta.get("version"):
            r.add_warning("structure", "meta.version", "Missing version field")

    def _check_region_distribution(self, r: ValidationResult):
        rd = self._data.get("region_distribution")
        if not rd:
            r.add_error("structure", "region_distribution", "Missing required section")
            return
        if not isinstance(rd, dict):
            r.add_error("structure", "region_distribution", "Must be a mapping")
            return
        for region in rd:
            if region not in _VALID_REGIONS:
                r.add_warning("structure", f"region_distribution.{region}",
                              f"Unknown region '{region}' (known: {sorted(_VALID_REGIONS)})")
        total = sum(float(v) for v in rd.values())
        if abs(total - 1.0) > 0.001:
            r.add_error("business", "region_distribution",
                        f"Values sum to {total:.4f}, must equal 1.0")

    def _check_user_segments(self, r: ValidationResult):
        segs = self._data.get("user_segments")
        if not segs:
            r.add_error("structure", "user_segments", "Missing required section")
            return
        total = 0.0
        for name, cfg in segs.items():
            path = f"user_segments.{name}"
            if name not in _VALID_SEGMENTS:
                r.add_warning("structure", path, f"Unknown segment name '{name}'")
            ratio = cfg.get("ratio")
            if ratio is None:
                r.add_error("structure", f"{path}.ratio", "Missing required field")
            elif not isinstance(ratio, (int, float)) or ratio < 0:
                r.add_error("structure", f"{path}.ratio", f"Must be a non-negative number, got {ratio!r}")
            else:
                total += float(ratio)
        if abs(total - 1.0) > 0.001:
            r.add_error("business", "user_segments",
                        f"Ratios sum to {total:.4f}, must equal 1.0")

    def _check_identity_priority(self, r: ValidationResult):
        ip = self._data.get("identity_priority")
        if not ip:
            r.add_error("structure", "identity_priority", "Missing required section")
            return
        for name, cfg in ip.items():
            path = f"identity_priority.{name}"
            # cfg can be a dict (legacy) or a list (new format)
            if isinstance(cfg, list):
                if not cfg:
                    r.add_error("structure", path, "Empty list")
                continue
            if not isinstance(cfg, dict):
                r.add_error("structure", path, f"Must be a dict or list, got {type(cfg).__name__}")
                continue
            if cfg.get("priority") is None:
                r.add_error("structure", f"{path}.priority", "Missing required field")
            if not cfg.get("sa_key"):
                r.add_error("structure", f"{path}.sa_key", "Missing required field")

    def _check_event_sequences(self, r: ValidationResult):
        seqs = self._data.get("event_sequences")
        if not seqs:
            r.add_warning("structure", "event_sequences", "No event sequences defined")
            return

        names_seen: Set[str] = set()
        for i, seq in enumerate(seqs):
            path = f"event_sequences[{i}]"
            name = seq.get("name", "")
            if not name:
                r.add_error("structure", f"{path}.name", "Missing required field")
            elif name in names_seen:
                r.add_error("structure", f"{path}.name", f"Duplicate sequence name '{name}'")
            else:
                names_seen.add(name)

            # condition syntax
            cond = seq.get("condition")
            if cond:
                self._check_condition(r, f"{path}.condition", cond)

            # conversion_rate
            cr = seq.get("conversion_rate")
            if cr is not None:
                if not isinstance(cr, (int, float)) or not (0.0 <= float(cr) <= 1.0):
                    r.add_error("structure", f"{path}.conversion_rate",
                                f"Must be a float in [0, 1], got {cr!r}")

            # terminal_states
            for ts in seq.get("terminal_states") or []:
                self._check_event_ref(r, f"{path}.terminal_states", ts)

            # events list
            events = seq.get("events") or []
            if not events:
                r.add_warning("structure", f"{path}.events", "Sequence has no events")
            for j, ev in enumerate(events):
                self._check_event_def(r, f"{path}.events[{j}]", ev)

    def _check_event_def(self, r: ValidationResult, path: str, ev: Any):
        if not isinstance(ev, dict):
            r.add_error("structure", path, f"Event definition must be a mapping, got {type(ev).__name__}")
            return

        event_name = ev.get("event")
        if not event_name:
            r.add_error("structure", f"{path}.event", "Missing required field")
        else:
            self._check_event_ref(r, f"{path}.event", event_name)

        # time_after_prev
        tap = ev.get("time_after_prev")
        if tap is not None:
            if not isinstance(tap, dict):
                r.add_error("structure", f"{path}.time_after_prev", "Must be a mapping with min/max")
            else:
                lo = tap.get("min", 0)
                hi = tap.get("max", lo)
                if lo > hi:
                    r.add_error("business", f"{path}.time_after_prev",
                                f"min ({lo}) > max ({hi})")

        # fields — check keys against tracking plan schema
        fields = ev.get("fields")
        if fields and event_name and self._plan:
            schema = self._plan.get_event_schema(event_name)
            if schema:
                valid_props = {p.name for p in schema.properties}
                for key in fields:
                    if key not in valid_props:
                        r.add_warning("reference", f"{path}.fields.{key}",
                                      f"Property '{key}' not found in Tracking Plan schema for '{event_name}'")

        # repeat — must be integer literal or {EventName.fieldName}
        repeat = ev.get("repeat")
        if repeat is not None:
            repeat_str = str(repeat)
            if not re.match(r'^\d+$', repeat_str) and not re.match(r'^\{[^}]+\}$', repeat_str):
                r.add_error("structure", f"{path}.repeat",
                            f"Must be an integer or {{EventName.fieldName}}, got {repeat_str!r}")

    def _check_fixed_accounts(self, r: ValidationResult):
        accounts = self._data.get("fixed_accounts") or []
        ids_seen: Set[str] = set()
        for i, acc in enumerate(accounts):
            path = f"fixed_accounts[{i}]"
            acc_id = acc.get("id", "")
            if not acc_id:
                r.add_error("structure", f"{path}.id", "Missing required field")
            elif acc_id in ids_seen:
                r.add_error("structure", f"{path}.id", f"Duplicate account id '{acc_id}'")
            else:
                ids_seen.add(acc_id)

            region = acc.get("region")
            if region and region not in _VALID_REGIONS:
                r.add_warning("structure", f"{path}.region",
                              f"Unknown region '{region}'")

            segment = acc.get("segment")
            if not segment:
                r.add_error("structure", f"{path}.segment", "Missing required field")
            elif segment not in _VALID_SEGMENTS:
                r.add_warning("structure", f"{path}.segment",
                              f"Unknown segment '{segment}'")

            # split_identity consistency
            if acc.get("split_identity"):
                if not acc.get("split_groups"):
                    r.add_error("structure", f"{path}.split_groups",
                                "split_identity=true requires split_groups to be defined")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_event_ref(self, r: ValidationResult, path: str, event_name: str):
        if self._known_events and event_name not in self._known_events:
            r.add_error("reference", path,
                        f"Event '{event_name}' not found in Tracking Plan")

    def _check_condition(self, r: ValidationResult, path: str, cond: str):
        for pattern in _CONDITION_PATTERNS:
            if pattern.match(cond.strip()):
                return
        r.add_error("structure", path,
                    f"Unrecognised condition syntax: {cond!r}. "
                    "Supported: 'segment in [L1,L2]', 'has EventName', 'not EventName'")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate business_logic.yaml")
    parser.add_argument("yaml_path", help="Path to business_logic.yaml")
    parser.add_argument("--tracking-plan", default=None, dest="tracking_plan",
                        help="Path to Tracking Plan Excel (enables reference checks)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 on warnings too")
    args = parser.parse_args()

    plan = None
    if args.tracking_plan:
        sys.path.insert(0, os.path.dirname(__file__))
        from tracking_plan import TrackingPlan
        plan = TrackingPlan(args.tracking_plan)

    validator = YamlValidator(args.yaml_path, tracking_plan=plan)
    result = validator.validate()

    print(f"\nValidating: {args.yaml_path}")
    if args.tracking_plan:
        print(f"Against:    {args.tracking_plan}")
    print()

    if result.errors:
        print(f"Errors ({len(result.errors)}):")
        for issue in result.errors:
            print(issue)
        print()

    if result.warnings:
        print(f"Warnings ({len(result.warnings)}):")
        for issue in result.warnings:
            print(issue)
        print()

    print(result.summary())

    if not result.passed or (args.strict and result.warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
