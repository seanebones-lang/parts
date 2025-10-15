"""
Hallucination Detector - Lester's Precision Guard
Detects AI hallucinations and provides confidence scoring for demo flair
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class HallucinationDetector:
    """Detects potential hallucinations in RAG responses"""
    
    def __init__(self):
        # Known valid parts patterns
        self.valid_part_patterns = [
            r'brake\s+(pads?|rotors?|calipers?)',
            r'(oil|air|fuel)\s+filters?',
            r'(spark\s+)?plugs?',
            r'alternators?',
            r'turbo(chargers?)?',
            r'(head|tail|fog)\s+lights?',
            r'(winter|summer|all\s+season)\s+tires?',
            r'(power\s+)?steering\s+(pumps?|fluid)',
            r'transmission\s+(fluid|parts?)',
            r'(engine|motor)\s+oil',
            r'batter(ies|y)',
            r'(wiper\s+)?blades?',
            r'(suspension|shock|strut)\s+(kits?|parts?)',
            r'radiators?',
            r'(alloy|steel)\s+wheels?'
        ]
        
        # Known valid car makes/models
        self.valid_cars = [
            'honda', 'civic', 'accord', 'pilot', 'cr-v',
            'ford', 'f-150', 'mustang', 'explorer', 'escape',
            'toyota', 'camry', 'corolla', 'rav4', 'highlander',
            'bmw', '3 series', '5 series', 'x3', 'x5',
            'mercedes', 'benz', 'c-class', 'e-class',
            'audi', 'a4', 'a6', 'q5', 'q7',
            'chevrolet', 'silverado', 'equinox', 'malibu',
            'nissan', 'altima', 'sentra', 'rogue', 'pathfinder'
        ]
        
        # Known valid years (reasonable range)
        self.valid_years = list(range(1990, 2025))
        
        # Known valid locations
        self.valid_locations = [
            'chicago north', 'ohare auto', 'logan square motors',
            'wrigley dealership', 'south side parts', 'loop luxury autos',
            'west town wheels', 'rosemont', 'evanston', 'skokie'
        ]
        
        # Suspicious patterns that might indicate hallucination
        self.suspicious_patterns = [
            r'\$\d{4,}',  # Prices over $999
            r'stock:\s*-\d+',  # Negative stock
            r'year:\s*\d{5,}',  # Years over 9999
            r'sku:\s*[^a-zA-Z0-9-]',  # Invalid SKU format
            r'location:\s*[^a-zA-Z\s]',  # Invalid location format
            r'part:\s*[^a-zA-Z0-9\s-]',  # Invalid part name format
        ]
    
    def detect_hallucination(self, query: str, response: Dict) -> Dict:
        """
        Detect potential hallucinations in the response
        Returns confidence score and detected issues
        """
        issues = []
        confidence_score = 1.0
        
        # Extract text to analyze
        response_text = str(response).lower()
        part_name = response.get('part', '').lower()
        location = response.get('location', '').lower()
        price = response.get('price', 0)
        stock = response.get('stock', 0)
        
        # Check 1: Valid part patterns
        if not any(re.search(pattern, part_name) for pattern in self.valid_part_patterns):
            if part_name and part_name != 'no exact match found':
                issues.append("Part name doesn't match known patterns")
                confidence_score -= 0.2
        
        # Check 2: Valid car makes/models
        query_lower = query.lower()
        car_mentioned = any(car in query_lower for car in self.valid_cars)
        if car_mentioned:
            part_car_match = any(car in part_name for car in self.valid_cars)
            if not part_car_match:
                issues.append("Part doesn't match car mentioned in query")
                confidence_score -= 0.15
        
        # Check 3: Reasonable price range
        if price > 2000:
            issues.append(f"Price ${price} seems unusually high")
            confidence_score -= 0.1
        elif price < 0:
            issues.append("Negative price detected")
            confidence_score -= 0.3
        
        # Check 4: Reasonable stock levels
        if stock > 1000:
            issues.append(f"Stock level {stock} seems unusually high")
            confidence_score -= 0.1
        elif stock < 0:
            issues.append("Negative stock detected")
            confidence_score -= 0.2
        
        # Check 5: Valid location
        if location and not any(loc in location for loc in self.valid_locations):
            issues.append(f"Unknown location: {location}")
            confidence_score -= 0.1
        
        # Check 6: Suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, response_text):
                issues.append(f"Suspicious pattern detected: {pattern}")
                confidence_score -= 0.2
        
        # Check 7: Response coherence
        if not self._check_coherence(query, response):
            issues.append("Response lacks coherence with query")
            confidence_score -= 0.25
        
        # Ensure confidence is between 0 and 1
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        return {
            "confidence_score": confidence_score,
            "issues": issues,
            "is_hallucination": confidence_score < 0.7,
            "risk_level": self._get_risk_level(confidence_score),
            "timestamp": datetime.now().isoformat()
        }
    
    def _check_coherence(self, query: str, response: Dict) -> bool:
        """Check if response is coherent with the query"""
        query_lower = query.lower()
        part_name = response.get('part', '').lower()
        
        # Extract key terms from query
        query_terms = set(re.findall(r'\b\w+\b', query_lower))
        part_terms = set(re.findall(r'\b\w+\b', part_name))
        
        # Check for overlap
        overlap = len(query_terms.intersection(part_terms))
        return overlap > 0 or len(query_terms) < 3  # Allow for very short queries
    
    def _get_risk_level(self, confidence_score: float) -> str:
        """Get risk level based on confidence score"""
        if confidence_score >= 0.9:
            return "🟢 Low Risk"
        elif confidence_score >= 0.7:
            return "🟡 Medium Risk"
        else:
            return "🔴 High Risk"
    
    def generate_hallucination_report(self, queries_responses: List[Tuple[str, Dict]]) -> Dict:
        """Generate a comprehensive hallucination report for demo"""
        total_queries = len(queries_responses)
        hallucination_count = 0
        total_confidence = 0
        risk_distribution = {"🟢 Low Risk": 0, "🟡 Medium Risk": 0, "🔴 High Risk": 0}
        
        detailed_results = []
        
        for query, response in queries_responses:
            detection_result = self.detect_hallucination(query, response)
            detailed_results.append({
                "query": query,
                "response": response,
                "detection": detection_result
            })
            
            if detection_result["is_hallucination"]:
                hallucination_count += 1
            
            total_confidence += detection_result["confidence_score"]
            risk_distribution[detection_result["risk_level"]] += 1
        
        hallucination_rate = (hallucination_count / total_queries) * 100 if total_queries > 0 else 0
        avg_confidence = total_confidence / total_queries if total_queries > 0 else 0
        
        return {
            "summary": {
                "total_queries": total_queries,
                "hallucination_count": hallucination_count,
                "hallucination_rate": f"{hallucination_rate:.1f}%",
                "average_confidence": f"{avg_confidence:.3f}",
                "risk_distribution": risk_distribution
            },
            "detailed_results": detailed_results,
            "timestamp": datetime.now().isoformat(),
            "detector_version": "1.0.0"
        }

# Global detector instance
hallucination_detector = HallucinationDetector()

def detect_response_hallucination(query: str, response: Dict) -> Dict:
    """Convenience function to detect hallucinations"""
    return hallucination_detector.detect_hallucination(query, response)

def generate_demo_hallucination_report() -> Dict:
    """Generate a demo hallucination report with sample data"""
    sample_queries_responses = [
        ("brake pads Honda Civic", {"part": "Brake Pads 2019 Honda Civic", "stock": 5, "price": 45, "location": "Chicago North"}),
        ("alternator Ford F-150", {"part": "Alternator 2018 Ford F-150", "stock": 2, "price": 120, "location": "O'Hare Auto"}),
        ("oil filter Toyota Camry", {"part": "Oil Filter Toyota Camry", "stock": 8, "price": 12, "location": "Logan Square Motors"}),
        ("turbo 1998 Honda Civic", {"part": "Turbocharger 1998 Honda Civic", "stock": 0, "price": 350, "location": "Wrigley Dealership"}),
        ("spark plugs BMW", {"part": "Spark Plugs BMW 3 Series", "stock": 4, "price": 8, "location": "Loop Luxury Autos"}),
    ]
    
    return hallucination_detector.generate_hallucination_report(sample_queries_responses)

if __name__ == "__main__":
    print("🔍 Lester's Hallucination Detector Demo")
    print("=" * 50)
    
    # Test with sample data
    report = generate_demo_hallucination_report()
    
    print(f"📊 Hallucination Report:")
    print(f"  Total Queries: {report['summary']['total_queries']}")
    print(f"  Hallucination Rate: {report['summary']['hallucination_rate']}")
    print(f"  Average Confidence: {report['summary']['average_confidence']}")
    print(f"  Risk Distribution: {report['summary']['risk_distribution']}")
    
    print(f"\n🔍 Detailed Results:")
    for result in report['detailed_results']:
        detection = result['detection']
        print(f"  Query: {result['query']}")
        print(f"    Confidence: {detection['confidence_score']:.3f}")
        print(f"    Risk: {detection['risk_level']}")
        if detection['issues']:
            print(f"    Issues: {', '.join(detection['issues'])}")
        print()
    
    print("✅ Hallucination detection system ready for demo!")
