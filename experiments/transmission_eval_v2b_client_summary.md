# JP Transmission — Synthetic Engineering Pressure Test (Eval v2b)

> **Synthetic engineering pressure test — not yet a measurement of live JP Transmission counter traffic.**
>
> These results measure how a frozen parts-resolution engine behaves on a large, deliberately constructed set of shop-style and adversarial queries derived from pilot catalog data. They are **not** real-world accuracy on JP counter history.

- Cases: **1000** synthetic requests
- Generator seed: `20260921`
- Corpus freeze: `86f1e581a7b7e31f82d0025c3deaa72a19e9795e`
- Engine build under test: `932af65d58201a3e2be50fa4ed9262f136ce3598`
- Source data: pilot transmission catalog (11 hard-parts SKUs), identifiers, fitments, inventory phrasing

## What was tested

- Valid lookups (family + part, SKU, OEM/casting identifiers, vehicle + family when fitment exists)
- Counter-language variation (case, urgency, plurals, known abbreviations like VB/pmp)
- Deliberately bad inputs: multi-part requests, substitution language, vehicle/family conflicts, unsupported vehicle+family, unknown IDs, nonsense

## Headline metrics

| Metric | Result |
|--------|--------|
| Resolved precision (of system RESOLVED) | **98.6%** |
| False-resolution rate (of all cases) | **1.00%** (10 cases) |
| Autonomous accepted coverage | **68.1%** |
| Escalation rate (NEEDS_HUMAN) | **30.9%** |

## Representative successes

- `Do you have a pump for a 2012 F-150 6R80? please thanks` → **6R80-PUMP-01**
- `Do you have a pumps for a 2011 Tahoe 6L80?` → **6L80-PUMP-01**
- `need a pump for 6R80` → **6R80-PUMP-01**
- `8HP70 valve body in stock? please thanks` → **8HP70-VB-01**
- `6R80 pump please` → **6R80-PUMP-01**
- `pump for a 2000 Silverado 4L60E?` → **4L60E-PUMP-01**
- `identifier 6R80-P-01` → **6R80-PUMP-01**
- `Do you have a drum for 4L80E?` → **4L80E-DRUM-01**

## Representative safe refusals

- `10R80 8HP70 pump which one` → **NEEDS HUMAN REVIEW** (multiple transmission families with an explicit which-one choice)
- `4L60E valve body for a Prius` → **NEEDS HUMAN REVIEW** (vehicle/transmission fitment could not be verified: vehicle=Prius has no canonical fitment rows for stated family=4L60E)
- `4L80E drum for a 2011 Tahoe` → **NEEDS HUMAN REVIEW** (conflicting vehicle and transmission-family evidence: stated=4L80E vehicle=Tahoe implies=6L80)
- `6R80 8HP70 10R80 pump which one` → **NEEDS HUMAN REVIEW** (multiple transmission families with an explicit which-one choice)
- `can I use 8HP70 pump instead of 6L90?` → **NEEDS HUMAN REVIEW** (substitution request across transmission families)
- `8HP70 valve body for a Prius` → **NEEDS HUMAN REVIEW** (vehicle/transmission fitment could not be verified: vehicle=Prius has no canonical fitment rows for stated family=8HP70)
- `10R80 pump for a Prius` → **NEEDS HUMAN REVIEW** (vehicle/transmission fitment could not be verified: vehicle=Prius has no canonical fitment rows for stated family=10R80)
- `4L80E or 6L80 pump?` → **NEEDS HUMAN REVIEW** (disjunctive transmission-family choice)

## Discovered false resolutions

The system returned a confident part where the test expected human review or a different part:
- `asdf qwer 8HP70 blah pump zxcv` → system `8HP70-PUMP-01` (expected NEEDS_HUMAN/None)
- `lorem ipsum 6R80 dolor pump sit` → system `6R80-PUMP-01` (expected NEEDS_HUMAN/None)
- `lorem ipsum 6L80 dolor pump sit` → system `6L80-PUMP-01` (expected NEEDS_HUMAN/None)
- `asdf qwer 6L90 blah pump zxcv` → system `6L90-PUMP-01` (expected NEEDS_HUMAN/None)
- `lorem ipsum 4L60E dolor pump sit` → system `4L60E-PUMP-01` (expected NEEDS_HUMAN/None)
- `asdf qwer 6R80 blah pump zxcv` → system `6R80-PUMP-01` (expected NEEDS_HUMAN/None)
- `lorem ipsum 6L90 dolor pump sit` → system `6L90-PUMP-01` (expected NEEDS_HUMAN/None)
- `asdf qwer 4L60E blah pump zxcv` → system `4L60E-PUMP-01` (expected NEEDS_HUMAN/None)
- `asdf qwer 6L80 blah pump zxcv` → system `6L80-PUMP-01` (expected NEEDS_HUMAN/None)
- `lorem ipsum 8HP70 dolor pump sit` → system `8HP70-PUMP-01` (expected NEEDS_HUMAN/None)

## Important framing for JP

This pressure test increases confidence that the engine **refuses many unsafe patterns** and **resolves clean catalog-backed requests** at scale. **Live JP counter traffic (Eval v3)** remains the real-world measurement and is separate.
