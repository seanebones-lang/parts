"""
Demo Logging System - Enterprise Edition
Professional logging for demo traceability and audit trails
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

# Setup professional logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/demo.log', mode='a'),
        logging.StreamHandler()
    ]
)

# Create specialized loggers
demo_logger = logging.getLogger('parts_demo')
query_logger = logging.getLogger('query_tracking')
performance_logger = logging.getLogger('performance')

class DemoLogger:
    """Professional logging for the parts demo system"""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.query_count = 0
        
    def log_query(self, query: str, result: Dict[str, Any], color: str, processing_time_ms: int) -> Dict[str, Any]:
        """Log RAG query interactions for audit trail"""
        self.query_count += 1
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "session_id": self.session_id,
            "query_id": f"Q{self.query_count:03d}",
            "timestamp": timestamp,
            "query": query,
            "response": result.get("response", ""),
            "color": color,
            "confidence": result.get("confidence", 0),
            "processing_time_ms": processing_time_ms,
            "suggestions": result.get("suggestions", []),
            "inventory_matches": len(result.get("inventory_matches", [])),
            "status": "success"
        }
        
        # Log to file and console
        query_logger.info(f"Query {self.query_count}: {query} -> {color} ({processing_time_ms}ms)")
        demo_logger.info(f"RAG Query: {json.dumps(log_entry)}")
        
        return log_entry
    
    def log_error(self, query: str, error: str, processing_time_ms: int = 0) -> Dict[str, Any]:
        """Log query errors"""
        self.query_count += 1
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "session_id": self.session_id,
            "query_id": f"Q{self.query_count:03d}",
            "timestamp": timestamp,
            "query": query,
            "error": error,
            "processing_time_ms": processing_time_ms,
            "status": "error"
        }
        
        query_logger.error(f"Query {self.query_count} FAILED: {query} -> {error}")
        demo_logger.error(f"RAG Error: {json.dumps(log_entry)}")
        
        return log_entry
    
    def log_performance(self, operation: str, duration_ms: int, details: Dict[str, Any] = None):
        """Log performance metrics"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "session_id": self.session_id,
            "timestamp": timestamp,
            "operation": operation,
            "duration_ms": duration_ms,
            "details": details or {}
        }
        
        performance_logger.info(f"Performance: {operation} took {duration_ms}ms")
        demo_logger.info(f"Performance: {json.dumps(log_entry)}")
    
    def log_demo_event(self, event: str, details: Dict[str, Any] = None):
        """Log demo-specific events"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "session_id": self.session_id,
            "timestamp": timestamp,
            "event": event,
            "details": details or {}
        }
        
        demo_logger.info(f"Demo Event: {event}")
        demo_logger.info(f"Demo Details: {json.dumps(log_entry)}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current demo session"""
        return {
            "session_id": self.session_id,
            "query_count": self.query_count,
            "session_duration": f"Started at {self.session_id}",
            "log_file": "logs/demo.log"
        }

# Global logger instance
demo_logger_instance = DemoLogger()

def log_query(query: str, result: Dict[str, Any], color: str, processing_time_ms: int) -> Dict[str, Any]:
    """Convenience function for logging queries"""
    return demo_logger_instance.log_query(query, result, color, processing_time_ms)

def log_error(query: str, error: str, processing_time_ms: int = 0) -> Dict[str, Any]:
    """Convenience function for logging errors"""
    return demo_logger_instance.log_error(query, error, processing_time_ms)

def log_performance(operation: str, duration_ms: int, details: Dict[str, Any] = None):
    """Convenience function for logging performance"""
    demo_logger_instance.log_performance(operation, duration_ms, details)

def log_demo_event(event: str, details: Dict[str, Any] = None):
    """Convenience function for logging demo events"""
    demo_logger_instance.log_demo_event(event, details)

def get_session_summary() -> Dict[str, Any]:
    """Get current session summary"""
    return demo_logger_instance.get_session_summary()

# Demo event logging functions
def log_demo_start():
    """Log demo session start"""
    log_demo_event("demo_started", {
        "version": "1.0.0",
        "features": ["RAG", "traffic_light", "multi_location", "confidence_scoring"]
    })

def log_demo_end():
    """Log demo session end"""
    summary = get_session_summary()
    log_demo_event("demo_ended", summary)

def log_color_distribution(queries: list):
    """Log color distribution for analytics"""
    colors = {"🟢": 0, "🟡": 0, "🔴": 0}
    
    for query in queries:
        if "color" in query:
            color = query["color"]
            if "🟢" in color:
                colors["🟢"] += 1
            elif "🟡" in color:
                colors["🟡"] += 1
            elif "🔴" in color:
                colors["🔴"] += 1
    
    log_demo_event("color_distribution", colors)

if __name__ == "__main__":
    # Test the logging system
    print("🚀 Testing Lester's Demo Logging System")
    print("=" * 50)
    
    # Log demo start
    log_demo_start()
    
    # Test query logging
    test_result = {
        "response": "Found brake pads for 2019 Honda Civic at Chicago North",
        "confidence": 0.85,
        "suggestions": ["Generate invoice", "Process payment"],
        "inventory_matches": [{"sku": "BP-HC19", "stock": 5}]
    }
    
    log_entry = log_query("brake pads for 2019 Honda Civic", test_result, "🟢 Auto-resolved", 150)
    print(f"✅ Logged query: {log_entry['query_id']}")
    
    # Test performance logging
    log_performance("vector_search", 45, {"results_found": 3})
    
    # Test error logging
    log_error("invalid query", "No matching parts found", 25)
    
    # Get session summary
    summary = get_session_summary()
    print(f"📊 Session summary: {summary}")
    
    # Log demo end
    log_demo_end()
    
    print("✅ Logging system test complete!")
    print("📁 Check logs/demo.log for detailed logs")
