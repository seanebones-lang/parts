"""AgentResult structured public shape (pure pydantic — no DB deps)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Prefer lightweight module so core CI needs only pydantic (via .[api])
from app.agents.result import AgentResult  # noqa: E402


def test_agent_result_to_public_dict():
    r = AgentResult(
        success=True,
        data={"sku": "BP-HC19"},
        message="ok",
        confidence=0.91,
        agent_type="parts_lookup",
        traffic_light="green",
        requires_human=False,
        correlation_id="c1",
        tokens_used=10,
        cost=0.001,
    )
    d = r.to_public_dict()
    assert d["success"] is True
    assert d["traffic_light"] == "green"
    assert d["data"]["sku"] == "BP-HC19"
    assert d["usage"]["tokens_used"] == 10
    assert d["errors"] == []
