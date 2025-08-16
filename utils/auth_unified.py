"""
Unified Authentication Utilities
Centralized functions to replace duplicate code across routes
"""

from fastapi import HTTPException, Header, status, Request
from sqlalchemy.orm import Session
from typing import Union

from models import User
from config import settings
from utils.logging_config import logger
from utils.auth_dependencies import require_api_key, resolve_user_flexible


# =============================================================================
# CENTRALIZED VERIFICATION FUNCTIONS
# =============================================================================


async def verify_api_key_unified(
    request: Request, authorization: str = Header(..., description="API key in format 'Bearer <key>'")
) -> str:
    """
    Unified API key verification function
    Replaces duplicate verify_api_key functions across routes
    """
    return await require_api_key(request, authorization)


async def get_user_with_auth(user_id: Union[int, str], request: Request, db: Session) -> User:
    """
    Get user by ID with flexible authentication
    Replaces the resolve_user function pattern used in student routes
    """
    return await resolve_user_flexible(user_id, request, db)


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================


def verify_api_key_legacy(authorization: str = Header(...)) -> str:
    """
    Legacy function for backward compatibility
    Use verify_api_key_unified for new code
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")

    api_key = authorization.replace("Bearer ", "")
    if api_key != settings.BACKEND_API_KEY:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return api_key


def resolve_user_legacy(user_id: Union[int, str], db: Session) -> User:
    """
    Legacy user resolution function for backward compatibility
    Use get_user_with_auth for new code
    """
    if isinstance(user_id, int):
        user = db.query(User).filter(User.id == user_id).first()
    else:
        user = db.query(User).filter(User.internal_user_id == user_id).first()
        if not user:
            user = db.query(User).filter(User.username == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
