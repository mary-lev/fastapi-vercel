"""
Cache Manager for Educational Platform
Provides multi-layer caching with Redis and in-memory fallback
"""

import json
import hashlib
import pickle
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum
import asyncio
from collections import OrderedDict
import time

from utils.structured_logging import get_logger, LogCategory

# Try to import Redis, fallback to in-memory if not available
try:
    import redis
    from redis import asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = get_logger("cache")

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

class CacheStrategy(str, Enum):
    """Cache strategies for different data types"""
    AGGRESSIVE = "aggressive"  # Long TTL, cache everything
    MODERATE = "moderate"      # Medium TTL, selective caching
    CONSERVATIVE = "conservative"  # Short TTL, minimal caching
    DISABLED = "disabled"      # No caching

class CacheLayer(str, Enum):
    """Cache layers in order of speed"""
    MEMORY = "memory"    # In-process memory cache (fastest)
    REDIS = "redis"      # Redis cache (fast, distributed)
    DATABASE = "database"  # Database-level caching (slowest)

# Default TTL values (in seconds)
DEFAULT_TTL = {
    "course_list": 3600,        # 1 hour - courses don't change often
    "course_detail": 1800,      # 30 minutes - course details
    "lesson_detail": 1800,      # 30 minutes - lesson content
    "topic_detail": 900,        # 15 minutes - topic content
    "user_profile": 300,        # 5 minutes - user data
    "user_progress": 60,        # 1 minute - progress updates frequently
    "task_solution": 300,       # 5 minutes - solutions
    "statistics": 600,          # 10 minutes - analytics data
    "security_check": 30,       # 30 seconds - security validations
}

# ============================================================================
# IN-MEMORY LRU CACHE
# ============================================================================

