"""FastAPI main application for Romanian Freight Forwarder Automation System"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
        
        yield
        
    finally:
        # Shutdown
        logger.info("🛑 Shutting down application")
        await close_db()
        logger.info("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered logistics automation platform for Romanian freight forwarders",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# Add custom exception handling middleware
app.add_middleware(ExceptionHandlerMiddleware)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


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
