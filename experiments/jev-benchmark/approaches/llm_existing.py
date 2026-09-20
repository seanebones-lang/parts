"""Approach B — existing LLM baseline (xAI / Grok, self-contained).

Uses the user's xAI API (https://api.x.ai/v1) with the fastest Grok model
(`grok-3-mini` by default — cheap, fast, deterministic). Self-contained, no
Postgres/FastAPI/LangGraph deps.

Taxonomy: constrained to the 7 frozen benchmark labels + separate needs_human
boolean. Gold labels never shown to the model.

Failure semantics per Phase 2 spec:
- Exactly one of the 7 labels forced; needs_human as separate bool.
- temperature=0.
- Record provider, model, tokens, cost, latency.
- API errors recorded as failures. No silent rule fallback.
- Missing credentials -> raises LLMClassifierError naming the required env var.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from labels import CLASSES

REQUIRED_ENV = "XAI_API_KEY"
BASE_URL = "https://api.x.ai/v1"
MODEL = "grok-3-mini"  # fastest + cheapest for bulk classification
PRICE_PER_MT = {"input": 0.15, "output": 0.60}  # grok-3-mini (approx)


def _client():
    from openai import OpenAI
    key = os.environ.get(REQUIRED_ENV)
    if not key:
        raise RuntimeError(f"{REQUIRED_ENV} is not set")
    return OpenAI(api_key=key, base_url=BASE_URL)


def config() -> dict:
    return {
        "name": "llm_existing",
        "implemented": True,
        "available": bool(os.environ.get(REQUIRED_ENV)),
        "required_env": None if os.environ.get(REQUIRED_ENV) else REQUIRED_ENV,
        "provider": "xai",
        "base_url": BASE_URL,
        "model": MODEL,
        "temperature": 0,
        "price_per_mtok_in": PRICE_PER_MT["input"],
        "price_per_mtok_out": PRICE_PER_MT["output"],
        "cost_per_query": "model-dependent",
        "offline": False,
    }


_SYSTEM_PROMPT = f"""You are a parts-desk email classifier for an auto dealership.
For each inbound inquiry, classify it into EXACTLY ONE of these seven content categories:

{chr(10).join('- ' + c for c in CLASSES)}

Definitions:
- parts_availability:    asks whether a specific part is in stock / available.
- price_request:         asks the price / cost / quote of a part.
- compatibility_fitment: asks whether a part fits a vehicle or is compatible.
- order_status:          asks about the status, tracking, or delivery of an EXISTING order.
- sell_part:             the sender wants to sell / trade in / offload parts.
- general_question:      hours, policies, locations, or other general questions.
- spam_or_irrelevant:    marketing, scams, phishing, or content not from a real customer.

Respond with ONLY a JSON object on a single line, no prose, no code fences:
{{"label": "<one of the seven above>", "needs_human": true_or_false}}

needs_human is a SEPARATE boolean (NOT a label): true only when this message
requires a human parts representative — escalations, complaints, threats,
ambiguous multi-intent, safety, or anything a contact form cannot safely auto-
answer. Set it false for routine availability/price/order-status/definite cases."""


def _build_user(subject: str, body: str, sender_email: str) -> str:
    return (
        "Classify this inbound parts inquiry.\n"
        f"Subject: {subject or ''}\n"
        f"From: {sender_email or 'unknown'}\n"
        f"Body:\n{body or ''}"
    )


def _try_parse(content: str) -> dict | None:
    content = (content or "").strip()
    if "```" in content:
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else content
        content = content.lstrip("json").strip()
    try:
        return json.loads(content)
    except Exception:
        pass
    s, e = content.find("{"), content.rfind("}")
    if s != -1 and e != -1:
        try:
            return json.loads(content[s : e + 1])
        except Exception:
            pass
    return None


class LLMClassifierError(RuntimeError):
    pass


def classify(subject: str, body: str, sender_email: str = "") -> dict[str, Any]:
    """Deterministic LLM classification of one query. Failures are recorded,
    never silently substituted."""
    if not os.environ.get(REQUIRED_ENV):
        raise LLMClassifierError(f"credentials unavailable: missing {REQUIRED_ENV}")
    client = _client()
    t0 = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=200,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user(subject, body, sender_email)},
            ],
        )
        latency = time.perf_counter() - t0

        content = (resp.choices[0].message.content or "").strip()
        usage = resp.usage
        in_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
        out_tok = int(getattr(usage, "completion_tokens", 0) or 0)
        cost = (in_tok / 1e6) * PRICE_PER_MT["input"] + (out_tok / 1e6) * PRICE_PER_MT["output"]

        parsed = _try_parse(content)
        if not isinstance(parsed, dict):
            raise LLMClassifierError(f"non-JSON model output: {content[:120]!r}")

        label = str(parsed.get("label", "")).strip().lower()
        if label not in CLASSES:
            raise LLMClassifierError(f"model returned invalid label {label!r}")

        return {
            "label": label,
            "confidence": 1.0,
            "needs_human": bool(parsed.get("needs_human", False)),
            "latency_s": latency,
            "cost_usd": round(cost, 6),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "total_tokens": in_tok + out_tok,
            "provider": "xai",
            "model": MODEL,
            "raw_output": content[:200],
        }
    except LLMClassifierError:
        raise
    except Exception as exc:
        raise LLMClassifierError(f"api_error: {exc}") from exc


def estimate_cost(corpus_rows: int) -> dict:
    """Dry-run cost estimate using conservative per-query token guess (no call)."""
    est_in, est_out = 450, 80
    return {
        "model": MODEL,
        "price_per_mtok_in": PRICE_PER_MT["input"],
        "price_per_mtok_out": PRICE_PER_MT["output"],
        "est_tokens_per_query_in": est_in,
        "est_tokens_per_query_out": est_out,
        "est_total_input_tokens": corpus_rows * est_in,
        "est_total_output_tokens": corpus_rows * est_out,
        "est_total_tokens": corpus_rows * (est_in + est_out),
        "est_total_cost_usd": round(
            (corpus_rows * est_in / 1e6) * PRICE_PER_MT["input"]
            + (corpus_rows * est_out / 1e6) * PRICE_PER_MT["output"],
            6,
        ),
        "note": "estimate only; actual tokens/cost recorded per request after run",
    }