"""
Barcode/RFID scanning service.
"""

import uuid
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.barcode import BarcodeScan, RFIDTag, ScanSession, InventoryAudit, ScanType, ScanStatus
from app.models.parts_catalog import PartsCatalog
from app.models.inventory import Inventory
from app.models.location import Location
from app.models.user import User


class BarcodeScanService:
    """Service for handling barcode/RFID scanning operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_scan_id(self) -> str:
        """Generate unique scan ID."""
        return f"SCAN_{uuid.uuid4().hex[:12].upper()}"
    
    def generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"SESS_{uuid.uuid4().hex[:12].upper()}"
    
    def generate_audit_id(self) -> str:
        """Generate unique audit ID."""
        return f"AUDIT_{uuid.uuid4().hex[:12].upper()}"
    
    async def process_scan(
        self,
        scan_data: str,
        scan_type: ScanType,
        location_id: int,
        scanned_by: str,
        device_id: Optional[str] = None,
        gps_coordinates: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a barcode/RFID scan."""
        start_time = datetime.utcnow()
        
        # Generate scan ID
        scan_id = self.generate_scan_id()
        
        # Create scan record
        scan = BarcodeScan(
            scan_id=scan_id,
            scan_type=scan_type.value,
            scan_data=scan_data,
            scanned_by=scanned_by,
            location_id=location_id,
            device_id=device_id,
            gps_coordinates=gps_coordinates,
            scan_timestamp=start_time,
            status=ScanStatus.PENDING
        )
        
        if metadata:
            scan.set_metadata(metadata)
        
        self.db.add(scan)
        
        try:
            # Process the scan based on type
            result = await self._process_scan_data(scan_data, scan_type, location_id)
            
            # Update scan with results
            scan.part_number = result.get("part_number")
            scan.manufacturer = result.get("manufacturer")
            scan.part_name = result.get("part_name")
            scan.status = ScanStatus.PROCESSED
            scan.processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            await self.db.commit()
            
            return {
                "scan_id": scan_id,
                "status": "success",
                "part_info": result,
                "processing_time": scan.processing_time
            }
            
        except Exception as e:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            scan.processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            await self.db.commit()
            
            return {
                "scan_id": scan_id,
                "status": "error",
                "error": str(e),
                "processing_time": scan.processing_time
            }
    
    async def _process_scan_data(
        self,
        scan_data: str,
        scan_type: ScanType,
        location_id: int
    ) -> Dict[str, Any]:
        """Process scan data and extract part information."""
        
        if scan_type == ScanType.BARCODE:
            return await self._process_barcode(scan_data, location_id)
        elif scan_type == ScanType.QR_CODE:
            return await self._process_qr_code(scan_data, location_id)
        elif scan_type == ScanType.RFID:
            return await self._process_rfid(scan_data, location_id)
        else:
            raise ValueError(f"Unsupported scan type: {scan_type}")
    
    async def _process_barcode(self, barcode: str, location_id: int) -> Dict[str, Any]:
        """Process barcode scan."""
        # Clean barcode data
        barcode = barcode.strip()
        
        # Try to find part by barcode/part number
        query = select(PartsCatalog).where(
            or_(
                PartsCatalog.part_number == barcode,
                PartsCatalog.barcode == barcode
            )
        )
        result = await self.db.execute(query)
        part = result.scalar_one_or_none()
        
        if part:
            # Check inventory at location
            inventory_query = select(Inventory).where(
                and_(
                    Inventory.part_id == part.id,
                    Inventory.location_id == location_id
                )
            )
            inventory_result = await self.db.execute(inventory_query)
            inventory = inventory_result.scalar_one_or_none()
            
            return {
                "part_number": part.part_number,
                "manufacturer": part.manufacturer,
                "part_name": part.part_name,
                "description": part.description,
                "current_stock": inventory.quantity if inventory else 0,
                "reorder_point": inventory.reorder_point if inventory else 0,
                "unit_price": part.unit_price,
                "found": True
            }
        else:
            # Try to extract part number from barcode using common patterns
            part_number = self._extract_part_number_from_barcode(barcode)
            if part_number:
                return await self._process_barcode(part_number, location_id)
            
            return {
                "part_number": barcode,
                "found": False,
                "message": "Part not found in catalog"
            }
    
    async def _process_qr_code(self, qr_data: str, location_id: int) -> Dict[str, Any]:
        """Process QR code scan."""
        try:
            # Try to parse as JSON first
            qr_json = json.loads(qr_data)
            if "part_number" in qr_json:
                return await self._process_barcode(qr_json["part_number"], location_id)
        except json.JSONDecodeError:
            pass
        
        # Try to extract part number from QR data
        part_number = self._extract_part_number_from_qr(qr_data)
        if part_number:
            return await self._process_barcode(part_number, location_id)
        
        # Treat as regular barcode
        return await self._process_barcode(qr_data, location_id)
    
    async def _process_rfid(self, rfid_data: str, location_id: int) -> Dict[str, Any]:
        """Process RFID scan."""
        # Look up RFID tag
        query = select(RFIDTag).where(RFIDTag.tag_id == rfid_data)
        result = await self.db.execute(query)
        tag = result.scalar_one_or_none()
        
        if tag and tag.part_number:
            # Update last seen
            tag.last_seen = datetime.utcnow()
            await self.db.commit()
            
            return await self._process_barcode(tag.part_number, location_id)
        else:
            return {
                "tag_id": rfid_data,
                "found": False,
                "message": "RFID tag not found or not associated with a part"
            }
    
    def _extract_part_number_from_barcode(self, barcode: str) -> Optional[str]:
        """Extract part number from barcode using common patterns."""
        # Common patterns for part numbers in barcodes
        patterns = [
            r'^(\d{4,12})$',  # Simple numeric part numbers
            r'^([A-Z]{2,4}\d{4,8})$',  # Alphanumeric part numbers
            r'^(\d{4,8}[A-Z]{1,3})$',  # Numeric + letters
        ]
        
        for pattern in patterns:
            match = re.match(pattern, barcode)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_part_number_from_qr(self, qr_data: str) -> Optional[str]:
        """Extract part number from QR code data."""
        # Look for part number patterns in QR data
        patterns = [
            r'part[_-]?number[:\s]*([A-Z0-9]{4,12})',
            r'pn[:\s]*([A-Z0-9]{4,12})',
            r'part[:\s]*([A-Z0-9]{4,12})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, qr_data, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    async def create_scan_session(
        self,
        user_id: int,
        location_id: int,
        session_type: str,
        device_id: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> str:
        """Create a new scan session."""
        session_id = self.generate_session_id()
        
        session = ScanSession(
            session_id=session_id,
            user_id=user_id,
            location_id=location_id,
            session_type=session_type,
            device_id=device_id,
            app_version=app_version
        )
        
        self.db.add(session)
        await self.db.commit()
        
        return session_id
    
    async def end_scan_session(self, session_id: str) -> Dict[str, Any]:
        """End a scan session and return statistics."""
        query = select(ScanSession).where(ScanSession.session_id == session_id)
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
        
        session.end_time = datetime.utcnow()
        
        # Get scan statistics for this session
        scans_query = select(BarcodeScan).where(
            and_(
                BarcodeScan.scanned_by == session.user_id,
                BarcodeScan.scan_timestamp >= session.start_time,
                BarcodeScan.scan_timestamp <= session.end_time
            )
        )
        scans_result = await self.db.execute(scans_query)
        scans = scans_result.scalars().all()
        
        # Calculate statistics
        total_scans = len(scans)
        successful_scans = len([s for s in scans if s.status == ScanStatus.PROCESSED])
        failed_scans = len([s for s in scans if s.status == ScanStatus.FAILED])
        duplicate_scans = len([s for s in scans if s.status == ScanStatus.DUPLICATE])
        
        session.total_scans = total_scans
        session.successful_scans = successful_scans
        session.failed_scans = failed_scans
        session.duplicate_scans = duplicate_scans
        
        await self.db.commit()
        
        return {
            "session_id": session_id,
            "duration": (session.end_time - session.start_time).total_seconds(),
            "total_scans": total_scans,
            "successful_scans": successful_scans,
            "failed_scans": failed_scans,
            "duplicate_scans": duplicate_scans,
            "success_rate": (successful_scans / total_scans * 100) if total_scans > 0 else 0
        }
    
    async def get_scan_history(
        self,
        location_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[BarcodeScan]:
        """Get scan history with filters."""
        query = select(BarcodeScan)
        
        if location_id:
            query = query.where(BarcodeScan.location_id == location_id)
        
        if user_id:
            query = query.where(BarcodeScan.scanned_by == user_id)
        
        if start_date:
            query = query.where(BarcodeScan.scan_timestamp >= start_date)
        
        if end_date:
            query = query.where(BarcodeScan.scan_timestamp <= end_date)
        
        query = query.order_by(desc(BarcodeScan.scan_timestamp)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_inventory_audit(
        self,
        location_id: int,
        audit_type: str,
        started_by: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new inventory audit."""
        audit_id = self.generate_audit_id()
        
        audit = InventoryAudit(
            audit_id=audit_id,
            audit_type=audit_type,
            location_id=location_id,
            started_by=started_by
        )
        
        if metadata:
            audit.set_metadata(metadata)
        
        self.db.add(audit)
        await self.db.commit()
        
        return audit_id
    
    async def complete_inventory_audit(
        self,
        audit_id: str,
        total_items_scanned: int,
        discrepancies_found: int
    ) -> Dict[str, Any]:
        """Complete an inventory audit."""
        query = select(InventoryAudit).where(InventoryAudit.audit_id == audit_id)
        result = await self.db.execute(query)
        audit = result.scalar_one_or_none()
        
        if not audit:
            raise ValueError("Audit not found")
        
        audit.end_time = datetime.utcnow()
        audit.total_items_scanned = total_items_scanned
        audit.discrepancies_found = discrepancies_found
        audit.accuracy_percentage = (
            (total_items_scanned - discrepancies_found) / total_items_scanned * 100
        ) if total_items_scanned > 0 else 0
        audit.status = "completed"
        
        await self.db.commit()
        
        return {
            "audit_id": audit_id,
            "duration": (audit.end_time - audit.start_time).total_seconds(),
            "total_items_scanned": total_items_scanned,
            "discrepancies_found": discrepancies_found,
            "accuracy_percentage": audit.accuracy_percentage
        }
    
    async def register_rfid_tag(
        self,
        tag_id: str,
        tag_type: str,
        part_number: str,
        location_id: int,
        frequency: Optional[str] = None,
        read_range: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RFIDTag:
        """Register a new RFID tag."""
        tag = RFIDTag(
            tag_id=tag_id,
            tag_type=tag_type,
            part_number=part_number,
            location_id=location_id,
            frequency=frequency,
            read_range=read_range
        )
        
        if metadata:
            tag.set_metadata(metadata)
        
        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        
        return tag
    
    async def get_rfid_tags(
        self,
        location_id: Optional[int] = None,
        part_number: Optional[str] = None,
        active_only: bool = True
    ) -> List[RFIDTag]:
        """Get RFID tags with filters."""
        query = select(RFIDTag)
        
        if location_id:
            query = query.where(RFIDTag.location_id == location_id)
        
        if part_number:
            query = query.where(RFIDTag.part_number == part_number)
        
        if active_only:
            query = query.where(RFIDTag.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_scan_statistics(
        self,
        location_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get scan statistics for a period."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(BarcodeScan).where(BarcodeScan.scan_timestamp >= start_date)
        
        if location_id:
            query = query.where(BarcodeScan.location_id == location_id)
        
        result = await self.db.execute(query)
        scans = result.scalars().all()
        
        # Calculate statistics
        total_scans = len(scans)
        successful_scans = len([s for s in scans if s.status == ScanStatus.PROCESSED])
        failed_scans = len([s for s in scans if s.status == ScanStatus.FAILED])
        duplicate_scans = len([s for s in scans if s.status == ScanStatus.DUPLICATE])
        
        # Scan type breakdown
        scan_types = {}
        for scan in scans:
            scan_type = scan.scan_type
            scan_types[scan_type] = scan_types.get(scan_type, 0) + 1
        
        # Daily breakdown
        daily_scans = {}
        for scan in scans:
            date_str = scan.scan_timestamp.date().isoformat()
            daily_scans[date_str] = daily_scans.get(date_str, 0) + 1
        
        return {
            "period_days": days,
            "total_scans": total_scans,
            "successful_scans": successful_scans,
            "failed_scans": failed_scans,
            "duplicate_scans": duplicate_scans,
            "success_rate": (successful_scans / total_scans * 100) if total_scans > 0 else 0,
            "scan_types": scan_types,
            "daily_scans": daily_scans,
            "average_processing_time": sum(s.processing_time or 0 for s in scans) / total_scans if total_scans > 0 else 0
        }
