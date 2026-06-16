#!/usr/bin/env python3
"""
project_context.py — read/write project-level context for sdeliver skills.

Usage:
    ./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set \
      business.dau 1000000 --source sd-design-performance-test

    ./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py get business.dau

    ./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py check \
      --skill sd-design-performance-test

    ./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py list
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("Missing dependency: PyYAML")
    print("Run: ./venv/bin/pip install -r <skill-repo>/requirements.txt")
    sys.exit(1)


DEFAULT_FILENAME = "PROJECT_CONTEXT.yaml"

# Registry of context keys required/used by each skill.
# This is the single source of truth for skill context schemas.
# Add new skills here as they adopt the context mechanism.
SKILL_SCHEMAS: Dict[str, Dict[str, List[str]]] = {
    "sd-design-performance-test": {
        "required": [
            "business.dau",
            "business.daily_events",
            "business.retention_days",
            "infra.cloud",
            "infra.region",
        ],
        "optional": [
            "business.peak_qps",
            "business.mau",
            "sla.realtime_import_qps",
            "sla.batch_import_records_per_hour",
            "sla.analytics_query_p95_seconds",
            "sla.email_send_per_minute",
            "env.cdp_url",
            "env.has_pii_encryption",
            "infra.include_cdp",
            "infra.include_ma",
        ],
    },
    "sd-size-server": {
        "required": [
            "business.dau",
            "business.daily_events",
            "business.retention_days",
        ],
        "optional": [
            "business.mau",
            "business.history_events",
            "infra.cloud",
            "infra.region",
            "infra.include_cdp",
            "infra.include_ma",
            "sla.realtime_import_qps",
            "sla.batch_import_records_per_hour",
        ],
    },
}


def _find_project_root() -> Path:
    """Walk up from cwd looking for .env + PROJECT_CONTEXT.yaml or just .env."""
    dir_ = Path.cwd()
    while dir_ != Path(dir_.anchor):
        if (dir_ / ".env").exists():
            return dir_
        dir_ = dir_.parent
    # Fallback: use cwd
    return Path.cwd()


def _load_context(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "version": "1.0",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "facts": {},
        }
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "facts" not in data:
        data["facts"] = {}
    return data


def _save_context(path: Path, data: Dict[str, Any]) -> None:
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _parse_value(value: str) -> Any:
    """Parse CLI string value into JSON-compatible scalar."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def get_context_value(context_path: Path, key: str) -> Optional[Any]:
    data = _load_context(context_path)
    return data.get("facts", {}).get(key)


def set_context_value(
    context_path: Path,
    key: str,
    value: Any,
    source: str = "",
    overwrite: bool = False,
) -> bool:
    data = _load_context(context_path)
    facts = data.setdefault("facts", {})

    if key in facts and not overwrite:
        return False

    # Parse string values that look like JSON scalars when called programmatically
    if isinstance(value, str):
        value = _parse_value(value)

    facts[key] = value
    if source:
        sources = data.setdefault("_sources", {})
        sources[key] = source
    _save_context(context_path, data)
    return True


def check_skill_context(context_path: Path, skill: str) -> Dict[str, List[str]]:
    schema = SKILL_SCHEMAS.get(skill)
    if not schema:
        return {"known": [], "missing": [], "optional_present": [], "optional_missing": []}

    data = _load_context(context_path)
    facts = data.get("facts", {})

    known = [k for k in schema["required"] if k in facts]
    missing = [k for k in schema["required"] if k not in facts]
    optional_present = [k for k in schema.get("optional", []) if k in facts]
    optional_missing = [k for k in schema.get("optional", []) if k not in facts]

    return {
        "known": known,
        "missing": missing,
        "optional_present": optional_present,
        "optional_missing": optional_missing,
    }


def _render_check(result: Dict[str, List[str]]) -> str:
    lines = []
    if result["known"]:
        lines.append("Known:")
        for k in result["known"]:
            lines.append(f"  ✅ {k}")
    if result["missing"]:
        lines.append("Missing (required):")
        for k in result["missing"]:
            lines.append(f"  ❌ {k}")
    if result["optional_present"]:
        lines.append("Optional known:")
        for k in result["optional_present"]:
            lines.append(f"  ✅ {k}")
    if result["optional_missing"]:
        lines.append("Optional missing:")
        for k in result["optional_missing"]:
            lines.append(f"  ⚪ {k}")
    if not any(result.values()):
        lines.append("No context schema registered for this skill.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Project context manager for sdeliver skills")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # set
    set_parser = subparsers.add_parser("set", help="Set a context value")
    set_parser.add_argument("key", help="Dot-namespaced key, e.g. business.dau")
    set_parser.add_argument("value", help="JSON-compatible value")
    set_parser.add_argument("--source", default="", help="Command/skill that confirmed this fact")
    set_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing value")
    set_parser.add_argument("--file", default=None, help="Path to PROJECT_CONTEXT.yaml")

    # get
    get_parser = subparsers.add_parser("get", help="Get a context value")
    get_parser.add_argument("key", help="Dot-namespaced key")
    get_parser.add_argument("--file", default=None, help="Path to PROJECT_CONTEXT.yaml")

    # check
    check_parser = subparsers.add_parser("check", help="Check required context for a skill")
    check_parser.add_argument("--skill", required=True, help="Skill name")
    check_parser.add_argument("--file", default=None, help="Path to PROJECT_CONTEXT.yaml")

    # list
    list_parser = subparsers.add_parser("list", help="List all known context facts")
    list_parser.add_argument("--file", default=None, help="Path to PROJECT_CONTEXT.yaml")

    # remove
    remove_parser = subparsers.add_parser("remove", help="Remove a context key")
    remove_parser.add_argument("key", help="Dot-namespaced key")
    remove_parser.add_argument("--file", default=None, help="Path to PROJECT_CONTEXT.yaml")

    args = parser.parse_args()

    context_path = Path(args.file) if args.file else _find_project_root() / DEFAULT_FILENAME

    if args.command == "set":
        value = _parse_value(args.value)
        ok = set_context_value(context_path, args.key, value, source=args.source, overwrite=args.overwrite)
        if not ok:
            print(f"⚠️  Key '{args.key}' already exists. Use --overwrite to replace.")
            sys.exit(1)
        print(f"✅ Set {args.key} = {value}")

    elif args.command == "get":
        value = get_context_value(context_path, args.key)
        if value is None:
            print(f"❌ Key '{args.key}' not found.")
            sys.exit(1)
        print(value)

    elif args.command == "check":
        result = check_skill_context(context_path, args.skill)
        print(_render_check(result))
        if result["missing"]:
            sys.exit(2)

    elif args.command == "list":
        data = _load_context(context_path)
        facts = data.get("facts", {})
        if not facts:
            print("No context facts recorded yet.")
            return
        print(f"PROJECT_CONTEXT ({context_path})")
        for k, v in facts.items():
            print(f"  {k}: {v}")

    elif args.command == "remove":
        data = _load_context(context_path)
        facts = data.get("facts", {})
        if args.key not in facts:
            print(f"❌ Key '{args.key}' not found.")
            sys.exit(1)
        del facts[args.key]
        data.get("_sources", {}).pop(args.key, None)
        _save_context(context_path, data)
        print(f"✅ Removed {args.key}")


if __name__ == "__main__":
    main()
