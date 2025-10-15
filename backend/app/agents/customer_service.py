"""
Customer Service Agent - Handles general customer inquiries.
"""

import time
from typing import Dict, Any
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType


class CustomerServiceAgent(BaseAgent):
    """Agent for handling customer service inquiries."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.CUSTOMER_SERVICE)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process customer service inquiry."""
        start_time = time.time()
        
        try:
            inquiry_type = input_data.get("inquiry_type", "general")
            customer_message = input_data.get("message", "")
            customer_info = input_data.get("customer_info", {})
            
            # Prepare response prompt
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": f"""
Customer inquiry type: {inquiry_type}
Customer message: {customer_message}
Customer info: {customer_info}

Provide a helpful, professional response. If you need more information, ask specific questions.
Be friendly but concise. If this requires human intervention, say so.
"""
                }
            ]
            
            # Get response from LLM
            llm_result = await self.llm_service.chat_completion(messages)
            
            processing_time = time.time() - start_time
            
            response_data = {
                "response": llm_result["content"],
                "inquiry_type": inquiry_type,
                "requires_human": self._needs_human_intervention(llm_result["content"]),
                "suggested_actions": self._suggest_actions(inquiry_type, llm_result["content"])
            }
            
            # Log the action
            await self.log_action(
                action="handle_customer_inquiry",
                input_data=input_data,
                output_data=response_data,
                success=True,
                processing_time=processing_time,
                tokens_used=llm_result.get("tokens_used"),
                cost=llm_result.get("cost"),
                confidence=0.9,  # High confidence for general responses
                customer_id=input_data.get("customer_id")
            )
            
            return AgentResult(
                success=True,
                data=response_data,
                message="Customer inquiry handled successfully",
                confidence=0.9,
                processing_time=processing_time,
                tokens_used=llm_result.get("tokens_used"),
                cost=llm_result.get("cost")
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action="handle_customer_inquiry",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                customer_id=input_data.get("customer_id")
            )
            
            return AgentResult(
                success=False,
                message=f"Customer service processing failed: {str(e)}",
                processing_time=processing_time
            )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for customer service."""
        return """
You are a professional customer service representative for a car dealership parts department.

Your responsibilities:
1. Provide helpful, accurate information about auto parts
2. Answer questions about compatibility, availability, and pricing
3. Guide customers through the ordering process
4. Handle complaints professionally and empathetically
5. Escalate complex issues to human staff when needed

Guidelines:
- Be friendly, professional, and helpful
- Keep responses concise but informative
- Ask clarifying questions when needed
- If you don't know something, say so and offer to connect them with a specialist
- For complex technical questions, suggest consulting with a mechanic
- Always maintain a positive, solution-oriented tone

Common inquiries you can handle:
- General parts information and compatibility
- Basic pricing questions
- Order status inquiries
- Shipping and delivery questions
- Return and exchange policies
- Warranty information

Escalate to human when:
- Complex technical issues
- Customer complaints requiring resolution
- Custom modifications or special orders
- Issues with existing orders that need investigation
"""
    
    def _needs_human_intervention(self, response: str) -> bool:
        """Determine if response indicates human intervention is needed."""
        human_keywords = [
            "speak with", "talk to", "connect you with", "transfer you to",
            "our specialist", "our expert", "human representative",
            "schedule a call", "appointment", "investigation needed"
        ]
        
        response_lower = response.lower()
        return any(keyword in response_lower for keyword in human_keywords)
    
    def _suggest_actions(self, inquiry_type: str, response: str) -> list:
        """Suggest follow-up actions based on inquiry type."""
        actions = []
        
        if inquiry_type == "parts_order":
            actions.extend(["create_order", "check_inventory", "provide_quote"])
        elif inquiry_type == "shipping_inquiry":
            actions.extend(["check_tracking", "update_shipping_info"])
        elif inquiry_type == "complaint":
            actions.extend(["escalate_to_manager", "log_complaint", "offer_resolution"])
        elif inquiry_type == "payment_inquiry":
            actions.extend(["check_payment_status", "send_invoice", "process_payment"])
        
        if self._needs_human_intervention(response):
            actions.append("escalate_to_human")
        
        return actions
