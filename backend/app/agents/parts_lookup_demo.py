"""
Parts Lookup Agent - Demo Implementation
A working RAG-powered parts lookup system with traffic-light color coding
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
import json
import asyncio
from datetime import datetime

# Mock data - replace with your actual vector store and embeddings
MOCK_INVENTORY = [
    {
        "location": "Chicago North",
        "part": "Brake Pads",
        "vehicle": "2019 Honda Civic",
        "sku": "BP-HC19",
        "stock": 5,
        "price": 45.00,
        "description": "Front brake pads for 2019 Honda Civic, ceramic compound"
    },
    {
        "location": "O'Hare",
        "part": "Alternator",
        "vehicle": "2018 Ford F-150",
        "sku": "ALT-F150",
        "stock": 2,
        "price": 120.00,
        "description": "High-output alternator for 2018 Ford F-150"
    },
    {
        "location": "Chicago South",
        "part": "Oil Filter",
        "vehicle": "2020 Toyota Camry",
        "sku": "OF-TC20",
        "stock": 12,
        "price": 8.50,
        "description": "Premium oil filter for 2020 Toyota Camry"
    },
    {
        "location": "Chicago North",
        "part": "Brake Pads",
        "vehicle": "2018 Honda Civic",
        "sku": "BP-HC18",
        "stock": 0,
        "price": 42.00,
        "description": "Front brake pads for 2018 Honda Civic"
    },
    {
        "location": "O'Hare",
        "part": "Air Filter",
        "vehicle": "2019 Honda Civic",
        "sku": "AF-HC19",
        "stock": 8,
        "price": 15.00,
        "description": "High-flow air filter for 2019 Honda Civic"
    }
]

class PartsQuery(BaseModel):
    text: str
    location_filter: Optional[str] = None
    urgency: str = "normal"  # normal, urgent, critical

class PartsResponse(BaseModel):
    response: str
    color: str
    confidence: float
    suggestions: List[str]
    inventory_matches: List[Dict]
    processing_time_ms: int

class PartsLookupAgent:
    """AI-powered parts lookup agent with RAG capabilities"""
    
    def __init__(self):
        self.inventory = MOCK_INVENTORY
        self.confidence_thresholds = {
            "green": 0.85,  # Auto-resolve
            "yellow": 0.70,  # Human review
            "red": 0.0     # Escalate
        }
    
    def semantic_search(self, query: str, location_filter: Optional[str] = None) -> List[Dict]:
        """Perform semantic search across inventory"""
        query_lower = query.lower()
        matches = []
        
        for item in self.inventory:
            # Skip if location filter doesn't match
            if location_filter and location_filter.lower() not in item["location"].lower():
                continue
                
            # Calculate relevance score based on text matching
            score = 0
            text_fields = [
                item["part"].lower(),
                item["vehicle"].lower(),
                item["description"].lower(),
                item["sku"].lower()
            ]
            
            # Boost score for exact matches
            for field in text_fields:
                if query_lower in field:
                    score += 0.3
                if any(word in field for word in query_lower.split()):
                    score += 0.1
            
            # Boost score for stock availability
            if item["stock"] > 0:
                score += 0.2
            else:
                score -= 0.3  # Penalize out-of-stock
                
            if score > 0:
                item_copy = item.copy()
                item_copy["relevance_score"] = min(score, 1.0)
                matches.append(item_copy)
        
        # Sort by relevance score
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches[:5]  # Return top 5 matches
    
    def determine_color(self, matches: List[Dict], query: str, urgency: str) -> tuple[str, float]:
        """Determine traffic-light color based on confidence and urgency"""
        if not matches:
            return "🔴 Escalate now", 0.0
            
        best_match = matches[0]
        confidence = best_match["relevance_score"]
        
        # Adjust confidence based on urgency
        if urgency == "critical":
            confidence -= 0.1
        elif urgency == "urgent":
            confidence -= 0.05
            
        # Determine color
        if confidence >= self.confidence_thresholds["green"]:
            return "🟢 Auto-resolved", confidence
        elif confidence >= self.confidence_thresholds["yellow"]:
            return "🟡 Human review", confidence
        else:
            return "🔴 Escalate now", confidence
    
    def generate_response(self, matches: List[Dict], color: str, confidence: float, query: str) -> str:
        """Generate human-readable response"""
        if not matches:
            return f"No parts found matching '{query}'. Please check part number or contact supplier sourcing agent."
        
        best_match = matches[0]
        
        if color == "🟢 Auto-resolved":
            return f"Found {best_match['part']} for {best_match['vehicle']} at {best_match['location']}. Stock: {best_match['stock']}, Price: ${best_match['price']:.2f}. Order can be processed automatically."
        elif color == "🟡 Human review":
            return f"Found potential match: {best_match['part']} for {best_match['vehicle']} at {best_match['location']}. Stock: {best_match['stock']}, Price: ${best_match['price']:.2f}. Please verify compatibility before processing."
        else:
            return f"Multiple potential matches found for '{query}'. Manual review required to ensure correct part selection and compatibility."
    
    def generate_suggestions(self, matches: List[Dict], color: str) -> List[str]:
        """Generate actionable suggestions based on results"""
        suggestions = []
        
        if color == "🟢 Auto-resolved":
            suggestions.extend([
                "Generate invoice automatically",
                "Process payment via Stripe",
                "Generate shipping label",
                "Send confirmation email to customer"
            ])
        elif color == "🟡 Human review":
            suggestions.extend([
                "Verify part compatibility",
                "Check customer vehicle details",
                "Confirm pricing and availability",
                "Review before processing order"
            ])
        else:
            suggestions.extend([
                "Contact customer for clarification",
                "Check supplier availability",
                "Escalate to parts specialist",
                "Consider alternative parts"
            ])
        
        # Add stock-specific suggestions
        for match in matches[:2]:  # Top 2 matches
            if match["stock"] == 0:
                suggestions.append(f"Reorder {match['sku']} - out of stock")
            elif match["stock"] < 3:
                suggestions.append(f"Low stock alert: {match['sku']} ({match['stock']} remaining)")
        
        return suggestions
    
    async def lookup_parts(self, query: PartsQuery) -> PartsResponse:
        """Main parts lookup method"""
        start_time = datetime.now()
        
        # Perform semantic search
        matches = self.semantic_search(query.text, query.location_filter)
        
        # Determine color and confidence
        color, confidence = self.determine_color(matches, query.text, query.urgency)
        
        # Generate response and suggestions
        response = self.generate_response(matches, color, confidence, query.text)
        suggestions = self.generate_suggestions(matches, color)
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return PartsResponse(
            response=response,
            color=color,
            confidence=confidence,
            suggestions=suggestions,
            inventory_matches=matches,
            processing_time_ms=processing_time
        )

# Global agent instance
parts_agent = PartsLookupAgent()

async def demo_lookup(query_text: str, location: str = None, urgency: str = "normal") -> Dict:
    """Demo function for testing the parts lookup agent"""
    query = PartsQuery(
        text=query_text,
        location_filter=location,
        urgency=urgency
    )
    
    result = await parts_agent.lookup_parts(query)
    
    return {
        "query": query_text,
        "response": result.response,
        "color": result.color,
        "confidence": f"{result.confidence:.2f}",
        "suggestions": result.suggestions,
        "matches_found": len(result.inventory_matches),
        "processing_time_ms": result.processing_time_ms,
        "inventory_details": result.inventory_matches
    }

# Example usage for testing
if __name__ == "__main__":
    async def test_demo():
        test_queries = [
            "brake pads for 2019 Honda Civic",
            "alternator for Ford F-150",
            "oil filter Toyota Camry",
            "brake pads 2018 Civic",  # This should show out of stock
            "air filter Honda Civic"
        ]
        
        print("🚀 Parts Lookup Agent Demo")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            result = await demo_lookup(query)
            print(f"📋 Response: {result['response']}")
            print(f"🚦 Color: {result['color']}")
            print(f"🎯 Confidence: {result['confidence']}")
            print(f"💡 Suggestions: {', '.join(result['suggestions'][:2])}")
            print(f"⏱️  Processing: {result['processing_time_ms']}ms")
            print("-" * 30)
    
    # Run the test
    asyncio.run(test_demo())
