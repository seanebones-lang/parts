"""
Parts service for managing parts catalog and operations.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.models.parts_catalog import PartsCatalog
from app.models.inventory import Inventory
from app.models.location import Location
from app.services.vector_service import VectorService


class PartsService:
    """Service for managing parts catalog operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_service = VectorService()
    
    async def get_part(self, part_id: int) -> Optional[Dict[str, Any]]:
        """Get a single part by ID."""
        query = select(PartsCatalog).where(PartsCatalog.id == part_id)
        result = await self.db.execute(query)
        part = result.scalar_one_or_none()
        
        if part:
            return self._serialize_part(part)
        return None
    
    async def get_parts(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get parts with optional filters."""
        query = select(PartsCatalog)
        
        # Apply filters
        if filters:
            if filters.get("category"):
                query = query.where(PartsCatalog.category == filters["category"])
            
            if filters.get("manufacturer"):
                query = query.where(PartsCatalog.manufacturer == filters["manufacturer"])
            
            if filters.get("make"):
                query = query.where(PartsCatalog.make == filters["make"])
            
            if filters.get("is_active") is not None:
                query = query.where(PartsCatalog.is_active == filters["is_active"])
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        parts = result.scalars().all()
        
        return [self._serialize_part(part) for part in parts]
    
    async def search_parts(
        self,
        search_term: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search parts using text search."""
        query = select(PartsCatalog).where(
            or_(
                PartsCatalog.part_name.ilike(f"%{search_term}%"),
                PartsCatalog.description.ilike(f"%{search_term}%"),
                PartsCatalog.part_number.ilike(f"%{search_term}%"),
                PartsCatalog.manufacturer.ilike(f"%{search_term}%")
            )
        )
        
        # Apply additional filters
        if filters:
            if filters.get("category"):
                query = query.where(PartsCatalog.category == filters["category"])
            
            if filters.get("make"):
                query = query.where(PartsCatalog.make == filters["make"])
        
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        parts = result.scalars().all()
        
        return [self._serialize_part(part) for part in parts]
    
    async def get_part_inventory(self, part_id: int, location_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get inventory for a part across locations."""
        query = select(Inventory).where(Inventory.part_id == part_id)
        
        if location_id:
            query = query.where(Inventory.location_id == location_id)
        
        query = query.options(selectinload(Inventory.location))
        
        result = await self.db.execute(query)
        inventory_items = result.scalars().all()
        
        inventory_data = []
        for item in inventory_items:
            item_data = {
                "id": item.id,
                "location_id": item.location_id,
                "location_name": item.location.name if item.location else None,
                "quantity_available": item.quantity_available,
                "quantity_reserved": item.quantity_reserved,
                "quantity_on_order": item.quantity_on_order,
                "total_quantity": item.total_quantity,
                "reorder_point": item.reorder_point,
                "reorder_quantity": item.reorder_quantity,
                "needs_reorder": item.needs_reorder,
                "bin_location": item.bin_location,
                "cost": float(item.cost) if item.cost else None,
                "last_counted": item.last_counted.isoformat() if item.last_counted else None
            }
            inventory_data.append(item_data)
        
        return inventory_data
    
    async def create_part(self, part_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new part."""
        part = PartsCatalog(**part_data)
        self.db.add(part)
        await self.db.commit()
        await self.db.refresh(part)
        
        # Index for semantic search
        await self.vector_service.index_part(self._serialize_part(part))
        
        return self._serialize_part(part)
    
    async def update_part(self, part_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing part."""
        query = select(PartsCatalog).where(PartsCatalog.id == part_id)
        result = await self.db.execute(query)
        part = result.scalar_one_or_none()
        
        if not part:
            return None
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(part, field):
                setattr(part, field, value)
        
        await self.db.commit()
        await self.db.refresh(part)
        
        # Re-index for semantic search
        await self.vector_service.index_part(self._serialize_part(part))
        
        return self._serialize_part(part)
    
    async def get_parts_by_vehicle(
        self,
        make: str,
        model: str,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get parts compatible with a specific vehicle."""
        query = select(PartsCatalog).where(
            and_(
                PartsCatalog.make == make,
                PartsCatalog.model == model
            )
        )
        
        if year:
            query = query.where(
                and_(
                    or_(PartsCatalog.year_from.is_(None), PartsCatalog.year_from <= year),
                    or_(PartsCatalog.year_to.is_(None), PartsCatalog.year_to >= year)
                )
            )
        
        result = await self.db.execute(query)
        parts = result.scalars().all()
        
        return [self._serialize_part(part) for part in parts]
    
    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        query = select(PartsCatalog.category).distinct().where(PartsCatalog.is_active == True)
        result = await self.db.execute(query)
        categories = [row[0] for row in result.fetchall()]
        return categories
    
    async def get_manufacturers(self) -> List[str]:
        """Get all unique manufacturers."""
        query = select(PartsCatalog.manufacturer).distinct().where(PartsCatalog.is_active == True)
        result = await self.db.execute(query)
        manufacturers = [row[0] for row in result.fetchall()]
        return manufacturers
    
    async def get_makes(self) -> List[str]:
        """Get all unique vehicle makes."""
        query = select(PartsCatalog.make).distinct().where(
            and_(PartsCatalog.make.isnot(None), PartsCatalog.is_active == True)
        )
        result = await self.db.execute(query)
        makes = [row[0] for row in result.fetchall()]
        return makes
    
    async def get_models(self, make: Optional[str] = None) -> List[str]:
        """Get all unique vehicle models, optionally filtered by make."""
        query = select(PartsCatalog.model).distinct().where(
            and_(PartsCatalog.model.isnot(None), PartsCatalog.is_active == True)
        )
        
        if make:
            query = query.where(PartsCatalog.make == make)
        
        result = await self.db.execute(query)
        models = [row[0] for row in result.fetchall()]
        return models
    
    async def bulk_import_parts(self, parts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk import parts from external data."""
        results = {
            "total": len(parts_data),
            "created": 0,
            "updated": 0,
            "errors": []
        }
        
        for part_data in parts_data:
            try:
                # Check if part already exists
                existing_part = await self._find_existing_part(part_data)
                
                if existing_part:
                    # Update existing part
                    await self.update_part(existing_part["id"], part_data)
                    results["updated"] += 1
                else:
                    # Create new part
                    await self.create_part(part_data)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append({
                    "part_data": part_data,
                    "error": str(e)
                })
        
        return results
    
    async def _find_existing_part(self, part_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find existing part by part number."""
        part_number = part_data.get("part_number")
        if not part_number:
            return None
        
        query = select(PartsCatalog).where(PartsCatalog.part_number == part_number)
        result = await self.db.execute(query)
        part = result.scalar_one_or_none()
        
        if part:
            return self._serialize_part(part)
        return None
    
    def _serialize_part(self, part: PartsCatalog) -> Dict[str, Any]:
        """Serialize part model to dictionary."""
        return {
            "id": part.id,
            "part_number": part.part_number,
            "manufacturer": part.manufacturer,
            "part_name": part.part_name,
            "description": part.description,
            "category": part.category,
            "subcategory": part.subcategory,
            "make": part.make,
            "model": part.model,
            "year_from": part.year_from,
            "year_to": part.year_to,
            "engine": part.engine,
            "transmission": part.transmission,
            "body_style": part.body_style,
            "compatible_parts": part.compatible_parts,
            "msrp": float(part.msrp) if part.msrp else None,
            "cost": float(part.cost) if part.cost else None,
            "weight": float(part.weight) if part.weight else None,
            "dimensions": part.dimensions,
            "is_active": part.is_active,
            "created_at": part.created_at.isoformat(),
            "updated_at": part.updated_at.isoformat()
        }
