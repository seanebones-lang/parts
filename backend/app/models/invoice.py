"""
Invoice model for billing.
"""

from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .base import TimestampMixin
from app.core.database import Base


class InvoiceStatus(enum.Enum):
    """Invoice status enumeration."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base, TimestampMixin):
    """Invoice model."""
    
    __tablename__ = "invoices"
    
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    
    # Invoice details
    subtotal = Column(Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    shipping_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    amount_paid = Column(Numeric(10, 2), default=0.00, nullable=False)
    balance_due = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Dates
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime, nullable=True)
    
    # Payment info
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    # PDF and email
    pdf_path = Column(String(500), nullable=True)
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    location = relationship("Location", back_populates="invoices")
    
    @property
    def is_paid(self):
        return self.status == InvoiceStatus.PAID
    
    @property
    def is_overdue(self):
        if self.is_paid:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.due_date
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', status='{self.status.value}')>"
