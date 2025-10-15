"""
Web scraping service for supplier parts catalogs.
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from bs4 import BeautifulSoup
import re
import json


class ScrapingService:
    """Service for web scraping supplier parts catalogs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session = None
        self.suppliers_config = {
            1: {  # Rock Auto
                "name": "Rock Auto",
                "base_url": "https://www.rockauto.com",
                "search_url": "https://www.rockauto.com/en/catalog/",
                "search_method": "form_submission",
                "selectors": {
                    "search_form": "form[action*='catalog']",
                    "search_input": "input[name='partkeyword']",
                    "results_container": ".searchresults",
                    "part_item": ".searchresult",
                    "part_number": ".partnumber",
                    "part_name": ".partname",
                    "price": ".price",
                    "availability": ".availability"
                }
            },
            2: {  # AutoZone
                "name": "AutoZone",
                "base_url": "https://www.autozone.com",
                "search_url": "https://www.autozone.com/search",
                "search_method": "query_param",
                "selectors": {
                    "results_container": ".search-results",
                    "part_item": ".product-tile",
                    "part_number": ".part-number",
                    "part_name": ".product-title",
                    "price": ".price",
                    "availability": ".availability"
                }
            },
            3: {  # O'Reilly's
                "name": "O'Reilly Auto Parts",
                "base_url": "https://www.oreillyauto.com",
                "search_url": "https://www.oreillyauto.com/search",
                "search_method": "query_param",
                "selectors": {
                    "results_container": ".search-results",
                    "part_item": ".product-tile",
                    "part_number": ".part-number",
                    "part_name": ".product-name",
                    "price": ".price",
                    "availability": ".availability"
                }
            },
            4: {  # NAPA
                "name": "NAPA Auto Parts",
                "base_url": "https://www.napaonline.com",
                "search_url": "https://www.napaonline.com/search",
                "search_method": "query_param",
                "selectors": {
                    "results_container": ".search-results",
                    "part_item": ".product-item",
                    "part_number": ".part-number",
                    "part_name": ".product-title",
                    "price": ".price",
                    "availability": ".stock-status"
                }
            },
            5: {  # CarParts.com
                "name": "CarParts.com",
                "base_url": "https://www.carparts.com",
                "search_url": "https://www.carparts.com/search",
                "search_method": "query_param",
                "selectors": {
                    "results_container": ".search-results",
                    "part_item": ".product-card",
                    "part_number": ".part-number",
                    "part_name": ".product-name",
                    "price": ".price",
                    "availability": ".availability"
                }
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def search_supplier(
        self,
        supplier_id: int,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        vehicle_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Search for parts on a supplier website."""
        try:
            start_time = datetime.now()
            
            if supplier_id not in self.suppliers_config:
                return {"success": False, "error": f"Supplier {supplier_id} not configured"}
            
            supplier_config = self.suppliers_config[supplier_id]
            
            # Build search query
            search_query = self._build_search_query(part_number, part_name, vehicle_info)
            
            # Perform search based on supplier method
            if supplier_config["search_method"] == "query_param":
                results = await self._search_with_query_param(supplier_config, search_query)
            elif supplier_config["search_method"] == "form_submission":
                results = await self._search_with_form_submission(supplier_config, search_query)
            else:
                return {"success": False, "error": f"Unsupported search method: {supplier_config['search_method']}"}
            
            if not results["success"]:
                return results
            
            # Parse results
            parsed_parts = self._parse_search_results(results["html"], supplier_config)
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "parts": parsed_parts,
                "supplier": supplier_config["name"],
                "search_time": search_time,
                "confidence": self._calculate_confidence(parsed_parts, search_query)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def check_availability(
        self,
        supplier_id: int,
        part_number: str
    ) -> Dict[str, Any]:
        """Check real-time availability for a specific part."""
        try:
            if supplier_id not in self.suppliers_config:
                return {"success": False, "error": f"Supplier {supplier_id} not configured"}
            
            supplier_config = self.suppliers_config[supplier_id]
            
            # Build direct part URL
            part_url = self._build_part_url(supplier_config, part_number)
            
            # Fetch part page
            async with self.session.get(part_url) as response:
                if response.status != 200:
                    return {"success": False, "error": f"Failed to fetch part page: {response.status}"}
                
                html = await response.text()
            
            # Parse availability information
            availability_data = self._parse_availability(html, supplier_config)
            
            return {
                "success": True,
                "availability": availability_data,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def place_supplier_order(
        self,
        supplier_id: int,
        parts: List[Dict[str, Any]],
        customer_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Place order with supplier (if automated ordering is supported)."""
        try:
            if supplier_id not in self.suppliers_config:
                return {"success": False, "error": f"Supplier {supplier_id} not configured"}
            
            supplier_config = self.suppliers_config[supplier_id]
            
            # Check if supplier supports automated ordering
            if not supplier_config.get("supports_automated_ordering", False):
                return {
                    "success": False,
                    "error": "Automated ordering not supported for this supplier",
                    "manual_order_required": True
                }
            
            # Mock order placement (in real implementation, this would use supplier APIs)
            order_data = {
                "order_number": f"SO-{supplier_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "supplier_id": supplier_id,
                "supplier_name": supplier_config["name"],
                "parts": parts,
                "customer_info": customer_info,
                "order_date": datetime.now().isoformat(),
                "status": "pending",
                "estimated_delivery": (datetime.now() + timedelta(days=supplier_config.get("delivery_time_days", 5))).isoformat()
            }
            
            return {
                "success": True,
                "order": order_data,
                "message": f"Order placed with {supplier_config['name']}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def update_supplier_data(
        self,
        supplier_id: int,
        update_type: str = "full"
    ) -> Dict[str, Any]:
        """Update supplier catalog data."""
        try:
            if supplier_id not in self.suppliers_config:
                return {"success": False, "error": f"Supplier {supplier_id} not configured"}
            
            supplier_config = self.suppliers_config[supplier_id]
            
            if update_type == "full":
                # Full catalog scrape
                parts = await self._scrape_full_catalog(supplier_config)
            elif update_type == "pricing":
                # Update pricing only
                parts = await self._update_pricing_data(supplier_config)
            elif update_type == "availability":
                # Update availability only
                parts = await self._update_availability_data(supplier_config)
            else:
                return {"success": False, "error": f"Unsupported update type: {update_type}"}
            
            return {
                "success": True,
                "parts_updated": len(parts),
                "update_type": update_type,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def scrape_supplier_catalog(
        self,
        supplier_id: int,
        category: Optional[str] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """Scrape supplier catalog for new parts."""
        try:
            if supplier_id not in self.suppliers_config:
                return {"success": False, "error": f"Supplier {supplier_id} not configured"}
            
            supplier_config = self.suppliers_config[supplier_id]
            
            # Scrape catalog
            parts = await self._scrape_catalog_category(supplier_config, category, limit)
            
            return {
                "success": True,
                "parts": parts,
                "category": category,
                "limit": limit,
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _build_search_query(
        self,
        part_number: Optional[str],
        part_name: Optional[str],
        vehicle_info: Optional[Dict[str, str]]
    ) -> str:
        """Build search query from part information."""
        query_parts = []
        
        if part_number:
            query_parts.append(part_number)
        
        if part_name:
            query_parts.append(part_name)
        
        if vehicle_info:
            make = vehicle_info.get("make", "")
            model = vehicle_info.get("model", "")
            year = vehicle_info.get("year", "")
            
            if make:
                query_parts.append(make)
            if model:
                query_parts.append(model)
            if year:
                query_parts.append(year)
        
        return " ".join(query_parts)
    
    async def _search_with_query_param(
        self,
        supplier_config: Dict[str, Any],
        search_query: str
    ) -> Dict[str, Any]:
        """Search using query parameter method."""
        try:
            search_url = f"{supplier_config['search_url']}?q={search_query}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    return {"success": False, "error": f"Search failed: {response.status}"}
                
                html = await response.text()
                
                return {"success": True, "html": html}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _search_with_form_submission(
        self,
        supplier_config: Dict[str, Any],
        search_query: str
    ) -> Dict[str, Any]:
        """Search using form submission method."""
        try:
            # First, get the search form
            async with self.session.get(supplier_config["base_url"]) as response:
                if response.status != 200:
                    return {"success": False, "error": f"Failed to load search page: {response.status}"}
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find and submit the search form
                form = soup.find('form', {'action': lambda x: x and 'catalog' in x})
                if not form:
                    return {"success": False, "error": "Search form not found"}
                
                form_data = {
                    'partkeyword': search_query
                }
                
                # Submit the form
                form_action = form.get('action', supplier_config["search_url"])
                if not form_action.startswith('http'):
                    form_action = supplier_config["base_url"] + form_action
                
                async with self.session.post(form_action, data=form_data) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"Form submission failed: {response.status}"}
                    
                    html = await response.text()
                    return {"success": True, "html": html}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_search_results(self, html: str, supplier_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse search results HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            parts = []
            
            selectors = supplier_config["selectors"]
            
            # Find results container
            results_container = soup.select_one(selectors.get("results_container", ""))
            if not results_container:
                return parts
            
            # Find individual part items
            part_items = results_container.select(selectors.get("part_item", ""))
            
            for item in part_items[:20]:  # Limit to first 20 results
                try:
                    part_data = self._extract_part_data(item, selectors)
                    if part_data:
                        parts.append(part_data)
                except Exception as e:
                    print(f"Error parsing part item: {e}")
                    continue
            
            return parts
            
        except Exception as e:
            print(f"Error parsing search results: {e}")
            return []
    
    def _extract_part_data(self, item_element, selectors: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract part data from HTML element."""
        try:
            part_data = {}
            
            # Extract part number
            part_number_elem = item_element.select_one(selectors.get("part_number", ""))
            if part_number_elem:
                part_data["supplier_part_number"] = part_number_elem.get_text(strip=True)
            
            # Extract part name
            part_name_elem = item_element.select_one(selectors.get("part_name", ""))
            if part_name_elem:
                part_data["part_name"] = part_name_elem.get_text(strip=True)
            
            # Extract price
            price_elem = item_element.select_one(selectors.get("price", ""))
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'\$?(\d+\.?\d*)', price_text)
                if price_match:
                    part_data["price"] = float(price_match.group(1))
            
            # Extract availability
            availability_elem = item_element.select_one(selectors.get("availability", ""))
            if availability_elem:
                availability_text = availability_elem.get_text(strip=True).lower()
                if "in stock" in availability_text or "available" in availability_text:
                    part_data["availability"] = "in_stock"
                elif "out of stock" in availability_text or "unavailable" in availability_text:
                    part_data["availability"] = "out_of_stock"
                else:
                    part_data["availability"] = "limited"
            else:
                part_data["availability"] = "unknown"
            
            # Default values
            part_data["delivery_days"] = 3  # Default delivery time
            part_data["minimum_quantity"] = 1
            
            # Only return if we have essential data
            if part_data.get("supplier_part_number") or part_data.get("part_name"):
                return part_data
            
            return None
            
        except Exception as e:
            print(f"Error extracting part data: {e}")
            return None
    
    def _build_part_url(self, supplier_config: Dict[str, Any], part_number: str) -> str:
        """Build direct URL to part page."""
        # This would be customized per supplier
        base_url = supplier_config["base_url"]
        return f"{base_url}/parts/{part_number}"
    
    def _parse_availability(self, html: str, supplier_config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse availability information from part page."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for availability indicators
            availability_text = ""
            price = None
            delivery_days = 3
            
            # Try to find price
            price_elements = soup.find_all(text=re.compile(r'\$[\d,]+\.?\d*'))
            if price_elements:
                price_match = re.search(r'\$?(\d+\.?\d*)', price_elements[0])
                if price_match:
                    price = float(price_match.group(1))
            
            # Try to find availability
            availability_elements = soup.find_all(text=re.compile(r'(in stock|out of stock|available|unavailable)', re.I))
            if availability_elements:
                availability_text = availability_elements[0].lower()
            
            # Determine availability status
            if "in stock" in availability_text or "available" in availability_text:
                availability = "in_stock"
            elif "out of stock" in availability_text or "unavailable" in availability_text:
                availability = "out_of_stock"
            else:
                availability = "unknown"
            
            return {
                "availability": availability,
                "price": price,
                "delivery_days": delivery_days,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error parsing availability: {e}")
            return {
                "availability": "unknown",
                "price": None,
                "delivery_days": 3,
                "checked_at": datetime.now().isoformat()
            }
    
    def _calculate_confidence(self, parts: List[Dict[str, Any]], search_query: str) -> float:
        """Calculate confidence score for search results."""
        if not parts:
            return 0.0
        
        # Base confidence on number of results and data completeness
        base_confidence = min(len(parts) / 5, 1.0)  # Max confidence at 5+ results
        
        # Boost confidence if results have good data
        complete_results = sum(1 for part in parts if part.get("price") and part.get("availability") != "unknown")
        data_confidence = complete_results / len(parts) if parts else 0
        
        return (base_confidence + data_confidence) / 2
    
    async def _scrape_full_catalog(self, supplier_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape full supplier catalog (mock implementation)."""
        # This would be a complex implementation that crawls the entire catalog
        # For now, return mock data
        return []
    
    async def _update_pricing_data(self, supplier_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update pricing data only (mock implementation)."""
        # This would update only pricing information
        return []
    
    async def _update_availability_data(self, supplier_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update availability data only (mock implementation)."""
        # This would update only availability information
        return []
    
    async def _scrape_catalog_category(
        self,
        supplier_config: Dict[str, Any],
        category: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Scrape specific category from catalog (mock implementation)."""
        # This would scrape a specific category
        return []