class LRUCache:
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            # Move to end (most recently used)
            value, expiry = self.cache.pop(key)
            
            # Check expiry
            if expiry and time.time() > expiry:
                self.misses += 1
                return None
                
            self.cache[key] = (value, expiry)
            self.hits += 1
            return value
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL"""
        # Calculate expiry
        expiry = time.time() + ttl if ttl else None
        
        # Remove if exists (to update position)
        if key in self.cache:
            self.cache.pop(key)
        
        # Add to end
        self.cache[key] = (value, expiry)
        
        # Evict if over size limit
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            self.evictions += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            self.cache.pop(key)
            return True
        return False
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{hit_rate:.2f}%"
        }

# ============================================================================
# CACHE MANAGER
# ============================================================================

class CacheManager:
    """Multi-layer cache manager with Redis and memory caching"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        memory_cache_size: int = 1000,
        default_ttl: int = 300,
        strategy: CacheStrategy = CacheStrategy.MODERATE
    ):
        self.strategy = strategy
        self.default_ttl = default_ttl
        
        # Initialize memory cache
        self.memory_cache = LRUCache(max_size=memory_cache_size)
        
        # Initialize Redis if available
        self.redis_client = None
        self.redis_async_client = None
        
        if REDIS_AVAILABLE and redis_url and strategy != CacheStrategy.DISABLED:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_async_client = aioredis.from_url(redis_url, decode_responses=True)
                logger.info(
                    "Redis cache initialized",
                    category=LogCategory.SYSTEM,
                    extra={"redis_url": redis_url}
                )
            except Exception as e:
                logger.warning(
                    "Failed to connect to Redis, using memory cache only",
                    category=LogCategory.SYSTEM,
                    exception=e
                )
        else:
            logger.info(
                "Using in-memory cache only",
                category=LogCategory.SYSTEM,
                extra={"strategy": strategy, "cache_size": memory_cache_size}
            )
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        # Create a unique key from arguments
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # Hash complex objects
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)
    
    def _get_ttl(self, cache_type: str) -> int:
        """Get TTL based on cache type and strategy"""
        if self.strategy == CacheStrategy.DISABLED:
            return 0
        
        base_ttl = DEFAULT_TTL.get(cache_type, self.default_ttl)
        
        if self.strategy == CacheStrategy.AGGRESSIVE:
            return base_ttl * 2
        elif self.strategy == CacheStrategy.CONSERVATIVE:
            return base_ttl // 2
        else:  # MODERATE
            return base_ttl
    
    # ========================================================================
    # SYNCHRONOUS METHODS
    # ========================================================================
    
    def get(self, key: str, layer: Optional[CacheLayer] = None) -> Optional[Any]:
        """Get value from cache (checks all layers)"""
        if self.strategy == CacheStrategy.DISABLED:
            return None
        
        # Try memory cache first
        if layer in [None, CacheLayer.MEMORY]:
            value = self.memory_cache.get(key)
            if value is not None:
                logger.debug(
                    f"Cache hit (memory): {key}",
                    category=LogCategory.PERFORMANCE,
                    extra={"layer": "memory", "key": key}
                )
                return value
        
        # Try Redis if available
        if layer in [None, CacheLayer.REDIS] and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    # Deserialize if needed
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                    
                    # Update memory cache
                    self.memory_cache.set(key, value, ttl=60)
                    
                    logger.debug(
                        f"Cache hit (redis): {key}",
                        category=LogCategory.PERFORMANCE,
                        extra={"layer": "redis", "key": key}
                    )
                    return value
            except Exception as e:
                logger.warning(
                    f"Redis get failed for key: {key}",
                    category=LogCategory.SYSTEM,
                    exception=e
                )
        
        logger.debug(
            f"Cache miss: {key}",
            category=LogCategory.PERFORMANCE,
            extra={"key": key}
        )
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        layer: Optional[CacheLayer] = None
    ):
        """Set value in cache"""
        if self.strategy == CacheStrategy.DISABLED:
            return
        
        ttl = ttl or self.default_ttl
        
        # Set in memory cache
        if layer in [None, CacheLayer.MEMORY]:
            self.memory_cache.set(key, value, ttl=ttl)
        
        # Set in Redis if available
        if layer in [None, CacheLayer.REDIS] and self.redis_client:
            try:
                # Serialize value
                serialized = json.dumps(value) if not isinstance(value, str) else value
                self.redis_client.setex(key, ttl, serialized)
                
                logger.debug(
                    f"Cache set: {key}",
                    category=LogCategory.PERFORMANCE,
                    extra={"key": key, "ttl": ttl, "layers": ["memory", "redis"]}
                )
            except Exception as e:
                logger.warning(
                    f"Redis set failed for key: {key}",
                    category=LogCategory.SYSTEM,
                    exception=e
                )
    
    def delete(self, key: str):
        """Delete key from all cache layers"""
        deleted = False
        
        # Delete from memory
        if self.memory_cache.delete(key):
            deleted = True
        
        # Delete from Redis
        if self.redis_client:
            try:
                if self.redis_client.delete(key):
                    deleted = True
            except Exception as e:
                logger.warning(
                    f"Redis delete failed for key: {key}",
                    category=LogCategory.SYSTEM,
                    exception=e
                )
        
        if deleted:
            logger.debug(
                f"Cache invalidated: {key}",
                category=LogCategory.PERFORMANCE,
                extra={"key": key}
            )
        
        return deleted
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        count = 0
        
        # Clear matching keys from memory cache
        keys_to_delete = [k for k in self.memory_cache.cache.keys() if pattern in k]
        for key in keys_to_delete:
            self.memory_cache.delete(key)
            count += 1
        
        # Clear from Redis
        if self.redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor, match=f"*{pattern}*")
                    if keys:
                        self.redis_client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(
                    f"Redis pattern delete failed for: {pattern}",
                    category=LogCategory.SYSTEM,
                    exception=e
                )
        
        logger.info(
            f"Cache invalidated {count} keys matching pattern: {pattern}",
            category=LogCategory.PERFORMANCE,
            extra={"pattern": pattern, "count": count}
        )
    
    # ========================================================================
    # ASYNCHRONOUS METHODS
    # ========================================================================
    
    async def aget(self, key: str, layer: Optional[CacheLayer] = None) -> Optional[Any]:
        """Async get value from cache"""
        if self.strategy == CacheStrategy.DISABLED:
            return None
        
        # Try memory cache first (synchronous but fast)
        if layer in [None, CacheLayer.MEMORY]:
            value = self.memory_cache.get(key)
            if value is not None:
                return value
        
        # Try Redis if available
        if layer in [None, CacheLayer.REDIS] and self.redis_async_client:
            try:
                value = await self.redis_async_client.get(key)
                if value:
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                    
                    # Update memory cache
                    self.memory_cache.set(key, value, ttl=60)
                    return value
            except Exception as e:
                logger.warning(
                    f"Async Redis get failed for key: {key}",
                    category=LogCategory.SYSTEM,
                    exception=e
                )
        
        return None
    
    async def aset(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        layer: Optional[CacheLayer] = None
    ):
        """Async set value in cache"""
        if self.strategy == CacheStrategy.DISABLED:
            return
        
        ttl = ttl or self.default_ttl
        
        # Set in memory cache (synchronous)
        if layer in [None, CacheLayer.MEMORY]:
            self.memory_cache.set(key, value, ttl=ttl)
        
        # Set in Redis if available
        if layer in [None, CacheLayer.REDIS] and self.redis_async_client:
            try:
                serialized = json.dumps(value) if not isinstance(value, str) else value
                await self.redis_async_client.setex(key, ttl, serialized)
            except Exception as e:
                logger.warning(
                    f"Async Redis set failed for key: {key}",
                    category=LogCategory.SYSTEM,
                    exception=e
                )
    
    # ========================================================================
    # DECORATORS
    # ========================================================================
    
    def cache(
        self,
        cache_type: str = "default",
        ttl: Optional[int] = None,
        key_prefix: Optional[str] = None
    ):
        """Decorator for caching function results"""
        
        def decorator(func: Callable):
            # Determine if function is async
            is_async = asyncio.iscoroutinefunction(func)
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                prefix = key_prefix or f"{func.__module__}.{func.__name__}"
                cache_key = self._generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = await self.aget(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                start_time = time.time()
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Cache result
                cache_ttl = ttl or self._get_ttl(cache_type)
                await self.aset(cache_key, result, ttl=cache_ttl)
                
                logger.debug(
                    f"Cached function result: {func.__name__}",
                    category=LogCategory.PERFORMANCE,
                    duration_ms=duration_ms,
                    extra={"function": func.__name__, "cache_type": cache_type, "ttl": cache_ttl}
                )
                
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Generate cache key
                prefix = key_prefix or f"{func.__module__}.{func.__name__}"
                cache_key = self._generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                start_time = time.time()
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Cache result
                cache_ttl = ttl or self._get_ttl(cache_type)
                self.set(cache_key, result, ttl=cache_ttl)
                
                logger.debug(
                    f"Cached function result: {func.__name__}",
                    category=LogCategory.PERFORMANCE,
                    duration_ms=duration_ms,
                    extra={"function": func.__name__, "cache_type": cache_type, "ttl": cache_ttl}
                )
                
                return result
            
            return async_wrapper if is_async else sync_wrapper
        
        return decorator
    
    def invalidate_on_update(self, patterns: List[str]):
        """Decorator to invalidate cache patterns after function execution"""
        
        def decorator(func: Callable):
            is_async = asyncio.iscoroutinefunction(func)
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                
                # Invalidate cache patterns
                for pattern in patterns:
                    self.invalidate_pattern(pattern)
                
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                
                # Invalidate cache patterns
                for pattern in patterns:
                    self.invalidate_pattern(pattern)
                
                return result
            
            return async_wrapper if is_async else sync_wrapper
        
        return decorator
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
    def clear_all(self):
        """Clear all cache entries"""
        # Clear memory cache
        self.memory_cache.clear()
        
        # Clear Redis
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                logger.info("All cache entries cleared", category=LogCategory.SYSTEM)
            except Exception as e:
                logger.warning("Failed to clear Redis cache", category=LogCategory.SYSTEM, exception=e)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "strategy": self.strategy,
            "memory_cache": self.memory_cache.stats(),
            "redis_available": self.redis_client is not None
        }
        
        # Get Redis stats if available
        if self.redis_client:
            try:
                info = self.redis_client.info("stats")
                stats["redis"] = {
                    "total_connections": info.get("total_connections_received", 0),
                    "commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            except Exception:
                stats["redis"] = "unavailable"
        
        return stats

# ============================================================================
# GLOBAL CACHE INSTANCE
# ============================================================================

# Initialize global cache manager (can be configured from environment)
import os

cache_manager = CacheManager(
    redis_url=os.getenv("REDIS_URL"),
    memory_cache_size=int(os.getenv("CACHE_MEMORY_SIZE", "1000")),
    default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "300")),
    strategy=CacheStrategy(os.getenv("CACHE_STRATEGY", "moderate"))
)

