"""
Inventory service for managing stock across locations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.models.inventory import Inventory
from app.models.parts_catalog import PartsCatalog
from app.models.location import Location
from app.models.order_item import OrderItem
from app.models.order import Order


class InventoryService:
    """Service for managing inventory operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_location_inventory(self, location_id: int) -> List[Dict[str, Any]]:
        """Get inventory for a specific location."""
        query = select(Inventory).where(Inventory.location_id == location_id)
        query = query.options(
            selectinload(Inventory.part),
            selectinload(Inventory.location)
        )
        
        result = await self.db.execute(query)
        inventory_items = result.scalars().all()
        
        return [self._serialize_inventory_item(item) for item in inventory_items]
    
    async def get_part_inventory(self, part_id: int, location_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get inventory for a part across locations."""
        query = select(Inventory).where(Inventory.part_id == part_id)
        
        if location_id:
            query = query.where(Inventory.location_id == location_id)
        
        query = query.options(
            selectinload(Inventory.part),
            selectinload(Inventory.location)
        )
        
        result = await self.db.execute(query)
        inventory_items = result.scalars().all()
        
        return [self._serialize_inventory_item(item) for item in inventory_items]
    
    async def update_inventory(
        self,
        part_id: int,
        location_id: int,
        quantity_change: int,
        operation: str = "adjustment"
    ) -> Dict[str, Any]:
        """Update inventory quantity."""
        query = select(Inventory).where(
            and_(
                Inventory.part_id == part_id,
                Inventory.location_id == location_id
            )
        )
        
        result = await self.db.execute(query)
        inventory_item = result.scalar_one_or_none()
        
        if not inventory_item:
            return {"success": False, "error": "Inventory item not found"}
        
        # Update quantity
        old_quantity = inventory_item.quantity_available
        new_quantity = old_quantity + quantity_change
        
        if new_quantity < 0:
            return {"success": False, "error": "Insufficient inventory"}
        
        inventory_item.quantity_available = new_quantity
        inventory_item.last_counted = datetime.utcnow()
        
        await self.db.commit()
        
        return {
            "success": True,
            "part_id": part_id,
            "location_id": location_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "operation": operation
        }
    
    async def reserve_inventory(
        self,
        part_id: int,
        location_id: int,
        quantity: int,
        order_id: int
    ) -> Dict[str, Any]:
        """Reserve inventory for an order."""
        query = select(Inventory).where(
            and_(
                Inventory.part_id == part_id,
                Inventory.location_id == location_id
            )
        )
        
        result = await self.db.execute(query)
        inventory_item = result.scalar_one_or_none()
        
        if not inventory_item:
            return {"success": False, "error": "Inventory item not found"}
        
        if inventory_item.quantity_available < quantity:
            return {"success": False, "error": "Insufficient inventory"}
        
        # Reserve inventory
        inventory_item.quantity_available -= quantity
        inventory_item.quantity_reserved += quantity
        
        await self.db.commit()
        
        return {
            "success": True,
            "part_id": part_id,
            "location_id": location_id,
            "quantity_reserved": quantity,
            "order_id": order_id,
            "remaining_available": inventory_item.quantity_available
        }
    
    async def release_reservation(
        self,
        part_id: int,
        location_id: int,
        quantity: int
    ) -> Dict[str, Any]:
        """Release reserved inventory."""
        query = select(Inventory).where(
            and_(
                Inventory.part_id == part_id,
                Inventory.location_id == location_id
            )
        )
        
        result = await self.db.execute(query)
        inventory_item = result.scalar_one_or_none()
        
        if not inventory_item:
            return {"success": False, "error": "Inventory item not found"}
        
        # Release reservation
        inventory_item.quantity_reserved -= quantity
        inventory_item.quantity_available += quantity
        
        await self.db.commit()
        
        return {
            "success": True,
            "part_id": part_id,
            "location_id": location_id,
            "quantity_released": quantity
        }
    
    async def receive_inventory(
        self,
        part_id: int,
        location_id: int,
        quantity: int,
        cost: Optional[float] = None,
        batch_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process received inventory."""
        query = select(Inventory).where(
            and_(
                Inventory.part_id == part_id,
                Inventory.location_id == location_id
            )
        )
        
        result = await self.db.execute(query)
        inventory_item = result.scalar_one_or_none()
        
        if not inventory_item:
            return {"success": False, "error": "Inventory item not found"}
        
        # Update inventory
        old_quantity = inventory_item.quantity_available
        inventory_item.quantity_available += quantity
        inventory_item.quantity_on_order = max(0, inventory_item.quantity_on_order - quantity)
        
        if cost:
            inventory_item.cost = cost
        
        inventory_item.last_counted = datetime.utcnow()
        
        await self.db.commit()
        
        return {
            "success": True,
            "part_id": part_id,
            "location_id": location_id,
            "quantity_received": quantity,
            "old_quantity": old_quantity,
            "new_quantity": inventory_item.quantity_available,
            "batch_number": batch_number
        }
    
    async def create_reorder(
        self,
        part_id: int,
        location_id: int,
        quantity: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a reorder for low stock item."""
        query = select(Inventory).where(
            and_(
                Inventory.part_id == part_id,
                Inventory.location_id == location_id
            )
        )
        
        result = await self.db.execute(query)
        inventory_item = result.scalar_one_or_none()
        
        if not inventory_item:
            return None
        
        # Determine reorder quantity
        reorder_quantity = quantity or inventory_item.reorder_quantity
        if reorder_quantity <= 0:
            return None
        
        # Update on-order quantity
        inventory_item.quantity_on_order += reorder_quantity
        
        await self.db.commit()
        
        return {
            "part_id": part_id,
            "location_id": location_id,
            "reorder_quantity": reorder_quantity,
            "estimated_cost": float(inventory_item.cost * reorder_quantity) if inventory_item.cost else 0,
            "reorder_date": datetime.utcnow().isoformat()
        }
    
    async def auto_reorder(self, location_id: int) -> List[Dict[str, Any]]:
        """Automatically reorder items below reorder point."""
        query = select(Inventory).where(
            and_(
                Inventory.location_id == location_id,
                Inventory.quantity_available <= Inventory.reorder_point,
                Inventory.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        low_stock_items = result.scalars().all()
        
        reorders = []
        for item in low_stock_items:
            reorder = await self.create_reorder(
                part_id=item.part_id,
                location_id=item.location_id,
                quantity=item.reorder_quantity
            )
            if reorder:
                reorders.append(reorder)
        
        return reorders
    
    async def validate_transfer(
        self,
        part_id: int,
        from_location_id: int,
        quantity: int
    ) -> Dict[str, Any]:
        """Validate stock transfer."""
        query = select(Inventory).where(
            and_(
                Inventory.part_id == part_id,
                Inventory.location_id == from_location_id
            )
        )
        
        result = await self.db.execute(query)
        inventory_item = result.scalar_one_or_none()
        
        if not inventory_item:
            return {"valid": False, "error": "Part not found at source location"}
        
        if inventory_item.quantity_available < quantity:
            return {"valid": False, "error": "Insufficient stock at source location"}
        
        return {"valid": True}
    
    async def transfer_stock(
        self,
        part_id: int,
        from_location_id: int,
        to_location_id: int,
        quantity: int
    ) -> Dict[str, Any]:
        """Transfer stock between locations."""
        # Validate transfer
        validation = await self.validate_transfer(part_id, from_location_id, quantity)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        
        # Remove from source location
        source_result = await self.update_inventory(
            part_id=part_id,
            location_id=from_location_id,
            quantity_change=-quantity,
            operation="transfer_out"
        )
        
        if not source_result["success"]:
            return source_result
        
        # Add to destination location
        dest_result = await self.update_inventory(
            part_id=part_id,
            location_id=to_location_id,
            quantity_change=quantity,
            operation="transfer_in"
        )
        
        if not dest_result["success"]:
            # Rollback source change
            await self.update_inventory(
                part_id=part_id,
                location_id=from_location_id,
                quantity_change=quantity,
                operation="rollback"
            )
            return dest_result
        
        return {
            "success": True,
            "part_id": part_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "quantity": quantity,
            "transfer_date": datetime.utcnow().isoformat()
        }
    
    async def generate_inventory_report(self, location_id: int) -> Dict[str, Any]:
        """Generate comprehensive inventory report."""
        # Get all inventory for location
        inventory_items = await self.get_location_inventory(location_id)
        
        # Calculate metrics
        total_items = len(inventory_items)
        in_stock_items = len([item for item in inventory_items if item["quantity_available"] > 0])
        out_of_stock_items = len([item for item in inventory_items if item["quantity_available"] == 0])
        low_stock_items = len([item for item in inventory_items if item["needs_reorder"]])
        
        # Calculate total value
        total_value = sum(
            item["quantity_available"] * (item["cost"] or 0)
            for item in inventory_items
        )
        
        # Find overstock items (quantity > 2x reorder quantity)
        overstock_items = [
            item for item in inventory_items
            if item["quantity_available"] > item["reorder_quantity"] * 2
        ]
        
        # Find fast movers (items with high turnover - simplified)
        fast_movers = [
            item for item in inventory_items
            if item["quantity_available"] < item["reorder_quantity"] * 0.5
            and item["quantity_available"] > 0
        ]
        
        return {
            "location_id": location_id,
            "report_date": datetime.utcnow().isoformat(),
            "summary": {
                "total_items": total_items,
                "in_stock": in_stock_items,
                "out_of_stock": out_of_stock_items,
                "low_stock": low_stock_items,
                "total_value": total_value
            },
            "overstock_items": overstock_items,
            "fast_movers": fast_movers,
            "detailed_inventory": inventory_items
        }
    
    def _serialize_inventory_item(self, item: Inventory) -> Dict[str, Any]:
        """Serialize inventory item to dictionary."""
        return {
            "id": item.id,
            "part_id": item.part_id,
            "location_id": item.location_id,
            "location_name": item.location.name if item.location else None,
            "part_number": item.part.part_number if item.part else None,
            "part_name": item.part.part_name if item.part else None,
            "quantity_available": item.quantity_available,
            "quantity_reserved": item.quantity_reserved,
            "quantity_on_order": item.quantity_on_order,
            "total_quantity": item.total_quantity,
            "reorder_point": item.reorder_point,
            "reorder_quantity": item.reorder_quantity,
            "needs_reorder": item.needs_reorder,
            "bin_location": item.bin_location,
            "cost": float(item.cost) if item.cost else None,
            "is_active": item.is_active,
            "last_counted": item.last_counted.isoformat() if item.last_counted else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat()
        }
