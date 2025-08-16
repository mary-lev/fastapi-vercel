"""
Centralized Authentication Middleware and Utilities
Provides consistent authentication across all endpoints
"""

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Union
import time
import uuid

from models import User
from db import get_db
from config import settings
from utils.logging_config import logger


class AuthenticationError(Exception):
    """Custom exception for authentication failures"""

    pass


class AuthContext:
    """Container for authentication context within a request"""

    def __init__(self):
        self.user: Optional[User] = None
        self.api_key: Optional[str] = None
        self.auth_method: Optional[str] = None
        self.request_id: str = str(uuid.uuid4())
        self.start_time: float = time.time()

    def set_user(self, user: User, method: str):
        """Set authenticated user and method"""
        self.user = user
        self.auth_method = method
        logger.info(f"User authenticated: {user.id} via {method} (request: {self.request_id})")

    def set_api_key(self, api_key: str):
        """Set API key authentication"""
        self.api_key = api_key
        self.auth_method = "api_key"
        logger.info(f"API key authentication (request: {self.request_id})")


def extract_bearer_token(authorization: str) -> str:
    """Extract bearer token from Authorization header"""
    if not authorization:
        raise AuthenticationError("Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Invalid authorization header format. Expected 'Bearer <token>'")

    return authorization.replace("Bearer ", "").strip()


def verify_api_key(api_key: str) -> bool:
    """Verify API key against configured value"""
    return api_key == settings.BACKEND_API_KEY


def resolve_user_by_id(user_id: Union[int, str], db: Session) -> Optional[User]:
    """
    Resolve user by various ID types with optimized queries
    Supports: integer ID, internal_user_id, username, telegram_user_id
    """
    try:
        if isinstance(user_id, int):
            # Direct database ID lookup
            return db.query(User).filter(User.id == user_id).first()

        elif isinstance(user_id, str):
            # Try different string-based lookups
            if user_id.isdigit():
                # Could be string representation of telegram_user_id
                telegram_id = int(user_id)
                user = db.query(User).filter(User.telegram_user_id == telegram_id).first()
                if user:
                    return user

            # Try internal_user_id first (most common)
            user = db.query(User).filter(User.internal_user_id == user_id).first()
            if user:
                return user

            # Fallback to username lookup
            return db.query(User).filter(User.username == user_id).first()

        return None

    except Exception as e:
        logger.error(f"Error resolving user {user_id}: {e}")
        return None


def resolve_user_by_telegram(telegram_user_id: int, db: Session) -> Optional[User]:
    """Resolve user by Telegram user ID"""
    try:
        return db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    except Exception as e:
        logger.error(f"Error resolving telegram user {telegram_user_id}: {e}")
        return None


async def add_auth_context_to_request(request: Request, call_next):
    """
    Middleware to add authentication context to all requests
    Does not enforce authentication - just makes it available
    """
    # Create auth context for this request
    auth_context = AuthContext()
    request.state.auth = auth_context

    # Extract authorization header if present
    authorization = request.headers.get("Authorization")
    if authorization:
        try:
            token = extract_bearer_token(authorization)
            if verify_api_key(token):
                auth_context.set_api_key(token)
        except AuthenticationError as e:
            # Don't fail here - let individual endpoints decide if auth is required
            logger.debug(f"Auth extraction failed: {e} (request: {auth_context.request_id})")

    # Process request
    response = await call_next(request)

    # Add timing and request ID headers
    process_time = time.time() - auth_context.start_time
    response.headers["X-Request-ID"] = auth_context.request_id
    response.headers["X-Process-Time"] = f"{process_time:.3f}"

    # Add auth method to response headers for debugging
    if auth_context.auth_method:
        response.headers["X-Auth-Method"] = auth_context.auth_method

    return response


def get_auth_context(request: Request) -> AuthContext:
    """Get authentication context from request state"""
    return getattr(request.state, "auth", AuthContext())


def validate_auth_context(auth_context: AuthContext, require_api_key: bool = False) -> None:
    """Validate authentication context and raise appropriate errors"""
    if require_api_key and not auth_context.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )


def log_authentication_attempt(
    request: Request,
    success: bool,
    user_id: Optional[Union[int, str]] = None,
    method: Optional[str] = None,
    error: Optional[str] = None,
):
    """Log authentication attempts for security monitoring"""
    auth_context = get_auth_context(request)
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")

    log_data = {
        "request_id": auth_context.request_id,
        "success": success,
        "client_ip": client_ip,
        "user_agent": user_agent,
        "endpoint": str(request.url.path),
        "method": request.method,
    }

    if user_id:
        log_data["user_id"] = user_id
    if method:
        log_data["auth_method"] = method
    if error:
        log_data["error"] = error

    if success:
        logger.info(f"Authentication successful: {log_data}")
    else:
        logger.warning(f"Authentication failed: {log_data}")
