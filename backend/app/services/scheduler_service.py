"""
Scheduler service for managing follow-up schedules and timing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.followup import Followup, FollowupStatus, FollowupType


class SchedulerService:
    """Service for scheduling and managing follow-ups."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def schedule_followup(
        self,
        followup_type: str,
        customer_id: int,
        related_id: int,
        scheduled_time: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Schedule a follow-up action."""
        try:
            # Parse scheduled time
            if scheduled_time:
                scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
            else:
                # Default scheduling based on follow-up type
                scheduled_dt = self._get_default_scheduled_time(followup_type)
            
            # Create follow-up record
            followup = Followup(
                followup_type=FollowupType(followup_type),
                customer_id=customer_id,
                related_id=related_id,
                scheduled_time=scheduled_dt,
                priority=priority,
                status=FollowupStatus.PENDING,
                metadata=str(metadata) if metadata else None
            )
            
            self.db.add(followup)
            await self.db.commit()
            await self.db.refresh(followup)
            
            return {
                "success": True,
                "followup_id": followup.id,
                "followup_type": followup_type,
                "customer_id": customer_id,
                "related_id": related_id,
                "scheduled_time": scheduled_dt.isoformat(),
                "priority": priority
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def cancel_followup(
        self,
        followup_id: int,
        reason: str = "Cancelled by request"
    ) -> Dict[str, Any]:
        """Cancel a scheduled follow-up."""
        try:
            query = select(Followup).where(Followup.id == followup_id)
            result = await self.db.execute(query)
            followup = result.scalar_one_or_none()
            
            if not followup:
                return {"success": False, "error": "Follow-up not found"}
            
            if followup.status != FollowupStatus.PENDING:
                return {"success": False, "error": "Cannot cancel completed follow-up"}
            
            followup.status = FollowupStatus.CANCELLED
            followup.cancelled_at = datetime.utcnow()
            followup.cancellation_reason = reason
            
            await self.db.commit()
            
            return {
                "success": True,
                "followup_id": followup_id,
                "status": "cancelled",
                "reason": reason,
                "cancelled_at": followup.cancelled_at.isoformat()
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def reschedule_followup(
        self,
        followup_id: int,
        new_time: str,
        reason: str = "Rescheduled"
    ) -> Dict[str, Any]:
        """Reschedule a follow-up to a new time."""
        try:
            query = select(Followup).where(Followup.id == followup_id)
            result = await self.db.execute(query)
            followup = result.scalar_one_or_none()
            
            if not followup:
                return {"success": False, "error": "Follow-up not found"}
            
            if followup.status != FollowupStatus.PENDING:
                return {"success": False, "error": "Cannot reschedule completed follow-up"}
            
            new_scheduled_time = datetime.fromisoformat(new_time.replace('Z', '+00:00'))
            
            followup.scheduled_time = new_scheduled_time
            followup.rescheduled_at = datetime.utcnow()
            followup.reschedule_reason = reason
            
            await self.db.commit()
            
            return {
                "success": True,
                "followup_id": followup_id,
                "new_scheduled_time": new_scheduled_time.isoformat(),
                "reason": reason,
                "rescheduled_at": followup.rescheduled_at.isoformat()
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def get_upcoming_followups(
        self,
        hours_ahead: int = 24,
        followup_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get follow-ups scheduled within the next N hours."""
        try:
            now = datetime.utcnow()
            cutoff_time = now + timedelta(hours=hours_ahead)
            
            query = select(Followup).where(
                Followup.status == FollowupStatus.PENDING,
                Followup.scheduled_time >= now,
                Followup.scheduled_time <= cutoff_time
            )
            
            if followup_type:
                query = query.where(Followup.followup_type == FollowupType(followup_type))
            
            query = query.order_by(Followup.scheduled_time.asc())
            
            result = await self.db.execute(query)
            followups = result.scalars().all()
            
            return [
                {
                    "id": followup.id,
                    "followup_type": followup.followup_type.value,
                    "customer_id": followup.customer_id,
                    "related_id": followup.related_id,
                    "scheduled_time": followup.scheduled_time.isoformat(),
                    "priority": followup.priority,
                    "minutes_until_due": int((followup.scheduled_time - now).total_seconds() / 60)
                }
                for followup in followups
            ]
            
        except Exception as e:
            print(f"Error getting upcoming follow-ups: {e}")
            return []
    
    async def get_overdue_followups(self) -> List[Dict[str, Any]]:
        """Get follow-ups that are overdue."""
        try:
            now = datetime.utcnow()
            
            query = select(Followup).where(
                Followup.status == FollowupStatus.PENDING,
                Followup.scheduled_time < now
            ).order_by(Followup.scheduled_time.asc())
            
            result = await self.db.execute(query)
            followups = result.scalars().all()
            
            return [
                {
                    "id": followup.id,
                    "followup_type": followup.followup_type.value,
                    "customer_id": followup.customer_id,
                    "related_id": followup.related_id,
                    "scheduled_time": followup.scheduled_time.isoformat(),
                    "priority": followup.priority,
                    "overdue_minutes": int((now - followup.scheduled_time).total_seconds() / 60)
                }
                for followup in followups
            ]
            
        except Exception as e:
            print(f"Error getting overdue follow-ups: {e}")
            return []
    
    async def get_followup_schedule(
        self,
        customer_id: Optional[int] = None,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get follow-up schedule for a customer or all customers."""
        try:
            now = datetime.utcnow()
            end_time = now + timedelta(days=days_ahead)
            
            query = select(Followup).where(
                Followup.scheduled_time >= now,
                Followup.scheduled_time <= end_time
            )
            
            if customer_id:
                query = query.where(Followup.customer_id == customer_id)
            
            query = query.order_by(Followup.scheduled_time.asc())
            
            result = await self.db.execute(query)
            followups = result.scalars().all()
            
            return [
                {
                    "id": followup.id,
                    "followup_type": followup.followup_type.value,
                    "customer_id": followup.customer_id,
                    "related_id": followup.related_id,
                    "scheduled_time": followup.scheduled_time.isoformat(),
                    "priority": followup.priority,
                    "status": followup.status.value,
                    "days_until_due": (followup.scheduled_time - now).days
                }
                for followup in followups
            ]
            
        except Exception as e:
            print(f"Error getting follow-up schedule: {e}")
            return []
    
    async def bulk_schedule_followups(
        self,
        followup_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Schedule multiple follow-ups in bulk."""
        try:
            created_followups = []
            errors = []
            
            for data in followup_data:
                try:
                    result = await self.schedule_followup(
                        followup_type=data["followup_type"],
                        customer_id=data["customer_id"],
                        related_id=data["related_id"],
                        scheduled_time=data.get("scheduled_time"),
                        priority=data.get("priority", "normal"),
                        metadata=data.get("metadata")
                    )
                    
                    if result["success"]:
                        created_followups.append(result)
                    else:
                        errors.append({"data": data, "error": result["error"]})
                        
                except Exception as e:
                    errors.append({"data": data, "error": str(e)})
            
            return {
                "success": len(errors) == 0,
                "created_count": len(created_followups),
                "error_count": len(errors),
                "created_followups": created_followups,
                "errors": errors
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_default_scheduled_time(self, followup_type: str) -> datetime:
        """Get default scheduled time based on follow-up type."""
        now = datetime.utcnow()
        
        if followup_type == "quote":
            # Quote follow-up: 24 hours after quote creation
            return now + timedelta(hours=24)
        elif followup_type == "payment":
            # Payment reminder: on due date
            return now + timedelta(days=30)  # Default 30 days
        elif followup_type == "shipping":
            # Shipping update: immediate
            return now
        elif followup_type == "satisfaction":
            # Satisfaction survey: 3 days after delivery
            return now + timedelta(days=3)
        else:
            # Default: 24 hours
            return now + timedelta(hours=24)
    
    async def get_scheduler_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics and metrics."""
        try:
            now = datetime.utcnow()
            
            # Get counts by status
            total_query = select(Followup)
            total_result = await self.db.execute(total_query)
            total_followups = len(total_result.scalars().all())
            
            pending_query = select(Followup).where(Followup.status == FollowupStatus.PENDING)
            pending_result = await self.db.execute(pending_query)
            pending_count = len(pending_result.scalars().all())
            
            completed_query = select(Followup).where(Followup.status == FollowupStatus.COMPLETED)
            completed_result = await self.db.execute(completed_query)
            completed_count = len(completed_result.scalars().all())
            
            cancelled_query = select(Followup).where(Followup.status == FollowupStatus.CANCELLED)
            cancelled_result = await self.db.execute(cancelled_query)
            cancelled_count = len(cancelled_result.scalars().all())
            
            # Get overdue count
            overdue_query = select(Followup).where(
                Followup.status == FollowupStatus.PENDING,
                Followup.scheduled_time < now
            )
            overdue_result = await self.db.execute(overdue_query)
            overdue_count = len(overdue_result.scalars().all())
            
            # Get upcoming count (next 24 hours)
            upcoming_query = select(Followup).where(
                Followup.status == FollowupStatus.PENDING,
                Followup.scheduled_time >= now,
                Followup.scheduled_time <= now + timedelta(hours=24)
            )
            upcoming_result = await self.db.execute(upcoming_query)
            upcoming_count = len(upcoming_result.scalars().all())
            
            return {
                "total_followups": total_followups,
                "pending_count": pending_count,
                "completed_count": completed_count,
                "cancelled_count": cancelled_count,
                "overdue_count": overdue_count,
                "upcoming_24h": upcoming_count,
                "completion_rate": completed_count / total_followups if total_followups > 0 else 0,
                "overdue_rate": overdue_count / pending_count if pending_count > 0 else 0
            }
            
        except Exception as e:
            print(f"Error getting scheduler statistics: {e}")
            return {}
    
    async def cleanup_old_followups(self, days_old: int = 90) -> Dict[str, Any]:
        """Clean up old completed follow-ups."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # This would delete old completed follow-ups
            # For now, just return success
            return {
                "success": True,
                "cleaned_up_count": 0,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
