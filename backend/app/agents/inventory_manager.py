"""
Inventory Manager Agent - Tracks stock, triggers reorders, manages receiving.
"""

import time
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent, AgentResult
from app.models.agent_log import AgentType
from app.services.inventory_service import InventoryService
from app.services.notification_service import NotificationService


class InventoryManagerAgent(BaseAgent):
    """Agent for managing inventory across locations."""
    
    def __init__(self, db):
        super().__init__(db, AgentType.INVENTORY_MANAGER)
        self.inventory_service = InventoryService(db)
        self.notification_service = NotificationService(db)
    
    async def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """Process inventory management request."""
        start_time = time.time()
        
        try:
            action = input_data.get("action", "check_inventory")
            
            if action == "check_inventory":
                result = await self._check_inventory_levels(input_data)
            elif action == "process_receiving":
                result = await self._process_receiving(input_data)
            elif action == "trigger_reorder":
                result = await self._trigger_reorder(input_data)
            elif action == "transfer_stock":
                result = await self._transfer_stock(input_data)
            else:
                result = await self._general_inventory_management(input_data)
            
            processing_time = time.time() - start_time
            
            # Log the action
            await self.log_action(
                action=f"inventory_{action}",
                input_data=input_data,
                output_data=result,
                success=True,
                processing_time=processing_time,
                confidence=0.9
            )
            
            return AgentResult(
                success=True,
                data=result,
                message=f"Inventory {action} completed successfully",
                confidence=0.9,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            await self.log_action(
                action=f"inventory_{input_data.get('action', 'unknown')}",
                input_data=input_data,
                output_data={},
                success=False,
                processing_time=processing_time,
                error_message=str(e)
            )
            
            return AgentResult(
                success=False,
                message=f"Inventory management failed: {str(e)}",
                processing_time=processing_time
            )
    
    async def _check_inventory_levels(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check inventory levels and identify reorder needs."""
        location_id = input_data.get("location_id")
        part_id = input_data.get("part_id")
        
        # Get inventory data
        if part_id:
            inventory_data = await self.inventory_service.get_part_inventory(part_id, location_id)
        else:
            inventory_data = await self.inventory_service.get_location_inventory(location_id)
        
        # Check reorder points
        reorder_items = []
        low_stock_items = []
        
        for item in inventory_data:
            if item.get("needs_reorder"):
                reorder_items.append(item)
            elif item.get("quantity_available", 0) <= item.get("reorder_point", 0) * 1.5:
                low_stock_items.append(item)
        
        # Generate alerts
        alerts = []
        if reorder_items:
            alerts.append({
                "type": "reorder_needed",
                "message": f"{len(reorder_items)} items need immediate reordering",
                "items": reorder_items
            })
        
        if low_stock_items:
            alerts.append({
                "type": "low_stock",
                "message": f"{len(low_stock_items)} items running low",
                "items": low_stock_items
            })
        
        return {
            "inventory_summary": {
                "total_items": len(inventory_data),
                "reorder_needed": len(reorder_items),
                "low_stock": len(low_stock_items),
                "in_stock": len([item for item in inventory_data if item.get("quantity_available", 0) > 0])
            },
            "alerts": alerts,
            "detailed_inventory": inventory_data
        }
    
    async def _process_receiving(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process received inventory."""
        location_id = input_data.get("location_id")
        received_items = input_data.get("received_items", [])
        
        processed_items = []
        
        for item in received_items:
            part_id = item.get("part_id")
            quantity_received = item.get("quantity")
            cost = item.get("cost")
            batch_number = item.get("batch_number")
            
            # Update inventory
            result = await self.inventory_service.receive_inventory(
                part_id=part_id,
                location_id=location_id,
                quantity=quantity_received,
                cost=cost,
                batch_number=batch_number
            )
            
            processed_items.append({
                "part_id": part_id,
                "quantity_received": quantity_received,
                "new_quantity": result.get("new_quantity"),
                "success": result.get("success", False)
            })
        
        # Send notifications
        await self.notification_service.send_receiving_notification(
            location_id=location_id,
            received_items=processed_items
        )
        
        return {
            "receiving_summary": {
                "items_processed": len(processed_items),
                "successful": len([item for item in processed_items if item["success"]]),
                "failed": len([item for item in processed_items if not item["success"]])
            },
            "processed_items": processed_items
        }
    
    async def _trigger_reorder(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger reorder for low stock items."""
        location_id = input_data.get("location_id")
        part_id = input_data.get("part_id")
        quantity = input_data.get("quantity")
        
        if part_id:
            # Single part reorder
            result = await self.inventory_service.create_reorder(
                part_id=part_id,
                location_id=location_id,
                quantity=quantity or None  # Use default reorder quantity if not specified
            )
            
            reorders = [result] if result else []
        else:
            # Auto-reorder for all items below reorder point
            reorders = await self.inventory_service.auto_reorder(location_id)
        
        # Send notifications
        if reorders:
            await self.notification_service.send_reorder_notification(
                location_id=location_id,
                reorders=reorders
            )
        
        return {
            "reorder_summary": {
                "orders_created": len(reorders),
                "total_value": sum(order.get("estimated_cost", 0) for order in reorders)
            },
            "reorders": reorders
        }
    
    async def _transfer_stock(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transfer stock between locations."""
        from_location_id = input_data.get("from_location_id")
        to_location_id = input_data.get("to_location_id")
        part_id = input_data.get("part_id")
        quantity = input_data.get("quantity")
        
        # Validate transfer
        validation = await self.inventory_service.validate_transfer(
            part_id=part_id,
            from_location_id=from_location_id,
            quantity=quantity
        )
        
        if not validation.get("valid"):
            return {
                "success": False,
                "error": validation.get("error"),
                "transfer": None
            }
        
        # Execute transfer
        transfer_result = await self.inventory_service.transfer_stock(
            part_id=part_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity
        )
        
        # Send notifications
        await self.notification_service.send_transfer_notification(
            transfer_result
        )
        
        return {
            "success": True,
            "transfer": transfer_result,
            "message": "Stock transfer completed successfully"
        }
    
    async def _general_inventory_management(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """General inventory management tasks."""
        location_id = input_data.get("location_id")
        
        # Get comprehensive inventory report
        report = await self.inventory_service.generate_inventory_report(location_id)
        
        return {
            "inventory_report": report,
            "recommendations": self._generate_inventory_recommendations(report)
        }
    
    def _generate_inventory_recommendations(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate inventory management recommendations."""
        recommendations = []
        
        # Check for overstock
        overstock_items = report.get("overstock_items", [])
        if overstock_items:
            recommendations.append({
                "type": "overstock",
                "priority": "medium",
                "message": f"{len(overstock_items)} items are overstocked",
                "action": "Consider transferring or discounting overstock items"
            })
        
        # Check for dead stock
        dead_stock_items = report.get("dead_stock_items", [])
        if dead_stock_items:
            recommendations.append({
                "type": "dead_stock",
                "priority": "high",
                "message": f"{len(dead_stock_items)} items have no movement",
                "action": "Review and consider liquidation of dead stock"
            })
        
        # Check for fast movers
        fast_movers = report.get("fast_movers", [])
        if fast_movers:
            recommendations.append({
                "type": "fast_movers",
                "priority": "low",
                "message": f"{len(fast_movers)} items are fast movers",
                "action": "Consider increasing reorder quantities for fast movers"
            })
        
        return recommendations
