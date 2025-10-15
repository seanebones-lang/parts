"""
Price comparison service for supplier parts.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession


class PriceComparisonService:
    """Service for comparing prices across suppliers."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def compare_parts(
        self,
        supplier_results: List[Dict[str, Any]],
        part_number: Optional[str] = None,
        part_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compare parts across multiple suppliers."""
        try:
            # Flatten all parts from all suppliers
            all_parts = []
            
            for supplier_result in supplier_results:
                supplier = supplier_result.get("supplier", {})
                parts = supplier_result.get("parts", [])
                
                for part in parts:
                    # Add supplier information to each part
                    part_with_supplier = {
                        **part,
                        "supplier_id": supplier.get("id"),
                        "supplier_name": supplier.get("name"),
                        "supplier_rating": supplier.get("rating", 3.0),
                        "supplier_delivery_time": supplier.get("delivery_time_days", 5),
                        "search_confidence": supplier_result.get("confidence", 0.8)
                    }
                    all_parts.append(part_with_supplier)
            
            if not all_parts:
                return {
                    "success": True,
                    "parts": [],
                    "comparison_summary": {
                        "total_options": 0,
                        "price_range": {"min": 0, "max": 0, "avg": 0},
                        "availability_summary": {},
                        "delivery_summary": {"min": 0, "max": 0, "avg": 0}
                    }
                }
            
            # Sort parts by price
            sorted_parts = sorted(
                [part for part in all_parts if part.get("price")], 
                key=lambda x: x.get("price", float('inf'))
            )
            
            # Generate comparison summary
            comparison_summary = self._generate_comparison_summary(sorted_parts)
            
            # Add comparison rankings
            for i, part in enumerate(sorted_parts):
                part["price_rank"] = i + 1
                part["value_score"] = self._calculate_value_score(part)
            
            return {
                "success": True,
                "parts": sorted_parts,
                "comparison_summary": comparison_summary,
                "best_options": self._get_best_options(sorted_parts)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_comparison_summary(self, parts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for the comparison."""
        if not parts:
            return {
                "total_options": 0,
                "price_range": {"min": 0, "max": 0, "avg": 0},
                "availability_summary": {},
                "delivery_summary": {"min": 0, "max": 0, "avg": 0}
            }
        
        # Price statistics
        prices = [part.get("price", 0) for part in parts if part.get("price")]
        price_min = min(prices) if prices else 0
        price_max = max(prices) if prices else 0
        price_avg = sum(prices) / len(prices) if prices else 0
        
        # Availability summary
        availability_counts = {}
        for part in parts:
            availability = part.get("availability", "unknown")
            availability_counts[availability] = availability_counts.get(availability, 0) + 1
        
        # Delivery statistics
        delivery_times = [part.get("delivery_days", 5) for part in parts]
        delivery_min = min(delivery_times) if delivery_times else 0
        delivery_max = max(delivery_times) if delivery_times else 0
        delivery_avg = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        return {
            "total_options": len(parts),
            "price_range": {
                "min": price_min,
                "max": price_max,
                "avg": price_avg,
                "range": price_max - price_min
            },
            "availability_summary": availability_counts,
            "delivery_summary": {
                "min": delivery_min,
                "max": delivery_max,
                "avg": delivery_avg
            }
        }
    
    def _calculate_value_score(self, part: Dict[str, Any]) -> float:
        """Calculate value score for a part (lower is better)."""
        try:
            price = part.get("price", 0)
            delivery_days = part.get("delivery_days", 5)
            supplier_rating = part.get("supplier_rating", 3.0)
            availability = part.get("availability", "unknown")
            
            # Base score from price (normalized)
            price_score = price / 100  # Assume $100 as reference price
            
            # Delivery penalty
            delivery_penalty = delivery_days * 0.1
            
            # Supplier rating bonus (lower rating = higher penalty)
            rating_penalty = (5 - supplier_rating) * 0.2
            
            # Availability bonus/penalty
            availability_bonus = 0
            if availability == "in_stock":
                availability_bonus = -0.1  # Bonus for in stock
            elif availability == "out_of_stock":
                availability_bonus = 0.5   # Penalty for out of stock
            elif availability == "limited":
                availability_bonus = 0.2   # Small penalty for limited
            
            # Calculate final score
            value_score = price_score + delivery_penalty + rating_penalty + availability_bonus
            
            return max(0, value_score)  # Ensure non-negative
            
        except Exception as e:
            print(f"Error calculating value score: {e}")
            return 1.0  # Default penalty score
    
    def _get_best_options(self, parts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get the best options in different categories."""
        if not parts:
            return {}
        
        best_options = {}
        
        # Best price
        cheapest_part = min(parts, key=lambda x: x.get("price", float('inf')))
        best_options["best_price"] = {
            "supplier": cheapest_part.get("supplier_name"),
            "price": cheapest_part.get("price"),
            "delivery_days": cheapest_part.get("delivery_days"),
            "availability": cheapest_part.get("availability")
        }
        
        # Fastest delivery
        fastest_part = min(parts, key=lambda x: x.get("delivery_days", float('inf')))
        if fastest_part != cheapest_part:
            best_options["fastest_delivery"] = {
                "supplier": fastest_part.get("supplier_name"),
                "price": fastest_part.get("price"),
                "delivery_days": fastest_part.get("delivery_days"),
                "availability": fastest_part.get("availability")
            }
        
        # Best value (lowest value score)
        best_value_part = min(parts, key=lambda x: x.get("value_score", float('inf')))
        if best_value_part != cheapest_part and best_value_part != fastest_part:
            best_options["best_value"] = {
                "supplier": best_value_part.get("supplier_name"),
                "price": best_value_part.get("price"),
                "delivery_days": best_value_part.get("delivery_days"),
                "availability": best_value_part.get("availability"),
                "value_score": best_value_part.get("value_score")
            }
        
        # Most reliable (highest supplier rating)
        most_reliable_part = max(parts, key=lambda x: x.get("supplier_rating", 0))
        if (most_reliable_part != cheapest_part and 
            most_reliable_part != fastest_part and 
            most_reliable_part != best_value_part):
            best_options["most_reliable"] = {
                "supplier": most_reliable_part.get("supplier_name"),
                "price": most_reliable_part.get("price"),
                "delivery_days": most_reliable_part.get("delivery_days"),
                "availability": most_reliable_part.get("availability"),
                "supplier_rating": most_reliable_part.get("supplier_rating")
            }
        
        return best_options
    
    async def generate_price_alert(
        self,
        part_number: str,
        target_price: float,
        current_best_price: float
    ) -> Dict[str, Any]:
        """Generate price alert if significant price change detected."""
        try:
            price_change_percent = ((current_best_price - target_price) / target_price) * 100
            
            alert_level = "info"
            if price_change_percent > 20:
                alert_level = "warning"
            elif price_change_percent < -20:
                alert_level = "success"
            
            return {
                "success": True,
                "alert": {
                    "part_number": part_number,
                    "target_price": target_price,
                    "current_best_price": current_best_price,
                    "price_change_percent": price_change_percent,
                    "alert_level": alert_level,
                    "message": self._generate_alert_message(price_change_percent, alert_level),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_alert_message(self, price_change_percent: float, alert_level: str) -> str:
        """Generate human-readable alert message."""
        if alert_level == "success":
            return f"Great news! Prices have dropped by {abs(price_change_percent):.1f}%"
        elif alert_level == "warning":
            return f"Warning: Prices have increased by {price_change_percent:.1f}%"
        else:
            return f"Price change of {price_change_percent:.1f}% detected"
    
    async def track_price_history(
        self,
        part_number: str,
        supplier_id: int,
        price: float
    ) -> Dict[str, Any]:
        """Track price history for trend analysis."""
        try:
            # This would store price history in database
            # For now, return success status
            return {
                "success": True,
                "message": f"Price history tracked for part {part_number} from supplier {supplier_id}",
                "price": price,
                "tracked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_price_trends(
        self,
        part_number: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get price trends for a part over time."""
        try:
            # This would query price history from database
            # For now, return mock trend data
            return {
                "success": True,
                "part_number": part_number,
                "trend_period_days": days,
                "trend": "stable",  # "increasing", "decreasing", "stable", "volatile"
                "average_price": 45.50,
                "price_range": {"min": 42.00, "max": 48.75},
                "recommendation": "Prices are stable, good time to order"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def find_price_anomalies(
        self,
        parts_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find price anomalies in supplier data."""
        try:
            anomalies = []
            
            if len(parts_data) < 3:
                return anomalies
            
            # Calculate price statistics
            prices = [part.get("price", 0) for part in parts_data if part.get("price")]
            if not prices:
                return anomalies
            
            avg_price = sum(prices) / len(prices)
            price_std = (sum((p - avg_price) ** 2 for p in prices) / len(prices)) ** 0.5
            
            # Find outliers (more than 2 standard deviations from mean)
            for part in parts_data:
                price = part.get("price", 0)
                if price > 0:
                    z_score = abs(price - avg_price) / price_std if price_std > 0 else 0
                    
                    if z_score > 2:  # Statistical outlier
                        anomalies.append({
                            "part": part,
                            "price": price,
                            "average_price": avg_price,
                            "z_score": z_score,
                            "anomaly_type": "high" if price > avg_price else "low",
                            "deviation_percent": ((price - avg_price) / avg_price) * 100
                        })
            
            return anomalies
            
        except Exception as e:
            print(f"Error finding price anomalies: {e}")
            return []
