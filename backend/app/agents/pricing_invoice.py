"""
Pricing & Invoice Agent - Generates quotes and invoices with tax calculations.
"""

import time
from typing import Dict, Any, List, Optional
from decimal import Decimal
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.services.pricing_service import PricingService
from app.services.invoice_service import InvoiceService
from app.services.tax_service import TaxService


class PricingInvoiceAgent(BaseAgent):
    """Agent for pricing and invoice generation."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.PRICING_INVOICE)
        self.pricing_service = PricingService(db)
        self.invoice_service = InvoiceService(db)
        self.tax_service = TaxService(db)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process pricing and invoice request."""
        start_time = time.time()
        
        try:
            action = input_data.get("action", "generate_quote")
            
            if action == "generate_quote":
                result = await self._generate_quote(input_data)
            elif action == "create_invoice":
                result = await self._create_invoice(input_data)
            elif action == "calculate_pricing":
                result = await self._calculate_pricing(input_data)
            elif action == "apply_discount":
                result = await self._apply_discount(input_data)
            else:
                result = await self._general_pricing_workflow(input_data)
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action=f"pricing_{action}",
                input_data=input_data,
                output_data=result,
                success=True,
                processing_time=processing_time,
                confidence=0.95,
                customer_id=input_data.get("customer_id"),
                order_id=input_data.get("order_id")
            )
            
            return AgentResult(
                success=True,
                data=result,
                message=f"Pricing {action} completed successfully",
                confidence=0.95,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action=f"pricing_{input_data.get('action', 'unknown')}",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e),
                customer_id=input_data.get("customer_id"),
                order_id=input_data.get("order_id")
            )
            
            return AgentResult(
                success=False,
                message=f"Pricing processing failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _generate_quote(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a quote for parts and services."""
        customer_id = input_data.get("customer_id")
        location_id = input_data.get("location_id")
        items = input_data.get("items", [])
        customer_type = input_data.get("customer_type", "retail")
        
        # Calculate pricing for each item
        quote_items = []
        subtotal = Decimal('0.00')
        
        for item in items:
            part_id = item.get("part_id")
            quantity = item.get("quantity", 1)
            
            # Get part pricing
            pricing = await self.pricing_service.get_part_pricing(
                part_id=part_id,
                location_id=location_id,
                customer_type=customer_type,
                quantity=quantity
            )
            
            if pricing:
                line_total = pricing["unit_price"] * quantity
                subtotal += line_total
                
                quote_items.append({
                    "part_id": part_id,
                    "part_number": pricing.get("part_number"),
                    "part_name": pricing.get("part_name"),
                    "quantity": quantity,
                    "unit_price": float(pricing["unit_price"]),
                    "line_total": float(line_total),
                    "discount_percent": pricing.get("discount_percent", 0),
                    "availability": pricing.get("availability")
                })
        
        # Calculate taxes
        tax_info = await self.tax_service.calculate_taxes(
            location_id=location_id,
            subtotal=subtotal,
            items=quote_items
        )
        
        # Calculate shipping if applicable
        shipping_cost = await self._calculate_shipping(
            items=quote_items,
            customer_id=customer_id,
            location_id=location_id
        )
        
        # Calculate total
        total_amount = subtotal + tax_info["total_tax"] + shipping_cost
        
        # Generate quote number
        quote_number = await self.invoice_service.generate_quote_number(location_id)
        
        quote_data = {
            "quote_number": quote_number,
            "customer_id": customer_id,
            "location_id": location_id,
            "customer_type": customer_type,
            "items": quote_items,
            "pricing": {
                "subtotal": float(subtotal),
                "tax_amount": float(tax_info["total_tax"]),
                "shipping_cost": float(shipping_cost),
                "total_amount": float(total_amount)
            },
            "tax_breakdown": tax_info["breakdown"],
            "valid_until": self._get_quote_expiry(),
            "terms_and_conditions": self._get_quote_terms()
        }
        
        return quote_data
    
    async def _create_invoice(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice from quote or order."""
        quote_id = input_data.get("quote_id")
        order_id = input_data.get("order_id")
        customer_id = input_data.get("customer_id")
        location_id = input_data.get("location_id")
        
        if quote_id:
            # Create invoice from quote
            invoice_data = await self._invoice_from_quote(quote_id, customer_id, location_id)
        elif order_id:
            # Create invoice from order
            invoice_data = await self._invoice_from_order(order_id, customer_id, location_id)
        else:
            raise ValueError("Either quote_id or order_id must be provided")
        
        # Generate PDF
        pdf_path = await self.invoice_service.generate_invoice_pdf(invoice_data)
        invoice_data["pdf_path"] = pdf_path
        
        # Send email notification
        await self.invoice_service.send_invoice_email(invoice_data)
        
        return invoice_data
    
    async def _calculate_pricing(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate pricing for parts with various factors."""
        part_id = input_data.get("part_id")
        location_id = input_data.get("location_id")
        customer_type = input_data.get("customer_type", "retail")
        quantity = input_data.get("quantity", 1)
        customer_tier = input_data.get("customer_tier", "standard")
        
        # Get base pricing
        base_pricing = await self.pricing_service.get_part_pricing(
            part_id=part_id,
            location_id=location_id,
            customer_type=customer_type,
            quantity=quantity
        )
        
        if not base_pricing:
            return {"error": "Part not found or not available"}
        
        # Apply customer tier discounts
        tier_discount = await self.pricing_service.get_customer_tier_discount(
            customer_tier=customer_tier,
            part_category=base_pricing.get("category")
        )
        
        # Apply quantity discounts
        quantity_discount = await self.pricing_service.get_quantity_discount(
            part_id=part_id,
            quantity=quantity
        )
        
        # Calculate final pricing
        unit_price = base_pricing["unit_price"]
        
        # Apply discounts (cumulative)
        if tier_discount > 0:
            unit_price *= (1 - tier_discount / 100)
        
        if quantity_discount > 0:
            unit_price *= (1 - quantity_discount / 100)
        
        line_total = unit_price * quantity
        
        return {
            "part_id": part_id,
            "part_number": base_pricing.get("part_number"),
            "part_name": base_pricing.get("part_name"),
            "base_price": float(base_pricing["unit_price"]),
            "unit_price": float(unit_price),
            "quantity": quantity,
            "line_total": float(line_total),
            "discounts": {
                "customer_tier": tier_discount,
                "quantity": quantity_discount,
                "total_discount_percent": tier_discount + quantity_discount
            },
            "availability": base_pricing.get("availability")
        }
    
    async def _apply_discount(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply promotional or special discounts."""
        items = input_data.get("items", [])
        discount_code = input_data.get("discount_code")
        customer_id = input_data.get("customer_id")
        location_id = input_data.get("location_id")
        
        # Validate discount code
        discount_info = await self.pricing_service.validate_discount_code(
            discount_code=discount_code,
            customer_id=customer_id,
            location_id=location_id,
            items=items
        )
        
        if not discount_info["valid"]:
            return {
                "success": False,
                "error": discount_info["error"],
                "discount_code": discount_code
            }
        
        # Apply discount to items
        discounted_items = []
        total_discount = Decimal('0.00')
        
        for item in items:
            if discount_info["applies_to"] == "all" or item["part_id"] in discount_info.get("applicable_parts", []):
                discount_amount = item["line_total"] * (discount_info["discount_percent"] / 100)
                discounted_line_total = item["line_total"] - discount_amount
                total_discount += discount_amount
                
                discounted_items.append({
                    **item,
                    "original_line_total": item["line_total"],
                    "discount_amount": float(discount_amount),
                    "line_total": float(discounted_line_total)
                })
            else:
                discounted_items.append(item)
        
        return {
            "success": True,
            "discount_code": discount_code,
            "discount_info": discount_info,
            "items": discounted_items,
            "total_discount": float(total_discount),
            "message": f"Applied {discount_info['discount_percent']}% discount"
        }
    
    async def _general_pricing_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general pricing workflow."""
        return {
            "message": "General pricing workflow processed",
            "input_data": input_data
        }
    
    async def _invoice_from_quote(self, quote_id: int, customer_id: int, location_id: int) -> Dict[str, Any]:
        """Create invoice from existing quote."""
        # This would fetch quote data and convert to invoice
        # For now, return placeholder data
        return {
            "invoice_type": "from_quote",
            "quote_id": quote_id,
            "customer_id": customer_id,
            "location_id": location_id,
            "status": "draft"
        }
    
    async def _invoice_from_order(self, order_id: int, customer_id: int, location_id: int) -> Dict[str, Any]:
        """Create invoice from existing order."""
        # This would fetch order data and convert to invoice
        # For now, return placeholder data
        return {
            "invoice_type": "from_order",
            "order_id": order_id,
            "customer_id": customer_id,
            "location_id": location_id,
            "status": "draft"
        }
    
    async def _calculate_shipping(self, items: List[Dict[str, Any]], customer_id: int, location_id: int) -> Decimal:
        """Calculate shipping costs."""
        # Simple shipping calculation based on weight and location
        total_weight = sum(item.get("weight", 0) * item.get("quantity", 1) for item in items)
        
        # Base shipping rates (simplified)
        if total_weight < 5:
            return Decimal('9.99')
        elif total_weight < 20:
            return Decimal('19.99')
        else:
            return Decimal('29.99')
    
    def _get_quote_expiry(self) -> str:
        """Get quote expiry date (30 days from now)."""
        from datetime import datetime, timedelta
        expiry_date = datetime.utcnow() + timedelta(days=30)
        return expiry_date.isoformat()
    
    def _get_quote_terms(self) -> List[str]:
        """Get standard quote terms and conditions."""
        return [
            "Quote valid for 30 days from issue date",
            "Prices subject to change without notice",
            "Payment terms: Net 30 days",
            "Shipping costs not included unless specified",
            "All sales final - no returns on special orders"
        ]
