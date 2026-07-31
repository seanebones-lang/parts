"""
Auto Parts Embeddings Fine-Tuner - Lester's Precision Upgrade
Fine-tunes sentence transformers for auto parts vocabulary
"""

import json
import os
from typing import List, Dict
from datetime import datetime

# Auto parts vocabulary corpus
AUTO_PARTS_CORPUS = [
    # Brake Systems
    {"text": "brake pads for Honda Civic 2019", "category": "brake_system"},
    {"text": "brake rotors front Honda Civic", "category": "brake_system"},
    {"text": "brake calipers Honda Civic rear", "category": "brake_system"},
    {"text": "brake fluid DOT 4", "category": "brake_system"},
    {"text": "brake lines Honda Civic", "category": "brake_system"},
    
    # Engine Components
    {"text": "alternator Ford F-150 2018", "category": "engine"},
    {"text": "starter motor Honda Civic", "category": "engine"},
    {"text": "spark plugs NGK Honda Civic", "category": "engine"},
    {"text": "ignition coils Honda Civic", "category": "engine"},
    {"text": "fuel injectors Honda Civic", "category": "engine"},
    {"text": "air filter Honda Civic", "category": "engine"},
    {"text": "oil filter Honda Civic", "category": "engine"},
    
    # Electrical Systems
    {"text": "battery Honda Civic 12V", "category": "electrical"},
    {"text": "headlight bulbs Honda Civic", "category": "electrical"},
    {"text": "tail light assembly Honda Civic", "category": "electrical"},
    {"text": "turn signal bulbs Honda Civic", "category": "electrical"},
    {"text": "fuses Honda Civic", "category": "electrical"},
    
    # Suspension & Steering
    {"text": "shock absorbers Honda Civic", "category": "suspension"},
    {"text": "struts Honda Civic front", "category": "suspension"},
    {"text": "wheel bearings Honda Civic", "category": "suspension"},
    {"text": "control arms Honda Civic", "category": "suspension"},
    {"text": "tie rod ends Honda Civic", "category": "suspension"},
    
    # Transmission
    {"text": "transmission fluid Honda Civic", "category": "transmission"},
    {"text": "clutch kit Honda Civic", "category": "transmission"},
    {"text": "clutch disc Honda Civic", "category": "transmission"},
    {"text": "pressure plate Honda Civic", "category": "transmission"},
    
    # Exhaust System
    {"text": "exhaust manifold Honda Civic", "category": "exhaust"},
    {"text": "catalytic converter Honda Civic", "category": "exhaust"},
    {"text": "muffler Honda Civic", "category": "exhaust"},
    {"text": "exhaust pipe Honda Civic", "category": "exhaust"},
    
    # Cooling System
    {"text": "radiator Honda Civic", "category": "cooling"},
    {"text": "thermostat Honda Civic", "category": "cooling"},
    {"text": "water pump Honda Civic", "category": "cooling"},
    {"text": "coolant Honda Civic", "category": "cooling"},
    
    # Wheels & Tires
    {"text": "alloy wheels Honda Civic", "category": "wheels"},
    {"text": "steel wheels Honda Civic", "category": "wheels"},
    {"text": "winter tires Honda Civic", "category": "wheels"},
    {"text": "summer tires Honda Civic", "category": "wheels"},
    {"text": "wheel hub Honda Civic", "category": "wheels"},
    
    # Ford F-150 Specific
    {"text": "brake pads Ford F-150 2018", "category": "brake_system"},
    {"text": "alternator Ford F-150 6.7L", "category": "engine"},
    {"text": "oil filter Ford F-150", "category": "engine"},
    {"text": "air filter Ford F-150", "category": "engine"},
    {"text": "spark plugs Ford F-150", "category": "engine"},
    
    # Toyota Camry Specific
    {"text": "brake pads Toyota Camry", "category": "brake_system"},
    {"text": "alternator Toyota Camry", "category": "engine"},
    {"text": "oil filter Toyota Camry", "category": "engine"},
    {"text": "air filter Toyota Camry", "category": "engine"},
    {"text": "spark plugs Toyota Camry", "category": "engine"},
    
    # BMW 3 Series Specific
    {"text": "premium brake pads BMW 3 Series", "category": "brake_system"},
    {"text": "luxury air filter BMW 3 Series", "category": "engine"},
    {"text": "performance exhaust BMW 3 Series", "category": "exhaust"},
    {"text": "sport suspension BMW 3 Series", "category": "suspension"},
    
    # Turbo & Performance
    {"text": "turbocharger Honda Civic 1998", "category": "performance"},
    {"text": "intercooler Honda Civic", "category": "performance"},
    {"text": "cold air intake Honda Civic", "category": "performance"},
    {"text": "performance chip Honda Civic", "category": "performance"},
    
    # OEM vs Aftermarket
    {"text": "OEM brake pads Honda Civic", "category": "oem"},
    {"text": "aftermarket brake pads Honda Civic", "category": "aftermarket"},
    {"text": "remanufactured alternator Ford F-150", "category": "remanufactured"},
    {"text": "new alternator Ford F-150", "category": "new"},
    
    # Location-Specific
    {"text": "brake pads Honda Civic Chicago North", "category": "location"},
    {"text": "alternator Ford F-150 O'Hare Auto", "category": "location"},
    {"text": "oil filter Toyota Camry Logan Square", "category": "location"},
    {"text": "brake pads BMW 3 Series Loop Luxury", "category": "location"},
    
    # Urgency & Stock
    {"text": "urgent brake pads Honda Civic", "category": "urgency"},
    {"text": "emergency alternator Ford F-150", "category": "urgency"},
    {"text": "low stock oil filter Toyota Camry", "category": "stock"},
    {"text": "out of stock turbo Honda Civic", "category": "stock"},
    
    # Cross-References
    {"text": "AC Delco 15-XXXX cross reference Honda Civic", "category": "cross_ref"},
    {"text": "Bosch part number 12345 Honda Civic", "category": "cross_ref"},
    {"text": "Denso alternator equivalent Ford F-150", "category": "cross_ref"},
    {"text": "NGK spark plug cross reference Toyota Camry", "category": "cross_ref"},
    
    # VIN-Specific
    {"text": "parts for VIN 1HGBH41JXMN109186 Honda Civic", "category": "vin_specific"},
    {"text": "VIN-specific alternator Ford F-150", "category": "vin_specific"},
    {"text": "exact fit parts Toyota Camry VIN", "category": "vin_specific"},
]

