"""
Runnable RAG Core - Enterprise Engine
The heart of the system - loads mock inventory, runs queries with colors, stubs Stripe/email
"""

import json
import random
import os
import pickle
import time
from datetime import datetime
from typing import Dict, List, Optional

# FAISS for persistent vector storage
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("WARNING: FAISS not available - using in-memory storage")

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("WARNING: Sentence transformers not available - using mock embeddings")

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

class PersistentRAGStore:
    """Persistent RAG storage with FAISS indexing"""
    
    def __init__(self, index_path: str = "chicago_parts_index.faiss", metadata_path: str = "parts_metadata.pkl"):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata = []
        self.embeddings_model = None
        
        # Initialize embeddings model
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embeddings_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                self.embedding_dim = self.embeddings_model.get_sentence_embedding_dimension()
            except Exception as e:
                print(f"⚠️ Failed to load embeddings model: {e}")
                EMBEDDINGS_AVAILABLE = False
        
        self.load_or_build_index()
    
    def load_or_build_index(self):
        """Load existing index or build new one"""
        if FAISS_AVAILABLE and os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            try:
                print("🔄 Loading existing FAISS index...")
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                print(f"✅ Loaded index with {len(self.metadata)} parts")
                return
            except Exception as e:
                print(f"⚠️ Failed to load index: {e}")
        
        print("🔧 Building new FAISS index...")
        self.build_index()
    
    def build_index(self):
        """Build FAISS index from inventory data"""
        if not EMBEDDINGS_AVAILABLE or not FAISS_AVAILABLE:
            print("⚠️ FAISS/embeddings not available - using in-memory storage")
            return
        
        # Prepare documents for indexing
        documents = []
        for location, parts in INVENTORY.items():
            for part_name, details in parts.items():
                doc_text = f"{location} - {part_name} - SKU: {details['sku']} - Stock: {details['stock']} - Price: ${details['price']}"
                documents.append({
                    'text': doc_text,
                    'location': location,
                    'part_name': part_name,
                    'details': details
                })
        
        # Generate embeddings
        texts = [doc['text'] for doc in documents]
        embeddings = self.embeddings_model.encode(texts)
        
        # Create FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(embeddings.astype('float32'))
        self.metadata = documents
        
        # Save to disk
        self.save_index()
        print(f"✅ Built and saved index with {len(documents)} parts")
    
    def save_index(self):
        """Save index and metadata to disk"""
        if FAISS_AVAILABLE and self.index is not None:
            try:
                faiss.write_index(self.index, self.index_path)
                with open(self.metadata_path, 'wb') as f:
                    pickle.dump(self.metadata, f)
                print(f"💾 Saved index to {self.index_path}")
            except Exception as e:
                print(f"⚠️ Failed to save index: {e}")
    
    def search(self, query: str, k: int = 3) -> List[Dict]:
        """Search for similar parts"""
        if not EMBEDDINGS_AVAILABLE or not FAISS_AVAILABLE or self.index is None:
            # Fallback to mock search
            return self.mock_search(query)
        
        try:
            # Generate query embedding
            query_embedding = self.embeddings_model.encode([query])
            
            # Search index
            scores, indices = self.index.search(query_embedding.astype('float32'), k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result['score'] = float(score)
                    results.append(result)
            
            return results
        except Exception as e:
            print(f"⚠️ Search failed: {e}")
            return self.mock_search(query)
    
    def mock_search(self, query: str) -> List[Dict]:
        """Fallback mock search"""
        # Simple keyword matching fallback
        query_lower = query.lower()
        results = []
        
        for location, parts in INVENTORY.items():
            for part_name, details in parts.items():
                if any(word in part_name.lower() for word in query_lower.split()):
                    results.append({
                        'text': f"{location} - {part_name} - SKU: {details['sku']} - Stock: {details['stock']} - Price: ${details['price']}",
                        'location': location,
                        'part_name': part_name,
                        'details': details,
                        'score': random.uniform(0.6, 0.9)
                    })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)[:3]

# Global persistent store
persistent_store = PersistentRAGStore()

# Hallucination detector
try:
    from hallucination_detector import detect_response_hallucination, generate_demo_hallucination_report
    HALLUCINATION_DETECTOR_AVAILABLE = True
    print("✅ Hallucination detector enabled")
except ImportError:
    HALLUCINATION_DETECTOR_AVAILABLE = False
    print("⚠️ Hallucination detector not available")

