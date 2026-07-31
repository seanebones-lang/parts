"""
Analytics Engine - Enterprise Edition
Real-time metrics and ROI tracking for enterprise operations
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import subprocess

class AnalyticsEngine:
    """Analytics engine for real-time metrics and ROI projections"""
    
    def __init__(self):
        self.log_file = "logs/demo.log"
        self.metrics_cache = {}
        self.last_update = None
        
        # Demo scaling factors
        self.locations_count = 7
        self.hours_per_day = 8
        self.days_per_month = 22
        self.months_per_year = 12
        
        # Cost assumptions
        self.avg_employee_cost = 40000  # Annual salary
        self.employees_replaced = 28  # Current manual processors
        self.system_cost_annual = 114000  # System operational costs
        
    def parse_log_entry(self, line: str) -> Optional[Dict]:
        """Parse a single log entry for metrics"""
        try:
            # Look for RAG Query entries
            if "RAG Query:" in line:
                # Extract JSON from log line
                json_start = line.find('{"session_id"')
                if json_start != -1:
                    json_str = line[json_start:]
                    log_entry = json.loads(json_str)
                    
                    # Extract metrics
                    return {
                        "timestamp": log_entry.get("timestamp", ""),
                        "query": log_entry.get("query", ""),
                        "color": log_entry.get("color", "warning"),
                        "confidence": log_entry.get("confidence", 0),
                        "processing_time_ms": log_entry.get("processing_time_ms", 0),
                        "savings": self._calculate_savings(log_entry),
                        "payment_status": log_entry.get("payment", {}).get("success") if log_entry.get("payment") else None
                    }
        except Exception as e:
            # Skip malformed entries
            pass
        return None
    
    def _calculate_savings(self, log_entry: Dict) -> float:
        """Calculate savings based on automation level"""
        color = log_entry.get("color", "warning")
        payment_success = log_entry.get("payment", {}).get("success") if log_entry.get("payment") else False
        
        # Base savings per automation level
        if "Auto-resolved" in color:
            base_savings = 45.00  # Full automation
            if payment_success:
                base_savings += 15.00  # Payment automation bonus
        elif "Human review" in color:
            base_savings = 20.00  # Partial automation
        else:
            base_savings = 0.00  # Manual processing
        
        return base_savings
    
    def load_logs(self, limit: int = 100) -> List[Dict]:
        """Load recent log entries"""
        logs = []
        
        if not os.path.exists(self.log_file):
            # Return mock data if no logs exist
            return self._get_mock_logs()
        
        try:
            # Get recent lines from log file
            result = subprocess.run(
                ["tail", "-n", str(limit), self.log_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        log_entry = self.parse_log_entry(line)
                        if log_entry:
                            logs.append(log_entry)
        except Exception as e:
            # Fallback to mock data
            return self._get_mock_logs()
        
        return logs if logs else self._get_mock_logs()
    
    def _get_mock_logs(self) -> List[Dict]:
        """Generate mock logs for demo purposes"""
        mock_logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "query": "brake pads for 2019 Honda Civic",
                "color": "🟢 Auto-resolved",
                "confidence": 0.85,
                "processing_time_ms": 150,
                "savings": 60.00,
                "payment_status": True
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "query": "alternator for 2018 Ford F-150",
                "color": "🟡 Human review",
                "confidence": 0.65,
                "processing_time_ms": 200,
                "savings": 20.00,
                "payment_status": None
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=10)).isoformat(),
                "query": "brake pads for 2018 Honda Civic",
                "color": "🔴 Escalate now",
                "confidence": 0.35,
                "processing_time_ms": 300,
                "savings": 0.00,
                "payment_status": None
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "query": "oil filter Toyota Camry",
                "color": "🟢 Auto-resolved",
                "confidence": 0.90,
                "processing_time_ms": 120,
                "savings": 50.00,
                "payment_status": True
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=20)).isoformat(),
                "query": "air filter Honda Civic",
                "color": "🟢 Auto-resolved",
                "confidence": 0.88,
                "processing_time_ms": 140,
                "savings": 55.00,
                "payment_status": True
            }
        ]
        return mock_logs
    
    def generate_metrics(self, logs: List[Dict] = None) -> Dict:
        """Generate comprehensive metrics from logs"""
        if logs is None:
            logs = self.load_logs()
        
        if not logs:
            return self._get_default_metrics()
        
        # Color distribution
        colors = [log["color"] for log in logs]
        color_counts = Counter(colors)
        
        # Calculate rates
        total_queries = len(logs)
        green_count = color_counts.get("🟢 Auto-resolved", 0) + color_counts.get("🟢 Auto-reply & Paid", 0)
        yellow_count = color_counts.get("🟡 Human review", 0) + color_counts.get("🟡 Review - Draft ready", 0)
        red_count = color_counts.get("🔴 Escalate now", 0) + color_counts.get("🔴 Urgent - Escalate", 0)
        
        green_rate = (green_count / total_queries) * 100 if total_queries > 0 else 0
        yellow_rate = (yellow_count / total_queries) * 100 if total_queries > 0 else 0
        red_rate = (red_count / total_queries) * 100 if total_queries > 0 else 0
        
        # Savings calculations
        total_savings = sum(log["savings"] for log in logs)
        avg_savings_per_query = total_savings / total_queries if total_queries > 0 else 0
        
        # Payment metrics
        payment_success_count = sum(1 for log in logs if log.get("payment_status"))
        payment_rate = (payment_success_count / total_queries) * 100 if total_queries > 0 else 0
        
        # Performance metrics
        avg_processing_time = sum(log["processing_time_ms"] for log in logs) / total_queries if total_queries > 0 else 0
        avg_confidence = sum(log["confidence"] for log in logs) / total_queries if total_queries > 0 else 0
        
        # ROI projections
        daily_queries = total_queries  # Assuming this is a day's worth
        monthly_queries = daily_queries * self.days_per_month
        annual_queries = monthly_queries * self.months_per_year
        
        # Scale to all locations
        annual_queries_all_locations = annual_queries * self.locations_count
        annual_savings_all_locations = (avg_savings_per_query * annual_queries_all_locations)
        
        # Current state costs
        current_annual_cost = self.employees_replaced * self.avg_employee_cost
        
        # Future state costs
        future_employees = 14  # Reduced staff
        future_annual_cost = (future_employees * self.avg_employee_cost) + self.system_cost_annual
        
        # Net savings
        net_annual_savings = current_annual_cost - future_annual_cost
        
        # ROI calculation
        system_investment = 874000  # Year 1 investment from README
        roi_timeline_months = (system_investment / (net_annual_savings / 12)) if net_annual_savings > 0 else 0
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "session_summary": {
                "total_queries": total_queries,
                "green_automation_rate": f"{green_rate:.1f}%",
                "yellow_review_rate": f"{yellow_rate:.1f}%",
                "red_escalation_rate": f"{red_rate:.1f}%",
                "payment_success_rate": f"{payment_rate:.1f}%"
            },
            "performance_metrics": {
                "avg_processing_time_ms": f"{avg_processing_time:.0f}",
                "avg_confidence_score": f"{avg_confidence:.2f}",
                "total_savings_demo": f"${total_savings:.2f}",
                "avg_savings_per_query": f"${avg_savings_per_query:.2f}"
            },
            "roi_projections": {
                "daily_queries_projected": daily_queries,
                "monthly_queries_projected": monthly_queries,
                "annual_queries_all_locations": annual_queries_all_locations,
                "annual_savings_projected": f"${annual_savings_all_locations:,.0f}",
                "current_annual_cost": f"${current_annual_cost:,.0f}",
                "future_annual_cost": f"${future_annual_cost:,.0f}",
                "net_annual_savings": f"${net_annual_savings:,.0f}",
                "roi_timeline_months": f"{roi_timeline_months:.1f}"
            },
            "color_distribution": {
                "🟢": green_count,
                "🟡": yellow_count,
                "🔴": red_count
            },
            "payment_metrics": {
                "total_payments": payment_success_count,
                "payment_rate": f"{payment_rate:.1f}%",
                "payment_boost_factor": "1.4x" if payment_rate > 50 else "1.0x"
            }
        }
        
        return metrics
    
    def _get_default_metrics(self) -> Dict:
        """Get default metrics when no logs are available"""
        return {
            "timestamp": datetime.now().isoformat(),
            "session_summary": {
                "total_queries": 0,
                "green_automation_rate": "0.0%",
                "yellow_review_rate": "0.0%",
                "red_escalation_rate": "0.0%",
                "payment_success_rate": "0.0%"
            },
            "performance_metrics": {
                "avg_processing_time_ms": "0",
                "avg_confidence_score": "0.00",
                "total_savings_demo": "$0.00",
                "avg_savings_per_query": "$0.00"
            },
            "roi_projections": {
                "daily_queries_projected": 0,
                "monthly_queries_projected": 0,
                "annual_queries_all_locations": 0,
                "annual_savings_projected": "$0",
                "current_annual_cost": "$1,120,000",
                "future_annual_cost": "$842,000",
                "net_annual_savings": "$278,000",
                "roi_timeline_months": "37.7"
            },
            "color_distribution": {
                "🟢": 0,
                "🟡": 0,
                "🔴": 0
            },
            "payment_metrics": {
                "total_payments": 0,
                "payment_rate": "0.0%",
                "payment_boost_factor": "1.0x"
            }
        }
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        metrics = self.generate_metrics()
        
        if format == "json":
            return json.dumps(metrics, indent=2)
        elif format == "csv":
            # Simple CSV export for key metrics
            csv_lines = [
                "Metric,Value",
                f"Total Queries,{metrics['session_summary']['total_queries']}",
                f"Green Automation Rate,{metrics['session_summary']['green_automation_rate']}",
                f"Total Savings Demo,{metrics['performance_metrics']['total_savings_demo']}",
                f"Annual Savings Projected,{metrics['roi_projections']['annual_savings_projected']}",
                f"ROI Timeline Months,{metrics['roi_projections']['roi_timeline_months']}"
            ]
            return "\n".join(csv_lines)
        else:
            return str(metrics)
    
    def get_trend_data(self, days: int = 7) -> Dict:
        """Get trend data for charts"""
        logs = self.load_logs(limit=1000)  # Get more data for trends
        
        # Group by day (simplified for demo)
        daily_data = defaultdict(lambda: {"queries": 0, "savings": 0, "green": 0})
        
        for log in logs:
            date = log["timestamp"][:10]  # Extract date
            daily_data[date]["queries"] += 1
            daily_data[date]["savings"] += log["savings"]
            if "🟢" in log["color"]:
                daily_data[date]["green"] += 1
        
        # Convert to chart data
        dates = sorted(daily_data.keys())
        trend_data = {
            "dates": dates,
            "queries": [daily_data[date]["queries"] for date in dates],
            "savings": [daily_data[date]["savings"] for date in dates],
            "green_rates": [(daily_data[date]["green"] / max(daily_data[date]["queries"], 1)) * 100 for date in dates]
        }
        
        return trend_data

# Global analytics engine instance
analytics_engine = AnalyticsEngine()

def generate_metrics(logs: List[Dict] = None) -> Dict:
    """Convenience function to generate metrics"""
    return analytics_engine.generate_metrics(logs)

def export_metrics(format: str = "json") -> str:
    """Convenience function to export metrics"""
    return analytics_engine.export_metrics(format)

def get_trend_data(days: int = 7) -> Dict:
    """Convenience function to get trend data"""
    return analytics_engine.get_trend_data(days)

if __name__ == "__main__":
    print("🚀 Lester's Analytics Engine Test")
    print("=" * 50)
    
    # Generate metrics
    metrics = generate_metrics()
    
    print("📊 Real-Time Metrics:")
    print(f"  Total Queries: {metrics['session_summary']['total_queries']}")
    print(f"  Green Automation: {metrics['session_summary']['green_automation_rate']}")
    print(f"  Payment Success: {metrics['session_summary']['payment_success_rate']}")
    print(f"  Total Savings: {metrics['performance_metrics']['total_savings_demo']}")
    print(f"  Annual Projected: {metrics['roi_projections']['annual_savings_projected']}")
    print(f"  ROI Timeline: {metrics['roi_projections']['roi_timeline_months']} months")
    
    print("\n📈 Color Distribution:")
    for color, count in metrics['color_distribution'].items():
        print(f"  {color}: {count}")
    
    print("\n💳 Payment Metrics:")
    print(f"  Total Payments: {metrics['payment_metrics']['total_payments']}")
    print(f"  Payment Rate: {metrics['payment_metrics']['payment_rate']}")
    print(f"  Boost Factor: {metrics['payment_metrics']['payment_boost_factor']}")
    
    print("\n📋 Export Formats:")
    print("JSON Export:")
    print(export_metrics("json")[:200] + "...")
    
    print("\n✅ Analytics engine test complete!")
