"""
Cache Service for Performance Optimization
Provides Redis-based caching for order data, user sessions, and business logic results.
"""

import json
import pickle
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta
from decimal import Decimal

import redis.asyncio as redis
from loguru import logger

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class CacheService:
    """
    Comprehensive caching service for performance optimization.
    
    Features:
    - Order data caching with TTL
    - Romanian business logic result caching
    - User session caching
    - API response caching
    - Real-time data synchronization
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.default_ttl = 3600  # 1 hour default TTL
        
        # Cache key prefixes for organization
        self.prefixes = {
            "order": "order:",
            "user": "user:",
            "session": "session:",
            "romanian_validation": "ro_validation:",
            "pricing": "pricing:",
            "workflow": "workflow:",
            "api_response": "api:",
            "websocket": "ws:"
        }
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            self.redis = redis.from_url(redis_url, decode_responses=False)
            
            # Test connection
            await self.redis.ping()
            logger.info("✅ Cache service initialized with Redis")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache service: {e}")
            self.redis = None
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("✅ Cache service connection closed")
    
    def _make_key(self, prefix: str, key: str) -> str:
        """Create a prefixed cache key"""
        return f"{self.prefixes.get(prefix, prefix)}{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        if isinstance(value, (dict, list)):
            # Use JSON for simple data structures
            return json.dumps(value, default=self._json_serializer).encode('utf-8')
        else:
            # Use pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value from Redis"""
        try:
            # Try JSON first
            return json.loads(value.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(value)
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for special types"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    async def set(self, prefix: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL"""
        if not self.redis:
            return False
        
        try:
            cache_key = self._make_key(prefix, key)
            serialized_value = self._serialize_value(value)
            
            ttl = ttl or self.default_ttl
            await self.redis.setex(cache_key, ttl, serialized_value)
            
            logger.debug(f"📥 Cached {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting cache {prefix}:{key}: {e}")
            return False
    
    async def get(self, prefix: str, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if not self.redis:
            return None
        
        try:
            cache_key = self._make_key(prefix, key)
            value = await self.redis.get(cache_key)
            
            if value is None:
                logger.debug(f"📤 Cache miss: {cache_key}")
                return None
            
            deserialized = self._deserialize_value(value)
            logger.debug(f"📤 Cache hit: {cache_key}")
            return deserialized
            
        except Exception as e:
            logger.error(f"❌ Error getting cache {prefix}:{key}: {e}")
            return None
    
    async def delete(self, prefix: str, key: str) -> bool:
        """Delete a value from cache"""
        if not self.redis:
            return False
        
        try:
            cache_key = self._make_key(prefix, key)
            deleted = await self.redis.delete(cache_key)
            
            if deleted:
                logger.debug(f"🗑️ Deleted cache: {cache_key}")
            
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"❌ Error deleting cache {prefix}:{key}: {e}")
            return False
    
    async def exists(self, prefix: str, key: str) -> bool:
        """Check if a key exists in cache"""
        if not self.redis:
            return False
        
        try:
            cache_key = self._make_key(prefix, key)
            return bool(await self.redis.exists(cache_key))
        except Exception as e:
            logger.error(f"❌ Error checking cache existence {prefix}:{key}: {e}")
            return False
    
    async def set_with_tags(self, prefix: str, key: str, value: Any, tags: List[str], ttl: Optional[int] = None) -> bool:
        """Set a value with tags for group invalidation"""
        if not self.redis:
            return False
        
        try:
            # Set the main value
            success = await self.set(prefix, key, value, ttl)
            if not success:
                return False
            
            # Add to tag sets
            cache_key = self._make_key(prefix, key)
            for tag in tags:
                tag_key = f"tag:{tag}"
                await self.redis.sadd(tag_key, cache_key)
                # Set TTL for tag sets too
                await self.redis.expire(tag_key, ttl or self.default_ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting tagged cache {prefix}:{key}: {e}")
            return False
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag"""
        if not self.redis:
            return 0
        
        try:
            tag_key = f"tag:{tag}"
            keys = await self.redis.smembers(tag_key)
            
            if keys:
                # Delete all keys associated with the tag
                deleted = await self.redis.delete(*keys)
                # Delete the tag set itself
                await self.redis.delete(tag_key)
                
                logger.info(f"🗑️ Invalidated {deleted} cache entries for tag: {tag}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error invalidating tag {tag}: {e}")
            return 0
    
    # Order-specific caching methods
    
    async def cache_order(self, order_id: str, order_data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache order data with 30-minute TTL"""
        tags = [f"user:{order_data.get('user_id', '')}", "orders"]
        return await self.set_with_tags("order", order_id, order_data, tags, ttl)
    
    async def get_cached_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get cached order data"""
        return await self.get("order", order_id)
    
    async def invalidate_order(self, order_id: str) -> bool:
        """Invalidate cached order data"""
        return await self.delete("order", order_id)
    
    async def invalidate_user_orders(self, user_id: str) -> int:
        """Invalidate all cached orders for a user"""
        return await self.invalidate_by_tag(f"user:{user_id}")
    
    # Romanian business logic caching
    
    async def cache_romanian_validation(self, order_data_hash: str, validation_result: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache Romanian validation results"""
        return await self.set("romanian_validation", order_data_hash, validation_result, ttl)
    
    async def get_cached_romanian_validation(self, order_data_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached Romanian validation result"""
        return await self.get("romanian_validation", order_data_hash)
    
    async def cache_pricing_calculation(self, order_data_hash: str, pricing_result: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache Romanian pricing calculations"""
        return await self.set("pricing", order_data_hash, pricing_result, ttl)
    
    async def get_cached_pricing(self, order_data_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached pricing calculation"""
        return await self.get("pricing", order_data_hash)
    
    # User session caching
    
    async def cache_user_session(self, user_id: str, session_data: Dict[str, Any], ttl: int = 7200) -> bool:
        """Cache user session data with 2-hour TTL"""
        return await self.set("session", user_id, session_data, ttl)
    
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user session"""
        return await self.get("session", user_id)
    
    async def invalidate_user_session(self, user_id: str) -> bool:
        """Invalidate user session"""
        return await self.delete("session", user_id)
    
    # WebSocket connection caching
    
    async def cache_websocket_state(self, user_id: str, state_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache WebSocket connection state"""
        return await self.set("websocket", user_id, state_data, ttl)
    
    async def get_websocket_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached WebSocket state"""
        return await self.get("websocket", user_id)
    
    # API response caching
    
    async def cache_api_response(self, endpoint: str, params_hash: str, response_data: Any, ttl: int = 300) -> bool:
        """Cache API response with 5-minute TTL"""
        cache_key = f"{endpoint}:{params_hash}"
        return await self.set("api_response", cache_key, response_data, ttl)
    
    async def get_cached_api_response(self, endpoint: str, params_hash: str) -> Optional[Any]:
        """Get cached API response"""
        cache_key = f"{endpoint}:{params_hash}"
        return await self.get("api_response", cache_key)
    
    # Performance monitoring
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if not self.redis:
            return {"error": "Cache not available"}
        
        try:
            info = await self.redis.info()
            stats = {
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "keys_by_prefix": {}
            }
            
            # Count keys by prefix
            for prefix_name, prefix in self.prefixes.items():
                pattern = f"{prefix}*"
                keys = await self.redis.keys(pattern)
                stats["keys_by_prefix"][prefix_name] = len(keys)
            
            # Calculate hit rate
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total = hits + misses
            if total > 0:
                stats["hit_rate"] = round((hits / total) * 100, 2)
            else:
                stats["hit_rate"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}")
            return {"error": str(e)}
    
    async def clear_all_cache(self) -> bool:
        """Clear all cache (use with caution)"""
        if not self.redis:
            return False
        
        try:
            await self.redis.flushdb()
            logger.warning("🧹 All cache cleared")
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}")
            return False

# Global cache service instance
cache_service = CacheService()

# Utility functions for easy access

async def get_cache() -> CacheService:
    """Get the global cache service instance"""
    return cache_service

def create_cache_key_hash(data: Dict[str, Any]) -> str:
    """Create a consistent hash for cache keys from data"""
    import hashlib
    
    # Sort keys to ensure consistent hashing
    sorted_data = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(sorted_data.encode()).hexdigest()

# Cache decorators for functions

def cache_result(prefix: str, ttl: int = 3600, use_args: bool = True):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = await get_cache()
            
            if use_args:
                # Create cache key from function arguments
                key_data = {"args": args, "kwargs": kwargs}
                cache_key = f"{func.__name__}:{create_cache_key_hash(key_data)}"
            else:
                cache_key = func.__name__
            
            # Try to get from cache first
            cached_result = await cache.get(prefix, cache_key)
            if cached_result is not None:
                logger.debug(f"🎯 Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(prefix, cache_key, result, ttl)
            logger.debug(f"💾 Cached result for {func.__name__}")
            
            return result
        return wrapper
    return decorator 