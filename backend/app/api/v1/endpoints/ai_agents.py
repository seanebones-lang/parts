"""
AI Agent endpoints for testing and interaction.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.agents.langgraph_workflow import LangGraphWorkflow
from app.agents.supervisor import SupervisorAgent
from app.agents.email_classifier import EmailClassifierAgent
from app.agents.customer_service import CustomerServiceAgent

router = APIRouter()


@router.post("/process-email")
async def process_email(
    email_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Process an email through the AI agent workflow."""
    try:
        workflow = LangGraphWorkflow()
        result = await workflow.process(email_data)
        
        return {
            "success": True,
            "result": result,
            "message": "Email processed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email processing failed: {str(e)}")


@router.post("/classify-email")
async def classify_email(
    email_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Classify an email using the Email Classifier Agent."""
    try:
        classifier = EmailClassifierAgent(db)
        result = await classifier.process(email_data)
        
        return {
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "confidence": result.confidence,
            "processing_time": result.processing_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email classification failed: {str(e)}")


@router.post("/handle-customer-inquiry")
async def handle_customer_inquiry(
    inquiry_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Handle a customer inquiry using the Customer Service Agent."""
    try:
        service = CustomerServiceAgent(db)
        result = await service.process(inquiry_data)
        
        return {
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "confidence": result.confidence,
            "processing_time": result.processing_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Customer inquiry handling failed: {str(e)}")


@router.post("/supervisor-workflow")
async def supervisor_workflow(
    workflow_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Process through the Supervisor Agent workflow."""
    try:
        supervisor = SupervisorAgent(db)
        result = await supervisor.process(workflow_data)
        
        return {
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "confidence": result.confidence,
            "processing_time": result.processing_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supervisor workflow failed: {str(e)}")


@router.get("/agent-status")
async def get_agent_status(db: AsyncSession = Depends(get_db)):
    """Get status of all AI agents."""
    return {
        "agents": {
            "email_classifier": {
                "status": "active",
                "description": "Classifies emails and routes to appropriate departments"
            },
            "customer_service": {
                "status": "active", 
                "description": "Handles general customer inquiries"
            },
            "supervisor": {
                "status": "active",
                "description": "Orchestrates workflows between agents"
            },
            "parts_lookup": {
                "status": "pending",
                "description": "Searches inventory across locations (Phase 3)"
            },
            "pricing_invoice": {
                "status": "pending",
                "description": "Handles pricing and invoicing (Phase 4)"
            },
            "shipping_coordinator": {
                "status": "pending",
                "description": "Manages shipping and tracking (Phase 6)"
            },
            "supplier_sourcing": {
                "status": "pending",
                "description": "Sources parts from external suppliers (Phase 7)"
            },
            "follow_up": {
                "status": "pending",
                "description": "Automated follow-up workflows (Phase 8)"
            }
        },
        "workflow_status": "active",
        "langgraph_integration": "enabled"
    }


@router.post("/test-agent")
async def test_agent(
    agent_type: str,
    test_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Test a specific agent with sample data."""
    try:
        if agent_type == "email_classifier":
            agent = EmailClassifierAgent(db)
        elif agent_type == "customer_service":
            agent = CustomerServiceAgent(db)
        elif agent_type == "supervisor":
            agent = SupervisorAgent(db)
        else:
            raise HTTPException(status_code=400, detail="Invalid agent type")
        
        result = await agent.process(test_data)
        
        return {
            "agent_type": agent_type,
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "confidence": result.confidence,
            "processing_time": result.processing_time,
            "tokens_used": result.tokens_used,
            "cost": result.cost
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent test failed: {str(e)}")
