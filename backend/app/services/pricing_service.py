"""
Pricing service for calculating part prices and discounts.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.parts_catalog import PartsCatalog
from app.models.inventory import Inventory
from app.models.customer import Customer


class PricingService:
    """Service for managing pricing calculations and discounts."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_part_pricing(
        self,
        part_id: int,
        location_id: int,
        customer_type: str = "retail",
        quantity: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Get pricing for a specific part."""
        try:
            # Get part details
            part_query = select(PartsCatalog).where(PartsCatalog.id == part_id)
            part_result = await self.db.execute(part_query)
            part = part_result.scalar_one_or_none()
            
            if not part:
                return None
            
            # Get inventory for pricing
            inventory_query = select(Inventory).where(
                and_(
                    Inventory.part_id == part_id,
                    Inventory.location_id == location_id
                )
            )
            inventory_result = await self.db.execute(inventory_query)
            inventory = inventory_result.scalar_one_or_none()
            
            # Calculate base price
            base_price = self._calculate_base_price(part, inventory, customer_type)
            
            # Get availability
            availability = await self._get_availability_info(part_id, location_id)
            
            return {
                "part_id": part_id,
                "part_number": part.part_number,
                "part_name": part.part_name,
                "category": part.category,
                "manufacturer": part.manufacturer,
                "unit_price": base_price,
                "msrp": float(part.msrp) if part.msrp else None,
                "cost": float(inventory.cost) if inventory and inventory.cost else None,
                "margin_percent": self._calculate_margin_percent(base_price, inventory.cost if inventory else None),
                "availability": availability,
                "quantity_available": inventory.quantity_available if inventory else 0
            }
            
        except Exception as e:
            print(f"Error getting part pricing: {e}")
            return None
    
    async def get_customer_tier_discount(
        self,
        customer_tier: str,
        part_category: str
    ) -> float:
        """Get customer tier discount percentage."""
        # Define tier discounts
        tier_discounts = {
            "platinum": 15.0,  # 15% discount for platinum customers
            "gold": 10.0,      # 10% discount for gold customers
            "silver": 5.0,     # 5% discount for silver customers
            "standard": 0.0    # No discount for standard customers
        }
        
        # Category-specific adjustments
        category_adjustments = {
            "brakes": 0.0,     # No additional discount for brakes
            "engine": 2.0,     # 2% additional for engine parts
            "tires": 5.0,      # 5% additional for tires
            "electrical": 3.0  # 3% additional for electrical
        }
        
        base_discount = tier_discounts.get(customer_tier, 0.0)
        category_adjustment = category_adjustments.get(part_category, 0.0)
        
        return base_discount + category_adjustment
    
    async def get_quantity_discount(
        self,
        part_id: int,
        quantity: int
    ) -> float:
        """Get quantity discount percentage."""
        # Quantity discount tiers
        if quantity >= 50:
            return 15.0  # 15% discount for 50+ pieces
        elif quantity >= 20:
            return 10.0  # 10% discount for 20+ pieces
        elif quantity >= 10:
            return 5.0   # 5% discount for 10+ pieces
        elif quantity >= 5:
            return 2.0   # 2% discount for 5+ pieces
        else:
            return 0.0   # No discount for less than 5 pieces
    
    async def validate_discount_code(
        self,
        discount_code: str,
        customer_id: int,
        location_id: int,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate discount code and return discount info."""
        # Mock discount codes (in production, these would be in database)
        valid_codes = {
            "SAVE10": {
                "discount_percent": 10.0,
                "applies_to": "all",
                "min_amount": 100.0,
                "max_discount": 50.0,
                "valid_until": "2024-12-31",
                "usage_limit": 1
            },
            "BRAKE20": {
                "discount_percent": 20.0,
                "applies_to": "category",
                "category": "brakes",
                "min_amount": 50.0,
                "max_discount": 100.0,
                "valid_until": "2024-12-31",
                "usage_limit": 1
            },
            "BULK15": {
                "discount_percent": 15.0,
                "applies_to": "quantity",
                "min_quantity": 10,
                "min_amount": 200.0,
                "valid_until": "2024-12-31",
                "usage_limit": 1
            }
        }
        
        if discount_code not in valid_codes:
            return {
                "valid": False,
                "error": "Invalid discount code"
            }
        
        discount_info = valid_codes[discount_code]
        
        # Check minimum amount
        total_amount = sum(item.get("line_total", 0) for item in items)
        if discount_info.get("min_amount", 0) > total_amount:
            return {
                "valid": False,
                "error": f"Minimum order amount of ${discount_info['min_amount']} required"
            }
        
        # Check quantity requirements
        if discount_info.get("applies_to") == "quantity":
            total_quantity = sum(item.get("quantity", 0) for item in items)
            if discount_info.get("min_quantity", 0) > total_quantity:
                return {
                    "valid": False,
                    "error": f"Minimum quantity of {discount_info['min_quantity']} required"
                }
        
        # Check category requirements
        if discount_info.get("applies_to") == "category":
            applicable_parts = []
            for item in items:
                if item.get("category") == discount_info.get("category"):
                    applicable_parts.append(item["part_id"])
            
            if not applicable_parts:
                return {
                    "valid": False,
                    "error": f"Discount only applies to {discount_info['category']} parts"
                }
            
            discount_info["applicable_parts"] = applicable_parts
        
        return {
            "valid": True,
            "discount_info": discount_info,
            "discount_percent": discount_info["discount_percent"],
            "applies_to": discount_info["applies_to"],
            "applicable_parts": discount_info.get("applicable_parts", []),
            "max_discount": discount_info.get("max_discount")
        }
    
    async def calculate_bulk_pricing(
        self,
        items: List[Dict[str, Any]],
        customer_tier: str = "standard"
    ) -> Dict[str, Any]:
        """Calculate pricing for multiple items with bulk discounts."""
        total_amount = Decimal('0.00')
        total_discount = Decimal('0.00')
        processed_items = []
        
        for item in items:
            part_id = item.get("part_id")
            quantity = item.get("quantity", 1)
            location_id = item.get("location_id")
            
            # Get base pricing
            pricing = await self.get_part_pricing(
                part_id=part_id,
                location_id=location_id,
                customer_type="bulk",
                quantity=quantity
            )
            
            if pricing:
                # Apply customer tier discount
                tier_discount = await self.get_customer_tier_discount(
                    customer_tier=customer_tier,
                    part_category=pricing["category"]
                )
                
                # Apply quantity discount
                quantity_discount = await self.get_quantity_discount(
                    part_id=part_id,
                    quantity=quantity
                )
                
                # Calculate final price
                unit_price = pricing["unit_price"]
                if tier_discount > 0:
                    unit_price *= (1 - tier_discount / 100)
                if quantity_discount > 0:
                    unit_price *= (1 - quantity_discount / 100)
                
                line_total = unit_price * quantity
                total_amount += line_total
                
                item_discount = (pricing["unit_price"] - unit_price) * quantity
                total_discount += item_discount
                
                processed_items.append({
                    **item,
                    "original_price": float(pricing["unit_price"]),
                    "final_price": float(unit_price),
                    "line_total": float(line_total),
                    "discounts": {
                        "tier": tier_discount,
                        "quantity": quantity_discount,
                        "total": tier_discount + quantity_discount
                    }
                })
        
        # Apply bulk order discount if applicable
        bulk_discount = 0.0
        if total_amount >= 1000:
            bulk_discount = 5.0
        elif total_amount >= 500:
            bulk_discount = 3.0
        elif total_amount >= 250:
            bulk_discount = 2.0
        
        if bulk_discount > 0:
            bulk_discount_amount = total_amount * (bulk_discount / 100)
            total_discount += bulk_discount_amount
            total_amount -= bulk_discount_amount
        
        return {
            "items": processed_items,
            "subtotal": float(total_amount + total_discount),
            "total_discount": float(total_discount),
            "bulk_discount": bulk_discount,
            "total_amount": float(total_amount),
            "discount_percent": float((total_discount / (total_amount + total_discount)) * 100) if total_amount + total_discount > 0 else 0
        }
    
    def _calculate_base_price(
        self,
        part: PartsCatalog,
        inventory: Optional[Inventory],
        customer_type: str
    ) -> Decimal:
        """Calculate base price for a part."""
        # Start with cost or MSRP
        if inventory and inventory.cost:
            base_cost = Decimal(str(inventory.cost))
        elif part.cost:
            base_cost = Decimal(str(part.cost))
        elif part.msrp:
            base_cost = Decimal(str(part.msrp)) * Decimal('0.6')  # Estimate 40% margin
        else:
            return Decimal('0.00')
        
        # Apply markup based on customer type
        markup_multipliers = {
            "retail": 2.0,      # 100% markup for retail
            "wholesale": 1.5,   # 50% markup for wholesale
            "dealer": 1.3,      # 30% markup for dealers
            "bulk": 1.2,        # 20% markup for bulk orders
            "internal": 1.1     # 10% markup for internal use
        }
        
        multiplier = markup_multipliers.get(customer_type, 2.0)
        return base_cost * Decimal(str(multiplier))
    
    def _calculate_margin_percent(
        self,
        selling_price: Decimal,
        cost: Optional[Decimal]
    ) -> Optional[float]:
        """Calculate margin percentage."""
        if not cost or cost == 0:
            return None
        
        margin = ((selling_price - cost) / cost) * 100
        return float(margin)
    
    async def _get_availability_info(
        self,
        part_id: int,
        location_id: int
    ) -> Dict[str, Any]:
        """Get availability information for a part."""
        # This would check inventory across all locations
        # For now, return mock data
        return {
            "current_location": {
                "available": True,
                "quantity": 25,
                "location_id": location_id
            },
            "other_locations": [
                {
                    "location_id": 2,
                    "location_name": "Westside Location",
                    "quantity": 15
                },
                {
                    "location_id": 3,
                    "location_name": "Eastside Branch", 
                    "quantity": 8
                }
            ],
            "can_transfer": True,
            "estimated_transfer_time": "1-2 business days"
        }
