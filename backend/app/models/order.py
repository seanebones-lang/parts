"""
Order model for customer orders.
"""

from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .base import TimestampMixin
from app.core.database import Base


class OrderStatus(enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Order(Base, TimestampMixin):
    """Order model."""
    
    __tablename__ = "orders"
    
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    # Order details
    subtotal = Column(Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    shipping_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Shipping info
    shipping_address = Column(Text, nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(50), nullable=True)
    shipping_zip = Column(String(20), nullable=True)
    shipping_method = Column(String(100), nullable=True)
    
    # Tracking
    notes = Column(Text, nullable=True)
    expected_ship_date = Column(DateTime, nullable=True)
    actual_ship_date = Column(DateTime, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    
    # AI processing
    ai_processed = Column(Boolean, default=False, nullable=False)
    ai_confidence = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    location = relationship("Location", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="order")
    shipments = relationship("Shipment", back_populates="order")
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', status='{self.status.value}')>"


class OrderItem(Base, TimestampMixin):
    """Order item model."""
    
    __tablename__ = "order_items"
    
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts_catalog.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    part = relationship("PartsCatalog", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, part_id={self.part_id}, qty={self.quantity})>"
