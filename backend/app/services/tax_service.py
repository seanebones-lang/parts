"""
Tax service for calculating taxes by location.
"""

from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.location import Location


class TaxService:
    """Service for tax calculations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Tax rates by state (simplified)
        self.state_tax_rates = {
            "CA": 0.0875,  # 8.75% California
            "NY": 0.08,    # 8% New York
            "TX": 0.0825,  # 8.25% Texas
            "FL": 0.06,    # 6% Florida
            "WA": 0.065,   # 6.5% Washington
            "OR": 0.0,     # 0% Oregon (no sales tax)
            "MT": 0.0,     # 0% Montana (no sales tax)
            "NH": 0.0,     # 0% New Hampshire (no sales tax)
            "DE": 0.0,     # 0% Delaware (no sales tax)
        }
        
        # Category-specific tax exemptions
        self.tax_exempt_categories = [
            "food",
            "prescription_drugs",
            "medical_equipment"
        ]
    
    async def calculate_taxes(
        self,
        location_id: int,
        subtotal: Decimal,
        items: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate taxes for an order."""
        try:
            # Get location information
            location_query = select(Location).where(Location.id == location_id)
            location_result = await self.db.execute(location_query)
            location = location_result.scalar_one_or_none()
            
            if not location:
                return {
                    "total_tax": Decimal('0.00'),
                    "breakdown": [],
                    "error": "Location not found"
                }
            
            state = location.state
            tax_rate = self.state_tax_rates.get(state, 0.07)  # Default 7% if state not found
            
            # Calculate tax for each item if provided
            tax_breakdown = []
            total_tax = Decimal('0.00')
            
            if items:
                for item in items:
                    item_tax = await self._calculate_item_tax(item, tax_rate, state)
                    tax_breakdown.append({
                        "part_id": item.get("part_id"),
                        "part_name": item.get("part_name"),
                        "line_total": float(item.get("line_total", 0)),
                        "tax_rate": float(tax_rate),
                        "tax_amount": float(item_tax),
                        "category": item.get("category", "general")
                    })
                    total_tax += item_tax
            else:
                # Calculate tax on total
                total_tax = subtotal * Decimal(str(tax_rate))
                tax_breakdown.append({
                    "description": "Sales Tax",
                    "subtotal": float(subtotal),
                    "tax_rate": float(tax_rate),
                    "tax_amount": float(total_tax)
                })
            
            return {
                "total_tax": total_tax,
                "tax_rate": tax_rate,
                "state": state,
                "location_name": location.name,
                "breakdown": tax_breakdown
            }
            
        except Exception as e:
            print(f"Error calculating taxes: {e}")
            return {
                "total_tax": Decimal('0.00'),
                "breakdown": [],
                "error": str(e)
            }
    
    async def calculate_tax_by_address(
        self,
        address: Dict[str, str],
        subtotal: Decimal,
        items: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate taxes based on shipping address."""
        try:
            state = address.get("state", "").upper()
            tax_rate = self.state_tax_rates.get(state, 0.07)
            
            # Calculate tax for each item if provided
            tax_breakdown = []
            total_tax = Decimal('0.00')
            
            if items:
                for item in items:
                    item_tax = await self._calculate_item_tax(item, tax_rate, state)
                    tax_breakdown.append({
                        "part_id": item.get("part_id"),
                        "part_name": item.get("part_name"),
                        "line_total": float(item.get("line_total", 0)),
                        "tax_rate": float(tax_rate),
                        "tax_amount": float(item_tax),
                        "category": item.get("category", "general")
                    })
                    total_tax += item_tax
            else:
                total_tax = subtotal * Decimal(str(tax_rate))
                tax_breakdown.append({
                    "description": "Sales Tax",
                    "subtotal": float(subtotal),
                    "tax_rate": float(tax_rate),
                    "tax_amount": float(total_tax)
                })
            
            return {
                "total_tax": total_tax,
                "tax_rate": tax_rate,
                "state": state,
                "breakdown": tax_breakdown
            }
            
        except Exception as e:
            print(f"Error calculating taxes by address: {e}")
            return {
                "total_tax": Decimal('0.00'),
                "breakdown": [],
                "error": str(e)
            }
    
    async def get_tax_rates_by_location(self, location_id: int) -> Dict[str, Any]:
        """Get tax rates for a specific location."""
        try:
            location_query = select(Location).where(Location.id == location_id)
            location_result = await self.db.execute(location_query)
            location = location_result.scalar_one_or_none()
            
            if not location:
                return {
                    "error": "Location not found"
                }
            
            state = location.state
            tax_rate = self.state_tax_rates.get(state, 0.07)
            
            return {
                "location_id": location_id,
                "location_name": location.name,
                "state": state,
                "tax_rate": tax_rate,
                "tax_rate_percent": tax_rate * 100,
                "exempt_categories": self.tax_exempt_categories
            }
            
        except Exception as e:
            return {
                "error": str(e)
            }
    
    async def validate_tax_exemption(
        self,
        customer_id: int,
        exemption_type: str
    ) -> Dict[str, Any]:
        """Validate tax exemption for customer."""
        try:
            # This would check customer exemption status in database
            # For now, return mock validation
            
            valid_exemptions = ["resale", "government", "nonprofit", "educational"]
            
            if exemption_type in valid_exemptions:
                return {
                    "valid": True,
                    "exemption_type": exemption_type,
                    "exemption_percent": 100.0,
                    "expires_at": "2024-12-31"
                }
            else:
                return {
                    "valid": False,
                    "error": "Invalid exemption type"
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _calculate_item_tax(
        self,
        item: Dict[str, Any],
        tax_rate: float,
        state: str
    ) -> Decimal:
        """Calculate tax for a specific item."""
        line_total = Decimal(str(item.get("line_total", 0)))
        category = item.get("category", "general")
        
        # Check if item is tax exempt
        if category.lower() in self.tax_exempt_categories:
            return Decimal('0.00')
        
        # Apply tax rate
        tax_amount = line_total * Decimal(str(tax_rate))
        
        return tax_amount
    
    async def get_tax_summary_by_state(self) -> Dict[str, Any]:
        """Get tax summary for all states."""
        return {
            "tax_rates": self.state_tax_rates,
            "exempt_categories": self.tax_exempt_categories,
            "last_updated": "2024-01-01"
        }
