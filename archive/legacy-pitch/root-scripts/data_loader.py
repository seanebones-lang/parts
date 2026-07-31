"""
Inventory Data Loader - Lester's Edition
Realistic dealership parts data across 7 Chicago locations
"""

import json
import os
import random
from typing import List, Dict
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Chicago dealership locations - your 7 spots
LOCATIONS = [
    "Chicago North", "O'Hare Auto", "Logan Square Motors", "Wrigley Dealership",
    "South Side Parts", "Loop Luxury Autos", "West Town Wheels"
]

# Realistic parts catalog with varying stock levels
PARTS_CATALOG = [
    # Honda Civic parts
    {"part": "Brake Pads - 2019 Honda Civic", "sku": "BP-HC19", "base_price": 45, "category": "brakes"},
    {"part": "Brake Pads - 2018 Honda Civic", "sku": "BP-HC18", "base_price": 42, "category": "brakes"},
    {"part": "Air Filter - 2019 Honda Civic", "sku": "AF-HC19", "base_price": 15, "category": "engine"},
    {"part": "Oil Filter - 2019 Honda Civic", "sku": "OF-HC19", "base_price": 8, "category": "engine"},
    {"part": "Spark Plugs - 2019 Honda Civic", "sku": "SP-HC19", "base_price": 12, "category": "engine"},
    {"part": "Timing Belt - 2019 Honda Civic", "sku": "TB-HC19", "base_price": 85, "category": "engine"},
    {"part": "Water Pump - 2019 Honda Civic", "sku": "WP-HC19", "base_price": 95, "category": "engine"},
    
    # Ford F-150 parts
    {"part": "Alternator - 2018 Ford F-150", "sku": "ALT-F150", "base_price": 120, "category": "electrical"},
    {"part": "Brake Rotors - 2018 Ford F-150", "sku": "BR-F150", "base_price": 85, "category": "brakes"},
    {"part": "Oil Filter - 2018 Ford F-150", "sku": "OF-F150", "base_price": 12, "category": "engine"},
    {"part": "Air Filter - 2018 Ford F-150", "sku": "AF-F150", "base_price": 18, "category": "engine"},
    {"part": "Transmission Filter - 2018 Ford F-150", "sku": "TF-F150", "base_price": 25, "category": "transmission"},
    
    # Toyota Camry parts
    {"part": "Oil Filter - 2020 Toyota Camry", "sku": "OF-TC20", "base_price": 8.50, "category": "engine"},
    {"part": "Air Filter - 2020 Toyota Camry", "sku": "AF-TC20", "base_price": 12, "category": "engine"},
    {"part": "Brake Pads - 2020 Toyota Camry", "sku": "BP-TC20", "base_price": 38, "category": "brakes"},
    {"part": "Spark Plugs - 2020 Toyota Camry", "sku": "SP-TC20", "base_price": 15, "category": "engine"},
    {"part": "Serpentine Belt - 2020 Toyota Camry", "sku": "SB-TC20", "base_price": 22, "category": "engine"},
    
    # Generic parts that work across models
    {"part": "Motor Oil - 5W-30", "sku": "MO-5W30", "base_price": 28, "category": "fluids"},
    {"part": "Coolant - Antifreeze", "sku": "COOL-ANTI", "base_price": 15, "category": "fluids"},
    {"part": "Windshield Wipers - Universal", "sku": "WW-UNIV", "base_price": 18, "category": "exterior"},
    {"part": "Cabin Air Filter - Universal", "sku": "CAF-UNIV", "base_price": 12, "category": "interior"},
    
    # High-value parts for escalation scenarios
    {"part": "Turbocharger - 2019 Honda Civic", "sku": "TURBO-HC19", "base_price": 350, "category": "performance"},
    {"part": "ECU - 2018 Ford F-150", "sku": "ECU-F150", "base_price": 450, "category": "electrical"},
    {"part": "Transmission - 2020 Toyota Camry", "sku": "TRANS-TC20", "base_price": 1200, "category": "transmission"},
]

def generate_realistic_stock(part: Dict, location: str) -> int:
    """Generate realistic stock levels based on part type and location"""
    base_stock = random.randint(0, 15)
    
    # Adjust based on part category
    if part["category"] in ["fluids", "engine"]:
        base_stock += random.randint(5, 10)  # Common parts
    elif part["category"] in ["performance", "transmission"]:
        base_stock = random.randint(0, 2)  # Rare parts
    elif part["category"] == "brakes":
        base_stock += random.randint(2, 8)  # Moderate demand
    
    # Adjust based on location (some locations have more stock)
    if location in ["Chicago North", "O'Hare Auto"]:
        base_stock += random.randint(2, 5)  # High-volume locations
    elif location in ["Loop Luxury Autos"]:
        base_stock = max(0, base_stock - random.randint(1, 3))  # Premium location, less stock
    
    return max(0, base_stock)