def mock_retrieve(query: str) -> Dict:
    """Enhanced retrieval with persistent FAISS store"""
    try:
        # Use persistent store for search
        results = persistent_store.search(query, k=1)
        
        if results and len(results) > 0:
            best_result = results[0]
            details = best_result['details']
            
            return {
                "part": best_result['part_name'],
                "location": best_result['location'],
                "stock": details["stock"],
                "sku": details["sku"],
                "price": details["price"],
                "score": best_result['score']
            }
    except Exception as e:
        print(f"⚠️ Persistent search failed: {e}")
    
    # Fallback to original fuzzy matching
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
    """Process a parts query and return formatted response with hallucination detection"""
    print(f"\n🔍 Query: {query}")
    
    hit = mock_retrieve(query)
    
    # Detect hallucinations if available
    hallucination_result = None
    if HALLUCINATION_DETECTOR_AVAILABLE:
        try:
            hallucination_result = detect_response_hallucination(query, hit)
            print(f"🧠 Hallucination Detection: {hallucination_result['risk_level']} (confidence: {hallucination_result['confidence_score']:.3f})")
            if hallucination_result['issues']:
                print(f"⚠️ Issues detected: {', '.join(hallucination_result['issues'])}")
        except Exception as e:
            print(f"⚠️ Hallucination detection failed: {e}")
    
    # Adjust confidence based on hallucination detection
    confidence = hit["score"]
    if hallucination_result and hallucination_result['is_hallucination']:
        confidence = min(confidence, hallucination_result['confidence_score'])
        print(f"🔍 Adjusted confidence due to hallucination risk: {confidence:.3f}")
    
    # Determine color and steps based on adjusted confidence
    color, steps = color_code(confidence, hit["stock"])
    
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
    
    response = {
        "query": query,
        "result": hit,
        "color": color,
        "next_steps": steps,
        "payment": payment,
        "ui_hint": "success" if "🟢" in color else "warning" if "🟡" in color else "error",
        "timestamp": datetime.now().isoformat(),
        "confidence": confidence
    }
    
    # Add hallucination detection info
    if hallucination_result:
        response["hallucination_detection"] = {
            "risk_level": hallucination_result["risk_level"],
            "confidence_score": hallucination_result["confidence_score"],
            "issues": hallucination_result["issues"],
            "is_hallucination": hallucination_result["is_hallucination"]
        }
    
    return response

