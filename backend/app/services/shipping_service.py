"""
Shipping service for multi-carrier integration and shipment management.
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.shipment import Shipment, ShipmentStatus


class ShippingService:
    """Service for shipping operations with multiple carriers."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.carriers = {
            "ups": UPSShippingProvider(),
            "fedex": FedExShippingProvider(),
            "usps": USPSShippingProvider(),
            "dhl": DHLShippingProvider()
        }
    
    async def get_shipping_rates(
        self,
        origin_address: Dict[str, str],
        destination_address: Dict[str, str],
        package_info: Dict[str, Any],
        service_types: List[str] = None
    ) -> Dict[str, Any]:
        """Get shipping rates from multiple carriers."""
        try:
            if not service_types:
                service_types = ["ground", "expedited", "overnight"]
            
            all_rates = []
            
            # Get rates from each carrier
            for carrier_name, carrier_provider in self.carriers.items():
                try:
                    carrier_rates = await carrier_provider.get_rates(
                        origin_address=origin_address,
                        destination_address=destination_address,
                        package_info=package_info,
                        service_types=service_types
                    )
                    
                    if carrier_rates["success"]:
                        all_rates.extend(carrier_rates["rates"])
                    
                except Exception as e:
                    print(f"Error getting rates from {carrier_name}: {e}")
                    continue
            
            # Sort rates by cost
            all_rates.sort(key=lambda x: x["cost"])
            
            return {
                "success": True,
                "rates": all_rates,
                "carrier_count": len(set(rate["carrier"] for rate in all_rates)),
                "total_options": len(all_rates)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_shipment(
        self,
        order_id: int,
        customer_id: int,
        shipping_address: Dict[str, str],
        service_type: str,
        package_info: Dict[str, Any],
        carrier: str
    ) -> Dict[str, Any]:
        """Create a new shipment."""
        try:
            # Get carrier provider
            carrier_provider = self.carriers.get(carrier)
            if not carrier_provider:
                return {"success": False, "error": f"Carrier {carrier} not supported"}
            
            # Create shipment with carrier
            shipment_result = await carrier_provider.create_shipment(
                service_type=service_type,
                package_info=package_info,
                destination_address=shipping_address
            )
            
            if not shipment_result["success"]:
                return shipment_result
            
            # Save shipment to database
            shipment = Shipment(
                order_id=order_id,
                customer_id=customer_id,
                carrier=carrier,
                service_type=service_type,
                tracking_number=shipment_result["tracking_number"],
                status=ShipmentStatus.CREATED,
                shipping_address=str(shipping_address),
                package_info=str(package_info),
                cost=shipment_result.get("cost", 0),
                estimated_delivery=shipment_result.get("estimated_delivery")
            )
            
            self.db.add(shipment)
            await self.db.commit()
            await self.db.refresh(shipment)
            
            return {
                "success": True,
                "shipment": {
                    "id": shipment.id,
                    "tracking_number": shipment.tracking_number,
                    "carrier": shipment.carrier,
                    "service_type": shipment.service_type,
                    "status": shipment.status.value,
                    "cost": float(shipment.cost),
                    "estimated_delivery": shipment.estimated_delivery.isoformat() if shipment.estimated_delivery else None
                }
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def update_shipment_status(
        self,
        shipment_id: int,
        status: str
    ) -> Dict[str, Any]:
        """Update shipment status."""
        try:
            # This would update the database
            # For now, return success
            return {"success": True, "shipment_id": shipment_id, "status": status}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_tracking_status(
        self,
        tracking_number: str,
        tracking_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update tracking status from carrier webhook."""
        try:
            # This would update the database with tracking information
            return {"success": True, "tracking_number": tracking_number}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_delivery_status(
        self,
        tracking_number: str,
        status: str,
        location: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update delivery status."""
        try:
            # This would update the database
            return {
                "success": True,
                "tracking_number": tracking_number,
                "status": status,
                "location": location,
                "timestamp": timestamp
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def schedule_pickup(
        self,
        shipment_id: int,
        pickup_date: str,
        pickup_time: str = "9:00 AM - 5:00 PM",
        pickup_address: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Schedule carrier pickup."""
        try:
            # This would schedule pickup with the carrier
            return {
                "success": True,
                "shipment_id": shipment_id,
                "pickup_date": pickup_date,
                "pickup_time": pickup_time,
                "pickup_scheduled": True
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_delivery_exception(
        self,
        tracking_number: str,
        exception_type: str,
        description: str,
        resolution_required: bool = True
    ) -> Dict[str, Any]:
        """Handle delivery exceptions."""
        try:
            # This would handle the exception and create resolution tasks
            return {
                "success": True,
                "tracking_number": tracking_number,
                "exception_type": exception_type,
                "description": description,
                "resolution_required": resolution_required,
                "exception_id": f"EXC-{tracking_number}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_shipment_history(
        self,
        order_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get shipment history with filters."""
        try:
            # This would query the database
            # For now, return mock data
            shipments = []
            
            return {
                "success": True,
                "shipments": shipments,
                "count": len(shipments)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


class UPSShippingProvider:
    """UPS shipping provider implementation."""
    
    def __init__(self):
        self.api_key = settings.UPS_API_KEY
        self.base_url = "https://onlinetools.ups.com/api"
    
    async def get_rates(
        self,
        origin_address: Dict[str, str],
        destination_address: Dict[str, str],
        package_info: Dict[str, Any],
        service_types: List[str]
    ) -> Dict[str, Any]:
        """Get UPS shipping rates."""
        try:
            # Mock UPS API call
            rates = []
            
            for service_type in service_types:
                if service_type == "ground":
                    rates.append({
                        "carrier": "UPS",
                        "service_type": "UPS Ground",
                        "cost": 8.95 + (package_info["weight"] * 0.5),
                        "delivery_days": 3,
                        "available": True
                    })
                elif service_type == "expedited":
                    rates.append({
                        "carrier": "UPS",
                        "service_type": "UPS 2nd Day Air",
                        "cost": 15.95 + (package_info["weight"] * 0.8),
                        "delivery_days": 2,
                        "available": True
                    })
                elif service_type == "overnight":
                    rates.append({
                        "carrier": "UPS",
                        "service_type": "UPS Next Day Air",
                        "cost": 25.95 + (package_info["weight"] * 1.2),
                        "delivery_days": 1,
                        "available": True
                    })
            
            return {"success": True, "rates": rates}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_shipment(
        self,
        service_type: str,
        package_info: Dict[str, Any],
        destination_address: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create UPS shipment."""
        try:
            # Mock UPS shipment creation
            tracking_number = f"1Z{datetime.now().strftime('%Y%m%d%H%M%S')}UPS"
            
            return {
                "success": True,
                "tracking_number": tracking_number,
                "cost": 8.95 + (package_info["weight"] * 0.5),
                "estimated_delivery": (datetime.now() + timedelta(days=3)).isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


class FedExShippingProvider:
    """FedEx shipping provider implementation."""
    
    def __init__(self):
        self.api_key = settings.FEDEX_API_KEY
        self.base_url = "https://api.fedex.com"
    
    async def get_rates(
        self,
        origin_address: Dict[str, str],
        destination_address: Dict[str, str],
        package_info: Dict[str, Any],
        service_types: List[str]
    ) -> Dict[str, Any]:
        """Get FedEx shipping rates."""
        try:
            # Mock FedEx API call
            rates = []
            
            for service_type in service_types:
                if service_type == "ground":
                    rates.append({
                        "carrier": "FedEx",
                        "service_type": "FedEx Ground",
                        "cost": 9.45 + (package_info["weight"] * 0.6),
                        "delivery_days": 3,
                        "available": True
                    })
                elif service_type == "expedited":
                    rates.append({
                        "carrier": "FedEx",
                        "service_type": "FedEx 2Day",
                        "cost": 16.95 + (package_info["weight"] * 0.9),
                        "delivery_days": 2,
                        "available": True
                    })
                elif service_type == "overnight":
                    rates.append({
                        "carrier": "FedEx",
                        "service_type": "FedEx Standard Overnight",
                        "cost": 26.95 + (package_info["weight"] * 1.3),
                        "delivery_days": 1,
                        "available": True
                    })
            
            return {"success": True, "rates": rates}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_shipment(
        self,
        service_type: str,
        package_info: Dict[str, Any],
        destination_address: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create FedEx shipment."""
        try:
            # Mock FedEx shipment creation
            tracking_number = f"1234{datetime.now().strftime('%Y%m%d%H%M%S')}FDX"
            
            return {
                "success": True,
                "tracking_number": tracking_number,
                "cost": 9.45 + (package_info["weight"] * 0.6),
                "estimated_delivery": (datetime.now() + timedelta(days=3)).isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


class USPSShippingProvider:
    """USPS shipping provider implementation."""
    
    def __init__(self):
        self.api_key = settings.USPS_API_KEY
        self.base_url = "https://secure.shippingapis.com"
    
    async def get_rates(
        self,
        origin_address: Dict[str, str],
        destination_address: Dict[str, str],
        package_info: Dict[str, Any],
        service_types: List[str]
    ) -> Dict[str, Any]:
        """Get USPS shipping rates."""
        try:
            # Mock USPS API call
            rates = []
            
            for service_type in service_types:
                if service_type == "ground":
                    rates.append({
                        "carrier": "USPS",
                        "service_type": "USPS Ground Advantage",
                        "cost": 7.95 + (package_info["weight"] * 0.4),
                        "delivery_days": 4,
                        "available": True
                    })
                elif service_type == "expedited":
                    rates.append({
                        "carrier": "USPS",
                        "service_type": "USPS Priority Mail",
                        "cost": 12.95 + (package_info["weight"] * 0.7),
                        "delivery_days": 2,
                        "available": True
                    })
                elif service_type == "overnight":
                    rates.append({
                        "carrier": "USPS",
                        "service_type": "USPS Priority Mail Express",
                        "cost": 24.95 + (package_info["weight"] * 1.1),
                        "delivery_days": 1,
                        "available": True
                    })
            
            return {"success": True, "rates": rates}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_shipment(
        self,
        service_type: str,
        package_info: Dict[str, Any],
        destination_address: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create USPS shipment."""
        try:
            # Mock USPS shipment creation
            tracking_number = f"9400{datetime.now().strftime('%Y%m%d%H%M%S')}US"
            
            return {
                "success": True,
                "tracking_number": tracking_number,
                "cost": 7.95 + (package_info["weight"] * 0.4),
                "estimated_delivery": (datetime.now() + timedelta(days=4)).isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


class DHLShippingProvider:
    """DHL shipping provider implementation."""
    
    def __init__(self):
        self.api_key = settings.DHL_API_KEY
        self.base_url = "https://api-eu.dhl.com"
    
    async def get_rates(
        self,
        origin_address: Dict[str, str],
        destination_address: Dict[str, str],
        package_info: Dict[str, Any],
        service_types: List[str]
    ) -> Dict[str, Any]:
        """Get DHL shipping rates."""
        try:
            # Mock DHL API call
            rates = []
            
            for service_type in service_types:
                if service_type == "ground":
                    rates.append({
                        "carrier": "DHL",
                        "service_type": "DHL Ground",
                        "cost": 10.95 + (package_info["weight"] * 0.7),
                        "delivery_days": 3,
                        "available": True
                    })
                elif service_type == "expedited":
                    rates.append({
                        "carrier": "DHL",
                        "service_type": "DHL Express",
                        "cost": 18.95 + (package_info["weight"] * 1.0),
                        "delivery_days": 2,
                        "available": True
                    })
                elif service_type == "overnight":
                    rates.append({
                        "carrier": "DHL",
                        "service_type": "DHL Same Day",
                        "cost": 28.95 + (package_info["weight"] * 1.5),
                        "delivery_days": 1,
                        "available": True
                    })
            
            return {"success": True, "rates": rates}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_shipment(
        self,
        service_type: str,
        package_info: Dict[str, Any],
        destination_address: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create DHL shipment."""
        try:
            # Mock DHL shipment creation
            tracking_number = f"1234{datetime.now().strftime('%Y%m%d%H%M%S')}DHL"
            
            return {
                "success": True,
                "tracking_number": tracking_number,
                "cost": 10.95 + (package_info["weight"] * 0.7),
                "estimated_delivery": (datetime.now() + timedelta(days=3)).isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
