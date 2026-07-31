"""
Stripe Mock Engine - Lester's Edition
Payment processing integration for end-to-end automation
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Optional
import uuid

# Mock Stripe configuration
MOCK_STRIPE_KEY = 'sk_test_mock_lester_edition'
MOCK_WEBHOOK_SECRET = 'whsec_mock_webhook_secret'

class StripeMockEngine:
    """Mock Stripe payment processing for demo automation"""
    
    def __init__(self):
        self.payment_intents = {}
        self.success_rate = 0.95  # 95% success rate for demo
        self.processing_fees = 0.029  # 2.9% + 30¢ per transaction
        
    def create_payment_intent(self, amount: int, description: str, customer_email: str = None) -> Dict:
        """Create mock Stripe payment intent - demo success every time"""
        intent_id = f"pi_mock_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
        
        # Calculate processing fee
        processing_fee = int(amount * self.processing_fees + 30)  # 2.9% + 30¢
        net_amount = amount - processing_fee
        
        intent = {
            "id": intent_id,
            "object": "payment_intent",
            "amount": amount,
            "amount_received": amount,
            "amount_capturable": 0,
            "currency": "usd",
            "status": "succeeded",
            "description": description,
            "client_secret": f"pi_mock_{intent_id}_secret_{random.randint(10000, 99999)}",
            "customer_email": customer_email,
            "processing_fee": processing_fee,
            "net_amount": net_amount,
            "created": int(datetime.now().timestamp()),
            "metadata": {
                "demo_mode": "true",
                "lester_edition": "v2",
                "automation_level": "high"
            }
        }
        
        self.payment_intents[intent_id] = intent
        return intent
    
    def process_order_with_stripe(self, order_details: Dict) -> Dict:
        """Process complete order with payment - green auto-charges"""
        try:
            # Extract order details
            part_name = order_details.get('part_name', 'Unknown Part')
            quantity = order_details.get('quantity', 1)
            unit_price = order_details.get('unit_price', 0)
            total_price = order_details.get('total_price', unit_price * quantity)
            customer_email = order_details.get('customer_email', 'customer@example.com')
            location = order_details.get('location', 'Chicago North')
            
            # Convert to cents for Stripe
            amount_cents = int(total_price * 100)
            
            # Create payment intent
            description = f"Parts order: {part_name} (Qty: {quantity}) - {location}"
            payment_intent = self.create_payment_intent(amount_cents, description, customer_email)
            
            # Generate order confirmation
            order_id = f"ORD-{int(datetime.now().timestamp())}-{random.randint(100, 999)}"
            
            result = {
                "success": True,
                "order_id": order_id,
                "payment_intent": payment_intent,
                "amount_charged": total_price,
                "processing_fee": payment_intent["processing_fee"] / 100,
                "net_amount": payment_intent["net_amount"] / 100,
                "next_steps": [
                    "Email confirmation sent",
                    "Inventory updated",
                    "Shipping label generated",
                    "Tracking number assigned"
                ],
                "automation_level": "full",
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fallback_action": "Manual processing required"
            }
    
    def generate_payment_confirmation_email(self, payment_result: Dict) -> str:
        """Generate professional payment confirmation email"""
        if not payment_result.get("success"):
            return "Payment processing failed - manual review required."
        
        payment_intent = payment_result["payment_intent"]
        order_id = payment_result["order_id"]
        
        email_template = f"""
Dear Valued Customer,

Your order has been processed and payment confirmed successfully!

Order Details:
• Order ID: {order_id}
• Payment ID: {payment_intent['id']}
• Amount Charged: ${payment_result['amount_charged']:.2f}
• Processing Fee: ${payment_result['processing_fee']:.2f}
• Net Amount: ${payment_result['net_amount']:.2f}

Next Steps:
• Your parts are being prepared for shipment
• Tracking information will be sent within 2 hours
• Expected delivery: 1-2 business days

Thank you for choosing Chicago Dealership Parts!

