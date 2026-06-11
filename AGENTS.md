# AGENTS.md

Agent guidance for AI agents working in this repository. This file is the **single source of truth** for how the project is structured and maintained.

## Project Overview

**sdeliver-skills** (`sensorsdata/sd-deliver-skills`) — a marketplace of **7 independent plugins** with 17 skills and 13 commands that bring structured delivery workflows to AI coding assistants for SensorsData CDP/MAE implementations.

Built for Hermes, OpenCode, Cursor, and Claude Code.

## Repo Structure

```
sd-deliver-skills/
├── AGENTS.md                        <- this file (agent guidance, single source of truth)
├── CLAUDE.md                        <- pointer to AGENTS.md (Claude compatibility)
├── validate_plugins.py              <- plugin validator
├── README.md                        <- public documentation (GitHub)
├── setup                            <- install script (registers all plugins)
├── shared/                          <- cross-plugin shared modules (cdp_client, md2docx, etc.)
├── references/                      <- global reference templates (Excel, drawio, docx)
├── bin/                             <- CLI tools (legacy, being migrated to sd-core/scripts/)
│
├── sd-core/                         <- Plugin: delivery core framework
│   ├── plugin.json
│   ├── skills/{skill}/SKILL.md      <- one folder per skill
│   ├── commands/{cmd}.md            <- one file per command
│   └── scripts/                     <- CLI tools
│
├── sd-tracking-design/              <- Plugin: tracking plan design
│   ├── plugin.json
│   ├── skills/{skill}/SKILL.md
│   ├── commands/{cmd}.md
│   └── scripts/
│
├── sd-tracking-pipeline/            <- Plugin: data pipeline execution
│   ├── plugin.json
│   ├── skills/{skill}/SKILL.md
│   ├── commands/{cmd}.md
│   └── scripts/
│
├── sd-infra/                        <- Plugin: infrastructure & tech design
│   ├── plugin.json
│   ├── skills/{skill}/SKILL.md
│   ├── commands/{cmd}.md
│   └── scripts/
│
├── sd-quality/                      <- Plugin: quality assurance
│   ├── plugin.json
│   ├── skills/{skill}/SKILL.md
│   ├── commands/{cmd}.md
│   └── scripts/
│
├── sd-docs/                         <- Plugin: delivery documents
│   ├── plugin.json
│   ├── skills/{skill}/SKILL.md
│   ├── commands/{cmd}.md
│   └── scripts/
│
└── sd-knowledge/                    <- Plugin: delivery knowledge base
    ├── plugin.json
    ├── skills/{skill}/SKILL.md
    └── commands/{cmd}.md
```

## The 7 Plugins

| Plugin | Focus |
|--------|-------|
| `sd-core` | Project onboarding, status awareness, skill dispatch, auto-feedback |
| `sd-tracking-design` | Tracking plan design: business scoping → event/attribute definition → Excel output |
| `sd-tracking-pipeline` | Data pipeline: YAML generation → validation → mock data → metadata import → data import → verification |
| `sd-infra` | Server sizing, tech design (LLD), architecture diagrams, performance testing |
| `sd-quality` | SIT testing, UAT testing, data validation |
| `sd-docs` | Business document formatting (Word/PDF generation) |
| `sd-knowledge` | Delivery FAQ: capacity estimation, Xinchuang, ID3, troubleshooting SOP |

## Key Design Rules

- **Skills = nouns/concepts.** Frameworks and knowledge that AI auto-loads when the topic matches (`tracking-plan-design`, `server-sizing`, `data-pipeline`).
- **Commands = verbs.** User-triggered workflows that chain one or more skills. Invoked via `/command-name`.
- **No cross-plugin hard references.** Commands suggest follow-ups in natural language only. Never hard-reference a command or skill from another plugin.
- **Intra-plugin references are fine** — skills and commands in the same plugin always ship together.
- Skills need `name` + `description` in frontmatter. Commands need `description` + `argument-hint`.
- A skill's **name must match its directory name**.
- Keep frontmatter lean (always loaded); put detail in the SKILL.md body (loaded when triggered) — progressive disclosure.

## What's Visible Where

| Location | Visible in | Notes |
|----------|-----------|-------|
| `plugin.json` → `description` | Agent skill list (Hermes, OpenCode, etc.) | Per-plugin summary |
| `SKILL.md` frontmatter → `description` | Agent auto-loading trigger | Include trigger phrases so the agent loads the skill at the right time |
| Command frontmatter → `description` + `argument-hint` | Agent interface (typing `/`) | Short and actionable |
| `README.md` | GitHub only | Full documentation |

## Validation

Run `python3 validate_plugins.py` from the repo root to check all plugins:

```
python3 validate_plugins.py
```

Validates: `plugin.json` required fields / name match / semver; skill frontmatter and name-matches-directory; command frontmatter; all required directories exist.

## Operational Procedures

### After adding/removing skills or commands
1. Run `python3 validate_plugins.py`
2. Update the counts in `README.md` (Plugin 清单 section)
3. Bump the version in `plugin.json` for the affected plugin

### After a description change
- A `plugin.json` description changed → check whether `README.md` needs the same edit
- A `SKILL.md` description changed → no other sync needed (it's the single source for that skill)

## What to Suggest After Completing Work

- After structural changes: "Want me to run the validator?"
- After adding/removing skills or commands: "Should I update the counts in README.md?"
- After editing descriptions: "Should I sync this to `README.md` / `plugin.json`?"
