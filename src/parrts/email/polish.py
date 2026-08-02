"""Optional LLM polish for suggested email replies (no-op without keys)."""

from __future__ import annotations

import os
from typing import Any


def llm_polish_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


def polish_response(
    *,
    subject: str,
    inbound_body: str,
    draft: str,
    classification: str | None = None,
    traffic_light: str | None = None,
) -> str | None:
    """
    Return a polished draft, or None if no provider / failure.
    Never invent inventory facts — keep SKUs/prices from the draft.
    """
    if not draft or not draft.strip():
        return None
    if not llm_polish_available():
        return None

    system = (
        "You polish customer-facing replies for a car dealership parts desk. "
        "Keep all SKUs, prices, stock numbers, and locations exactly as written. "
        "Do not invent parts. Be concise, professional, warm. "
        "Return only the final email body text."
    )
    user = (
        f"Classification: {classification or 'n/a'}\n"
        f"Traffic light: {traffic_light or 'n/a'}\n"
        f"Inbound subject: {subject}\n"
        f"Inbound body:\n{inbound_body[:2000]}\n\n"
        f"Draft reply to polish:\n{draft}"
    )

    if os.environ.get("OPENAI_API_KEY"):
        try:
            return _openai(system, user)
        except Exception:
            pass
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _anthropic(system, user)
        except Exception:
            pass
    return None


def _openai(system: str, user: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("PARRTS_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip()


def _anthropic(system: str, user: str) -> str:
    from anthropic import Anthropic

    client = Anthropic()
    model = (
        os.environ.get("PARRTS_ANTHROPIC_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or "claude-sonnet-4-20250514"
    )
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts: list[str] = []
    for block in msg.content:
        t = getattr(block, "text", None)
        if t:
            parts.append(t)
    return "\n".join(parts).strip()


def maybe_polish(email_row: dict[str, Any], draft: str | None = None) -> str:
    """Polish if keys present; else return draft unchanged."""
    text = draft if draft is not None else (email_row.get("suggested_response") or "")
    tl = email_row.get("traffic_light")
    color = tl.get("color") if isinstance(tl, dict) else tl
    polished = polish_response(
        subject=str(email_row.get("subject") or ""),
        inbound_body=str(email_row.get("body_text") or ""),
        draft=text,
        classification=email_row.get("email_type"),
        traffic_light=str(color) if color else None,
    )
    return polished or text
