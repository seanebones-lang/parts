"""
Email model for tracking email threads and AI processing.
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from .base import TimestampMixin
from app.core.database import Base


class EmailType(enum.Enum):
    """Email type enumeration."""
    PARTS_ORDER = "parts_order"
    QUOTE_REQUEST = "quote_request"
    SHIPPING_INQUIRY = "shipping_inquiry"
    COMPLAINT = "complaint"
    GENERAL_INQUIRY = "general_inquiry"
    PAYMENT_INQUIRY = "payment_inquiry"
    CUSTOMER_SERVICE = "customer_service"
    UNKNOWN = "unknown"


class EmailStatus(enum.Enum):
    """Email status enumeration."""
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    RESPONDED = "responded"
    ESCALATED = "escalated"
    ERROR = "error"


class Email(Base, TimestampMixin):
    """Email model for tracking and processing."""
    
    __tablename__ = "emails"
    
    message_id = Column(String(255), nullable=False, unique=True, index=True)
    thread_id = Column(String(255), nullable=True, index=True)
    subject = Column(String(500), nullable=False)
    sender_email = Column(String(255), nullable=False, index=True)
    sender_name = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=False)
    email_type = Column(Enum(EmailType), nullable=True)
    status = Column(Enum(EmailStatus), default=EmailStatus.RECEIVED, nullable=False)
    
    # Email content
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)  # List of attachment info
    
    # AI processing
    ai_processed = Column(Boolean, default=False, nullable=False)
    ai_confidence = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00
    ai_classification = Column(JSON, nullable=True)  # AI classification results
    ai_extracted_data = Column(JSON, nullable=True)  # Extracted order/customer data
    
    # Processing results
    routed_to_agent = Column(String(100), nullable=True)
    response_sent = Column(Boolean, default=False, nullable=False)
    response_sent_at = Column(DateTime, nullable=True)
    order_created = Column(Boolean, default=False, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    order = relationship("Order")
    
    def __repr__(self):
        return f"<Email(id={self.id}, message_id='{self.message_id}', type='{self.email_type}')>"
