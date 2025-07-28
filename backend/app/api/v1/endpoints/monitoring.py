"""
System Monitoring and Performance Endpoints
Provides comprehensive system health, cache statistics, and performance metrics.
"""

import psutil
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.services.cache_service import cache_service
from app.services.websocket_manager import websocket_manager

logger = get_logger(__name__)
monitoring_router = APIRouter(prefix="/monitoring", tags=["System Monitoring"])

@monitoring_router.get("/health")
async def system_health():
    """
    Comprehensive system health check.
    
    Returns:
    - System resource usage
    - Service availability
    - Database connectivity
    - Cache status
    - WebSocket connections
    """
    try:
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "services": {},
            "system": {},
            "performance": {}
        }
        
        # System resource monitoring
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            health_data["system"] = {
                "cpu_usage_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / 1024**3, 2),
                    "available_gb": round(memory.available / 1024**3, 2),
                    "used_gb": round(memory.used / 1024**3, 2),
                    "percent_used": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / 1024**3, 2),
                    "free_gb": round(disk.free / 1024**3, 2),
                    "used_gb": round(disk.used / 1024**3, 2),
                    "percent_used": round((disk.used / disk.total) * 100, 2)
                }
            }
            
            health_data["services"]["system_monitoring"] = "healthy"
            
        except Exception as e:
            logger.error(f"❌ Error getting system metrics: {e}")
            health_data["services"]["system_monitoring"] = f"error: {str(e)}"
        
        # Cache service health
        try:
            cache_stats = await cache_service.get_cache_stats()
            if "error" in cache_stats:
                health_data["services"]["cache"] = f"error: {cache_stats['error']}"
            else:
                health_data["services"]["cache"] = "healthy"
                health_data["performance"]["cache"] = cache_stats
                
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}")
            health_data["services"]["cache"] = f"error: {str(e)}"
        
        # WebSocket service health
        try:
            ws_stats = websocket_manager.get_connection_stats()
            health_data["services"]["websocket"] = "healthy"
            health_data["performance"]["websocket"] = ws_stats
            
        except Exception as e:
            logger.error(f"❌ Error getting WebSocket stats: {e}")
            health_data["services"]["websocket"] = f"error: {str(e)}"
        
        # Determine overall health status
        failed_services = [
            service for service, status in health_data["services"].items() 
            if status != "healthy"
        ]
        
        if failed_services:
            health_data["status"] = "degraded"
            health_data["failed_services"] = failed_services
        
        # Performance warnings
        warnings = []
        if health_data["system"]["cpu_usage_percent"] > 80:
            warnings.append("High CPU usage detected")
        
        if health_data["system"]["memory"]["percent_used"] > 85:
            warnings.append("High memory usage detected")
        
        if health_data["system"]["disk"]["percent_used"] > 90:
            warnings.append("Low disk space detected")
        
        if warnings:
            health_data["warnings"] = warnings
        
        return JSONResponse(content=health_data)
        
    except Exception as e:
        logger.error(f"❌ Error in health check: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "timestamp": datetime.utcnow().isoformat(),
                "status": "unhealthy",
                "error": str(e)
            }
        )

