"""
Supplier model for external parts sourcing.
"""

from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .base import TimestampMixin
from app.core.database import Base


class Supplier(Base, TimestampMixin):
    """Supplier model for external parts sourcing."""
    
    __tablename__ = "suppliers"
    
    name = Column(String(255), nullable=False, unique=True)
    website = Column(String(500), nullable=True)
    api_endpoint = Column(String(500), nullable=True)
    api_key = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    
    # Scraping configuration
    scrape_enabled = Column(Boolean, default=True, nullable=False)
    scrape_config = Column(JSON, nullable=True)  # Scraping rules and selectors
    
    # Performance metrics
    response_time_avg = Column(Numeric(8, 2), nullable=True)  # Average response time in seconds
    success_rate = Column(Numeric(5, 2), nullable=True)  # Success rate percentage
    last_scrape = Column(DateTime, nullable=True)
    last_successful_scrape = Column(DateTime, nullable=True)
    
    # Pricing and availability
    markup_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    shipping_cost = Column(Numeric(10, 2), default=0.00, nullable=False)
    minimum_order = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_trusted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    supplier_parts = relationship("SupplierPart", back_populates="supplier")
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, name='{self.name}', active={self.is_active})>"


class SupplierPart(Base, TimestampMixin):
    """Supplier part availability and pricing."""
    
    __tablename__ = "supplier_parts"
    
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    part_number = Column(String(100), nullable=False, index=True)
    manufacturer = Column(String(100), nullable=True)
    supplier_part_number = Column(String(100), nullable=True)
    part_name = Column(String(255), nullable=True)
    
    # Pricing and availability
    price = Column(Numeric(10, 2), nullable=True)
    quantity_available = Column(Integer, nullable=True)
    is_available = Column(Boolean, default=False, nullable=False)
    
    # Shipping info
    shipping_time = Column(String(100), nullable=True)  # "2-3 days", "1 week", etc.
    shipping_cost = Column(Numeric(10, 2), nullable=True)
    
    # Last updated
    last_checked = Column(DateTime, nullable=True)
    last_available = Column(DateTime, nullable=True)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="supplier_parts")
    
    def __repr__(self):
        return f"<SupplierPart(id={self.id}, supplier_id={self.supplier_id}, part_number='{self.part_number}')>"
