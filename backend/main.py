"""
Main FastAPI application entry point for the Dealership AI Parts System.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.services.health_service import HealthService

# API router depends on models/services that may still be mid-fix elsewhere.
# Keep core app bootable (/, /health) even if the full v1 surface fails to import.
try:
    from app.api.v1.api import api_router
except Exception as _api_import_error:  # pragma: no cover
    api_router = None
    print(f"Warning: API router not loaded: {_api_import_error}")

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting Dealership AI Parts System...")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully")
    except Exception as exc:
        # Boot even if DB is unavailable; health endpoint will report degraded.
        print(f"Database init skipped/failed: {exc}")

    if _get_parrts_engine() is not None:
        print("Parrts hybrid RAG core ready")
    else:
        print("Parrts hybrid RAG core not loaded")

    yield

    # Shutdown
    print("Shutting down Dealership AI Parts System...")
    try:
        await engine.dispose()
    except Exception:
        pass


# Create FastAPI application
app = FastAPI(
    title="Dealership AI Parts System",
    description="AI-powered multi-location dealership parts management system",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"],
)

# Include API routes when available
if api_router is not None:
    app.include_router(api_router, prefix="/api/v1")
else:
    print("Warning: /api/v1 routes unavailable due to import errors in models/endpoints")


@app.get("/")
async def root():
    """Root endpoint with system status."""
    parrts = _get_parrts_engine() is not None
    return {
        "message": "Dealership AI Parts System API",
        "version": "1.1.0",
        "status": "operational",
        "parrts_core": "ready" if parrts else "unavailable",
        "api_v1": "loaded" if api_router is not None else "degraded",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Honest health check — reports degraded when dependencies are down."""
    health_service = HealthService()
    result = await health_service.check_all_services()
    parrts = _get_parrts_engine()
    result["parrts_core"] = "ready" if parrts is not None else "unavailable"
    return result


@app.get("/query")
async def parrts_query(
    text: str,
    location: str | None = None,
    top_k: int = 5,
    use_llm: bool = False,
):
    """Hybrid parts query via parrts core (no DB required)."""
    eng = _get_parrts_engine()
    if eng is None:
        return {"error": "parrts core unavailable", "success": False}
    result = eng.query(text=text, location=location, top_k=top_k, use_llm=use_llm)
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
