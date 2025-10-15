"""
Serialized tracking API endpoints for VIN and serial number management.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.serialized_service import SerializedTrackingService
from app.services.auth_service import get_current_active_user
from app.models.user import User
from app.models.serialized import SerializedItemType, SerializedItemStatus
from pydantic import BaseModel

router = APIRouter()


class SerializedItemCreate(BaseModel):
    """Request model for creating serialized item."""
    serial_number: str
    item_type: SerializedItemType
    part_number: Optional[str] = None
    manufacturer: Optional[str] = None
    part_name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[int] = None
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    mileage: Optional[int] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    condition_rating: Optional[int] = None
    condition_notes: Optional[str] = None
    received_by: Optional[str] = None
    metadata: Optional[dict] = None


class SerializedItemResponse(BaseModel):
    """Response model for serialized item."""
    serial_number: str
    item_type: str
    status: str
    part_number: Optional[str] = None
    manufacturer: Optional[str] = None
    part_name: Optional[str] = None
    description: Optional[str] = None
    location_id: Optional[int] = None
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    mileage: Optional[int] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    condition_rating: Optional[int] = None
    condition_notes: Optional[str] = None
    received_date: Optional[datetime] = None
    received_by: Optional[str] = None
    last_movement_date: Optional[datetime] = None
    last_movement_type: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class VINLookupRequest(BaseModel):
    """Request model for VIN lookup."""
    vin: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    trim: Optional[str] = None
    body_style: Optional[str] = None
    engine_type: Optional[str] = None
    transmission_type: Optional[str] = None
    drive_type: Optional[str] = None
    fuel_type: Optional[str] = None
    displacement: Optional[str] = None
    horsepower: Optional[int] = None
    torque: Optional[int] = None
    cylinders: Optional[int] = None
    doors: Optional[int] = None
    seats: Optional[int] = None
    exterior_color: Optional[str] = None
    interior_color: Optional[str] = None
    features: Optional[dict] = None
    msrp: Optional[float] = None
    current_value: Optional[float] = None
    metadata: Optional[dict] = None


class ItemTransferRequest(BaseModel):
    """Request model for item transfer."""
    serial_number: str
    from_location_id: int
    to_location_id: int
    transfer_reason: Optional[str] = None
    transfer_method: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_arrival: Optional[datetime] = None
    metadata: Optional[dict] = None


class ItemReservationRequest(BaseModel):
    """Request model for item reservation."""
    serial_number: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    expires_date: Optional[datetime] = None
    reservation_notes: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/items", response_model=SerializedItemResponse)
async def create_serialized_item(
    item_data: SerializedItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new serialized item."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        item = await serialized_service.create_serialized_item(
            serial_number=item_data.serial_number,
            item_type=item_data.item_type,
            part_number=item_data.part_number,
            manufacturer=item_data.manufacturer,
            part_name=item_data.part_name,
            description=item_data.description,
            location_id=item_data.location_id,
            vin=item_data.vin,
            make=item_data.make,
            model=item_data.model,
            year=item_data.year,
            color=item_data.color,
            mileage=item_data.mileage,
            cost_price=item_data.cost_price,
            selling_price=item_data.selling_price,
            condition_rating=item_data.condition_rating,
            condition_notes=item_data.condition_notes,
            received_by=current_user.username,
            metadata=item_data.metadata
        )
        
        return SerializedItemResponse(
            serial_number=item.serial_number,
            item_type=item.item_type.value,
            status=item.status.value,
            part_number=item.part_number,
            manufacturer=item.manufacturer,
            part_name=item.part_name,
            description=item.description,
            location_id=item.location_id,
            vin=item.vin,
            make=item.make,
            model=item.model,
            year=item.year,
            color=item.color,
            mileage=item.mileage,
            cost_price=item.cost_price,
            selling_price=item.selling_price,
            condition_rating=item.condition_rating,
            condition_notes=item.condition_notes,
            received_date=item.received_date,
            received_by=item.received_by,
            last_movement_date=item.last_movement_date,
            last_movement_type=item.last_movement_type,
            metadata=item.get_metadata(),
            created_at=item.created_at,
            updated_at=item.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create serialized item: {str(e)}"
        )


@router.get("/items/{serial_number}", response_model=SerializedItemResponse)
async def get_serialized_item(
    serial_number: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get serialized item by serial number."""
    serialized_service = SerializedTrackingService(db)
    
    item = await serialized_service.get_serialized_item_by_serial_number(serial_number)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serialized item not found"
        )
    
    return SerializedItemResponse(
        serial_number=item.serial_number,
        item_type=item.item_type.value,
        status=item.status.value,
        part_number=item.part_number,
        manufacturer=item.manufacturer,
        part_name=item.part_name,
        description=item.description,
        location_id=item.location_id,
        vin=item.vin,
        make=item.make,
        model=item.model,
        year=item.year,
        color=item.color,
        mileage=item.mileage,
        cost_price=item.cost_price,
        selling_price=item.selling_price,
        condition_rating=item.condition_rating,
        condition_notes=item.condition_notes,
        received_date=item.received_date,
        received_by=item.received_by,
        last_movement_date=item.last_movement_date,
        last_movement_type=item.last_movement_type,
        metadata=item.get_metadata(),
        created_at=item.created_at,
        updated_at=item.updated_at
    )


