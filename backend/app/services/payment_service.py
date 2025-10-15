"""
Payment service for Stripe integration and payment processing.
"""

import stripe
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.invoice import Invoice, InvoiceStatus
from app.models.order import Order


class PaymentService:
    """Service for payment processing with Stripe."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY
    
    async def create_payment_intent(
        self,
        invoice_id: int,
        amount: float,
        currency: str = "usd",
        customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Stripe payment intent for an invoice."""
        try:
            # Get invoice details
            invoice = await self._get_invoice(invoice_id)
            if not invoice:
                return {"success": False, "error": "Invoice not found"}
            
            # Create or get Stripe customer
            stripe_customer_id = await self._get_or_create_stripe_customer(
                customer_email=invoice.customer.email,
                customer_name=invoice.customer.full_name
            )
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=stripe_customer_id,
                metadata={
                    "invoice_id": str(invoice_id),
                    "invoice_number": invoice.invoice_number,
                    "order_id": str(invoice.order_id) if invoice.order_id else "",
                    "customer_id": str(invoice.customer_id)
                },
                description=f"Invoice {invoice.invoice_number}",
                receipt_email=customer_email or invoice.customer.email,
                automatic_payment_methods={
                    "enabled": True,
                }
            )
            
            # Update invoice with payment intent
            await self._update_invoice_payment_intent(invoice_id, payment_intent.id)
            
            return {
                "success": True,
                "payment_intent": {
                    "id": payment_intent.id,
                    "client_secret": payment_intent.client_secret,
                    "amount": amount,
                    "currency": currency,
                    "status": payment_intent.status
                },
                "customer_email": customer_email or invoice.customer.email
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_payment_link(
        self,
        invoice_id: int,
        amount: float,
        currency: str = "usd",
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Stripe payment link for an invoice."""
        try:
            # Get invoice details
            invoice = await self._get_invoice(invoice_id)
            if not invoice:
                return {"success": False, "error": "Invoice not found"}
            
            # Create or get Stripe customer
            stripe_customer_id = await self._get_or_create_stripe_customer(
                customer_email=invoice.customer.email,
                customer_name=invoice.customer.full_name
            )
            
            # Create price for the invoice
            price = stripe.Price.create(
                unit_amount=int(amount * 100),
                currency=currency,
                product_data={
                    "name": f"Invoice {invoice.invoice_number}",
                    "description": f"Payment for invoice {invoice.invoice_number}",
                    "metadata": {
                        "invoice_id": str(invoice_id),
                        "invoice_number": invoice.invoice_number
                    }
                }
            )
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price.id,
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url or f"{settings.CORS_ORIGINS[0]}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url or f"{settings.CORS_ORIGINS[0]}/payment/cancel",
                metadata={
                    "invoice_id": str(invoice_id),
                    "invoice_number": invoice.invoice_number,
                    "order_id": str(invoice.order_id) if invoice.order_id else "",
                    "customer_id": str(invoice.customer_id)
                },
                invoice_creation={"enabled": True},
                receipt_email=invoice.customer.email
            )
            
            return {
                "success": True,
                "payment_link": {
                    "url": checkout_session.url,
                    "session_id": checkout_session.id,
                    "amount": amount,
                    "currency": currency
                },
                "invoice_number": invoice.invoice_number
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_payment_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stripe webhook events."""
        try:
            event_type = event_data.get("type")
            
            if event_type == "payment_intent.succeeded":
                return await self._handle_payment_success(event_data)
            elif event_type == "payment_intent.payment_failed":
                return await self._handle_payment_failed(event_data)
            elif event_type == "checkout.session.completed":
                return await self._handle_checkout_completed(event_data)
            elif event_type == "invoice.payment_succeeded":
                return await self._handle_invoice_payment_succeeded(event_data)
            else:
                return {"success": True, "message": f"Unhandled event type: {event_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_payment_status(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """Get payment status from Stripe."""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "success": True,
                "payment_status": {
                    "id": payment_intent.id,
                    "status": payment_intent.status,
                    "amount": payment_intent.amount / 100,  # Convert from cents
                    "currency": payment_intent.currency,
                    "created": datetime.fromtimestamp(payment_intent.created),
                    "metadata": payment_intent.metadata
                }
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def refund_payment(
        self,
        payment_intent_id: str,
        amount: Optional[float] = None,
        reason: str = "requested_by_customer"
    ) -> Dict[str, Any]:
        """Refund a payment."""
        try:
            refund_params = {
                "payment_intent": payment_intent_id,
                "reason": reason
            }
            
            if amount:
                refund_params["amount"] = int(amount * 100)  # Convert to cents
            
            refund = stripe.Refund.create(**refund_params)
            
            # Update invoice status if full refund
            if not amount:  # Full refund
                invoice_id = await self._get_invoice_id_by_payment_intent(payment_intent_id)
                if invoice_id:
                    await self._update_invoice_status(invoice_id, InvoiceStatus.REFUNDED)
            
            return {
                "success": True,
                "refund": {
                    "id": refund.id,
                    "amount": refund.amount / 100,
                    "status": refund.status,
                    "reason": refund.reason
                }
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_payment_reminder(
        self,
        invoice_id: int,
        reminder_type: str = "payment_due"
    ) -> Dict[str, Any]:
        """Send payment reminder email."""
        try:
            invoice = await self._get_invoice(invoice_id)
            if not invoice:
                return {"success": False, "error": "Invoice not found"}
            
            # Create payment link
            payment_link_result = await self.create_payment_link(invoice_id, invoice.total_amount)
            
            if not payment_link_result["success"]:
                return payment_link_result
            
            # Send reminder email (this would integrate with email service)
            reminder_data = {
                "invoice_id": invoice_id,
                "invoice_number": invoice.invoice_number,
                "customer_email": invoice.customer.email,
                "customer_name": invoice.customer.full_name,
                "amount": float(invoice.total_amount),
                "due_date": invoice.due_date.isoformat(),
                "payment_link": payment_link_result["payment_link"]["url"],
                "reminder_type": reminder_type,
                "overdue_days": self._calculate_overdue_days(invoice.due_date)
            }
            
            # This would send the actual email
            print(f"Sending payment reminder for invoice {invoice.invoice_number}")
            print(f"Payment link: {payment_link_result['payment_link']['url']}")
            
            return {
                "success": True,
                "reminder_sent": True,
                "reminder_data": reminder_data
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_payment_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get payment analytics and metrics."""
        try:
            # Query Stripe for payment data
            params = {"limit": 100}
            
            if start_date:
                params["created"] = {"gte": int(start_date.timestamp())}
            
            if end_date:
                if "created" not in params:
                    params["created"] = {}
                params["created"]["lte"] = int(end_date.timestamp())
            
            payment_intents = stripe.PaymentIntent.list(**params)
            
            # Calculate metrics
            total_payments = len(payment_intents.data)
            total_amount = sum(pi.amount for pi in payment_intents.data if pi.status == "succeeded") / 100
            successful_payments = len([pi for pi in payment_intents.data if pi.status == "succeeded"])
            failed_payments = len([pi for pi in payment_intents.data if pi.status == "payment_failed"])
            
            success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
            
            return {
                "success": True,
                "analytics": {
                    "total_payments": total_payments,
                    "successful_payments": successful_payments,
                    "failed_payments": failed_payments,
                    "success_rate": success_rate,
                    "total_amount": total_amount,
                    "average_payment": total_amount / successful_payments if successful_payments > 0 else 0,
                    "period": {
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None
                    }
                }
            }
            
        except stripe.error.StripeError as e:
            return {"success": False, "error": f"Stripe error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID."""
        # This would query the database
        # For now, return mock data
        return None
    
    async def _get_or_create_stripe_customer(
        self,
        customer_email: str,
        customer_name: str
    ) -> str:
        """Get or create Stripe customer."""
        try:
            # Check if customer exists
            customers = stripe.Customer.list(email=customer_email, limit=1)
            
            if customers.data:
                return customers.data[0].id
            
            # Create new customer
            customer = stripe.Customer.create(
                email=customer_email,
                name=customer_name
            )
            
            return customer.id
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe customer error: {str(e)}")
    
    async def _update_invoice_payment_intent(
        self,
        invoice_id: int,
        payment_intent_id: str
    ) -> None:
        """Update invoice with payment intent ID."""
        # This would update the database
        pass
    
    async def _update_invoice_status(
        self,
        invoice_id: int,
        status: InvoiceStatus
    ) -> None:
        """Update invoice status."""
        # This would update the database
        pass
    
    async def _get_invoice_id_by_payment_intent(
        self,
        payment_intent_id: str
    ) -> Optional[int]:
        """Get invoice ID by payment intent ID."""
        # This would query the database
        return None
    
    def _calculate_overdue_days(self, due_date: datetime) -> int:
        """Calculate number of overdue days."""
        if datetime.utcnow() > due_date:
            return (datetime.utcnow() - due_date).days
        return 0
    
    async def _handle_payment_success(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment."""
        payment_intent = event_data.get("data", {}).get("object", {})
        invoice_id = payment_intent.get("metadata", {}).get("invoice_id")
        
        if invoice_id:
            await self._update_invoice_status(int(invoice_id), InvoiceStatus.PAID)
            
            # Record payment in database
            await self._record_payment(
                invoice_id=int(invoice_id),
                payment_intent_id=payment_intent["id"],
                amount=payment_intent["amount"] / 100,
                payment_method="card"
            )
        
        return {"success": True, "message": "Payment success handled"}
    
    async def _handle_payment_failed(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment."""
        payment_intent = event_data.get("data", {}).get("object", {})
        invoice_id = payment_intent.get("metadata", {}).get("invoice_id")
        
        if invoice_id:
            # Send payment failed notification
            print(f"Payment failed for invoice {invoice_id}")
        
        return {"success": True, "message": "Payment failure handled"}
    
    async def _handle_checkout_completed(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completed checkout session."""
        session = event_data.get("data", {}).get("object", {})
        invoice_id = session.get("metadata", {}).get("invoice_id")
        
        if invoice_id:
            await self._update_invoice_status(int(invoice_id), InvoiceStatus.PAID)
            
            # Record payment in database
            await self._record_payment(
                invoice_id=int(invoice_id),
                payment_intent_id=session["payment_intent"],
                amount=session["amount_total"] / 100,
                payment_method="card"
            )
        
        return {"success": True, "message": "Checkout completion handled"}
    
    async def _handle_invoice_payment_succeeded(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful invoice payment."""
        # Handle Stripe invoice payment
        return {"success": True, "message": "Invoice payment success handled"}
    
    async def _record_payment(
        self,
        invoice_id: int,
        payment_intent_id: str,
        amount: float,
        payment_method: str
    ) -> None:
        """Record payment in database."""
        # This would update the database with payment record
        pass
