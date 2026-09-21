# Eval v3 — Real JP Transmission counter holdout

## Freeze

| Item | Value |
|------|--------|
| **SUT SHA** | `932af65d58201a3e2be50fa4ed9262f136ce3598` |
| **Branch** | `vertical/transmission-hard-parts` |
| **Eval v1 / v2** | Regression suites only — do not edit fixtures or retune against them |
| **Resolver / fitment / normalization / confidence / decision policy / JEV authority** | **FROZEN** for the collection window |

`JEV_DECISION_ENABLED` stays **off by default**. Shadow (`JEV_SHADOW_ENABLED`) may stay on for observation only.

## What Eval v3 is

Real-world holdout measurement from **genuine counter requests** as entered by staff.

- **No synthetic cases**
- **No rewrites** of raw query wording before storage
- Target **50–100** real requests; if fewer, report the smaller N honestly
- Do **not** stop early because results look good or bad
- Do **not** tune production mid-window based on individual failures

## Source of truth (no parallel DB)

Every counter inquiry already writes `automation_runs` with:

- `kind = transmission_request_uow`
- `schema = transmission_request_uow.v1`

Human Accept / Correct / Resolve updates the **same row** (`final_accepted_*`, `human_override`, `feedback_action`).

Eval v3 **reads that ledger**. It does not invent a second evaluation store.

Ledger path (pilot root):

```text
{root}/.parrts/automation.db
```

## Privacy

Do not collect customer names, phones, addresses, or payment data.
The evaluation needs the **parts request**, not customer identity.
If a free-text note contains PII, strip it before sharing reports.

## Operator collection checklist

1. Deploy / run counter against SUT `932af65…` (or a build that only adds non-behavior packaging on top of that freeze).
2. Counter staff use `/transmission` as normal.
3. For every request that reaches a human decision, complete feedback:
   - RESOLVED correct → **Accept result**
   - RESOLVED wrong → **Correct result** (enter true SKU)
   - NEEDS_HUMAN → **Resolve request** when the true SKU is known, or leave open if still unknown
4. Do not paste synthetic demo queries into the Eval v3 cohort intentionally.
5. Leave failures recorded; continue.

## Metrics (after window closes)

Computed by:

```bash
PYTHONPATH=src:backend:experiments \
  python experiments/run_transmission_eval_v3_report.py \
  --root /path/to/pilot/root \
  [--since ISO8601] [--until ISO8601]
```

| Metric | Definition |
|--------|------------|
| total requests | uow rows in window |
| RESOLVED / NEEDS_HUMAN | system_outcome counts |
| resolved precision | accepted RESOLVED (no override) / all system RESOLVED with final feedback |
| false-resolution count | system RESOLVED + human correct (override) **or** final_sku ≠ system_sku |
| autonomous accepted coverage | accept-without-override / total |
| escalation rate | system NEEDS_HUMAN / total |
| override rate | human_override=true / total with feedback |
| missed-resolution (heuristic) | system NEEDS_HUMAN + human resolve with a final SKU |
| unresolved-after-human-review | feedback missing and still requires_human / not finalized |

**False RESOLVED** is the highest-severity class.

## Closing the window

1. Stop collection (no more rows enter the cohort, or set `--until`).
2. Run the report script; commit `experiments/transmission_eval_v3_report.md` + `_results.json` only.
3. Group failures **after** close — do not pre-bake category taxonomies.
4. Recommend the smallest next eng change; **do not implement** until review.

## Status right now

Local `.parrts/automation.db` at freeze time had **zero** `transmission_request_uow` rows (only email/import kinds).  
Eval v3 is **collection_open** with **N=0 real requests** until JP counter traffic lands on a frozen pilot root.