@router.get("/items/search")
async def search_serialized_items(
    search_term: Optional[str] = Query(None),
    item_type: Optional[SerializedItemType] = Query(None),
    status: Optional[SerializedItemStatus] = Query(None),
    location_id: Optional[int] = Query(None),
    manufacturer: Optional[str] = Query(None),
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Search serialized items with filters."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        items = await serialized_service.search_serialized_items(
            search_term=search_term,
            item_type=item_type,
            status=status,
            location_id=location_id,
            manufacturer=manufacturer,
            make=make,
            model=model,
            year=year,
            limit=limit
        )
        
        return {
            "items": [
                {
                    "serial_number": item.serial_number,
                    "item_type": item.item_type.value,
                    "status": item.status.value,
                    "part_number": item.part_number,
                    "manufacturer": item.manufacturer,
                    "part_name": item.part_name,
                    "vin": item.vin,
                    "make": item.make,
                    "model": item.model,
                    "year": item.year,
                    "location_id": item.location_id,
                    "cost_price": item.cost_price,
                    "selling_price": item.selling_price,
                    "condition_rating": item.condition_rating,
                    "received_date": item.received_date,
                    "last_movement_date": item.last_movement_date,
                    "metadata": item.get_metadata()
                }
                for item in items
            ],
            "total": len(items)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search serialized items: {str(e)}"
        )


@router.put("/items/{serial_number}/status")
async def update_item_status(
    serial_number: str,
    new_status: SerializedItemStatus,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update serialized item status."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        success = await serialized_service.update_item_status(
            serial_number=serial_number,
            new_status=new_status,
            updated_by=current_user.username,
            notes=notes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Serialized item not found"
            )
        
        return {"message": "Item status updated successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update item status: {str(e)}"
        )


@router.get("/items/{serial_number}/history")
async def get_item_history(
    serial_number: str,
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get history for a serialized item."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        history = await serialized_service.get_item_history(
            serial_number=serial_number,
            limit=limit
        )
        
        return {
            "history": [
                {
                    "action": entry.action,
                    "description": entry.description,
                    "from_location_id": entry.from_location_id,
                    "to_location_id": entry.to_location_id,
                    "performed_by": entry.performed_by,
                    "user_id": entry.user_id,
                    "created_at": entry.created_at,
                    "metadata": entry.get_metadata()
                }
                for entry in history
            ],
            "total": len(history)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get item history: {str(e)}"
        )


@router.post("/vin/lookup")
async def create_vin_lookup(
    vin_data: VINLookupRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update VIN lookup information."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        vin_lookup = await serialized_service.create_vin_lookup(
            vin=vin_data.vin,
            make=vin_data.make,
            model=vin_data.model,
            year=vin_data.year,
            trim=vin_data.trim,
            body_style=vin_data.body_style,
            engine_type=vin_data.engine_type,
            transmission_type=vin_data.transmission_type,
            drive_type=vin_data.drive_type,
            fuel_type=vin_data.fuel_type,
            displacement=vin_data.displacement,
            horsepower=vin_data.horsepower,
            torque=vin_data.torque,
            cylinders=vin_data.cylinders,
            doors=vin_data.doors,
            seats=vin_data.seats,
            exterior_color=vin_data.exterior_color,
            interior_color=vin_data.interior_color,
            features=vin_data.features,
            msrp=vin_data.msrp,
            current_value=vin_data.current_value,
            metadata=vin_data.metadata
        )
        
        return {
            "vin": vin_lookup.vin,
            "make": vin_lookup.make,
            "model": vin_lookup.model,
            "year": vin_lookup.year,
            "trim": vin_lookup.trim,
            "body_style": vin_lookup.body_style,
            "engine_type": vin_lookup.engine_type,
            "transmission_type": vin_lookup.transmission_type,
            "drive_type": vin_lookup.drive_type,
            "fuel_type": vin_lookup.fuel_type,
            "displacement": vin_lookup.displacement,
            "horsepower": vin_lookup.horsepower,
            "torque": vin_lookup.torque,
            "cylinders": vin_lookup.cylinders,
            "doors": vin_lookup.doors,
            "seats": vin_lookup.seats,
            "exterior_color": vin_lookup.exterior_color,
            "interior_color": vin_lookup.interior_color,
            "features": json.loads(vin_lookup.features) if vin_lookup.features else None,
            "msrp": vin_lookup.msrp,
            "current_value": vin_lookup.current_value,
            "metadata": vin_lookup.get_metadata(),
            "created_at": vin_lookup.created_at,
            "updated_at": vin_lookup.updated_at
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VIN lookup: {str(e)}"
        )


