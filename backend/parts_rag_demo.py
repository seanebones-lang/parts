"""
Enhanced Parts RAG Demo - Lester's Version
FastAPI endpoint with LangChain integration, logging, and mobile polish
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import asyncio
from datetime import datetime
import uvicorn

# LangChain imports
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain.llms import HuggingFaceHub

# Import our custom modules
import sys
sys.path.append('..')
from data_loader import load_vectorstore_from_disk, get_inventory_summary
from logger import log_query, log_error, log_performance, log_demo_start, log_demo_end, get_session_summary
from email_mock import EmailProcessor, fetch_mock_emails, process_email, get_email_stats

# For production, swap to Anthropic
# from anthropic import Anthropic

app = FastAPI(
    title="Parts RAG Demo - Lester's Edition",
    description="AI-powered parts lookup with traffic-light color coding",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced inventory docs with more realistic data
inventory_docs = [
    Document(page_content="Location: Chicago North - Brake Pads (2019 Honda Civic): In stock 5, SKU: BP-HC19, Price: $45, Description: Ceramic brake pads for front wheels"),
    Document(page_content="Location: O'Hare - Alternator (2018 Ford F-150): Low stock 2, SKU: ALT-F150, Price: $120, Description: High-output alternator 150A"),
    Document(page_content="Location: Chicago South - Oil Filter (2020 Toyota Camry): In stock 12, SKU: OF-TC20, Price: $8.50, Description: Premium oil filter"),
    Document(page_content="Location: Chicago North - Brake Pads (2018 Honda Civic): Out of stock 0, SKU: BP-HC18, Price: $42, Description: Front brake pads ceramic"),
    Document(page_content="Location: O'Hare - Air Filter (2019 Honda Civic): In stock 8, SKU: AF-HC19, Price: $15, Description: High-flow air filter"),
    Document(page_content="Location: Chicago South - Spark Plugs (2020 Toyota Camry): In stock 24, SKU: SP-TC20, Price: $12, Description: Iridium spark plugs set of 4"),
    Document(page_content="Location: Chicago North - Timing Belt (2019 Honda Civic): Low stock 1, SKU: TB-HC19, Price: $85, Description: OEM timing belt kit"),
    Document(page_content="Location: O'Hare - Water Pump (2018 Ford F-150): In stock 3, SKU: WP-F150, Price: $95, Description: Heavy-duty water pump"),
]

# Initialize RAG system with Lester's data loader
try:
    print("🚀 Initializing Lester's Parts RAG System...")
    
    # Load vector store from disk or build new one
    vectorstore = load_vectorstore_from_disk()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    # Use HuggingFace Hub for demo (swap to Anthropic for production)
    llm = HuggingFaceHub(repo_id="gpt2", model_kwargs={"temperature": 0.5})
    
    # Production Claude setup (commented out for demo)
    # llm = Anthropic(model="claude-3-5-sonnet")
    
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    
    # Initialize email processor with RAG system
    email_processor = EmailProcessor(vectorstore=vectorstore, qa_chain=qa_chain)
    
    print("✅ RAG system initialized with realistic dealership data")
    print("✅ Email processor initialized with RAG integration")
    
except Exception as e:
    print(f"⚠️ RAG initialization failed: {e}")
    print("🔄 Falling back to mock responses")
    qa_chain = None
    vectorstore = None
    retriever = None
    
    # Initialize email processor in fallback mode
    email_processor = EmailProcessor()

class Query(BaseModel):
    text: str
    location_filter: Optional[str] = None
    urgency: str = "normal"

class EnhancedResponse(BaseModel):
    success: bool
    query: str
    response: str
    color: str
    confidence: float
    suggestions: List[str]
    processing_time_ms: int
    timestamp: str
    inventory_matches: List[Dict]
    # Mobile/Web UI enhancements
    ui_hint: str
    color_emoji: str
    priority: str
    action_required: bool
    next_steps: List[str]

def calculate_confidence_score(query_text: str, retrieved_docs: List[Document]) -> float:
    """Calculate confidence score based on query relevance"""
    if not retrieved_docs:
        return 0.0
    
    query_lower = query_text.lower()
    total_score = 0
    
    for doc in retrieved_docs:
        content_lower = doc.page_content.lower()
        
        # Exact phrase match gets highest score
        if query_lower in content_lower:
            total_score += 0.4
        else:
            # Word overlap scoring
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            overlap = len(query_words.intersection(content_words))
            total_score += (overlap / len(query_words)) * 0.3
        
        # Stock availability bonus
        if "in stock" in content_lower and "0" not in content_lower:
            total_score += 0.2
        elif "low stock" in content_lower:
            total_score += 0.1
        else:
            total_score -= 0.3  # Penalty for out of stock
    
    return min(total_score / len(retrieved_docs), 1.0)

def determine_traffic_light(confidence: float, urgency: str) -> tuple[str, List[str], Dict[str, Any]]:
    """Determine traffic light color and generate mobile-friendly UI hints"""
    
    # Adjust thresholds based on urgency
    if urgency == "critical":
        green_threshold = 0.9
        yellow_threshold = 0.7
    elif urgency == "urgent":
        green_threshold = 0.85
        yellow_threshold = 0.65
    else:
        green_threshold = 0.8
        yellow_threshold = 0.5
    
    if confidence >= green_threshold:
        color = "🟢 Auto-resolved"
        suggestions = [
            "Generate invoice automatically",
            "Process payment via Stripe",
            "Generate shipping label",
            "Send confirmation email"
        ]
        ui_hint = "display-success"
        color_emoji = "🟢"
        priority = "low"
        action_required = False
        next_steps = ["Process order", "Send confirmation"]
    elif confidence >= yellow_threshold:
        color = "🟡 Human review"
        suggestions = [
            "Verify part compatibility",
            "Check customer vehicle details",
            "Confirm pricing and availability",
            "Review before processing"
        ]
        ui_hint = "display-warning"
        color_emoji = "🟡"
        priority = "medium"
        action_required = True
        next_steps = ["Review details", "Confirm with customer"]
    else:
        color = "🔴 Escalate now"
        suggestions = [
            "Contact customer for clarification",
            "Check supplier availability",
            "Escalate to parts specialist",
            "Consider alternative parts"
        ]
        ui_hint = "display-alert"
        color_emoji = "🔴"
        priority = "high"
        action_required = True
        next_steps = ["Escalate immediately", "Contact specialist"]
    
    mobile_hints = {
        "ui_hint": ui_hint,
        "color_emoji": color_emoji,
        "priority": priority,
        "action_required": action_required,
        "next_steps": next_steps
    }
    
    return color, suggestions, mobile_hints

@app.post("/query_parts", response_model=EnhancedResponse)
async def query_parts(query: Query):
    """
    Enhanced parts lookup with RAG and traffic-light color coding
    
    🟢 Auto-resolved (80%+ confidence): Process automatically
    🟡 Human review (50-80% confidence): Flag for review  
    🔴 Escalate now (<50% confidence): Manual intervention
    """
    start_time = datetime.now()
    
    try:
        if qa_chain is None:
            # Fallback mock response
            return EnhancedResponse(
                success=True,
                query=query.text,
                response=f"Mock response for '{query.text}' - RAG system not initialized",
                color="🟡 Human review",
                confidence=0.6,
                suggestions=["Initialize RAG system", "Check embeddings", "Verify LLM connection"],
                processing_time_ms=50,
                timestamp=datetime.now().isoformat(),
                inventory_matches=[]
            )
        
        # Build enhanced prompt
        location_context = f" at {query.location_filter}" if query.location_filter else " across all locations"
        urgency_context = f" (URGENT)" if query.urgency in ["urgent", "critical"] else ""
        
        prompt = f"""You are a parts expert for Chicago dealerships{urgency_context}. 
        
        Customer query: '{query.text}'
        Search scope: {query.location_filter or 'All locations'}
        
        Instructions:
        1. Find the best matching parts{location_context}
        2. Check stock availability and pricing
        3. Provide specific recommendations
        4. Include SKU, location, stock level, and price
        
        Format your response clearly with specific part details."""
        
        # Get RAG response with error handling
        try:
            result = qa_chain.run(prompt)
            retrieved_docs = retriever.get_relevant_documents(query.text)
            confidence = calculate_confidence_score(query.text, retrieved_docs)
        except Exception as e:
            # Fallback response if RAG fails
            result = f"Fallback response for: {query.text}. RAG system temporarily unavailable."
            retrieved_docs = []
            confidence = 0.5  # Medium confidence for fallback
            log_error(query.text, f"RAG processing failed: {str(e)}")
        
        # Determine traffic light color, suggestions, and mobile hints
        color, suggestions, mobile_hints = determine_traffic_light(confidence, query.urgency)
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Format inventory matches
        inventory_matches = []
        for doc in retrieved_docs[:3]:  # Top 3 matches
            inventory_matches.append({
                "content": doc.page_content,
                "relevance_score": confidence,
                "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
            })
        
        # Prepare result for logging
        result_data = {
            "response": result,
            "confidence": confidence,
            "suggestions": suggestions,
            "inventory_matches": inventory_matches
        }
        
        # Log the query
        log_query(query.text, result_data, color, processing_time)
        
        return EnhancedResponse(
            success=True,
            query=query.text,
            response=result,
            color=color,
            confidence=confidence,
            suggestions=suggestions,
            processing_time_ms=processing_time,
            timestamp=datetime.now().isoformat(),
            inventory_matches=inventory_matches,
            # Mobile/Web UI enhancements
            ui_hint=mobile_hints["ui_hint"],
            color_emoji=mobile_hints["color_emoji"],
            priority=mobile_hints["priority"],
            action_required=mobile_hints["action_required"],
            next_steps=mobile_hints["next_steps"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parts lookup failed: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with system status"""
    return {
        "message": "🚀 Parts RAG Demo - Lester's Edition",
        "version": "1.0.0",
        "status": "operational",
        "rag_system": "active" if qa_chain else "fallback_mode",
        "features": [
            "Semantic parts search with LangChain",
            "Traffic-light color coding (🟢🟡🔴)",
            "Confidence scoring and escalation",
            "Multi-location inventory checking",
            "Automated workflow suggestions"
        ],
        "demo_endpoints": {
            "POST /query_parts": "Main parts lookup with RAG",
            "GET /demo_scenarios": "Pre-built demo scenarios",
            "GET /inventory": "Current inventory overview",
            "GET /docs": "Interactive API documentation"
        }
    }

