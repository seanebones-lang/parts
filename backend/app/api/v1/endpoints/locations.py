"""
Location endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user_if_production
from app.core.database import get_db
from app.models.user import User
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.services.location_service import LocationService

router = APIRouter()


@router.get("/", response_model=List[LocationResponse])
async def get_locations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get all locations."""
    service = LocationService(db)
    return await service.get_locations(skip=skip, limit=limit)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get location by ID."""
    service = LocationService(db)
    location = await service.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.post("/", response_model=LocationResponse)
async def create_location(
    location: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Create new location."""
    _ = current_user
    service = LocationService(db)
    return await service.create_location(location)


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    location: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Update location."""
    _ = current_user
    service = LocationService(db)
    updated_location = await service.update_location(location_id, location)
    if not updated_location:
        raise HTTPException(status_code=404, detail="Location not found")
    return updated_location


@router.delete("/{location_id}")
async def delete_location(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Delete location."""
    _ = current_user
    service = LocationService(db)
    success = await service.delete_location(location_id)
    if not success:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"message": "Location deleted successfully"}
