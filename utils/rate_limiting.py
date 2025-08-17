"""Rate limiting utilities for API protection"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, Request, status
from functools import wraps
import asyncio
from utils.logging_config import logger


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter

    In production, you'd want to use Redis for this to work across
    multiple server instances and provide persistence.
    """

    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.violations: Dict[str, int] = {}  # Track security violations per user
        self.blocked_users: Dict[str, datetime] = {}  # Track blocked users
        self.cleanup_interval = 1800  # Clean old entries every 30 minutes
        self.last_cleanup = datetime.utcnow()

    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leaks"""
        now = datetime.utcnow()

        # More frequent cleanup for better memory management
        if (now - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return

        cutoff = now - timedelta(hours=24)  # Keep last 24 hours
        keys_to_remove = []
        total_removed_timestamps = 0
        total_removed_keys = 0

        for key, timestamps in self.requests.items():
            # Filter out old timestamps
            original_count = len(timestamps)
            recent_timestamps = [ts for ts in timestamps if ts > cutoff]

            if recent_timestamps:
                self.requests[key] = recent_timestamps
                total_removed_timestamps += original_count - len(recent_timestamps)
            else:
                keys_to_remove.append(key)

        # Remove empty keys
        for key in keys_to_remove:
            del self.requests[key]
            total_removed_keys += 1

        self.last_cleanup = now

        # Log cleanup statistics for monitoring
        if total_removed_keys > 0 or total_removed_timestamps > 0:
            print(
                f"Rate limiter cleanup: removed {total_removed_keys} keys and {total_removed_timestamps} old timestamps"
            )

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
        self.requests[key] = [timestamp for timestamp in self.requests[key] if timestamp > window_start]

        # Check if we've exceeded the limit
        if len(self.requests[key]) >= max_requests:
            return False

        # Record this request
        self.requests[key].append(now)
        return True

    def force_cleanup(self):
        """Force immediate cleanup of old entries"""
        self.last_cleanup = datetime.utcnow() - timedelta(seconds=self.cleanup_interval + 1)
        self._cleanup_old_entries()

    def record_security_violation(self, key: str) -> None:
        """Record a security violation for progressive penalties"""
        self.violations[key] = self.violations.get(key, 0) + 1

        # Progressive blocking based on violation count
        violation_count = self.violations[key]
        if violation_count >= 3:
            # Block for increasing durations
            block_minutes = min(60 * (2 ** (violation_count - 3)), 1440)  # Max 24 hours
            self.blocked_users[key] = datetime.utcnow() + timedelta(minutes=block_minutes)
            logger.warning(f"User {key} blocked for {block_minutes} minutes after {violation_count} violations")

    def is_blocked(self, key: str) -> bool:
        """Check if a user is currently blocked due to security violations"""
        if key in self.blocked_users:
            if datetime.utcnow() < self.blocked_users[key]:
                return True
            else:
                # Block expired, remove it
                del self.blocked_users[key]
        return False

    def get_block_info(self, key: str) -> Optional[dict]:
        """Get blocking information for a user"""
        if key in self.blocked_users:
            remaining = self.blocked_users[key] - datetime.utcnow()
            if remaining.total_seconds() > 0:
                return {
                    "blocked": True,
                    "remaining_seconds": int(remaining.total_seconds()),
                    "violations": self.violations.get(key, 0),
                }
        return {"blocked": False, "violations": self.violations.get(key, 0)}

    def get_stats(self) -> dict:
        """Get current rate limiter statistics for monitoring"""
        total_keys = len(self.requests)
        total_requests = sum(len(timestamps) for timestamps in self.requests.values())
        total_violations = sum(self.violations.values())
        active_blocks = sum(1 for block_time in self.blocked_users.values() if block_time > datetime.utcnow())

        return {
            "total_tracked_keys": total_keys,
            "total_tracked_requests": total_requests,
            "total_violations": total_violations,
            "active_blocks": active_blocks,
            "last_cleanup": self.last_cleanup.isoformat(),
            "next_cleanup_in_seconds": self.cleanup_interval - (datetime.utcnow() - self.last_cleanup).total_seconds(),
        }


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
                    detail=f"Rate limit exceeded: max {max_requests} requests per {window_minutes} minutes",
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
        if hasattr(arg, "telegram_user_id"):
            return f"telegram:{arg.telegram_user_id}"

    # Fallback to IP address
    return f"ip:{request.client.host if request.client else 'unknown'}"


# Security-specific rate limiting functions for code execution
def check_code_execution_limits(user_id: str) -> None:
    """Check both rate limits and security blocks for code execution"""
    key = f"code_exec:{user_id}"

    # Check if user is blocked due to security violations
    if rate_limiter.is_blocked(key):
        block_info = rate_limiter.get_block_info(key)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account temporarily blocked due to security violations. "
            f"Remaining: {block_info['remaining_seconds']} seconds",
        )

    # Check rate limits (30 requests per 5 minutes for code execution)
    if not rate_limiter.is_allowed(key, max_requests=30, window_minutes=5):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for code execution: max 30 requests per 5 minutes",
        )


def record_security_violation_for_user(user_id: str) -> None:
    """Record a security violation for a user"""
    key = f"code_exec:{user_id}"
    rate_limiter.record_security_violation(key)
    logger.warning(f"Security violation recorded for user {user_id}")


def user_rate_limit_key(request: Request, user_id: str, *args, **kwargs) -> str:
    """Generate rate limit key for user-specific endpoints"""
    return f"user:{user_id}"