@app.get("/demo_scenarios")
async def get_demo_scenarios():
    """Pre-built demo scenarios for Thursday presentation"""
    scenarios = [
        {
            "name": "Perfect Match - Auto Process",
            "query": {"text": "brake pads for 2019 Honda Civic", "urgency": "normal"},
            "expected_color": "🟢 Auto-resolved",
            "description": "High confidence match with stock available - processes automatically"
        },
        {
            "name": "Low Stock Alert",
            "query": {"text": "alternator for 2018 Ford F-150", "urgency": "urgent"},
            "expected_color": "🟡 Human review",
            "description": "Part found but low stock requires human attention"
        },
        {
            "name": "Out of Stock",
            "query": {"text": "brake pads for 2018 Honda Civic", "urgency": "critical"},
            "expected_color": "🔴 Escalate now",
            "description": "Part found but out of stock - needs sourcing"
        },
        {
            "name": "Location-Specific Search",
            "query": {"text": "oil filter Toyota Camry", "location_filter": "Chicago South"},
            "expected_color": "🟢 Auto-resolved",
            "description": "Search within specific location with high confidence"
        }
    ]
    
    return {
        "scenarios": scenarios,
        "total_scenarios": len(scenarios),
        "usage": "Use these scenarios to demonstrate different system behaviors during your presentation"
    }