@router.get("/vin/{vin}")
async def get_vin_lookup(
    vin: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get VIN lookup information."""
    serialized_service = SerializedTrackingService(db)
    
    vin_lookup = await serialized_service.get_vin_lookup(vin)
    if not vin_lookup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VIN lookup not found"
        )
    
    return {
        "vin": vin_lookup.vin,
        "make": vin_lookup.make,
        "model": vin_lookup.model,
        "year": vin_lookup.year,
        "trim": vin_lookup.trim,
        "body_style": vin_lookup.body_style,
        "engine_type": vin_lookup.engine_type,
        "transmission_type": vin_lookup.transmission_type,
        "drive_type": vin_lookup.drive_type,
        "fuel_type": vin_lookup.fuel_type,
        "displacement": vin_lookup.displacement,
        "horsepower": vin_lookup.horsepower,
        "torque": vin_lookup.torque,
        "cylinders": vin_lookup.cylinders,
        "doors": vin_lookup.doors,
        "seats": vin_lookup.seats,
        "exterior_color": vin_lookup.exterior_color,
        "interior_color": vin_lookup.interior_color,
        "features": json.loads(vin_lookup.features) if vin_lookup.features else None,
        "msrp": vin_lookup.msrp,
        "current_value": vin_lookup.current_value,
        "metadata": vin_lookup.get_metadata(),
        "created_at": vin_lookup.created_at,
        "updated_at": vin_lookup.updated_at
    }


@router.post("/transfers")
async def create_item_transfer(
    transfer_data: ItemTransferRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new serialized item transfer."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        transfer = await serialized_service.create_item_transfer(
            serial_number=transfer_data.serial_number,
            from_location_id=transfer_data.from_location_id,
            to_location_id=transfer_data.to_location_id,
            transfer_reason=transfer_data.transfer_reason,
            transfer_method=transfer_data.transfer_method,
            initiated_by=current_user.id,
            tracking_number=transfer_data.tracking_number,
            estimated_arrival=transfer_data.estimated_arrival,
            metadata=transfer_data.metadata
        )
        
        return {
            "transfer_id": transfer.transfer_id,
            "serial_number": transfer.serial_number,
            "from_location_id": transfer.from_location_id,
            "to_location_id": transfer.to_location_id,
            "transfer_reason": transfer.transfer_reason,
            "transfer_method": transfer.transfer_method,
            "status": transfer.status,
            "tracking_number": transfer.tracking_number,
            "estimated_arrival": transfer.estimated_arrival,
            "message": "Transfer created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transfer: {str(e)}"
        )


@router.post("/reservations")
async def create_item_reservation(
    reservation_data: ItemReservationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new serialized item reservation."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        reservation = await serialized_service.create_item_reservation(
            serial_number=reservation_data.serial_number,
            customer_id=reservation_data.customer_id,
            customer_name=reservation_data.customer_name,
            customer_phone=reservation_data.customer_phone,
            customer_email=reservation_data.customer_email,
            expires_date=reservation_data.expires_date,
            reservation_notes=reservation_data.reservation_notes,
            reserved_by=current_user.id,
            metadata=reservation_data.metadata
        )
        
        return {
            "reservation_id": reservation.reservation_id,
            "serial_number": reservation.serial_number,
            "customer_id": reservation.customer_id,
            "customer_name": reservation.customer_name,
            "customer_phone": reservation.customer_phone,
            "customer_email": reservation.customer_email,
            "reserved_date": reservation.reserved_date,
            "expires_date": reservation.expires_date,
            "status": reservation.status,
            "message": "Reservation created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reservation: {str(e)}"
        )


@router.get("/statistics")
async def get_serialized_item_statistics(
    location_id: Optional[int] = Query(None),
    item_type: Optional[SerializedItemType] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for serialized items."""
    serialized_service = SerializedTrackingService(db)
    
    try:
        stats = await serialized_service.get_serialized_item_statistics(
            location_id=location_id,
            item_type=item_type
        )
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check for serialized tracking service."""
    return {
        "status": "healthy",
        "service": "serialized_tracking",
        "timestamp": datetime.utcnow().isoformat()
    }
