"""
Email Mock Integration - Lester's Edition
IMAP simulation for dealership email processing with RAG integration
"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random

# Import our logging system
from logger import log_query, log_demo_event

# Import Stripe mock engine
from stripe_mock import process_order_with_stripe, generate_payment_confirmation_email, get_payment_statistics

# Mock dealership emails - realistic scenarios
MOCK_EMAILS = [
    {
        "id": 1,
        "from": "customer@chicagoauto.com",
        "subject": "Need brake pads for 2019 Honda Civic ASAP",
        "body": "Hi team, got a '19 Civic in the shop—brake pads in stock? Ship to O'Hare if yes. Customer waiting.",
        "timestamp": datetime.now().isoformat(),
        "priority": "urgent"
    },
    {
        "id": 2,
        "from": "mechanic@fordfan.com",
        "subject": "Alternator for F-150—urgent!",
        "body": "2018 F-150 alternator—low stock? Quote and ship to Logan Square. Customer needs it today.",
        "timestamp": datetime.now().isoformat(),
        "priority": "urgent"
    },
    {
        "id": 3,
        "from": "service@toyotadealer.com",
        "subject": "Oil filter for 2020 Camry",
        "body": "Regular maintenance - need oil filter for 2020 Toyota Camry. Chicago South location preferred.",
        "timestamp": datetime.now().isoformat(),
        "priority": "normal"
    },
    {
        "id": 4,
        "from": "customer@email.com",
        "subject": "Brake pads for 2018 Honda Civic",
        "body": "Looking for brake pads for 2018 Honda Civic. Out of stock everywhere? Need alternatives.",
        "timestamp": datetime.now().isoformat(),
        "priority": "normal"
    },
    {
        "id": 5,
        "from": "tech@autoshop.com",
        "subject": "Air filter Honda Civic",
        "body": "Air filter for Honda Civic - any year 2018-2020. Multiple locations to check.",
        "timestamp": datetime.now().isoformat(),
        "priority": "normal"
    },
    {
        "id": 6,
        "from": "urgent@repair.com",
        "subject": "CRITICAL: Turbo for Honda Civic",
        "body": "URGENT: Customer's 2019 Honda Civic needs turbocharger. No stock anywhere? Escalate immediately!",
        "timestamp": datetime.now().isoformat(),
        "priority": "critical"
    },
    {
        "id": 7,
        "from": "parts@dealer.com",
        "subject": "Spark plugs Toyota Camry",
        "body": "Need spark plugs for 2020 Toyota Camry. Regular maintenance order.",
        "timestamp": datetime.now().isoformat(),
        "priority": "normal"
    },
    {
        "id": 8,
        "from": "customer@email.com",
        "subject": "Timing belt Honda Civic",
        "body": "Timing belt for 2019 Honda Civic - low stock alert? Need to know ASAP.",
        "timestamp": datetime.now().isoformat(),
        "priority": "urgent"
    }
]

class EmailProcessor:
    """Email processing system with RAG integration"""
    
    def __init__(self, vectorstore=None, qa_chain=None):
        self.vectorstore = vectorstore
        self.qa_chain = qa_chain
        self.processed_emails = []
    
    def fetch_mock_emails(self, num: int = 5) -> List[Dict]:
        """Simulate IMAP fetch - pull recent emails"""
        # Sort by timestamp (most recent first)
        sorted_emails = sorted(MOCK_EMAILS, key=lambda x: x['timestamp'], reverse=True)
        return sorted_emails[:num]
    
    def extract_query_from_email(self, email: Dict) -> str:
        """Extract parts query from email subject and body"""
        subject = email.get('subject', '')
        body = email.get('body', '')
        
        # Combine subject and body for query
        full_text = f"{subject} {body}"
        
        # Clean up the text
        full_text = re.sub(r'[^\w\s\-]', ' ', full_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        return full_text
    
    def determine_urgency_from_email(self, email: Dict) -> str:
        """Determine urgency from email content"""
        priority = email.get('priority', 'normal')
        
        # Additional urgency detection from content
        content = f"{email.get('subject', '')} {email.get('body', '')}".lower()
        
        if any(word in content for word in ['urgent', 'asap', 'critical', 'immediately', 'emergency']):
            return 'critical'
        elif any(word in content for word in ['today', 'rush', 'priority', 'quickly']):
            return 'urgent'
        else:
            return priority
    
    def process_email(self, email: Dict) -> Dict:
        """Process email through RAG system"""
        try:
            # Extract query from email
            query = self.extract_query_from_email(email)
            urgency = self.determine_urgency_from_email(email)
            
            # If we have RAG system, use it
            if self.qa_chain and self.vectorstore:
                # Build prompt for email processing
                prompt = f"""Process this dealership email query: "{query}"
                
                Instructions:
                1. Find matching parts in inventory
                2. Check stock levels and pricing
                3. Determine if order can be processed automatically
                4. Draft a professional reply
                
                Format: Provide specific part details, stock levels, and next steps."""
                
                # Get RAG response
                result = self.qa_chain.run(prompt)
                
                # Calculate confidence (mock for now - would use retrieval scores)
                confidence = random.uniform(0.6, 0.95)
                
            else:
                # Fallback mock response
                result = f"Mock response for: {query}"
                confidence = 0.7
            
            # Determine color and draft reply based on confidence and urgency
            color, draft_reply, payment_result = self._generate_response_and_color(
                email, query, result, confidence, urgency
            )
            
            # Log the email processing
            log_entry = log_query(query, {"response": draft_reply, "payment": payment_result}, color)
            
            # Prepare response
            processed = {
                "email_id": email["id"],
                "from": email["from"],
                "subject": email["subject"],
                "query": query,
                "color": color,
                "confidence": confidence,
                "draft_reply": draft_reply,
                "urgency": urgency,
                "ui_hint": self._get_ui_hint(color),
                "priority": self._get_priority(color),
                "action_required": "🔴" in color or "🟡" in color,
                "next_steps": self._get_next_steps(color),
                "log_id": log_entry.get("timestamp", datetime.now().isoformat()),
                "processing_time_ms": random.randint(50, 200),
                # Payment integration fields
                "payment_status": payment_result.get("success") if payment_result else None,
                "payment_intent": payment_result.get("payment_intent") if payment_result else None,
                "order_id": payment_result.get("order_id") if payment_result else None,
                "amount_charged": payment_result.get("amount_charged") if payment_result else None
            }
            
            self.processed_emails.append(processed)
            return processed
            
        except Exception as e:
            # Error handling
            error_response = {
                "email_id": email["id"],
                "error": str(e),
                "color": "🔴 Error - Manual review required",
                "draft_reply": "Error processing email - please review manually",
                "ui_hint": "display-error",
                "priority": "high",
                "action_required": True
            }
            
            log_demo_event("email_processing_error", {
                "email_id": email["id"],
                "error": str(e)
            })
            
            return error_response
    
    def _generate_response_and_color(self, email: Dict, query: str, result: str, confidence: float, urgency: str) -> tuple[str, str, Dict]:
        """Generate color-coded response and draft reply with payment integration"""
        
        # Adjust confidence based on urgency
        if urgency == "critical":
            confidence -= 0.1
        elif urgency == "urgent":
            confidence -= 0.05
        
        payment_result = None
        
        # Determine color based on confidence
        if confidence >= 0.8:
            color = "🟢 Auto-reply & Paid"
            
            # Extract order details from query/result for payment processing
            order_details = self._extract_order_details(query, result, email)
            
            # Process payment for high-confidence orders
            payment_result = process_order_with_stripe(order_details)
            
            if payment_result.get("success"):
                draft_reply = self._generate_payment_confirmation_reply(email, query, result, payment_result)
            else:
                draft_reply = self._generate_auto_reply(email, query, result)
                
        elif confidence >= 0.5:
            color = "🟡 Review - Draft ready"
            draft_reply = self._generate_review_reply(email, query, result)
        else:
            color = "🔴 Urgent - Escalate"
            draft_reply = self._generate_escalation_reply(email, query, result)
        
        return color, draft_reply, payment_result
    
    def _extract_order_details(self, query: str, result: str, email: Dict) -> Dict:
        """Extract order details from query and result for payment processing"""
        # Mock order details extraction - in production, this would use NLP
        order_details = {
            "part_name": "Brake Pads - 2019 Honda Civic",  # Default for demo
            "quantity": 1,
            "unit_price": 45.00,
            "total_price": 45.00,
            "customer_email": email.get("from", "customer@example.com"),
            "location": "Chicago North"
        }
        
        # Extract part name from query
        query_lower = query.lower()
        if "brake pads" in query_lower:
            if "2019" in query_lower and "civic" in query_lower:
                order_details["part_name"] = "Brake Pads - 2019 Honda Civic"
                order_details["unit_price"] = 45.00
            elif "2018" in query_lower and "civic" in query_lower:
                order_details["part_name"] = "Brake Pads - 2018 Honda Civic"
                order_details["unit_price"] = 42.00
        elif "alternator" in query_lower:
            order_details["part_name"] = "Alternator - 2018 Ford F-150"
            order_details["unit_price"] = 120.00
        elif "oil filter" in query_lower:
            order_details["part_name"] = "Oil Filter - 2020 Toyota Camry"
            order_details["unit_price"] = 8.50
        elif "air filter" in query_lower:
            order_details["part_name"] = "Air Filter - 2019 Honda Civic"
            order_details["unit_price"] = 15.00
        
        order_details["total_price"] = order_details["unit_price"] * order_details["quantity"]
        
        return order_details
    
    def _generate_payment_confirmation_reply(self, email: Dict, query: str, result: str, payment_result: Dict) -> str:
        """Generate payment confirmation reply"""
        payment_intent = payment_result["payment_intent"]
        order_id = payment_result["order_id"]
        
        return f"""Hi {email['from'].split('@')[0]},

