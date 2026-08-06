"""
Main API router for v1 endpoints.

Each endpoint module is soft-imported so a single broken module does not
take down the entire /api/v1 surface.
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()
_loaded: list[str] = []
_failed: dict[str, str] = {}


def _include(name: str, module_path: str, prefix: str, tags: list[str]) -> None:
    """Import module_path and include its `router` if present."""
    import importlib

    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, "router", None)
        if router is None:
            raise AttributeError(f"{module_path} has no `router`")
        api_router.include_router(router, prefix=prefix, tags=tags)
        _loaded.append(name)
    except Exception as exc:  # pragma: no cover - exercised at import time
        _failed[name] = f"{type(exc).__name__}: {exc}"
        print(f"Warning: /api/v1{prefix} not loaded ({name}): {exc}")


# Core identity / inventory
_include("auth", "app.api.v1.endpoints.auth", "/auth", ["authentication"])
_include("health", "app.api.v1.endpoints.health", "/health", ["health"])
_include("locations", "app.api.v1.endpoints.locations", "/locations", ["locations"])
_include("customers", "app.api.v1.endpoints.customers", "/customers", ["customers"])
_include("parts", "app.api.v1.endpoints.parts", "/parts", ["parts"])
_include("inventory", "app.api.v1.endpoints.inventory", "/inventory", ["inventory"])
_include("orders", "app.api.v1.endpoints.orders", "/orders", ["orders"])
_include("payments", "app.api.v1.endpoints.payments", "/payments", ["payments"])
_include("shipping", "app.api.v1.endpoints.shipping", "/shipping", ["shipping"])
_include("analytics", "app.api.v1.endpoints.analytics", "/analytics", ["analytics"])
_include("emails", "app.api.v1.endpoints.emails", "/emails", ["emails"])
_include("ai_agents", "app.api.v1.endpoints.ai_agents", "/ai-agents", ["ai-agents"])
_include("barcode", "app.api.v1.endpoints.barcode", "/barcode", ["barcode-scanning"])
_include("serialized", "app.api.v1.endpoints.serialized", "/serialized", ["serialized-tracking"])
_include("deployment", "app.api.v1.endpoints.deployment", "/deployment", ["deployment"])
_include("rollout", "app.api.v1.endpoints.rollout", "/rollout", ["rollout"])
_include("dms", "app.api.v1.endpoints.dms", "/dms", ["dms"])
_include("system", "app.api.v1.endpoints.system", "/system", ["system"])
_include("automation", "app.api.v1.endpoints.automation", "/automation", ["automation"])


def router_status() -> dict:
    """Report which v1 sub-routers loaded."""
    return {
        "loaded": list(_loaded),
        "failed": dict(_failed),
        "loaded_count": len(_loaded),
        "failed_count": len(_failed),
        "ok": len(_failed) == 0 and len(_loaded) > 0,
    }
