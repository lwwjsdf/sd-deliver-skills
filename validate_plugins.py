#!/usr/bin/env python3
"""sd-deliver-skills plugin validator.

Checks:
  - plugin.json: required fields, name match, semver
  - skill SKILL.md: frontmatter name + description, name matches directory
  - command .md: frontmatter description + argument-hint
  - Required directories exist
  - (with --check-tests) every script has a corresponding test file

Usage:
  python3 validate_plugins.py
  python3 validate_plugins.py --check-tests
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set

REPO = Path(__file__).resolve().parent

PLUGINS = [
    "sd-core",
    "sd-tracking-design",
    "sd-tracking-pipeline",
    "sd-infra",
    "sd-quality",
    "sd-docs",
    "sd-knowledge",
]

errors: List[str] = []
warnings: List[str] = []
total_skills = 0
active_skills = 0
draft_skills = 0
deprecated_skills = 0
total_commands = 0
active_commands = 0
draft_commands = 0
deprecated_commands = 0
total_scripts = 0
scripts_with_tests = 0
scripts_without_tests: List[str] = []


def err(msg: str):
    errors.append(msg)


def warn(msg: str):
    warnings.append(msg)


def parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a markdown file."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    frontmatter = {}
    for line in parts[1].strip().split("\n"):
        m = re.match(r"^(\w[\w-]*)\s*:\s*(.*)", line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            # Handle multiline values (starting with |)
            frontmatter[key] = value
    return frontmatter


def validate_semver(version: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+$", version))


def validate_plugin(plugin_name: str):
    global total_skills, active_skills, draft_skills, deprecated_skills
    global total_commands, active_commands, draft_commands, deprecated_commands
    plugin_dir = REPO / plugin_name
    if not plugin_dir.is_dir():
        err(f"[{plugin_name}] Plugin directory not found: {plugin_name}/")
        return

    # plugin.json
    pjson = plugin_dir / "plugin.json"
    if not pjson.is_file():
        err(f"[{plugin_name}] Missing plugin.json")
    else:
        try:
            data = json.loads(pjson.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            err(f"[{plugin_name}] plugin.json parse error: {e}")
            data = {}

        for field in ["name", "version", "description"]:
            if field not in data:
                err(f"[{plugin_name}] plugin.json missing field: {field}")

        if data.get("name") != plugin_name:
            err(
                f"[{plugin_name}] plugin.json name '{data.get('name')}' "
                f"doesn't match directory name '{plugin_name}'"
            )

        version = data.get("version", "")
        if version and not validate_semver(version):
            err(f"[{plugin_name}] plugin.json version '{version}' is not semver")

    # skills/
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        warn(f"[{plugin_name}] No skills/ directory")
    else:
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                err(f"[{plugin_name}] Skill '{skill_name}' missing SKILL.md")
                continue

            fm = parse_frontmatter(skill_file)
            if "name" not in fm:
                err(f"[{plugin_name}] Skill '{skill_name}' frontmatter missing 'name'")
            elif fm["name"] != skill_name:
                err(
                    f"[{plugin_name}] Skill '{skill_name}' frontmatter name "
                    f"'{fm['name']}' doesn't match directory name"
                )
            if "description" not in fm:
                err(f"[{plugin_name}] Skill '{skill_name}' frontmatter missing 'description'")

            # Status
            total_skills += 1
            status = fm.get("status", "active")
            if status == "draft":
                draft_skills += 1
            elif status == "deprecated":
                deprecated_skills += 1
            elif status == "active":
                active_skills += 1
            else:
                warn(f"[{plugin_name}] Skill '{skill_name}' has unknown status '{status}' (expected: active, draft, deprecated)")
                active_skills += 1  # Treat unknown as active

    # commands/
    commands_dir = plugin_dir / "commands"
    if not commands_dir.is_dir():
        warn(f"[{plugin_name}] No commands/ directory")
    else:
        for cmd_file in sorted(commands_dir.iterdir()):
            if not cmd_file.name.endswith(".md"):
                continue
            fm = parse_frontmatter(cmd_file)
            if "description" not in fm:
                err(f"[{plugin_name}] Command '{cmd_file.name}' frontmatter missing 'description'")

            # Status
            total_commands += 1
            status = fm.get("status", "active")
            if status == "draft":
                draft_commands += 1
            elif status == "deprecated":
                deprecated_commands += 1
            elif status == "active":
                active_commands += 1
            else:
                warn(f"[{plugin_name}] Command '{cmd_file.name}' has unknown status '{status}' (expected: active, draft, deprecated)")
                active_commands += 1  # Treat unknown as active

    # scripts/ (optional)
    scripts_dir = plugin_dir / "scripts"
    if scripts_dir.is_dir():
        # Check for __pycache__ only warning
        pycache = scripts_dir / "__pycache__"
        if pycache.is_dir():
            pass  # acceptable


def _expected_test_patterns(script_rel_path: Path) -> List[str]:
    """Return candidate test file name patterns for a script.

    scripts/foo.py              -> test_foo.py, test_foo_*.py
    scripts/bar/foo.py          -> test_bar_foo.py, test_bar_foo_*.py
                                  or test_bar/test_foo.py, test_bar/test_foo_*.py
    """
    parts = script_rel_path.with_suffix("").parts
    dotted = "_".join(parts)
    flat_patterns = [f"test_{dotted}.py", f"test_{dotted}_*.py"]
    if len(parts) > 1:
        subdir = parts[0]
        module = parts[-1]
        nested_patterns = [
            f"{subdir}/test_{module}.py",
            f"{subdir}/test_{module}_*.py",
        ]
        return flat_patterns + nested_patterns
    return flat_patterns


def _has_matching_test(tests_dir: Path, patterns: List[str]) -> bool:
    """Check whether any file under tests_dir matches the given glob patterns."""
    for pattern in patterns:
        if list(tests_dir.glob(pattern)):
            return True
    return False


def validate_tests():
    """Verify every script under sd-*/scripts/ has a corresponding test file."""
    global total_scripts, scripts_with_tests
    for plugin_name in PLUGINS:
        plugin_dir = REPO / plugin_name
        scripts_dir = plugin_dir / "scripts"
        tests_dir = plugin_dir / "tests"
        if not scripts_dir.is_dir():
            continue
        for script in sorted(scripts_dir.rglob("*.py")):
            if script.name == "__init__.py":
                continue
            if "__pycache__" in script.parts:
                continue
            total_scripts += 1
            rel = script.relative_to(scripts_dir)
            patterns = _expected_test_patterns(rel)
            if tests_dir.is_dir() and _has_matching_test(tests_dir, patterns):
                scripts_with_tests += 1
            else:
                scripts_without_tests.append(f"{plugin_name}/scripts/{rel}")
                err(
                    f"[{plugin_name}] Missing test for script '{rel}' "
                    f"(expected one of: {', '.join(patterns)})"
                )


def validate_pytest_collection():
    """Run pytest --collect-only to catch import/syntax errors in tests."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        err("pytest not found; cannot validate test collection")
        return
    if result.returncode != 0:
        err("pytest --collect-only failed; tests have import or syntax errors")
        # Surface the tail of pytest output so the user can debug.
        tail = "\n".join(result.stderr.splitlines()[-20:] or result.stdout.splitlines()[-20:])
        for line in tail.splitlines():
            err(f"  {line}")


