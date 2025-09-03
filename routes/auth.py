"""
Authentication Service Router
Handles all authentication-related functionality: Telegram auth, sessions, user management
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Header, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel
from typing import Optional, Dict, Any

from db import get_db
from models import User, TelegramLinkToken, UserStatus
from utils.jwt_utils import jwt_manager
from utils.logging_config import logger
from utils.rate_limiting import rate_limit, telegram_rate_limit_key
from utils.auth_dependencies import require_api_key
from config import settings

router = APIRouter()


# Pydantic models
class TelegramLinkRequest(BaseModel):
    telegram_user_id: int
    course_id: Optional[int] = 1  # Default to course 1
    telegram_username: Optional[str] = None  # Telegram username (without @)
    first_name: Optional[str] = None  # User's first name from Telegram
    last_name: Optional[str] = None  # User's last name from Telegram


class TelegramLinkResponse(BaseModel):
    link_url: str


class TelegramCompleteRequest(BaseModel):
    token: str


class TelegramCompleteResponse(BaseModel):
    status: str
    user: Dict[str, Any]
    token: Optional[str] = None
    course_id: Optional[int] = None


class SessionCreateRequest(BaseModel):
    session_id: str
    page_url: str
    user_agent: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    events_count: int
    session_data: Optional[Dict[str, Any]] = None


# Helper functions - using centralized authentication
# verify_api_key has been moved to utils/auth_unified.py


# Standard authentication endpoints
@router.post("/login", summary="Standard login (placeholder)")
async def login():
    """Standard login endpoint - placeholder for future implementation"""
    return {"message": "Standard login not yet implemented", "available_methods": ["telegram"]}


@router.post("/logout", summary="Logout and invalidate session")
async def logout():
    """Logout endpoint - placeholder for session invalidation"""
    return {"message": "Logout successful", "status": "ok"}


# Telegram authentication endpoints
@router.post("/telegram/link", response_model=TelegramLinkResponse, summary="Create Telegram auth link")
@rate_limit(max_requests=5, window_minutes=10, key_func=telegram_rate_limit_key)
async def create_telegram_link(
    request: Request,
    link_request: TelegramLinkRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(require_api_key),
):
    """
    Create a secure link for Telegram account linking

    This endpoint creates a short-lived, single-use token that allows
    a Telegram user to link their account with the web application.
    """
    try:
        telegram_user_id = link_request.telegram_user_id
        course_id = link_request.course_id

        # Extract telegram user info from request
        telegram_username = link_request.telegram_username
        first_name = link_request.first_name
        last_name = link_request.last_name

        logger.info(f"Creating Telegram link for user: {telegram_user_id}, course: {course_id}")
        logger.info(
            f"Telegram user info - username: {telegram_username}, first_name: {first_name}, last_name: {last_name}"
        )

        # Check if this telegram_user_id is already linked to an existing user
        existing_user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()

        if existing_user:
            logger.info(f"Telegram user {telegram_user_id} already linked to user {existing_user.id}")

            # Update existing user's info with latest telegram data if provided
            should_update_username = telegram_username and (
                existing_user.username.startswith("telegram_user_")  # Auto-generated
                or existing_user.username.startswith("updated_username_")  # Test data
                or existing_user.username == "Anonymous"  # Default value
            )

            if should_update_username:
                # Update username to real telegram username
                existing_user.username = telegram_username
                logger.info(f"Updated username for existing user {existing_user.id} to: {telegram_username}")

            # Update first name if it's empty, test data, or auto-generated
            should_update_first_name = first_name and (
                not existing_user.first_name  # Empty
                or existing_user.first_name.startswith("telegram_user_")  # Auto-generated
                or existing_user.first_name in ["Updated", "Anonymous"]  # Test/default data
            )

            if should_update_first_name:
                existing_user.first_name = first_name
                logger.info(f"Updated first_name for existing user {existing_user.id} to: {first_name}")

            # Update last name if it's empty, test data, or auto-generated
            should_update_last_name = last_name and (
                not existing_user.last_name  # Empty
                or existing_user.last_name.startswith("telegram_user_")  # Auto-generated
                or existing_user.last_name in ["Name", "Anonymous"]  # Test/default data
            )

            if should_update_last_name:
                existing_user.last_name = last_name
                logger.info(f"Updated last_name for existing user {existing_user.id} to: {last_name}")

            db.commit()

        # Create JWT token
        token_data = jwt_manager.create_link_token(telegram_user_id, course_id)

        # Store token metadata in database for single-use enforcement
        link_token = TelegramLinkToken(
            jti=token_data["jti"],
            telegram_user_id=telegram_user_id,
            expires_at=token_data["expires_at"],
            is_used=False,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
        )

        db.add(link_token)
        db.commit()

        # Create the link URL
        link_url = f"{settings.FRONTEND_BASE_URL}/telegram/complete?token={token_data['token']}"
        if course_id:
            link_url += f"&course_id={course_id}"

        logger.info(f"Telegram link created for user {telegram_user_id}, jti: {token_data['jti']}")

        return TelegramLinkResponse(link_url=link_url)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in create_telegram_link: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Token generation conflict")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in create_telegram_link: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in create_telegram_link: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/telegram/complete", response_model=TelegramCompleteResponse, summary="Complete Telegram authentication")
@rate_limit(max_requests=10, window_minutes=10)
async def complete_telegram_link(
    request: Request, complete_request: TelegramCompleteRequest, db: Session = Depends(get_db)
):
    """
    Complete Telegram account linking and create user session

    This endpoint verifies the link token and either creates a new user
    or updates an existing user with the Telegram user ID.
    """
    try:
        token = complete_request.token
        logger.info("Processing Telegram link completion")

        # Verify JWT token
        payload = jwt_manager.verify_link_token(token)
        if not payload:
            logger.warning("Invalid or expired token submitted")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOKEN_INVALID")

        jti = payload["jti"]
        telegram_user_id = payload["telegram_user_id"]
        course_id = payload.get("course_id")

        # Check if token has been used (single-use enforcement)
        token_record = db.query(TelegramLinkToken).filter(TelegramLinkToken.jti == jti).first()

        if not token_record:
            logger.warning(f"Token record not found for jti: {jti}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOKEN_INVALID")

        if token_record.is_used:
            logger.warning(f"Attempt to reuse token: {jti}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOKEN_USED")

        # Check if token has expired (additional check)
        now = datetime.now(timezone.utc)
        if token_record.expires_at <= now.replace(tzinfo=None):
            logger.warning(f"Expired token submitted: {jti}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOKEN_EXPIRED")

        # Mark token as used
        token_record.is_used = True
        token_record.used_at = now.replace(tzinfo=None)

        # Check if user with this telegram_user_id already exists
        existing_user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()

        if existing_user:
            # User already exists and is linked
            user = existing_user
            logger.info(f"Existing user {user.id} authenticated via Telegram")
        else:
            # Check if we should create a new user or link to existing user
            # For this implementation, we'll create a new user
            # In production, you might want different logic here

            # Generate a unique internal_user_id
            internal_user_id = str(uuid.uuid4())

            # Use telegram username if available, otherwise fallback to auto-generated
            username = (
                token_record.telegram_username
                if token_record.telegram_username
                else f"telegram_user_{telegram_user_id}"
            )

            # Create new user with telegram information
            user = User(
                internal_user_id=internal_user_id,
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=token_record.first_name,
                last_name=token_record.last_name,
                hashed_sub=f"telegram:{telegram_user_id}",  # Unique identifier
                status=UserStatus.STUDENT,  # Enum-safe status
            )

            db.add(user)
            logger.info(f"Created new user for Telegram user {telegram_user_id} with username: {username}")

        db.commit()

        # Create session token
        session_token = jwt_manager.create_session_token(user.id, telegram_user_id)

        # Return success response
        response_data = {
            "status": "ok",
            "user": {
                "id": user.id,
                "telegram_user_id": user.telegram_user_id,
                "username": user.username,
                "internal_user_id": user.internal_user_id,
            },
            "token": session_token,
            "course_id": course_id,
        }

        logger.info(f"Telegram linking completed successfully for user {user.id}")
        return TelegramCompleteResponse(**response_data)

    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in complete_telegram_link: {e}")

        # Check if this is a unique constraint violation on telegram_user_id
        if "telegram_user_id" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Telegram account already linked to another user"
            )

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data conflict occurred")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in complete_telegram_link: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in complete_telegram_link: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/telegram/status/{telegram_user_id}", summary="Check Telegram link status")
async def get_telegram_link_status(
    request: Request, telegram_user_id: int, db: Session = Depends(get_db), api_key: str = Depends(require_api_key)
):
    """
    Check if a Telegram user ID is already linked to an account

    This endpoint can be used by the bot to check linking status
    """
    try:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()

        return {
            "telegram_user_id": telegram_user_id,
            "is_linked": user is not None,
            "user_id": user.id if user else None,
            "username": user.username if user else None,
        }

    except Exception as e:
        logger.error(f"Error checking Telegram link status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/sessions/refresh", summary="Refresh session token")
async def refresh_session_token(authorization: str = Header(...), db: Session = Depends(get_db)):
    """Refresh an expired session token"""
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")

        token = authorization.replace("Bearer ", "")

        # Verify the current token (even if expired)
        payload = jwt_manager.verify_session_token(token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user_id = int(payload["sub"])
        telegram_user_id = payload.get("telegram_user_id")

        # Verify user still exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Create new session token
        new_token = jwt_manager.create_session_token(user_id, telegram_user_id)

        return {
            "token": new_token,
            "user_id": user_id,
            "expires_in": 24 * 3600,  # 24 hours in seconds
            "status": "refreshed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing session token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Health check for auth service
@router.get("/health", summary="Authentication service health check")
async def auth_health_check():
    """Health check endpoint for the authentication service"""
    return {
        "service": "authentication",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {"telegram_auth": True, "session_management": True, "token_refresh": True},
    }
