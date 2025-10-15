"""
API rate limiting middleware and service.
"""

import time
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
import asyncio


class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests: Dict[str, deque] = defaultdict(deque)
        self.hour_requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, float] = {}
        self.block_duration = 3600  # 1 hour
    
    def _cleanup_old_requests(self, requests: deque, max_age: float):
        """Remove old requests from the deque."""
        current_time = time.time()
        while requests and requests[0] < current_time - max_age:
            requests.popleft()
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get real IP from headers (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def is_rate_limited(self, request: Request) -> tuple[bool, Optional[str]]:
        """Check if request should be rate limited."""
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Check if IP is blocked
        if client_id in self.blocked_ips:
            if current_time < self.blocked_ips[client_id]:
                return True, f"IP blocked until {self.blocked_ips[client_id]}"
            else:
                # Remove expired block
                del self.blocked_ips[client_id]
        
        # Clean up old requests
        self._cleanup_old_requests(self.minute_requests[client_id], 60)
        self._cleanup_old_requests(self.hour_requests[client_id], 3600)
        
        # Check minute limit
        if len(self.minute_requests[client_id]) >= self.requests_per_minute:
            # Block IP for excessive requests
            self.blocked_ips[client_id] = current_time + self.block_duration
            return True, "Rate limit exceeded - IP blocked for 1 hour"
        
        # Check hour limit
        if len(self.hour_requests[client_id]) >= self.requests_per_hour:
            return True, "Hourly rate limit exceeded"
        
        # Add current request
        self.minute_requests[client_id].append(current_time)
        self.hour_requests[client_id].append(current_time)
        
        return False, None
    
    def get_rate_limit_info(self, request: Request) -> Dict[str, int]:
        """Get rate limit information for client."""
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Clean up old requests
        self._cleanup_old_requests(self.minute_requests[client_id], 60)
        self._cleanup_old_requests(self.hour_requests[client_id], 3600)
        
        return {
            "requests_per_minute": len(self.minute_requests[client_id]),
            "requests_per_hour": len(self.hour_requests[client_id]),
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
            "remaining_minute": max(0, self.requests_per_minute - len(self.minute_requests[client_id])),
            "remaining_hour": max(0, self.requests_per_hour - len(self.hour_requests[client_id]))
        }


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60, requests_per_hour=1000)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    is_limited, reason = rate_limiter.is_rate_limited(request)
    
    if is_limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": reason,
                "retry_after": 60
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(rate_limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0"
            }
        )
    
    # Add rate limit headers to response
    rate_info = rate_limiter.get_rate_limit_info(request)
    
    response = await call_next(request)
    
    response.headers["X-RateLimit-Limit"] = str(rate_info["minute_limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining_minute"])
    response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
    
    return response


class EndpointRateLimiter:
    """Rate limiter for specific endpoints."""
    
    def __init__(self):
        self.limits: Dict[str, RateLimiter] = {}
    
    def add_endpoint_limit(self, endpoint: str, requests_per_minute: int, requests_per_hour: int):
        """Add rate limit for specific endpoint."""
        self.limits[endpoint] = RateLimiter(requests_per_minute, requests_per_hour)
    
    def check_endpoint_limit(self, request: Request, endpoint: str) -> tuple[bool, Optional[str]]:
        """Check rate limit for specific endpoint."""
        if endpoint not in self.limits:
            return False, None
        
        return self.limits[endpoint].is_rate_limited(request)
    
    def get_endpoint_info(self, request: Request, endpoint: str) -> Dict[str, int]:
        """Get rate limit info for specific endpoint."""
        if endpoint not in self.limits:
            return {}
        
        return self.limits[endpoint].get_rate_limit_info(request)


# Global endpoint rate limiter
endpoint_rate_limiter = EndpointRateLimiter()

# Configure endpoint-specific limits
endpoint_rate_limiter.add_endpoint_limit("/auth/login", 5, 50)  # Stricter limits for login
endpoint_rate_limiter.add_endpoint_limit("/auth/register", 3, 10)  # Very strict for registration
endpoint_rate_limiter.add_endpoint_limit("/barcode/scan", 100, 1000)  # Higher limits for scanning
endpoint_rate_limiter.add_endpoint_limit("/analytics", 30, 200)  # Moderate limits for analytics
endpoint_rate_limiter.add_endpoint_limit("/serialized/search", 50, 500)  # Higher limits for search


def get_rate_limit_info(request: Request) -> Dict[str, any]:
    """Get comprehensive rate limit information."""
    global_info = rate_limiter.get_rate_limit_info(request)
    
    # Get endpoint-specific info if available
    endpoint_info = {}
    for endpoint in endpoint_rate_limiter.limits.keys():
        endpoint_info[endpoint] = endpoint_rate_limiter.get_endpoint_info(request, endpoint)
    
    return {
        "global": global_info,
        "endpoints": endpoint_info,
        "blocked_ips": len(rate_limiter.blocked_ips)
    }
