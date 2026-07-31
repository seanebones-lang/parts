"""
Customer endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user_if_production
from app.core.database import get_db
from app.models.user import User

router = APIRouter()


@router.get("/")
async def get_customers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all customers."""
    return {"message": "Customer endpoints - coming soon"}


@router.get("/{customer_id}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get customer by ID."""
    return {"message": f"Get customer {customer_id} - coming soon"}


@router.post("/")
async def create_customer(
    customer_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Create customer (stub).

    Auth: open when AUTH_MODE=demo; JWT required when AUTH_MODE=production.
    """
    _ = current_user
    return {
        "success": True,
        "message": "Customer create - coming soon",
        "customer": customer_data,
    }


@router.put("/{customer_id}")
async def update_customer(
    customer_id: int,
    customer_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Update customer (stub)."""
    _ = current_user
    return {
        "success": True,
        "message": f"Customer {customer_id} update - coming soon",
        "customer": customer_data,
    }


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Delete customer (stub)."""
    _ = current_user
    return {
        "success": True,
        "message": f"Customer {customer_id} delete - coming soon",
    }
