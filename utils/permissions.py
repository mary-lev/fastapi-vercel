"""
Role-Based Access Control (RBAC) System
Provides fine-grained permission management
"""

from enum import Enum
from typing import Set, Dict, List, Optional, Callable
from functools import wraps
from fastapi import HTTPException, status

from models import User, UserStatus
from utils.logging_config import logger


class Permission(Enum):
    """Define specific permissions in the system"""

    # Course Management
    CREATE_COURSE = "create_course"
    EDIT_COURSE = "edit_course"
    DELETE_COURSE = "delete_course"
    VIEW_COURSE = "view_course"

    # Lesson Management
    CREATE_LESSON = "create_lesson"
    EDIT_LESSON = "edit_lesson"
    DELETE_LESSON = "delete_lesson"
    VIEW_LESSON = "view_lesson"

    # Task Management
    CREATE_TASK = "create_task"
    EDIT_TASK = "edit_task"
    DELETE_TASK = "delete_task"
    VIEW_TASK = "view_task"
    SUBMIT_TASK = "submit_task"

    # User Management
    CREATE_USER = "create_user"
    EDIT_USER = "edit_user"
    DELETE_USER = "delete_user"
    VIEW_USER = "view_user"
    VIEW_ALL_USERS = "view_all_users"

    # Student Progress
    VIEW_OWN_PROGRESS = "view_own_progress"
    VIEW_ALL_PROGRESS = "view_all_progress"
    SUBMIT_SOLUTION = "submit_solution"
    VIEW_FEEDBACK = "view_feedback"

    # Analytics & Reports
    VIEW_ANALYTICS = "view_analytics"
    VIEW_REPORTS = "view_reports"
    EXPORT_DATA = "export_data"

    # System Administration
    MANAGE_SYSTEM = "manage_system"
    VIEW_LOGS = "view_logs"
    MANAGE_API_KEYS = "manage_api_keys"

    # Telegram Integration
    MANAGE_TELEGRAM = "manage_telegram"
    SEND_NOTIFICATIONS = "send_notifications"


# Define role-permission mappings
STUDENT_PERMISSIONS = {
    Permission.VIEW_COURSE,
    Permission.VIEW_LESSON,
    Permission.VIEW_TASK,
    Permission.SUBMIT_TASK,
    Permission.VIEW_OWN_PROGRESS,
    Permission.SUBMIT_SOLUTION,
    Permission.VIEW_FEEDBACK,
}

PROFESSOR_PERMISSIONS = {
    *STUDENT_PERMISSIONS,
    # Course management
    Permission.CREATE_COURSE,
    Permission.EDIT_COURSE,
    Permission.DELETE_COURSE,
    # Lesson management
    Permission.CREATE_LESSON,
    Permission.EDIT_LESSON,
    Permission.DELETE_LESSON,
    # Task management
    Permission.CREATE_TASK,
    Permission.EDIT_TASK,
    Permission.DELETE_TASK,
    # Student monitoring
    Permission.VIEW_ALL_PROGRESS,
    Permission.VIEW_ANALYTICS,
    Permission.VIEW_REPORTS,
    # User management (limited)
    Permission.VIEW_USER,
    Permission.VIEW_ALL_USERS,
    # Telegram
    Permission.MANAGE_TELEGRAM,
    Permission.SEND_NOTIFICATIONS,
}

ADMIN_PERMISSIONS = {
    # Include all permissions
    *[perm for perm in Permission],
}

ROLE_PERMISSIONS: Dict[UserStatus, Set[Permission]] = {
    UserStatus.STUDENT: STUDENT_PERMISSIONS,
    UserStatus.PROFESSOR: PROFESSOR_PERMISSIONS,
    UserStatus.ADMIN: ADMIN_PERMISSIONS,
}


