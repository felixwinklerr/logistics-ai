"""Main API router configuration"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, orders
from app.api.v1.endpoints.monitoring import monitoring_router

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(monitoring_router, tags=["System Monitoring"])
