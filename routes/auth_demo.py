"""
Authentication System Demonstration
Shows how to use the new centralized authentication features
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import Union

from models import User
from db import get_db
from utils.auth_dependencies import (
    get_current_user,
    get_current_user_optional,
    require_api_key,
    get_user_by_id,
    require_professor,
    require_admin,
)
from utils.permissions import Permission, require_permission, get_permission_summary, PermissionChecker

router = APIRouter()


@router.get("/demo/public")
async def public_endpoint():
    """Public endpoint - no authentication required"""
    return {"message": "This is a public endpoint", "auth_required": False}


@router.get("/demo/optional-auth")
async def optional_auth_endpoint(current_user: User = Depends(get_current_user_optional)):
    """Endpoint with optional authentication - shows different data based on auth status"""
    if current_user:
        return {"message": f"Hello {current_user.username}!", "user_id": current_user.id, "authenticated": True}
    else:
        return {"message": "Hello anonymous user!", "authenticated": False}


@router.get("/demo/protected")
async def protected_endpoint(current_user: User = Depends(get_current_user)):
    """Protected endpoint - requires authentication"""
    return {
        "message": f"Welcome {current_user.username}!",
        "user_id": current_user.id,
        "status": current_user.status.value if current_user.status else None,
        "permissions": get_permission_summary(current_user),
    }


@router.get("/demo/api-key-only")
async def api_key_endpoint(request: Request, api_key: str = Depends(require_api_key)):
    """Endpoint that only requires API key authentication"""
    return {
        "message": "API key authentication successful",
        "api_key_valid": True,
        "request_id": getattr(request.state, "auth", {}).request_id,
    }


@router.get("/demo/user-lookup/{user_id}")
async def user_lookup_endpoint(
    user_id: Union[int, str],
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_user_by_id),
):
    """Demonstrate user lookup by ID with API key auth"""
    return {
        "message": "User lookup successful",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "status": current_user.status.value if current_user.status else None,
        },
    }


@router.get("/demo/professor-only")
async def professor_only_endpoint(current_user: User = Depends(require_professor)):
    """Endpoint that requires professor or admin privileges"""
    return {
        "message": f"Hello Professor {current_user.username}!",
        "access_level": "professor",
        "permissions": get_permission_summary(current_user),
    }


@router.get("/demo/admin-only")
async def admin_only_endpoint(current_user: User = Depends(require_admin)):
    """Endpoint that requires admin privileges"""
    return {
        "message": f"Hello Admin {current_user.username}!",
        "access_level": "admin",
        "permissions": get_permission_summary(current_user),
    }


@router.get("/demo/permission-based")
@require_permission(Permission.VIEW_ANALYTICS)
async def permission_based_endpoint(current_user: User = Depends(get_current_user)):
    """Endpoint that requires specific permission"""
    return {
        "message": "You have analytics viewing permission!",
        "permission_checked": Permission.VIEW_ANALYTICS.value,
        "user_permissions": [p.value for p in PermissionChecker.get_user_permissions(current_user)],
    }


@router.get("/demo/auth-methods")
async def auth_methods_info():
    """Information about available authentication methods"""
    return {
        "authentication_methods": {
            "session_auth": {
                "description": "User session-based authentication",
                "usage": "Include session token in request",
                "endpoints": ["/demo/protected", "/demo/professor-only"],
            },
            "api_key_auth": {
                "description": "API key authentication for bots/services",
                "usage": "Include 'Authorization: Bearer <api_key>' header",
                "endpoints": ["/demo/api-key-only", "/demo/user-lookup/{user_id}"],
            },
            "optional_auth": {
                "description": "Endpoints that work with or without auth",
                "usage": "Authentication is optional, different response based on auth status",
                "endpoints": ["/demo/optional-auth"],
            },
        },
        "role_based_access": {
            "student": "Basic access to courses and own data",
            "professor": "Course management and student analytics",
            "admin": "Full system access",
        },
        "permission_system": {
            "description": "Fine-grained permissions beyond roles",
            "example_permissions": [p.value for p in Permission][:10],  # Show first 10
        },
    }
