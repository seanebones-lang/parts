"""
Runnable RAG Core - Lester's Missing Engine
The heart of the system - loads mock inventory, runs queries with colors, stubs Stripe/email
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Optional

# Mock inventory - your 7 Chicago spots
INVENTORY = {
    "Chicago North": {
        "Brake Pads 2019 Honda Civic": {"stock": 5, "sku": "BP-HC19", "price": 45},
        "Air Filter Honda Civic": {"stock": 12, "sku": "AF-HC", "price": 18},
        "Spark Plugs Honda Civic": {"stock": 8, "sku": "SP-HC", "price": 25}
    },
    "O'Hare Auto": {
        "Alternator 2018 Ford F-150": {"stock": 2, "sku": "ALT-F150", "price": 120},
        "Brake Pads Ford F-150": {"stock": 3, "sku": "BP-F150", "price": 65},
        "Oil Filter Ford F-150": {"stock": 15, "sku": "OF-F150", "price": 14}
    },
    "Logan Square Motors": {
        "Oil Filter Toyota Camry": {"stock": 8, "sku": "OF-TC", "price": 12},
        "Brake Pads Toyota Camry": {"stock": 6, "sku": "BP-TC", "price": 38},
        "Alternator Toyota Camry": {"stock": 1, "sku": "ALT-TC", "price": 95}
    },
    "Wrigley Dealership": {
        "Turbocharger 1998 Honda Civic": {"stock": 0, "sku": "TURBO-HC98", "price": 350},
        "Exhaust System Honda Civic": {"stock": 4, "sku": "EX-HC", "price": 180},
        "Transmission Honda Civic": {"stock": 2, "sku": "TR-HC", "price": 450}
    },
    "South Side Parts": {
        "Wheel Bearings Honda Civic": {"stock": 7, "sku": "WB-HC", "price": 85},
        "Shock Absorbers Honda Civic": {"stock": 5, "sku": "SA-HC", "price": 120},
        "Clutch Kit Honda Civic": {"stock": 3, "sku": "CK-HC", "price": 280}
    },
    "Loop Luxury Autos": {
        "Premium Brake Pads BMW 3 Series": {"stock": 4, "sku": "PBP-BMW3", "price": 180},
        "Luxury Air Filter BMW 3 Series": {"stock": 6, "sku": "LAF-BMW3", "price": 45},
        "Performance Exhaust BMW 3 Series": {"stock": 2, "sku": "PE-BMW3", "price": 850}
    },
    "West Town Wheels": {
        "Alloy Wheels Honda Civic": {"stock": 8, "sku": "AW-HC", "price": 320},
        "Winter Tires Honda Civic": {"stock": 12, "sku": "WT-HC", "price": 180},
        "Brake Rotors Honda Civic": {"stock": 6, "sku": "BR-HC", "price": 75}
    }
}

def mock_retrieve(query: str) -> Dict:
    """Simple fuzzy match - prod: embeddings/FAISS."""
    query_lower = query.lower()
    
    # Find best match across all locations
    best_match = None
    best_location = None
    best_score = 0
    
    for location, parts in INVENTORY.items():
        for part_name, details in parts.items():
            # Simple keyword matching
            part_lower = part_name.lower()
            score = 0
            
            # Check for car make/model matches
            if any(car in query_lower for car in ['civic', 'honda']) and any(car in part_lower for car in ['civic', 'honda']):
                score += 0.3
            if any(car in query_lower for car in ['ford', 'f-150']) and any(car in part_lower for car in ['ford', 'f-150']):
                score += 0.3
            if any(car in query_lower for car in ['toyota', 'camry']) and any(car in part_lower for car in ['toyota', 'camry']):
                score += 0.3
            if any(car in query_lower for car in ['bmw']) and any(car in part_lower for car in ['bmw']):
                score += 0.3
            
            # Check for part type matches
            if any(part in query_lower for part in ['brake', 'pad']) and any(part in part_lower for part in ['brake', 'pad']):
                score += 0.4
            if any(part in query_lower for part in ['alternator']) and 'alternator' in part_lower:
                score += 0.4
            if any(part in query_lower for part in ['oil', 'filter']) and any(part in part_lower for part in ['oil', 'filter']):
                score += 0.4
            if any(part in query_lower for part in ['turbo']) and 'turbo' in part_lower:
                score += 0.4
            if any(part in query_lower for part in ['air', 'filter']) and any(part in part_lower for part in ['air', 'filter']):
                score += 0.4
            
            # Check for year matches
            if any(year in query_lower for year in ['2019', '2018', '1998']) and any(year in part_lower for year in ['2019', '2018', '1998']):
                score += 0.3
            
            if score > best_score:
                best_score = score
                best_match = part_name
                best_location = location
    
    # Add some randomness to make it more realistic
    best_score = min(best_score + random.uniform(0.1, 0.3), 1.0)
    
    if best_match and best_location:
        details = INVENTORY[best_location][best_match]
        return {
            "part": best_match,
            "location": best_location,
            "stock": details["stock"],
            "sku": details["sku"],
            "price": details["price"],
            "score": best_score
        }
    else:
        # Fallback for no match
        return {
            "part": "No exact match found",
            "location": "Multiple locations",
            "stock": 0,
            "sku": "N/A",
            "price": 0,
            "score": random.uniform(0.1, 0.4)
        }

def color_code(score: float, stock: int) -> tuple[str, List[str]]:
    """Determine color and next steps based on confidence and stock"""
    if score > 0.8 and stock > 0:
        return "🟢 Auto-resolved & Paid", ["Process payment", "Generate invoice", "Update inventory", "Send confirmation"]
    elif score > 0.8 and stock == 0:
        return "🟡 Low stock alert", ["Check other locations", "Quote customer", "Suggest alternatives"]
    elif score > 0.5 or stock > 0:
        return "🟡 Human review", ["Verify part match", "Check customer needs", "Prepare quote"]
    else:
        return "🔴 Escalate now", ["Call customer", "Manual lookup", "Escalate to supervisor"]

def process_query(query: str) -> Dict:
    """Process a parts query and return formatted response"""
    hit = mock_retrieve(query)
    color, steps = color_code(hit["score"], hit["stock"])
    
    # Generate payment info for green orders
    payment = None
    if "🟢" in color and hit["stock"] > 0:
        payment = {
            "id": f"pi_{int(datetime.now().timestamp())}",
            "amount": hit["price"] * 100,  # Stripe uses cents
            "currency": "usd",
            "status": "succeeded",
            "description": f"Parts order: {hit['part']}"
        }
    
    return {
        "query": query,
        "result": hit,
        "color": color,
        "next_steps": steps,
        "payment": payment,
        "ui_hint": "success" if "🟢" in color else "warning" if "🟡" in color else "error",
        "timestamp": datetime.now().isoformat(),
        "confidence": hit["score"]
    }

def serve_api(port: int = 8000):
    """Simple Flask server for API endpoints"""
    try:
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        
        @app.route('/query_parts', methods=['POST'])
        def query_parts():
            data = request.get_json()
            query = data.get('text', '')
            result = process_query(query)
            return jsonify(result)
        
        @app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
        
        print(f"🚀 Lester's RAG Core API running on http://localhost:{port}")
        print(f"📊 Try: curl -X POST http://localhost:{port}/query_parts -H 'Content-Type: application/json' -d '{{\"text\": \"brake pads Civic\"}}'")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except ImportError:
        print("❌ Flask not installed. Install with: pip install flask")
        print("💡 Running in CLI mode instead...")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        serve_api()
    else:
        # CLI mode
        print("🚀 Lester's RAG Core - Query Engine")
        print("=" * 50)
        print("Enter parts queries (type 'quit' to exit):")
        print("Examples: 'brake pads 2019 Honda Civic', 'alternator Ford F-150'")
        print()
        
        while True:
            try:
                query = input("🔍 Query: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not query:
                    continue
                
                result = process_query(query)
                print(json.dumps(result, indent=2))
                print("-" * 50)
                
            except KeyboardInterrupt:
                print("\n👋 Lester's RAG Core shutting down...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
