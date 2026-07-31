"""
Main FastAPI application entry point for the Dealership AI Parts System.
"""

from contextlib import asynccontextmanager
import time
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.services.health_service import HealthService


def enforce_production_secrets() -> None:
    """Fail fast when production would run with insecure defaults.

    Triggers when ENVIRONMENT=production OR AUTH_MODE=production.
    - Insecure SECRET_KEY → RuntimeError (hard fail)
    - DEBUG=True in production → RuntimeError (hard fail)
    """
    if not settings.is_production_runtime():
        return

    problems: list[str] = []
    if settings.secret_key_is_insecure():
        problems.append(
            "SECRET_KEY is missing or uses an insecure default "
            "(set a strong unique SECRET_KEY for production)"
        )
    if settings.DEBUG:
        problems.append(
            "DEBUG=True is not allowed when ENVIRONMENT or AUTH_MODE is production"
        )
    if problems:
        raise RuntimeError(
            "Production secret guard failed:\n- " + "\n- ".join(problems)
        )


# Boot-time guard (import/module load). Demo/dev defaults still boot.
enforce_production_secrets()

# API router depends on models/services that may still be mid-fix elsewhere.
# Keep core app bootable (/, /health) even if the full v1 surface fails to import.
try:
    from app.api.v1.api import api_router
except Exception as _api_import_error:  # pragma: no cover
    api_router = None
    print(f"Warning: API router not loaded: {_api_import_error}")

try:
    from app.middleware.rate_limiting import rate_limit_middleware
except Exception:  # pragma: no cover
    rate_limit_middleware = None

# Always-available hybrid RAG surface (no Postgres required)
_parrts_engine = None


def _get_parrts_engine():
    global _parrts_engine
    if _parrts_engine is not None:
        return _parrts_engine
    try:
        from pathlib import Path

        from parrts.embeddings import HashingEmbedder
        from parrts.engine import PartsRAGEngine

        root = Path(__file__).resolve().parent.parent
        engine_obj = PartsRAGEngine(root=root, embedder=HashingEmbedder())
        engine_obj.ensure_ready()
        _parrts_engine = engine_obj
        return _parrts_engine
    except Exception as exc:
        print(f"Warning: parrts engine unavailable: {exc}")
        return None


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID / correlation id to every request."""

    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.correlation_id = cid
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = cid
        response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Re-check in case env was mutated after import (e.g. tests / late .env).
    enforce_production_secrets()
    print("Starting Dealership AI Parts System...")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Auth mode: {settings.AUTH_MODE} (demo = open endpoints; production requires JWT)")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully")
    except Exception as exc:
        print(f"Database init skipped/failed: {exc}")

    if _get_parrts_engine() is not None:
        print("Parrts hybrid RAG core ready")
    else:
        print("Parrts hybrid RAG core not loaded")

    yield

    print("Shutting down Dealership AI Parts System...")
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="Dealership AI Parts System",
    description=(
        "AI-powered multi-location dealership parts management system. "
        f"Auth mode: {settings.AUTH_MODE}."
    ),
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"],
)

app.add_middleware(CorrelationMiddleware)

if settings.RATE_LIMIT_ENABLED and rate_limit_middleware is not None:
    try:
        from app.middleware.rate_limiting import configure_rate_limiter

        configure_rate_limiter(
            settings.RATE_LIMIT_PER_MINUTE, settings.RATE_LIMIT_PER_HOUR
        )
    except Exception:
        pass
    app.middleware("http")(rate_limit_middleware)
    print("Rate limiting middleware enabled")

if api_router is not None:
    app.include_router(api_router, prefix="/api/v1")
else:
    print("Warning: /api/v1 routes unavailable due to import errors in models/endpoints")


@app.get("/")
async def root():
    """Root endpoint with system status."""
    parrts = _get_parrts_engine() is not None
    api_detail = None
    if api_router is not None:
        try:
            from app.api.v1.api import router_status

            api_detail = router_status()
        except Exception as exc:
            api_detail = {"error": str(exc)}
    return {
        "message": "Dealership AI Parts System API",
        "version": "1.3.0",
        "status": "operational",
        "parrts_core": "ready" if parrts else "unavailable",
        "api_v1": "loaded" if api_router is not None else "degraded",
        "api_v1_detail": api_detail,
        "auth_mode": settings.AUTH_MODE,
        "auth_note": (
            "Demo mode: JWT endpoints optional; /query and /health are open."
            if settings.AUTH_MODE == "demo"
            else "Production mode: protect mutating routes with JWT."
        ),
        "rate_limit": settings.RATE_LIMIT_ENABLED,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Honest health check — reports degraded when dependencies are down."""
    health_service = HealthService()
    result = await health_service.check_all_services()
    parrts = _get_parrts_engine()
    result["parrts_core"] = "ready" if parrts is not None else "unavailable"
    result["auth_mode"] = settings.AUTH_MODE
    result["rate_limit"] = settings.RATE_LIMIT_ENABLED
    result["pgvector_enabled"] = bool(getattr(settings, "PGVECTOR_ENABLED", False))
    result["vector_backend"] = getattr(settings, "VECTOR_BACKEND", "auto")
    result["api_v1"] = "loaded" if api_router is not None else "degraded"
    try:
        from app.api.v1.api import router_status

        result["api_v1_detail"] = router_status()
    except Exception as exc:
        result["api_v1_detail"] = {"error": str(exc)}
    try:
        from app.services.vector_service import VectorService

        result["vector"] = VectorService().backend_status()
    except Exception as exc:
        result["vector"] = {"error": str(exc)}
    return result


