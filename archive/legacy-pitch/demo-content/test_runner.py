"""
Test Runner & Error Cage - Lester's Missing Bulletproof
Runs scenarios, logs fails, spits report. Catches glitches like low-stock reds.
"""

import json
import sys
import subprocess
from datetime import datetime
from typing import List, Dict

# Import the core if available
try:
    from rag_demo import process_query
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    print("⚠️ RAG core not available - running mock tests")

# Test scenarios
SCENARIOS = [
    ("brake pads 2019 Honda Civic", "🟢", "Should auto-resolve with payment"),
    ("alternator 2018 Ford F-150", "🟡", "Low stock - should flag for review"),
    ("turbo 1998 Civic", "🔴", "Out of stock - should escalate"),
    ("oil filter Toyota Camry", "🟢", "Should auto-resolve"),
    ("brake pads BMW 3 Series", "🟡", "Premium parts - review needed"),
    ("nonexistent part 2025", "🔴", "No match - should escalate"),
    ("air filter Honda Civic", "🟢", "Common part - should auto-resolve"),
    ("transmission Honda Civic", "🟡", "Expensive part - review needed"),
    ("wheel bearings Honda Civic", "🟢", "Should auto-resolve"),
    ("performance exhaust BMW", "🟡", "High-value part - review needed")
]

def mock_process_query(query: str) -> Dict:
    """Mock version for testing when core isn't available"""
    if "civic" in query.lower() and "brake" in query.lower():
        return {
            "query": query,
            "result": {"part": "Brake Pads Honda Civic", "stock": 5, "price": 45, "score": 0.9},
            "color": "🟢 Auto-resolved & Paid",
            "payment": {"id": "pi_123", "amount": 4500, "status": "succeeded"}
        }
    elif "alternator" in query.lower():
        return {
            "query": query,
            "result": {"part": "Alternator Ford F-150", "stock": 2, "price": 120, "score": 0.7},
            "color": "🟡 Human review"
        }
    elif "turbo" in query.lower():
        return {
            "query": query,
            "result": {"part": "Turbocharger Honda Civic", "stock": 0, "price": 350, "score": 0.6},
            "color": "🔴 Escalate now"
        }
    else:
        return {
            "query": query,
            "result": {"part": "Unknown", "stock": 0, "price": 0, "score": 0.3},
            "color": "🔴 Escalate now"
        }

