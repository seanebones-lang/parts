"""
Location service for business logic.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate


class LocationService:
    """Location service for managing dealership locations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_locations(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Location]:
        """Get all locations with pagination."""
        query = select(Location).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_location(self, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        query = select(Location).where(Location.id == location_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_location(self, location_data: LocationCreate) -> Location:
        """Create new location."""
        location = Location(**location_data.dict())
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        return location
    
    async def update_location(
        self, 
        location_id: int, 
        location_data: LocationUpdate
    ) -> Optional[Location]:
        """Update location."""
        location = await self.get_location(location_id)
        if not location:
            return None
        
        update_data = location_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(location, field, value)
        
        await self.db.commit()
        await self.db.refresh(location)
        return location
    
    async def delete_location(self, location_id: int) -> bool:
        """Delete location."""
        location = await self.get_location(location_id)
        if not location:
            return False
        
        await self.db.delete(location)
        await self.db.commit()
        return True
