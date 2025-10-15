"""
ERP Mock Integration - Lester's Workflow Welds
Integrates RAG outputs to PO mocks with SMS notifications
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# Mock ERP systems
ERP_SYSTEMS = {
    "CDK": {
        "name": "CDK Global",
        "api_endpoint": "https://api.cdk.com/v1/",
        "po_prefix": "CDK",
        "integration_type": "REST API"
    },
    "Reynolds": {
        "name": "Reynolds and Reynolds",
        "api_endpoint": "https://api.reynolds.com/v2/",
        "po_prefix": "RRN",
        "integration_type": "REST API"
    },
    "DealerSocket": {
        "name": "DealerSocket",
        "api_endpoint": "https://api.dealersocket.com/v1/",
        "po_prefix": "DSK",
        "integration_type": "REST API"
    }
}

@dataclass
class PurchaseOrder:
    """Purchase order data structure"""
    po_id: str
    part_name: str
    part_sku: str
    quantity: int
    unit_price: float
    total_price: float
    from_location: str
    to_location: str
    status: str
    created_at: datetime
    estimated_delivery: datetime
    tracking_number: Optional[str] = None
    supplier: Optional[str] = None

class ERPMockIntegration:
    """Mock ERP integration for purchase orders"""
    
    def __init__(self, erp_system: str = "CDK"):
        self.erp_system = erp_system
        self.erp_config = ERP_SYSTEMS.get(erp_system, ERP_SYSTEMS["CDK"])
        self.po_counter = 1000
        self.purchase_orders = []
        
    def create_purchase_order(self, part_data: Dict, from_location: str, to_location: str, quantity: int = 1) -> PurchaseOrder:
        """Create a purchase order"""
        self.po_counter += 1
        po_id = f"{self.erp_config['po_prefix']}-{self.po_counter:06d}"
        
        # Calculate pricing with markup for transfer
        unit_price = part_data.get("price", 0)
        transfer_markup = 0.15  # 15% markup for inter-location transfers
        transfer_price = unit_price * (1 + transfer_markup)
        total_price = transfer_price * quantity
        
        # Estimate delivery time (1-3 days for local transfers)
        delivery_hours = random.randint(24, 72)
        estimated_delivery = datetime.now() + timedelta(hours=delivery_hours)
        
        po = PurchaseOrder(
            po_id=po_id,
            part_name=part_data.get("part", "Unknown Part"),
            part_sku=part_data.get("sku", "N/A"),
            quantity=quantity,
            unit_price=transfer_price,
            total_price=total_price,
            from_location=from_location,
            to_location=to_location,
            status="pending",
            created_at=datetime.now(),
            estimated_delivery=estimated_delivery
        )
        
        self.purchase_orders.append(po)
        return po
    
    def process_order(self, po: PurchaseOrder) -> Dict:
        """Process purchase order through ERP system"""
        # Simulate ERP processing delay
        time.sleep(0.1)  # Simulate API call
        
        # Update status based on ERP response
        success_rate = 0.95  # 95% success rate
        if random.random() < success_rate:
            po.status = "approved"
            po.tracking_number = f"TRK{random.randint(100000, 999999)}"
            po.supplier = f"Supplier-{random.randint(1, 10)}"
            
            return {
                "success": True,
                "po_id": po.po_id,
                "status": "approved",
                "tracking_number": po.tracking_number,
                "supplier": po.supplier,
                "estimated_delivery": po.estimated_delivery.isoformat(),
                "message": f"Purchase order {po.po_id} approved and tracking assigned"
            }
        else:
            po.status = "rejected"
            return {
                "success": False,
                "po_id": po.po_id,
                "status": "rejected",
                "message": f"Purchase order {po.po_id} rejected - insufficient inventory or supplier unavailable"
            }
    
    def get_order_status(self, po_id: str) -> Optional[Dict]:
        """Get order status from ERP"""
        po = next((p for p in self.purchase_orders if p.po_id == po_id), None)
        if not po:
            return None
        
        return {
            "po_id": po.po_id,
            "status": po.status,
            "part_name": po.part_name,
            "quantity": po.quantity,
            "total_price": po.total_price,
            "from_location": po.from_location,
            "to_location": po.to_location,
            "created_at": po.created_at.isoformat(),
            "estimated_delivery": po.estimated_delivery.isoformat(),
            "tracking_number": po.tracking_number,
            "supplier": po.supplier
        }
    
    def get_location_inventory(self, location: str) -> List[Dict]:
        """Get inventory for a specific location"""
        # Mock inventory data
        mock_inventory = [
            {"sku": "BP-HC19", "part": "Brake Pads Honda Civic", "stock": 5, "price": 45},
            {"sku": "ALT-F150", "part": "Alternator Ford F-150", "stock": 2, "price": 120},
            {"sku": "OF-TC", "part": "Oil Filter Toyota Camry", "stock": 8, "price": 12}
        ]
        
        # Add location-specific variations
        for item in mock_inventory:
            item["location"] = location
            # Vary stock based on location
            item["stock"] = max(0, item["stock"] + random.randint(-2, 2))
        
        return mock_inventory
    
    def check_transfer_feasibility(self, part_sku: str, from_location: str, to_location: str, quantity: int) -> Dict:
        """Check if transfer is feasible"""
        from_inventory = self.get_location_inventory(from_location)
        part_inventory = next((item for item in from_inventory if item["sku"] == part_sku), None)
        
        if not part_inventory:
            return {
                "feasible": False,
                "reason": f"Part {part_sku} not found at {from_location}",
                "available_stock": 0
            }
        
        available_stock = part_inventory["stock"]
        if available_stock < quantity:
            return {
                "feasible": False,
                "reason": f"Insufficient stock at {from_location}",
                "available_stock": available_stock,
                "requested_quantity": quantity
            }
        
        return {
            "feasible": True,
            "reason": "Transfer feasible",
            "available_stock": available_stock,
            "requested_quantity": quantity,
            "unit_price": part_inventory["price"]
        }

class SMSNotificationService:
    """Mock SMS notification service"""
    
    def __init__(self):
        self.notifications = []
    
    def send_transfer_notification(self, po: PurchaseOrder, recipient_phone: str) -> Dict:
        """Send SMS notification about transfer"""
        # Mock SMS sending
        message = f"Parts transfer {po.po_id}: {po.part_name} x{po.quantity} from {po.from_location} to {po.to_location}. ETA: {po.estimated_delivery.strftime('%m/%d %H:%M')}. Track: {po.tracking_number or 'TBD'}"
        
        notification = {
            "id": f"SMS-{len(self.notifications) + 1}",
            "phone": recipient_phone,
            "message": message,
            "po_id": po.po_id,
            "sent_at": datetime.now().isoformat(),
            "status": "sent"
        }
        
        self.notifications.append(notification)
        
        return {
            "success": True,
            "notification_id": notification["id"],
            "message": "SMS notification sent",
            "recipient": recipient_phone
        }
    
    def send_status_update(self, po_id: str, status: str, recipient_phone: str) -> Dict:
        """Send status update SMS"""
        message = f"Update: PO {po_id} status changed to {status}"
        
        notification = {
            "id": f"SMS-{len(self.notifications) + 1}",
            "phone": recipient_phone,
            "message": message,
            "po_id": po_id,
            "sent_at": datetime.now().isoformat(),
            "status": "sent"
        }
        
        self.notifications.append(notification)
        
        return {
            "success": True,
            "notification_id": notification["id"],
            "message": "Status update sent"
        }

class WorkflowIntegration:
    """Main workflow integration class"""
    
    def __init__(self, erp_system: str = "CDK"):
        self.erp = ERPMockIntegration(erp_system)
        self.sms = SMSNotificationService()
    
    def process_rag_to_po(self, rag_result: Dict, from_location: str, to_location: str, quantity: int = 1, recipient_phone: str = "+1-555-0123") -> Dict:
        """Complete workflow: RAG result → PO → SMS notification"""
        
        # Extract part data from RAG result
        part_data = rag_result.get("result", {})
        
        if not part_data or part_data.get("stock", 0) <= 0:
            return {
                "success": False,
                "message": "No available stock for transfer",
                "rag_result": rag_result
            }
        
        # Check transfer feasibility
        feasibility = self.erp.check_transfer_feasibility(
            part_data.get("sku", ""),
            from_location,
            to_location,
            quantity
        )
        
        if not feasibility["feasible"]:
            return {
                "success": False,
                "message": feasibility["reason"],
                "feasibility_check": feasibility
            }
        
        # Create purchase order
        po = self.erp.create_purchase_order(part_data, from_location, to_location, quantity)
        
        # Process through ERP
        erp_result = self.erp.process_order(po)
        
        if erp_result["success"]:
            # Send SMS notification
            sms_result = self.sms.send_transfer_notification(po, recipient_phone)
            
            return {
                "success": True,
                "message": "Complete workflow executed successfully",
                "rag_result": rag_result,
                "purchase_order": {
                    "po_id": po.po_id,
                    "part_name": po.part_name,
                    "quantity": po.quantity,
                    "total_price": po.total_price,
                    "from_location": po.from_location,
                    "to_location": po.to_location,
                    "estimated_delivery": po.estimated_delivery.isoformat(),
                    "tracking_number": po.tracking_number
                },
                "erp_result": erp_result,
                "sms_result": sms_result
            }
        else:
            return {
                "success": False,
                "message": "ERP processing failed",
                "purchase_order": {
                    "po_id": po.po_id,
                    "status": po.status
                },
                "erp_result": erp_result
            }
    
    def get_workflow_stats(self) -> Dict:
        """Get workflow statistics"""
        total_pos = len(self.erp.purchase_orders)
        successful_pos = len([p for p in self.erp.purchase_orders if p.status == "approved"])
        total_sms = len(self.sms.notifications)
        
        return {
            "total_purchase_orders": total_pos,
            "successful_orders": successful_pos,
            "success_rate": (successful_pos / total_pos * 100) if total_pos > 0 else 0,
            "total_sms_notifications": total_sms,
            "erp_system": self.erp.erp_system,
            "last_updated": datetime.now().isoformat()
        }

def demo_erp_integration():
    """Demo ERP integration functionality"""
    print("🏭 Lester's ERP Integration Demo")
    print("=" * 50)
    
    # Initialize workflow
    workflow = WorkflowIntegration("CDK")
    
    # Mock RAG result
    rag_result = {
        "result": {
            "part": "Brake Pads 2019 Honda Civic",
            "location": "Chicago North",
            "stock": 5,
            "sku": "BP-HC19",
            "price": 45,
            "score": 0.9
        },
        "color": "🟢 Auto-resolved & Paid"
    }
    
    print("🔍 Processing RAG result through ERP workflow...")
    print(f"Part: {rag_result['result']['part']}")
    print(f"Stock: {rag_result['result']['stock']}")
    print(f"Location: {rag_result['result']['location']}")
    
    # Process complete workflow
    workflow_result = workflow.process_rag_to_po(
        rag_result=rag_result,
        from_location="Chicago North",
        to_location="O'Hare Auto",
        quantity=2,
        recipient_phone="+1-312-555-0123"
    )
    
    print(f"\n📊 Workflow Result:")
    print(f"Success: {workflow_result['success']}")
    print(f"Message: {workflow_result['message']}")
    
    if workflow_result['success']:
        po_data = workflow_result['purchase_order']
        print(f"\n📋 Purchase Order:")
        print(f"  PO ID: {po_data['po_id']}")
        print(f"  Part: {po_data['part_name']}")
        print(f"  Quantity: {po_data['quantity']}")
        print(f"  Total Price: ${po_data['total_price']:.2f}")
        print(f"  From: {po_data['from_location']}")
        print(f"  To: {po_data['to_location']}")
        print(f"  ETA: {po_data['estimated_delivery']}")
        print(f"  Tracking: {po_data['tracking_number']}")
        
        sms_data = workflow_result['sms_result']
        print(f"\n📱 SMS Notification:")
        print(f"  ID: {sms_data['notification_id']}")
        print(f"  Recipient: {sms_data['recipient']}")
        print(f"  Status: {sms_data['message']}")
    
    # Show workflow stats
    stats = workflow.get_workflow_stats()
    print(f"\n📈 Workflow Statistics:")
    print(f"  Total POs: {stats['total_purchase_orders']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print(f"  SMS Sent: {stats['total_sms_notifications']}")
    print(f"  ERP System: {stats['erp_system']}")
    
    print(f"\n🏢 Available ERP Systems:")
    for system, config in ERP_SYSTEMS.items():
        print(f"  - {system}: {config['name']} ({config['integration_type']})")

if __name__ == "__main__":
    demo_erp_integration()