def validate_references():
    """Validate global references/ directory exists."""
    refs = REPO / "references"
    refs_legacy = REPO / "refrences"
    if not refs.is_dir() and not refs_legacy.is_dir():
        warn("No references/ directory")


def main():
    parser = argparse.ArgumentParser(description="Validate sd-deliver-skills plugins")
    parser.add_argument(
        "--check-tests",
        action="store_true",
        help="Also verify every script has a corresponding test file",
    )
    args = parser.parse_args()

    for plugin in PLUGINS:
        validate_plugin(plugin)

    validate_references()

    if args.check_tests:
        validate_tests()
        validate_pytest_collection()

    print(f"\n{'='*50}")
    print(f"sd-deliver-skills validator")
    print(f"{'='*50}\n")

    # Summary
    print(f"\n{'='*50}")
    print(f"Summary")
    print(f"{'='*50}")
    print(f"  Skills:       {total_skills} (active: {active_skills}, draft: {draft_skills}, deprecated: {deprecated_skills})")
    print(f"  Commands:     {total_commands} (active: {active_commands}, draft: {draft_commands}, deprecated: {deprecated_commands})")
    if args.check_tests:
        print(f"  Scripts:      {total_scripts} (with tests: {scripts_with_tests}, missing: {len(scripts_without_tests)})")

    if not errors and not warnings:
        print("\n✅ All plugins passed!")
        return 0

    if errors:
        print(f"\n❌ {len(errors)} error(s):")
        for e in errors:
            print(f"   {e}")

    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"   {w}")

    if errors:
        print("\n❌ Validation FAILED")
        return 1
    else:
        print("\n⚠️  Passed with warnings")
        return 0


if __name__ == "__main__":
    sys.exit(main())