def create_fine_tuning_dataset():
    """Create fine-tuning dataset for auto parts vocabulary"""
    print("🔧 Creating auto parts fine-tuning dataset...")
    
    # Create training pairs for contrastive learning
    training_pairs = []
    
    for i, item1 in enumerate(AUTO_PARTS_CORPUS):
        for j, item2 in enumerate(AUTO_PARTS_CORPUS):
            if i != j:
                # Same category = positive pair (similar)
                if item1["category"] == item2["category"]:
                    training_pairs.append({
                        "anchor": item1["text"],
                        "positive": item2["text"],
                        "label": 1
                    })
                # Different category = negative pair (dissimilar)
                else:
                    training_pairs.append({
                        "anchor": item1["text"],
                        "positive": item2["text"],
                        "label": 0
                    })
    
    # Save dataset
    dataset_file = "auto_parts_training_dataset.json"
    with open(dataset_file, "w") as f:
        json.dump({
            "corpus": AUTO_PARTS_CORPUS,
            "training_pairs": training_pairs[:1000],  # Limit for demo
            "created_at": datetime.now().isoformat(),
            "total_pairs": len(training_pairs)
        }, f, indent=2)
    
    print(f"✅ Created dataset: {dataset_file}")
    print(f"📊 Total training pairs: {len(training_pairs)}")
    print(f"📊 Limited to 1000 pairs for demo")
    
    return dataset_file