Thank you for your order! Your payment has been processed successfully.

Order Details:
• Order ID: {order_id}
• Payment ID: {payment_intent['id']}
• Amount Charged: ${payment_result['amount_charged']:.2f}
• Parts: {payment_result.get('part_name', 'Automotive Parts')}

Your order is being prepared for shipment and tracking information will be sent within 2 hours.

Thank you for choosing Chicago Dealership Parts!

Best regards,
Automated Parts Processing System
Chicago Dealership Group"""
    
    def _generate_auto_reply(self, email: Dict, query: str, result: str) -> str:
        """Generate automatic reply for high-confidence matches"""
        return f"""Hi {email['from'].split('@')[0]},

Thank you for your inquiry. We have the requested parts in stock and ready to ship.

{result}

Order will be processed automatically and shipped today.
Tracking information will be sent shortly.

Best regards,
Chicago Dealership Parts Team"""
    
    def _generate_review_reply(self, email: Dict, query: str, result: str) -> str:
        """Generate review reply for medium-confidence matches"""
        return f"""Hi {email['from'].split('@')[0]},

Thank you for your inquiry. We found potential matches but need to verify compatibility.

{result}

Please confirm the exact vehicle details and we'll process your order.
A team member will review this within 30 minutes.

Best regards,
Chicago Dealership Parts Team"""
    
    def _generate_escalation_reply(self, email: Dict, query: str, result: str) -> str:
        """Generate escalation reply for low-confidence matches"""
        return f"""Hi {email['from'].split('@')[0]},

