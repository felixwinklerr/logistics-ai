"""Security middleware for Romanian Freight Forwarder system"""
import time
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API protection"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds
        self.clients: Dict[str, deque] = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old requests
        client_requests = self.clients[client_ip]
        while client_requests and client_requests[0] <= current_time - self.period:
            client_requests.popleft()
        
        # Check rate limit
        if len(client_requests) >= self.calls:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": int(self.period)
                }
            )
        
        # Add current request
        client_requests.append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(self.calls - len(client_requests))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.period))
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware for enhanced security"""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


def setup_cors_middleware(app):
    """Configure CORS middleware for frontend integration"""
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React development server
            "http://127.0.0.1:3000",
            "http://localhost:5173",  # Vite development server
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "User-Agent",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining", 
            "X-RateLimit-Reset",
        ]
    )


def setup_security_middleware(app):
    """Setup all security middleware"""
    
    # Rate limiting (100 requests per minute per IP)
    app.add_middleware(RateLimitMiddleware, calls=100, period=60)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # CORS configuration
    setup_cors_middleware(app)
    
    logger.info("Security middleware configured")


# Authentication rate limits for sensitive endpoints
class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Stricter rate limiting for authentication endpoints"""
    
    def __init__(self, app, calls: int = 10, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, deque] = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next):
        # Only apply to auth endpoints
        if not request.url.path.startswith("/api/v1/auth/"):
            return await call_next(request)
        
        # Skip health check
        if request.url.path.endswith("/health"):
            return await call_next(request)
        
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old requests
        client_requests = self.clients[client_ip]
        while client_requests and client_requests[0] <= current_time - self.period:
            client_requests.popleft()
        
        # Check auth rate limit (stricter)
        if len(client_requests) >= self.calls:
            logger.warning(f"Auth rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Authentication rate limit exceeded",
                    "retry_after": int(self.period)
                }
            )
        
        # Add current request
        client_requests.append(current_time)
        
        return await call_next(request)