# ============================================================================
# FASTAPI CACHE DECORATOR 
# ============================================================================

def api_cache(
    cache_type: str = "default",
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching FastAPI endpoint responses
    
    Args:
        cache_type: Type of cache (affects TTL calculation)
        ttl: Override TTL in seconds
        key_builder: Custom function to build cache key from request
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Extract path parameters from kwargs
                path_params = []
                for k, v in kwargs.items():
                    if k not in ['db', 'request', 'response']:
                        path_params.append(f"{k}:{v}")
                
                cache_key = f"{func.__module__}.{func.__name__}:{':'.join(path_params)}"
            
            # Try cache first
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(
                    f"API cache hit: {func.__name__}",
                    category=LogCategory.PERFORMANCE,
                    extra={"cache_key": cache_key, "endpoint": func.__name__}
                )
                return cached_value
            
            # Execute endpoint
            result = await func(*args, **kwargs)
            
            # Cache result
            cache_ttl = ttl or cache_manager._get_ttl(cache_type)
            cache_manager.set(cache_key, result, ttl=cache_ttl)
            
            logger.debug(
                f"API response cached: {func.__name__}",
                category=LogCategory.PERFORMANCE,
                extra={"cache_key": cache_key, "ttl": cache_ttl}
            )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                path_params = []
                for k, v in kwargs.items():
                    if k not in ['db', 'request', 'response']:
                        path_params.append(f"{k}:{v}")
                
                cache_key = f"{func.__module__}.{func.__name__}:{':'.join(path_params)}"
            
            # Try cache first
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute endpoint
            result = func(*args, **kwargs)
            
            # Cache result
            cache_ttl = ttl or cache_manager._get_ttl(cache_type)
            cache_manager.set(cache_key, result, ttl=cache_ttl)
            
            return result
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# ============================================================================
# CACHE UTILITIES
# ============================================================================

def cache_key_for_user(user_id: Union[int, str], prefix: str) -> str:
    """Generate cache key for user-specific data"""
    return f"user:{user_id}:{prefix}"

def cache_key_for_course(course_id: int, prefix: str) -> str:
    """Generate cache key for course-specific data"""
    return f"course:{course_id}:{prefix}"

def cache_key_for_task(task_id: int, prefix: str) -> str:
    """Generate cache key for task-specific data"""
    return f"task:{task_id}:{prefix}"

def invalidate_user_cache(user_id: Union[int, str]):
    """Invalidate all cache entries for a user"""
    cache_manager.invalidate_pattern(f"user:{user_id}:")

def invalidate_course_cache(course_id: int):
    """Invalidate all cache entries for a course"""
    cache_manager.invalidate_pattern(f"course:{course_id}:")

def invalidate_task_cache(task_id: int):
    """Invalidate all cache entries for a task"""
    cache_manager.invalidate_pattern(f"task:{task_id}:")