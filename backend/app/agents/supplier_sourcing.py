"""
Supplier Sourcing Agent - Finds parts from external suppliers when out of stock.
"""

import time
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.services.supplier_service import SupplierService
from app.services.scraping_service import ScrapingService
from app.services.price_comparison_service import PriceComparisonService


class SupplierSourcingAgent(BaseAgent):
    """Agent for sourcing parts from external suppliers."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.SUPPLIER_SOURCING)
        self.supplier_service = SupplierService(db)
        self.scraping_service = ScrapingService(db)
        self.price_comparison_service = PriceComparisonService(db)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process parts sourcing request."""
        start_time = time.time()
        
        try:
            action = input_data.get("action", "find_parts")
            
            if action == "find_parts":
                result = await self._find_parts_from_suppliers(input_data)
            elif action == "compare_prices":
                result = await self._compare_supplier_prices(input_data)
            elif action == "check_availability":
                result = await self._check_supplier_availability(input_data)
            elif action == "place_supplier_order":
                result = await self._place_supplier_order(input_data)
            elif action == "update_supplier_data":
                result = await self._update_supplier_data(input_data)
            elif action == "scrape_supplier_catalog":
                result = await self._scrape_supplier_catalog(input_data)
            else:
                result = await self._general_sourcing_workflow(input_data)
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action=f"sourcing_{action}",
                input_data=input_data,
                output_data=result,
                success=True,
                processing_time=processing_time,
                confidence=0.95,
                customer_id=input_data.get("customer_id"),
                part_id=input_data.get("part_id")
            )
            
            return AgentResult(
                success=True,
                data=result,
                message=f"Parts sourcing {action} completed successfully",
                confidence=0.95,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action=f"sourcing_{input_data.get('action', 'unknown')}",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                customer_id=input_data.get("customer_id"),
                part_id=input_data.get("part_id")
            )
            
            return AgentResult(
                success=False,
                message=f"Parts sourcing failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _find_parts_from_suppliers(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Find parts from external suppliers when out of stock."""
        part_number = input_data.get("part_number")
        part_name = input_data.get("part_name")
        vehicle_info = input_data.get("vehicle_info", {})
        max_suppliers = input_data.get("max_suppliers", 5)
        
        if not part_number and not part_name:
            return {"success": False, "error": "part_number or part_name is required"}
        
        # Get active suppliers
        suppliers = await self.supplier_service.get_active_suppliers()
        
        if not suppliers:
            return {"success": False, "error": "No active suppliers found"}
        
        # Search each supplier for the part
        supplier_results = []
        successful_searches = 0
        
        for supplier in suppliers[:max_suppliers]:
            try:
                # Search supplier for the part
                search_result = await self.scraping_service.search_supplier(
                    supplier_id=supplier["id"],
                    part_number=part_number,
                    part_name=part_name,
                    vehicle_info=vehicle_info
                )
                
                if search_result["success"] and search_result["parts"]:
                    supplier_results.append({
                        "supplier": supplier,
                        "parts": search_result["parts"],
                        "search_time": search_result.get("search_time", 0),
                        "confidence": search_result.get("confidence", 0.8)
                    })
                    successful_searches += 1
                
            except Exception as e:
                print(f"Error searching supplier {supplier['name']}: {e}")
                continue
        
        if not supplier_results:
            return {
                "success": False,
                "error": "Part not found in any supplier catalog",
                "searched_suppliers": len(suppliers[:max_suppliers]),
                "successful_searches": successful_searches
            }
        
        # Compare prices and availability
        comparison_result = await self.price_comparison_service.compare_parts(
            supplier_results=supplier_results,
            part_number=part_number,
            part_name=part_name
        )
        
        # Generate recommendations
        recommendations = self._generate_sourcing_recommendations(comparison_result)
        
        return {
            "success": True,
            "part_number": part_number,
            "part_name": part_name,
            "supplier_results": supplier_results,
            "price_comparison": comparison_result,
            "recommendations": recommendations,
            "total_suppliers_searched": len(suppliers[:max_suppliers]),
            "successful_searches": successful_searches,
            "best_option": self._select_best_option(comparison_result)
        }
    
    async def _compare_supplier_prices(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare prices across multiple suppliers."""
        parts_data = input_data.get("parts_data", [])
        
        if not parts_data:
            return {"success": False, "error": "parts_data is required"}
        
        # Compare prices
        comparison_result = await self.price_comparison_service.compare_parts(
            supplier_results=parts_data,
            part_number=input_data.get("part_number"),
            part_name=input_data.get("part_name")
        )
        
        # Generate price insights
        price_insights = self._generate_price_insights(comparison_result)
        
        return {
            "success": True,
            "comparison": comparison_result,
            "insights": price_insights,
            "recommendations": self._generate_price_recommendations(comparison_result)
        }
    
    async def _check_supplier_availability(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check real-time availability from suppliers."""
        supplier_id = input_data.get("supplier_id")
        part_number = input_data.get("part_number")
        
        if not supplier_id or not part_number:
            return {"success": False, "error": "supplier_id and part_number are required"}
        
        # Check availability
        availability_result = await self.scraping_service.check_availability(
            supplier_id=supplier_id,
            part_number=part_number
        )
        
        if availability_result["success"]:
            # Update supplier data
            await self.supplier_service.update_part_availability(
                supplier_id=supplier_id,
                part_number=part_number,
                availability_data=availability_result["availability"]
            )
        
        return availability_result
    
    async def _place_supplier_order(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place order with external supplier."""
        supplier_id = input_data.get("supplier_id")
        parts = input_data.get("parts", [])
        customer_info = input_data.get("customer_info", {})
        
        if not supplier_id or not parts:
            return {"success": False, "error": "supplier_id and parts are required"}
        
        # Get supplier details
        supplier = await self.supplier_service.get_supplier(supplier_id)
        
        if not supplier:
            return {"success": False, "error": "Supplier not found"}
        
        # Check if supplier supports automated ordering
        if not supplier.get("supports_automated_ordering", False):
            return {
                "success": False,
                "error": "Supplier does not support automated ordering",
                "manual_order_required": True,
                "supplier_contact": supplier.get("contact_info", {})
            }
        
        # Place order with supplier
        order_result = await self.scraping_service.place_supplier_order(
            supplier_id=supplier_id,
            parts=parts,
            customer_info=customer_info
        )
        
        if order_result["success"]:
            # Record the order
            await self.supplier_service.record_supplier_order(
                supplier_id=supplier_id,
                order_data=order_result["order"],
                parts=parts
            )
        
        return order_result
    
    async def _update_supplier_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update supplier catalog and pricing data."""
        supplier_id = input_data.get("supplier_id")
        update_type = input_data.get("update_type", "full")  # "full", "pricing", "availability"
        
        if not supplier_id:
            return {"success": False, "error": "supplier_id is required"}
        
        # Update supplier data
        update_result = await self.scraping_service.update_supplier_data(
            supplier_id=supplier_id,
            update_type=update_type
        )
        
        if update_result["success"]:
            # Update supplier last_updated timestamp
            await self.supplier_service.update_supplier_timestamp(
                supplier_id=supplier_id,
                last_updated=update_result.get("updated_at")
            )
        
        return update_result
    
    async def _scrape_supplier_catalog(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrape supplier catalog for new parts."""
        supplier_id = input_data.get("supplier_id")
        category = input_data.get("category")
        limit = input_data.get("limit", 1000)
        
        if not supplier_id:
            return {"success": False, "error": "supplier_id is required"}
        
        # Scrape catalog
        scrape_result = await self.scraping_service.scrape_supplier_catalog(
            supplier_id=supplier_id,
            category=category,
            limit=limit
        )
        
        if scrape_result["success"]:
            # Save scraped parts to database
            await self.supplier_service.save_scraped_parts(
                supplier_id=supplier_id,
                parts=scrape_result["parts"]
            )
        
        return scrape_result
    
    async def _general_sourcing_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general parts sourcing workflow."""
        return {
            "message": "General parts sourcing workflow processed",
            "input_data": input_data
        }
    
    def _generate_sourcing_recommendations(self, comparison_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sourcing recommendations based on comparison results."""
        recommendations = []
        
        if not comparison_result.get("parts"):
            return recommendations
        
        parts = comparison_result["parts"]
        
        # Best price recommendation
        cheapest = min(parts, key=lambda x: x.get("price", float('inf'))) if parts else None
        if cheapest:
            recommendations.append({
                "type": "best_price",
                "title": "Best Price Option",
                "supplier": cheapest.get("supplier_name"),
                "price": cheapest.get("price"),
                "availability": cheapest.get("availability"),
                "delivery_time": cheapest.get("delivery_time"),
                "reason": "Lowest cost option"
            })
        
        # Fastest delivery recommendation
        fastest = min(parts, key=lambda x: x.get("delivery_days", float('inf'))) if parts else None
        if fastest and fastest != cheapest:
            recommendations.append({
                "type": "fastest_delivery",
                "title": "Fastest Delivery",
                "supplier": fastest.get("supplier_name"),
                "price": fastest.get("price"),
                "availability": fastest.get("availability"),
                "delivery_time": fastest.get("delivery_time"),
                "reason": "Quickest delivery option"
            })
        
        # Most reliable supplier recommendation
        reliable = max(parts, key=lambda x: x.get("supplier_rating", 0)) if parts else None
        if reliable and reliable != cheapest and reliable != fastest:
            recommendations.append({
                "type": "most_reliable",
                "title": "Most Reliable Supplier",
                "supplier": reliable.get("supplier_name"),
                "price": reliable.get("price"),
                "availability": reliable.get("availability"),
                "delivery_time": reliable.get("delivery_time"),
                "supplier_rating": reliable.get("supplier_rating"),
                "reason": "Highest rated supplier"
            })
        
        return recommendations
    
    def _select_best_option(self, comparison_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select the best sourcing option based on multiple factors."""
        parts = comparison_result.get("parts", [])
        
        if not parts:
            return None
        
        # Score each option (lower score = better)
        scored_parts = []
        
        for part in parts:
            score = 0
            
            # Price factor (40% weight)
            price_score = (part.get("price", 0) / max(p.get("price", 1) for p in parts)) * 40
            score += price_score
            
            # Delivery time factor (30% weight)
            delivery_score = (part.get("delivery_days", 7) / 7) * 30
            score += delivery_score
            
            # Availability factor (20% weight)
            availability = part.get("availability", "in_stock")
            if availability == "in_stock":
                availability_score = 0
            elif availability == "limited":
                availability_score = 10
            else:
                availability_score = 20
            score += availability_score
            
            # Supplier rating factor (10% weight)
            rating = part.get("supplier_rating", 3)
            rating_score = ((5 - rating) / 5) * 10
            score += rating_score
            
            scored_parts.append({**part, "score": score})
        
        # Return the part with the lowest score
        return min(scored_parts, key=lambda x: x["score"]) if scored_parts else None
    
    def _generate_price_insights(self, comparison_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate price comparison insights."""
        insights = []
        
        parts = comparison_result.get("parts", [])
        if len(parts) < 2:
            return insights
        
        prices = [part.get("price", 0) for part in parts if part.get("price")]
        
        if not prices:
            return insights
        
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Price range insight
        if max_price - min_price > avg_price * 0.2:  # More than 20% variation
            insights.append({
                "type": "price_variation",
                "title": "High Price Variation",
                "message": f"Prices range from ${min_price:.2f} to ${max_price:.2f} (${max_price - min_price:.2f} difference)",
                "recommendation": "Compare supplier terms and delivery options"
            })
        
        # Best value insight
        best_value = min(parts, key=lambda x: x.get("price", float('inf')))
        if best_value:
            insights.append({
                "type": "best_value",
                "title": "Best Value Option",
                "message": f"{best_value.get('supplier_name')} offers the lowest price at ${best_value.get('price'):.2f}",
                "recommendation": "Consider this option for cost optimization"
            })
        
        return insights
    
    def _generate_price_recommendations(self, comparison_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate price-based recommendations."""
        recommendations = []
        
        parts = comparison_result.get("parts", [])
        if not parts:
            return recommendations
        
        # Group by price ranges
        low_price_parts = [p for p in parts if p.get("price", 0) < sum(p.get("price", 0) for p in parts) / len(parts) * 0.8]
        high_price_parts = [p for p in parts if p.get("price", 0) > sum(p.get("price", 0) for p in parts) / len(parts) * 1.2]
        
        if low_price_parts:
            recommendations.append({
                "type": "budget_option",
                "title": "Budget-Friendly Options",
                "suppliers": [p.get("supplier_name") for p in low_price_parts],
                "price_range": f"${min(p.get('price', 0) for p in low_price_parts):.2f} - ${max(p.get('price', 0) for p in low_price_parts):.2f}",
                "reason": "Lower cost options available"
            })
        
        if high_price_parts:
            recommendations.append({
                "type": "premium_option",
                "title": "Premium Options",
                "suppliers": [p.get("supplier_name") for p in high_price_parts],
                "price_range": f"${min(p.get('price', 0) for p in high_price_parts):.2f} - ${max(p.get('price', 0) for p in high_price_parts):.2f}",
                "reason": "Higher-end suppliers with premium service"
            })
        
        return recommendations
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for supplier sourcing agent."""
        return """
You are a specialized Supplier Sourcing Agent for a dealership parts management system.

Your responsibilities:
1. Find parts from external suppliers when not available in-house
2. Compare prices across multiple suppliers (Rock Auto, AutoZone, O'Reilly's, etc.)
3. Check real-time availability and delivery times
4. Place orders with suppliers when automated ordering is available
5. Maintain supplier catalog data through web scraping
6. Provide sourcing recommendations based on price, speed, and reliability

Key Suppliers:
- Rock Auto: Wide selection, competitive pricing, good availability
- AutoZone: Fast delivery, extensive network, premium pricing
- O'Reilly's: Good service, moderate pricing, reliable delivery
- NAPA: Premium parts, higher pricing, excellent quality
- CarParts.com: Online focus, competitive pricing, good selection

Sourcing Criteria:
- Price competitiveness (40% weight)
- Delivery speed (30% weight)
- Availability (20% weight)
- Supplier reliability (10% weight)

Always provide multiple options with clear recommendations and reasoning for the best choice.
"""
