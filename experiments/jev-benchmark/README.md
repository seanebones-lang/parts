# JEV Benchmark (parts-inquiry classification)

Isolated, read-only benchmark comparing three approaches for classifying an
incoming dealership parts inquiry. **Does not modify production code, APIs,
schemas, or dependencies** — it only reads the existing `parrts` email desk.

## Status

- [x] Scaffold + hand-labeled gold corpus (>=100 examples, 7 content classes)
- [x] Approach A: rule-based baseline (`parrts.email.classify`)
- [x] Approach B: existing LLM classifier (optional/local credentials required)
- [x] Approach C: JEV — **STUB only, not implemented**
- [ ] Run A, B, C together (this iteration runs A only per instructions)

## Taxonomy

Seven mutually-exclusive content classes (lowercase snake_case):

```
parts_availability  price_request  compatibility_fitment  order_status
sell_part           general_question  spam_or_irrelevant
```

`needs_human` is a **separate boolean** adjudication flag, evaluated
independently (NOT an 8th label). See `labels.py` for mapping vs the
production `EMAIL_TYPES`.

## Run

```bash
# Build / refresh the corpus (assigns independent gold labels)
#   Run from repo root so `parrts` is importable:
PYTHONPATH=src python experiments/jev-benchmark/corpus/build_corpus.py

# Deterministic baseline only (this iteration)
PYTHONPATH=src python experiments/jev-benchmark/run_benchmark.py --approach rule_based

# All three (B skipped cleanly if no credentials; C always skipped as stub)
PYTHONPATH=backend:src python experiments/jev-benchmark/run_benchmark.py \
    --approach rule_based --approach llm_existing --approach jev
```

Output: `results/report.json` (full), plus a human-readable console summary.

## Important guarantees (per approved plan)

1. **Gold labels are ground truth**, assigned by hand in
   `corpus/build_corpus.py`. They are **never** derived from
   `classify_email()` output.
2. **No production files are touched.** Only new files under this directory.
3. **No JEV SDK / API / credentials.** `approaches/jev.py` is a stub that
   raises `NotImplementedError`.
4. **LLM adapter is optional** and self-gating: if backend deps or
   `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` are unavailable it is skipped cleanly.
5. **Deterministic baseline cost = $0** (no token cost).

## Provenance / honesty

- `source="seed_data"` / `"test_fixture"` — from existing repo fixtures.
- `source="synthetic"` — hand-authored by the benchmark author to exercise
  every class plus hard edge cases (fitment+price, vague existing-order, sell
  used parts, disguised spam, complaint-with-parts, incomplete vehicle,
  typo-heavy, very short, multi-intent). Deliberately NOT labeled as customer
  history.
- Deliberate taxonomy gaps the benchmark exposes: new-part order intent,
  billing/payment inquiries, and complaint/escalations have **no dedicated
  content class** — they are folded to the nearest class and carried by the
  `needs_human` flag (per approved decision #2).

## Files

```
labels.py                 taxonomy + class constants
metrics.py                accuracy, per-class P/R/F1, confusion, needs_human, latency
run_benchmark.py          runner (CLI)
corpus/build_corpus.py    builds gold_labels.jsonl
corpus/gold_labels.jsonl  the committed gold corpus
approaches/rule_based.py  A: wrapper over parrts.email.classify
approaches/llm_existing.py B: optional LLM adapter
approaches/jev.py         C: stub
results/                  per-run report.json
```