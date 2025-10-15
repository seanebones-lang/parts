"""
Real-time alerts and notifications system.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from enum import Enum

from app.models.inventory import Inventory
from app.models.location import Location
from app.models.user import User
from app.models.email import Email
from app.models.order import Order


class AlertType(str, Enum):
    """Types of alerts."""
    INVENTORY_LOW = "inventory_low"
    INVENTORY_EXPIRED = "inventory_expired"
    INVENTORY_EXPIRING = "inventory_expiring"
    ORDER_OVERDUE = "order_overdue"
    PAYMENT_FAILED = "payment_failed"
    SHIPMENT_DELAYED = "shipment_delayed"
    SYSTEM_ERROR = "system_error"
    SECURITY_BREACH = "security_breach"
    MAINTENANCE_DUE = "maintenance_due"
    CUSTOM = "custom"


class AlertPriority(str, Enum):
    """Alert priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"


class AlertService:
    """Service for managing real-time alerts and notifications."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.active_alerts: Dict[str, List[Dict]] = {}
        self.subscribers: Dict[str, List[str]] = {}
    
    async def check_inventory_alerts(self) -> List[Dict[str, Any]]:
        """Check for inventory-related alerts."""
        alerts = []
        
        # Check for low inventory
        low_inventory_query = select(Inventory).where(
            and_(
                Inventory.quantity_available <= Inventory.reorder_point,
                Inventory.is_active == True
            )
        )
        result = await self.db.execute(low_inventory_query)
        low_items = result.scalars().all()
        
        for item in low_items:
            alerts.append({
                "type": AlertType.INVENTORY_LOW,
                "priority": AlertPriority.HIGH,
                "title": "Low Inventory Alert",
                "message": f"Part {item.part.part_number} is below reorder point ({item.quantity_available}/{item.reorder_point})",
                "location_id": item.location_id,
                "part_id": item.part_id,
                "current_quantity": item.quantity_available,
                "reorder_point": item.reorder_point,
                "timestamp": datetime.utcnow()
            })
        
        # Check for expired inventory
        expired_query = select(Inventory).where(
            and_(
                Inventory.expiration_date < datetime.utcnow(),
                Inventory.is_expired == False,
                Inventory.is_active == True
            )
        )
        result = await self.db.execute(expired_query)
        expired_items = result.scalars().all()
        
        for item in expired_items:
            alerts.append({
                "type": AlertType.INVENTORY_EXPIRED,
                "priority": AlertPriority.CRITICAL,
                "title": "Expired Inventory Alert",
                "message": f"Part {item.part.part_number} has expired on {item.expiration_date}",
                "location_id": item.location_id,
                "part_id": item.part_id,
                "expiration_date": item.expiration_date,
                "timestamp": datetime.utcnow()
            })
            
            # Mark as expired
            item.is_expired = True
            await self.db.commit()
        
        # Check for expiring inventory
        warning_date = datetime.utcnow() + timedelta(days=30)
        expiring_query = select(Inventory).where(
            and_(
                Inventory.expiration_date <= warning_date,
                Inventory.expiration_date > datetime.utcnow(),
                Inventory.is_expired == False,
                Inventory.is_active == True
            )
        )
        result = await self.db.execute(expiring_query)
        expiring_items = result.scalars().all()
        
        for item in expiring_items:
            days_until_expiry = (item.expiration_date - datetime.utcnow()).days
            alerts.append({
                "type": AlertType.INVENTORY_EXPIRING,
                "priority": AlertPriority.MEDIUM,
                "title": "Inventory Expiring Soon",
                "message": f"Part {item.part.part_number} expires in {days_until_expiry} days",
                "location_id": item.location_id,
                "part_id": item.part_id,
                "expiration_date": item.expiration_date,
                "days_until_expiry": days_until_expiry,
                "timestamp": datetime.utcnow()
            })
        
        return alerts
    
    async def check_order_alerts(self) -> List[Dict[str, Any]]:
        """Check for order-related alerts."""
        alerts = []
        
        # Check for overdue orders
        overdue_date = datetime.utcnow() - timedelta(days=7)
        overdue_query = select(Order).where(
            and_(
                Order.created_at < overdue_date,
                Order.status.in_(["pending", "processing", "shipped"])
            )
        )
        result = await self.db.execute(overdue_query)
        overdue_orders = result.scalars().all()
        
        for order in overdue_orders:
            days_overdue = (datetime.utcnow() - order.created_at).days
            alerts.append({
                "type": AlertType.ORDER_OVERDUE,
                "priority": AlertPriority.HIGH,
                "title": "Overdue Order Alert",
                "message": f"Order {order.id} is {days_overdue} days overdue",
                "order_id": order.id,
                "customer_id": order.customer_id,
                "location_id": order.location_id,
                "days_overdue": days_overdue,
                "timestamp": datetime.utcnow()
            })
        
        return alerts
    
    async def create_custom_alert(
        self,
        alert_type: AlertType,
        priority: AlertPriority,
        title: str,
        message: str,
        location_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a custom alert."""
        alert = {
            "type": alert_type,
            "priority": priority,
            "title": title,
            "message": message,
            "location_id": location_id,
            "user_id": user_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow(),
            "id": f"alert_{datetime.utcnow().timestamp()}"
        }
        
        # Store in active alerts
        alert_key = f"{alert_type}_{location_id or 'global'}"
        if alert_key not in self.active_alerts:
            self.active_alerts[alert_key] = []
        self.active_alerts[alert_key].append(alert)
        
        # Send notifications
        await self.send_alert_notifications(alert)
        
        return alert
    
    async def send_alert_notifications(self, alert: Dict[str, Any]):
        """Send alert notifications through various channels."""
        channels = [AlertChannel.DASHBOARD, AlertChannel.EMAIL]
        
        for channel in channels:
            if channel == AlertChannel.DASHBOARD:
                await self.send_dashboard_notification(alert)
            elif channel == AlertChannel.EMAIL:
                await self.send_email_notification(alert)
    
    async def send_dashboard_notification(self, alert: Dict[str, Any]):
        """Send notification to dashboard subscribers."""
        # This would integrate with WebSocket or Server-Sent Events
        # For now, we'll store in the active alerts
        pass
    
    async def send_email_notification(self, alert: Dict[str, Any]):
        """Send email notification for critical alerts."""
        if alert["priority"] in [AlertPriority.HIGH, AlertPriority.CRITICAL]:
            # Create email record
            email = Email(
                to_email="admin@dealership.com",  # This should be configurable
                subject=f"[{alert['priority'].upper()}] {alert['title']}",
                body=alert["message"],
                email_type="system_alert",
                status="pending"
            )
            
            self.db.add(email)
            await self.db.commit()
    
    async def get_active_alerts(
        self,
        location_id: Optional[int] = None,
        alert_type: Optional[AlertType] = None,
        priority: Optional[AlertPriority] = None
    ) -> List[Dict[str, Any]]:
        """Get active alerts with filters."""
        all_alerts = []
        
        for key, alerts in self.active_alerts.items():
            for alert in alerts:
                if location_id and alert.get("location_id") != location_id:
                    continue
                if alert_type and alert["type"] != alert_type:
                    continue
                if priority and alert["priority"] != priority:
                    continue
                
                all_alerts.append(alert)
        
        # Sort by priority and timestamp
        priority_order = {
            AlertPriority.CRITICAL: 4,
            AlertPriority.HIGH: 3,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 1
        }
        
        all_alerts.sort(
            key=lambda x: (priority_order.get(x["priority"], 0), x["timestamp"]),
            reverse=True
        )
        
        return all_alerts
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for key, alerts in self.active_alerts.items():
            for i, alert in enumerate(alerts):
                if alert.get("id") == alert_id:
                    alert["acknowledged"] = True
                    alert["acknowledged_at"] = datetime.utcnow()
                    return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for key, alerts in self.active_alerts.items():
            for i, alert in enumerate(alerts):
                if alert.get("id") == alert_id:
                    alert["resolved"] = True
                    alert["resolved_at"] = datetime.utcnow()
                    return True
        return False
    
    async def subscribe_to_alerts(
        self,
        user_id: int,
        location_id: Optional[int] = None,
        alert_types: Optional[List[AlertType]] = None
    ):
        """Subscribe user to alerts."""
        subscription_key = f"user_{user_id}_{location_id or 'global'}"
        self.subscribers[subscription_key] = {
            "user_id": user_id,
            "location_id": location_id,
            "alert_types": alert_types or list(AlertType),
            "subscribed_at": datetime.utcnow()
        }
    
    async def run_alert_checks(self):
        """Run all alert checks."""
        all_alerts = []
        
        # Check inventory alerts
        inventory_alerts = await self.check_inventory_alerts()
        all_alerts.extend(inventory_alerts)
        
        # Check order alerts
        order_alerts = await self.check_order_alerts()
        all_alerts.extend(order_alerts)
        
        # Process new alerts
        for alert in all_alerts:
            await self.send_alert_notifications(alert)
        
        return all_alerts
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        all_alerts = []
        for alerts in self.active_alerts.values():
            all_alerts.extend(alerts)
        
        if not all_alerts:
            return {
                "total_alerts": 0,
                "priority_counts": {},
                "type_counts": {},
                "unacknowledged": 0,
                "unresolved": 0
            }
        
        priority_counts = {}
        type_counts = {}
        unacknowledged = 0
        unresolved = 0
        
        for alert in all_alerts:
            # Priority counts
            priority = alert["priority"]
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Type counts
            alert_type = alert["type"]
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
            
            # Unacknowledged/unresolved counts
            if not alert.get("acknowledged", False):
                unacknowledged += 1
            if not alert.get("resolved", False):
                unresolved += 1
        
        return {
            "total_alerts": len(all_alerts),
            "priority_counts": priority_counts,
            "type_counts": type_counts,
            "unacknowledged": unacknowledged,
            "unresolved": unresolved,
            "subscribers": len(self.subscribers)
        }
