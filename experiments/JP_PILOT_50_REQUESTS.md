# JP Pilot — 50 real counter requests (operating procedure)

**Purpose:** Run ~50 real JP Transmission counter requests through PARTS without changing JP’s existing counter workflow.

This is **not** Eval v3 data and **not** a synthetic eval set.

| Dataset | Role |
|---------|------|
| Synthetic demo inventory (`data/jp_demo/`) | Pilot UI / training stock — **not** live JP qty |
| Eval v1 / v2 / v2b | Engineering regression / synthetic pressure |
| **This procedure** | How staff collect **real** requests |
| Eval v3 | Future report over real `transmission_request_uow` rows only |

## Three search result modes (counter)

| Mode | Meaning | Pilot action |
|------|---------|--------------|
| **EXACT MATCH** | One safe SKU/identifier identity | Accept / Correct on the proposed SKU |
| **INVENTORY MATCHES** | Product class clear; multiple sellable lots | Operator **selects a physical lot**, then quote/reserve. **Not** an autonomous exact resolve |
| **NEEDS REVIEW** | Genuine uncertainty/safety | Resolve with final SKU, or note why unresolvable |

Do **not** score INVENTORY MATCHES as “false resolution” or as autonomous exact-match success.

Separate pilot metrics (collect when possible; do not fabricate):

- Exact resolver correctness
- Discovery usefulness (did lots match the ask?)
- Human correction rate (exact path)
- Search-to-quote success
- Needs-review rate

## Rules

1. Do **not** invent requests. Only record what a real counter customer asked.
2. Strip unnecessary customer PII (names, phones, emails, plate numbers). Keep the **parts request text**.
3. Do not treat demo inventory quantities as JP’s live stock when talking to the customer.
4. For every request, record the **search mode** plus one of:
   - **ACCEPT** — exact match correct as-is
   - **CORRECT** — exact match SKU changed by human
   - **RESOLVE / NEEDS REVIEW** — safety path finalized or left open
   - **LOT SELECTED** — inventory-matches path; note chosen SKU/location
5. Prefer the existing UI feedback controls on Parts Search for exact/needs-review so the unit-of-work ledger stays the source of truth. Lot selection is operational (quote/reserve), not UoW ACCEPT.

## Per-request capture fields

| Field | Notes |
|-------|--------|
| Date | ISO or local date |
| Original inquiry text | Raw counter wording |
| Search mode | exact_match / inventory_matches / needs_review |
| System outcome | RESOLVED / NEEDS_HUMAN / (blank if browse) |
| Proposed SKU | System SKU or blank |
| Selected lot SKU | If inventory_matches |
| Final accepted SKU | After human action |
| Human action | ACCEPT / CORRECT / RESOLVE / LOT_SELECTED |
| Short note | Optional; no PII |

Optional paper/CSV log if ledger is unavailable — still no invented rows.

## Target

50 finalized real requests. If fewer exist, report N honestly and keep collecting.

## After collection

Use Eval v3 tooling against the pilot root ledger (`experiments/EVAL_V3_PROTOCOL.md`, `run_transmission_eval_v3_report.py`). Do not mix synthetic inventory marketing with Eval v3 precision claims. Keep **resolver accuracy** separate from **discovery usefulness**.
