"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter
from .endpoints import health, locations, customers, parts, orders, emails, ai_agents, inventory, payments, analytics, deployment, rollout, auth, barcode, serialized

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(barcode.router, prefix="/barcode", tags=["barcode-scanning"])
api_router.include_router(serialized.router, prefix="/serialized", tags=["serialized-tracking"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(parts.router, prefix="/parts", tags=["parts"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(deployment.router, prefix="/deployment", tags=["deployment"])
api_router.include_router(rollout.router, prefix="/rollout", tags=["rollout"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(ai_agents.router, prefix="/ai-agents", tags=["ai-agents"])
