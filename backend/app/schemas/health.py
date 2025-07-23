"""Health check Pydantic schemas"""
from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    """Individual service status"""
    name: str = Field(..., description="Service name")
    status: Literal["healthy", "unhealthy", "degraded", "error"] = Field(
        ..., description="Service status"
    )
    message: str = Field(..., description="Status message or error details")


class HealthResponse(BaseModel):
    """Basic health check response"""
    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ..., description="Overall application status"
    )
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment (development/staging/production)")
    timestamp: datetime = Field(..., description="Check timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "logistics-ai-backend",
                "version": "1.0.0",
                "environment": "development",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    }


class ReadinessResponse(HealthResponse):
    """Detailed readiness check response with service dependencies"""
    checks_duration_ms: int = Field(..., description="Time taken for all checks in milliseconds")
    services: List[ServiceStatus] = Field(..., description="Individual service statuses")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "logistics-ai-backend",
                "version": "1.0.0",
                "environment": "development",
                "timestamp": "2024-01-15T10:30:00Z",
                "checks_duration_ms": 245,
                "services": [
                    {
                        "name": "database",
                        "status": "healthy",
                        "message": "Connected"
                    },
                    {
                        "name": "redis",
                        "status": "healthy", 
                        "message": "Connected"
                    },
                    {
                        "name": "ai_services",
                        "status": "healthy",
                        "message": "Configured: OpenAI, Anthropic"
                    }
                ]
            }
        }
    } 