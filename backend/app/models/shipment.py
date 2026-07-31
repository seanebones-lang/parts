"""
Shipment model for tracking shipping and delivery.
"""

from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from .base import TimestampMixin
from app.core.database import Base


class ShipmentStatus(enum.Enum):
    """Shipment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    RETURNED = "returned"


class Shipment(Base, TimestampMixin):
    """Shipment model."""
    
    __tablename__ = "shipments"
    
    tracking_number = Column(String(100), nullable=False, unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PENDING, nullable=False)
    
    # Carrier info
    carrier = Column(String(100), nullable=False)  # UPS, FedEx, USPS, etc.
    service_type = Column(String(100), nullable=True)  # Ground, 2-Day, Overnight, etc.
    carrier_tracking_url = Column(String(500), nullable=True)
    
    # Shipping details
    weight = Column(Numeric(8, 2), nullable=True)
    dimensions = Column(String(100), nullable=True)  # LxWxH
    shipping_cost = Column(Numeric(10, 2), nullable=True)
    
    # Addresses
    from_address = Column(Text, nullable=False)
    to_address = Column(Text, nullable=False)
    
    # Dates
    shipped_date = Column(DateTime, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    actual_delivery = Column(DateTime, nullable=True)
    
    # Tracking updates
    last_tracking_update = Column(DateTime, nullable=True)
    tracking_updates = Column(JSON, nullable=True)  # Array of tracking events
    
    # Delivery confirmation
    delivered_to = Column(String(255), nullable=True)
    delivery_signature = Column(String(255), nullable=True)
    delivery_notes = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="shipments")
    
    @property
    def is_delivered(self):
        return self.status == ShipmentStatus.DELIVERED
    
    @property
    def is_in_transit(self):
        return self.status in [ShipmentStatus.SHIPPED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY]
    
    def __repr__(self):
        return f"<Shipment(id={self.id}, tracking_number='{self.tracking_number}', status='{self.status.value}')>"
