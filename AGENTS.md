# AGENTS.md

Agent guidance for AI agents working in this repository. This file is the **single source of truth** for how the project is structured and maintained.

## Project Overview

**sdeliver-skills** (`sensorsdata/sd-deliver-skills`) — a marketplace of **7 independent plugins** with 19 skills and 16 commands that bring structured delivery workflows to AI coding assistants for SensorsData CDP/MAE implementations.

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

## Installation

1. Clone the skill repo (or use npm/npx):
   ```bash
   git clone git@github.com:sensorsdata/sd-deliver-skills.git
   cd sd-deliver-skills
   ./setup --host all
   ```

2. Initialize a client project (this creates a project-local Python virtual environment):
   ```bash
   sdeliver init westk ~/projects/westk
   cd ~/projects/westk
   ```

3. Always run scripts through the project virtual environment:
   ```bash
   ./venv/bin/python /path/to/sd-deliver-skills/sd-tracking-pipeline/scripts/generate_mock_data.py \
     --rules ./rules/business_logic.yaml
   ```

   Or use the wrapper (finds `venv/` by walking up from cwd):
   ```bash
   sdeliver-python /path/to/sd-deliver-skills/sd-tracking-pipeline/scripts/generate_mock_data.py \
     --rules ./rules/business_logic.yaml
   ```

**Never** install skill dependencies into the global/system Python interpreter.

## Python Environment Rules

- Each client project owns its own `venv/` created by `sdeliver init`.
- `requirements.txt` at the skill-repo root is the single source of truth for all plugin dependencies.
- Scripts must **not** auto-install packages via `subprocess.check_call([sys.executable, "-m", "pip", "install"])`.
- If a dependency is missing, fail fast and tell the user to run:
  ```bash
  ./venv/bin/pip install -r /path/to/sd-deliver-skills/requirements.txt
  ```
- Running tests on the skill repo itself may use the repo's own venv or the global Python if the test runner is already set up; scripts executed for a delivery project must use the project venv.

## Script Execution Convention

All command documentation and skill examples must use one of these forms:

```bash
# Preferred: project-local venv
./venv/bin/python <skill-repo>/sd-<plugin>/scripts/<script>.py [args]

# Alternative: wrapper that locates the venv
sdeliver-python <skill-repo>/sd-<plugin>/scripts/<script>.py [args]
```

Do **not** use bare `./venv/bin/python <skill-repo>/sd-<plugin>/scripts/xxx.py` in command docs.

## Document Format Contract & Gate

Any file consumed by a script must have a declared, versioned schema and a validator.

| Document type | Schema / Template | Validator |
|---------------|-------------------|-----------|
| Tracking Plan Excel | `sd-tracking-pipeline/references/TRACKING_PLAN_SCHEMA.md` | `validate_tracking_plan.py` |
| business_logic.yaml | `sd-tracking-pipeline/references/BUSINESS_LOGIC_SCHEMA.md` | `yaml_validator.py` |
| SIT Test Case Excel | `sd-tracking-pipeline/references/SIT_TEST_CASE_TEMPLATE.md` | `sd-quality/scripts/validate_test_cases.py --type sit` |
| UAT Test Case Excel | `sd-tracking-pipeline/references/UAT_TEST_CASE_TEMPLATE.md` | `sd-quality/scripts/validate_test_cases.py --type uat` |
| Performance Test Plan | `sd-tracking-pipeline/references/PERFORMANCE_TEST_PLAN_TEMPLATE.md` | `sd-infra/scripts/validate_performance_test_plan.py` |

### Agent rules for parsing documents

1. **Do not write ad-hoc parsers.** If an input file does not match the declared schema, stop and report the validation error.
2. **Run the validator first.** Every command that reads a structured document must start with the relevant `validate_*.py` step.
3. **No silent format adaptation.** Do not adjust column indices, sheet names, or header mappings on the fly to match a new file.
4. **New format versions are skill changes.** If a client provides a file in a new format, record it via `/sd-feedback` and extend the official parser/validator in the skill repo.
5. **Templates are the contract.** Before asking a client for a document, point them to the corresponding template in `sd-*/references/`.

## Project Context Memory

To avoid asking the same questions every session, every command must read from and write to a **project-level context file**.

### Files

| File | Purpose |
|------|---------|
| `PROJECT_CONTEXT.yaml` | Structured, confirmed facts about the project (business scale, environment, SLA, etc.). |
| `CLARIFICATION.md` | Human-readable tracking of open questions and confirmations. |

`PROJECT_CONTEXT.yaml` is the **single source of truth** for confirmed facts. `CLARIFICATION.md` is for narrative and pending items.

