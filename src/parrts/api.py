"""Thin FastAPI surface over PartsRAGEngine.

Run:
  uvicorn parrts.api:app --reload --port 8080
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "parrts.api requires FastAPI. Install with: pip install 'parrts[api]'"
    ) from exc

from parrts import __version__
from parrts.embeddings import HashingEmbedder, resolve_embedder
from parrts.engine import PartsRAGEngine


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language parts query")
    location: Optional[str] = None
    top_k: int = Field(5, ge=1, le=50)
    use_llm: bool = False
    use_rerank: bool = False


def _project_root() -> Path:
    env = os.environ.get("PARRTS_ROOT")
    if env:
        return Path(env).resolve()
    # Prefer cwd; if package installed from repo, walk up looking for pyproject
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "parrts").exists():
            return candidate
    return cwd


@lru_cache(maxsize=1)
def get_engine() -> PartsRAGEngine:
    root = _project_root()
    embedder_name = os.environ.get("PARRTS_EMBEDDER", "hash").lower()
    if embedder_name == "hash":
        embedder = HashingEmbedder()
    else:
        embedder = resolve_embedder(embedder_name)
    engine = PartsRAGEngine(root=root, embedder=embedder)
    engine.ensure_ready()
    return engine


app = FastAPI(
    title="Parrts Hybrid RAG API",
    description="Modern hybrid retrieval + traffic-light policy for multi-location parts",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("PARRTS_CORS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        eng = get_engine()
        st = eng.status()
        return {
            "status": "healthy" if st.get("built") else "degraded",
            "version": __version__,
            "engine": st,
        }
    except Exception as exc:  # pragma: no cover
        return {"status": "unhealthy", "version": __version__, "error": str(exc)}


@app.get("/inventory/summary")
def inventory_summary() -> dict[str, Any]:
    eng = get_engine()
    st = eng.status()
    inv = st.get("inventory") or {}
    return {"version": __version__, **inv, "root": st.get("root")}


@app.post("/query")
def query_post(body: QueryRequest) -> dict[str, Any]:
    eng = get_engine()
    result = eng.query(
        text=body.text,
        location=body.location,
        top_k=body.top_k,
        use_llm=body.use_llm,
        use_rerank=body.use_rerank,
    )
    return result.to_dict()


@app.get("/query")
def query_get(
    text: str = Query(..., min_length=1),
    location: Optional[str] = None,
    top_k: int = Query(5, ge=1, le=50),
    use_llm: bool = False,
    use_rerank: bool = False,
) -> dict[str, Any]:
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    eng = get_engine()
    result = eng.query(
        text=text,
        location=location,
        top_k=top_k,
        use_llm=use_llm,
        use_rerank=use_rerank,
    )
    return result.to_dict()


@app.post("/ingest")
def ingest(force: bool = False) -> dict[str, Any]:
    # Clear cached engine so next call rebuilds
    get_engine.cache_clear()
    root = _project_root()
    embedder_name = os.environ.get("PARRTS_EMBEDDER", "hash").lower()
    embedder = HashingEmbedder() if embedder_name == "hash" else resolve_embedder(embedder_name)
    engine = PartsRAGEngine(root=root, embedder=embedder)
    info = engine.build(force_inventory=force)
    get_engine.cache_clear()
    return {"ok": True, "action": "ingest", **info}
