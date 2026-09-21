# Transmission Eval v2b — Synthetic Pressure Test (internal)

- Generated: `2026-09-21T16:22:58+00:00`
- Corpus freeze SHA: `86f1e581a7b7e31f82d0025c3deaa72a19e9795e`
- SUT: `932af65d58201a3e2be50fa4ed9262f136ce3598`
- RNG seed: `20260921`
- Cases: **1000** (synthetic; not live JP traffic)

## Metrics (deterministic only, JEV off)

| Metric | Value |
|--------|-------|
| Expected RESOLVED | 681 |
| Expected NEEDS_HUMAN | 319 |
| Actual RESOLVED | 691 |
| Actual NEEDS_HUMAN | 309 |
| Resolved precision | 0.9855282199710564 |
| False-resolution count | 10 |
| False-resolution rate | 0.0100 |
| Autonomous accepted coverage | 0.681 |
| Escalation rate | 0.309 |
| Correct escalation count | 309 |
| Correct escalation rate (vs expected NH) | 0.9686520376175548 |
| Unnecessary escalation / missed-resolution | 0 |
| Override-equivalent rate | 0.010 |

## Verdict counts

```json
{
  "accept": 681,
  "correct_escalation": 309,
  "false_resolution": 10
}
```

## Cohort verdicts

```json
{
  "A": {
    "accept": 391
  },
  "B": {
    "accept": 290
  },
  "C": {
    "correct_escalation": 309,
    "false_resolution": 10
  }
}
```

## FALSE RESOLVED (complete list)

- **V2B-0342** [C/adversarial_nonsense] query=`asdf qwer 8HP70 blah pump zxcv` system=RESOLVED/8HP70-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0481** [C/adversarial_nonsense] query=`lorem ipsum 6R80 dolor pump sit` system=RESOLVED/6R80-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0560** [C/adversarial_nonsense] query=`lorem ipsum 6L80 dolor pump sit` system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0593** [C/adversarial_nonsense] query=`asdf qwer 6L90 blah pump zxcv` system=RESOLVED/6L90-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0670** [C/adversarial_nonsense] query=`lorem ipsum 4L60E dolor pump sit` system=RESOLVED/4L60E-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0827** [C/adversarial_nonsense] query=`asdf qwer 6R80 blah pump zxcv` system=RESOLVED/6R80-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0837** [C/adversarial_nonsense] query=`lorem ipsum 6L90 dolor pump sit` system=RESOLVED/6L90-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0839** [C/adversarial_nonsense] query=`asdf qwer 4L60E blah pump zxcv` system=RESOLVED/4L60E-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0846** [C/adversarial_nonsense] query=`asdf qwer 6L80 blah pump zxcv` system=RESOLVED/6L80-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`
- **V2B-0882** [C/adversarial_nonsense] query=`lorem ipsum 8HP70 dolor pump sit` system=RESOLVED/8HP70-PUMP-01 expected=NEEDS_HUMAN/None amb=`None`

## Missed resolutions (sample up to 40)

- none

## Failure groups (post-hoc)

```json
{
  "by_verdict_category": {
    "false_resolution|adversarial_nonsense": 10
  },
  "by_mutation": {},
  "by_adversarial": {
    "nonsense": 10
  }
}
```

## Recommendations (do not implement in this task)

See agent final report.