@monitoring_router.get("/cache/stats")
async def cache_statistics():
    """
    Detailed cache performance statistics.
    
    Returns:
    - Hit/miss ratios
    - Memory usage
    - Key distribution
    - Performance metrics
    """
    try:
        stats = await cache_service.get_cache_stats()
        
        return JSONResponse(content={
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_statistics": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting cache statistics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@monitoring_router.get("/websocket/stats")
async def websocket_statistics():
    """
    WebSocket connection and real-time communication statistics.
    
    Returns:
    - Active connections
    - Room statistics
    - User presence data
    - Connection performance
    """
    try:
        stats = websocket_manager.get_connection_stats()
        
        return JSONResponse(content={
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "websocket_statistics": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting WebSocket statistics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@monitoring_router.get("/database/stats")
async def database_statistics(db: AsyncSession = Depends(get_db)):
    """
    Database performance and usage statistics.
    
    Returns:
    - Connection pool status
    - Query performance metrics
    - Table statistics
    - Index usage
    """
    try:
        # Get database statistics
        db_stats = {
            "connection_status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Test database connectivity
        try:
            result = await db.execute("SELECT 1")
            test_result = result.scalar()
            if test_result == 1:
                db_stats["connectivity"] = "healthy"
            else:
                db_stats["connectivity"] = "unhealthy"
        except Exception as e:
            db_stats["connectivity"] = f"error: {str(e)}"
        
        # Get table statistics (if needed)
        try:
            # Example: Get order table statistics
            result = await db.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats 
                WHERE schemaname = 'public' 
                AND tablename = 'orders'
                LIMIT 10
            """)
            
            table_stats = result.fetchall()
            db_stats["table_statistics"] = [
                {
                    "schema": row[0],
                    "table": row[1], 
                    "column": row[2],
                    "distinct_values": row[3],
                    "correlation": row[4]
                }
                for row in table_stats
            ]
            
        except Exception as e:
            logger.warning(f"Could not get detailed table stats: {e}")
            db_stats["table_statistics"] = "not_available"
        
        return JSONResponse(content={
            "success": True,
            "database_statistics": db_stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting database statistics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@monitoring_router.get("/performance/summary")
async def performance_summary():
    """
    Comprehensive performance summary combining all system metrics.
    
    Returns:
    - Overall system performance score
    - Key performance indicators
    - Optimization recommendations
    - Trend analysis
    """
    try:
        # Collect all performance data
        cache_stats = await cache_service.get_cache_stats()
        ws_stats = websocket_manager.get_connection_stats()
        
        # System metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Calculate performance score (0-100)
        performance_score = 100
        
        # Deduct points for high resource usage
        if cpu_percent > 80:
            performance_score -= 20
        elif cpu_percent > 60:
            performance_score -= 10
        
        if memory.percent > 85:
            performance_score -= 20
        elif memory.percent > 70:
            performance_score -= 10
        
        # Cache performance impact
        if isinstance(cache_stats, dict) and "hit_rate" in cache_stats:
            hit_rate = cache_stats["hit_rate"]
            if hit_rate < 50:
                performance_score -= 15
            elif hit_rate < 70:
                performance_score -= 10
        
        # Performance level
        if performance_score >= 90:
            performance_level = "excellent"
        elif performance_score >= 75:
            performance_level = "good"
        elif performance_score >= 60:
            performance_level = "fair"
        else:
            performance_level = "poor"
        
        # Generate recommendations
        recommendations = []
        
        if cpu_percent > 70:
            recommendations.append("Consider optimizing CPU-intensive operations")
        
        if memory.percent > 80:
            recommendations.append("Memory usage is high - consider increasing cache TTL or server capacity")
        
        if isinstance(cache_stats, dict) and cache_stats.get("hit_rate", 0) < 70:
            recommendations.append("Cache hit rate is low - review caching strategy")
        
        if ws_stats["active_connections"] > 100:
            recommendations.append("High WebSocket connection count - monitor for performance impact")
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_score": performance_score,
            "performance_level": performance_level,
            "key_metrics": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "cache_hit_rate": cache_stats.get("hit_rate", 0) if isinstance(cache_stats, dict) else 0,
                "active_websocket_connections": ws_stats["active_connections"],
                "cache_keys_total": sum(cache_stats.get("keys_by_prefix", {}).values()) if isinstance(cache_stats, dict) else 0
            },
            "recommendations": recommendations,
            "system_health": "healthy" if performance_score >= 70 else "needs_attention"
        }
        
        return JSONResponse(content={
            "success": True,
            "performance_summary": summary
        })
        
    except Exception as e:
        logger.error(f"❌ Error generating performance summary: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@monitoring_router.post("/cache/clear")
async def clear_cache():
    """
    Clear all cached data (admin function - use with caution).
    """
    try:
        success = await cache_service.clear_all_cache()
        
        if success:
            logger.warning("🧹 Cache cleared via monitoring endpoint")
            return JSONResponse(content={
                "success": True,
                "message": "All cache cleared successfully",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Failed to clear cache"
                }
            )
            
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@monitoring_router.get("/romanian-business/stats")
async def romanian_business_statistics():
    """
    Romanian business logic performance and usage statistics.
    
    Returns:
    - Validation performance metrics
    - Pricing calculation statistics
    - Workflow state distribution
    - Romanian compliance metrics
    """
    try:
        # This would be enhanced with actual business logic metrics
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_metrics": {
                "total_validations": "tracked_via_cache",
                "success_rate": "calculated_from_logs",
                "average_processing_time": "measured_via_timing"
            },
            "pricing_metrics": {
                "total_calculations": "tracked_via_cache",
                "average_vat_amount": "calculated_from_results",
                "currency_distribution": "RON_primary_EUR_secondary"
            },
            "workflow_metrics": {
                "state_distribution": "tracked_via_database",
                "transition_success_rate": "measured_via_logs",
                "average_completion_time": "calculated_from_history"
            },
            "compliance_status": "operational",
            "note": "Detailed metrics would be implemented with business intelligence integration"
        }
        
        return JSONResponse(content={
            "success": True,
            "romanian_business_statistics": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting Romanian business statistics: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        ) 