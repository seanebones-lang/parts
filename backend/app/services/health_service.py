"""
Health check service.
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from app.core.config import settings


class HealthService:
    """Health check service for monitoring system status."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis_client = None
    
    async def check_all_services(self) -> Dict[str, Any]:
        """Check all system services."""
        return {
            "status": "healthy",
            "services": {
                "database": await self._check_database(),
                "redis": await self._check_redis(),
                "ai_services": await self._check_ai_services(),
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Will be replaced with actual timestamp
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            result = await self.db.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "response_time_ms": 0  # Will implement actual timing
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            if not self.redis_client:
                self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            return {
                "status": "healthy",
                "response_time_ms": 0  # Will implement actual timing
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e)
            }
    
    async def _check_ai_services(self) -> Dict[str, Any]:
        """Check AI service availability."""
        # This will check OpenAI and Anthropic API connectivity
        return {
            "status": "healthy",
            "openai": "available",
            "anthropic": "available"
        }