class PermissionChecker:
    """Helper class for checking permissions"""

    @staticmethod
    def user_has_permission(user: User, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        if not user or not user.status:
            return False

        user_permissions = ROLE_PERMISSIONS.get(user.status, set())
        return permission in user_permissions

    @staticmethod
    def user_has_any_permission(user: User, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(PermissionChecker.user_has_permission(user, perm) for perm in permissions)

    @staticmethod
    def user_has_all_permissions(user: User, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions"""
        return all(PermissionChecker.user_has_permission(user, perm) for perm in permissions)

    @staticmethod
    def get_user_permissions(user: User) -> Set[Permission]:
        """Get all permissions for a user"""
        if not user or not user.status:
            return set()

        return ROLE_PERMISSIONS.get(user.status, set())

    @staticmethod
    def can_access_user_data(current_user: User, target_user: User) -> bool:
        """Check if current user can access target user's data"""
        # Users can always access their own data
        if current_user.id == target_user.id:
            return True

        # Professors and admins can access student data
        if current_user.status in [UserStatus.PROFESSOR, UserStatus.ADMIN]:
            return True

        return False

    @staticmethod
    def can_modify_user_data(current_user: User, target_user: User) -> bool:
        """Check if current user can modify target user's data"""
        # Admins can modify anyone
        if current_user.status == UserStatus.ADMIN:
            return True

        # Users can modify their own basic data
        if current_user.id == target_user.id:
            return True

        # Professors can modify students in their courses (TODO: implement course enrollment check)
        if current_user.status == UserStatus.PROFESSOR and target_user.status == UserStatus.STUDENT:
            return True

        return False


def require_permission(permission: Permission):
    """Decorator to require specific permission for an endpoint"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the current_user parameter
            current_user = None
            for key, value in kwargs.items():
                if key == "current_user" and isinstance(value, User):
                    current_user = value
                    break

            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            if not PermissionChecker.user_has_permission(current_user, permission):
                logger.warning(
                    f"Permission denied: User {current_user.id} " f"attempted {permission.value} without permission"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {permission.value}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission):
    """Decorator to require any of the specified permissions"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = None
            for key, value in kwargs.items():
                if key == "current_user" and isinstance(value, User):
                    current_user = value
                    break

            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            if not PermissionChecker.user_has_any_permission(current_user, list(permissions)):
                perm_names = [p.value for p in permissions]
                logger.warning(
                    f"Permission denied: User {current_user.id} " f"attempted action requiring one of {perm_names}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of these permissions required: {', '.join(perm_names)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_own_data_or_permission(permission: Permission):
    """Decorator to allow access to own data OR require specific permission"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = None
            target_user_id = None

            # Find current_user and user_id parameters
            for key, value in kwargs.items():
                if key == "current_user" and isinstance(value, User):
                    current_user = value
                elif key in ["user_id", "target_user_id"] and value:
                    target_user_id = value

            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            # Allow if accessing own data
            if target_user_id and str(current_user.id) == str(target_user_id):
                return await func(*args, **kwargs)

            # Otherwise require permission
            if not PermissionChecker.user_has_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Can only access own data or requires elevated permissions",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_permission_summary(user: User) -> Dict[str, any]:
    """Get a summary of user's permissions for API responses"""
    permissions = PermissionChecker.get_user_permissions(user)

    return {
        "user_id": user.id,
        "username": user.username,
        "status": user.status.value if user.status else None,
        "permissions": [perm.value for perm in permissions],
        "permission_groups": {
            "course_management": any(
                perm in permissions
                for perm in [Permission.CREATE_COURSE, Permission.EDIT_COURSE, Permission.DELETE_COURSE]
            ),
            "user_management": any(
                perm in permissions
                for perm in [Permission.CREATE_USER, Permission.EDIT_USER, Permission.VIEW_ALL_USERS]
            ),
            "analytics": Permission.VIEW_ANALYTICS in permissions,
            "system_admin": Permission.MANAGE_SYSTEM in permissions,
        },
    }
