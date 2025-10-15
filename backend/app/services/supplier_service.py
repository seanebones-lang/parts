"""
Supplier service for managing external parts suppliers.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.supplier import Supplier, SupplierPart


class SupplierService:
    """Service for managing external parts suppliers."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_active_suppliers(self) -> List[Dict[str, Any]]:
        """Get all active suppliers."""
        try:
            query = select(Supplier).where(Supplier.is_active == True)
            result = await self.db.execute(query)
            suppliers = result.scalars().all()
            
            return [
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "website": supplier.website,
                    "api_endpoint": supplier.api_endpoint,
                    "supports_automated_ordering": supplier.supports_automated_ordering,
                    "contact_info": supplier.contact_info,
                    "rating": supplier.rating,
                    "delivery_time_days": supplier.delivery_time_days,
                    "minimum_order": float(supplier.minimum_order) if supplier.minimum_order else None,
                    "last_updated": supplier.last_updated.isoformat() if supplier.last_updated else None
                }
                for supplier in suppliers
            ]
            
        except Exception as e:
            print(f"Error getting active suppliers: {e}")
            return []
    
    async def get_supplier(self, supplier_id: int) -> Optional[Dict[str, Any]]:
        """Get supplier by ID."""
        try:
            query = select(Supplier).where(Supplier.id == supplier_id)
            result = await self.db.execute(query)
            supplier = result.scalar_one_or_none()
            
            if supplier:
                return {
                    "id": supplier.id,
                    "name": supplier.name,
                    "website": supplier.website,
                    "api_endpoint": supplier.api_endpoint,
                    "supports_automated_ordering": supplier.supports_automated_ordering,
                    "contact_info": supplier.contact_info,
                    "rating": supplier.rating,
                    "delivery_time_days": supplier.delivery_time_days,
                    "minimum_order": float(supplier.minimum_order) if supplier.minimum_order else None,
                    "last_updated": supplier.last_updated.isoformat() if supplier.last_updated else None
                }
            return None
            
        except Exception as e:
            print(f"Error getting supplier {supplier_id}: {e}")
            return None
    
    async def search_supplier_parts(
        self,
        supplier_id: int,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        vehicle_info: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for parts in supplier catalog."""
        try:
            query = select(SupplierPart).where(SupplierPart.supplier_id == supplier_id)
            
            # Add search filters
            conditions = []
            
            if part_number:
                conditions.append(
                    or_(
                        SupplierPart.supplier_part_number.ilike(f"%{part_number}%"),
                        SupplierPart.oem_part_number.ilike(f"%{part_number}%")
                    )
                )
            
            if part_name:
                conditions.append(SupplierPart.part_name.ilike(f"%{part_name}%"))
            
            if vehicle_info:
                make = vehicle_info.get("make")
                model = vehicle_info.get("model")
                year = vehicle_info.get("year")
                
                if make:
                    conditions.append(SupplierPart.compatible_vehicles.ilike(f"%{make}%"))
                if model:
                    conditions.append(SupplierPart.compatible_vehicles.ilike(f"%{model}%"))
                if year:
                    conditions.append(SupplierPart.compatible_vehicles.ilike(f"%{year}%"))
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await self.db.execute(query)
            parts = result.scalars().all()
            
            return [
                {
                    "id": part.id,
                    "supplier_id": part.supplier_id,
                    "supplier_part_number": part.supplier_part_number,
                    "oem_part_number": part.oem_part_number,
                    "part_name": part.part_name,
                    "description": part.description,
                    "price": float(part.price) if part.price else None,
                    "availability": part.availability,
                    "delivery_days": part.delivery_days,
                    "minimum_quantity": part.minimum_quantity,
                    "compatible_vehicles": part.compatible_vehicles,
                    "last_updated": part.last_updated.isoformat() if part.last_updated else None
                }
                for part in parts
            ]
            
        except Exception as e:
            print(f"Error searching supplier parts: {e}")
            return []
    
    async def update_part_availability(
        self,
        supplier_id: int,
        part_number: str,
        availability_data: Dict[str, Any]
    ) -> bool:
        """Update part availability data."""
        try:
            query = select(SupplierPart).where(
                and_(
                    SupplierPart.supplier_id == supplier_id,
                    or_(
                        SupplierPart.supplier_part_number == part_number,
                        SupplierPart.oem_part_number == part_number
                    )
                )
            )
            result = await self.db.execute(query)
            part = result.scalar_one_or_none()
            
            if part:
                part.availability = availability_data.get("availability", part.availability)
                part.price = availability_data.get("price", part.price)
                part.delivery_days = availability_data.get("delivery_days", part.delivery_days)
                part.last_updated = datetime.utcnow()
                
                await self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            await self.db.rollback()
            print(f"Error updating part availability: {e}")
            return False
    
    async def record_supplier_order(
        self,
        supplier_id: int,
        order_data: Dict[str, Any],
        parts: List[Dict[str, Any]]
    ) -> bool:
        """Record a supplier order."""
        try:
            # This would create a SupplierOrder record
            # For now, just log the order
            print(f"Recording supplier order for supplier {supplier_id}")
            print(f"Order data: {order_data}")
            print(f"Parts: {parts}")
            
            return True
            
        except Exception as e:
            print(f"Error recording supplier order: {e}")
            return False
    
    async def update_supplier_timestamp(
        self,
        supplier_id: int,
        last_updated: Optional[str] = None
    ) -> bool:
        """Update supplier last_updated timestamp."""
        try:
            query = select(Supplier).where(Supplier.id == supplier_id)
            result = await self.db.execute(query)
            supplier = result.scalar_one_or_none()
            
            if supplier:
                supplier.last_updated = datetime.fromisoformat(last_updated) if last_updated else datetime.utcnow()
                await self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            await self.db.rollback()
            print(f"Error updating supplier timestamp: {e}")
            return False
    
    async def save_scraped_parts(
        self,
        supplier_id: int,
        parts: List[Dict[str, Any]]
    ) -> int:
        """Save scraped parts to database."""
        try:
            saved_count = 0
            
            for part_data in parts:
                # Check if part already exists
                existing_query = select(SupplierPart).where(
                    and_(
                        SupplierPart.supplier_id == supplier_id,
                        SupplierPart.supplier_part_number == part_data.get("supplier_part_number")
                    )
                )
                existing_result = await self.db.execute(existing_query)
                existing_part = existing_result.scalar_one_or_none()
                
                if existing_part:
                    # Update existing part
                    existing_part.part_name = part_data.get("part_name", existing_part.part_name)
                    existing_part.description = part_data.get("description", existing_part.description)
                    existing_part.price = part_data.get("price", existing_part.price)
                    existing_part.availability = part_data.get("availability", existing_part.availability)
                    existing_part.delivery_days = part_data.get("delivery_days", existing_part.delivery_days)
                    existing_part.last_updated = datetime.utcnow()
                else:
                    # Create new part
                    new_part = SupplierPart(
                        supplier_id=supplier_id,
                        supplier_part_number=part_data.get("supplier_part_number", ""),
                        oem_part_number=part_data.get("oem_part_number", ""),
                        part_name=part_data.get("part_name", ""),
                        description=part_data.get("description", ""),
                        price=part_data.get("price"),
                        availability=part_data.get("availability", "unknown"),
                        delivery_days=part_data.get("delivery_days"),
                        minimum_quantity=part_data.get("minimum_quantity", 1),
                        compatible_vehicles=part_data.get("compatible_vehicles", ""),
                        last_updated=datetime.utcnow()
                    )
                    self.db.add(new_part)
                
                saved_count += 1
            
            await self.db.commit()
            return saved_count
            
        except Exception as e:
            await self.db.rollback()
            print(f"Error saving scraped parts: {e}")
            return 0
    
    async def get_supplier_statistics(self) -> Dict[str, Any]:
        """Get supplier statistics and performance metrics."""
        try:
            # Get total suppliers
            total_suppliers_query = select(Supplier)
            total_suppliers_result = await self.db.execute(total_suppliers_query)
            total_suppliers = len(total_suppliers_result.scalars().all())
            
            # Get active suppliers
            active_suppliers_query = select(Supplier).where(Supplier.is_active == True)
            active_suppliers_result = await self.db.execute(active_suppliers_query)
            active_suppliers = len(active_suppliers_result.scalars().all())
            
            # Get total parts cataloged
            total_parts_query = select(SupplierPart)
            total_parts_result = await self.db.execute(total_parts_query)
            total_parts = len(total_parts_result.scalars().all())
            
            # Get parts updated recently (last 7 days)
            from datetime import timedelta
            recent_date = datetime.utcnow() - timedelta(days=7)
            recent_parts_query = select(SupplierPart).where(SupplierPart.last_updated >= recent_date)
            recent_parts_result = await self.db.execute(recent_parts_query)
            recent_parts = len(recent_parts_result.scalars().all())
            
            return {
                "total_suppliers": total_suppliers,
                "active_suppliers": active_suppliers,
                "total_parts_cataloged": total_parts,
                "recently_updated_parts": recent_parts,
                "catalog_freshness_percent": (recent_parts / total_parts * 100) if total_parts > 0 else 0
            }
            
        except Exception as e:
            print(f"Error getting supplier statistics: {e}")
            return {
                "total_suppliers": 0,
                "active_suppliers": 0,
                "total_parts_cataloged": 0,
                "recently_updated_parts": 0,
                "catalog_freshness_percent": 0
            }
    
    async def create_supplier(
        self,
        name: str,
        website: str,
        api_endpoint: Optional[str] = None,
        supports_automated_ordering: bool = False,
        contact_info: Optional[Dict[str, str]] = None,
        rating: float = 3.0,
        delivery_time_days: int = 5,
        minimum_order: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create a new supplier."""
        try:
            supplier = Supplier(
                name=name,
                website=website,
                api_endpoint=api_endpoint,
                supports_automated_ordering=supports_automated_ordering,
                contact_info=str(contact_info) if contact_info else None,
                rating=rating,
                delivery_time_days=delivery_time_days,
                minimum_order=minimum_order,
                is_active=True,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            
            self.db.add(supplier)
            await self.db.commit()
            await self.db.refresh(supplier)
            
            return {
                "success": True,
                "supplier": {
                    "id": supplier.id,
                    "name": supplier.name,
                    "website": supplier.website,
                    "api_endpoint": supplier.api_endpoint,
                    "supports_automated_ordering": supplier.supports_automated_ordering,
                    "rating": supplier.rating,
                    "delivery_time_days": supplier.delivery_time_days,
                    "minimum_order": float(supplier.minimum_order) if supplier.minimum_order else None
                }
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def update_supplier(
        self,
        supplier_id: int,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update supplier information."""
        try:
            query = select(Supplier).where(Supplier.id == supplier_id)
            result = await self.db.execute(query)
            supplier = result.scalar_one_or_none()
            
            if not supplier:
                return {"success": False, "error": "Supplier not found"}
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(supplier, field):
                    setattr(supplier, field, value)
            
            supplier.last_updated = datetime.utcnow()
            
            await self.db.commit()
            
            return {
                "success": True,
                "supplier": {
                    "id": supplier.id,
                    "name": supplier.name,
                    "website": supplier.website,
                    "api_endpoint": supplier.api_endpoint,
                    "supports_automated_ordering": supplier.supports_automated_ordering,
                    "rating": supplier.rating,
                    "delivery_time_days": supplier.delivery_time_days,
                    "minimum_order": float(supplier.minimum_order) if supplier.minimum_order else None
                }
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