def create_enhanced_embeddings():
    """Create enhanced embeddings with auto parts vocabulary"""
    print("🚀 Creating enhanced auto parts embeddings...")
    
    try:
        from sentence_transformers import SentenceTransformer, InputExample, losses
        from torch.utils.data import DataLoader
        
        # Load base model
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Create training examples
        training_examples = []
        
        # Add auto parts vocabulary as positive examples
        for item in AUTO_PARTS_CORPUS:
            training_examples.append(InputExample(
                texts=[item["text"], item["text"]],  # Self-similarity
                label=1.0
            ))
        
        # Create data loader
        train_dataloader = DataLoader(training_examples, shuffle=True, batch_size=16)
        
        # Define loss function
        train_loss = losses.CosineSimilarityLoss(model)
        
        # Fine-tune model
        print("🔧 Fine-tuning embeddings for auto parts vocabulary...")
        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=3,  # Quick fine-tuning for demo
            warmup_steps=100,
            output_path='./auto_parts_embeddings_model'
        )
        
        print("✅ Fine-tuned embeddings saved to: ./auto_parts_embeddings_model")
        
        # Test the fine-tuned model
        test_queries = [
            "brake pads Honda Civic",
            "alternator Ford F-150",
            "oil filter Toyota Camry",
            "turbo Honda Civic"
        ]
        
        print("\n🧪 Testing fine-tuned embeddings...")
        for query in test_queries:
            # Find most similar parts
            similarities = []
            for item in AUTO_PARTS_CORPUS[:10]:  # Test on first 10
                similarity = model.similarity([query], [item["text"]])[0][0]
                similarities.append((item["text"], similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            print(f"Query: {query}")
            print(f"  Top match: {similarities[0][0]} (similarity: {similarities[0][1]:.3f})")
            print(f"  Category: {next(item['category'] for item in AUTO_PARTS_CORPUS if item['text'] == similarities[0][0])}")
            print()
        
        return True
        
    except ImportError as e:
        print(f"⚠️ Required libraries not available: {e}")
        print("💡 Install with: pip install sentence-transformers torch")
        return False
    except Exception as e:
        print(f"❌ Fine-tuning failed: {e}")
        return False

def create_vocabulary_enhancement():
    """Create vocabulary enhancement for better retrieval"""
    print("📚 Creating auto parts vocabulary enhancement...")
    
    # Create vocabulary mappings
    vocabulary_mappings = {
        "synonyms": {
            "brake_pads": ["brake pads", "brake shoes", "brake linings", "friction material"],
            "alternator": ["alternator", "generator", "charging system", "electrical generator"],
            "oil_filter": ["oil filter", "engine filter", "lube filter", "motor filter"],
            "air_filter": ["air filter", "intake filter", "engine air filter", "air cleaner"],
            "spark_plugs": ["spark plugs", "ignition plugs", "spark plugs set", "ignition system"],
            "turbo": ["turbocharger", "turbo", "forced induction", "supercharger"]
        },
        "abbreviations": {
            "BP": "brake pads",
            "ALT": "alternator",
            "OF": "oil filter",
            "AF": "air filter",
            "SP": "spark plugs",
            "TURBO": "turbocharger"
        },
        "manufacturers": {
            "NGK": "NGK spark plugs",
            "AC Delco": "AC Delco parts",
            "Bosch": "Bosch components",
            "Denso": "Denso parts",
            "Honda": "Honda OEM",
            "Ford": "Ford OEM",
            "Toyota": "Toyota OEM",
            "BMW": "BMW OEM"
        },
        "years": {
            "2019": "2019 model year",
            "2018": "2018 model year",
            "1998": "1998 model year",
            "2020": "2020 model year",
            "2021": "2021 model year"
        }
    }
    
    # Save vocabulary mappings
    vocab_file = "auto_parts_vocabulary.json"
    with open(vocab_file, "w") as f:
        json.dump({
            "vocabulary_mappings": vocabulary_mappings,
            "created_at": datetime.now().isoformat(),
            "total_mappings": sum(len(v) for v in vocabulary_mappings.values())
        }, f, indent=2)
    
    print(f"✅ Vocabulary enhancement saved to: {vocab_file}")
    print(f"📊 Total mappings: {sum(len(v) for v in vocabulary_mappings.values())}")
    
    return vocab_file

def main():
    """Main fine-tuning process"""
    print("🚀 Lester's Auto Parts Embeddings Fine-Tuner")
    print("=" * 60)
    
    # Step 1: Create training dataset
    dataset_file = create_fine_tuning_dataset()
    
    # Step 2: Create vocabulary enhancement
    vocab_file = create_vocabulary_enhancement()
    
    # Step 3: Fine-tune embeddings (optional)
    print("\n🤔 Fine-tune embeddings? This requires sentence-transformers and torch.")
    print("💡 For demo, we'll skip this step and use the vocabulary enhancement.")
    
    # For demo purposes, we'll skip the actual fine-tuning
    # Uncomment the next line to enable fine-tuning:
    # create_enhanced_embeddings()
    
    print("\n✅ Auto parts vocabulary enhancement complete!")
    print(f"📁 Files created:")
    print(f"  - {dataset_file}")
    print(f"  - {vocab_file}")
    print("\n💡 To use enhanced vocabulary in RAG core:")
    print("  1. Load vocabulary mappings from auto_parts_vocabulary.json")
    print("  2. Expand queries using synonyms and abbreviations")
    print("  3. Boost retrieval accuracy for auto parts queries")

if __name__ == "__main__":
    main()
