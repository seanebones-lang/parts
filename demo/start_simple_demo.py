#!/usr/bin/env python3
"""
Simple Demo Starter - Lester's Missing Piece
One-click demo setup for the core RAG system
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def check_dependencies():
    """Check if required dependencies are available"""
    print("🔍 Checking dependencies...")
    
    required_modules = ['json', 'datetime', 'random']
    missing = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            missing.append(module)
            print(f"  ❌ {module}")
    
    # Check optional modules
    optional_modules = ['flask', 'pandas']
    for module in optional_modules:
        try:
            __import__(module)
            print(f"  ✅ {module} (optional)")
        except ImportError:
            print(f"  ⚠️ {module} (optional - install with: pip install {module})")
    
    return len(missing) == 0

def run_quick_test():
    """Run a quick test to verify everything works"""
    print("\n🧪 Running quick test...")
    
    try:
        # Import the RAG core
        sys.path.append('.')
        from rag_demo import process_query
        
        # Test a simple query
        result = process_query("brake pads Honda Civic")
        
        print(f"  Query: brake pads Honda Civic")
        print(f"  Result: {result.get('color', 'Unknown')}")
        print(f"  Confidence: {result.get('confidence', 0):.2f}")
        
        if result.get('payment'):
            print(f"  Payment: {result['payment']['id']}")
        
        print("  ✅ Test passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False

def start_cli_demo():
    """Start the CLI demo"""
    print("\n🚀 Starting Lester's RAG Core CLI Demo")
    print("=" * 50)
    
    try:
        from rag_demo import process_query
        
        print("Enter parts queries (type 'quit' to exit):")
        print("Examples:")
        print("  - brake pads 2019 Honda Civic")
        print("  - alternator 2018 Ford F-150")
        print("  - oil filter Toyota Camry")
        print("  - turbo 1998 Honda Civic")
        print()
        
        while True:
            try:
                query = input("🔍 Query: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not query:
                    continue
                
                result = process_query(query)
                print("\n📊 Result:")
                print(json.dumps(result, indent=2))
                print("-" * 50)
                
            except KeyboardInterrupt:
                print("\n👋 Demo shutting down...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
                
    except ImportError:
        print("❌ RAG core not available. Make sure rag_demo.py is in the demo directory.")

def start_api_demo():
    """Start the API demo"""
    print("\n🌐 Starting Lester's RAG Core API Demo")
    print("=" * 50)
    
    try:
        from rag_demo import serve_api
        serve_api(port=8001)  # Use different port to avoid conflicts
        
    except ImportError:
        print("❌ Flask not available. Install with: pip install flask")
        print("💡 Falling back to CLI mode...")
        start_cli_demo()

def main():
    """Main demo starter"""
    print("🚀 Lester's Simple Demo Starter")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    if not deps_ok:
        print("\n❌ Missing required dependencies. Please install them first.")
        return
    
    # Run quick test
    test_ok = run_quick_test()
    
    if not test_ok:
        print("\n⚠️ Quick test failed, but continuing anyway...")
    
    # Ask user what they want to do
    print("\n🎯 Demo Options:")
    print("1. CLI Demo (interactive)")
    print("2. API Demo (web server)")
    print("3. Quick Test Only")
    
    try:
        choice = input("\nChoose option (1-3): ").strip()
        
        if choice == "1":
            start_cli_demo()
        elif choice == "2":
            start_api_demo()
        elif choice == "3":
            print("✅ Demo test complete!")
        else:
            print("Invalid choice. Starting CLI demo...")
            start_cli_demo()
            
    except KeyboardInterrupt:
        print("\n👋 Demo cancelled by user.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
