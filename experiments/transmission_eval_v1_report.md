# Transmission Counter Evaluation v1

- Baseline commit: `39797b6f9366de9b2fecd86013c895238e9deccf`
- Generated: 2026-09-21T03:25:30+00:00
- Cases: 20
- System frozen: no resolver/policy changes during run

## Pass A — deterministic policy only

| Metric | Value |
|--------|-------|
| Total requests | 20 |
| RESOLVED | 14 |
| NEEDS_HUMAN | 6 |
| Resolved precision | 1.000 |
| Human escalation rate | 0.300 |
| Override rate | 0.050 |
| False-resolution count | 0 |
| Autonomous accepted coverage | 0.700 |

## Per-query results (Pass A)

| ID | Query | System | SKU | Conf | Human | Final SKU | Notes |
|----|-------|--------|-----|------|-------|-----------|-------|
| E01 | Do you have a pump for a 2011 Tahoe 6L80? | RESOLVED/resolved | 6L80-PUMP-01 | 0.9 | accept | 6L80-PUMP-01 | Clean vehicle + family + part type |
| E02 | 6L80 VB in stock? | RESOLVED/resolved | 6L80-VB-01 | 0.9 | accept | 6L80-VB-01 | Abbreviation VB = valve body |
| E03 | need a 6l80 valv body rebuilt | RESOLVED/resolved | 6L80-VB-01 | 0.9 | accept | 6L80-VB-01 | Misspelling valv/body |
| E04 | Do you have 24264418? | RESOLVED/resolved | 6L80-PUMP-01 | 0.9 | accept | 6L80-PUMP-01 | Casting/OEM identifier hit |
| E05 | looking for oem 24264419 | RESOLVED/resolved | 6L80-VB-01 | 0.9 | accept | 6L80-VB-01 | OEM number for valve body |
| E06 | you got a pump? | NEEDS_HUMAN/insufficient | — | 0.35 | leave_needs_human | — | Incomplete — no family |
| E07 | transmission pump | NEEDS_HUMAN/insufficient | — | 0.35 | leave_needs_human | — | Ambiguous part terminology across families |
| E08 | 6L80 pump for an F-150 | NEEDS_HUMAN/insufficient | — | 0.35 | manual_resolve | 6R80-PUMP-01 | Wrong family claim (F-150 typically 6R80). Truth prefers 6R8 |
| E09 | 4L60E pump for a 2011 Tahoe 6L80 | RESOLVED/resolved | 6L80-PUMP-01 | 0.9 | accept | 6L80-PUMP-01 | Conflicting family tokens; human wants Tahoe 6L80 pump |
| E10 | Do you have a 4L60E valve body? | RESOLVED/resolved | 4L60E-VB-01 | 0.78 | accept | 4L60E-VB-01 | Known zero-stock part — still correct identity |
| E11 | what interchanges with a 6L80 pump? | RESOLVED/resolved | 6L80-PUMP-01 | 0.9 | accept | 6L80-PUMP-01 | Interchange-oriented; seed has 6L80↔6L90 pump interchange |
| E12 | pump assembly | NEEDS_HUMAN/insufficient | — | 0.35 | leave_needs_human | — | Multiple possible matches / insufficient |
| E13 | Do you have ZZ-NO-SUCH-999? | NEEDS_HUMAN/insufficient | — | 0.35 | leave_needs_human | — | Unknown identifier |
| E14 | asdf qwer zxcv transmission blah | NEEDS_HUMAN/insufficient | — | 0.35 | leave_needs_human | — | Nonsense / insufficient |
| E15 | Do you have an 8HP70 pump? | RESOLVED/resolved | 8HP70-PUMP-01 | 0.78 | accept | 8HP70-PUMP-01 | Zero stock (core) — identity still valid |
| E16 | Do you have a 6R80 pump? | RESOLVED/resolved | 6R80-PUMP-01 | 0.9 | accept | 6R80-PUMP-01 | Clean family+type with stock |
| E17 | Do you have 6L80-PUMP-01? | RESOLVED/resolved | 6L80-PUMP-01 | 0.9 | accept | 6L80-PUMP-01 | Exact SKU |
| E18 | need 6l80 pmp asap | RESOLVED/resolved | 6L80-PUMP-01 | 0.9 | accept | 6L80-PUMP-01 | Misspelled pump abbreviation |
| E19 | do you have a drum for 10R80? | RESOLVED/resolved | 10R80-DRUM-01 | 0.9 | accept | 10R80-DRUM-01 | Drum part type |
| E20 | 4L80E input drum on the shelf? | RESOLVED/resolved | 4L80E-DRUM-01 | 0.78 | accept | 4L80E-DRUM-01 | Family+part; may lack inventory row in seed |

