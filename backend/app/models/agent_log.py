"""
Agent log model for tracking AI agent actions and performance.
"""

from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from .base import TimestampMixin
from app.core.database import Base


class AgentType(enum.Enum):
    """Agent type enumeration."""
    EMAIL_CLASSIFIER = "email_classifier"
    CUSTOMER_SERVICE = "customer_service"
    PARTS_LOOKUP = "parts_lookup"
    INVENTORY_MANAGER = "inventory_manager"
    PRICING_INVOICE = "pricing_invoice"
    PAYMENT_PROCESSING = "payment_processing"
    SUPPLIER_SOURCING = "supplier_sourcing"
    SHIPPING_COORDINATOR = "shipping_coordinator"
    FOLLOW_UP = "follow_up"
    SUPERVISOR = "supervisor"


class LogLevel(enum.Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AgentLog(Base, TimestampMixin):
    """Agent log model for tracking AI agent actions."""
    
    __tablename__ = "agent_logs"
    
    agent_type = Column(Enum(AgentType), nullable=False, index=True)
    log_level = Column(Enum(LogLevel), default=LogLevel.INFO, nullable=False)
    
    # Context
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Action details
    action = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    input_data = Column(JSON, nullable=True)  # Input data for the agent
    output_data = Column(JSON, nullable=True)  # Output data from the agent
    
    # Performance metrics
    processing_time = Column(Numeric(8, 3), nullable=True)  # Processing time in seconds
    tokens_used = Column(Integer, nullable=True)
    cost = Column(Numeric(10, 4), nullable=True)  # Cost in dollars
    confidence_score = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    email = relationship("Email")
    order = relationship("Order")
    customer = relationship("Customer")
    
    def __repr__(self):
        return f"<AgentLog(id={self.id}, agent='{self.agent_type.value}', action='{self.action}', success={self.success})>"
