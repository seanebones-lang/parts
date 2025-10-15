"""
Supervisor Agent - Orchestrates other agents and handles complex workflows.
"""

import time
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.email_classifier import EmailClassifierAgent
from app.agents.customer_service import CustomerServiceAgent
from app.agents.parts_lookup import PartsLookupAgent
from app.agents.pricing_invoice import PricingInvoiceAgent
from app.models.agent_log import AgentType


class SupervisorAgent(BaseAgent):
    """Supervisor agent that orchestrates other agents."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.SUPERVISOR)
        self.email_classifier = EmailClassifierAgent(db)
        self.customer_service = CustomerServiceAgent(db)
        self.parts_lookup = PartsLookupAgent(db)
        self.pricing_invoice = PricingInvoiceAgent(db)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process input and delegate to appropriate agents."""
        start_time = time.time()
        
        try:
            workflow_type = input_data.get("workflow_type", "email_processing")
            
            if workflow_type == "email_processing":
                result = await self._handle_email_workflow(input_data)
            elif workflow_type == "customer_inquiry":
                result = await self._handle_customer_inquiry_workflow(input_data)
            else:
                result = await self._handle_generic_workflow(input_data)
            
            processing_time = time.time() - start_time
            
            # Log supervisor action
            await self.log_action(
                action="orchestrate_workflow",
                input_data=input_data,
                output_data=result.data,
                success=result.success,
                processing_time=processing_time,
                tokens_used=result.tokens_used,
                cost=result.cost,
                confidence=result.confidence,
                workflow_type=workflow_type
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action="orchestrate_workflow",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                workflow_type=input_data.get("workflow_type")
            )
            
            return AgentResult(
                success=False,
                message=f"Supervisor workflow failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _handle_email_workflow(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle email processing workflow."""
        # Step 1: Classify email
        classification_result = await self.email_classifier.process(input_data)
        
        if not classification_result.success:
            return classification_result
        
        classification_data = classification_result.data
        workflow_steps = ["email_classified"]
        
        # Step 2: Route to appropriate handler
        if classification_data.get("classification") == "general_inquiry":
            # Handle with customer service agent
            customer_input = {
                "inquiry_type": classification_data.get("classification"),
                "message": input_data.get("body", ""),
                "customer_info": classification_data.get("extracted_info", {})
            }
            
            service_result = await self.customer_service.process(customer_input)
            workflow_steps.append("customer_service_handled")
            
            return AgentResult(
                success=service_result.success,
                data={
                    "workflow_steps": workflow_steps,
                    "classification": classification_data,
                    "service_response": service_result.data
                },
                message="Email workflow completed",
                confidence=min(classification_result.confidence, service_result.confidence or 0.9),
                processing_time=(classification_result.processing_time or 0) + (service_result.processing_time or 0),
                tokens_used=(classification_result.tokens_used or 0) + (service_result.tokens_used or 0),
                cost=(classification_result.cost or 0) + (service_result.cost or 0)
            )
        
        else:
            # Route to specialized agents (to be implemented in later phases)
            workflow_steps.append("routed_to_specialist")
            
            return AgentResult(
                success=True,
                data={
                    "workflow_steps": workflow_steps,
                    "classification": classification_data,
                    "next_agent": self._determine_next_agent(classification_data.get("classification")),
                    "requires_human": classification_data.get("requires_human", False)
                },
                message="Email classified and routed",
                confidence=classification_result.confidence,
                processing_time=classification_result.processing_time,
                tokens_used=classification_result.tokens_used,
                cost=classification_result.cost
            )
    
    async def _handle_customer_inquiry_workflow(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle direct customer inquiry workflow."""
        # Route directly to customer service
        service_result = await self.customer_service.process(input_data)
        
        return AgentResult(
            success=service_result.success,
            data={
                "workflow_steps": ["customer_inquiry_handled"],
                "service_response": service_result.data
            },
            message="Customer inquiry workflow completed",
            confidence=service_result.confidence,
            processing_time=service_result.processing_time,
            tokens_used=service_result.tokens_used,
            cost=service_result.cost
        )
    
    async def _handle_generic_workflow(self, input_data: Dict[str, Any]) -> AgentResult:
        """Handle generic workflow."""
        return AgentResult(
            success=False,
            message="Unknown workflow type",
            data={"workflow_type": input_data.get("workflow_type")}
        )
    
    def _determine_next_agent(self, classification: str) -> str:
        """Determine which agent should handle the classified email next."""
        agent_mapping = {
            "parts_order": "parts_lookup_agent",
            "quote_request": "pricing_invoice_agent", 
            "shipping_inquiry": "shipping_coordinator_agent",
            "complaint": "customer_service_agent",
            "payment_inquiry": "pricing_invoice_agent",
            "customer_service": "customer_service_agent"
        }
        
        return agent_mapping.get(classification, "customer_service_agent")
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for supervisor."""
        return """
You are the Supervisor Agent for a dealership parts management system.

Your responsibilities:
1. Orchestrate workflows between specialized agents
2. Handle complex multi-step processes
3. Ensure proper routing of tasks
4. Monitor agent performance and outcomes
5. Escalate issues when necessary

You coordinate the following agents:
- Email Classifier Agent: Classifies and routes emails
- Customer Service Agent: Handles general inquiries
- Parts Lookup Agent: Searches inventory (coming soon)
- Pricing & Invoice Agent: Handles pricing (coming soon)
- Shipping Coordinator Agent: Manages shipping (coming soon)
- Supplier Sourcing Agent: Finds external parts (coming soon)
- Follow-up Agent: Automated follow-ups (coming soon)

Always ensure proper workflow completion and maintain high quality standards.
"""
