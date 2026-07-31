"""
Email processing endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user_if_production
from app.core.database import get_db
from app.models.user import User

router = APIRouter()


@router.get("/")
async def get_emails(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all emails."""
    return {"message": "Email endpoints - coming soon"}


@router.get("/{email_id}")
async def get_email(
    email_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get email by ID."""
    return {"message": f"Get email {email_id} - coming soon"}


@router.post("/process")
async def process_emails(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Trigger email processing."""
    _ = current_user
    return {"message": "Process emails - coming soon"}
