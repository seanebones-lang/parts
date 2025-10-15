"""
Label service for shipping label generation and management.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings


class LabelService:
    """Service for shipping label generation and management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.label_output_dir = "generated_labels"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.label_output_dir):
            os.makedirs(self.label_output_dir)
    
    async def generate_shipping_label(
        self,
        shipment_id: int,
        service_type: str = "ground"
    ) -> Dict[str, Any]:
        """Generate shipping label for a shipment."""
        try:
            # Get shipment details (this would query the database)
            shipment_data = await self._get_shipment_data(shipment_id)
            
            if not shipment_data:
                return {"success": False, "error": "Shipment not found"}
            
            # Generate label based on carrier
            carrier = shipment_data["carrier"].lower()
            
            if carrier == "ups":
                label_result = await self._generate_ups_label(shipment_data, service_type)
            elif carrier == "fedex":
                label_result = await self._generate_fedex_label(shipment_data, service_type)
            elif carrier == "usps":
                label_result = await self._generate_usps_label(shipment_data, service_type)
            elif carrier == "dhl":
                label_result = await self._generate_dhl_label(shipment_data, service_type)
            else:
                return {"success": False, "error": f"Carrier {carrier} not supported"}
            
            if label_result["success"]:
                # Save label metadata
                await self._save_label_metadata(shipment_id, label_result)
            
            return label_result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_return_label(
        self,
        original_shipment_id: int,
        return_reason: str = "customer_return"
    ) -> Dict[str, Any]:
        """Generate return shipping label."""
        try:
            # Get original shipment data
            original_shipment = await self._get_shipment_data(original_shipment_id)
            
            if not original_shipment:
                return {"success": False, "error": "Original shipment not found"}
            
            # Create return shipment data
            return_shipment = {
                **original_shipment,
                "tracking_number": f"RTN-{original_shipment['tracking_number']}",
                "is_return": True,
                "return_reason": return_reason,
                # Swap origin and destination for return
                "origin_address": original_shipment["destination_address"],
                "destination_address": original_shipment["origin_address"]
            }
            
            # Generate return label
            carrier = return_shipment["carrier"].lower()
            
            if carrier == "ups":
                label_result = await self._generate_ups_label(return_shipment, "ground")
            elif carrier == "fedex":
                label_result = await self._generate_fedex_label(return_shipment, "ground")
            elif carrier == "usps":
                label_result = await self._generate_usps_label(return_shipment, "ground")
            elif carrier == "dhl":
                label_result = await self._generate_dhl_label(return_shipment, "ground")
            else:
                return {"success": False, "error": f"Carrier {carrier} not supported"}
            
            return label_result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_ups_label(
        self,
        shipment_data: Dict[str, Any],
        service_type: str
    ) -> Dict[str, Any]:
        """Generate UPS shipping label."""
        try:
            tracking_number = shipment_data["tracking_number"]
            filename = f"UPS_{tracking_number}.pdf"
            filepath = os.path.join(self.label_output_dir, filename)
            
            # Create PDF label
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # UPS Label Header
            header_style = ParagraphStyle(
                'UPSHeader',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12,
                alignment=1,
                textColor=colors.brown
            )
            
            story.append(Paragraph("UPS SHIPPING LABEL", header_style))
            story.append(Spacer(1, 12))
            
            # Tracking Information
            tracking_info = [
                ["Tracking Number:", tracking_number],
                ["Service:", f"UPS {service_type.title()}"],
                ["Ship Date:", datetime.now().strftime("%Y-%m-%d")],
                ["Reference:", shipment_data.get("order_number", "")]
            ]
            
            tracking_table = Table(tracking_info, colWidths=[2*inch, 4*inch])
            tracking_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(tracking_table)
            story.append(Spacer(1, 20))
            
            # Addresses
            origin = shipment_data.get("origin_address", {})
            destination = shipment_data.get("destination_address", {})
            
            # Origin Address
            story.append(Paragraph("FROM:", styles['Heading3']))
            origin_text = f"{origin.get('name', '')}<br/>{origin.get('address', '')}<br/>{origin.get('city', '')}, {origin.get('state', '')} {origin.get('zip', '')}"
            story.append(Paragraph(origin_text, styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Destination Address
            story.append(Paragraph("TO:", styles['Heading3']))
            dest_text = f"{destination.get('name', '')}<br/>{destination.get('address', '')}<br/>{destination.get('city', '')}, {destination.get('state', '')} {destination.get('zip', '')}"
            story.append(Paragraph(dest_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Package Information
            package_info = shipment_data.get("package_info", {})
            package_data = [
                ["Weight:", f"{package_info.get('weight', 0)} lbs"],
                ["Dimensions:", f"{package_info.get('length', 0)}\" x {package_info.get('width', 0)}\" x {package_info.get('height', 0)}\""],
                ["Items:", f"{package_info.get('item_count', 0)} items"]
            ]
            
            package_table = Table(package_data, colWidths=[1.5*inch, 2*inch])
            package_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(package_table)
            
            # Build PDF
            doc.build(story)
            
            return {
                "success": True,
                "label": {
                    "filepath": filepath,
                    "filename": filename,
                    "tracking_number": tracking_number,
                    "carrier": "UPS",
                    "service_type": service_type,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_fedex_label(
        self,
        shipment_data: Dict[str, Any],
        service_type: str
    ) -> Dict[str, Any]:
        """Generate FedEx shipping label."""
        try:
            tracking_number = shipment_data["tracking_number"]
            filename = f"FEDEX_{tracking_number}.pdf"
            filepath = os.path.join(self.label_output_dir, filename)
            
            # Create PDF label (similar to UPS but with FedEx branding)
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # FedEx Label Header
            header_style = ParagraphStyle(
                'FedExHeader',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12,
                alignment=1,
                textColor=colors.red
            )
            
            story.append(Paragraph("FEDEX SHIPPING LABEL", header_style))
            story.append(Spacer(1, 12))
            
            # Similar structure to UPS label
            # ... (implementation similar to UPS)
            
            # Build PDF
            doc.build(story)
            
            return {
                "success": True,
                "label": {
                    "filepath": filepath,
                    "filename": filename,
                    "tracking_number": tracking_number,
                    "carrier": "FedEx",
                    "service_type": service_type,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_usps_label(
        self,
        shipment_data: Dict[str, Any],
        service_type: str
    ) -> Dict[str, Any]:
        """Generate USPS shipping label."""
        try:
            tracking_number = shipment_data["tracking_number"]
            filename = f"USPS_{tracking_number}.pdf"
            filepath = os.path.join(self.label_output_dir, filename)
            
            # Create PDF label (similar structure with USPS branding)
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # USPS Label Header
            header_style = ParagraphStyle(
                'USPSHeader',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12,
                alignment=1,
                textColor=colors.blue
            )
            
            story.append(Paragraph("USPS SHIPPING LABEL", header_style))
            story.append(Spacer(1, 12))
            
            # Similar structure to other carriers
            # ... (implementation similar to UPS)
            
            # Build PDF
            doc.build(story)
            
            return {
                "success": True,
                "label": {
                    "filepath": filepath,
                    "filename": filename,
                    "tracking_number": tracking_number,
                    "carrier": "USPS",
                    "service_type": service_type,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_dhl_label(
        self,
        shipment_data: Dict[str, Any],
        service_type: str
    ) -> Dict[str, Any]:
        """Generate DHL shipping label."""
        try:
            tracking_number = shipment_data["tracking_number"]
            filename = f"DHL_{tracking_number}.pdf"
            filepath = os.path.join(self.label_output_dir, filename)
            
            # Create PDF label (similar structure with DHL branding)
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # DHL Label Header
            header_style = ParagraphStyle(
                'DHLHeader',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12,
                alignment=1,
                textColor=colors.red
            )
            
            story.append(Paragraph("DHL SHIPPING LABEL", header_style))
            story.append(Spacer(1, 12))
            
            # Similar structure to other carriers
            # ... (implementation similar to UPS)
            
            # Build PDF
            doc.build(story)
            
            return {
                "success": True,
                "label": {
                    "filepath": filepath,
                    "filename": filename,
                    "tracking_number": tracking_number,
                    "carrier": "DHL",
                    "service_type": service_type,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_shipment_data(self, shipment_id: int) -> Optional[Dict[str, Any]]:
        """Get shipment data from database."""
        # This would query the database
        # For now, return mock data
        return {
            "id": shipment_id,
            "tracking_number": f"1Z{datetime.now().strftime('%Y%m%d%H%M%S')}UPS",
            "carrier": "UPS",
            "order_number": f"ORD{shipment_id:06d}",
            "origin_address": {
                "name": "Dealership Parts Dept",
                "address": "123 Main St",
                "city": "Los Angeles",
                "state": "CA",
                "zip": "90210"
            },
            "destination_address": {
                "name": "John Smith",
                "address": "456 Oak Ave",
                "city": "New York",
                "state": "NY",
                "zip": "10001"
            },
            "package_info": {
                "weight": 2.5,
                "length": 8,
                "width": 6,
                "height": 4,
                "item_count": 1
            }
        }
    
    async def _save_label_metadata(
        self,
        shipment_id: int,
        label_result: Dict[str, Any]
    ) -> None:
        """Save label metadata to database."""
        # This would save label information to database
        print(f"Saving label metadata for shipment {shipment_id}")
