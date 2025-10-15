"""
Customer model for dealership customers.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Numeric
from sqlalchemy.orm import relationship
from .base import TimestampMixin
from app.core.database import Base


class Customer(Base, TimestampMixin):
    """Customer model."""
    
    __tablename__ = "customers"
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    company_name = Column(String(255), nullable=True)
    tax_id = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_contact = Column(DateTime, nullable=True)
    total_orders = Column(Integer, default=0, nullable=False)
    total_spent = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.full_name}', email='{self.email}')>"
