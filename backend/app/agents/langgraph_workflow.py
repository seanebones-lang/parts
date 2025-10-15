"""
LangGraph workflow for orchestrating AI agents.
"""

from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.agents.supervisor import SupervisorAgent
from app.agents.email_classifier import EmailClassifierAgent
from app.agents.customer_service import CustomerServiceAgent
from app.core.database import AsyncSessionLocal


class WorkflowState(TypedDict):
    """State for the LangGraph workflow."""
    messages: Annotated[List[BaseMessage], add_messages]
    workflow_type: str
    input_data: Dict[str, Any]
    classification_result: Dict[str, Any]
    service_result: Dict[str, Any]
    final_result: Dict[str, Any]
    requires_human: bool
    next_agent: str
    error: str


class LangGraphWorkflow:
    """LangGraph workflow for orchestrating agents."""
    
    def __init__(self):
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("email_classifier", self._email_classifier_node)
        workflow.add_node("customer_service", self._customer_service_node)
        workflow.add_node("route_decision", self._route_decision_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Add edges
        workflow.set_entry_point("supervisor")
        
        workflow.add_conditional_edges(
            "supervisor",
            self._should_route_to_classifier,
            {
                "classify": "email_classifier",
                "direct_service": "customer_service",
                "end": END
            }
        )
        
        workflow.add_edge("email_classifier", "route_decision")
        workflow.add_edge("customer_service", "finalize")
        
        workflow.add_conditional_edges(
            "route_decision",
            self._route_after_classification,
            {
                "service": "customer_service",
                "specialist": "finalize",  # Will route to specialist agents in future phases
                "end": END
            }
        )
        
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def _supervisor_node(self, state: WorkflowState) -> WorkflowState:
        """Supervisor node - initial routing decision."""
        try:
            async with AsyncSessionLocal() as db:
                supervisor = SupervisorAgent(db)
                
                # Determine workflow type
                workflow_type = "email_processing"
                if "inquiry_type" in state.get("input_data", {}):
                    workflow_type = "customer_inquiry"
                
                result = await supervisor.process({
                    "workflow_type": workflow_type,
                    **state.get("input_data", {})
                })
                
                state["workflow_type"] = workflow_type
                state["final_result"] = result.data or {}
                
                if not result.success:
                    state["error"] = result.message
                    state["requires_human"] = True
                
                return state
                
        except Exception as e:
            state["error"] = str(e)
            state["requires_human"] = True
            return state
    
    async def _email_classifier_node(self, state: WorkflowState) -> WorkflowState:
        """Email classifier node."""
        try:
            async with AsyncSessionLocal() as db:
                classifier = EmailClassifierAgent(db)
                
                result = await classifier.process(state.get("input_data", {}))
                
                if result.success:
                    state["classification_result"] = result.data or {}
                else:
                    state["error"] = result.message
                    state["requires_human"] = True
                
                return state
                
        except Exception as e:
            state["error"] = str(e)
            state["requires_human"] = True
            return state
    
    async def _customer_service_node(self, state: WorkflowState) -> WorkflowState:
        """Customer service node."""
        try:
            async with AsyncSessionLocal() as db:
                service = CustomerServiceAgent(db)
                
                # Prepare input for customer service
                service_input = {
                    "inquiry_type": state.get("classification_result", {}).get("classification", "general"),
                    "message": state.get("input_data", {}).get("body", ""),
                    "customer_info": state.get("classification_result", {}).get("extracted_info", {})
                }
                
                result = await service.process(service_input)
                
                if result.success:
                    state["service_result"] = result.data or {}
                else:
                    state["error"] = result.message
                    state["requires_human"] = True
                
                return state
                
        except Exception as e:
            state["error"] = str(e)
            state["requires_human"] = True
            return state
    
    async def _route_decision_node(self, state: WorkflowState) -> WorkflowState:
        """Route decision node after classification."""
        classification = state.get("classification_result", {})
        
        # Determine next agent based on classification
        if classification.get("classification") in ["general_inquiry", "customer_service"]:
            state["next_agent"] = "customer_service"
        elif classification.get("classification") == "parts_order":
            state["next_agent"] = "parts_lookup"  # Future phase
        elif classification.get("classification") == "quote_request":
            state["next_agent"] = "pricing_invoice"  # Future phase
        else:
            state["next_agent"] = "customer_service"
        
        return state
    
    async def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow."""
        # Combine all results
        final_result = {
            "workflow_type": state.get("workflow_type"),
            "classification": state.get("classification_result"),
            "service_response": state.get("service_result"),
            "next_agent": state.get("next_agent"),
            "requires_human": state.get("requires_human", False),
            "error": state.get("error")
        }
        
        state["final_result"] = final_result
        return state
    
    def _should_route_to_classifier(self, state: WorkflowState) -> str:
        """Determine if we should route to email classifier."""
        if state.get("error"):
            return "end"
        
        workflow_type = state.get("workflow_type", "")
        if workflow_type == "email_processing":
            return "classify"
        elif workflow_type == "customer_inquiry":
            return "direct_service"
        else:
            return "end"
    
    def _route_after_classification(self, state: WorkflowState) -> str:
        """Route after classification."""
        if state.get("error"):
            return "end"
        
        next_agent = state.get("next_agent", "")
        if next_agent == "customer_service":
            return "service"
        elif next_agent in ["parts_lookup", "pricing_invoice", "shipping_coordinator"]:
            return "specialist"  # Future phases
        else:
            return "end"
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input through the workflow."""
        initial_state = WorkflowState(
            messages=[],
            workflow_type="",
            input_data=input_data,
            classification_result={},
            service_result={},
            final_result={},
            requires_human=False,
            next_agent="",
            error=""
        )
        
        try:
            final_state = await self.workflow.ainvoke(initial_state)
            return final_state.get("final_result", {})
        except Exception as e:
            return {
                "error": str(e),
                "requires_human": True,
                "workflow_type": "error"
            }
