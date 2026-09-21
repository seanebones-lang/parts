# Transmission Counter Evaluation v2

- Freeze commit (cases): `643ce5c6d91164932effd55c3f92ee68997787db`
- SUT: `8fd2e28decb8154f61fde49fdc4df37c2ba9096b`
- Generated: 2026-09-21T16:13:06+00:00
- Cases: 90
- Real JP requests: 0
- Synthetic blind: 90

## Category distribution

- adversarial: 10
- ambiguous: 12
- clean: 15
- counter_language: 15
- fitment_interchange: 10
- identifier: 8
- inventory: 8
- vehicle_family_conflict: 12

## Pass A — deterministic only

| Metric | Value |
|--------|-------|
| Total | 90 |
| RESOLVED | 51 |
| NEEDS_HUMAN | 39 |
| Resolved precision | 1.000 |
| False-resolution count | 0 |
| Missed-resolution count | 1 |
| Correct escalations | 38 |
| Escalation rate | 0.433 |
| Override rate | 0.011 |
| Autonomous accepted coverage | 0.567 |

### False RESOLVED
- none

### Missed resolutions
- **V2-58** [fitment_interchange] `cross over from 6L90 heavy pump to 6L80` → system=NEEDS_HUMAN expected_sku=6L90-PUMP-01

## Pass B — deterministic + live JEV

Not run or empty.

## Comparison to Eval v1 (frozen)

| Metric | Eval v1 A | Eval v2 A |
|--------|-----------|-----------|
| Cases | 20 | 90 |
| Resolved precision | 1.000 | 1.0 |
| False resolutions | 0 | 0 |
| Autonomous coverage | 0.700 | 0.567 |
| Escalation rate | 0.300 | 0.433 |

## Recommendations (do not implement yet)

See final agent report — ranked by severity from this measurement only.
