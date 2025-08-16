"""
FastAPI Authentication Dependencies
Provides clean dependency injection for authentication across routes
"""

from fastapi import Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session
from typing import Optional, Union
from functools import wraps

from models import User, UserStatus
from db import get_db
from utils.auth_middleware import (
    get_auth_context,
    resolve_user_by_id,
    resolve_user_by_telegram,
    extract_bearer_token,
    verify_api_key,
    validate_auth_context,
    log_authentication_attempt,
    AuthenticationError,
)
from utils.logging_config import logger


# =============================================================================
# CORE AUTHENTICATION DEPENDENCIES
# =============================================================================


async def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    Use this for endpoints where authentication is optional
    """
    auth_context = get_auth_context(request)

    # If user already resolved in this request, return it
    if auth_context.user:
        return auth_context.user

    # Try to resolve user if we have auth info
    if auth_context.api_key:
        # API key auth doesn't resolve to a specific user
        # Individual endpoints can specify user_id parameter
        return None

    return None


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Get current authenticated user - raises 401 if not authenticated
    Use this for endpoints that require authentication
    """
    user = await get_current_user_optional(request, db)

    if not user:
        log_authentication_attempt(request, False, error="No authenticated user found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    log_authentication_attempt(request, True, user_id=user.id, method="session")
    return user


async def require_api_key(
    request: Request, authorization: str = Header(..., description="API key in format 'Bearer <key>'")
) -> str:
    """
    Require valid API key authentication
    Use this for bot endpoints and internal API calls
    """
    try:
        api_key = extract_bearer_token(authorization)
        if not verify_api_key(api_key):
            log_authentication_attempt(request, False, method="api_key", error="Invalid API key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update auth context
        auth_context = get_auth_context(request)
        auth_context.set_api_key(api_key)

        log_authentication_attempt(request, True, method="api_key")
        return api_key

    except AuthenticationError as e:
        log_authentication_attempt(request, False, method="api_key", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e), headers={"WWW-Authenticate": "Bearer"}
        )


async def get_user_by_id(
    user_id: Union[int, str],
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key),  # Require API key for user lookup
) -> User:
    """
    Get user by ID with API key authentication
    Use this for endpoints that need to lookup users by ID
    """
    user = resolve_user_by_id(user_id, db)

    if not user:
        log_authentication_attempt(request, False, user_id=user_id, method="lookup", error="User not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    log_authentication_attempt(request, True, user_id=user.id, method="lookup")
    return user


async def get_telegram_user(
    telegram_user_id: int, request: Request, db: Session = Depends(get_db), api_key: str = Depends(require_api_key)
) -> User:
    """
    Get user by Telegram user ID with API key authentication
    Use this for Telegram bot endpoints
    """
    user = resolve_user_by_telegram(telegram_user_id, db)

    if not user:
        log_authentication_attempt(
            request, False, user_id=telegram_user_id, method="telegram", error="Telegram user not found"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram user not found")

    log_authentication_attempt(request, True, user_id=user.id, method="telegram")
    return user


# =============================================================================
# ROLE-BASED AUTHENTICATION DEPENDENCIES
# =============================================================================


async def require_student(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be a student or higher"""
    if current_user.status not in [UserStatus.STUDENT, UserStatus.PROFESSOR, UserStatus.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")
    return current_user


async def require_professor(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be a professor or admin"""
    if current_user.status not in [UserStatus.PROFESSOR, UserStatus.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Professor access required")
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an admin"""
    if current_user.status != UserStatus.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# =============================================================================
# FLEXIBLE USER RESOLUTION (Backward Compatibility)
# =============================================================================


async def resolve_user_flexible(user_id: Union[int, str], request: Request, db: Session = Depends(get_db)) -> User:
    """
    Flexible user resolution that works with both API key and session auth
    Use this for migration compatibility
    """
    auth_context = get_auth_context(request)

    # Check if we have any form of authentication
    if not auth_context.api_key and not auth_context.user:
        # Try to extract API key from header for backward compatibility
        authorization = request.headers.get("Authorization")
        if authorization:
            try:
                api_key = extract_bearer_token(authorization)
                if verify_api_key(api_key):
                    auth_context.set_api_key(api_key)
            except AuthenticationError:
                pass

    # If still no auth, require it
    if not auth_context.api_key and not auth_context.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve user
    user = resolve_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def create_auth_dependency(required_status: Optional[UserStatus] = None):
    """
    Factory function to create custom auth dependencies
    """

    async def auth_dependency(current_user: User = Depends(get_current_user)) -> User:
        if required_status and current_user.status != required_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Access requires {required_status.value} status"
            )
        return current_user

    return auth_dependency


def optional_auth(func):
    """
    Decorator to make authentication optional for an endpoint
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Replace get_current_user with get_current_user_optional in kwargs
        if "current_user" in kwargs and kwargs["current_user"] is None:
            kwargs["current_user"] = None
        return await func(*args, **kwargs)

    return wrapper
