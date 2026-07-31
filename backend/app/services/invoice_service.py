"""
Invoice service for generating PDF invoices and managing invoice operations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    letter = None  # type: ignore
    SimpleDocTemplate = Paragraph = Spacer = Table = TableStyle = None  # type: ignore
    getSampleStyleSheet = ParagraphStyle = None  # type: ignore
    inch = None  # type: ignore
    colors = None  # type: ignore
    REPORTLAB_AVAILABLE = False


class InvoiceService:
    """Service for invoice generation and management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pdf_output_dir = "generated_invoices"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.pdf_output_dir):
            os.makedirs(self.pdf_output_dir)
    
    async def generate_invoice_pdf(self, invoice_data: Dict[str, Any]) -> str:
        """Generate PDF invoice."""
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError(
                "reportlab is not installed. pip install reportlab to enable PDF invoices."
            )
        try:
            invoice_number = invoice_data.get("invoice_number", f"INV-{uuid.uuid4().hex[:8].upper()}")
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.pdf_output_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            
            story.append(Paragraph("INVOICE", title_style))
            story.append(Spacer(1, 12))
            
            # Invoice details
            invoice_details = [
                ["Invoice Number:", invoice_number],
                ["Date:", datetime.now().strftime("%Y-%m-%d")],
                ["Due Date:", invoice_data.get("due_date", "30 days")],
                ["Status:", invoice_data.get("status", "Draft")]
            ]
            
            invoice_table = Table(invoice_details, colWidths=[2*inch, 3*inch])
            invoice_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(invoice_table)
            story.append(Spacer(1, 20))
            
            # Customer information
            customer_info = invoice_data.get("customer_info", {})
            story.append(Paragraph("Bill To:", styles['Heading3']))
            
            customer_details = [
                customer_info.get("name", "Customer Name"),
                customer_info.get("address", "Address"),
                customer_info.get("city", "City") + ", " + customer_info.get("state", "State") + " " + customer_info.get("zip", "Zip"),
                customer_info.get("phone", "Phone"),
                customer_info.get("email", "Email")
            ]
            
            for detail in customer_details:
                if detail:
                    story.append(Paragraph(detail, styles['Normal']))
            
            story.append(Spacer(1, 20))
            
            # Items table
            story.append(Paragraph("Items:", styles['Heading3']))
            
            items = invoice_data.get("items", [])
            items_data = [["Part Number", "Description", "Qty", "Unit Price", "Total"]]
            
            for item in items:
                items_data.append([
                    item.get("part_number", ""),
                    item.get("part_name", ""),
                    str(item.get("quantity", 0)),
                    f"${item.get('unit_price', 0):.2f}",
                    f"${item.get('line_total', 0):.2f}"
                ])
            
            items_table = Table(items_data, colWidths=[1.2*inch, 2.5*inch, 0.6*inch, 1*inch, 1*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 20))
            
            # Totals
            pricing = invoice_data.get("pricing", {})
            totals_data = [
                ["Subtotal:", f"${pricing.get('subtotal', 0):.2f}"],
                ["Tax:", f"${pricing.get('tax_amount', 0):.2f}"],
                ["Shipping:", f"${pricing.get('shipping_cost', 0):.2f}"],
                ["", ""],
                ["Total:", f"${pricing.get('total_amount', 0):.2f}"]
            ]
            
            totals_table = Table(totals_data, colWidths=[2*inch, 1*inch])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -2), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
                ('FONTNAME', (1, 0), (1, -2), 'Helvetica'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
                ('LINEBELOW', (0, -2), (-1, -2), 1, colors.black),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
            ]))
            
            story.append(totals_table)
            story.append(Spacer(1, 30))
            
            # Terms and conditions
            story.append(Paragraph("Terms and Conditions:", styles['Heading3']))
            terms = [
                "Payment is due within 30 days of invoice date.",
                "Late payments may be subject to a 1.5% monthly service charge.",
                "All sales are final. Returns subject to approval.",
                "Prices are subject to change without notice."
            ]
            
            for term in terms:
                story.append(Paragraph(f"• {term}", styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            return filepath
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            raise
    
    async def generate_quote_number(self, location_id: int) -> str:
        """Generate unique quote number."""
        # Generate quote number with location prefix and timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        location_prefix = f"L{location_id:02d}"
        quote_number = f"Q{location_prefix}-{timestamp}"
        
        return quote_number
    
    async def generate_invoice_number(self, location_id: int) -> str:
        """Generate unique invoice number."""
        # Generate invoice number with location prefix and timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        location_prefix = f"L{location_id:02d}"
        invoice_number = f"INV{location_prefix}-{timestamp}"
        
        return invoice_number
    
    async def send_invoice_email(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send invoice email to customer."""
        try:
            # This would integrate with email service
            # For now, return success status
            
            customer_email = invoice_data.get("customer_info", {}).get("email")
            invoice_number = invoice_data.get("invoice_number")
            pdf_path = invoice_data.get("pdf_path")
            
            if not customer_email:
                return {
                    "success": False,
                    "error": "Customer email not found"
                }
            
            # Mock email sending
            print(f"Sending invoice {invoice_number} to {customer_email}")
            print(f"PDF attached: {pdf_path}")
            
            return {
                "success": True,
                "email_sent_to": customer_email,
                "invoice_number": invoice_number,
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_invoice_status(self, invoice_number: str) -> Dict[str, Any]:
        """Get invoice status and payment information."""
        # This would query the database for invoice status
        # For now, return mock data
        
        return {
            "invoice_number": invoice_number,
            "status": "sent",
            "amount": 1250.00,
            "paid_amount": 0.00,
            "balance_due": 1250.00,
            "due_date": "2024-12-15",
            "created_at": "2024-11-15T10:30:00Z",
            "last_payment": None
        }
    
    async def record_payment(
        self,
        invoice_number: str,
        payment_amount: float,
        payment_method: str,
        payment_reference: str
    ) -> Dict[str, Any]:
        """Record payment against invoice."""
        try:
            # This would update the database with payment information
            # For now, return success status
            
            return {
                "success": True,
                "invoice_number": invoice_number,
                "payment_amount": payment_amount,
                "payment_method": payment_method,
                "payment_reference": payment_reference,
                "payment_date": datetime.now().isoformat(),
                "remaining_balance": max(0, 1250.00 - payment_amount)  # Mock remaining balance
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_receipt_pdf(
        self,
        payment_data: Dict[str, Any]
    ) -> str:
        """Generate payment receipt PDF."""
        try:
            receipt_number = f"RCP-{uuid.uuid4().hex[:8].upper()}"
            filename = f"{receipt_number}.pdf"
            filepath = os.path.join(self.pdf_output_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'ReceiptTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1
            )
            
            story.append(Paragraph("PAYMENT RECEIPT", title_style))
            story.append(Spacer(1, 12))
            
            # Receipt details
            receipt_details = [
                ["Receipt Number:", receipt_number],
                ["Payment Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Invoice Number:", payment_data.get("invoice_number", "")],
                ["Payment Method:", payment_data.get("payment_method", "")],
                ["Payment Reference:", payment_data.get("payment_reference", "")]
            ]
            
            receipt_table = Table(receipt_details, colWidths=[2*inch, 3*inch])
            receipt_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(receipt_table)
            story.append(Spacer(1, 20))
            
            # Payment amount
            amount_style = ParagraphStyle(
                'Amount',
                parent=styles['Heading2'],
                fontSize=16,
                alignment=1
            )
            
            story.append(Paragraph(f"Amount Paid: ${payment_data.get('payment_amount', 0):.2f}", amount_style))
            story.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(story)
            
            return filepath
            
        except Exception as e:
            print(f"Error generating receipt PDF: {e}")
            raise