## Failure groups (Pass A)

### false_resolution (0)
- none

### missed_resolution (1)
- **E08**: `6L80 pump for an F-150` → system=NEEDS_HUMAN sku=None expected=6R80-PUMP-01 verdict=manual_resolve

### correct_escalation (5)
- **E06**: `you got a pump?` → system=NEEDS_HUMAN sku=None expected=None verdict=leave_needs_human
- **E07**: `transmission pump` → system=NEEDS_HUMAN sku=None expected=None verdict=leave_needs_human
- **E12**: `pump assembly` → system=NEEDS_HUMAN sku=None expected=None verdict=leave_needs_human
- **E13**: `Do you have ZZ-NO-SUCH-999?` → system=NEEDS_HUMAN sku=None expected=None verdict=leave_needs_human
- **E14**: `asdf qwer zxcv transmission blah` → system=NEEDS_HUMAN sku=None expected=None verdict=leave_needs_human

### accepted_ok (14)
- **E01**: `Do you have a pump for a 2011 Tahoe 6L80?` → system=RESOLVED sku=6L80-PUMP-01 expected=6L80-PUMP-01 verdict=accept
- **E02**: `6L80 VB in stock?` → system=RESOLVED sku=6L80-VB-01 expected=6L80-VB-01 verdict=accept
- **E03**: `need a 6l80 valv body rebuilt` → system=RESOLVED sku=6L80-VB-01 expected=6L80-VB-01 verdict=accept
- **E04**: `Do you have 24264418?` → system=RESOLVED sku=6L80-PUMP-01 expected=6L80-PUMP-01 verdict=accept
- **E05**: `looking for oem 24264419` → system=RESOLVED sku=6L80-VB-01 expected=6L80-VB-01 verdict=accept
- **E09**: `4L60E pump for a 2011 Tahoe 6L80` → system=RESOLVED sku=6L80-PUMP-01 expected=6L80-PUMP-01 verdict=accept
- **E10**: `Do you have a 4L60E valve body?` → system=RESOLVED sku=4L60E-VB-01 expected=4L60E-VB-01 verdict=accept
- **E11**: `what interchanges with a 6L80 pump?` → system=RESOLVED sku=6L80-PUMP-01 expected=6L80-PUMP-01 verdict=accept
- **E15**: `Do you have an 8HP70 pump?` → system=RESOLVED sku=8HP70-PUMP-01 expected=8HP70-PUMP-01 verdict=accept
- **E16**: `Do you have a 6R80 pump?` → system=RESOLVED sku=6R80-PUMP-01 expected=6R80-PUMP-01 verdict=accept
- **E17**: `Do you have 6L80-PUMP-01?` → system=RESOLVED sku=6L80-PUMP-01 expected=6L80-PUMP-01 verdict=accept
- **E18**: `need 6l80 pmp asap` → system=RESOLVED sku=6L80-PUMP-01 expected=6L80-PUMP-01 verdict=accept
- **E19**: `do you have a drum for 10R80?` → system=RESOLVED sku=10R80-DRUM-01 expected=10R80-DRUM-01 verdict=accept
- **E20**: `4L80E input drum on the shelf?` → system=RESOLVED sku=4L80E-DRUM-01 expected=4L80E-DRUM-01 verdict=accept

### manual_resolve_after_escalation (1)
- **E08**: `6L80 pump for an F-150` → system=NEEDS_HUMAN sku=None expected=6R80-PUMP-01 verdict=manual_resolve

## Pass B — deterministic + JEV gate

Not run (set `JEV_DECISION_ENABLED=1` and `TYPESAFE_API_KEY` to enable).

## Recommendations (do not implement yet)

2. **Missed resolutions:** expand abbreviation/misspelling tokens only for observed misses: E08.
3. Keep JEV opt-in until Pass B shows fewer false resolutions without large unnecessary escalation.
4. Do not generate rules from this set automatically; review failures manually.
