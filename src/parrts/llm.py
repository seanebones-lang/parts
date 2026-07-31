"""Optional LLM answer synthesis; no-op without API keys."""

from __future__ import annotations

import os
from typing import Any

from parrts.models import QueryResult, RankedHit


def _has_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _has_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def llm_available() -> bool:
    return _has_openai() or _has_anthropic()


def _format_context(hits: list[RankedHit]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        p = h.part
        lines.append(
            f"{i}. {p.name} | loc={p.location} | sku={p.sku} | "
            f"stock={p.stock} | price=${p.price:.2f} | score={h.score:.3f}"
        )
    return "\n".join(lines) if lines else "(no hits)"


def synthesize_answer(query: str, result: QueryResult) -> str | None:
    """
    Generate a short natural-language answer from retrieval context.
    Returns None when no provider keys / SDKs are available.
    """
    if not llm_available():
        return None

    context = _format_context(result.hits)
    tl = result.traffic_light
    tl_txt = f"{tl.color} conf={tl.confidence}" if tl else "n/a"
    system = (
        "You are a helpful auto-parts inventory assistant for Chicago dealerships. "
        "Answer concisely using only the provided inventory hits. "
        "Mention stock, location, SKU, and price when relevant. "
        "If traffic light is red, say what to do next."
    )
    user = (
        f"Customer query: {query}\n"
        f"Traffic light: {tl_txt}\n"
        f"Hits:\n{context}\n"
        "Write a 2-4 sentence answer."
    )

    if _has_openai():
        try:
            return _openai_complete(system, user)
        except Exception:
            pass
    if _has_anthropic():
        try:
            return _anthropic_complete(system, user)
        except Exception:
            pass
    return None


def _openai_complete(system: str, user: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("PARRTS_OPENAI_MODEL", "gpt-4.1-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=300,
    )
    return (resp.choices[0].message.content or "").strip()


def _anthropic_complete(system: str, user: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("PARRTS_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    msg = client.messages.create(
        model=model,
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts: list[str] = []
    for block in msg.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def offline_answer(query: str, result: QueryResult) -> str:
    """Deterministic template answer when LLM is disabled/unavailable."""
    if not result.hits:
        return (
            f"No matching parts found for '{query}'. "
            "Try make, model, year, and part type (e.g. brake pads 2019 Honda Civic)."
        )
    top = result.hits[0]
    p = top.part
    tl = result.traffic_light
    color = tl.color if tl else "unknown"
    return (
        f"Best match for '{query}': {p.name} at {p.location} "
        f"(SKU {p.sku}, stock {p.stock}, ${p.price:.2f}, score {top.score:.2f}). "
        f"Traffic light: {color}."
        + (f" {tl.reason}" if tl and tl.reason else "")
    )


def status_info() -> dict[str, Any]:
    return {
        "openai": _has_openai(),
        "anthropic": _has_anthropic(),
        "llm_available": llm_available(),
    }
