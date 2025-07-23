"""Health check endpoints"""
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger
import aioredis
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.schemas.health import HealthResponse, ReadinessResponse, ServiceStatus

router = APIRouter()


async def check_database() -> ServiceStatus:
    """Check database connectivity"""
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return ServiceStatus(name="database", status="healthy", message="Connected")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ServiceStatus(name="database", status="unhealthy", message=str(e))


async def check_redis() -> ServiceStatus:
    """Check Redis connectivity"""
    try:
        redis = aioredis.from_url(settings.redis_url)
        await redis.ping()
        await redis.close()
        return ServiceStatus(name="redis", status="healthy", message="Connected")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return ServiceStatus(name="redis", status="unhealthy", message=str(e))


async def check_ai_services() -> ServiceStatus:
    """Check AI services configuration"""
    try:
        if not settings.openai_api_key and not settings.anthropic_api_key:
            return ServiceStatus(
                name="ai_services", 
                status="degraded", 
                message="No AI API keys configured"
            )
        
        # Basic configuration check (not actual API call to save costs)
        configured_services = []
        if settings.openai_api_key:
            configured_services.append("OpenAI")
        if settings.anthropic_api_key:
            configured_services.append("Anthropic")
        if settings.azure_openai_endpoint and settings.azure_openai_key:
            configured_services.append("Azure OpenAI")
            
        message = f"Configured: {', '.join(configured_services)}"
        return ServiceStatus(name="ai_services", status="healthy", message=message)
    except Exception as e:
        logger.error(f"AI services check failed: {e}")
        return ServiceStatus(name="ai_services", status="unhealthy", message=str(e))


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="logistics-ai-backend",
        version=settings.version,
        environment=settings.environment,
        timestamp=datetime.utcnow()
    )


@router.get("/detailed", response_model=ReadinessResponse)
async def detailed_health_check():
    """Detailed health check with service dependencies"""
    start_time = datetime.utcnow()
    
    # Run all checks concurrently
    db_check, redis_check, ai_check = await asyncio.gather(
        check_database(),
        check_redis(), 
        check_ai_services(),
        return_exceptions=True
    )
    
    # Handle any exceptions from gather
    services = []
    overall_status = "healthy"
    
    for check in [db_check, redis_check, ai_check]:
        if isinstance(check, Exception):
            services.append(ServiceStatus(
                name="unknown",
                status="error",
                message=str(check)
            ))
            overall_status = "unhealthy"
        else:
            services.append(check)
            if check.status in ["unhealthy", "error"]:
                overall_status = "unhealthy"
            elif check.status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"
    
    return ReadinessResponse(
        status=overall_status,
        service="logistics-ai-backend", 
        version=settings.version,
        environment=settings.environment,
        timestamp=start_time,
        checks_duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
        services=services
    )


@router.get("/readiness")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        detailed_health = await detailed_health_check()
        if detailed_health.status == "unhealthy":
            raise HTTPException(status_code=503, detail="Service not ready")
        return {"status": "ready"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/liveness")
async def liveness_check():
    """Kubernetes-style liveness probe"""
    return {"status": "alive", "timestamp": datetime.utcnow()} 