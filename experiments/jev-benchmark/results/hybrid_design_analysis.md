# Hybrid Classifier Design Analysis (Frozen Data)

Date: 2026-09-20
Corpus: 124 frozen examples (unchanged)
Baselines frozen: RULES (37.10% acc) and GROK-3-MINI (90.32% acc)

## 1. Deterministic (RULES) Empirical Performance

**Classes with usable precision for potential bypass:**
- `price_request`: Precision 0.368, Recall 0.926 → high recall, low precision. Many other classes collapse into it.
- `order_status`: Precision 0.636, Recall 0.467 → best precision among deterministic classes, but still below 95% target.

**Classes with zero usable precision:**
- `parts_availability`, `compatibility_fitment`, `sell_part`, `spam_or_irrelevant` → all 0.0 precision/recall.
- `general_question` → low precision (0.311) due to heavy false-positive inflow from other classes.

**Confidence calibration:**
- RULES confidence is keyword-weight based. High-confidence predictions (≥0.9) are still frequently wrong when the input contains mixed signals (e.g., price + fitment, complaint + parts request).
- No evidence that a high deterministic confidence threshold would yield ≥95% precision on any class.

**Conclusion on deterministic bypass:**
No deterministic subset reaches the required ≥95% precision threshold with a generalizable, non-overfit condition. Any bypass would risk material accuracy regression. Therefore the hybrid will use deterministic routing only for the narrow high-precision subset of `order_status` (and possibly a very conservative slice of `price_request`) and send the majority of traffic to Grok.

## 2. Grok-3-MINI Performance on Frozen Corpus

- Strong overall accuracy (90.32%).
- Excellent on `sell_part` (F1 1.0), `compatibility_fitment` (0.97), `price_request` (0.94), `spam_or_irrelevant` (0.90).
- Weakest on `general_question` (recall only 0.59) — many multi-intent or vague inquiries fall here.
- needs_human positive recall: only 29.17% (21 false negatives). This is the biggest safety gap.
- Grok confidence is always reported as 1.0 (temperature=0, deterministic). Therefore model confidence cannot be used as a routing signal in the hybrid.

## 3. Risk / Escalation Gate Design

The needs_human gate must be high-recall (favor false positives over false negatives).

General operational signals (not derived from gold examples):
- Explicit complaint, refund demand, or "unacceptable" language
- Payment/fraud dispute or "chargeback" / "dispute" language
- Threats, legal, BBB, attorney, or "lawsuit" language
- Safety-critical language ("unsafe", "dangerous", "injury")
- Explicit request for manager / human / person / "speak to"
- Angry or abusive tone indicators
- Conflicting high-impact requests in one message
- Low classifier confidence on any high-stakes class

The gate runs first. Any trigger sends the inquiry to human regardless of later classifier output.

## 4. Hybrid Routing Policy (Pre-declared)

1. **Risk / Escalation Gate** (high-recall)
   - If any risk signal present → HUMAN
   - Else continue

2. **Deterministic Bypass** (conservative, ≥95% target)
   - Only `order_status` with clear tracking/shipment language and no risk signals → deterministic route
   - Very narrow conservative slice of `price_request` (pure price + part + vehicle, no fitment language, no risk) → deterministic route
   - All other cases → Grok

3. **Grok Fallback**
   - Because Grok confidence is not usable (always 1.0), all non-bypassed, non-risk cases go to Grok.
   - Grok output is accepted as the final classification unless the risk gate already triggered.

This policy deliberately errs on the side of sending more traffic to Grok rather than risking incorrect deterministic routing.

## 5. Grok Confidence Handling

The frozen Grok adapter (`llm_existing.py`) always returns `confidence: 1.0`.  
No usable per-prediction confidence signal is available from the current implementation.

Therefore the hybrid cannot perform confidence-based escalation on Grok outputs. All non-risk, non-deterministic-bypass traffic is sent to Grok and its output is used directly.

## 6. Pre-declared Thresholds (before any hybrid evaluation)

- needs_human probability threshold: **0.50** (frozen, not tuned)
- Deterministic bypass precision target: **≥ 0.95** (empirically not met by any broad deterministic subset, so bypass is minimal)

This document is the frozen design basis for the hybrid implementation. No changes will be made after the first complete evaluation run.