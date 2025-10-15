"""
Inventory management endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.inventory_service import InventoryService
from app.agents.inventory_manager import InventoryManagerAgent

router = APIRouter()


@router.get("/location/{location_id}")
async def get_location_inventory(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get inventory for a specific location."""
    service = InventoryService(db)
    inventory = await service.get_location_inventory(location_id)
    
    return {
        "success": True,
        "location_id": location_id,
        "inventory": inventory,
        "count": len(inventory)
    }


@router.get("/part/{part_id}")
async def get_part_inventory(
    part_id: int,
    location_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get inventory for a part across locations."""
    service = InventoryService(db)
    inventory = await service.get_part_inventory(part_id, location_id)
    
    return {
        "success": True,
        "part_id": part_id,
        "location_id": location_id,
        "inventory": inventory,
        "count": len(inventory)
    }


@router.post("/update")
async def update_inventory(
    part_id: int,
    location_id: int,
    quantity_change: int,
    operation: str = "adjustment",
    db: AsyncSession = Depends(get_db)
):
    """Update inventory quantity."""
    try:
        service = InventoryService(db)
        result = await service.update_inventory(
            part_id=part_id,
            location_id=location_id,
            quantity_change=quantity_change,
            operation=operation
        )
        
        if result["success"]:
            return {
                "success": True,
                "result": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inventory update failed: {str(e)}")


@router.post("/reserve")
async def reserve_inventory(
    part_id: int,
    location_id: int,
    quantity: int,
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Reserve inventory for an order."""
    try:
        service = InventoryService(db)
        result = await service.reserve_inventory(
            part_id=part_id,
            location_id=location_id,
            quantity=quantity,
            order_id=order_id
        )
        
        if result["success"]:
            return {
                "success": True,
                "result": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inventory reservation failed: {str(e)}")


@router.post("/release")
async def release_reservation(
    part_id: int,
    location_id: int,
    quantity: int,
    db: AsyncSession = Depends(get_db)
):
    """Release reserved inventory."""
    try:
        service = InventoryService(db)
        result = await service.release_reservation(
            part_id=part_id,
            location_id=location_id,
            quantity=quantity
        )
        
        if result["success"]:
            return {
                "success": True,
                "result": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reservation release failed: {str(e)}")


@router.post("/receive")
async def receive_inventory(
    location_id: int,
    received_items: List[dict],
    db: AsyncSession = Depends(get_db)
):
    """Process received inventory."""
    try:
        agent = InventoryManagerAgent(db)
        result = await agent.process({
            "action": "process_receiving",
            "location_id": location_id,
            "received_items": received_items
        })
        
        if result.success:
            return {
                "success": True,
                "result": result.data
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Receiving failed: {str(e)}")


@router.post("/reorder")
async def trigger_reorder(
    location_id: int,
    part_id: Optional[int] = None,
    quantity: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Trigger reorder for low stock items."""
    try:
        agent = InventoryManagerAgent(db)
        result = await agent.process({
            "action": "trigger_reorder",
            "location_id": location_id,
            "part_id": part_id,
            "quantity": quantity
        })
        
        if result.success:
            return {
                "success": True,
                "result": result.data
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reorder failed: {str(e)}")


@router.post("/transfer")
async def transfer_stock(
    part_id: int,
    from_location_id: int,
    to_location_id: int,
    quantity: int,
    db: AsyncSession = Depends(get_db)
):
    """Transfer stock between locations."""
    try:
        agent = InventoryManagerAgent(db)
        result = await agent.process({
            "action": "transfer_stock",
            "part_id": part_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "quantity": quantity
        })
        
        if result.success:
            return {
                "success": True,
                "result": result.data
            }
        else:
            raise HTTPException(status_code=400, detail=result.data.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stock transfer failed: {str(e)}")


@router.get("/report/{location_id}")
async def get_inventory_report(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive inventory report."""
    try:
        agent = InventoryManagerAgent(db)
        result = await agent.process({
            "action": "check_inventory",
            "location_id": location_id
        })
        
        if result.success:
            return {
                "success": True,
                "report": result.data
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/low-stock/{location_id}")
async def get_low_stock_items(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get low stock items for a location."""
    try:
        agent = InventoryManagerAgent(db)
        result = await agent.process({
            "action": "check_inventory",
            "location_id": location_id
        })
        
        if result.success:
            low_stock_items = []
            for alert in result.data.get("alerts", []):
                if alert["type"] == "low_stock":
                    low_stock_items.extend(alert["items"])
            
            return {
                "success": True,
                "location_id": location_id,
                "low_stock_items": low_stock_items,
                "count": len(low_stock_items)
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Low stock check failed: {str(e)}")
