"""
Deployment endpoints for pilot deployment management and monitoring.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user_if_production
from app.core.database import get_db
from app.models.user import User
from app.services.deployment_service import DeploymentService

router = APIRouter()


@router.get("/status/{location_id}")
async def get_deployment_status(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get deployment status for a specific location."""
    try:
        service = DeploymentService(db)
        status = await service.get_deployment_status(location_id)
        
        if status["success"]:
            return status
        else:
            raise HTTPException(status_code=400, detail=status["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment status: {str(e)}")


@router.get("/training/{location_id}")
async def get_staff_training_progress(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get staff training progress for a location."""
    try:
        service = DeploymentService(db)
        training = await service.get_staff_training_progress(location_id)
        
        if training.get("success", True):
            return training
        else:
            raise HTTPException(status_code=400, detail=training["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training progress: {str(e)}")


@router.get("/feedback/{location_id}")
async def get_pilot_feedback(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get pilot feedback and issues for a location."""
    try:
        service = DeploymentService(db)
        feedback = await service.get_pilot_feedback(location_id)
        
        if feedback.get("success", True):
            return feedback
        else:
            raise HTTPException(status_code=400, detail=feedback["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pilot feedback: {str(e)}")


@router.get("/metrics/{location_id}")
async def get_pilot_metrics_comparison(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get pilot metrics comparison for a location."""
    try:
        service = DeploymentService(db)
        metrics = await service.get_pilot_metrics_comparison(location_id)
        
        if metrics.get("success", True):
            return metrics
        else:
            raise HTTPException(status_code=400, detail=metrics["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pilot metrics: {str(e)}")


@router.get("/report/{location_id}")
async def generate_pilot_report(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate comprehensive pilot deployment report."""
    try:
        service = DeploymentService(db)
        report = await service.generate_pilot_report(location_id)
        
        if report["success"]:
            return report
        else:
            raise HTTPException(status_code=400, detail=report["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate pilot report: {str(e)}")


@router.put("/status/{location_id}")
async def update_deployment_status(
    location_id: int,
    status: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Update deployment status for a location."""
    _ = current_user
    try:
        service = DeploymentService(db)
        result = await service.update_deployment_status(location_id, status, notes)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update deployment status: {str(e)}")


@router.get("/health/{location_id}")
async def get_system_health(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get system health for a location."""
    try:
        service = DeploymentService(db)
        status = await service.get_deployment_status(location_id)
        
        if status["success"]:
            return {
                "success": True,
                "location_id": location_id,
                "system_health": status["system_health"],
                "checked_at": status["system_health"]["last_health_check"]
            }
        else:
            raise HTTPException(status_code=400, detail=status["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")


@router.get("/overview")
async def get_all_deployments_overview(
    db: AsyncSession = Depends(get_db)
):
    """Get overview of all deployments."""
    try:
        service = DeploymentService(db)
        
        # Get status for all locations (1-7)
        deployments = []
        for location_id in range(1, 8):
            status = await service.get_deployment_status(location_id)
            if status["success"]:
                deployments.append({
                    "location_id": location_id,
                    "location_name": status["location"]["name"],
                    "status": status["location"]["status"],
                    "deployed_at": status["location"]["deployed_at"],
                    "system_health": status["system_health"]["api_status"],
                    "uptime": status["system_health"]["uptime_percentage"]
                })
        
        return {
            "success": True,
            "total_locations": 7,
            "deployed_locations": len([d for d in deployments if d["status"] == "deployed"]),
            "deployments": deployments
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployments overview: {str(e)}")
