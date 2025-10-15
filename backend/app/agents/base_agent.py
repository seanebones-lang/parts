"""
Base agent class for all AI agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.agent_log import AgentLog, AgentType, LogLevel
from app.services.llm_service import LLMService


class AgentResult(BaseModel):
    """Standard result format for all agents."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, db: AsyncSession, agent_type: AgentType):
        self.db = db
        self.agent_type = agent_type
        self.llm_service = LLMService()
        
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process input data and return result."""
        pass
    
    async def log_action(
        self,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool,
        processing_time: float,
        tokens_used: int = None,
        cost: float = None,
        confidence: float = None,
        error_message: str = None,
        **context
    ):
        """Log agent action to database."""
        log = AgentLog(
            agent_type=self.agent_type,
            log_level=LogLevel.INFO if success else LogLevel.ERROR,
            action=action,
            message=error_message if not success else "Action completed successfully",
            input_data=input_data,
            output_data=output_data,
            processing_time=processing_time,
            tokens_used=tokens_used,
            cost=cost,
            confidence=confidence,
            success=success,
            error_message=error_message,
            **context
        )
        
        self.db.add(log)
        await self.db.commit()
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for this agent."""
        return f"""
You are a specialized AI agent for a dealership parts management system.
Agent Type: {self.agent_type.value}
Current Time: {datetime.utcnow().isoformat()}

You must be accurate, helpful, and professional in all interactions.
Always provide confidence scores for your responses.
If you're unsure about something, say so rather than guessing.
"""
    
    def _validate_confidence(self, confidence: float) -> float:
        """Validate and normalize confidence score."""
        if confidence is None:
            return 0.5
        return max(0.0, min(1.0, confidence))
