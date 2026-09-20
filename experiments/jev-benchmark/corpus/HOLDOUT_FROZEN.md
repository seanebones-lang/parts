# Blind Holdout Corpus — FROZEN

**Timestamp**: 2026-09-20 15:22 CDT  
**File**: `holdout_labels.jsonl`  
**SHA-256**: `4c17edde4fdca2c89b3bb23605ab687c0b72449ac23258232ea7829ca2d06313`  
**Total examples**: 200  
**Source**: entirely new synthetic generation (no overlap with development corpus)

## Class Distribution
- price_request: 35
- parts_availability: 32
- general_question: 30
- compatibility_fitment: 28
- spam_or_irrelevant: 28
- order_status: 25
- sell_part: 22

## needs_human Distribution
- False: 169 (84.5%)
- True: 31 (15.5%)

## Freeze Statement

This holdout corpus was generated and labeled **before any classifier was run against it**.

No model (RULES, GROK, HYBRID, or JEV) had seen any of these 200 examples at the time of freezing.

No tuning, prompt changes, or threshold adjustments were made after generation.

This file is now permanently frozen as an evaluation set. Any future inspection of errors must be done after the blind evaluation is complete.

**Frozen by**: Hermes Agent (Phase 5)  
**Date**: 2026-09-20