@app.get("/inventory")
async def get_inventory():
    """Get current inventory overview"""
    inventory_summary = {}
    
    for doc in inventory_docs:
        content = doc.page_content
        location = content.split(" - ")[0].replace("Location: ", "")
        
        if location not in inventory_summary:
            inventory_summary[location] = {
                "total_parts": 0,
                "in_stock": 0,
                "low_stock": 0,
                "out_of_stock": 0
            }
        
        inventory_summary[location]["total_parts"] += 1
        
        if "In stock" in content:
            inventory_summary[location]["in_stock"] += 1
        elif "Low stock" in content:
            inventory_summary[location]["low_stock"] += 1
        elif "Out of stock" in content:
            inventory_summary[location]["out_of_stock"] += 1
    
    return {
        "inventory_summary": inventory_summary,
        "total_locations": len(inventory_summary),
        "last_updated": datetime.now().isoformat(),
        "rag_status": "active" if qa_chain else "fallback"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rag_system": "operational" if qa_chain else "fallback",
        "vector_store": "connected",
        "llm": "active" if qa_chain else "offline",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/bulk_demo")
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
        query = Query(**query_data)
        try:
            result = await query_parts(query)
            results.append({
                "query": result.query,
                "color": result.color,
                "confidence": result.confidence,
                "processing_time_ms": result.processing_time_ms
            })
        except Exception as e:
            results.append({
                "query": query_data["text"],
                "color": "🔴 Error",
                "confidence": 0.0,
                "processing_time_ms": 0,
                "error": str(e)
            })
    
    return {
        "bulk_demo_results": results,
        "total_queries": len(results),
        "success_rate": f"{len([r for r in results if r['confidence'] > 0.5]) / len(results) * 100:.1f}%",
        "average_processing_time": f"{sum(r['processing_time_ms'] for r in results) / len(results):.1f}ms"
    }

@app.post("/fetch_emails")
async def fetch_emails(num: int = 5):
    """Fetch and process mock emails"""
    try:
        emails = fetch_mock_emails(num)
        processed_emails = []
        
        for email in emails:
            processed = email_processor.process_email(email)
            processed_emails.append(processed)
        
        return {
            "success": True,
            "emails_processed": len(processed_emails),
            "results": processed_emails,
            "stats": email_processor.get_email_stats()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email processing failed: {str(e)}")

@app.post("/process_email")
async def process_single_email(email_id: int):
    """Process a single email by ID"""
    try:
        emails = fetch_mock_emails(10)  # Get more emails to find the ID
        email = next((e for e in emails if e["id"] == email_id), None)
        
        if not email:
            raise HTTPException(status_code=404, detail=f"Email {email_id} not found")
        
        processed = email_processor.process_email(email)
        return processed
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email processing failed: {str(e)}")

@app.get("/logs/recent")
async def get_recent_logs(limit: int = 10):
    """Get recent log entries for dashboard"""
    try:
        import subprocess
        import os
        
        log_file = "logs/demo.log"
        if not os.path.exists(log_file):
            return {"logs": [], "message": "No logs available yet"}
        
        # Get recent lines from log file
        result = subprocess.run(
            ["tail", "-n", str(limit), log_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            logs = []
            for line in lines:
                if line.strip():
                    logs.append({"entry": line.strip()})
            return {"logs": logs}
        else:
            return {"logs": [], "message": "Could not read logs"}
            
    except Exception as e:
        return {"logs": [], "error": str(e)}

@app.get("/email_stats")
async def get_email_statistics():
    """Get email processing statistics"""
    try:
        stats = email_processor.get_email_stats()
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not get email stats: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Lester's Parts RAG Demo...")
    print("📋 Available endpoints:")
    print("  - POST /query_parts - Main parts lookup with RAG")
    print("  - GET /demo_scenarios - Pre-built scenarios for demo")
    print("  - GET /inventory - Current inventory overview")
    print("  - POST /bulk_demo - Run multiple demos")
    print("  - GET /docs - Interactive API documentation")
    print("\n🎯 Demo ready for Thursday presentation!")
    print("💡 Pro tip: Use ngrok to expose this locally for mobile testing")
    print("📁 Logs saved to: logs/demo.log")
    print("")
    
    # Log demo start
    log_demo_start()
    
    try:
        # Start the demo server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped by user")
        log_demo_end()
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        log_demo_end()
