"""
Order processing endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.order_service import OrderService
from app.services.pricing_service import PricingService
from app.agents.pricing_invoice import PricingInvoiceAgent
from app.models.order import OrderStatus

router = APIRouter()


@router.get("/")
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get orders with optional filters."""
    try:
        service = OrderService(db)
        
        # Convert status string to enum if provided
        order_status = None
        if status:
            try:
                order_status = OrderStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status value")
        
        orders = await service.get_orders(
            skip=skip,
            limit=limit,
            customer_id=customer_id,
            location_id=location_id,
            status=order_status
        )
        
        return {
            "success": True,
            "orders": orders,
            "count": len(orders)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get order by ID."""
    try:
        service = OrderService(db)
        order = await service.get_order(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "success": True,
            "order": order
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order: {str(e)}")


@router.post("/")
async def create_order(
    order_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new order."""
    try:
        service = OrderService(db)
        
        required_fields = ["customer_id", "location_id", "items"]
        for field in required_fields:
            if field not in order_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await service.create_order(
            customer_id=order_data["customer_id"],
            location_id=order_data["location_id"],
            items=order_data["items"],
            shipping_address=order_data.get("shipping_address"),
            notes=order_data.get("notes")
        )
        
        if result["success"]:
            return {
                "success": True,
                "order": result["order"],
                "message": "Order created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update order status."""
    try:
        service = OrderService(db)
        
        new_status = status_data.get("status")
        notes = status_data.get("notes")
        
        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        try:
            order_status = OrderStatus(new_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")
        
        result = await service.update_order_status(
            order_id=order_id,
            new_status=order_status,
            notes=notes
        )
        
        if result["success"]:
            return {
                "success": True,
                "result": result,
                "message": "Order status updated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update order status: {str(e)}")


@router.post("/{order_id}/reserve")
async def reserve_inventory(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Reserve inventory for an order."""
    try:
        service = OrderService(db)
        result = await service.reserve_inventory_for_order(order_id)
        
        if result["success"]:
            return {
                "success": True,
                "result": result,
                "message": "Inventory reserved successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reserve inventory: {str(e)}")


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    cancel_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Cancel an order."""
    try:
        service = OrderService(db)
        
        reason = cancel_data.get("reason", "Customer request")
        result = await service.cancel_order(order_id, reason)
        
        if result["success"]:
            return {
                "success": True,
                "result": result,
                "message": "Order cancelled successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


@router.get("/analytics/summary")
async def get_order_analytics(
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get order analytics and metrics."""
    try:
        service = OrderService(db)
        
        # Parse dates if provided
        from datetime import datetime
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        analytics = await service.get_order_analytics(
            location_id=location_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.post("/quote")
async def generate_quote(
    quote_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Generate a quote for parts and services."""
    try:
        agent = PricingInvoiceAgent(db)
        
        required_fields = ["customer_id", "location_id", "items"]
        for field in required_fields:
            if field not in quote_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await agent.process({
            "action": "generate_quote",
            **quote_data
        })
        
        if result.success:
            return {
                "success": True,
                "quote": result.data,
                "message": "Quote generated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quote: {str(e)}")


@router.post("/invoice")
async def create_invoice(
    invoice_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create invoice from quote or order."""
    try:
        agent = PricingInvoiceAgent(db)
        
        if "quote_id" not in invoice_data and "order_id" not in invoice_data:
            raise HTTPException(status_code=400, detail="Either quote_id or order_id is required")
        
        result = await agent.process({
            "action": "create_invoice",
            **invoice_data
        })
        
        if result.success:
            return {
                "success": True,
                "invoice": result.data,
                "message": "Invoice created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {str(e)}")


@router.post("/pricing/calculate")
async def calculate_pricing(
    pricing_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Calculate pricing for parts."""
    try:
        agent = PricingInvoiceAgent(db)
        
        required_fields = ["part_id", "location_id"]
        for field in required_fields:
            if field not in pricing_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await agent.process({
            "action": "calculate_pricing",
            **pricing_data
        })
        
        if result.success:
            return {
                "success": True,
                "pricing": result.data,
                "message": "Pricing calculated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate pricing: {str(e)}")


@router.post("/discount/apply")
async def apply_discount(
    discount_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Apply discount code to order."""
    try:
        agent = PricingInvoiceAgent(db)
        
        required_fields = ["items", "discount_code"]
        for field in required_fields:
            if field not in discount_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await agent.process({
            "action": "apply_discount",
            **discount_data
        })
        
        if result.success:
            return {
                "success": True,
                "discount_result": result.data,
                "message": "Discount applied successfully"
            }
        else:
            return {
                "success": False,
                "error": result.data.get("error"),
                "message": "Discount could not be applied"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply discount: {str(e)}")