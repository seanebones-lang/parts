"""
Follow-up Agent - Handles automated follow-ups for quotes, payments, and satisfaction.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.services.followup_service import FollowupService
from app.services.notification_service import NotificationService
from app.services.scheduler_service import SchedulerService


class FollowUpAgent(BaseAgent):
    """Agent for automated follow-ups and customer retention."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.FOLLOW_UP)
        self.followup_service = FollowupService(db)
        self.notification_service = NotificationService(db)
        self.scheduler_service = SchedulerService(db)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process follow-up request."""
        start_time = time.time()
        
        try:
            action = input_data.get("action", "schedule_followup")
            
            if action == "schedule_followup":
                result = await self._schedule_followup(input_data)
            elif action == "process_followup_queue":
                result = await self._process_followup_queue(input_data)
            elif action == "send_quote_followup":
                result = await self._send_quote_followup(input_data)
            elif action == "send_payment_reminder":
                result = await self._send_payment_reminder(input_data)
            elif action == "send_shipping_update":
                result = await self._send_shipping_update(input_data)
            elif action == "send_satisfaction_survey":
                result = await self._send_satisfaction_survey(input_data)
            elif action == "handle_followup_response":
                result = await self._handle_followup_response(input_data)
            elif action == "cancel_followup":
                result = await self._cancel_followup(input_data)
            else:
                result = await self._general_followup_workflow(input_data)
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action=f"followup_{action}",
                input_data=input_data,
                output_data=result,
                success=True,
                processing_time=processing_time,
                confidence=0.95,
                customer_id=input_data.get("customer_id"),
                followup_id=input_data.get("followup_id")
            )
            
            return AgentResult(
                success=True,
                data=result,
                message=f"Follow-up {action} completed successfully",
                confidence=0.95,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action=f"followup_{input_data.get('action', 'unknown')}",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                customer_id=input_data.get("customer_id"),
                followup_id=input_data.get("followup_id")
            )
            
            return AgentResult(
                success=False,
                message=f"Follow-up processing failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _schedule_followup(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a follow-up action."""
        followup_type = input_data.get("followup_type")  # "quote", "payment", "shipping", "satisfaction"
        customer_id = input_data.get("customer_id")
        related_id = input_data.get("related_id")  # quote_id, invoice_id, order_id, etc.
        scheduled_time = input_data.get("scheduled_time")
        priority = input_data.get("priority", "normal")
        
        if not followup_type or not customer_id or not related_id:
            return {"success": False, "error": "followup_type, customer_id, and related_id are required"}
        
        # Create follow-up schedule
        schedule_result = await self.scheduler_service.schedule_followup(
            followup_type=followup_type,
            customer_id=customer_id,
            related_id=related_id,
            scheduled_time=scheduled_time,
            priority=priority,
            metadata=input_data.get("metadata", {})
        )
        
        if schedule_result["success"]:
            # Add to follow-up queue
            await self.followup_service.add_to_queue(
                followup_id=schedule_result["followup_id"],
                followup_type=followup_type,
                customer_id=customer_id
            )
        
        return schedule_result
    
    async def _process_followup_queue(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pending follow-ups from the queue."""
        try:
            # Get pending follow-ups
            pending_followups = await self.followup_service.get_pending_followups()
            
            if not pending_followups:
                return {
                    "success": True,
                    "processed": 0,
                    "message": "No pending follow-ups to process"
                }
            
            processed_count = 0
            results = []
            
            for followup in pending_followups:
                try:
                    # Process based on follow-up type
                    if followup["followup_type"] == "quote":
                        result = await self._send_quote_followup(followup)
                    elif followup["followup_type"] == "payment":
                        result = await self._send_payment_reminder(followup)
                    elif followup["followup_type"] == "shipping":
                        result = await self._send_shipping_update(followup)
                    elif followup["followup_type"] == "satisfaction":
                        result = await self._send_satisfaction_survey(followup)
                    else:
                        result = {"success": False, "error": f"Unknown follow-up type: {followup['followup_type']}"}
                    
                    if result["success"]:
                        # Mark as processed
                        await self.followup_service.mark_followup_processed(
                            followup_id=followup["id"],
                            result=result
                        )
                        processed_count += 1
                    
                    results.append({
                        "followup_id": followup["id"],
                        "type": followup["followup_type"],
                        "customer_id": followup["customer_id"],
                        "result": result
                    })
                    
                except Exception as e:
                    print(f"Error processing follow-up {followup['id']}: {e}")
                    results.append({
                        "followup_id": followup["id"],
                        "type": followup["followup_type"],
                        "customer_id": followup["customer_id"],
                        "result": {"success": False, "error": str(e)}
                    })
                    continue
            
            return {
                "success": True,
                "processed": processed_count,
                "total": len(pending_followups),
                "results": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _send_quote_followup(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send quote follow-up email."""
        quote_id = input_data.get("quote_id") or input_data.get("related_id")
        customer_id = input_data.get("customer_id")
        followup_stage = input_data.get("followup_stage", "initial")  # "initial", "reminder", "final"
        
        if not quote_id or not customer_id:
            return {"success": False, "error": "quote_id and customer_id are required"}
        
        # Get quote and customer details
        quote_data = await self.followup_service.get_quote_data(quote_id)
        customer_data = await self.followup_service.get_customer_data(customer_id)
        
        if not quote_data or not customer_data:
            return {"success": False, "error": "Quote or customer data not found"}
        
        # Generate follow-up message based on stage
        message_content = self._generate_quote_followup_message(
            quote_data=quote_data,
            customer_data=customer_data,
            stage=followup_stage
        )
        
        # Send follow-up email
        email_result = await self.notification_service.send_email(
            to_email=customer_data["email"],
            subject=message_content["subject"],
            body=message_content["body"],
            template_data={
                "customer_name": customer_data["full_name"],
                "quote_number": quote_data["quote_number"],
                "quote_amount": quote_data["total_amount"],
                "expiry_date": quote_data["valid_until"],
                "quote_link": f"/quotes/{quote_id}"
            }
        )
        
        if email_result["success"]:
            # Log the follow-up
            await self.followup_service.log_followup_action(
                followup_type="quote",
                customer_id=customer_id,
                related_id=quote_id,
                action="email_sent",
                stage=followup_stage,
                email_id=email_result.get("email_id")
            )
        
        return {
            "success": email_result["success"],
            "followup_type": "quote",
            "stage": followup_stage,
            "customer_id": customer_id,
            "quote_id": quote_id,
            "email_sent": email_result["success"],
            "message": f"Quote follow-up {followup_stage} sent" if email_result["success"] else "Failed to send quote follow-up"
        }
    
    async def _send_payment_reminder(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send payment reminder email."""
        invoice_id = input_data.get("invoice_id") or input_data.get("related_id")
        customer_id = input_data.get("customer_id")
        reminder_stage = input_data.get("reminder_stage", "due")  # "due", "overdue_3d", "overdue_7d", "final"
        
        if not invoice_id or not customer_id:
            return {"success": False, "error": "invoice_id and customer_id are required"}
        
        # Get invoice and customer details
        invoice_data = await self.followup_service.get_invoice_data(invoice_id)
        customer_data = await self.followup_service.get_customer_data(customer_id)
        
        if not invoice_data or not customer_data:
            return {"success": False, "error": "Invoice or customer data not found"}
        
        # Generate payment reminder message
        message_content = self._generate_payment_reminder_message(
            invoice_data=invoice_data,
            customer_data=customer_data,
            stage=reminder_stage
        )
        
        # Send payment reminder
        email_result = await self.notification_service.send_email(
            to_email=customer_data["email"],
            subject=message_content["subject"],
            body=message_content["body"],
            template_data={
                "customer_name": customer_data["full_name"],
                "invoice_number": invoice_data["invoice_number"],
                "amount_due": invoice_data["total_amount"],
                "due_date": invoice_data["due_date"],
                "payment_link": invoice_data.get("payment_link", ""),
                "overdue_days": self._calculate_overdue_days(invoice_data["due_date"])
            }
        )
        
        if email_result["success"]:
            # Log the reminder
            await self.followup_service.log_followup_action(
                followup_type="payment",
                customer_id=customer_id,
                related_id=invoice_id,
                action="reminder_sent",
                stage=reminder_stage,
                email_id=email_result.get("email_id")
            )
        
        return {
            "success": email_result["success"],
            "followup_type": "payment",
            "stage": reminder_stage,
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "email_sent": email_result["success"],
            "message": f"Payment reminder {reminder_stage} sent" if email_result["success"] else "Failed to send payment reminder"
        }
    
    async def _send_shipping_update(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send shipping update notification."""
        shipment_id = input_data.get("shipment_id") or input_data.get("related_id")
        customer_id = input_data.get("customer_id")
        update_type = input_data.get("update_type", "shipped")  # "shipped", "in_transit", "delivered"
        
        if not shipment_id or not customer_id:
            return {"success": False, "error": "shipment_id and customer_id are required"}
        
        # Get shipment and customer details
        shipment_data = await self.followup_service.get_shipment_data(shipment_id)
        customer_data = await self.followup_service.get_customer_data(customer_id)
        
        if not shipment_data or not customer_data:
            return {"success": False, "error": "Shipment or customer data not found"}
        
        # Generate shipping update message
        message_content = self._generate_shipping_update_message(
            shipment_data=shipment_data,
            customer_data=customer_data,
            update_type=update_type
        )
        
        # Send shipping update
        email_result = await self.notification_service.send_email(
            to_email=customer_data["email"],
            subject=message_content["subject"],
            body=message_content["body"],
            template_data={
                "customer_name": customer_data["full_name"],
                "tracking_number": shipment_data["tracking_number"],
                "carrier": shipment_data["carrier"],
                "estimated_delivery": shipment_data.get("estimated_delivery", ""),
                "current_status": shipment_data["status"],
                "tracking_link": shipment_data.get("tracking_link", "")
            }
        )
        
        if email_result["success"]:
            # Log the update
            await self.followup_service.log_followup_action(
                followup_type="shipping",
                customer_id=customer_id,
                related_id=shipment_id,
                action="update_sent",
                stage=update_type,
                email_id=email_result.get("email_id")
            )
        
        return {
            "success": email_result["success"],
            "followup_type": "shipping",
            "update_type": update_type,
            "customer_id": customer_id,
            "shipment_id": shipment_id,
            "email_sent": email_result["success"],
            "message": f"Shipping update {update_type} sent" if email_result["success"] else "Failed to send shipping update"
        }
    
    async def _send_satisfaction_survey(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send customer satisfaction survey."""
        order_id = input_data.get("order_id") or input_data.get("related_id")
        customer_id = input_data.get("customer_id")
        survey_type = input_data.get("survey_type", "delivery")  # "delivery", "service", "product"
        
        if not order_id or not customer_id:
            return {"success": False, "error": "order_id and customer_id are required"}
        
        # Get order and customer details
        order_data = await self.followup_service.get_order_data(order_id)
        customer_data = await self.followup_service.get_customer_data(customer_id)
        
        if not order_data or not customer_data:
            return {"success": False, "error": "Order or customer data not found"}
        
        # Generate satisfaction survey
        message_content = self._generate_satisfaction_survey_message(
            order_data=order_data,
            customer_data=customer_data,
            survey_type=survey_type
        )
        
        # Send satisfaction survey
        email_result = await self.notification_service.send_email(
            to_email=customer_data["email"],
            subject=message_content["subject"],
            body=message_content["body"],
            template_data={
                "customer_name": customer_data["full_name"],
                "order_number": order_data["order_number"],
                "delivery_date": order_data.get("delivery_date", ""),
                "survey_link": f"/surveys/{order_id}?type={survey_type}",
                "feedback_link": f"/feedback/{order_id}"
            }
        )
        
        if email_result["success"]:
            # Log the survey
            await self.followup_service.log_followup_action(
                followup_type="satisfaction",
                customer_id=customer_id,
                related_id=order_id,
                action="survey_sent",
                stage=survey_type,
                email_id=email_result.get("email_id")
            )
        
        return {
            "success": email_result["success"],
            "followup_type": "satisfaction",
            "survey_type": survey_type,
            "customer_id": customer_id,
            "order_id": order_id,
            "email_sent": email_result["success"],
            "message": f"Satisfaction survey {survey_type} sent" if email_result["success"] else "Failed to send satisfaction survey"
        }
    
    async def _handle_followup_response(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle customer response to follow-up."""
        followup_id = input_data.get("followup_id")
        response_type = input_data.get("response_type")  # "positive", "negative", "neutral", "no_response"
        response_data = input_data.get("response_data", {})
        
        if not followup_id or not response_type:
            return {"success": False, "error": "followup_id and response_type are required"}
        
        # Update follow-up with response
        update_result = await self.followup_service.update_followup_response(
            followup_id=followup_id,
            response_type=response_type,
            response_data=response_data
        )
        
        if update_result["success"]:
            # Determine next action based on response
            next_action = self._determine_next_action(response_type, response_data)
            
            if next_action:
                # Schedule next follow-up if needed
                await self._schedule_next_followup(followup_id, next_action)
        
        return update_result
    
    async def _cancel_followup(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a scheduled follow-up."""
        followup_id = input_data.get("followup_id")
        reason = input_data.get("reason", "Customer request")
        
        if not followup_id:
            return {"success": False, "error": "followup_id is required"}
        
        # Cancel the follow-up
        cancel_result = await self.scheduler_service.cancel_followup(
            followup_id=followup_id,
            reason=reason
        )
        
        # Remove from queue
        await self.followup_service.remove_from_queue(followup_id)
        
        return cancel_result
    
    async def _general_followup_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general follow-up workflow."""
        return {
            "message": "General follow-up workflow processed",
            "input_data": input_data
        }
    
    def _generate_quote_followup_message(
        self,
        quote_data: Dict[str, Any],
        customer_data: Dict[str, Any],
        stage: str
    ) -> Dict[str, str]:
        """Generate quote follow-up message based on stage."""
        customer_name = customer_data["full_name"]
        quote_number = quote_data["quote_number"]
        amount = quote_data["total_amount"]
        expiry_date = quote_data["valid_until"]
        
        if stage == "initial":
            return {
                "subject": f"Quote {quote_number} - Ready for Your Review",
                "body": f"""
Dear {customer_name},

Thank you for your interest in our parts and services. We've prepared a detailed quote for you:

Quote Number: {quote_number}
Total Amount: ${amount:.2f}
Valid Until: {expiry_date}

Please review the attached quote and let us know if you'd like to proceed with this order. If you have any questions or need modifications, please don't hesitate to contact us.

You can also view the quote online at: /quotes/{quote_data['id']}

Best regards,
Your Parts Team
                """
            }
        elif stage == "reminder":
            return {
                "subject": f"Quote {quote_number} - Friendly Reminder",
                "body": f"""
Dear {customer_name},

This is a friendly reminder about your pending quote:

Quote Number: {quote_number}
Total Amount: ${amount:.2f}
Valid Until: {expiry_date}

We wanted to make sure you received our quote and answer any questions you might have. Our team is standing by to help you with your parts needs.

If you're ready to proceed, simply reply to this email or give us a call.

Best regards,
Your Parts Team
                """
            }
        else:  # final
            return {
                "subject": f"Quote {quote_number} - Final Notice",
                "body": f"""
Dear {customer_name},

This is our final notice regarding your quote:

Quote Number: {quote_number}
Total Amount: ${amount:.2f}
Expires: {expiry_date}

We don't want you to miss out on this pricing. If you're still interested, please contact us immediately as this quote will expire soon.

We're here to help with any questions or concerns you might have.

Best regards,
Your Parts Team
                """
            }
    
    def _generate_payment_reminder_message(
        self,
        invoice_data: Dict[str, Any],
        customer_data: Dict[str, Any],
        stage: str
    ) -> Dict[str, str]:
        """Generate payment reminder message based on stage."""
        customer_name = customer_data["full_name"]
        invoice_number = invoice_data["invoice_number"]
        amount = invoice_data["total_amount"]
        due_date = invoice_data["due_date"]
        overdue_days = self._calculate_overdue_days(due_date)
        
        if stage == "due":
            return {
                "subject": f"Payment Due - Invoice {invoice_number}",
                "body": f"""
Dear {customer_name},

This is a friendly reminder that payment is due for your recent order:

Invoice Number: {invoice_number}
Amount Due: ${amount:.2f}
Due Date: {due_date}

You can pay securely online using the link below:
{invoice_data.get('payment_link', '')}

Thank you for your business!

Best regards,
Your Parts Team
                """
            }
        elif stage == "overdue_3d":
            return {
                "subject": f"Payment Overdue - Invoice {invoice_number}",
                "body": f"""
Dear {customer_name},

We noticed that payment for the following invoice is now overdue:

Invoice Number: {invoice_number}
Amount Due: ${amount:.2f}
Original Due Date: {due_date}
Days Overdue: {overdue_days}

To avoid any service interruptions, please remit payment at your earliest convenience.

You can pay online at: {invoice_data.get('payment_link', '')}

If you have any questions or need to discuss payment arrangements, please contact us immediately.

Best regards,
Your Parts Team
                """
            }
        else:  # overdue_7d or final
            return {
                "subject": f"Final Payment Notice - Invoice {invoice_number}",
                "body": f"""
Dear {customer_name},

This is our final notice regarding your overdue invoice:

Invoice Number: {invoice_number}
Amount Due: ${amount:.2f}
Original Due Date: {due_date}
Days Overdue: {overdue_days}

Please remit payment immediately to avoid any additional charges or service interruptions.

You can pay online at: {invoice_data.get('payment_link', '')}

If payment has already been made, please disregard this notice. If you have any questions, please contact us immediately.

Best regards,
Your Parts Team
                """
            }
    
    def _generate_shipping_update_message(
        self,
        shipment_data: Dict[str, Any],
        customer_data: Dict[str, Any],
        update_type: str
    ) -> Dict[str, str]:
        """Generate shipping update message based on type."""
        customer_name = customer_data["full_name"]
        tracking_number = shipment_data["tracking_number"]
        carrier = shipment_data["carrier"]
        
        if update_type == "shipped":
            return {
                "subject": f"Your Order Has Shipped - Tracking #{tracking_number}",
                "body": f"""
Dear {customer_name},

Great news! Your order has been shipped and is on its way to you.

Tracking Number: {tracking_number}
Carrier: {carrier}
Estimated Delivery: {shipment_data.get('estimated_delivery', '3-5 business days')}

You can track your package at: {shipment_data.get('tracking_link', '')}

Thank you for your business!

Best regards,
Your Parts Team
                """
            }
        elif update_type == "delivered":
            return {
                "subject": f"Your Order Has Been Delivered - Tracking #{tracking_number}",
                "body": f"""
Dear {customer_name},

Your order has been successfully delivered!

Tracking Number: {tracking_number}
Carrier: {carrier}
Delivery Date: {shipment_data.get('delivery_date', 'Today')}

We hope you're satisfied with your purchase. If you have any questions or need assistance, please don't hesitate to contact us.

Thank you for your business!

Best regards,
Your Parts Team
                """
            }
        else:  # in_transit
            return {
                "subject": f"Order Update - Tracking #{tracking_number}",
                "body": f"""
Dear {customer_name},

Here's an update on your order:

Tracking Number: {tracking_number}
Carrier: {carrier}
Current Status: {shipment_data['status']}
Estimated Delivery: {shipment_data.get('estimated_delivery', '3-5 business days')}

You can track your package at: {shipment_data.get('tracking_link', '')}

Thank you for your business!

Best regards,
Your Parts Team
                """
            }
    
    def _generate_satisfaction_survey_message(
        self,
        order_data: Dict[str, Any],
        customer_data: Dict[str, Any],
        survey_type: str
    ) -> Dict[str, str]:
        """Generate satisfaction survey message."""
        customer_name = customer_data["full_name"]
        order_number = order_data["order_number"]
        
        return {
            "subject": f"How Was Your Experience? - Order {order_number}",
            "body": f"""
Dear {customer_name},

We hope you're enjoying your recent purchase!

Order Number: {order_number}
Delivery Date: {order_data.get('delivery_date', 'Recently')}

Your feedback is important to us and helps us improve our service. Would you mind taking a quick 2-minute survey about your experience?

Survey Link: /surveys/{order_data['id']}?type={survey_type}

If you have any questions or concerns, please don't hesitate to contact us directly.

Thank you for your business!

Best regards,
Your Parts Team
                """
        }
    
    def _calculate_overdue_days(self, due_date: str) -> int:
        """Calculate number of days overdue."""
        try:
            due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            now = datetime.utcnow()
            if now > due:
                return (now - due).days
            return 0
        except:
            return 0
    
    def _determine_next_action(self, response_type: str, response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Determine next action based on customer response."""
        if response_type == "positive":
            return None  # No further action needed
        elif response_type == "negative":
            return {
                "action": "escalate_to_human",
                "reason": "Customer expressed dissatisfaction",
                "data": response_data
            }
        elif response_type == "neutral":
            return {
                "action": "schedule_followup",
                "followup_type": "satisfaction",
                "delay_hours": 72  # Follow up in 3 days
            }
        else:  # no_response
            return {
                "action": "schedule_followup",
                "followup_type": "satisfaction",
                "delay_hours": 168  # Follow up in 1 week
            }
    
    async def _schedule_next_followup(self, followup_id: int, next_action: Dict[str, Any]) -> None:
        """Schedule next follow-up based on action."""
        if next_action["action"] == "escalate_to_human":
            # Create escalation task
            await self.followup_service.create_escalation_task(
                followup_id=followup_id,
                reason=next_action["reason"],
                data=next_action["data"]
            )
        elif next_action["action"] == "schedule_followup":
            # Schedule next follow-up
            scheduled_time = datetime.utcnow() + timedelta(hours=next_action["delay_hours"])
            await self.scheduler_service.schedule_followup(
                followup_type=next_action["followup_type"],
                customer_id=next_action.get("customer_id"),
                related_id=next_action.get("related_id"),
                scheduled_time=scheduled_time.isoformat(),
                metadata=next_action.get("metadata", {})
            )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for follow-up agent."""
        return """
You are a specialized Follow-up Agent for a dealership parts management system.

Your responsibilities:
1. Schedule and send automated follow-ups for quotes, payments, and deliveries
2. Handle customer responses and determine appropriate next actions
3. Send customer satisfaction surveys after order completion
4. Manage follow-up workflows and escalation procedures
5. Track follow-up effectiveness and optimize timing

Follow-up Types:
- Quote Follow-ups: 24 hours, 3 days, 1 week (initial, reminder, final)
- Payment Reminders: Due date, 3 days overdue, 7 days overdue, final notice
- Shipping Updates: Shipped, in transit, delivered notifications
- Satisfaction Surveys: Post-delivery feedback collection

Key Features:
- Automated scheduling and queue management
- Personalized email templates
- Response handling and escalation
- Performance tracking and analytics
- Multi-channel communication (email, SMS, phone)

Always maintain a professional, helpful tone and ensure follow-ups add value to the customer experience.
"""
