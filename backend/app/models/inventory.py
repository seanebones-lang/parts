"""
Inventory model for tracking parts across locations.
"""

from sqlalchemy import Column, Integer, Numeric, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from .base import TimestampMixin
from app.core.database import Base


class Inventory(Base, TimestampMixin):
    """Inventory tracking model."""
    
    __tablename__ = "inventory"
    
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts_catalog.id"), nullable=False)
    quantity_available = Column(Integer, default=0, nullable=False)
    quantity_reserved = Column(Integer, default=0, nullable=False)
    quantity_on_order = Column(Integer, default=0, nullable=False)
    reorder_point = Column(Integer, default=0, nullable=False)
    reorder_quantity = Column(Integer, default=0, nullable=False)
    last_counted = Column(DateTime, nullable=True)
    bin_location = Column(String(50), nullable=True)
    cost = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Expiration tracking
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    batch_number = Column(String(100), nullable=True)
    lot_number = Column(String(100), nullable=True)
    manufacture_date = Column(DateTime(timezone=True), nullable=True)
    shelf_life_days = Column(Integer, nullable=True)
    is_expired = Column(Boolean, default=False, nullable=False)
    expiration_warning_days = Column(Integer, default=30, nullable=False)
    
    # Relationships
    location = relationship("Location", back_populates="inventory")
    part = relationship("PartsCatalog", back_populates="inventory")
    
    @property
    def total_quantity(self):
        return self.quantity_available + self.quantity_reserved + self.quantity_on_order
    
    @property
    def needs_reorder(self):
        return self.quantity_available <= self.reorder_point
    
    def __repr__(self):
        return f"<Inventory(id={self.id}, location_id={self.location_id}, part_id={self.part_id}, qty={self.quantity_available})>"
