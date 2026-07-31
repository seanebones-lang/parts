"""LangGraph workflow graph + offline parts path tests."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "backend"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core")


def test_workflow_registers_all_specialists():
    from app.agents.langgraph_workflow import SPECIALIST_NODES, LangGraphWorkflow

    wf = LangGraphWorkflow()
    nodes = set(wf.graph_nodes())
    for name in SPECIALIST_NODES:
        assert name in nodes
    assert "supervisor" in nodes
    assert "finalize" in nodes
    assert "email_classifier" in nodes


def test_parts_lookup_workflow_offline():
    from app.agents.langgraph_workflow import LangGraphWorkflow

    wf = LangGraphWorkflow()

    async def _run():
        return await wf.process(
            {"query": "brake pads for 2019 Honda Civic", "workflow_type": "parts_lookup"}
        )

    result = asyncio.run(_run())
    assert isinstance(result, dict)
    # Either agent path or parrts fallback should populate parts_response
    parts = result.get("parts_response") or {}
    # Accept hits list or nested data
    hits = parts.get("hits") or (parts.get("data") or {}).get("hits") or []
    assert result.get("workflow_type") == "parts_lookup" or hits or result.get(
        "agents_invoked"
    )
    assert "agents_invoked" in result
    assert "parts_lookup" in (result.get("agents_invoked") or []) or hits


def test_email_route_heuristic_to_parts():
    from app.agents.langgraph_workflow import LangGraphWorkflow

    wf = LangGraphWorkflow()

    async def _run():
        return await wf.process(
            {
                "subject": "Need brake pads",
                "body": "Looking for brake pads for 2019 Honda Civic stock check",
            }
        )

    result = asyncio.run(_run())
    assert isinstance(result, dict)
    # classification fallback or parts path
    assert result.get("classification") or result.get("parts_response") is not None
