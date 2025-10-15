"""
Shipping Coordinator Agent - Handles shipping arrangements and tracking.
"""

import time
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.services.shipping_service import ShippingService
from app.services.tracking_service import TrackingService
from app.services.label_service import LabelService


class ShippingCoordinatorAgent(BaseAgent):
    """Agent for shipping coordination and logistics management."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.SHIPPING_COORDINATOR)
        self.shipping_service = ShippingService(db)
        self.tracking_service = TrackingService(db)
        self.label_service = LabelService(db)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process shipping-related request."""
        start_time = time.time()
        
        try:
            action = input_data.get("action", "create_shipment")
            
            if action == "create_shipment":
                result = await self._create_shipment(input_data)
            elif action == "get_shipping_rates":
                result = await self._get_shipping_rates(input_data)
            elif action == "generate_label":
                result = await self._generate_shipping_label(input_data)
            elif action == "track_shipment":
                result = await self._track_shipment(input_data)
            elif action == "schedule_pickup":
                result = await self._schedule_pickup(input_data)
            elif action == "update_delivery_status":
                result = await self._update_delivery_status(input_data)
            elif action == "handle_delivery_exception":
                result = await self._handle_delivery_exception(input_data)
            else:
                result = await self._general_shipping_workflow(input_data)
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action=f"shipping_{action}",
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
                message=f"Shipping {action} completed successfully",
                confidence=0.95,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action=f"shipping_{input_data.get('action', 'unknown')}",
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
                message=f"Shipping processing failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _create_shipment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new shipment."""
        order_id = input_data.get("order_id")
        customer_id = input_data.get("customer_id")
        shipping_address = input_data.get("shipping_address")
        items = input_data.get("items", [])
        
        if not order_id or not shipping_address:
            return {"success": False, "error": "order_id and shipping_address are required"}
        
        # Get shipping rates
        rates_result = await self.shipping_service.get_shipping_rates(
            origin_address=input_data.get("origin_address"),
            destination_address=shipping_address,
            package_info=input_data.get("package_info", self._calculate_package_info(items)),
            service_types=input_data.get("service_types", ["ground", "expedited", "overnight"])
        )
        
        if not rates_result["success"]:
            return rates_result
        
        # Select best shipping option (default to ground)
        selected_service = self._select_shipping_service(rates_result["rates"])
        
        # Create shipment
        shipment_result = await self.shipping_service.create_shipment(
            order_id=order_id,
            customer_id=customer_id,
            shipping_address=shipping_address,
            service_type=selected_service["service_type"],
            package_info=selected_service["package_info"],
            carrier=selected_service["carrier"]
        )
        
        if shipment_result["success"]:
            # Generate shipping label
            label_result = await self.label_service.generate_shipping_label(
                shipment_id=shipment_result["shipment"]["id"],
                service_type=selected_service["service_type"]
            )
            
            if label_result["success"]:
                shipment_result["label"] = label_result["label"]
                
                # Send tracking notification to customer
                await self._send_tracking_notification(
                    customer_id=customer_id,
                    tracking_number=shipment_result["shipment"]["tracking_number"]
                )
        
        return shipment_result
    
    async def _get_shipping_rates(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get shipping rates for different carriers and services."""
        origin_address = input_data.get("origin_address")
        destination_address = input_data.get("destination_address")
        package_info = input_data.get("package_info")
        service_types = input_data.get("service_types", ["ground", "expedited", "overnight"])
        
        if not origin_address or not destination_address or not package_info:
            return {"success": False, "error": "origin_address, destination_address, and package_info are required"}
        
        # Get rates from multiple carriers
        rates_result = await self.shipping_service.get_shipping_rates(
            origin_address=origin_address,
            destination_address=destination_address,
            package_info=package_info,
            service_types=service_types
        )
        
        if rates_result["success"]:
            # Add recommendations
            recommendations = self._generate_shipping_recommendations(rates_result["rates"])
            rates_result["recommendations"] = recommendations
        
        return rates_result
    
    async def _generate_shipping_label(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate shipping label for an existing shipment."""
        shipment_id = input_data.get("shipment_id")
        
        if not shipment_id:
            return {"success": False, "error": "shipment_id is required"}
        
        # Generate label
        label_result = await self.label_service.generate_shipping_label(
            shipment_id=shipment_id,
            service_type=input_data.get("service_type", "ground")
        )
        
        if label_result["success"]:
            # Update shipment status
            await self.shipping_service.update_shipment_status(
                shipment_id=shipment_id,
                status="label_created"
            )
        
        return label_result
    
    async def _track_shipment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track shipment status."""
        tracking_number = input_data.get("tracking_number")
        carrier = input_data.get("carrier")
        
        if not tracking_number:
            return {"success": False, "error": "tracking_number is required"}
        
        # Get tracking information
        tracking_result = await self.tracking_service.get_tracking_info(
            tracking_number=tracking_number,
            carrier=carrier
        )
        
        if tracking_result["success"]:
            # Update local tracking status
            await self.shipping_service.update_tracking_status(
                tracking_number=tracking_number,
                tracking_info=tracking_result["tracking_info"]
            )
            
            # Check if delivery is complete
            if tracking_result["tracking_info"]["status"] == "delivered":
                await self._handle_delivery_completion(tracking_number)
        
        return tracking_result
    
    async def _schedule_pickup(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule carrier pickup."""
        shipment_id = input_data.get("shipment_id")
        pickup_date = input_data.get("pickup_date")
        pickup_time = input_data.get("pickup_time", "9:00 AM - 5:00 PM")
        
        if not shipment_id or not pickup_date:
            return {"success": False, "error": "shipment_id and pickup_date are required"}
        
        # Schedule pickup with carrier
        pickup_result = await self.shipping_service.schedule_pickup(
            shipment_id=shipment_id,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            pickup_address=input_data.get("pickup_address")
        )
        
        return pickup_result
    
    async def _update_delivery_status(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update delivery status from webhook or manual update."""
        tracking_number = input_data.get("tracking_number")
        status = input_data.get("status")
        location = input_data.get("location")
        timestamp = input_data.get("timestamp")
        
        if not tracking_number or not status:
            return {"success": False, "error": "tracking_number and status are required"}
        
        # Update delivery status
        update_result = await self.shipping_service.update_delivery_status(
            tracking_number=tracking_number,
            status=status,
            location=location,
            timestamp=timestamp
        )
        
        if update_result["success"]:
            # Send status notification to customer
            await self._send_delivery_status_notification(
                tracking_number=tracking_number,
                status=status,
                location=location
            )
        
        return update_result
    
    async def _handle_delivery_exception(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delivery exceptions (damage, delay, etc.)."""
        tracking_number = input_data.get("tracking_number")
        exception_type = input_data.get("exception_type")
        description = input_data.get("description")
        
        if not tracking_number or not exception_type:
            return {"success": False, "error": "tracking_number and exception_type are required"}
        
        # Handle the exception
        exception_result = await self.shipping_service.handle_delivery_exception(
            tracking_number=tracking_number,
            exception_type=exception_type,
            description=description,
            resolution_required=input_data.get("resolution_required", True)
        )
        
        if exception_result["success"]:
            # Notify customer and staff
            await self._send_exception_notification(
                tracking_number=tracking_number,
                exception_type=exception_type,
                description=description
            )
        
        return exception_result
    
    async def _general_shipping_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general shipping workflow."""
        return {
            "message": "General shipping workflow processed",
            "input_data": input_data
        }
    
    def _calculate_package_info(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate package dimensions and weight from items."""
        total_weight = 0
        total_volume = 0
        item_count = 0
        
        for item in items:
            weight = item.get("weight", 0)
            length = item.get("length", 0)
            width = item.get("width", 0)
            height = item.get("height", 0)
            quantity = item.get("quantity", 1)
            
            total_weight += weight * quantity
            total_volume += (length * width * height * quantity)
            item_count += quantity
        
        # Estimate package dimensions if not provided
        if total_volume > 0:
            # Simple cubic root estimation
            side = (total_volume ** (1/3)) * 1.2  # Add 20% for packaging
            length = width = height = side
        else:
            # Default dimensions for small parts
            length = width = height = 6
        
        return {
            "weight": max(total_weight, 1),  # Minimum 1 lb
            "length": length,
            "width": width,
            "height": height,
            "item_count": item_count
        }
    
    def _select_shipping_service(self, rates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best shipping service based on cost and delivery time."""
        # Filter for available services
        available_rates = [rate for rate in rates if rate["available"]]
        
        if not available_rates:
            return rates[0] if rates else None
        
        # Sort by cost (prefer ground shipping for cost efficiency)
        ground_services = [rate for rate in available_rates if "ground" in rate["service_type"].lower()]
        
        if ground_services:
            return min(ground_services, key=lambda x: x["cost"])
        
        # Fallback to cheapest available service
        return min(available_rates, key=lambda x: x["cost"])
    
    def _generate_shipping_recommendations(self, rates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate shipping recommendations based on rates."""
        recommendations = []
        
        # Find best options
        cheapest = min(rates, key=lambda x: x["cost"]) if rates else None
        fastest = min(rates, key=lambda x: x["delivery_days"]) if rates else None
        
        if cheapest:
            recommendations.append({
                "type": "cost_effective",
                "title": "Most Cost-Effective",
                "service": cheapest["service_type"],
                "carrier": cheapest["carrier"],
                "cost": cheapest["cost"],
                "delivery_days": cheapest["delivery_days"],
                "reason": "Best value for money"
            })
        
        if fastest and fastest != cheapest:
            recommendations.append({
                "type": "fastest",
                "title": "Fastest Delivery",
                "service": fastest["service_type"],
                "carrier": fastest["carrier"],
                "cost": fastest["cost"],
                "delivery_days": fastest["delivery_days"],
                "reason": "Quickest delivery time"
            })
        
        # Add balanced option
        balanced = None
        if len(rates) > 2:
            sorted_by_balance = sorted(rates, key=lambda x: x["cost"] + (x["delivery_days"] * 2))
            balanced = sorted_by_balance[0]
            
            if balanced and balanced != cheapest and balanced != fastest:
                recommendations.append({
                    "type": "balanced",
                    "title": "Best Balance",
                    "service": balanced["service_type"],
                    "carrier": balanced["carrier"],
                    "cost": balanced["cost"],
                    "delivery_days": balanced["delivery_days"],
                    "reason": "Good balance of cost and speed"
                })
        
        return recommendations
    
    async def _send_tracking_notification(self, customer_id: int, tracking_number: str) -> None:
        """Send tracking notification to customer."""
        # This would integrate with notification service
        print(f"Sending tracking notification to customer {customer_id} for tracking {tracking_number}")
    
    async def _send_delivery_status_notification(self, tracking_number: str, status: str, location: str) -> None:
        """Send delivery status notification."""
        print(f"Delivery status update for {tracking_number}: {status} at {location}")
    
    async def _send_exception_notification(self, tracking_number: str, exception_type: str, description: str) -> None:
        """Send delivery exception notification."""
        print(f"Delivery exception for {tracking_number}: {exception_type} - {description}")
    
    async def _handle_delivery_completion(self, tracking_number: str) -> None:
        """Handle delivery completion."""
        # Update order status to delivered
        # Send delivery confirmation
        # Trigger follow-up actions
        print(f"Handling delivery completion for {tracking_number}")
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for shipping coordinator agent."""
        return """
You are a specialized Shipping Coordinator Agent for a dealership parts management system.

Your responsibilities:
1. Coordinate shipping arrangements for parts orders
2. Compare rates across multiple carriers (UPS, FedEx, USPS, DHL)
3. Generate shipping labels and tracking information
4. Monitor shipment status and handle exceptions
5. Schedule pickups and manage delivery logistics
6. Provide shipping recommendations based on cost and speed

Shipping Services:
- Ground: Most cost-effective for standard delivery
- Expedited: Faster delivery for urgent orders
- Overnight: Next-day delivery for critical parts
- International: Cross-border shipping for special orders

Key Features:
- Multi-carrier rate shopping
- Automated label generation
- Real-time tracking updates
- Delivery exception handling
- Customer notification system
- Pickup scheduling
- Insurance and signature options

Always prioritize cost-effectiveness while meeting delivery requirements and customer expectations.
"""