@app.get("/metrics")
async def metrics_stub():
    """Lightweight Prometheus-style metrics stub (no external deps)."""
    lines = [
        "# HELP parrts_info Static build info",
        "# TYPE parrts_info gauge",
        f'parrts_info{{version="1.2.0",auth_mode="{settings.AUTH_MODE}"}} 1',
        "# HELP parrts_pgvector_enabled 1 if PGVECTOR_ENABLED",
        "# TYPE parrts_pgvector_enabled gauge",
        f"parrts_pgvector_enabled {1 if getattr(settings, 'PGVECTOR_ENABLED', False) else 0}",
        "# HELP parrts_rate_limit_enabled 1 if rate limiting on",
        "# TYPE parrts_rate_limit_enabled gauge",
        f"parrts_rate_limit_enabled {1 if settings.RATE_LIMIT_ENABLED else 0}",
        "# HELP parrts_core_ready 1 if hybrid RAG core loaded",
        "# TYPE parrts_core_ready gauge",
        f"parrts_core_ready {1 if _get_parrts_engine() is not None else 0}",
    ]
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/query")
async def parrts_query(
    text: str,
    location: str | None = None,
    top_k: int = 5,
    use_llm: bool = False,
    expand_parent: bool = False,
    use_rerank: bool = False,
):
    """Hybrid parts query via parrts core (no DB required)."""
    eng = _get_parrts_engine()
    if eng is None:
        return {"error": "parrts core unavailable", "success": False}
    result = eng.query(
        text=text,
        location=location,
        top_k=top_k,
        use_llm=use_llm,
        expand_parent=expand_parent,
        use_rerank=use_rerank,
    )
    return result.to_dict()


@app.post("/query")
async def parrts_query_post(payload: dict):
    """POST hybrid parts query via parrts core."""
    eng = _get_parrts_engine()
    if eng is None:
        return {"error": "parrts core unavailable", "success": False}
    text = str(payload.get("text") or payload.get("query") or "").strip()
    if not text:
        return {"error": "text is required", "success": False}
    result = eng.query(
        text=text,
        location=payload.get("location"),
        top_k=int(payload.get("top_k") or 5),
        use_llm=bool(payload.get("use_llm", False)),
        expand_parent=bool(payload.get("expand_parent", False)),
        use_rerank=bool(payload.get("use_rerank", False)),
    )
    return result.to_dict()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
