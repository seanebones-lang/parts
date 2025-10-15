"""
Payment processing endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.payment_service import PaymentService
from app.agents.payment_agent import PaymentAgent

router = APIRouter()


@router.post("/create-intent")
async def create_payment_intent(
    payment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe payment intent."""
    try:
        service = PaymentService(db)
        
        required_fields = ["invoice_id", "amount"]
        for field in required_fields:
            if field not in payment_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await service.create_payment_intent(
            invoice_id=payment_data["invoice_id"],
            amount=payment_data["amount"],
            currency=payment_data.get("currency", "usd"),
            customer_email=payment_data.get("customer_email")
        )
        
        if result["success"]:
            return {
                "success": True,
                "payment_intent": result["payment_intent"],
                "message": "Payment intent created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment intent: {str(e)}")


@router.post("/create-link")
async def create_payment_link(
    payment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe payment link."""
    try:
        service = PaymentService(db)
        
        required_fields = ["invoice_id", "amount"]
        for field in required_fields:
            if field not in payment_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await service.create_payment_link(
            invoice_id=payment_data["invoice_id"],
            amount=payment_data["amount"],
            currency=payment_data.get("currency", "usd"),
            success_url=payment_data.get("success_url"),
            cancel_url=payment_data.get("cancel_url")
        )
        
        if result["success"]:
            return {
                "success": True,
                "payment_link": result["payment_link"],
                "message": "Payment link created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment link: {str(e)}")


@router.post("/webhook")
async def handle_stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events."""
    try:
        import stripe
        from app.core.config import settings
        
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        service = PaymentService(db)
        result = await service.handle_payment_webhook(event)
        
        return {"success": True, "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook handling failed: {str(e)}")


@router.get("/status/{payment_intent_id}")
async def get_payment_status(
    payment_intent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get payment status from Stripe."""
    try:
        service = PaymentService(db)
        result = await service.get_payment_status(payment_intent_id)
        
        if result["success"]:
            return {
                "success": True,
                "payment_status": result["payment_status"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment status: {str(e)}")


@router.post("/refund")
async def process_refund(
    refund_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Process payment refund."""
    try:
        service = PaymentService(db)
        
        required_fields = ["payment_intent_id"]
        for field in required_fields:
            if field not in refund_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await service.refund_payment(
            payment_intent_id=refund_data["payment_intent_id"],
            amount=refund_data.get("amount"),
            reason=refund_data.get("reason", "requested_by_customer")
        )
        
        if result["success"]:
            return {
                "success": True,
                "refund": result["refund"],
                "message": "Refund processed successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process refund: {str(e)}")


@router.post("/reminder")
async def send_payment_reminder(
    reminder_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Send payment reminder."""
    try:
        agent = PaymentAgent(db)
        
        required_fields = ["invoice_id"]
        for field in required_fields:
            if field not in reminder_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        result = await agent.process({
            "action": "send_reminder",
            **reminder_data
        })
        
        if result.success:
            return {
                "success": True,
                "result": result.data,
                "message": "Payment reminder sent successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reminder: {str(e)}")


@router.get("/analytics")
async def get_payment_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get payment analytics."""
    try:
        agent = PaymentAgent(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            from datetime import datetime
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        result = await agent.process({
            "action": "generate_payment_analytics",
            "start_date": start_dt,
            "end_date": end_dt
        })
        
        if result.success:
            return {
                "success": True,
                "analytics": result.data["analytics"],
                "insights": result.data.get("insights", [])
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.post("/test-payment")
async def test_payment_processing(
    test_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Test payment processing with sample data."""
    try:
        agent = PaymentAgent(db)
        
        action = test_data.get("action", "create_payment")
        result = await agent.process(test_data)
        
        return {
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "confidence": result.confidence,
            "processing_time": result.processing_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment test failed: {str(e)}")
