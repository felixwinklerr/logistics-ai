"""FastAPI main application for Romanian Freight Forwarder Automation System"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from loguru import logger

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1.api import api_router
from app.middleware.exception_handler import (
    ExceptionHandlerMiddleware,
    http_exception_handler,
    validation_exception_handler
)
from app.middleware.security import setup_security_middleware, AuthRateLimitMiddleware


# Configure logging
logging.basicConfig(level=logging.INFO)
logger.add("logs/app.log", rotation="500 MB", level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Romanian Freight Forwarder Automation System")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    try:
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Initialize WebSocket manager
        from app.services.websocket_manager import websocket_manager
        await websocket_manager.initialize()
        logger.info("✅ WebSocket manager initialized")
        
        # Initialize cache service
        from app.services.cache_service import cache_service
        await cache_service.initialize()
        logger.info("✅ Cache service initialized")
        
        yield
        
    finally:
        # Shutdown
        logger.info("🛑 Shutting down application")
        
        # Cleanup WebSocket connections
        from app.services.websocket_manager import websocket_manager
        await websocket_manager.cleanup()
        logger.info("✅ WebSocket connections cleaned up")
        
        # Close cache service
        from app.services.cache_service import cache_service
        await cache_service.close()
        logger.info("✅ Cache service closed")
        
        await close_db()
        logger.info("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Romanian Freight Forwarder Automation API",
    description="Enterprise-grade freight forwarding automation with Romanian business logic",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Include WebSocket routes
from app.api.v1.websockets import websocket_router
app.include_router(websocket_router)

# Setup middleware
setup_security_middleware(app)

# CORS configuration for WebSocket and API access
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend dev servers
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(AuthRateLimitMiddleware)

# Exception handling middleware
app.add_middleware(ExceptionHandlerMiddleware)

# Trusted host middleware
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(422, http_exception_handler)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Romanian Freight Forwarder Automation System",
        "version": settings.version,
        "environment": settings.environment,
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "logistics-ai-backend",
        "version": settings.version,
        "environment": settings.environment
    }


@app.get("/readiness")
async def readiness_check():
    """Readiness check endpoint"""
    # This could include database connectivity checks
    return {
        "status": "ready",
        "service": "logistics-ai-backend",
        "version": settings.version,
        "checks": {
            "database": "connected",  # TODO: Add actual DB check
            "redis": "connected",     # TODO: Add actual Redis check
            "ai_services": "configured"  # TODO: Add AI service checks
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
