"""
Celery configuration for background tasks.
"""

from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "dealership_parts",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.ai_tasks", 
        "app.tasks.inventory_tasks",
        "app.tasks.shipping_tasks",
        "app.tasks.followup_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "process-emails": {
        "task": "app.tasks.email_tasks.process_new_emails",
        "schedule": 30.0,  # Every 30 seconds
    },
    "check-inventory-levels": {
        "task": "app.tasks.inventory_tasks.check_reorder_points",
        "schedule": 3600.0,  # Every hour
    },
    "update-shipment-tracking": {
        "task": "app.tasks.shipping_tasks.update_shipment_tracking",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "send-follow-up-emails": {
        "task": "app.tasks.followup_tasks.send_scheduled_followups",
        "schedule": 3600.0,  # Every hour
    },
}
