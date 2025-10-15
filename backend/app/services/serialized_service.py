"""
Serialized tracking service for VIN and serial number management.
"""

import uuid
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.serialized import (
    SerializedItem, SerializedItemHistory, VINLookup, SerializedItemTransfer,
    SerializedItemReservation, SerializedItemInspection, SerializedItemRecall,
    SerializedItemType, SerializedItemStatus
)
from app.models.parts_catalog import PartsCatalog
from app.models.location import Location
from app.models.user import User
from app.models.customer import Customer


class SerializedTrackingService:
    """Service for managing serialized items and VIN tracking."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_transfer_id(self) -> str:
        """Generate unique transfer ID."""
        return f"TRANSFER_{uuid.uuid4().hex[:12].upper()}"
    
    def generate_reservation_id(self) -> str:
        """Generate unique reservation ID."""
        return f"RESERVE_{uuid.uuid4().hex[:12].upper()}"
    
    def generate_inspection_id(self) -> str:
        """Generate unique inspection ID."""
        return f"INSPECT_{uuid.uuid4().hex[:12].upper()}"
    
    def generate_recall_id(self) -> str:
        """Generate unique recall ID."""
        return f"RECALL_{uuid.uuid4().hex[:12].upper()}"
    
    def validate_vin(self, vin: str) -> bool:
        """Validate VIN format."""
        if not vin or len(vin) != 17:
            return False
        
        # VIN validation regex (simplified)
        vin_pattern = r'^[A-HJ-NPR-Z0-9]{17}$'
        return bool(re.match(vin_pattern, vin.upper()))
    
    def validate_serial_number(self, serial_number: str) -> bool:
        """Validate serial number format."""
        if not serial_number or len(serial_number) < 3:
            return False
        
        # Basic serial number validation
        return bool(re.match(r'^[A-Z0-9\-_]{3,100}$', serial_number.upper()))
    
    async def create_serialized_item(
        self,
        serial_number: str,
        item_type: SerializedItemType,
        part_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        part_name: Optional[str] = None,
        description: Optional[str] = None,
        location_id: Optional[int] = None,
        vin: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        color: Optional[str] = None,
        mileage: Optional[int] = None,
        cost_price: Optional[float] = None,
        selling_price: Optional[float] = None,
        condition_rating: Optional[int] = None,
        condition_notes: Optional[str] = None,
        received_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializedItem:
        """Create a new serialized item."""
        
        # Validate serial number
        if not self.validate_serial_number(serial_number):
            raise ValueError("Invalid serial number format")
        
        # Validate VIN if provided
        if vin and not self.validate_vin(vin):
            raise ValueError("Invalid VIN format")
        
        # Check if serial number already exists
        existing_item = await self.get_serialized_item_by_serial_number(serial_number)
        if existing_item:
            raise ValueError("Serial number already exists")
        
        # Create serialized item
        item = SerializedItem(
            serial_number=serial_number.upper(),
            item_type=item_type,
            part_number=part_number,
            manufacturer=manufacturer,
            part_name=part_name,
            description=description,
            location_id=location_id,
            vin=vin.upper() if vin else None,
            make=make,
            model=model,
            year=year,
            color=color,
            mileage=mileage,
            cost_price=cost_price,
            selling_price=selling_price,
            condition_rating=condition_rating,
            condition_notes=condition_notes,
            received_date=datetime.utcnow(),
            received_by=received_by,
            last_movement_date=datetime.utcnow(),
            last_movement_type="received"
        )
        
        if metadata:
            item.set_metadata(metadata)
        
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        
        # Create history entry
        await self.add_item_history(
            serial_number=serial_number,
            action="received",
            description=f"Item received and added to inventory",
            to_location_id=location_id,
            performed_by=received_by
        )
        
        return item
    
    async def get_serialized_item_by_serial_number(self, serial_number: str) -> Optional[SerializedItem]:
        """Get serialized item by serial number."""
        query = select(SerializedItem).where(SerializedItem.serial_number == serial_number.upper())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_serialized_item_by_vin(self, vin: str) -> Optional[SerializedItem]:
        """Get serialized item by VIN."""
        query = select(SerializedItem).where(SerializedItem.vin == vin.upper())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search_serialized_items(
        self,
        search_term: Optional[str] = None,
        item_type: Optional[SerializedItemType] = None,
        status: Optional[SerializedItemStatus] = None,
        location_id: Optional[int] = None,
        manufacturer: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 100
    ) -> List[SerializedItem]:
        """Search serialized items with filters."""
        query = select(SerializedItem)
        
        if search_term:
            query = query.where(
                or_(
                    SerializedItem.serial_number.ilike(f"%{search_term}%"),
                    SerializedItem.part_number.ilike(f"%{search_term}%"),
                    SerializedItem.part_name.ilike(f"%{search_term}%"),
                    SerializedItem.vin.ilike(f"%{search_term}%"),
                    SerializedItem.description.ilike(f"%{search_term}%")
                )
            )
        
        if item_type:
            query = query.where(SerializedItem.item_type == item_type)
        
        if status:
            query = query.where(SerializedItem.status == status)
        
        if location_id:
            query = query.where(SerializedItem.location_id == location_id)
        
        if manufacturer:
            query = query.where(SerializedItem.manufacturer.ilike(f"%{manufacturer}%"))
        
        if make:
            query = query.where(SerializedItem.make.ilike(f"%{make}%"))
        
        if model:
            query = query.where(SerializedItem.model.ilike(f"%{model}%"))
        
        if year:
            query = query.where(SerializedItem.year == year)
        
        query = query.order_by(desc(SerializedItem.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_item_status(
        self,
        serial_number: str,
        new_status: SerializedItemStatus,
        updated_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update serialized item status."""
        item = await self.get_serialized_item_by_serial_number(serial_number)
        if not item:
            return False
        
        old_status = item.status
        item.status = new_status
        item.last_movement_date = datetime.utcnow()
        item.last_movement_type = "status_change"
        
        await self.db.commit()
        
        # Create history entry
        await self.add_item_history(
            serial_number=serial_number,
            action="status_change",
            description=f"Status changed from {old_status} to {new_status}. {notes or ''}",
            performed_by=updated_by
        )
        
        return True
    
    async def add_item_history(
        self,
        serial_number: str,
        action: str,
        description: Optional[str] = None,
        from_location_id: Optional[int] = None,
        to_location_id: Optional[int] = None,
        performed_by: Optional[str] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializedItemHistory:
        """Add history entry for serialized item."""
        history = SerializedItemHistory(
            serial_number=serial_number.upper(),
            action=action,
            description=description,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            performed_by=performed_by,
            user_id=user_id
        )
        
        if metadata:
            history.set_metadata(metadata)
        
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        
        return history
    
    async def get_item_history(
        self,
        serial_number: str,
        limit: int = 100
    ) -> List[SerializedItemHistory]:
        """Get history for a serialized item."""
        query = select(SerializedItemHistory).where(
            SerializedItemHistory.serial_number == serial_number.upper()
        ).order_by(desc(SerializedItemHistory.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_vin_lookup(
        self,
        vin: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        trim: Optional[str] = None,
        body_style: Optional[str] = None,
        engine_type: Optional[str] = None,
        transmission_type: Optional[str] = None,
        drive_type: Optional[str] = None,
        fuel_type: Optional[str] = None,
        displacement: Optional[str] = None,
        horsepower: Optional[int] = None,
        torque: Optional[int] = None,
        cylinders: Optional[int] = None,
        doors: Optional[int] = None,
        seats: Optional[int] = None,
        exterior_color: Optional[str] = None,
        interior_color: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
        msrp: Optional[float] = None,
        current_value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VINLookup:
        """Create or update VIN lookup information."""
        
        if not self.validate_vin(vin):
            raise ValueError("Invalid VIN format")
        
        # Check if VIN lookup already exists
        query = select(VINLookup).where(VINLookup.vin == vin.upper())
        result = await self.db.execute(query)
        vin_lookup = result.scalar_one_or_none()
        
        if vin_lookup:
            # Update existing VIN lookup
            vin_lookup.make = make or vin_lookup.make
            vin_lookup.model = model or vin_lookup.model
            vin_lookup.year = year or vin_lookup.year
            vin_lookup.trim = trim or vin_lookup.trim
            vin_lookup.body_style = body_style or vin_lookup.body_style
            vin_lookup.engine_type = engine_type or vin_lookup.engine_type
            vin_lookup.transmission_type = transmission_type or vin_lookup.transmission_type
            vin_lookup.drive_type = drive_type or vin_lookup.drive_type
            vin_lookup.fuel_type = fuel_type or vin_lookup.fuel_type
            vin_lookup.displacement = displacement or vin_lookup.displacement
            vin_lookup.horsepower = horsepower or vin_lookup.horsepower
            vin_lookup.torque = torque or vin_lookup.torque
            vin_lookup.cylinders = cylinders or vin_lookup.cylinders
            vin_lookup.doors = doors or vin_lookup.doors
            vin_lookup.seats = seats or vin_lookup.seats
            vin_lookup.exterior_color = exterior_color or vin_lookup.exterior_color
            vin_lookup.interior_color = interior_color or vin_lookup.interior_color
            vin_lookup.msrp = msrp or vin_lookup.msrp
            vin_lookup.current_value = current_value or vin_lookup.current_value
            
            if features:
                vin_lookup.features = json.dumps(features)
            
            if metadata:
                vin_lookup.set_metadata(metadata)
            
            await self.db.commit()
            await self.db.refresh(vin_lookup)
            
            return vin_lookup
        else:
            # Create new VIN lookup
            vin_lookup = VINLookup(
                vin=vin.upper(),
                make=make,
                model=model,
                year=year,
                trim=trim,
                body_style=body_style,
                engine_type=engine_type,
                transmission_type=transmission_type,
                drive_type=drive_type,
                fuel_type=fuel_type,
                displacement=displacement,
                horsepower=horsepower,
                torque=torque,
                cylinders=cylinders,
                doors=doors,
                seats=seats,
                exterior_color=exterior_color,
                interior_color=interior_color,
                msrp=msrp,
                current_value=current_value
            )
            
            if features:
                vin_lookup.features = json.dumps(features)
            
            if metadata:
                vin_lookup.set_metadata(metadata)
            
            self.db.add(vin_lookup)
            await self.db.commit()
            await self.db.refresh(vin_lookup)
            
            return vin_lookup
    
    async def get_vin_lookup(self, vin: str) -> Optional[VINLookup]:
        """Get VIN lookup information."""
        query = select(VINLookup).where(VINLookup.vin == vin.upper())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_item_transfer(
        self,
        serial_number: str,
        from_location_id: int,
        to_location_id: int,
        transfer_reason: Optional[str] = None,
        transfer_method: Optional[str] = None,
        initiated_by: Optional[int] = None,
        tracking_number: Optional[str] = None,
        estimated_arrival: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializedItemTransfer:
        """Create a new serialized item transfer."""
        
        # Check if item exists
        item = await self.get_serialized_item_by_serial_number(serial_number)
        if not item:
            raise ValueError("Serialized item not found")
        
        # Check if item is available for transfer
        if item.status != SerializedItemStatus.IN_STOCK:
            raise ValueError("Item is not available for transfer")
        
        transfer_id = self.generate_transfer_id()
        
        transfer = SerializedItemTransfer(
            transfer_id=transfer_id,
            serial_number=serial_number.upper(),
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            transfer_reason=transfer_reason,
            transfer_method=transfer_method,
            initiated_by=initiated_by,
            tracking_number=tracking_number,
            estimated_arrival=estimated_arrival
        )
        
        if metadata:
            transfer.set_metadata(metadata)
        
        self.db.add(transfer)
        await self.db.commit()
        await self.db.refresh(transfer)
        
        # Update item status
        await self.update_item_status(
            serial_number=serial_number,
            new_status=SerializedItemStatus.RESERVED,
            updated_by="system",
            notes=f"Reserved for transfer to location {to_location_id}"
        )
        
        # Create history entry
        await self.add_item_history(
            serial_number=serial_number,
            action="transfer_initiated",
            description=f"Transfer initiated from location {from_location_id} to location {to_location_id}",
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            user_id=initiated_by
        )
        
        return transfer
    
    async def complete_item_transfer(
        self,
        transfer_id: str,
        received_by: Optional[str] = None,
        actual_arrival: Optional[datetime] = None
    ) -> bool:
        """Complete a serialized item transfer."""
        
        query = select(SerializedItemTransfer).where(SerializedItemTransfer.transfer_id == transfer_id)
        result = await self.db.execute(query)
        transfer = result.scalar_one_or_none()
        
        if not transfer:
            return False
        
        # Update transfer
        transfer.status = "received"
        transfer.received_by = received_by
        transfer.actual_arrival = actual_arrival or datetime.utcnow()
        
        # Update item location and status
        item = await self.get_serialized_item_by_serial_number(transfer.serial_number)
        if item:
            item.location_id = transfer.to_location_id
            item.status = SerializedItemStatus.IN_STOCK
            item.last_movement_date = datetime.utcnow()
            item.last_movement_type = "transfer_completed"
        
        await self.db.commit()
        
        # Create history entry
        await self.add_item_history(
            serial_number=transfer.serial_number,
            action="transfer_completed",
            description=f"Transfer completed to location {transfer.to_location_id}",
            from_location_id=transfer.from_location_id,
            to_location_id=transfer.to_location_id,
            performed_by=received_by
        )
        
        return True
    
    async def create_item_reservation(
        self,
        serial_number: str,
        customer_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        expires_date: Optional[datetime] = None,
        reservation_notes: Optional[str] = None,
        reserved_by: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SerializedItemReservation:
        """Create a new serialized item reservation."""
        
        # Check if item exists and is available
        item = await self.get_serialized_item_by_serial_number(serial_number)
        if not item:
            raise ValueError("Serialized item not found")
        
        if item.status != SerializedItemStatus.IN_STOCK:
            raise ValueError("Item is not available for reservation")
        
        reservation_id = self.generate_reservation_id()
        
        reservation = SerializedItemReservation(
            reservation_id=reservation_id,
            serial_number=serial_number.upper(),
            customer_id=customer_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            expires_date=expires_date,
            reservation_notes=reservation_notes,
            reserved_by=reserved_by
        )
        
        if metadata:
            reservation.set_metadata(metadata)
        
        self.db.add(reservation)
        await self.db.commit()
        await self.db.refresh(reservation)
        
        # Update item status
        await self.update_item_status(
            serial_number=serial_number,
            new_status=SerializedItemStatus.RESERVED,
            updated_by="system",
            notes=f"Reserved for customer {customer_name or customer_id}"
        )
        
        # Create history entry
        await self.add_item_history(
            serial_number=serial_number,
            action="reserved",
            description=f"Item reserved for customer {customer_name or customer_id}",
            performed_by="system",
            user_id=reserved_by
        )
        
        return reservation
    
    async def get_serialized_item_statistics(
        self,
        location_id: Optional[int] = None,
        item_type: Optional[SerializedItemType] = None
    ) -> Dict[str, Any]:
        """Get statistics for serialized items."""
        
        query = select(SerializedItem)
        
        if location_id:
            query = query.where(SerializedItem.location_id == location_id)
        
        if item_type:
            query = query.where(SerializedItem.item_type == item_type)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Calculate statistics
        total_items = len(items)
        status_counts = {}
        type_counts = {}
        location_counts = {}
        
        for item in items:
            # Status counts
            status = item.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Type counts
            item_type = item.item_type.value
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            # Location counts
            if item.location_id:
                location_counts[item.location_id] = location_counts.get(item.location_id, 0) + 1
        
        # Calculate total value
        total_value = sum(item.selling_price or 0 for item in items if item.selling_price)
        
        return {
            "total_items": total_items,
            "status_counts": status_counts,
            "type_counts": type_counts,
            "location_counts": location_counts,
            "total_value": total_value,
            "average_value": total_value / total_items if total_items > 0 else 0
        }