Best regards,
Automated Parts Processing System
Chicago Dealership Group
"""
        
        return email_template.strip()
    
    def get_payment_statistics(self) -> Dict:
        """Get payment processing statistics"""
        total_intents = len(self.payment_intents)
        successful_payments = len([pi for pi in self.payment_intents.values() if pi["status"] == "succeeded"])
        
        total_amount = sum(pi["amount"] for pi in self.payment_intents.values()) / 100
        total_fees = sum(pi["processing_fee"] for pi in self.payment_intents.values()) / 100
        net_amount = sum(pi["net_amount"] for pi in self.payment_intents.values()) / 100
        
        return {
            "total_payments": total_intents,
            "successful_payments": successful_payments,
            "success_rate": f"{successful_payments / max(total_intents, 1) * 100:.1f}%",
            "total_amount_processed": f"${total_amount:.2f}",
            "total_processing_fees": f"${total_fees:.2f}",
            "net_revenue": f"${net_amount:.2f}",
            "average_transaction": f"${total_amount / max(total_intents, 1):.2f}"
        }
    
    def simulate_webhook_event(self, payment_intent_id: str, event_type: str = "payment_intent.succeeded") -> Dict:
        """Simulate Stripe webhook event for testing"""
        if payment_intent_id not in self.payment_intents:
            return {"error": "Payment intent not found"}
        
        webhook_event = {
            "id": f"evt_mock_{int(datetime.now().timestamp())}",
            "object": "event",
            "type": event_type,
            "data": {
                "object": self.payment_intents[payment_intent_id]
            },
            "created": int(datetime.now().timestamp()),
            "livemode": False
        }
        
        return webhook_event

# Global Stripe mock instance
stripe_mock = StripeMockEngine()

def create_mock_payment_intent(amount: int, description: str, customer_email: str = None) -> Dict:
    """Convenience function to create payment intent"""
    return stripe_mock.create_payment_intent(amount, description, customer_email)

def process_order_with_stripe(order_details: Dict) -> Dict:
    """Convenience function to process order with payment"""
    return stripe_mock.process_order_with_stripe(order_details)

def generate_payment_confirmation_email(payment_result: Dict) -> str:
    """Convenience function to generate confirmation email"""
    return stripe_mock.generate_payment_confirmation_email(payment_result)

def get_payment_statistics() -> Dict:
    """Convenience function to get payment stats"""
    return stripe_mock.get_payment_statistics()

if __name__ == "__main__":
    print("🚀 Lester's Stripe Mock Engine Test")
    print("=" * 50)
    
    # Test payment processing
    test_order = {
        "part_name": "Brake Pads - 2019 Honda Civic",
        "quantity": 1,
        "unit_price": 45.00,
        "total_price": 45.00,
        "customer_email": "customer@chicagoauto.com",
        "location": "Chicago North"
    }
    
    print(f"📦 Processing test order: {test_order['part_name']}")
    result = process_order_with_stripe(test_order)
    
    if result["success"]:
        print(f"✅ Payment successful!")
        print(f"💰 Order ID: {result['order_id']}")
        print(f"💳 Payment ID: {result['payment_intent']['id']}")
        print(f"💵 Amount charged: ${result['amount_charged']:.2f}")
        print(f"📧 Confirmation email generated")
        
        # Show confirmation email
        print(f"\n📧 Confirmation Email:")
        print("-" * 40)
        print(generate_payment_confirmation_email(result))
    else:
        print(f"❌ Payment failed: {result['error']}")
    
    # Show statistics
    stats = get_payment_statistics()
    print(f"\n📊 Payment Statistics:")
    print(f"  Total payments: {stats['total_payments']}")
    print(f"  Success rate: {stats['success_rate']}")
    print(f"  Total processed: {stats['total_amount_processed']}")
    print(f"  Net revenue: {stats['net_revenue']}")
    
    print("\n✅ Stripe mock engine test complete!")