def load_mock_inventory() -> List[Document]:
    """Load and generate realistic parts data across all locations"""
    docs = []
    
    for part in PARTS_CATALOG:
        for location in LOCATIONS:
            stock = generate_realistic_stock(part, location)
            price = part["base_price"] + random.uniform(-5, 10)  # Price variation
            
            # Create realistic document content
            content = f"""Location: {location} - {part['part']}: Stock {stock}, SKU: {part['sku']}, Price: ${price:.2f}
Category: {part['category']}
Description: High-quality {part['category']} component for automotive applications
Availability: {'In stock' if stock > 3 else 'Low stock' if stock > 0 else 'Out of stock'}
Cross-location availability: Checked across 7 Chicago dealership locations"""
            
            metadata = {
                "location": location,
                "part": part["part"],
                "sku": part["sku"],
                "stock": stock,
                "price": round(price, 2),
                "category": part["category"],
                "status": "in_stock" if stock > 3 else "low_stock" if stock > 0 else "out_of_stock"
            }
            
            docs.append(Document(page_content=content, metadata=metadata))
    
    return docs

def build_vectorstore(docs: List[Document]) -> FAISS:
    """Embed and index docs - optimized for parts precision"""
    print("🔧 Building vector store with realistic dealership data...")
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, 
        chunk_overlap=50  # Tighter chunks for parts precision
    )
    
    chunks = text_splitter.split_documents(docs)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Save for quick reloads
    vectorstore.save_local("data/faiss_index")
    
    print(f"✅ Loaded {len(docs)} parts across {len(LOCATIONS)} locations")
    print(f"📊 Total chunks: {len(chunks)}")
    
    return vectorstore

def load_vectorstore_from_disk() -> FAISS:
    """Load pre-built vector store from disk"""
    try:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.load_local("data/faiss_index", embeddings)
        print("✅ Loaded vector store from disk")
        return vectorstore
    except Exception as e:
        print(f"⚠️ Could not load from disk: {e}")
        print("🔄 Building new vector store...")
        return build_vectorstore(load_mock_inventory())

def save_inventory_json(docs: List[Document]):
    """Save inventory data as JSON for reference"""
    inventory_data = []
    for doc in docs:
        inventory_data.append({
            "content": doc.page_content,
            "metadata": doc.metadata
        })
    
    with open("data/inventory.json", "w") as f:
        json.dump(inventory_data, f, indent=2)
    
    print("💾 Inventory data saved to data/inventory.json")

def get_inventory_summary(docs: List[Document]) -> Dict:
    """Get inventory summary for dashboard"""
    summary = {}
    
    for doc in docs:
        location = doc.metadata["location"]
        if location not in summary:
            summary[location] = {
                "total_parts": 0,
                "in_stock": 0,
                "low_stock": 0,
                "out_of_stock": 0,
                "total_value": 0
            }
        
        summary[location]["total_parts"] += 1
        summary[location]["total_value"] += doc.metadata["price"] * doc.metadata["stock"]
        
        status = doc.metadata["status"]
        if status == "in_stock":
            summary[location]["in_stock"] += 1
        elif status == "low_stock":
            summary[location]["low_stock"] += 1
        else:
            summary[location]["out_of_stock"] += 1
    
    return summary

if __name__ == "__main__":
    print("🚀 Lester's Inventory Data Loader")
    print("=" * 50)
    
    # Generate realistic inventory
    docs = load_mock_inventory()
    
    # Build vector store
    vectorstore = build_vectorstore(docs)
    
    # Save data for reference
    save_inventory_json(docs)
    
    # Show summary
    summary = get_inventory_summary(docs)
    print("\n📊 Inventory Summary:")
    for location, stats in summary.items():
        print(f"  {location}: {stats['total_parts']} parts, ${stats['total_value']:.0f} value")
        print(f"    🟢 In stock: {stats['in_stock']}, 🟡 Low stock: {stats['low_stock']}, 🔴 Out of stock: {stats['out_of_stock']}")
    
    print(f"\n✅ Ready for queries! Vector store built with {len(docs)} parts across {len(LOCATIONS)} locations")