Thank you for your inquiry. This requires immediate attention from our parts specialist.

{result}

A senior team member will contact you within 15 minutes to discuss options.
We apologize for any delay.

Best regards,
Chicago Dealership Parts Team"""
    
    def _get_ui_hint(self, color: str) -> str:
        """Get UI hint based on color"""
        if "🟢" in color:
            return "display-success"
        elif "🟡" in color:
            return "display-warning"
        else:
            return "display-alert"
    
    def _get_priority(self, color: str) -> str:
        """Get priority level based on color"""
        if "🟢" in color:
            return "low"
        elif "🟡" in color:
            return "medium"
        else:
            return "high"
    
    def _get_next_steps(self, color: str) -> List[str]:
        """Get next steps based on color"""
        if "🟢" in color:
            return ["Send confirmation email", "Generate shipping label", "Update inventory"]
        elif "🟡" in color:
            return ["Review with team", "Confirm with customer", "Verify compatibility"]
        else:
            return ["Escalate immediately", "Contact specialist", "Check suppliers"]
    
    def get_processed_emails(self) -> List[Dict]:
        """Get all processed emails"""
        return self.processed_emails
    
    def get_email_stats(self) -> Dict:
        """Get email processing statistics"""
        if not self.processed_emails:
            return {"total": 0, "colors": {}}
        
        colors = {"🟢": 0, "🟡": 0, "🔴": 0}
        for email in self.processed_emails:
            color = email.get("color", "")
            if "🟢" in color:
                colors["🟢"] += 1
            elif "🟡" in color:
                colors["🟡"] += 1
            elif "🔴" in color:
                colors["🔴"] += 1
        
        return {
            "total": len(self.processed_emails),
            "colors": colors,
            "automation_rate": f"{colors['🟢'] / len(self.processed_emails) * 100:.1f}%"
        }

# Global email processor instance
email_processor = EmailProcessor()

def fetch_mock_emails(num: int = 5) -> List[Dict]:
    """Convenience function to fetch mock emails"""
    return email_processor.fetch_mock_emails(num)

def process_email(email: Dict) -> Dict:
    """Convenience function to process an email"""
    return email_processor.process_email(email)

def get_email_stats() -> Dict:
    """Convenience function to get email statistics"""
    return email_processor.get_email_stats()

if __name__ == "__main__":
    print("🚀 Lester's Email Mock Integration Test")
    print("=" * 50)
    
    # Test email processing
    emails = fetch_mock_emails(3)
    
    for email in emails:
        print(f"\n📧 Processing Email {email['id']}: {email['subject']}")
        processed = process_email(email)
        print(f"🎯 Color: {processed['color']}")
        print(f"📝 Draft: {processed['draft_reply'][:100]}...")
        print(f"⏱️  Processing: {processed['processing_time_ms']}ms")
    
    # Show stats
    stats = get_email_stats()
    print(f"\n📊 Email Processing Stats:")
    print(f"  Total processed: {stats['total']}")
    print(f"  🟢 Auto: {stats['colors']['🟢']}")
    print(f"  🟡 Review: {stats['colors']['🟡']}")
    print(f"  🔴 Escalate: {stats['colors']['🔴']}")
    print(f"  Automation rate: {stats['automation_rate']}")
    
    print("\n✅ Email mock integration test complete!")
