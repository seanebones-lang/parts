"""
Rollout endpoints for multi-location deployment management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.rollout_service import RolloutService

router = APIRouter()


@router.get("/status")
async def get_rollout_status(
    db: AsyncSession = Depends(get_db)
):
    """Get overall rollout status across all locations."""
    try:
        service = RolloutService(db)
        status = await service.get_rollout_status()
        
        if status["success"]:
            return status
        else:
            raise HTTPException(status_code=400, detail=status["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rollout status: {str(e)}")


@router.get("/progress/{location_id}")
async def get_deployment_progress(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed deployment progress for a specific location."""
    try:
        service = RolloutService(db)
        progress = await service.get_deployment_progress(location_id)
        
        if progress["success"]:
            return progress
        else:
            raise HTTPException(status_code=400, detail=progress["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment progress: {str(e)}")


@router.post("/start/{location_id}")
async def start_location_deployment(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Start deployment process for a specific location."""
    try:
        service = RolloutService(db)
        result = await service.start_location_deployment(location_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start deployment: {str(e)}")


@router.get("/metrics/enterprise")
async def get_enterprise_metrics(
    db: AsyncSession = Depends(get_db)
):
    """Get enterprise-wide metrics across all locations."""
    try:
        service = RolloutService(db)
        metrics = await service.get_enterprise_metrics()
        
        if metrics["success"]:
            return metrics
        else:
            raise HTTPException(status_code=400, detail=metrics["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get enterprise metrics: {str(e)}")


@router.get("/report")
async def generate_rollout_report(
    db: AsyncSession = Depends(get_db)
):
    """Generate comprehensive rollout status report."""
    try:
        service = RolloutService(db)
        report = await service.generate_rollout_report()
        
        if report["success"]:
            return report
        else:
            raise HTTPException(status_code=400, detail=report["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate rollout report: {str(e)}")


@router.get("/timeline")
async def get_rollout_timeline(
    db: AsyncSession = Depends(get_db)
):
    """Get complete rollout timeline."""
    try:
        service = RolloutService(db)
        status = await service.get_rollout_status()
        
        if status["success"]:
            return {
                "success": True,
                "timeline": status["rollout_timeline"],
                "next_deployment": status["next_deployment"]
            }
        else:
            raise HTTPException(status_code=400, detail=status["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rollout timeline: {str(e)}")


@router.get("/locations/{location_id}/training")
async def get_location_training_status(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get training status for a specific location."""
    try:
        service = RolloutService(db)
        
        # This would get actual training data
        # For now, return mock data based on rollout phase
        rollout_phase = service._get_rollout_phase(location_id)
        training_status = await service._get_staff_training_status(location_id)
        
        return {
            "success": True,
            "location_id": location_id,
            "rollout_phase": rollout_phase,
            "training_status": training_status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training status: {str(e)}")


@router.get("/locations/{location_id}/performance")
async def get_location_performance(
    location_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics for a specific location."""
    try:
        service = RolloutService(db)
        performance = await service._get_location_performance(location_id)
        
        return {
            "success": True,
            "location_id": location_id,
            "performance_metrics": performance
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get location performance: {str(e)}")


@router.get("/summary")
async def get_rollout_summary(
    db: AsyncSession = Depends(get_db)
):
    """Get high-level rollout summary."""
    try:
        service = RolloutService(db)
        status = await service.get_rollout_status()
        metrics = await service.get_enterprise_metrics()
        
        if status["success"] and metrics["success"]:
            return {
                "success": True,
                "summary": {
                    "total_locations": 7,
                    "deployed_locations": status["rollout_status"]["deployed_locations"],
                    "in_progress_locations": status["rollout_status"]["in_progress_locations"],
                    "pending_locations": status["rollout_status"]["pending_locations"],
                    "rollout_progress": status["rollout_status"]["rollout_progress"],
                    "enterprise_metrics": metrics["enterprise_metrics"],
                    "rollout_impact": metrics["rollout_impact"]
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to get rollout data")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rollout summary: {str(e)}")
