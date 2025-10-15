"""
Barcode/RFID scanning API endpoints.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.barcode_service import BarcodeScanService
from app.services.auth_service import get_current_active_user
from app.models.user import User
from app.models.barcode import ScanType, ScanStatus
from pydantic import BaseModel

router = APIRouter()


class ScanRequest(BaseModel):
    """Request model for barcode/RFID scan."""
    scan_data: str
    scan_type: ScanType
    location_id: int
    device_id: Optional[str] = None
    gps_coordinates: Optional[str] = None
    metadata: Optional[dict] = None


class ScanResponse(BaseModel):
    """Response model for scan results."""
    scan_id: str
    status: str
    part_info: Optional[dict] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None


class ScanSessionRequest(BaseModel):
    """Request model for creating scan session."""
    location_id: int
    session_type: str
    device_id: Optional[str] = None
    app_version: Optional[str] = None


class ScanSessionResponse(BaseModel):
    """Response model for scan session."""
    session_id: str
    message: str


class RFIDTagRequest(BaseModel):
    """Request model for RFID tag registration."""
    tag_id: str
    tag_type: str
    part_number: str
    location_id: int
    frequency: Optional[str] = None
    read_range: Optional[float] = None
    metadata: Optional[dict] = None


class InventoryAuditRequest(BaseModel):
    """Request model for inventory audit."""
    location_id: int
    audit_type: str
    metadata: Optional[dict] = None


@router.post("/scan", response_model=ScanResponse)
async def process_scan(
    scan_request: ScanRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Process a barcode/RFID scan."""
    barcode_service = BarcodeScanService(db)
    
    try:
        result = await barcode_service.process_scan(
            scan_data=scan_request.scan_data,
            scan_type=scan_request.scan_type,
            location_id=scan_request.location_id,
            scanned_by=current_user.username,
            device_id=scan_request.device_id,
            gps_coordinates=scan_request.gps_coordinates,
            metadata=scan_request.metadata
        )
        
        return ScanResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan processing failed: {str(e)}"
        )


@router.post("/session", response_model=ScanSessionResponse)
async def create_scan_session(
    session_request: ScanSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new scan session."""
    barcode_service = BarcodeScanService(db)
    
    try:
        session_id = await barcode_service.create_scan_session(
            user_id=current_user.id,
            location_id=session_request.location_id,
            session_type=session_request.session_type,
            device_id=session_request.device_id,
            app_version=session_request.app_version
        )
        
        return ScanSessionResponse(
            session_id=session_id,
            message="Scan session created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scan session: {str(e)}"
        )


@router.post("/session/{session_id}/end")
async def end_scan_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """End a scan session and get statistics."""
    barcode_service = BarcodeScanService(db)
    
    try:
        result = await barcode_service.end_scan_session(session_id)
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end scan session: {str(e)}"
        )


@router.get("/history")
async def get_scan_history(
    location_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get scan history with filters."""
    barcode_service = BarcodeScanService(db)
    
    try:
        scans = await barcode_service.get_scan_history(
            location_id=location_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "scans": [
                {
                    "scan_id": scan.scan_id,
                    "scan_type": scan.scan_type,
                    "scan_data": scan.scan_data,
                    "part_number": scan.part_number,
                    "manufacturer": scan.manufacturer,
                    "part_name": scan.part_name,
                    "location_id": scan.location_id,
                    "scanned_by": scan.scanned_by,
                    "scan_timestamp": scan.scan_timestamp,
                    "status": scan.status,
                    "processing_time": scan.processing_time,
                    "error_message": scan.error_message,
                    "metadata": scan.get_metadata()
                }
                for scan in scans
            ],
            "total": len(scans)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scan history: {str(e)}"
        )


@router.post("/rfid/register")
async def register_rfid_tag(
    tag_request: RFIDTagRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Register a new RFID tag."""
    barcode_service = BarcodeScanService(db)
    
    try:
        tag = await barcode_service.register_rfid_tag(
            tag_id=tag_request.tag_id,
            tag_type=tag_request.tag_type,
            part_number=tag_request.part_number,
            location_id=tag_request.location_id,
            frequency=tag_request.frequency,
            read_range=tag_request.read_range,
            metadata=tag_request.metadata
        )
        
        return {
            "tag_id": tag.tag_id,
            "tag_type": tag.tag_type,
            "part_number": tag.part_number,
            "location_id": tag.location_id,
            "is_active": tag.is_active,
            "message": "RFID tag registered successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register RFID tag: {str(e)}"
        )


@router.get("/rfid/tags")
async def get_rfid_tags(
    location_id: Optional[int] = Query(None),
    part_number: Optional[str] = Query(None),
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get RFID tags with filters."""
    barcode_service = BarcodeScanService(db)
    
    try:
        tags = await barcode_service.get_rfid_tags(
            location_id=location_id,
            part_number=part_number,
            active_only=active_only
        )
        
        return {
            "tags": [
                {
                    "tag_id": tag.tag_id,
                    "tag_type": tag.tag_type,
                    "frequency": tag.frequency,
                    "part_number": tag.part_number,
                    "location_id": tag.location_id,
                    "is_active": tag.is_active,
                    "last_seen": tag.last_seen,
                    "battery_level": tag.battery_level,
                    "read_range": tag.read_range,
                    "metadata": tag.get_metadata()
                }
                for tag in tags
            ],
            "total": len(tags)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RFID tags: {str(e)}"
        )


@router.post("/audit")
async def create_inventory_audit(
    audit_request: InventoryAuditRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new inventory audit."""
    barcode_service = BarcodeScanService(db)
    
    try:
        audit_id = await barcode_service.create_inventory_audit(
            location_id=audit_request.location_id,
            audit_type=audit_request.audit_type,
            started_by=current_user.id,
            metadata=audit_request.metadata
        )
        
        return {
            "audit_id": audit_id,
            "message": "Inventory audit created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create inventory audit: {str(e)}"
        )


@router.post("/audit/{audit_id}/complete")
async def complete_inventory_audit(
    audit_id: str,
    total_items_scanned: int,
    discrepancies_found: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete an inventory audit."""
    barcode_service = BarcodeScanService(db)
    
    try:
        result = await barcode_service.complete_inventory_audit(
            audit_id=audit_id,
            total_items_scanned=total_items_scanned,
            discrepancies_found=discrepancies_found
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete inventory audit: {str(e)}"
        )


@router.get("/statistics")
async def get_scan_statistics(
    location_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get scan statistics for a period."""
    barcode_service = BarcodeScanService(db)
    
    try:
        stats = await barcode_service.get_scan_statistics(
            location_id=location_id,
            days=days
        )
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scan statistics: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check for barcode scanning service."""
    return {
        "status": "healthy",
        "service": "barcode_scanning",
        "timestamp": datetime.utcnow().isoformat()
    }
