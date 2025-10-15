"""
Barcode/RFID scanning models and services.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import TimestampMixin
from app.core.database import Base
from enum import Enum
from typing import Optional, List, Dict, Any
import json


class ScanType(str, Enum):
    """Types of scanning operations."""
    BARCODE = "barcode"
    QR_CODE = "qr_code"
    RFID = "rfid"
    MANUAL = "manual"


class ScanStatus(str, Enum):
    """Status of scan operations."""
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class BarcodeScan(Base, TimestampMixin):
    """Model for tracking barcode/RFID scans."""
    
    __tablename__ = "barcode_scans"
    
    # Scan identification
    scan_id = Column(String(100), unique=True, index=True, nullable=False)
    scan_type = Column(String(20), nullable=False)  # barcode, qr_code, rfid
    scan_data = Column(Text, nullable=False)  # Raw scan data
    
    # Part information
    part_number = Column(String(100), nullable=True, index=True)
    manufacturer = Column(String(100), nullable=True)
    part_name = Column(String(255), nullable=True)
    
    # Location and inventory
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Location")
    
    # Scan metadata
    scanned_by = Column(String(100), nullable=True)  # User who scanned
    scan_timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    device_id = Column(String(100), nullable=True)  # Mobile device ID
    gps_coordinates = Column(String(50), nullable=True)  # "lat,lng"
    
    # Processing status
    status = Column(String(20), default=ScanStatus.PENDING)
    processing_time = Column(Float, nullable=True)  # Processing time in seconds
    error_message = Column(Text, nullable=True)
    
    # Additional data
    metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    def set_metadata(self, data: Dict[str, Any]):
        """Set metadata as JSON string."""
        self.metadata = json.dumps(data)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if self.metadata:
            return json.loads(self.metadata)
        return {}


class RFIDTag(Base, TimestampMixin):
    """Model for RFID tag management."""
    
    __tablename__ = "rfid_tags"
    
    # Tag identification
    tag_id = Column(String(100), unique=True, index=True, nullable=False)
    tag_type = Column(String(50), nullable=False)  # passive, active, semi-passive
    frequency = Column(String(20), nullable=True)  # 125kHz, 13.56MHz, 860-960MHz
    
    # Associated part
    part_number = Column(String(100), nullable=True, index=True)
    manufacturer = Column(String(100), nullable=True)
    
    # Location and status
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Location")
    
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    battery_level = Column(Integer, nullable=True)  # For active tags
    
    # Physical properties
    read_range = Column(Float, nullable=True)  # Read range in meters
    temperature_range = Column(String(50), nullable=True)  # Operating temperature
    waterproof_rating = Column(String(20), nullable=True)  # IP rating
    
    # Additional data
    metadata = Column(Text, nullable=True)  # JSON string for additional data


class ScanSession(Base, TimestampMixin):
    """Model for tracking scanning sessions."""
    
    __tablename__ = "scan_sessions"
    
    # Session identification
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User")
    
    # Session details
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Location")
    
    session_type = Column(String(50), nullable=False)  # inventory_check, receiving, shipping
    start_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Session statistics
    total_scans = Column(Integer, default=0)
    successful_scans = Column(Integer, default=0)
    failed_scans = Column(Integer, default=0)
    duplicate_scans = Column(Integer, default=0)
    
    # Device information
    device_id = Column(String(100), nullable=True)
    app_version = Column(String(20), nullable=True)
    
    # Additional data
    metadata = Column(Text, nullable=True)  # JSON string for additional data


class InventoryAudit(Base, TimestampMixin):
    """Model for inventory audit trails."""
    
    __tablename__ = "inventory_audits"
    
    # Audit identification
    audit_id = Column(String(100), unique=True, index=True, nullable=False)
    audit_type = Column(String(50), nullable=False)  # cycle_count, full_inventory, spot_check
    
    # Location and scope
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    location = relationship("Location")
    
    # Audit details
    started_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_by_user = relationship("User")
    
    start_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Audit results
    total_items_scanned = Column(Integer, default=0)
    discrepancies_found = Column(Integer, default=0)
    accuracy_percentage = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default="in_progress")  # in_progress, completed, cancelled
    
    # Additional data
    metadata = Column(Text, nullable=True)  # JSON string for additional data
