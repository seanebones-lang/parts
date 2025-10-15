"""
Order service for managing customer orders.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem, OrderStatus
from app.models.customer import Customer
from app.models.location import Location
from app.models.parts_catalog import PartsCatalog
from app.models.inventory import Inventory
from app.services.inventory_service import InventoryService
from app.services.pricing_service import PricingService


class OrderService:
    """Service for managing customer orders."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_service = InventoryService(db)
        self.pricing_service = PricingService(db)
    
    async def create_order(
        self,
        customer_id: int,
        location_id: int,
        items: List[Dict[str, Any]],
        shipping_address: Optional[Dict[str, str]] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new customer order."""
        try:
            # Generate order number
            order_number = await self._generate_order_number(location_id)
            
            # Validate customer and location
            customer = await self._get_customer(customer_id)
            location = await self._get_location(location_id)
            
            if not customer:
                return {"success": False, "error": "Customer not found"}
            
            if not location:
                return {"success": False, "error": "Location not found"}
            
            # Validate and price items
            order_items = []
            subtotal = 0.0
            
            for item in items:
                part_id = item.get("part_id")
                quantity = item.get("quantity", 1)
                
                # Get part pricing
                pricing = await self.pricing_service.get_part_pricing(
                    part_id=part_id,
                    location_id=location_id,
                    customer_type="retail",
                    quantity=quantity
                )
                
                if not pricing:
                    return {"success": False, "error": f"Part {part_id} not found or not available"}
                
                # Check availability
                if pricing["quantity_available"] < quantity:
                    return {"success": False, "error": f"Insufficient inventory for part {pricing['part_number']}"}
                
                order_items.append({
                    "part_id": part_id,
                    "quantity": quantity,
                    "unit_price": float(pricing["unit_price"]),
                    "total_price": float(pricing["unit_price"] * quantity)
                })
                
                subtotal += pricing["unit_price"] * quantity
            
            # Create order
            order = Order(
                order_number=order_number,
                customer_id=customer_id,
                location_id=location_id,
                status=OrderStatus.PENDING,
                subtotal=subtotal,
                tax_amount=0.0,  # Will be calculated separately
                shipping_amount=0.0,  # Will be calculated separately
                total_amount=subtotal,
                shipping_address=str(shipping_address) if shipping_address else None,
                notes=notes
            )
            
            self.db.add(order)
            await self.db.flush()  # Get the order ID
            
            # Create order items
            for item_data in order_items:
                order_item = OrderItem(
                    order_id=order.id,
                    part_id=item_data["part_id"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    total_price=item_data["total_price"]
                )
                self.db.add(order_item)
            
            await self.db.commit()
            
            return {
                "success": True,
                "order": self._serialize_order(order),
                "order_items": order_items
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID."""
        query = select(Order).where(Order.id == order_id)
        query = query.options(
            selectinload(Order.customer),
            selectinload(Order.location),
            selectinload(Order.items).selectinload(OrderItem.part)
        )
        
        result = await self.db.execute(query)
        order = result.scalar_one_or_none()
        
        if order:
            return self._serialize_order(order)
        return None
    
    async def get_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        customer_id: Optional[int] = None,
        location_id: Optional[int] = None,
        status: Optional[OrderStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get orders with optional filters."""
        query = select(Order)
        query = query.options(
            selectinload(Order.customer),
            selectinload(Order.location)
        )
        
        # Apply filters
        if customer_id:
            query = query.where(Order.customer_id == customer_id)
        
        if location_id:
            query = query.where(Order.location_id == location_id)
        
        if status:
            query = query.where(Order.status == status)
        
        query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
        
        result = await self.db.execute(query)
        orders = result.scalars().all()
        
        return [self._serialize_order(order) for order in orders]
    
    async def update_order_status(
        self,
        order_id: int,
        new_status: OrderStatus,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update order status."""
        try:
            query = select(Order).where(Order.id == order_id)
            result = await self.db.execute(query)
            order = result.scalar_one_or_none()
            
            if not order:
                return {"success": False, "error": "Order not found"}
            
            old_status = order.status
            order.status = new_status
            
            # Update timestamps based on status
            if new_status == OrderStatus.CONFIRMED:
                order.expected_ship_date = datetime.utcnow().replace(hour=23, minute=59, second=59)
            elif new_status == OrderStatus.SHIPPED:
                order.actual_ship_date = datetime.utcnow()
            elif new_status == OrderStatus.DELIVERED:
                order.delivery_date = datetime.utcnow()
            
            if notes:
                order.notes = (order.notes or "") + f"\n[{datetime.utcnow().isoformat()}] {notes}"
            
            await self.db.commit()
            
            return {
                "success": True,
                "order_id": order_id,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "updated_at": order.updated_at.isoformat()
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def reserve_inventory_for_order(self, order_id: int) -> Dict[str, Any]:
        """Reserve inventory for an order."""
        try:
            query = select(Order).where(Order.id == order_id)
            query = query.options(selectinload(Order.items))
            result = await self.db.execute(query)
            order = result.scalar_one_or_none()
            
            if not order:
                return {"success": False, "error": "Order not found"}
            
            reservations = []
            
            for item in order.items:
                # Reserve inventory
                reservation = await self.inventory_service.reserve_inventory(
                    part_id=item.part_id,
                    location_id=order.location_id,
                    quantity=item.quantity,
                    order_id=order_id
                )
                
                if not reservation["success"]:
                    # Release any previous reservations
                    await self._release_order_reservations(order_id)
                    return {"success": False, "error": reservation["error"]}
                
                reservations.append(reservation)
            
            # Update order status
            await self.update_order_status(order_id, OrderStatus.CONFIRMED, "Inventory reserved")
            
            return {
                "success": True,
                "order_id": order_id,
                "reservations": reservations
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cancel_order(self, order_id: int, reason: str) -> Dict[str, Any]:
        """Cancel an order and release reservations."""
        try:
            # Release inventory reservations
            await self._release_order_reservations(order_id)
            
            # Update order status
            result = await self.update_order_status(
                order_id=order_id,
                new_status=OrderStatus.CANCELLED,
                notes=f"Cancelled: {reason}"
            )
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_order_analytics(
        self,
        location_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get order analytics and metrics."""
        try:
            query = select(Order)
            
            if location_id:
                query = query.where(Order.location_id == location_id)
            
            if start_date:
                query = query.where(Order.created_at >= start_date)
            
            if end_date:
                query = query.where(Order.created_at <= end_date)
            
            result = await self.db.execute(query)
            orders = result.scalars().all()
            
            # Calculate metrics
            total_orders = len(orders)
            total_revenue = sum(order.total_amount for order in orders)
            
            status_counts = {}
            for order in orders:
                status = order.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Average order value
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            
            return {
                "total_orders": total_orders,
                "total_revenue": float(total_revenue),
                "average_order_value": float(avg_order_value),
                "status_breakdown": status_counts,
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _generate_order_number(self, location_id: int) -> str:
        """Generate unique order number."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        location_prefix = f"L{location_id:02d}"
        order_number = f"ORD{location_prefix}-{timestamp}"
        
        return order_number
    
    async def _get_customer(self, customer_id: int) -> Optional[Customer]:
        """Get customer by ID."""
        query = select(Customer).where(Customer.id == customer_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_location(self, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        query = select(Location).where(Location.id == location_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _release_order_reservations(self, order_id: int) -> None:
        """Release all inventory reservations for an order."""
        query = select(Order).where(Order.id == order_id)
        query = query.options(selectinload(Order.items))
        result = await self.db.execute(query)
        order = result.scalar_one_or_none()
        
        if order:
            for item in order.items:
                await self.inventory_service.release_reservation(
                    part_id=item.part_id,
                    location_id=order.location_id,
                    quantity=item.quantity
                )
    
    def _serialize_order(self, order: Order) -> Dict[str, Any]:
        """Serialize order to dictionary."""
        return {
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": order.customer.full_name if order.customer else None,
            "location_id": order.location_id,
            "location_name": order.location.name if order.location else None,
            "status": order.status.value,
            "subtotal": float(order.subtotal),
            "tax_amount": float(order.tax_amount),
            "shipping_amount": float(order.shipping_amount),
            "total_amount": float(order.total_amount),
            "shipping_address": order.shipping_address,
            "notes": order.notes,
            "expected_ship_date": order.expected_ship_date.isoformat() if order.expected_ship_date else None,
            "actual_ship_date": order.actual_ship_date.isoformat() if order.actual_ship_date else None,
            "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
            "ai_processed": order.ai_processed,
            "ai_confidence": float(order.ai_confidence) if order.ai_confidence else None,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "items": [
                {
                    "id": item.id,
                    "part_id": item.part_id,
                    "part_number": item.part.part_number if item.part else None,
                    "part_name": item.part.part_name if item.part else None,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price)
                }
                for item in order.items
            ] if hasattr(order, 'items') else []
        }
