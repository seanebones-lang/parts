"""
Serialized tracking models for VIN and serial number management.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import TimestampMixin
from app.core.database import Base
from enum import Enum as PyEnum
from typing import Optional, Dict, Any
import json
import re




class MetaJSONMixin:
    """JSON blob helpers for models that store extra_data (DB column metadata)."""

    def set_metadata(self, data: Dict[str, Any]):
        self.extra_data = json.dumps(data)

    def get_metadata(self) -> Dict[str, Any]:
        if getattr(self, "extra_data", None):
            return json.loads(self.extra_data)
        return {}


class SerializedItemType(str, PyEnum):
    """Types of serialized items."""
    VEHICLE = "vehicle"
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    PART = "part"
    COMPONENT = "component"


class SerializedItemStatus(str, PyEnum):
    """Status of serialized items."""
    IN_STOCK = "in_stock"
    RESERVED = "reserved"
    SOLD = "sold"
    RETURNED = "returned"
    DAMAGED = "damaged"
    RECALLED = "recalled"
    SCRAPPED = "scrapped"


class SerializedItem(Base, TimestampMixin, MetaJSONMixin):
    """Model for tracking serialized items (VIN, serial numbers, etc.)."""
    
    __tablename__ = "serialized_items"
    
    # Item identification
    serial_number = Column(String(100), unique=True, index=True, nullable=False)
    item_type = Column(Enum(SerializedItemType), nullable=False)
    status = Column(Enum(SerializedItemStatus), default=SerializedItemStatus.IN_STOCK)
    
    # Part information
    part_number = Column(String(100), nullable=True, index=True)
    manufacturer = Column(String(100), nullable=True)
    part_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Vehicle information (for VINs)
    vin = Column(String(17), nullable=True, index=True)
    make = Column(String(50), nullable=True)
    model = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True)
    color = Column(String(50), nullable=True)
    mileage = Column(Integer, nullable=True)
    
    # Location and inventory
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Location")
    
    # Financial information
    cost_price = Column(Float, nullable=True)
    selling_price = Column(Float, nullable=True)
    warranty_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Condition and quality
    condition_rating = Column(Integer, nullable=True)  # 1-10 scale
    condition_notes = Column(Text, nullable=True)
    quality_inspection_date = Column(DateTime(timezone=True), nullable=True)
    quality_inspector = Column(String(100), nullable=True)
    
    # History and tracking
    received_date = Column(DateTime(timezone=True), nullable=True)
    received_by = Column(String(100), nullable=True)
    last_movement_date = Column(DateTime(timezone=True), nullable=True)
    last_movement_type = Column(String(50), nullable=True)  # received, sold, transferred, etc.
    
    # Additional data
    extra_data = Column("metadata", Text, nullable=True)  # JSON blob (attr != SQLAlchemy reserved)
    


class SerializedItemHistory(Base, TimestampMixin, MetaJSONMixin):
    """Model for tracking serialized item history."""
    
    __tablename__ = "serialized_item_history"
    
    # Item reference
    serial_number = Column(String(100), ForeignKey("serialized_items.serial_number"), nullable=False)
    serialized_item = relationship("SerializedItem")
    
    # History details
    action = Column(String(100), nullable=False)  # received, sold, transferred, inspected, etc.
    description = Column(Text, nullable=True)
    
    # Location changes
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    
    # User information
    performed_by = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")
    
    # Additional data
    extra_data = Column("metadata", Text, nullable=True)  # JSON blob (attr != SQLAlchemy reserved)


class VINLookup(Base, TimestampMixin, MetaJSONMixin):
    """Model for VIN lookup and vehicle information."""
    
    __tablename__ = "vin_lookups"
    
    # VIN information
    vin = Column(String(17), unique=True, index=True, nullable=False)
    
    # Vehicle details
    make = Column(String(50), nullable=True)
    model = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True)
    trim = Column(String(100), nullable=True)
    body_style = Column(String(50), nullable=True)
    engine_type = Column(String(100), nullable=True)
    transmission_type = Column(String(50), nullable=True)
    drive_type = Column(String(50), nullable=True)
    fuel_type = Column(String(50), nullable=True)
    
    # Vehicle specifications
    displacement = Column(String(20), nullable=True)  # Engine displacement
    horsepower = Column(Integer, nullable=True)
    torque = Column(Integer, nullable=True)
    cylinders = Column(Integer, nullable=True)
    doors = Column(Integer, nullable=True)
    seats = Column(Integer, nullable=True)
    
    # Color and features
    exterior_color = Column(String(50), nullable=True)
    interior_color = Column(String(50), nullable=True)
    features = Column(Text, nullable=True)  # JSON string of features
    
    # Market information
    msrp = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    depreciation_rate = Column(Float, nullable=True)
    
    # Additional data
    extra_data = Column("metadata", Text, nullable=True)  # JSON blob (attr != SQLAlchemy reserved)


class SerializedItemTransfer(Base, TimestampMixin, MetaJSONMixin):
    """Model for tracking serialized item transfers between locations."""
    
    __tablename__ = "serialized_item_transfers"
    
    # Transfer identification
    transfer_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # Item information
    serial_number = Column(String(100), ForeignKey("serialized_items.serial_number"), nullable=False)
    serialized_item = relationship("SerializedItem")
    
    # Transfer details
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    
    # Transfer information
    transfer_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    transfer_reason = Column(String(100), nullable=True)
    transfer_method = Column(String(50), nullable=True)  # truck, courier, pickup, etc.
    
    # User information
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    initiated_by_user = relationship("User")
    received_by = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, in_transit, received, cancelled
    tracking_number = Column(String(100), nullable=True)
    estimated_arrival = Column(DateTime(timezone=True), nullable=True)
    actual_arrival = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data
    extra_data = Column("metadata", Text, nullable=True)  # JSON blob (attr != SQLAlchemy reserved)


class SerializedItemReservation(Base, TimestampMixin, MetaJSONMixin):
    """Model for tracking serialized item reservations."""
    
    __tablename__ = "serialized_item_reservations"
    
    # Reservation identification
    reservation_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # Item information
    serial_number = Column(String(100), ForeignKey("serialized_items.serial_number"), nullable=False)
    serialized_item = relationship("SerializedItem")
    
    # Customer information
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer = relationship("Customer")
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_email = Column(String(255), nullable=True)
    
    # Reservation details
    reserved_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_date = Column(DateTime(timezone=True), nullable=True)
    reservation_notes = Column(Text, nullable=True)
    
    # User information
    reserved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reserved_by_user = relationship("User")
    
    # Status
    status = Column(String(20), default="active")  # active, expired, cancelled, fulfilled
    
    # Additional data
    extra_data = Column("metadata", Text, nullable=True)  # JSON blob (attr != SQLAlchemy reserved)


class SerializedItemInspection(Base, TimestampMixin, MetaJSONMixin):
    """Model for tracking serialized item inspections."""
    
    __tablename__ = "serialized_item_inspections"
    
    # Inspection identification
    inspection_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # Item information
    serial_number = Column(String(100), ForeignKey("serialized_items.serial_number"), nullable=False)
    serialized_item = relationship("SerializedItem")
    
    # Inspection details
    inspection_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    inspection_type = Column(String(50), nullable=False)  # quality, safety, compliance, etc.
    inspector_name = Column(String(100), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    inspector = relationship("User")
    
    # Inspection results
    overall_rating = Column(Integer, nullable=True)  # 1-10 scale
    passed = Column(Boolean, nullable=True)
    issues_found = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    
    # Inspection checklist
    checklist_items = Column(Text, nullable=True)  # JSON string of checklist items
    
    # Additional data
    extra_data = Column("metadata", Text, nullable=True)  # JSON blob (attr != SQLAlchemy reserved)


class SerializedItemRecall(Base, TimestampMixin, MetaJSONMixin):
    """Model for tracking serialized item recalls."""
    
    __tablename__ = "serialized_item_recalls"
    
    # Recall identification
    recall_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # Item information
    serial_number = Column(String(100), ForeignKey("serialized_items.serial_number"), nullable=False)
    serialized_item = relationship("SerializedItem")
    
    # Recall details
    recall_reason = Column(Text, nullable=False)
    recall_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    recall_type = Column(String(50), nullable=False)  # safety, quality, compliance, etc.
    
    # Recall status
    status = Column(String(20), default="active")  # active, resolved, cancelled
    resolution_date = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # User information
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    initiated_by_user = relationship("User", foreign_keys=[initiated_by])
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    
    # Additional data
    extra_data = Column("metadata", Text, nullable=True)  # JSON blob (attr != SQLAlchemy reserved)
