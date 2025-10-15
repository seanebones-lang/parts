"""
Payment Agent - Handles payment processing and tracking.
"""

import time
from typing import Dict, Any, Optional
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService


class PaymentAgent(BaseAgent):
    """Agent for payment processing and management."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.PAYMENT_PROCESSING)
        self.payment_service = PaymentService(db)
        self.notification_service = NotificationService(db)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process payment-related request."""
        start_time = time.time()
        
        try:
            action = input_data.get("action", "create_payment")
            
            if action == "create_payment":
                result = await self._create_payment(input_data)
            elif action == "send_reminder":
                result = await self._send_payment_reminder(input_data)
            elif action == "process_refund":
                result = await self._process_refund(input_data)
            elif action == "check_payment_status":
                result = await self._check_payment_status(input_data)
            elif action == "generate_payment_analytics":
                result = await self._generate_payment_analytics(input_data)
            else:
                result = await self._general_payment_workflow(input_data)
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action=f"payment_{action}",
                input_data=input_data,
                output_data=result,
                success=True,
                processing_time=processing_time,
                confidence=0.95,
                customer_id=input_data.get("customer_id"),
                invoice_id=input_data.get("invoice_id")
            )
            
            return AgentResult(
                success=True,
                data=result,
                message=f"Payment {action} completed successfully",
                confidence=0.95,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action=f"payment_{input_data.get('action', 'unknown')}",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                customer_id=input_data.get("customer_id"),
                invoice_id=input_data.get("invoice_id")
            )
            
            return AgentResult(
                success=False,
                message=f"Payment processing failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _create_payment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment intent or link for an invoice."""
        invoice_id = input_data.get("invoice_id")
        amount = input_data.get("amount")
        payment_type = input_data.get("payment_type", "link")  # "intent" or "link"
        
        if not invoice_id or not amount:
            return {"success": False, "error": "invoice_id and amount are required"}
        
        if payment_type == "intent":
            # Create payment intent for embedded payment forms
            result = await self.payment_service.create_payment_intent(
                invoice_id=invoice_id,
                amount=amount,
                customer_email=input_data.get("customer_email")
            )
        else:
            # Create payment link for email/redirect payments
            result = await self.payment_service.create_payment_link(
                invoice_id=invoice_id,
                amount=amount,
                success_url=input_data.get("success_url"),
                cancel_url=input_data.get("cancel_url")
            )
        
        if result["success"]:
            # Send payment notification
            await self.notification_service.send_payment_notification(
                invoice_id=invoice_id,
                payment_data=result
            )
        
        return result
    
    async def _send_payment_reminder(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send payment reminder for overdue invoices."""
        invoice_id = input_data.get("invoice_id")
        reminder_type = input_data.get("reminder_type", "payment_due")
        
        if not invoice_id:
            return {"success": False, "error": "invoice_id is required"}
        
        # Send payment reminder
        result = await self.payment_service.send_payment_reminder(
            invoice_id=invoice_id,
            reminder_type=reminder_type
        )
        
        if result["success"]:
            # Log reminder sent
            await self.log_action(
                action="payment_reminder_sent",
                input_data=input_data,
                output_data=result,
                success=True,
                confidence=1.0,
                invoice_id=invoice_id
            )
        
        return result
    
    async def _process_refund(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment refund."""
        payment_intent_id = input_data.get("payment_intent_id")
        amount = input_data.get("amount")  # Optional partial refund amount
        reason = input_data.get("reason", "requested_by_customer")
        
        if not payment_intent_id:
            return {"success": False, "error": "payment_intent_id is required"}
        
        # Process refund
        result = await self.payment_service.refund_payment(
            payment_intent_id=payment_intent_id,
            amount=amount,
            reason=reason
        )
        
        if result["success"]:
            # Send refund notification
            await self.notification_service.send_refund_notification(
                refund_data=result["refund"]
            )
        
        return result
    
    async def _check_payment_status(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check payment status."""
        payment_intent_id = input_data.get("payment_intent_id")
        
        if not payment_intent_id:
            return {"success": False, "error": "payment_intent_id is required"}
        
        # Get payment status from Stripe
        result = await self.payment_service.get_payment_status(payment_intent_id)
        
        return result
    
    async def _generate_payment_analytics(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate payment analytics and insights."""
        start_date = input_data.get("start_date")
        end_date = input_data.get("end_date")
        
        # Get payment analytics
        analytics = await self.payment_service.get_payment_analytics(
            start_date=start_date,
            end_date=end_date
        )
        
        if analytics["success"]:
            # Generate insights
            insights = self._generate_payment_insights(analytics["analytics"])
            analytics["insights"] = insights
        
        return analytics
    
    async def _general_payment_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general payment workflow."""
        return {
            "message": "General payment workflow processed",
            "input_data": input_data
        }
    
    def _generate_payment_insights(self, analytics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from payment analytics."""
        insights = []
        
        success_rate = analytics.get("success_rate", 0)
        total_payments = analytics.get("total_payments", 0)
        
        # Success rate insights
        if success_rate < 85:
            insights.append({
                "type": "warning",
                "title": "Low Payment Success Rate",
                "message": f"Payment success rate is {success_rate:.1f}%, below recommended 85%",
                "recommendation": "Review failed payment reasons and optimize checkout flow"
            })
        elif success_rate > 95:
            insights.append({
                "type": "success",
                "title": "Excellent Payment Success Rate",
                "message": f"Payment success rate is {success_rate:.1f}%, excellent performance",
                "recommendation": "Continue current payment optimization strategies"
            })
        
        # Volume insights
        if total_payments > 100:
            avg_payment = analytics.get("average_payment", 0)
            if avg_payment < 50:
                insights.append({
                    "type": "info",
                    "title": "Low Average Payment Amount",
                    "message": f"Average payment is ${avg_payment:.2f}, consider upselling strategies",
                    "recommendation": "Implement cross-selling and upselling features"
                })
        
        # Failed payments insights
        failed_payments = analytics.get("failed_payments", 0)
        if failed_payments > total_payments * 0.15:  # More than 15% failed
            insights.append({
                "type": "warning",
                "title": "High Failed Payment Rate",
                "message": f"{failed_payments} payments failed, investigate common failure reasons",
                "recommendation": "Analyze failed payment patterns and improve payment UX"
            })
        
        return insights
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for payment agent."""
        return """
You are a specialized Payment Agent for a dealership parts management system.

Your responsibilities:
1. Process payments through Stripe integration
2. Generate payment links and intents for invoices
3. Send automated payment reminders
4. Handle refunds and payment disputes
5. Monitor payment analytics and provide insights
6. Ensure PCI compliance and security best practices

Payment Types:
- Payment Links: For email-based payments and redirects
- Payment Intents: For embedded payment forms
- Recurring Payments: For subscription-based services

Key Features:
- Automatic payment reminders for overdue invoices
- Multi-currency support (USD primary)
- Refund processing and tracking
- Payment analytics and reporting
- Integration with invoice system
- Customer payment history tracking

Always ensure secure handling of payment information and maintain PCI compliance.
"""
