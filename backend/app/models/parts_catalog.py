"""
Parts catalog model with vector embeddings for semantic search.
"""

from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import TimestampMixin
from app.core.database import Base


class PartsCatalog(Base, TimestampMixin):
    """Parts catalog model with vector embeddings."""
    
    __tablename__ = "parts_catalog"
    
    part_number = Column(String(100), nullable=False, unique=True, index=True)
    manufacturer = Column(String(100), nullable=False, index=True)
    part_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)
    make = Column(String(50), nullable=True, index=True)
    model = Column(String(100), nullable=True, index=True)
    year_from = Column(Integer, nullable=True)
    year_to = Column(Integer, nullable=True)
    engine = Column(String(100), nullable=True)
    transmission = Column(String(100), nullable=True)
    body_style = Column(String(100), nullable=True)
    compatible_parts = Column(ARRAY(String), nullable=True)
    msrp = Column(Numeric(10, 2), nullable=True)
    cost = Column(Numeric(10, 2), nullable=True)
    weight = Column(Numeric(8, 2), nullable=True)
    dimensions = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    vector_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="part")
    order_items = relationship("OrderItem", back_populates="part")
    
    def __repr__(self):
        return f"<PartsCatalog(id={self.id}, part_number='{self.part_number}', name='{self.part_name}')>"