def serve_api(port: int = 8000):
    """Simple Flask server for API endpoints with offline resilience and Prometheus metrics"""
    try:
        from flask import Flask, request, jsonify
        import json as json_lib
        
        # Prometheus metrics
        try:
            from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
            PROMETHEUS_AVAILABLE = True
            
            # Define metrics
            RAG_QUERIES_TOTAL = Counter('rag_queries_total', 'Total RAG queries', ['status', 'location'])
            RAG_QUERY_DURATION = Histogram('rag_query_duration_seconds', 'RAG query duration')
            RAG_CONFIDENCE_SCORE = Histogram('rag_confidence_score', 'RAG confidence scores')
            RAG_OFFLINE_QUEUE_SIZE = Gauge('rag_offline_queue_size', 'Number of queries in offline queue')
            RAG_FAISS_INDEX_SIZE = Gauge('rag_faiss_index_size', 'Number of documents in FAISS index')
            
            print("✅ Prometheus metrics enabled")
        except ImportError:
            PROMETHEUS_AVAILABLE = False
            print("⚠️ Prometheus not available - metrics disabled")
        
        app = Flask(__name__)
        
        # Offline query queue
        query_queue_file = "demo/query_queue.json"
        
        def load_query_queue():
            """Load offline query queue"""
            try:
                if os.path.exists(query_queue_file):
                    with open(query_queue_file, 'r') as f:
                        return json_lib.load(f)
                return []
            except Exception:
                return []
        
        def save_query_queue(queue):
            """Save offline query queue"""
            try:
                os.makedirs(os.path.dirname(query_queue_file), exist_ok=True)
                with open(query_queue_file, 'w') as f:
                    json_lib.dump(queue, f, indent=2)
            except Exception as e:
                print(f"⚠️ Failed to save query queue: {e}")
        
        def get_cached_response(query: str) -> Optional[Dict]:
            """Get cached response for offline mode"""
            # Simple cache based on keywords
            query_lower = query.lower()
            cache_keywords = {
                "brake": {"part": "Brake Pads Honda Civic", "stock": 5, "price": 45, "score": 0.9},
                "alternator": {"part": "Alternator Ford F-150", "stock": 2, "price": 120, "score": 0.8},
                "oil": {"part": "Oil Filter Toyota Camry", "stock": 8, "price": 12, "score": 0.85}
            }
            
            for keyword, cached_result in cache_keywords.items():
                if keyword in query_lower:
                    return cached_result
            return None
        
        @app.route('/query_parts', methods=['POST'])
        def query_parts():
            start_time = time.time()
            data = request.get_json()
            query = data.get('text', '')
            location = data.get('location', 'unknown')
            
            # Check if offline mode (simulate network issues)
            offline_mode = request.headers.get('X-Offline-Mode') == 'true'
            
            if offline_mode:
                # Queue query for later processing
                queue = load_query_queue()
                queue.append({
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "status": "queued"
                })
                save_query_queue(queue)
                
                # Update metrics
                if PROMETHEUS_AVAILABLE:
                    RAG_OFFLINE_QUEUE_SIZE.set(len(queue))
                    RAG_QUERIES_TOTAL.labels(status='offline', location=location).inc()
                
                # Return cached response if available
                cached = get_cached_response(query)
                if cached:
                    return jsonify({
                        "query": query,
                        "result": cached,
                        "color": "🟡 Offline Mode",
                        "next_steps": ["Query queued for sync", "Using cached response"],
                        "offline": True,
                        "queue_id": len(queue) - 1
                    })
                else:
                    return jsonify({
                        "query": query,
                        "result": {"part": "No cached response", "stock": 0, "price": 0, "score": 0.5},
                        "color": "🟡 Offline Mode",
                        "next_steps": ["Query queued for sync", "Connect to network for live results"],
                        "offline": True,
                        "queue_id": len(queue) - 1
                    })
            
            # Normal online processing with metrics
            try:
                result = process_query(query)
                
                # Update Prometheus metrics
                if PROMETHEUS_AVAILABLE:
                    duration = time.time() - start_time
                    RAG_QUERY_DURATION.observe(duration)
                    RAG_CONFIDENCE_SCORE.observe(result.get('confidence', 0.5))
                    
                    # Determine status based on color
                    color = result.get('color', '')
                    if '🟢' in color:
                        status = 'success'
                    elif '🟡' in color:
                        status = 'review'
                    else:
                        status = 'escalate'
                    
                    RAG_QUERIES_TOTAL.labels(status=status, location=location).inc()
                
                return jsonify(result)
                
            except Exception as e:
                # Update error metrics
                if PROMETHEUS_AVAILABLE:
                    RAG_QUERIES_TOTAL.labels(status='error', location=location).inc()
                
                return jsonify({
                    "query": query,
                    "error": str(e),
                    "color": "🔴 Error",
                    "next_steps": ["System error - contact support"]
                }), 500
        
        @app.route('/sync_queue', methods=['POST'])
        def sync_queue():
            """Process queued queries when back online"""
            queue = load_query_queue()
            processed = []
            
            for item in queue:
                if item.get("status") == "queued":
                    try:
                        result = process_query(item["query"])
                        item["status"] = "processed"
                        item["result"] = result
                        item["processed_at"] = datetime.now().isoformat()
                        processed.append(item)
                    except Exception as e:
                        item["status"] = "error"
                        item["error"] = str(e)
                        processed.append(item)
            
            save_query_queue(queue)
            return jsonify({
                "processed": len(processed),
                "queue": queue
            })
        
        @app.route('/queue_status', methods=['GET'])
        def queue_status():
            """Get offline queue status"""
            queue = load_query_queue()
            pending = len([q for q in queue if q.get("status") == "queued"])
            return jsonify({
                "pending_queries": pending,
                "total_queued": len(queue),
                "last_sync": datetime.now().isoformat()
            })
        
        @app.route('/hallucination_report', methods=['GET'])
        def hallucination_report():
            """Get hallucination detection report for demo"""
            if HALLUCINATION_DETECTOR_AVAILABLE:
                try:
                    report = generate_demo_hallucination_report()
                    return jsonify(report)
                except Exception as e:
                    return jsonify({"error": str(e)}), 500
            else:
                return jsonify({"error": "Hallucination detector not available"}), 503
        
        @app.route('/metrics', methods=['GET'])
        def metrics():
            """Prometheus metrics endpoint"""
            if PROMETHEUS_AVAILABLE:
                # Update FAISS index size metric
                try:
                    if persistent_store and persistent_store.metadata:
                        RAG_FAISS_INDEX_SIZE.set(len(persistent_store.metadata))
                except:
                    pass
                
                return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
            else:
                return jsonify({"error": "Prometheus not available"}), 503
        
        @app.route('/health', methods=['GET'])
        def health():
            queue = load_query_queue()
            return jsonify({
                "status": "healthy", 
                "timestamp": datetime.now().isoformat(),
                "offline_support": True,
                "queue_file": query_queue_file,
                "prometheus_enabled": PROMETHEUS_AVAILABLE,
                "pending_queries": len([q for q in queue if q.get("status") == "queued"]),
                "faiss_index_size": len(persistent_store.metadata) if persistent_store and persistent_store.metadata else 0
            })
        
        print(f"🚀 Lester's RAG Core API running on http://localhost:{port}")
        print(f"📊 Try: curl -X POST http://localhost:{port}/query_parts -H 'Content-Type: application/json' -d '{{\"text\": \"brake pads Civic\"}}'")
        print(f"📱 Offline mode: Add header 'X-Offline-Mode: true'")
        print(f"🔄 Sync queue: POST /sync_queue")
        print(f"📈 Metrics: http://localhost:{port}/metrics")
        print(f"🏥 Health: http://localhost:{port}/health")
        print(f"🧠 Hallucination Report: http://localhost:{port}/hallucination_report")
        
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
