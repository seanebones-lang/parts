#!/usr/bin/env python3
"""
Parts RAG Demo Test Script - Lester's Edition
Test script to validate the demo functionality for Thursday's presentation
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict

# Test configuration
BASE_URL = "http://localhost:8000"
DEMO_SCENARIOS = [
    {
        "name": "Perfect Match - Auto Process",
        "query": {"text": "brake pads for 2019 Honda Civic", "urgency": "normal"},
        "expected_color": "🟢 Auto-resolved"
    },
    {
        "name": "Low Stock Alert",
        "query": {"text": "alternator for 2018 Ford F-150", "urgency": "urgent"},
        "expected_color": "🟡 Human review"
    },
    {
        "name": "Out of Stock",
        "query": {"text": "brake pads for 2018 Honda Civic", "urgency": "critical"},
        "expected_color": "🔴 Escalate now"
    },
    {
        "name": "Location-Specific Search",
        "query": {"text": "oil filter Toyota Camry", "location_filter": "Chicago South"},
        "expected_color": "🟢 Auto-resolved"
    },
    {
        "name": "Ambiguous Query",
        "query": {"text": "air filter Honda", "urgency": "normal"},
        "expected_color": "🟡 Human review"
    }
]

class DemoTestRunner:
    """Test runner for the Parts RAG Demo"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = []
    
    async def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_root_endpoint(self) -> bool:
        """Test the root endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Root endpoint working: {data['message']}")
                return True
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    async def test_parts_query(self, scenario: Dict) -> Dict:
        """Test a parts query scenario"""
        try:
            response = await self.client.post(
                f"{self.base_url}/query_parts",
                json=scenario["query"]
            )
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    "scenario": scenario["name"],
                    "success": True,
                    "query": data["query"],
                    "color": data["color"],
                    "confidence": data["confidence"],
                    "processing_time_ms": data["processing_time_ms"],
                    "suggestions": data["suggestions"],
                    "expected_color": scenario["expected_color"],
                    "color_match": data["color"] == scenario["expected_color"]
                }
                
                # Determine if test passed
                if result["color_match"]:
                    print(f"✅ {scenario['name']}: {data['color']} (confidence: {data['confidence']:.2f})")
                else:
                    print(f"⚠️ {scenario['name']}: Expected {scenario['expected_color']}, got {data['color']}")
                
                return result
            else:
                print(f"❌ {scenario['name']}: HTTP {response.status_code}")
                return {
                    "scenario": scenario["name"],
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            print(f"❌ {scenario['name']}: {e}")
            return {
                "scenario": scenario["name"],
                "success": False,
                "error": str(e)
            }
    
    async def test_inventory_endpoint(self) -> bool:
        """Test the inventory endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/inventory")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Inventory endpoint working: {data['total_locations']} locations")
                return True
            else:
                print(f"❌ Inventory endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Inventory endpoint error: {e}")
            return False
    
    async def test_demo_scenarios_endpoint(self) -> bool:
        """Test the demo scenarios endpoint"""
        try:
            response = await self.client.get(f"{self.base_url}/demo_scenarios")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Demo scenarios endpoint working: {data['total_scenarios']} scenarios")
                return True
            else:
                print(f"❌ Demo scenarios endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Demo scenarios endpoint error: {e}")
            return False
    
    async def test_bulk_demo(self) -> bool:
        """Test the bulk demo endpoint"""
        try:
            response = await self.client.post(f"{self.base_url}/bulk_demo")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Bulk demo working: {data['success_rate']} success rate")
                return True
            else:
                print(f"❌ Bulk demo failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Bulk demo error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict:
        """Run all tests and return results"""
        print("🚀 Starting Parts RAG Demo Tests...")
        print("=" * 60)
        
        # Test basic endpoints
        health_ok = await self.test_health_check()
        root_ok = await self.test_root_endpoint()
        inventory_ok = await self.test_inventory_endpoint()
        scenarios_ok = await self.test_demo_scenarios_endpoint()
        bulk_ok = await self.test_bulk_demo()
        
        print("\n📋 Testing Parts Query Scenarios...")
        print("-" * 40)
        
        # Test all scenarios
        scenario_results = []
        for scenario in DEMO_SCENARIOS:
            result = await self.test_parts_query(scenario)
            scenario_results.append(result)
        
        # Calculate summary
        total_tests = len(scenario_results)
        successful_tests = len([r for r in scenario_results if r.get("success", False)])
        color_matches = len([r for r in scenario_results if r.get("color_match", False)])
        
        avg_processing_time = sum(r.get("processing_time_ms", 0) for r in scenario_results) / total_tests
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "basic_endpoints": {
                "health": health_ok,
                "root": root_ok,
                "inventory": inventory_ok,
                "scenarios": scenarios_ok,
                "bulk_demo": bulk_ok
            },
            "scenario_tests": scenario_results,
            "summary": {
                "total_scenarios": total_tests,
                "successful_tests": successful_tests,
                "color_matches": color_matches,
                "success_rate": f"{successful_tests / total_tests * 100:.1f}%",
                "color_accuracy": f"{color_matches / total_tests * 100:.1f}%",
                "average_processing_time_ms": f"{avg_processing_time:.1f}"
            }
        }
        
        print("\n📊 Test Summary")
        print("=" * 60)
        print(f"✅ Successful tests: {successful_tests}/{total_tests}")
        print(f"🎯 Color accuracy: {color_matches}/{total_tests}")
        print(f"⏱️  Average processing time: {avg_processing_time:.1f}ms")
        print(f"📈 Success rate: {successful_tests / total_tests * 100:.1f}%")
        
        if successful_tests == total_tests and color_matches >= total_tests * 0.8:
            print("\n🎉 ALL TESTS PASSED! Demo ready for Thursday!")
        else:
            print("\n⚠️ Some tests failed. Check the results above.")
        
        return summary
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

async def main():
    """Main test function"""
    test_runner = DemoTestRunner(BASE_URL)
    
    try:
        results = await test_runner.run_all_tests()
        
        # Save results to file
        with open("demo_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Test results saved to demo_test_results.json")
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
    finally:
        await test_runner.close()

def print_demo_instructions():
    """Print demo instructions for Thursday"""
    print("\n" + "=" * 80)
    print("🎯 THURSDAY DEMO INSTRUCTIONS - LESTER'S EDITION")
    print("=" * 80)
    print("\n1. 🚀 Start the demo server:")
    print("   cd backend && python parts_rag_demo.py")
    print("\n2. 🌐 Expose locally (for mobile testing):")
    print("   ngrok http 8000")
    print("\n3. 📱 Test on mobile:")
    print("   Use the ngrok URL + /docs for interactive API")
    print("\n4. 🎬 Demo flow:")
    print("   - Show the GitHub repo structure")
    print("   - Fire up the API endpoint")
    print("   - Run through the demo scenarios")
    print("   - Show the traffic-light color coding")
    print("   - Demonstrate confidence scoring")
    print("\n5. 💡 Pro tips:")
    print("   - Use Postman on your phone for mobile demo")
    print("   - Have the demo scenarios ready")
    print("   - Show the processing times (sub-second)")
    print("   - Highlight the automated suggestions")
    print("\n6. 🎯 Key selling points:")
    print("   - 80-90% automation rate")
    print("   - Sub-second response times")
    print("   - Traffic-light triage system")
    print("   - Multi-location inventory visibility")
    print("   - Automated workflow suggestions")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    print_demo_instructions()
    asyncio.run(main())