def run_tests() -> Dict:
    """Run all test scenarios and generate report"""
    print("🧪 Lester's Test Runner - Bulletproof Validation")
    print("=" * 60)
    
    results = []
    start_time = datetime.now()
    
    for i, (query, expected_color, description) in enumerate(SCENARIOS, 1):
        print(f"Test {i:2d}/10: {query[:40]}...")
        
        try:
            if CORE_AVAILABLE:
                result = process_query(query)
            else:
                result = mock_process_query(query)
            
            actual_color = result.get("color", "")
            passed = expected_color in actual_color
            
            test_result = {
                "test_id": i,
                "query": query,
                "expected": expected_color,
                "actual": actual_color,
                "passed": passed,
                "description": description,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            if passed:
                print(f"    ✅ PASS - {actual_color}")
            else:
                print(f"    ❌ FAIL - Expected {expected_color}, got {actual_color}")
            
            results.append(test_result)
            
        except Exception as e:
            error_result = {
                "test_id": i,
                "query": query,
                "expected": expected_color,
                "actual": "ERROR",
                "passed": False,
                "description": description,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            results.append(error_result)
            print(f"    💥 ERROR - {str(e)}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Generate summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    failed_tests = total_tests - passed_tests
    
    summary = {
        "test_run": {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
        },
        "results": results,
        "environment": {
            "core_available": CORE_AVAILABLE,
            "python_version": sys.version,
            "platform": sys.platform
        }
    }
    
    # Save report
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Report saved: {report_file}")
    
    if failed_tests > 0:
        print(f"\n⚠️ {failed_tests} test(s) failed - check the report for details")
    else:
        print("\n🎉 All tests passed! System is bulletproof!")
    
    return summary

def run_quick_health_check():
    """Quick health check for demo readiness"""
    print("🏥 Lester's Quick Health Check")
    print("=" * 40)
    
    checks = []
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 8):
        checks.append({"check": "Python Version", "status": "✅", "details": f"{python_version.major}.{python_version.minor}"})
    else:
        checks.append({"check": "Python Version", "status": "❌", "details": f"{python_version.major}.{python_version.minor} (Need 3.8+)"})
    
    # Check core availability
    if CORE_AVAILABLE:
        checks.append({"check": "RAG Core", "status": "✅", "details": "Available"})
    else:
        checks.append({"check": "RAG Core", "status": "⚠️", "details": "Using mock"})
    
    # Check FAISS availability
    try:
        import faiss
        checks.append({"check": "FAISS", "status": "✅", "details": "Available for persistence"})
    except ImportError:
        checks.append({"check": "FAISS", "status": "⚠️", "details": "Not available - using in-memory"})
    
    # Check sentence transformers
    try:
        from sentence_transformers import SentenceTransformer
        checks.append({"check": "Embeddings", "status": "✅", "details": "Available for semantic search"})
    except ImportError:
        checks.append({"check": "Embeddings", "status": "⚠️", "details": "Not available - using keyword matching"})
    
    # Check dependencies
    try:
        import json
        checks.append({"check": "JSON Module", "status": "✅", "details": "Available"})
    except ImportError:
        checks.append({"check": "JSON Module", "status": "❌", "details": "Missing"})
    
    # Check Flask for API mode
    try:
        import flask
        checks.append({"check": "Flask API", "status": "✅", "details": "Available for API mode"})
    except ImportError:
        checks.append({"check": "Flask API", "status": "⚠️", "details": "Not available - CLI mode only"})
    
    # Print results
    for check in checks:
        print(f"{check['status']} {check['check']}: {check['details']}")
    
    all_good = all(check['status'] in ['✅', '⚠️'] for check in checks)
    
    print("\n" + "=" * 40)
    if all_good:
        print("🎯 System ready for demo!")
    else:
        print("⚠️ Some issues found - check above")
    
    return all_good

def run_persistence_test():
    """Test FAISS persistence functionality"""
    print("💾 Lester's Persistence Test")
    print("=" * 40)
    
    if not CORE_AVAILABLE:
        print("❌ RAG core not available for persistence test")
        return False
    
    try:
        from rag_demo import persistent_store
        
        # Test search functionality
        test_queries = [
            "brake pads Honda Civic",
            "alternator Ford F-150",
            "oil filter Toyota Camry"
        ]
        
        print("🔍 Testing search functionality...")
        for query in test_queries:
            results = persistent_store.search(query, k=1)
            if results:
                result = results[0]
                print(f"  ✅ {query}: {result['part_name']} (score: {result['score']:.3f})")
            else:
                print(f"  ❌ {query}: No results")
        
        # Check if index files exist
        import os
        index_files = ["chicago_parts_index.faiss", "parts_metadata.pkl"]
        for file in index_files:
            if os.path.exists(file):
                print(f"  ✅ {file}: Exists")
            else:
                print(f"  ⚠️ {file}: Not found")
        
        print("\n🎯 Persistence test complete!")
        return True
        
    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Lester's Test Runner")
    parser.add_argument("--run", action="store_true", help="Run full test suite")
    parser.add_argument("--health", action="store_true", help="Run quick health check")
    parser.add_argument("--quick", action="store_true", help="Run 3 quick tests")
    parser.add_argument("--persistence", action="store_true", help="Test FAISS persistence")
    
    args = parser.parse_args()
    
    if args.health:
        run_quick_health_check()
    elif args.persistence:
        run_persistence_test()
    elif args.quick:
        # Run just 3 key tests
        print("⚡ Lester's Quick Test (3 scenarios)")
        quick_scenarios = SCENARIOS[:3]
        for query, expected, desc in quick_scenarios:
            try:
                if CORE_AVAILABLE:
                    result = process_query(query)
                else:
                    result = mock_process_query(query)
                actual = result.get("color", "")
                passed = expected in actual
                status = "✅" if passed else "❌"
                print(f"{status} {query}: {actual}")
            except Exception as e:
                print(f"💥 {query}: ERROR - {e}")
    else:
        run_tests()
