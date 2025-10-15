"""
Location model for dealership locations.
"""

from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.orm import relationship
from .base import TimestampMixin
from app.core.database import Base


class Location(Base, TimestampMixin):
    """Dealership location model."""
    
    __tablename__ = "locations"
    
    name = Column(String(255), nullable=False, unique=True)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(20), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    manager_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="location")
    orders = relationship("Order", back_populates="location")
    invoices = relationship("Invoice", back_populates="location")
    users = relationship("User", back_populates="location")
    
    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}')>"
