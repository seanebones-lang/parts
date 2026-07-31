"""
Parts Lookup Agent - Semantic search across parts catalog.
"""

import time
from typing import Dict, Any, List, Optional

from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.services.vector_service import VectorService
from app.services.parts_service import PartsService

# Optional core engine (owned by CORE under src/parrts) — use when importable
try:
    from parrts.engine import PartsRAGEngine  # type: ignore

    _PARRTS_ENGINE_AVAILABLE = True
except ImportError:
    PartsRAGEngine = None  # type: ignore
    _PARRTS_ENGINE_AVAILABLE = False


class PartsLookupAgent(BaseAgent):
    """Agent for semantic parts lookup and inventory checking."""

    def __init__(self, db):
        super().__init__(db, AgentType.PARTS_LOOKUP)
        self.vector_service = VectorService()
        self.parts_service = PartsService(db)
        self.parrts_engine = None
        if _PARRTS_ENGINE_AVAILABLE and PartsRAGEngine is not None:
            try:
                self.parrts_engine = PartsRAGEngine()
            except Exception:
                self.parrts_engine = None
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process parts lookup request."""
        start_time = time.time()
        
        try:
            query = input_data.get("query", "")
            vehicle_info = input_data.get("vehicle_info", {})
            location_id = input_data.get("location_id")
            customer_id = input_data.get("customer_id")
            
            # Step 1: Perform semantic search
            search_results = await self._semantic_search(query, vehicle_info)
            
            # Step 2: Check inventory across locations
            inventory_results = await self._check_inventory(search_results, location_id)
            
            # Step 3: Format and rank results
            formatted_results = await self._format_results(
                inventory_results, 
                query, 
                vehicle_info,
                customer_id
            )
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action="parts_lookup",
                input_data=input_data,
                output_data=formatted_results,
                success=True,
                processing_time=processing_time,
                confidence=self._calculate_confidence(formatted_results),
                customer_id=customer_id
            )
            
            return AgentResult(
                success=True,
                data=formatted_results,
                message="Parts lookup completed successfully",
                confidence=self._calculate_confidence(formatted_results),
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action="parts_lookup",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                customer_id=input_data.get("customer_id")
            )
            
            return AgentResult(
                success=False,
                message=f"Parts lookup failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _semantic_search(self, query: str, vehicle_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform semantic search on parts catalog."""
        enhanced_query = self._enhance_query(query, vehicle_info)
        filters = self._build_filters(vehicle_info)

        # Prefer CORE PartsRAGEngine when present (semantic search / demo path)
        if self.parrts_engine is not None:
            try:
                engine_results = await self._search_via_parrts(enhanced_query, vehicle_info, filters)
                if engine_results:
                    return engine_results
            except Exception:
                # Fall through to vector_service
                pass

        return await self.vector_service.semantic_search(
            query=enhanced_query,
            limit=10,
            filters=filters,
        )

    async def _search_via_parrts(
        self,
        query: str,
        vehicle_info: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Adapter around parrts.engine.PartsRAGEngine if available."""
        engine = self.parrts_engine
        if engine is None:
            return []

        search_fn = None
        for name in ("semantic_search", "search", "query", "lookup"):
            if hasattr(engine, name):
                search_fn = getattr(engine, name)
                break
        if search_fn is None:
            return []

        import inspect

        call_attempts = [
            lambda: search_fn(
                query=query, limit=10, filters=filters, vehicle_info=vehicle_info
            ),
            lambda: search_fn(query=query, limit=10, filters=filters),
            lambda: search_fn(query=query, top_k=10),
            lambda: search_fn(query=query),
            lambda: search_fn(query),
        ]

        raw = None
        last_err: Optional[Exception] = None
        for attempt in call_attempts:
            try:
                result = attempt()
                if inspect.isawaitable(result):
                    raw = await result
                else:
                    raw = result
                break
            except TypeError as exc:
                last_err = exc
                continue
            except Exception as exc:
                last_err = exc
                break

        if raw is None:
            if last_err:
                raise last_err
            return []

        return self._normalize_parrts_results(raw)

    def _normalize_parrts_results(self, raw: Any) -> List[Dict[str, Any]]:
        """Normalize engine output to list[dict] with relevance_score when possible."""
        if raw is None:
            return []
        if isinstance(raw, dict):
            for key in ("results", "parts", "items", "hits", "data"):
                if key in raw and isinstance(raw[key], list):
                    raw = raw[key]
                    break
            else:
                return [raw]
        if not isinstance(raw, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in raw:
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            elif hasattr(item, "dict"):
                item = item.dict()
            elif not isinstance(item, dict):
                item = {"value": item}
            if "relevance_score" not in item:
                score = item.get("score", item.get("similarity_score", item.get("similarity")))
                if score is not None:
                    try:
                        item["relevance_score"] = float(score)
                    except (TypeError, ValueError):
                        item["relevance_score"] = 0.0
            normalized.append(item)
        return normalized
    
    async def _check_inventory(self, parts: List[Dict[str, Any]], preferred_location_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Check inventory for parts across all locations."""
        inventory_results = []
        
        for part in parts:
            part_id = part.get("id")
            
            # Get inventory across all locations
            inventory = await self.parts_service.get_part_inventory(part_id)
            
            # Calculate availability and best location
            availability = self._calculate_availability(inventory, preferred_location_id)
            
            part_with_inventory = {
                **part,
                "inventory": inventory,
                "availability": availability
            }
            
            inventory_results.append(part_with_inventory)
        
        return inventory_results
    
    async def _format_results(self, results: List[Dict[str, Any]], query: str, vehicle_info: Dict[str, Any], customer_id: Optional[int] = None) -> Dict[str, Any]:
        """Format and rank search results."""
        # Sort by relevance and availability
        sorted_results = sorted(results, key=lambda x: (
            x.get("relevance_score", 0),
            x.get("availability", {}).get("total_quantity", 0)
        ), reverse=True)
        
        # Prepare response
        formatted_results = {
            "query": query,
            "vehicle_info": vehicle_info,
            "total_results": len(sorted_results),
            "parts": sorted_results[:5],  # Top 5 results
            "recommendations": self._generate_recommendations(sorted_results, vehicle_info),
            "alternative_parts": self._find_alternatives(sorted_results),
            "customer_history": await self._get_customer_history(customer_id) if customer_id else None
        }
        
        return formatted_results
    
    def _enhance_query(self, query: str, vehicle_info: Dict[str, Any]) -> str:
        """Enhance search query with vehicle context."""
        if not vehicle_info:
            return query
        
        make = vehicle_info.get("make", "")
        model = vehicle_info.get("model", "")
        year = vehicle_info.get("year", "")
        
        if make and model and year:
            return f"{query} for {year} {make} {model}"
        elif make and model:
            return f"{query} for {make} {model}"
        else:
            return query
    
    def _build_filters(self, vehicle_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build filters for vector search (plain scalars for bound SQL params)."""
        filters: Dict[str, Any] = {}

        if vehicle_info.get("make"):
            filters["make"] = vehicle_info["make"]
        if vehicle_info.get("model"):
            filters["model"] = vehicle_info["model"]
        if vehicle_info.get("year"):
            year = vehicle_info["year"]
            # Vehicle year must fall within part year_from/year_to range
            filters["year_from"] = year
            filters["year_to"] = year

        return filters
    
    def _calculate_availability(self, inventory: List[Dict[str, Any]], preferred_location_id: Optional[int] = None) -> Dict[str, Any]:
        """Calculate availability metrics."""
        total_quantity = sum(item.get("quantity_available", 0) for item in inventory)
        total_locations = len([item for item in inventory if item.get("quantity_available", 0) > 0])
        
        # Find best location (closest to preferred or highest stock)
        best_location = None
        if preferred_location_id:
            preferred_item = next(
                (item for item in inventory if item.get("location_id") == preferred_location_id), 
                None
            )
            if preferred_item and preferred_item.get("quantity_available", 0) > 0:
                best_location = preferred_item
        
        if not best_location:
            best_location = max(inventory, key=lambda x: x.get("quantity_available", 0))
        
        return {
            "total_quantity": total_quantity,
            "available_locations": total_locations,
            "best_location": best_location,
            "in_stock": total_quantity > 0,
            "needs_reorder": any(item.get("needs_reorder", False) for item in inventory)
        }
    
    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate confidence score for search results."""
        parts = results.get("parts", [])
        if not parts:
            return 0.1
        
        # Base confidence on top result relevance
        top_result = parts[0]
        relevance_score = top_result.get("relevance_score", 0)
        
        # Boost confidence if we have inventory
        availability = top_result.get("availability", {})
        if availability.get("in_stock"):
            relevance_score += 0.2
        
        return min(1.0, relevance_score)
    
    def _generate_recommendations(self, results: List[Dict[str, Any]], vehicle_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations based on search results."""
        recommendations = []
        
        # Recommend based on availability
        in_stock_parts = [part for part in results if part.get("availability", {}).get("in_stock")]
        if in_stock_parts:
            recommendations.append({
                "type": "in_stock",
                "message": f"Found {len(in_stock_parts)} parts in stock",
                "parts": in_stock_parts[:3]
            })
        
        # Recommend compatible parts
        compatible_parts = [part for part in results if self._is_compatible(part, vehicle_info)]
        if compatible_parts:
            recommendations.append({
                "type": "compatible",
                "message": f"Found {len(compatible_parts)} compatible parts",
                "parts": compatible_parts[:3]
            })
        
        return recommendations
    
    def _find_alternatives(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find alternative parts for out-of-stock items."""
        alternatives = []
        
        for part in results:
            if not part.get("availability", {}).get("in_stock"):
                # Look for similar parts from different manufacturers
                alternatives.append({
                    "original_part": part,
                    "message": "Alternative parts available",
                    "suggestions": []  # Will be populated with actual alternatives
                })
        
        return alternatives
    
    async def _get_customer_history(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer's parts purchase history."""
        if not customer_id:
            return None
        
        # This will be implemented to fetch customer history
        return {
            "recent_parts": [],
            "frequent_parts": [],
            "preferred_locations": []
        }
    
    def _is_compatible(self, part: Dict[str, Any], vehicle_info: Dict[str, Any]) -> bool:
        """Check if part is compatible with vehicle."""
        if not vehicle_info:
            return True
        
        part_make = part.get("make", "")
        part_model = part.get("model", "")
        part_year_from = part.get("year_from")
        part_year_to = part.get("year_to")
        
        vehicle_make = vehicle_info.get("make", "")
        vehicle_model = vehicle_info.get("model", "")
        vehicle_year = vehicle_info.get("year")
        
        # Check make/model compatibility
        if part_make and vehicle_make and part_make.lower() != vehicle_make.lower():
            return False
        
        if part_model and vehicle_model and part_model.lower() != vehicle_model.lower():
            return False
        
        # Check year compatibility
        if vehicle_year and part_year_from and part_year_to:
            return part_year_from <= vehicle_year <= part_year_to
        
        return True
