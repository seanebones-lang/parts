"""
Webhooks system for third-party integrations.
"""

import json
import hashlib
import hmac
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from enum import Enum
import httpx

from app.models.base import TimestampMixin
from app.core.database import Base
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey


class WebhookEvent(str, Enum):
    """Webhook event types."""
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_COMPLETED = "order.completed"
    ORDER_CANCELLED = "order.cancelled"
    PAYMENT_RECEIVED = "payment.received"
    PAYMENT_FAILED = "payment.failed"
    INVENTORY_LOW = "inventory.low"
    INVENTORY_EXPIRED = "inventory.expired"
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_DELIVERED = "shipment.delivered"
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    PART_CREATED = "part.created"
    PART_UPDATED = "part.updated"


class WebhookStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DISABLED = "disabled"


class WebhookSubscription(Base, TimestampMixin):
    """Model for webhook subscriptions."""
    
    __tablename__ = "webhook_subscriptions"
    
    # Subscription details
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)  # For signature verification
    
    # Event filtering
    events = Column(Text, nullable=False)  # JSON array of event types
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Delivery settings
    timeout_seconds = Column(Integer, default=30, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay_seconds = Column(Integer, default=60, nullable=False)
    
    # Statistics
    total_deliveries = Column(Integer, default=0, nullable=False)
    successful_deliveries = Column(Integer, default=0, nullable=False)
    failed_deliveries = Column(Integer, default=0, nullable=False)
    last_delivery_attempt = Column(DateTime(timezone=True), nullable=True)
    last_successful_delivery = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data
    metadata = Column(Text, nullable=True)  # JSON string for additional data


class WebhookDelivery(Base, TimestampMixin):
    """Model for webhook delivery attempts."""
    
    __tablename__ = "webhook_deliveries"
    
    # Subscription reference
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id"), nullable=False)
    subscription = relationship("WebhookSubscription")
    
    # Delivery details
    event_type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)  # JSON payload
    headers = Column(Text, nullable=True)  # JSON headers
    
    # Delivery status
    status = Column(String(20), default=WebhookStatus.PENDING, nullable=False)
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Retry information
    attempt_number = Column(Integer, default=1, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timing
    delivery_started_at = Column(DateTime(timezone=True), nullable=True)
    delivery_completed_at = Column(DateTime(timezone=True), nullable=True)


class WebhookService:
    """Service for managing webhooks."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def create_subscription(
        self,
        name: str,
        url: str,
        events: List[WebhookEvent],
        secret: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        retry_delay_seconds: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebhookSubscription:
        """Create a new webhook subscription."""
        
        subscription = WebhookSubscription(
            name=name,
            url=url,
            secret=secret,
            events=json.dumps([event.value for event in events]),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds
        )
        
        if metadata:
            subscription.metadata = json.dumps(metadata)
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        return subscription
    
    async def get_subscriptions(
        self,
        event_type: Optional[WebhookEvent] = None,
        active_only: bool = True
    ) -> List[WebhookSubscription]:
        """Get webhook subscriptions with filters."""
        
        query = select(WebhookSubscription)
        
        if active_only:
            query = query.where(WebhookSubscription.is_active == True)
        
        if event_type:
            query = query.where(WebhookSubscription.events.contains(f'"{event_type.value}"'))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def send_webhook(
        self,
        event_type: WebhookEvent,
        payload: Dict[str, Any],
        event_id: Optional[str] = None
    ) -> List[WebhookDelivery]:
        """Send webhook for an event."""
        
        # Get subscriptions for this event
        subscriptions = await self.get_subscriptions(event_type=event_type)
        
        deliveries = []
        
        for subscription in subscriptions:
            delivery = await self._create_delivery(subscription, event_type, payload)
            deliveries.append(delivery)
            
            # Send webhook asynchronously
            asyncio.create_task(self._deliver_webhook(delivery))
        
        return deliveries
    
    async def _create_delivery(
        self,
        subscription: WebhookSubscription,
        event_type: WebhookEvent,
        payload: Dict[str, Any]
    ) -> WebhookDelivery:
        """Create a webhook delivery record."""
        
        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_type=event_type.value,
            payload=json.dumps(payload),
            delivery_started_at=datetime.utcnow()
        )
        
        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)
        
        return delivery
    
    async def _deliver_webhook(self, delivery: WebhookDelivery):
        """Deliver webhook to the subscription URL."""
        
        subscription = delivery.subscription
        
        try:
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Dealership-Parts-System/1.0",
                "X-Webhook-Event": delivery.event_type,
                "X-Webhook-Delivery": str(delivery.id),
                "X-Webhook-Timestamp": str(int(datetime.utcnow().timestamp()))
            }
            
            # Add signature if secret is configured
            if subscription.secret:
                signature = self._generate_signature(
                    delivery.payload,
                    subscription.secret
                )
                headers["X-Webhook-Signature"] = f"sha256={signature}"
            
            # Send webhook
            response = await self.http_client.post(
                subscription.url,
                content=delivery.payload,
                headers=headers,
                timeout=subscription.timeout_seconds
            )
            
            # Update delivery status
            delivery.status = WebhookStatus.DELIVERED
            delivery.response_status_code = response.status_code
            delivery.response_body = response.text
            delivery.delivery_completed_at = datetime.utcnow()
            
            # Update subscription statistics
            subscription.total_deliveries += 1
            subscription.successful_deliveries += 1
            subscription.last_delivery_attempt = datetime.utcnow()
            subscription.last_successful_delivery = datetime.utcnow()
            
            await self.db.commit()
            
        except Exception as e:
            # Handle delivery failure
            await self._handle_delivery_failure(delivery, str(e))
    
    async def _handle_delivery_failure(self, delivery: WebhookDelivery, error_message: str):
        """Handle webhook delivery failure."""
        
        subscription = delivery.subscription
        
        delivery.error_message = error_message
        delivery.delivery_completed_at = datetime.utcnow()
        
        # Check if we should retry
        if delivery.attempt_number < subscription.max_retries:
            delivery.status = WebhookStatus.RETRYING
            delivery.attempt_number += 1
            delivery.next_retry_at = datetime.utcnow() + timedelta(
                seconds=subscription.retry_delay_seconds * delivery.attempt_number
            )
            
            # Schedule retry
            asyncio.create_task(self._schedule_retry(delivery))
        else:
            delivery.status = WebhookStatus.FAILED
        
        # Update subscription statistics
        subscription.total_deliveries += 1
        subscription.failed_deliveries += 1
        subscription.last_delivery_attempt = datetime.utcnow()
        
        await self.db.commit()
    
    async def _schedule_retry(self, delivery: WebhookDelivery):
        """Schedule a retry for failed webhook delivery."""
        
        if not delivery.next_retry_at:
            return
        
        # Wait until retry time
        wait_seconds = (delivery.next_retry_at - datetime.utcnow()).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        
        # Retry delivery
        await self._deliver_webhook(delivery)
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        expected_signature = self._generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    async def get_delivery_history(
        self,
        subscription_id: Optional[int] = None,
        event_type: Optional[WebhookEvent] = None,
        status: Optional[WebhookStatus] = None,
        limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get webhook delivery history."""
        
        query = select(WebhookDelivery)
        
        if subscription_id:
            query = query.where(WebhookDelivery.subscription_id == subscription_id)
        
        if event_type:
            query = query.where(WebhookDelivery.event_type == event_type.value)
        
        if status:
            query = query.where(WebhookDelivery.status == status.value)
        
        query = query.order_by(WebhookDelivery.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_webhook_statistics(self) -> Dict[str, Any]:
        """Get webhook statistics."""
        
        # Get subscription stats
        subscriptions_query = select(WebhookSubscription)
        subscriptions_result = await self.db.execute(subscriptions_query)
        subscriptions = subscriptions_result.scalars().all()
        
        total_subscriptions = len(subscriptions)
        active_subscriptions = len([s for s in subscriptions if s.is_active])
        
        # Get delivery stats
        deliveries_query = select(WebhookDelivery)
        deliveries_result = await self.db.execute(deliveries_query)
        deliveries = deliveries_result.scalars().all()
        
        total_deliveries = len(deliveries)
        successful_deliveries = len([d for d in deliveries if d.status == WebhookStatus.DELIVERED])
        failed_deliveries = len([d for d in deliveries if d.status == WebhookStatus.FAILED])
        pending_deliveries = len([d for d in deliveries if d.status == WebhookStatus.PENDING])
        retrying_deliveries = len([d for d in deliveries if d.status == WebhookStatus.RETRYING])
        
        # Event type breakdown
        event_counts = {}
        for delivery in deliveries:
            event_type = delivery.event_type
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "subscriptions": {
                "total": total_subscriptions,
                "active": active_subscriptions,
                "inactive": total_subscriptions - active_subscriptions
            },
            "deliveries": {
                "total": total_deliveries,
                "successful": successful_deliveries,
                "failed": failed_deliveries,
                "pending": pending_deliveries,
                "retrying": retrying_deliveries,
                "success_rate": (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
            },
            "event_types": event_counts
        }
    
    async def cleanup_old_deliveries(self, days_to_keep: int = 30):
        """Clean up old webhook delivery records."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # This would need to be implemented with proper SQL delete
        # For now, we'll just return the count of records that would be deleted
        query = select(WebhookDelivery).where(WebhookDelivery.created_at < cutoff_date)
        result = await self.db.execute(query)
        old_deliveries = result.scalars().all()
        
        return len(old_deliveries)
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
