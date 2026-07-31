"""
LangGraph workflow for orchestrating AI agents.

Modern path (2026-07-31):
- email_classifier → route → parts_lookup | customer_service | finalize
- parts_lookup prefers `parrts` hybrid RAG when importable
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.agents.customer_service import CustomerServiceAgent
from app.agents.email_classifier import EmailClassifierAgent
from app.agents.parts_lookup import PartsLookupAgent
from app.agents.supervisor import SupervisorAgent
from app.core.database import AsyncSessionLocal


class WorkflowState(TypedDict):
    """State for the LangGraph workflow."""

    messages: Annotated[List[BaseMessage], add_messages]
    workflow_type: str
    input_data: Dict[str, Any]
    classification_result: Dict[str, Any]
    service_result: Dict[str, Any]
    parts_result: Dict[str, Any]
    final_result: Dict[str, Any]
    requires_human: bool
    next_agent: str
    error: str


class LangGraphWorkflow:
    """LangGraph workflow for orchestrating agents."""

    def __init__(self) -> None:
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(WorkflowState)

        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("email_classifier", self._email_classifier_node)
        workflow.add_node("customer_service", self._customer_service_node)
        workflow.add_node("parts_lookup", self._parts_lookup_node)
        workflow.add_node("route_decision", self._route_decision_node)
        workflow.add_node("finalize", self._finalize_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self._should_route_to_classifier,
            {
                "classify": "email_classifier",
                "direct_service": "customer_service",
                "parts": "parts_lookup",
                "end": END,
            },
        )

        workflow.add_edge("email_classifier", "route_decision")
        workflow.add_edge("customer_service", "finalize")
        workflow.add_edge("parts_lookup", "finalize")

        workflow.add_conditional_edges(
            "route_decision",
            self._route_after_classification,
            {
                "service": "customer_service",
                "parts": "parts_lookup",
                "end": END,
            },
        )

        workflow.add_edge("finalize", END)
        return workflow.compile()

    async def _supervisor_node(self, state: WorkflowState) -> WorkflowState:
        try:
            async with AsyncSessionLocal() as db:
                supervisor = SupervisorAgent(db)

                workflow_type = "email_processing"
                input_data = state.get("input_data", {}) or {}
                if "inquiry_type" in input_data:
                    workflow_type = "customer_inquiry"
                if input_data.get("parts_query") or input_data.get("query"):
                    workflow_type = "parts_lookup"

                result = await supervisor.process(
                    {"workflow_type": workflow_type, **input_data}
                )

                state["workflow_type"] = workflow_type
                state["final_result"] = result.data or {}

                if not result.success:
                    state["error"] = result.message
                    state["requires_human"] = True

                return state
        except Exception as e:
            # Soft-fail supervisor when DB is down — still allow parts path
            state["error"] = ""
            input_data = state.get("input_data", {}) or {}
            if input_data.get("parts_query") or input_data.get("query"):
                state["workflow_type"] = "parts_lookup"
            elif "body" in input_data or "subject" in input_data:
                state["workflow_type"] = "email_processing"
            else:
                state["workflow_type"] = "customer_inquiry"
            state.setdefault("final_result", {})
            state["_supervisor_soft_error"] = str(e)  # type: ignore[typeddict-item]
            return state

    async def _email_classifier_node(self, state: WorkflowState) -> WorkflowState:
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
            # Heuristic fallback without LLM/DB
            body = (state.get("input_data", {}) or {}).get("body", "")
            subject = (state.get("input_data", {}) or {}).get("subject", "")
            blob = f"{subject} {body}".lower()
            if any(k in blob for k in ("part", "brake", "filter", "stock", "sku", "order")):
                classification = "parts_order"
            elif any(k in blob for k in ("quote", "price", "how much")):
                classification = "quote_request"
            else:
                classification = "general_inquiry"
            state["classification_result"] = {
                "classification": classification,
                "fallback": True,
                "error": str(e),
            }
            return state

    async def _customer_service_node(self, state: WorkflowState) -> WorkflowState:
        try:
            async with AsyncSessionLocal() as db:
                service = CustomerServiceAgent(db)
                service_input = {
                    "inquiry_type": state.get("classification_result", {}).get(
                        "classification", "general"
                    ),
                    "message": state.get("input_data", {}).get("body", ""),
                    "customer_info": state.get("classification_result", {}).get(
                        "extracted_info", {}
                    ),
                }
                result = await service.process(service_input)
                if result.success:
                    state["service_result"] = result.data or {}
                else:
                    state["error"] = result.message
                    state["requires_human"] = True
                return state
        except Exception as e:
            state["service_result"] = {
                "message": "Customer service unavailable; escalate to human.",
                "error": str(e),
            }
            state["requires_human"] = True
            return state

    async def _parts_lookup_node(self, state: WorkflowState) -> WorkflowState:
        input_data = state.get("input_data", {}) or {}
        query = (
            input_data.get("parts_query")
            or input_data.get("query")
            or input_data.get("body")
            or input_data.get("subject")
            or ""
        )
        vehicle_info = input_data.get("vehicle_info") or state.get(
            "classification_result", {}
        ).get("extracted_info", {})

        try:
            async with AsyncSessionLocal() as db:
                agent = PartsLookupAgent(db)
                result = await agent.process(
                    {
                        "query": query,
                        "vehicle_info": vehicle_info,
                        "location": input_data.get("location"),
                    }
                )
                if result.success:
                    state["parts_result"] = result.data or {}
                    # traffic light may require human
                    color = (result.data or {}).get("color") or (result.data or {}).get(
                        "traffic_light"
                    )
                    if str(color).lower() in {"red", "yellow"}:
                        state["requires_human"] = True
                else:
                    state["error"] = result.message
                    state["requires_human"] = True
                return state
        except Exception:
            # Direct parrts core fallback (no DB)
            try:
                from pathlib import Path

                from parrts.embeddings import HashingEmbedder
                from parrts.engine import PartsRAGEngine

                root = Path(__file__).resolve().parents[3]
                if not (root / "pyproject.toml").exists():
                    root = Path.cwd()
                engine = PartsRAGEngine(root=root, embedder=HashingEmbedder())
                engine.ensure_ready()
                qr = engine.query(text=str(query), use_llm=False)
                state["parts_result"] = qr.to_dict()
                color = (qr.to_dict().get("traffic_light") or {}).get("color") or qr.to_dict().get(
                    "color"
                )
                if str(color).lower() in {"red", "yellow"}:
                    state["requires_human"] = True
            except Exception as inner:
                state["error"] = str(inner)
                state["requires_human"] = True
                state["parts_result"] = {}
            return state

    async def _route_decision_node(self, state: WorkflowState) -> WorkflowState:
        classification = state.get("classification_result", {}) or {}
        label = str(classification.get("classification", "")).lower()

        if label in {"parts_order", "quote_request", "parts_lookup", "inventory"}:
            state["next_agent"] = "parts_lookup"
        elif label in {"general_inquiry", "customer_service", "complaint", "payment_inquiry"}:
            state["next_agent"] = "customer_service"
        else:
            # Default: if body looks like a parts query, go parts
            blob = str((state.get("input_data") or {}).get("body", "")).lower()
            if any(k in blob for k in ("part", "brake", "filter", "stock", "sku")):
                state["next_agent"] = "parts_lookup"
            else:
                state["next_agent"] = "customer_service"
        return state

    async def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        state["final_result"] = {
            "workflow_type": state.get("workflow_type"),
            "classification": state.get("classification_result"),
            "service_response": state.get("service_result"),
            "parts_response": state.get("parts_result"),
            "next_agent": state.get("next_agent"),
            "requires_human": state.get("requires_human", False),
            "error": state.get("error") or None,
        }
        return state

    def _should_route_to_classifier(self, state: WorkflowState) -> str:
        if state.get("error") and state.get("workflow_type") not in {
            "parts_lookup",
            "email_processing",
            "customer_inquiry",
        }:
            return "end"

        workflow_type = state.get("workflow_type", "")
        if workflow_type == "parts_lookup":
            return "parts"
        if workflow_type == "email_processing":
            return "classify"
        if workflow_type == "customer_inquiry":
            return "direct_service"
        return "end"

    def _route_after_classification(self, state: WorkflowState) -> str:
        if state.get("error") and not state.get("classification_result"):
            return "end"
        next_agent = state.get("next_agent", "")
        if next_agent == "parts_lookup":
            return "parts"
        if next_agent == "customer_service":
            return "service"
        return "end"

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        initial_state: WorkflowState = {
            "messages": [],
            "workflow_type": "",
            "input_data": input_data,
            "classification_result": {},
            "service_result": {},
            "parts_result": {},
            "final_result": {},
            "requires_human": False,
            "next_agent": "",
            "error": "",
        }
        try:
            final_state = await self.workflow.ainvoke(initial_state)
            return final_state.get("final_result", {})
        except Exception as e:
            return {
                "error": str(e),
                "requires_human": True,
                "workflow_type": "error",
            }
