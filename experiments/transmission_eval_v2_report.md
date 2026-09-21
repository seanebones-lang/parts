# Transmission Counter Evaluation v2

- Freeze commit (cases): `643ce5c6d91164932effd55c3f92ee68997787db`
- SUT: `8fd2e28decb8154f61fde49fdc4df37c2ba9096b`
- Generated: 2026-09-21T03:50:47+00:00
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
| RESOLVED | 59 |
| NEEDS_HUMAN | 31 |
| Resolved precision | 0.864 |
| False-resolution count | 8 |
| Missed-resolution count | 0 |
| Correct escalations | 31 |
| Escalation rate | 0.344 |
| Override rate | 0.089 |
| Autonomous accepted coverage | 0.567 |

### False RESOLVED
- **V2-52** [ambiguous] `pump or valve body for 6L80 — not sure which` → system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None
- **V2-58** [fitment_interchange] `cross over from 6L90 heavy pump to 6L80` → system=RESOLVED/6L80-PUMP-01 expected=RESOLVED/6L90-PUMP-01
- **V2-59** [fitment_interchange] `is 6R80 pump same as 6L80 pump?` → system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None
- **V2-62** [fitment_interchange] `can I use 6L90 pump instead of 6L80?` → system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None
- **V2-81** [adversarial] `6L80 pump that is also a 6R80 valve body right now` → system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None
- **V2-84** [adversarial] `CVT pump for Prius 6L80` → system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None
- **V2-87** [adversarial] `6L80 6L90 6R80 pump which one` → system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None
- **V2-90** [adversarial] `6L80 pump AND 6L80 valve body both now` → system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None

### Missed resolutions
- none

## Pass B — deterministic + live JEV

| Metric | Pass A | Pass B |
|--------|--------|--------|
| Resolved precision | 0.864406779661017 | 0.8771929824561403 |
| False resolutions | 8 | 7 |
| Missed resolutions | 0 | 2 |
| Escalation rate | 0.344 | 0.367 |
| Autonomous coverage | 0.567 | 0.556 |
| JEV escalations | — | 5 |

### A → B flips (2)
- **V2-28**: RESOLVED/6R80-PUMP-01 → NEEDS_HUMAN/6R80-PUMP-01 (jev_nh=True, label=parts_availability)
- **V2-58**: RESOLVED/6L80-PUMP-01 → NEEDS_HUMAN/6L80-PUMP-01 (jev_nh=True, label=compatibility_fitment)

JEV consulted: 90/90
JEV labels: {'parts_availability': 51, 'general_question': 8, 'spam_or_irrelevant': 9, 'compatibility_fitment': 22}
JEV escalation IDs: ['V2-28', 'V2-36', 'V2-42', 'V2-58', 'V2-86']

## Comparison to Eval v1 (frozen)

| Metric | Eval v1 A | Eval v2 A |
|--------|-----------|-----------|
| Cases | 20 | 90 |
| Resolved precision | 1.000 | 0.864406779661017 |
| False resolutions | 0 | 8 |
| Autonomous coverage | 0.700 | 0.567 |
| Escalation rate | 0.300 | 0.344 |

## Recommendations (do not implement yet)

See final agent report — ranked by severity from this measurement only.
