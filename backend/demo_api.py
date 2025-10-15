"""
Demo API Endpoint for Parts Lookup Agent
FastAPI endpoint showcasing the AI-powered parts lookup system
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
from datetime import datetime
import uvicorn

from app.agents.parts_lookup_demo import PartsQuery, PartsLookupAgent

# Create FastAPI app for demo
demo_app = FastAPI(
    title="Parts Lookup Demo API",
    description="AI-powered parts lookup system with traffic-light color coding",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize the parts lookup agent
parts_agent = PartsLookupAgent()

class DemoQuery(BaseModel):
    text: str
    location_filter: Optional[str] = None
    urgency: str = "normal"

class DemoResponse(BaseModel):
    success: bool
    query: str
    response: str
    color: str
    confidence: float
    suggestions: List[str]
    inventory_matches: List[Dict]
    processing_time_ms: int
    timestamp: str
    system_status: str

@demo_app.get("/")
async def root():
    """Root endpoint with demo information"""
    return {
        "message": "🚀 Parts Lookup Demo API - AI-Powered Dealership Parts Management",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Semantic parts search across multiple locations",
            "Traffic-light color coding (🟢🟡🔴)",
            "Real-time inventory checking",
            "Automated suggestions and workflows",
            "Confidence scoring and escalation"
        ],
        "demo_endpoints": {
            "POST /query_parts": "Main parts lookup endpoint",
            "GET /demo_scenarios": "Pre-built demo scenarios",
            "GET /inventory": "View current inventory",
            "GET /docs": "Interactive API documentation"
        }
    }

@demo_app.post("/query_parts", response_model=DemoResponse)
async def query_parts(query: DemoQuery):
    """
    Main parts lookup endpoint with traffic-light color coding
    
    This endpoint demonstrates the AI-powered parts lookup system:
    - 🟢 Auto-resolved (95%+ confidence): Process automatically
    - 🟡 Human review (70-95% confidence): Flag for review
    - 🔴 Escalate now (<70% confidence): Manual intervention required
    """
    try:
        # Convert to internal query format
        parts_query = PartsQuery(
            text=query.text,
            location_filter=query.location_filter,
            urgency=query.urgency
        )
        
        # Perform parts lookup
        result = await parts_agent.lookup_parts(parts_query)
        
        return DemoResponse(
            success=True,
            query=query.text,
            response=result.response,
            color=result.color,
            confidence=result.confidence,
            suggestions=result.suggestions,
            inventory_matches=result.inventory_matches,
            processing_time_ms=result.processing_time_ms,
            timestamp=datetime.now().isoformat(),
            system_status="operational"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parts lookup failed: {str(e)}")

@demo_app.get("/demo_scenarios")
async def get_demo_scenarios():
    """Get pre-built demo scenarios for presentation"""
    scenarios = [
        {
            "name": "Perfect Match - Auto Process",
            "description": "High confidence match with stock available",
            "query": "brake pads for 2019 Honda Civic",
            "expected_color": "🟢 Auto-resolved",
            "use_case": "Customer needs brake pads, system finds exact match with stock"
        },
        {
            "name": "Low Stock Alert",
            "description": "Match found but low stock requires attention",
            "query": "alternator for 2018 Ford F-150",
            "expected_color": "🟡 Human review",
            "use_case": "Part found but only 2 in stock - needs reorder"
        },
        {
            "name": "Out of Stock",
            "description": "Part found but no stock available",
            "query": "brake pads for 2018 Honda Civic",
            "expected_color": "🔴 Escalate now",
            "use_case": "Customer needs part but it's out of stock - needs sourcing"
        },
        {
            "name": "Ambiguous Query",
            "description": "Multiple potential matches require clarification",
            "query": "air filter Honda",
            "expected_color": "🟡 Human review",
            "use_case": "Multiple Honda models - need to clarify specific vehicle"
        },
        {
            "name": "Location-Specific Search",
            "description": "Search within specific location",
            "query": "oil filter Toyota Camry",
            "location_filter": "Chicago South",
            "expected_color": "🟢 Auto-resolved",
            "use_case": "Customer at specific location needs part"
        }
    ]
    
    return {
        "scenarios": scenarios,
        "total_scenarios": len(scenarios),
        "usage": "Use these scenarios to demonstrate different system behaviors during your presentation"
    }

@demo_app.get("/inventory")
async def get_inventory():
    """Get current inventory status"""
    inventory_summary = {}
    
    for item in parts_agent.inventory:
        location = item["location"]
        if location not in inventory_summary:
            inventory_summary[location] = {
                "total_parts": 0,
                "in_stock": 0,
                "low_stock": 0,
                "out_of_stock": 0,
                "parts": []
            }
        
        inventory_summary[location]["total_parts"] += 1
        inventory_summary[location]["parts"].append({
            "part": item["part"],
            "vehicle": item["vehicle"],
            "sku": item["sku"],
            "stock": item["stock"],
            "price": item["price"],
            "status": "in_stock" if item["stock"] > 3 else "low_stock" if item["stock"] > 0 else "out_of_stock"
        })
        
        if item["stock"] > 3:
            inventory_summary[location]["in_stock"] += 1
        elif item["stock"] > 0:
            inventory_summary[location]["low_stock"] += 1
        else:
            inventory_summary[location]["out_of_stock"] += 1
    
    return {
        "inventory_summary": inventory_summary,
        "total_locations": len(inventory_summary),
        "last_updated": datetime.now().isoformat()
    }

@demo_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ai_agent": "operational",
        "inventory_system": "connected",
        "color_coding": "active",
        "timestamp": datetime.now().isoformat()
    }

@demo_app.post("/bulk_demo")
async def bulk_demo():
    """Run multiple demo queries to showcase system capabilities"""
    demo_queries = [
        {"text": "brake pads for 2019 Honda Civic", "urgency": "normal"},
        {"text": "alternator for 2018 Ford F-150", "urgency": "urgent"},
        {"text": "oil filter Toyota Camry", "location_filter": "Chicago South"},
        {"text": "brake pads 2018 Civic", "urgency": "critical"},
        {"text": "air filter Honda Civic", "urgency": "normal"}
    ]
    
    results = []
    for query_data in demo_queries:
        query = DemoQuery(**query_data)
        result = await query_parts(query)
        results.append({
            "query": result.query,
            "color": result.color,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms
        })
    
    return {
        "bulk_demo_results": results,
        "total_queries": len(results),
        "success_rate": f"{len([r for r in results if r['confidence'] > 0.7]) / len(results) * 100:.1f}%",
        "average_processing_time": f"{sum(r['processing_time_ms'] for r in results) / len(results):.1f}ms"
    }

if __name__ == "__main__":
    print("🚀 Starting Parts Lookup Demo API...")
    print("📋 Available endpoints:")
    print("  - POST /query_parts - Main parts lookup")
    print("  - GET /demo_scenarios - Pre-built scenarios")
    print("  - GET /inventory - Current inventory")
    print("  - POST /bulk_demo - Run multiple demos")
    print("  - GET /docs - Interactive documentation")
    print("\n🎯 Demo ready for Thursday presentation!")
    
    uvicorn.run(
        demo_app,
        host="0.0.0.0",
        port=8001,  # Different port to avoid conflicts
        reload=True,
        log_level="info"
    )
