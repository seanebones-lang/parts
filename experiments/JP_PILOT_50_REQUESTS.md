# JP Pilot — 50 real counter requests (operating procedure)

**Purpose:** Run ~50 real JP Transmission counter requests through PARTS without changing JP’s existing counter workflow.

This is **not** Eval v3 data and **not** a synthetic eval set.

| Dataset | Role |
|---------|------|
| Synthetic demo inventory (`data/jp_demo/`) | Pilot UI / training stock — **not** live JP qty |
| Eval v1 / v2 / v2b | Engineering regression / synthetic pressure |
| **This procedure** | How staff collect **real** requests |
| Eval v3 | Future report over real `transmission_request_uow` rows only |

## Rules

1. Do **not** invent requests. Only record what a real counter customer asked.
2. Strip unnecessary customer PII (names, phones, emails, plate numbers). Keep the **parts request text**.
3. Do not treat demo inventory quantities as JP’s live stock when talking to the customer.
4. For every request, record exactly one of:
   - **ACCEPT** — system match is correct as-is
   - **CORRECT** — system proposed a SKU but human changed it
   - **RESOLVE / NEEDS REVIEW** — system escalated or human finished an incomplete match
5. Prefer the existing UI feedback controls on Parts Search (Accept match / Correct match / Resolve request) so the unit-of-work ledger stays the source of truth.

## Per-request capture fields

| Field | Notes |
|-------|--------|
| Date | ISO or local date |
| Original inquiry text | Raw counter wording |
| System outcome | RESOLVED / NEEDS_HUMAN |
| Proposed SKU | System SKU or blank |
| Final accepted SKU | After human action |
| Human action | ACCEPT / CORRECT / RESOLVE |
| Short note | Optional; no PII |

Optional paper/CSV log if ledger is unavailable — still no invented rows.

## Target

50 finalized real requests. If fewer exist, report N honestly and keep collecting.

## After collection

Use Eval v3 tooling against the pilot root ledger (`experiments/EVAL_V3_PROTOCOL.md`, `run_transmission_eval_v3_report.py`). Do not mix synthetic inventory marketing with Eval v3 precision claims.
