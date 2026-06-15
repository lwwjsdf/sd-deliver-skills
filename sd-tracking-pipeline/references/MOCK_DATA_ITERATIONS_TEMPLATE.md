# Mock Data Iterations

This template records every round of mock-data generation for a delivery project.
Copy it to the project root as `MOCK_DATA_ITERATIONS.md` and append one section per iteration.

## Iteration v1 (YYYY-MM-DD)

### Goal
What this round of mock data is intended to validate or demonstrate.

### Configuration

| Item | Value |
|------|-------|
| Users | e.g. 100 |
| Days | e.g. 30 |
| Sessions per day | e.g. 5 |
| Platforms | e.g. MP, Web |
| Rules file | `rules/business_logic.yaml` |
| Tracking Plan | `references/<tracking-plan>.xlsx` |
| Generator version / rule version | e.g. v1 |

### Feedback Addressed
List the client or QA feedback that triggered this iteration.

- e.g. Membership expiration dates should include both expired and active users.
- e.g. `Product_Payment_Detail` should be derived from `Product_Order_Payment`.

### Changes
Describe the rule / script / schema changes made in this iteration.

- e.g. Added `date_relative_to_today` distribution for membership expiration.
- e.g. Removed standalone `Product_Payment_Detail` event; added `derive` config with source mapping and `{timestamp}` prefix for `ticketID`.

### Validation Results

| Check | Pass | Total | Notes |
|-------|------|-------|-------|
| Field-level checks | 22 | 22 | |
| Cross-event checks | 11 | 11 | |
| Constraint violations | 0 | 0 | |

### Output Files

| File | Description |
|------|-------------|
| `mock_data/<prefix>_v1.jsonl` | Full import-ready event data |
| `mock_data/<prefix>_v1_sample.json` | First 100 records for human review |
| `mock_data/<prefix>_v1_identity_map.csv` | ID-mapping reference |
| `mock_data/<prefix>_v1_validation_report.md` | Constraint / quality report |

---

## Iteration v2 (YYYY-MM-DD)

(Add subsequent iterations below.)
