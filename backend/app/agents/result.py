"""Structured agent result — pure Pydantic (no SQLAlchemy / DB imports)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentResult(BaseModel):
    """Standard result format for all agents."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    agent_type: Optional[str] = None
    traffic_light: Optional[str] = None  # green | yellow | red
    requires_human: bool = False
    correlation_id: Optional[str] = None
    errors: Optional[List[str]] = None

    def to_public_dict(self) -> Dict[str, Any]:
        """Stable JSON shape for API / LangGraph finalize nodes."""
        return {
            "success": self.success,
            "message": self.message,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "agent_type": self.agent_type,
            "traffic_light": self.traffic_light,
            "requires_human": self.requires_human,
            "correlation_id": self.correlation_id,
            "data": self.data or {},
            "errors": self.errors or [],
            "usage": {
                "tokens_used": self.tokens_used,
                "cost": self.cost,
            },
        }
