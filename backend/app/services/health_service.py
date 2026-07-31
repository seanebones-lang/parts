"""
Health check service — honest status, optional dependency probes.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class HealthService:
    """Health check service for monitoring system status."""

    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self.db = db

    async def check_all_services(self) -> Dict[str, Any]:
        """Check system services; return degraded/unhealthy when deps fail."""
        postgres = await self.check_postgres()
        redis_status = await self.check_redis()
        ai = await self._check_ai_services()

        services = {
            "database": postgres,
            "redis": redis_status,
            "ai_services": ai,
        }

        statuses = [s.get("status") for s in services.values()]
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "healthy" for s in statuses) or any(s == "degraded" for s in statuses):
            # Partial availability or soft failures
            if any(s == "unhealthy" for s in statuses):
                overall = "degraded"
            else:
                overall = "degraded" if any(s != "healthy" for s in statuses) else "healthy"
        else:
            overall = "unhealthy"

        # AI without keys is degraded, not a hard fail of the whole app
        if overall == "unhealthy" and postgres.get("status") == "healthy":
            overall = "degraded"

        return {
            "status": overall,
            "services": services,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def check_postgres(self) -> Dict[str, Any]:
        """Optional Postgres connectivity check."""
        start = time.perf_counter()
        try:
            if self.db is not None:
                await self.db.execute(text("SELECT 1"))
                ms = (time.perf_counter() - start) * 1000
                return {"status": "healthy", "response_time_ms": round(ms, 2)}

            # Standalone probe via engine (main /health without Depends)
            from app.core.database import engine

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            ms = (time.perf_counter() - start) * 1000
            return {"status": "healthy", "response_time_ms": round(ms, 2)}
        except Exception as exc:
            ms = (time.perf_counter() - start) * 1000
            return {
                "status": "unhealthy",
                "error": str(exc),
                "response_time_ms": round(ms, 2),
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
            }

    async def check_redis(self) -> Dict[str, Any]:
        """Optional Redis connectivity check."""
        start = time.perf_counter()
        client = None
        try:
            import redis.asyncio as redis

            client = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await client.ping()
            ms = (time.perf_counter() - start) * 1000
            return {"status": "healthy", "response_time_ms": round(ms, 2)}
        except ImportError:
            return {
                "status": "degraded",
                "error": "redis package not installed",
            }
        except Exception as exc:
            ms = (time.perf_counter() - start) * 1000
            return {
                "status": "unhealthy",
                "error": str(exc),
                "response_time_ms": round(ms, 2),
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
            }
        finally:
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    try:
                        await client.close()
                    except Exception:
                        pass

    async def _check_ai_services(self) -> Dict[str, Any]:
        """Report AI client configuration (no live billed calls)."""
        try:
            from app.services.llm_service import LLMService

            llm = LLMService()
            providers = llm.provider_status()
            if llm.available:
                status = "healthy"
            elif not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
                status = "degraded"
                providers["note"] = "No API keys configured"
            else:
                status = "degraded"
                providers["note"] = "Keys set but async clients unavailable"
            return {"status": status, **providers}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    # Back-compat private aliases used by older call sites
    async def _check_database(self) -> Dict[str, Any]:
        return await self.check_postgres()

    async def _check_redis(self) -> Dict[str, Any]:
        return await self.check_redis()