### Location

`PROJECT_CONTEXT.yaml` lives at the project root, next to `.env`:

```
~/projects/westk/
├── .env
├── PROJECT.md
├── PROJECT_CONTEXT.yaml
├── CLARIFICATION.md
├── references/
└── ...
```

### Schema

`PROJECT_CONTEXT.yaml` is a flat key/value map grouped by topic. Example:

```yaml
version: "1.0"
last_updated: "2026-06-16T10:00:00Z"
facts:
  business.dau: 1000000
  business.daily_events: 5000000
  business.retention_days: 365
  business.peak_qps: 3000
  infra.cloud: AWS
  infra.region: ap-southeast-1
  infra.include_cdp: true
  infra.include_ma: true
  sla.realtime_import_qps: 1000
  sla.batch_import_records_per_hour: 1000000
  sla.analytics_query_p95_seconds: 5
  sla.email_send_per_minute: 1000
  env.cdp_url: "https://..."
  env.has_pii_encryption: true
```

Key rules:
- Use dot-namespaced keys: `<topic>.<subtopic>.<name>`.
- Values must be JSON-compatible (string, number, boolean, list, dict).
- Every key must have a `source` command/skill recorded in `CLARIFICATION.md`.

### Command workflow

Every command that needs project facts must follow this pattern:

1. **Read context** — Run `project_context.py check --skill <skill-name>` to list known and missing keys.
2. **Use known facts** — Fill in answers from `PROJECT_CONTEXT.yaml` automatically.
3. **Ask only for missing facts** — Ask the user only for keys marked `missing`.
4. **Remember answers** — After the user confirms a fact, run `project_context.py set <key> <value> --source <command-name>`.
5. **Update CLARIFICATION.md** — Mark the item as confirmed.

Example for `/sd-design-performance-test`:

```bash
# 1. Check what is missing
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py check \
  --skill sd-design-performance-test

# 2. Set a confirmed fact
./venv/bin/python <skill-repo>/sd-core/scripts/project_context.py set \
  business.dau 1000000 \
  --source sd-design-performance-test
```

### Skill context schemas

Each skill or command declares its required context keys in its documentation. Example:

```yaml
# sd-design-performance-test required context
required:
  - business.dau
  - business.daily_events
  - business.retention_days
  - infra.cloud
  - infra.region
optional:
  - sla.realtime_import_qps
  - sla.batch_import_records_per_hour
  - env.has_pii_encryption
```

If a required key is missing, the command must ask for it before executing.

### Cross-project knowledge沉淀

Confirmed facts that are likely reusable across projects can be promoted to the delivery knowledge base:

1. Capture the pattern in `/sd-feedback`.
2. Periodically review feedback and add concise entries to `sd-knowledge/skills/delivery-faq/SKILL.md`.
3. Link back to the source project only if needed.

### Agent rules

1. **Never guess project facts.** If a fact is not in `PROJECT_CONTEXT.yaml`, treat it as unknown.
2. **Prefer reading context over asking.** Always check context before asking the user.
3. **Write back immediately.** After receiving an answer, update `PROJECT_CONTEXT.yaml` in the same turn.
4. **Keep keys stable.** Do not rename keys lightly; skills depend on them.
5. **Sensitive values.** Do not store API keys, passwords, or tokens in `PROJECT_CONTEXT.yaml`; keep those in `.env`.

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

## 脚本开发规范（TDD）

All executable scripts under `sd-*/scripts/` must be developed test-first.

### Test layout

- One test file per script: `sd-<plugin>/tests/test_<module>.py` mirrors `sd-<plugin>/scripts/<module>.py`.
- All CDP, OpenAPI, network and filesystem I/O must be mocked; use `tmp_path` / `temp_dir` for files.
- Mark tests with `@pytest.mark.unit`, `@pytest.mark.integration` or `@pytest.mark.slow`.

### TDD checklist

1. Write the failing test before implementing the script/function.
2. Every public function has at least one test.
3. Every error-handling branch has a `pytest.raises` test.
4. Coverage threshold: **80%** line coverage per script.
5. Run before committing:
   ```bash
   make test-plugin PLUGIN=sd-<plugin>   # plugin-level
   make test                             # all non-integration tests
   make validate                         # structure + test coverage
   ```
6. `python3 validate_plugins.py --check-tests` treats a missing test file as an **error**.

### Test commands

```bash
make test                  # run all unit tests
make test-plugin PLUGIN=sd-tracking-pipeline
make validate              # validate_plugins.py --check-tests
make cov                   # coverage report
```

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
