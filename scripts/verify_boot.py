#!/usr/bin/env python3
"""
Backend + parrts boot smoke (no Postgres required for core paths).

Usage:
  PYTHONPATH=backend:src python scripts/verify_boot.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "backend"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)


def main() -> int:
    report: dict = {"ok": True, "checks": {}}

    # config
    try:
        from app.core.config import settings

        report["checks"]["config"] = {
            "ok": True,
            "version": settings.VERSION,
            "auth_mode": settings.AUTH_MODE,
            "pgvector_enabled": bool(getattr(settings, "PGVECTOR_ENABLED", False)),
        }
    except Exception as exc:
        report["ok"] = False
        report["checks"]["config"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # api router soft-load
    try:
        from app.api.v1 import api as api_mod

        st = api_mod.router_status()
        report["checks"]["api_v1"] = {
            "ok": st.get("ok", False) or st.get("loaded_count", 0) > 0,
            **st,
        }
        if st.get("loaded_count", 0) == 0:
            report["ok"] = False
    except Exception as exc:
        report["ok"] = False
        report["checks"]["api_v1"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # main app
    try:
        import main as main_mod

        app = main_mod.app
        paths = sorted({getattr(r, "path", "") for r in app.routes})
        need = {"/", "/health", "/query", "/metrics"}
        missing = sorted(need - set(paths))
        report["checks"]["main_app"] = {
            "ok": not missing and main_mod.api_router is not None,
            "missing_core_paths": missing,
            "api_v1_mounted": main_mod.api_router is not None,
            "route_count": len(app.routes),
        }
        if missing or main_mod.api_router is None:
            report["ok"] = False
    except Exception as exc:
        report["ok"] = False
        report["checks"]["main_app"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # parrts core
    try:
        from parrts.embeddings import HashingEmbedder
        from parrts.engine import PartsRAGEngine

        eng = PartsRAGEngine(root=ROOT, embedder=HashingEmbedder())
        eng.ensure_ready()
        q = eng.query("brake pads for 2019 Honda Civic", use_llm=False, top_k=3)
        d = q.to_dict()
        report["checks"]["parrts"] = {
            "ok": bool(d.get("hits")),
            "hit_count": len(d.get("hits") or []),
            "traffic_light": (d.get("traffic_light") or {}).get("color"),
        }
        if not d.get("hits"):
            report["ok"] = False
    except Exception as exc:
        report["ok"] = False
        report["checks"]["parrts"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
