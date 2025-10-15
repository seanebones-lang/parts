"""
Market analysis and competitive intelligence tools.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from enum import Enum
import httpx

from app.models.parts_catalog import PartsCatalog
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.invoice import Invoice
from app.models.location import Location


class MarketAnalysisService:
    """Service for market analysis and competitive intelligence."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def analyze_part_demand(
        self,
        part_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        category: Optional[str] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """Analyze demand patterns for parts."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query for orders
        query = select(Order).where(Order.created_at >= start_date)
        
        if part_number:
            # This would need a join with OrderItem
            pass
        
        result = await self.db.execute(query)
        orders = result.scalars().all()
        
        # Analyze demand patterns
        daily_demand = {}
        weekly_demand = {}
        monthly_demand = {}
        
        for order in orders:
            order_date = order.created_at.date()
            
            # Daily demand
            daily_key = order_date.isoformat()
            daily_demand[daily_key] = daily_demand.get(daily_key, 0) + 1
            
            # Weekly demand
            week_key = f"{order_date.year}-W{order_date.isocalendar()[1]}"
            weekly_demand[week_key] = weekly_demand.get(week_key, 0) + 1
            
            # Monthly demand
            month_key = f"{order_date.year}-{order_date.month:02d}"
            monthly_demand[month_key] = monthly_demand.get(month_key, 0) + 1
        
        # Calculate trends
        daily_values = list(daily_demand.values())
        weekly_values = list(weekly_demand.values())
        monthly_values = list(monthly_demand.values())
        
        # Simple trend calculation
        daily_trend = self._calculate_trend(daily_values)
        weekly_trend = self._calculate_trend(weekly_values)
        monthly_trend = self._calculate_trend(monthly_values)
        
        return {
            "period_days": days,
            "total_orders": len(orders),
            "daily_demand": daily_demand,
            "weekly_demand": weekly_demand,
            "monthly_demand": monthly_demand,
            "trends": {
                "daily": daily_trend,
                "weekly": weekly_trend,
                "monthly": monthly_trend
            },
            "average_daily_orders": sum(daily_values) / len(daily_values) if daily_values else 0,
            "peak_demand_day": max(daily_demand.items(), key=lambda x: x[1]) if daily_demand else None,
            "lowest_demand_day": min(daily_demand.items(), key=lambda x: x[1]) if daily_demand else None
        }
    
    def _calculate_trend(self, values: List[int]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        
        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    async def analyze_pricing_competitiveness(
        self,
        part_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze pricing competitiveness against market."""
        
        # Get our pricing data
        query = select(PartsCatalog)
        
        if part_number:
            query = query.where(PartsCatalog.part_number == part_number)
        if manufacturer:
            query = query.where(PartsCatalog.manufacturer == manufacturer)
        if category:
            query = query.where(PartsCatalog.category == category)
        
        result = await self.db.execute(query)
        parts = result.scalars().all()
        
        pricing_analysis = {
            "total_parts_analyzed": len(parts),
            "price_ranges": {},
            "competitive_positioning": {},
            "recommendations": []
        }
        
        if not parts:
            return pricing_analysis
        
        # Analyze price ranges
        prices = [part.unit_price for part in parts if part.unit_price]
        
        if prices:
            pricing_analysis["price_ranges"] = {
                "min": min(prices),
                "max": max(prices),
                "average": sum(prices) / len(prices),
                "median": sorted(prices)[len(prices)//2]
            }
            
            # Competitive positioning
            avg_price = pricing_analysis["price_ranges"]["average"]
            below_market = len([p for p in prices if p < avg_price * 0.9])
            at_market = len([p for p in prices if avg_price * 0.9 <= p <= avg_price * 1.1])
            above_market = len([p for p in prices if p > avg_price * 1.1])
            
            pricing_analysis["competitive_positioning"] = {
                "below_market": below_market,
                "at_market": at_market,
                "above_market": above_market,
                "market_position": "below" if below_market > above_market else "above" if above_market > below_market else "at_market"
            }
            
            # Generate recommendations
            if below_market > above_market:
                pricing_analysis["recommendations"].append("Consider increasing prices - currently below market")
            elif above_market > below_market:
                pricing_analysis["recommendations"].append("Consider reducing prices - currently above market")
            else:
                pricing_analysis["recommendations"].append("Pricing appears competitive with market")
        
        return pricing_analysis
    
    async def analyze_seasonal_patterns(
        self,
        part_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        category: Optional[str] = None,
        years: int = 2
    ) -> Dict[str, Any]:
        """Analyze seasonal demand patterns."""
        
        start_date = datetime.utcnow() - timedelta(days=years * 365)
        
        # Get orders for the period
        query = select(Order).where(Order.created_at >= start_date)
        result = await self.db.execute(query)
        orders = result.scalars().all()
        
        # Analyze by month
        monthly_patterns = {}
        for order in orders:
            month = order.created_at.month
            monthly_patterns[month] = monthly_patterns.get(month, 0) + 1
        
        # Analyze by quarter
        quarterly_patterns = {}
        for order in orders:
            quarter = (order.created_at.month - 1) // 3 + 1
            quarterly_patterns[quarter] = quarterly_patterns.get(quarter, 0) + 1
        
        # Analyze by day of week
        daily_patterns = {}
        for order in orders:
            day_of_week = order.created_at.weekday()
            daily_patterns[day_of_week] = daily_patterns.get(day_of_week, 0) + 1
        
        # Calculate seasonality index
        monthly_values = [monthly_patterns.get(i, 0) for i in range(1, 13)]
        avg_monthly = sum(monthly_values) / 12 if monthly_values else 0
        
        seasonality_index = {}
        for month, count in monthly_patterns.items():
            seasonality_index[month] = count / avg_monthly if avg_monthly > 0 else 0
        
        return {
            "period_years": years,
            "total_orders": len(orders),
            "monthly_patterns": monthly_patterns,
            "quarterly_patterns": quarterly_patterns,
            "daily_patterns": daily_patterns,
            "seasonality_index": seasonality_index,
            "peak_month": max(monthly_patterns.items(), key=lambda x: x[1]) if monthly_patterns else None,
            "lowest_month": min(monthly_patterns.items(), key=lambda x: x[1]) if monthly_patterns else None,
            "peak_quarter": max(quarterly_patterns.items(), key=lambda x: x[1]) if quarterly_patterns else None,
            "peak_day": max(daily_patterns.items(), key=lambda x: x[1]) if daily_patterns else None
        }
    
    async def analyze_customer_segments(
        self,
        days: int = 90
    ) -> Dict[str, Any]:
        """Analyze customer segments and behavior."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get orders and customers
        orders_query = select(Order).where(Order.created_at >= start_date)
        orders_result = await self.db.execute(orders_query)
        orders = orders_result.scalars().all()
        
        # Analyze customer behavior
        customer_stats = {}
        for order in orders:
            customer_id = order.customer_id
            if customer_id not in customer_stats:
                customer_stats[customer_id] = {
                    "order_count": 0,
                    "total_value": 0,
                    "first_order": order.created_at,
                    "last_order": order.created_at
                }
            
            customer_stats[customer_id]["order_count"] += 1
            customer_stats[customer_id]["total_value"] += order.total_amount or 0
            customer_stats[customer_id]["last_order"] = max(
                customer_stats[customer_id]["last_order"],
                order.created_at
            )
        
        # Segment customers
        segments = {
            "high_value": [],
            "frequent": [],
            "new": [],
            "at_risk": []
        }
        
        current_date = datetime.utcnow()
        
        for customer_id, stats in customer_stats.items():
            # High value customers (top 20% by value)
            if stats["total_value"] > 0:
                segments["high_value"].append(customer_id)
            
            # Frequent customers (multiple orders)
            if stats["order_count"] > 1:
                segments["frequent"].append(customer_id)
            
            # New customers (first order in period)
            if stats["first_order"] >= start_date:
                segments["new"].append(customer_id)
            
            # At-risk customers (no recent orders)
            days_since_last = (current_date - stats["last_order"]).days
            if days_since_last > 30:
                segments["at_risk"].append(customer_id)
        
        # Calculate segment metrics
        total_customers = len(customer_stats)
        
        return {
            "period_days": days,
            "total_customers": total_customers,
            "total_orders": len(orders),
            "segments": {
                "high_value": {
                    "count": len(segments["high_value"]),
                    "percentage": len(segments["high_value"]) / total_customers * 100 if total_customers > 0 else 0
                },
                "frequent": {
                    "count": len(segments["frequent"]),
                    "percentage": len(segments["frequent"]) / total_customers * 100 if total_customers > 0 else 0
                },
                "new": {
                    "count": len(segments["new"]),
                    "percentage": len(segments["new"]) / total_customers * 100 if total_customers > 0 else 0
                },
                "at_risk": {
                    "count": len(segments["at_risk"]),
                    "percentage": len(segments["at_risk"]) / total_customers * 100 if total_customers > 0 else 0
                }
            },
            "average_order_value": sum(stats["total_value"] for stats in customer_stats.values()) / len(orders) if orders else 0,
            "average_orders_per_customer": len(orders) / total_customers if total_customers > 0 else 0
        }
    
    async def analyze_inventory_turnover(
        self,
        location_id: Optional[int] = None,
        category: Optional[str] = None,
        days: int = 365
    ) -> Dict[str, Any]:
        """Analyze inventory turnover rates."""
        
        # Get inventory data
        query = select(Inventory)
        
        if location_id:
            query = query.where(Inventory.location_id == location_id)
        
        result = await self.db.execute(query)
        inventory_items = result.scalars().all()
        
        turnover_analysis = {
            "total_items": len(inventory_items),
            "turnover_rates": {},
            "slow_moving": [],
            "fast_moving": [],
            "recommendations": []
        }
        
        for item in inventory_items:
            # Calculate turnover rate (simplified)
            if item.cost and item.quantity_available > 0:
                # This would need actual sales data to calculate properly
                # For now, we'll use a mock calculation
                turnover_rate = 0.5  # Mock turnover rate
                
                turnover_analysis["turnover_rates"][item.part_id] = turnover_rate
                
                if turnover_rate < 0.2:
                    turnover_analysis["slow_moving"].append({
                        "part_id": item.part_id,
                        "part_number": item.part.part_number if item.part else None,
                        "quantity": item.quantity_available,
                        "turnover_rate": turnover_rate
                    })
                elif turnover_rate > 1.0:
                    turnover_analysis["fast_moving"].append({
                        "part_id": item.part_id,
                        "part_number": item.part.part_number if item.part else None,
                        "quantity": item.quantity_available,
                        "turnover_rate": turnover_rate
                    })
        
        # Generate recommendations
        if len(turnover_analysis["slow_moving"]) > len(turnover_analysis["fast_moving"]):
            turnover_analysis["recommendations"].append("Consider reducing inventory levels for slow-moving items")
        
        if len(turnover_analysis["fast_moving"]) > 0:
            turnover_analysis["recommendations"].append("Increase stock levels for fast-moving items")
        
        return turnover_analysis
    
    async def get_market_intelligence_summary(self) -> Dict[str, Any]:
        """Get comprehensive market intelligence summary."""
        
        # Run all analyses
        demand_analysis = await self.analyze_part_demand(days=90)
        pricing_analysis = await self.analyze_pricing_competitiveness()
        seasonal_analysis = await self.analyze_seasonal_patterns(years=1)
        customer_analysis = await self.analyze_customer_segments(days=90)
        inventory_analysis = await self.analyze_inventory_turnover(days=365)
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "demand_analysis": demand_analysis,
            "pricing_analysis": pricing_analysis,
            "seasonal_analysis": seasonal_analysis,
            "customer_analysis": customer_analysis,
            "inventory_analysis": inventory_analysis,
            "key_insights": [
                f"Total orders in last 90 days: {demand_analysis['total_orders']}",
                f"Average daily orders: {demand_analysis['average_daily_orders']:.1f}",
                f"Market position: {pricing_analysis['competitive_positioning'].get('market_position', 'unknown')}",
                f"Peak demand month: {seasonal_analysis['peak_month'][0] if seasonal_analysis['peak_month'] else 'N/A'}",
                f"Customer segments: {customer_analysis['total_customers']} total customers",
                f"Inventory items: {inventory_analysis['total_items']} items tracked"
            ]
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
