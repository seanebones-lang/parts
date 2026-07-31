"""
LangGraph workflow for orchestrating AI agents.

Wave 9 (2026-07-31):
- Full specialist graph: email → parts | service | inventory | pricing |
  payment | shipping | supplier | follow_up → finalize
- parts_lookup prefers `parrts` hybrid RAG when importable / DB down
- Soft-fail every specialist when DB or agent deps are unavailable
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.core.database import AsyncSessionLocal


class WorkflowState(TypedDict, total=False):
    """State for the LangGraph workflow."""

    messages: Annotated[List[BaseMessage], add_messages]
    workflow_type: str
    input_data: Dict[str, Any]
    classification_result: Dict[str, Any]
    service_result: Dict[str, Any]
    parts_result: Dict[str, Any]
    inventory_result: Dict[str, Any]
    pricing_result: Dict[str, Any]
    payment_result: Dict[str, Any]
    shipping_result: Dict[str, Any]
    supplier_result: Dict[str, Any]
    follow_up_result: Dict[str, Any]
    final_result: Dict[str, Any]
    requires_human: bool
    next_agent: str
    error: str
    agents_invoked: List[str]


SPECIALIST_NODES = (
    "parts_lookup",
    "customer_service",
    "inventory",
    "pricing",
    "payment",
    "shipping",
    "supplier",
    "follow_up",
)


def _result_public(result: Any) -> Dict[str, Any]:
    if result is None:
        return {}
    if hasattr(result, "to_public_dict"):
        return result.to_public_dict()
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {"raw": str(result)}


def _mark_human(state: WorkflowState, result: Any = None, color: Any = None) -> None:
    if result is not None:
        if getattr(result, "requires_human", False):
            state["requires_human"] = True
        data = getattr(result, "data", None) or {}
        if isinstance(data, dict):
            color = color or data.get("color") or data.get("traffic_light")
            if isinstance(data.get("traffic_light"), dict):
                color = data["traffic_light"].get("color")
    if str(color or "").lower() in {"red", "yellow"}:
        state["requires_human"] = True


class LangGraphWorkflow:
    """LangGraph workflow for orchestrating dealership specialist agents."""

    def __init__(self) -> None:
        self.workflow = self._build_workflow()

    def graph_nodes(self) -> List[str]:
        """Return registered node names (for tests / status)."""
        return [
            "supervisor",
            "email_classifier",
            "route_decision",
            *SPECIALIST_NODES,
            "finalize",
        ]

    def _build_workflow(self):
        workflow = StateGraph(WorkflowState)

        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("email_classifier", self._email_classifier_node)
        workflow.add_node("route_decision", self._route_decision_node)
        workflow.add_node("parts_lookup", self._parts_lookup_node)
        workflow.add_node("customer_service", self._customer_service_node)
        workflow.add_node("inventory", self._inventory_node)
        workflow.add_node("pricing", self._pricing_node)
        workflow.add_node("payment", self._payment_node)
        workflow.add_node("shipping", self._shipping_node)
        workflow.add_node("supplier", self._supplier_node)
        workflow.add_node("follow_up", self._follow_up_node)
        workflow.add_node("finalize", self._finalize_node)

        workflow.set_entry_point("supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self._should_route_to_classifier,
            {
                "classify": "email_classifier",
                "direct_service": "customer_service",
                "parts": "parts_lookup",
                "inventory": "inventory",
                "pricing": "pricing",
                "payment": "payment",
                "shipping": "shipping",
                "supplier": "supplier",
                "follow_up": "follow_up",
                "end": END,
            },
        )

        workflow.add_edge("email_classifier", "route_decision")

        route_map = {
            "service": "customer_service",
            "parts": "parts_lookup",
            "inventory": "inventory",
            "pricing": "pricing",
            "payment": "payment",
            "shipping": "shipping",
            "supplier": "supplier",
            "follow_up": "follow_up",
            "end": END,
        }
        workflow.add_conditional_edges(
            "route_decision", self._route_after_classification, route_map
        )

        for node in SPECIALIST_NODES:
            workflow.add_edge(node, "finalize")
        workflow.add_edge("finalize", END)
        return workflow.compile()

    def _track(self, state: WorkflowState, name: str) -> None:
        invoked = list(state.get("agents_invoked") or [])
        if name not in invoked:
            invoked.append(name)
        state["agents_invoked"] = invoked

    async def _run_agent(
        self,
        state: WorkflowState,
        *,
        agent_key: str,
        import_path: str,
        class_name: str,
        payload: Dict[str, Any],
        result_key: str,
        offline_fallback: Optional[Dict[str, Any]] = None,
    ) -> WorkflowState:
        self._track(state, agent_key)
        try:
            module = __import__(import_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            async with AsyncSessionLocal() as db:
                agent = cls(db)
                result = await agent.process(payload)
                if getattr(result, "success", False):
                    state[result_key] = _result_public(result)
                    _mark_human(state, result)
                else:
                    state[result_key] = _result_public(result) or {
                        "success": False,
                        "message": getattr(result, "message", "failed"),
                    }
                    state["requires_human"] = True
                    if getattr(result, "message", None):
                        state["error"] = result.message
                return state
        except Exception as exc:
            if offline_fallback is not None:
                state[result_key] = {**offline_fallback, "fallback": True, "error": str(exc)}
            else:
                state[result_key] = {
                    "success": False,
                    "message": f"{agent_key} unavailable",
                    "error": str(exc),
                    "requires_human": True,
                }
                state["requires_human"] = True
            return state

    async def _supervisor_node(self, state: WorkflowState) -> WorkflowState:
        self._track(state, "supervisor")
        input_data = state.get("input_data", {}) or {}
        try:
            from app.agents.supervisor import SupervisorAgent

            async with AsyncSessionLocal() as db:
                supervisor = SupervisorAgent(db)
                workflow_type = "email_processing"
                if "inquiry_type" in input_data:
                    workflow_type = "customer_inquiry"
                if input_data.get("parts_query") or input_data.get("query"):
                    workflow_type = "parts_lookup"
                if input_data.get("action") in {
                    "check_inventory",
                    "process_receiving",
                    "trigger_reorder",
                    "transfer_stock",
                }:
                    workflow_type = "inventory"
                if input_data.get("workflow_type"):
                    workflow_type = str(input_data["workflow_type"])

                result = await supervisor.process(
                    {"workflow_type": workflow_type, **input_data}
                )
                state["workflow_type"] = workflow_type
                state["final_result"] = getattr(result, "data", None) or {}
                if not getattr(result, "success", True):
                    state["error"] = getattr(result, "message", "") or ""
                    state["requires_human"] = True
                return state
        except Exception as e:
            state["error"] = ""
            if input_data.get("parts_query") or input_data.get("query"):
                state["workflow_type"] = "parts_lookup"
            elif input_data.get("action") in {
                "check_inventory",
                "process_receiving",
                "trigger_reorder",
                "transfer_stock",
            }:
                state["workflow_type"] = "inventory"
            elif input_data.get("workflow_type"):
                state["workflow_type"] = str(input_data["workflow_type"])
            elif "body" in input_data or "subject" in input_data:
                state["workflow_type"] = "email_processing"
            else:
                state["workflow_type"] = "customer_inquiry"
            state.setdefault("final_result", {})
            state["_supervisor_soft_error"] = str(e)  # type: ignore[typeddict-item]
            return state

    async def _email_classifier_node(self, state: WorkflowState) -> WorkflowState:
        self._track(state, "email_classifier")
        try:
            from app.agents.email_classifier import EmailClassifierAgent

            async with AsyncSessionLocal() as db:
                classifier = EmailClassifierAgent(db)
                result = await classifier.process(state.get("input_data", {}) or {})
                if getattr(result, "success", False):
                    state["classification_result"] = getattr(result, "data", None) or {}
                else:
                    state["error"] = getattr(result, "message", "") or ""
                    state["requires_human"] = True
                return state
        except Exception as e:
            body = (state.get("input_data", {}) or {}).get("body", "")
            subject = (state.get("input_data", {}) or {}).get("subject", "")
            blob = f"{subject} {body}".lower()
            if any(k in blob for k in ("ship", "tracking", "ups", "fedex", "deliver")):
                classification = "shipping"
            elif any(k in blob for k in ("pay", "invoice", "stripe", "card")):
                classification = "payment_inquiry"
            elif any(k in blob for k in ("quote", "price", "how much", "msrp")):
                classification = "quote_request"
            elif any(k in blob for k in ("reorder", "stock", "receiving", "transfer")):
                classification = "inventory"
            elif any(k in blob for k in ("supplier", "source", "oem", "aftermarket")):
                classification = "supplier"
            elif any(k in blob for k in ("follow", "reminder", "check in")):
                classification = "follow_up"
            elif any(k in blob for k in ("part", "brake", "filter", "sku", "order")):
                classification = "parts_order"
            else:
                classification = "general_inquiry"
            state["classification_result"] = {
                "classification": classification,
                "fallback": True,
                "error": str(e),
            }
            return state

    async def _customer_service_node(self, state: WorkflowState) -> WorkflowState:
        payload = {
            "inquiry_type": (state.get("classification_result") or {}).get(
                "classification", "general"
            ),
            "message": (state.get("input_data") or {}).get("body", ""),
            "customer_info": (state.get("classification_result") or {}).get(
                "extracted_info", {}
            ),
        }
        return await self._run_agent(
            state,
            agent_key="customer_service",
            import_path="app.agents.customer_service",
            class_name="CustomerServiceAgent",
            payload=payload,
            result_key="service_result",
            offline_fallback={
                "success": True,
                "message": "Customer service offline stub — escalate if needed.",
                "requires_human": True,
            },
        )

    async def _parts_lookup_node(self, state: WorkflowState) -> WorkflowState:
        self._track(state, "parts_lookup")
        input_data = state.get("input_data", {}) or {}
        query = (
            input_data.get("parts_query")
            or input_data.get("query")
            or input_data.get("body")
            or input_data.get("subject")
            or ""
        )
        vehicle_info = input_data.get("vehicle_info") or (
            state.get("classification_result") or {}
        ).get("extracted_info", {})

        try:
            from app.agents.parts_lookup import PartsLookupAgent

            async with AsyncSessionLocal() as db:
                agent = PartsLookupAgent(db)
                result = await agent.process(
                    {
                        "query": query,
                        "vehicle_info": vehicle_info,
                        "location": input_data.get("location"),
                    }
                )
                if getattr(result, "success", False):
                    state["parts_result"] = _result_public(result)
                    _mark_human(state, result)
                else:
                    state["error"] = getattr(result, "message", "") or ""
                    state["requires_human"] = True
                    state["parts_result"] = _result_public(result)
                return state
        except Exception:
            try:
                from pathlib import Path

                from parrts.embeddings import HashingEmbedder
                from parrts.engine import PartsRAGEngine

                root = Path(__file__).resolve().parents[3]
                if not (root / "pyproject.toml").exists():
                    root = Path.cwd()
                engine = PartsRAGEngine(root=root, embedder=HashingEmbedder())
                engine.ensure_ready()
                qr = engine.query(
                    text=str(query),
                    use_llm=False,
                    expand_parent=bool(input_data.get("expand_parent", False)),
                )
                data = qr.to_dict()
                state["parts_result"] = data
                color = (data.get("traffic_light") or {}).get("color")
                _mark_human(state, color=color)
            except Exception as inner:
                state["error"] = str(inner)
                state["requires_human"] = True
                state["parts_result"] = {}
            return state

    async def _inventory_node(self, state: WorkflowState) -> WorkflowState:
        input_data = state.get("input_data", {}) or {}
        return await self._run_agent(
            state,
            agent_key="inventory",
            import_path="app.agents.inventory_manager",
            class_name="InventoryManagerAgent",
            payload={
                "action": input_data.get("action", "check_inventory"),
                **input_data,
            },
            result_key="inventory_result",
            offline_fallback={
                "success": True,
                "message": "Inventory agent offline — use parrts inventory summary",
                "hint": "python -m parrts status",
            },
        )

    async def _pricing_node(self, state: WorkflowState) -> WorkflowState:
        input_data = state.get("input_data", {}) or {}
        # Prefer parts hits already in state for quote context
        payload = {
            **input_data,
            "parts": (state.get("parts_result") or {}).get("data")
            or (state.get("parts_result") or {}).get("hits")
            or [],
        }
        return await self._run_agent(
            state,
            agent_key="pricing",
            import_path="app.agents.pricing_invoice",
            class_name="PricingInvoiceAgent",
            payload=payload,
            result_key="pricing_result",
            offline_fallback={
                "success": True,
                "message": "Pricing offline stub",
                "requires_human": True,
            },
        )

    async def _payment_node(self, state: WorkflowState) -> WorkflowState:
        return await self._run_agent(
            state,
            agent_key="payment",
            import_path="app.agents.payment_agent",
            class_name="PaymentAgent",
            payload=state.get("input_data", {}) or {},
            result_key="payment_result",
            offline_fallback={
                "success": True,
                "message": "Payment mock path (no Stripe keys)",
                "mode": "mock",
            },
        )

    async def _shipping_node(self, state: WorkflowState) -> WorkflowState:
        return await self._run_agent(
            state,
            agent_key="shipping",
            import_path="app.agents.shipping_coordinator",
            class_name="ShippingCoordinatorAgent",
            payload=state.get("input_data", {}) or {},
            result_key="shipping_result",
            offline_fallback={
                "success": True,
                "message": "Shipping mock path (no EasyPost keys)",
                "mode": "mock",
            },
        )

    async def _supplier_node(self, state: WorkflowState) -> WorkflowState:
        return await self._run_agent(
            state,
            agent_key="supplier",
            import_path="app.agents.supplier_sourcing",
            class_name="SupplierSourcingAgent",
            payload=state.get("input_data", {}) or {},
            result_key="supplier_result",
            offline_fallback={
                "success": True,
                "message": "Supplier sourcing disabled without feature flag",
                "mode": "stub",
            },
        )

    async def _follow_up_node(self, state: WorkflowState) -> WorkflowState:
        return await self._run_agent(
            state,
            agent_key="follow_up",
            import_path="app.agents.follow_up",
            class_name="FollowUpAgent",
            payload=state.get("input_data", {}) or {},
            result_key="follow_up_result",
            offline_fallback={
                "success": True,
                "message": "Follow-up scheduled stub",
                "mode": "stub",
            },
        )

    async def _route_decision_node(self, state: WorkflowState) -> WorkflowState:
        self._track(state, "route_decision")
        classification = state.get("classification_result", {}) or {}
        label = str(classification.get("classification", "")).lower()
        input_data = state.get("input_data") or {}

        if label in {"parts_order", "parts_lookup"}:
            state["next_agent"] = "parts_lookup"
        elif label in {"quote_request", "pricing"}:
            state["next_agent"] = "pricing"
        elif label in {"inventory", "reorder", "receiving"}:
            state["next_agent"] = "inventory"
        elif label in {"payment_inquiry", "payment"}:
            state["next_agent"] = "payment"
        elif label in {"shipping", "delivery"}:
            state["next_agent"] = "shipping"
        elif label in {"supplier", "sourcing"}:
            state["next_agent"] = "supplier"
        elif label in {"follow_up", "reminder"}:
            state["next_agent"] = "follow_up"
        elif label in {"general_inquiry", "customer_service", "complaint"}:
            state["next_agent"] = "customer_service"
        else:
            blob = f"{input_data.get('body', '')} {input_data.get('subject', '')}".lower()
            if any(k in blob for k in ("part", "brake", "filter", "stock", "sku")):
                state["next_agent"] = "parts_lookup"
            else:
                state["next_agent"] = "customer_service"
        return state

    async def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        self._track(state, "finalize")
        state["final_result"] = {
            "workflow_type": state.get("workflow_type"),
            "classification": state.get("classification_result"),
            "service_response": state.get("service_result"),
            "parts_response": state.get("parts_result"),
            "inventory_response": state.get("inventory_result"),
            "pricing_response": state.get("pricing_result"),
            "payment_response": state.get("payment_result"),
            "shipping_response": state.get("shipping_result"),
            "supplier_response": state.get("supplier_result"),
            "follow_up_response": state.get("follow_up_result"),
            "next_agent": state.get("next_agent"),
            "agents_invoked": state.get("agents_invoked") or [],
            "requires_human": state.get("requires_human", False),
            "error": state.get("error") or None,
        }
        return state

    def _should_route_to_classifier(self, state: WorkflowState) -> str:
        workflow_type = state.get("workflow_type", "")
        mapping = {
            "parts_lookup": "parts",
            "email_processing": "classify",
            "customer_inquiry": "direct_service",
            "inventory": "inventory",
            "pricing": "pricing",
            "payment": "payment",
            "shipping": "shipping",
            "supplier": "supplier",
            "follow_up": "follow_up",
        }
        return mapping.get(workflow_type, "end")

    def _route_after_classification(self, state: WorkflowState) -> str:
        if state.get("error") and not state.get("classification_result"):
            return "end"
        next_agent = state.get("next_agent", "")
        mapping = {
            "parts_lookup": "parts",
            "customer_service": "service",
            "inventory": "inventory",
            "pricing": "pricing",
            "payment": "payment",
            "shipping": "shipping",
            "supplier": "supplier",
            "follow_up": "follow_up",
        }
        return mapping.get(next_agent, "end")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        initial_state: WorkflowState = {
            "messages": [],
            "workflow_type": "",
            "input_data": input_data,
            "classification_result": {},
            "service_result": {},
            "parts_result": {},
            "inventory_result": {},
            "pricing_result": {},
            "payment_result": {},
            "shipping_result": {},
            "supplier_result": {},
            "follow_up_result": {},
            "final_result": {},
            "requires_human": False,
            "next_agent": "",
            "error": "",
            "agents_invoked": [],
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
