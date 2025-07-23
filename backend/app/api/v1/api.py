"""API v1 router configuration"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, orders
from app.api.v1 import ai, subcontractors

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(subcontractors.router, prefix="/subcontractors", tags=["subcontractors"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Document Processing"]) 