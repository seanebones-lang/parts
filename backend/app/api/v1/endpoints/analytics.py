"""
Analytics endpoints for business intelligence and reporting.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_overview(
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive dashboard overview."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        overview = await service.get_dashboard_overview(
            location_id=location_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return overview
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard overview: {str(e)}")


@router.get("/reports/{report_type}")
async def get_performance_report(
    report_type: str,
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Generate detailed performance reports."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        report = await service.get_performance_report(
            report_type=report_type,
            location_id=location_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        if report["success"]:
            return report
        else:
            raise HTTPException(status_code=400, detail=report["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/metrics/email")
async def get_email_metrics(
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get email processing metrics."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Default to last 30 days
        if not start_dt:
            start_dt = datetime.utcnow() - timedelta(days=30)
        if not end_dt:
            end_dt = datetime.utcnow()
        
        metrics = await service._get_email_metrics(location_id, start_dt, end_dt)
        
        return {
            "success": True,
            "metrics": metrics,
            "period": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get email metrics: {str(e)}")


@router.get("/metrics/orders")
async def get_order_metrics(
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get order processing metrics."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Default to last 30 days
        if not start_dt:
            start_dt = datetime.utcnow() - timedelta(days=30)
        if not end_dt:
            end_dt = datetime.utcnow()
        
        metrics = await service._get_order_metrics(location_id, start_dt, end_dt)
        
        return {
            "success": True,
            "metrics": metrics,
            "period": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order metrics: {str(e)}")


@router.get("/metrics/revenue")
async def get_revenue_metrics(
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get revenue and financial metrics."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Default to last 30 days
        if not start_dt:
            start_dt = datetime.utcnow() - timedelta(days=30)
        if not end_dt:
            end_dt = datetime.utcnow()
        
        metrics = await service._get_revenue_metrics(location_id, start_dt, end_dt)
        
        return {
            "success": True,
            "metrics": metrics,
            "period": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get revenue metrics: {str(e)}")


@router.get("/metrics/inventory")
async def get_inventory_metrics(
    location_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get inventory metrics."""
    try:
        service = AnalyticsService(db)
        
        metrics = await service._get_inventory_metrics(location_id)
        
        return {
            "success": True,
            "metrics": metrics,
            "location_id": location_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get inventory metrics: {str(e)}")


@router.get("/metrics/agents")
async def get_agent_metrics(
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get AI agent performance metrics."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Default to last 30 days
        if not start_dt:
            start_dt = datetime.utcnow() - timedelta(days=30)
        if not end_dt:
            end_dt = datetime.utcnow()
        
        metrics = await service._get_agent_metrics(location_id, start_dt, end_dt)
        
        return {
            "success": True,
            "metrics": metrics,
            "period": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent metrics: {str(e)}")


@router.get("/metrics/customers")
async def get_customer_metrics(
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get customer metrics."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Default to last 30 days
        if not start_dt:
            start_dt = datetime.utcnow() - timedelta(days=30)
        if not end_dt:
            end_dt = datetime.utcnow()
        
        metrics = await service._get_customer_metrics(location_id, start_dt, end_dt)
        
        return {
            "success": True,
            "metrics": metrics,
            "period": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get customer metrics: {str(e)}")


@router.get("/export/{report_type}")
async def export_report(
    report_type: str,
    format: str = Query("json", description="Export format: json, csv, pdf"),
    location_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Export reports in various formats."""
    try:
        service = AnalyticsService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        report = await service.get_performance_report(
            report_type=report_type,
            location_id=location_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        if not report["success"]:
            raise HTTPException(status_code=400, detail=report["error"])
        
        # For now, return JSON format
        # In production, this would generate CSV or PDF files
        return {
            "success": True,
            "format": format,
            "report_type": report_type,
            "data": report,
            "exported_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")
