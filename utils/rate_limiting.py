"""Rate limiting utilities for API protection"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, Request, status
from functools import wraps
import asyncio


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter
    
    In production, you'd want to use Redis for this to work across
    multiple server instances and provide persistence.
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.cleanup_interval = 3600  # Clean old entries every hour
        self.last_cleanup = datetime.utcnow()
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leaks"""
        now = datetime.utcnow()
        if (now - self.last_cleanup).seconds < self.cleanup_interval:
            return
        
        cutoff = now - timedelta(hours=24)  # Keep last 24 hours
        keys_to_remove = []
        
        for key, timestamps in self.requests.items():
            # Filter out old timestamps
            recent_timestamps = [ts for ts in timestamps if ts > cutoff]
            if recent_timestamps:
                self.requests[key] = recent_timestamps
            else:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]
        
        self.last_cleanup = now
    
    def is_allowed(self, key: str, max_requests: int, window_minutes: int) -> bool:
        """
        Check if a request is allowed based on rate limits
        
        Args:
            key: Unique identifier for the client (IP, user_id, etc.)
            max_requests: Maximum number of requests allowed
            window_minutes: Time window in minutes
        
        Returns:
            True if request is allowed, False if rate limited
        """
        self._cleanup_old_entries()
        
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Filter out requests outside the time window
        self.requests[key] = [
            timestamp for timestamp in self.requests[key] 
            if timestamp > window_start
        ]
        
        # Check if we've exceeded the limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Record this request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def rate_limit(max_requests: int, window_minutes: int, key_func=None):
    """
    Rate limiting decorator
    
    Args:
        max_requests: Maximum requests allowed in the time window
        window_minutes: Time window in minutes
        key_func: Function to generate rate limit key (defaults to IP address)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Generate rate limit key
            if key_func:
                limit_key = key_func(request, *args, **kwargs)
            else:
                # Default to IP address
                limit_key = request.client.host if request.client else "unknown"
            
            # Check rate limit
            if not rate_limiter.is_allowed(limit_key, max_requests, window_minutes):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: max {max_requests} requests per {window_minutes} minutes"
                )
            
            # Call the original function
            if asyncio.iscoroutinefunction(func):
                return await func(request, *args, **kwargs)
            else:
                return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def telegram_rate_limit_key(request: Request, *args, **kwargs) -> str:
    """Generate rate limit key for Telegram endpoints based on telegram_user_id"""
    # Extract telegram_user_id from request body or args
    for arg in args:
        if hasattr(arg, 'telegram_user_id'):
            return f"telegram:{arg.telegram_user_id}"
    
    # Fallback to IP address
    return f"ip:{request.client.host if request.client else 'unknown'}"