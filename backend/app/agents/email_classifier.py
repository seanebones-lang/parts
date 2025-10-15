"""
Email Classifier Agent - Routes emails to appropriate departments.
"""

import json
import time
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.models.email import EmailType


class EmailClassifierAgent(BaseAgent):
    """Agent for classifying and routing emails."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.EMAIL_CLASSIFIER)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Classify email and determine routing."""
        start_time = time.time()
        
        try:
            email_subject = input_data.get("subject", "")
            email_body = input_data.get("body", "")
            sender_email = input_data.get("sender_email", "")
            
            # Prepare classification prompt
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": f"""
Classify this email and extract relevant information:

Subject: {email_subject}
From: {sender_email}
Body: {email_body}

Provide your response in this exact JSON format:
{{
    "classification": "parts_order|quote_request|shipping_inquiry|complaint|general_inquiry|payment_inquiry|customer_service|unknown",
    "confidence": 0.95,
    "department": "parts|service|sales|admin",
    "priority": "low|medium|high|urgent",
    "extracted_info": {{
        "customer_name": "John Doe",
        "phone": "555-1234",
        "vehicle_info": "2020 Honda Civic",
        "parts_requested": ["brake pads", "oil filter"],
        "quantity": 1,
        "urgency": "normal"
    }},
    "suggested_response": "Brief suggested response",
    "requires_human": false
}}
"""
                }
            ]
            
            # Get classification from LLM
            llm_result = await self.llm_service.chat_completion(messages)
            classification_data = self._parse_classification(llm_result["content"])
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action="classify_email",
                input_data=input_data,
                output_data=classification_data,
                success=True,
                processing_time=processing_time,
                tokens_used=llm_result.get("tokens_used"),
                cost=llm_result.get("cost"),
                confidence=classification_data.get("confidence"),
                email_id=input_data.get("email_id")
            )
            
            return AgentResult(
                success=True,
                data=classification_data,
                message="Email classified successfully",
                confidence=classification_data.get("confidence"),
                processing_time=processing_time,
                tokens_used=llm_result.get("tokens_used"),
                cost=llm_result.get("cost")
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action="classify_email",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                email_id=input_data.get("email_id")
            )
            
            return AgentResult(
                success=False,
                message=f"Email classification failed: {str(e)}",
                processing_time=processing_time
            )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for email classification."""
        return """
You are an expert email classifier for a car dealership parts department.

Your job is to:
1. Classify emails into categories: parts_order, quote_request, shipping_inquiry, complaint, general_inquiry, payment_inquiry, customer_service, or unknown
2. Determine the appropriate department: parts, service, sales, or admin
3. Assess priority level: low, medium, high, or urgent
4. Extract relevant customer and order information
5. Suggest appropriate responses

Classification Guidelines:
- parts_order: Customer wants to order specific parts
- quote_request: Customer asking for price estimates
- shipping_inquiry: Questions about delivery, tracking, shipping
- complaint: Customer complaints, issues, problems
- general_inquiry: General questions about parts, compatibility
- payment_inquiry: Questions about billing, payments, invoices
- customer_service: General customer service requests
- unknown: Cannot determine category

Priority Guidelines:
- urgent: Complaints, immediate issues, VIP customers
- high: Time-sensitive orders, shipping problems
- medium: Regular orders, standard inquiries
- low: General questions, informational requests

Be accurate and provide high confidence scores only when you're certain.
"""
    
    def _parse_classification(self, content: str) -> Dict[str, Any]:
        """Parse classification response from LLM."""
        try:
            # Extract JSON from response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                return json.loads(json_str)
        except Exception as e:
            pass
        
        # Fallback parsing
        return {
            "classification": "unknown",
            "confidence": 0.1,
            "department": "admin",
            "priority": "low",
            "extracted_info": {},
            "suggested_response": "Thank you for your email. We'll review and respond shortly.",
            "requires_human": True
        }
