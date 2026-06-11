#!/usr/bin/env python3
"""Merge command entries from a JSON file into opencode.jsonc.

Usage:
  python3 merge_commands.py <commands.json> <opencode.jsonc>
"""
import json
import re
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: merge_commands.py <commands.json> <opencode.jsonc>", file=sys.stderr)
        sys.exit(1)

    cmd_file = sys.argv[1]
    config_file = sys.argv[2]

    with open(cmd_file) as f:
        commands = json.load(f)

    with open(config_file) as f:
        content = f.read()

    # Strip comments and trailing commas for JSON parsing
    clean = re.sub(r'//.*', '', content)
    clean = re.sub(r',\s*}', '}', clean)
    clean = re.sub(r',\s*]', ']', clean)
    try:
        config = json.loads(clean)
    except json.JSONDecodeError:
        # If parsing fails, start fresh but preserve $schema
        config = {}
        schema_match = re.search(r'"\$schema"\s*:\s*"([^"]+)"', content)
        if schema_match:
            config['$schema'] = schema_match.group(1)

    if 'command' not in config:
        config['command'] = {}
    for name, cmd in commands.items():
        config['command'][name] = cmd

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"  Registered {len(commands)} commands in opencode.jsonc")


if __name__ == "__main__":
    main()
