"""
Centralized error handling utilities for consistent error responses
"""

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from utils.logging_config import logger
from typing import Optional, Any
import traceback


class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class NotFoundError(Exception):
    """Custom exception for resource not found errors"""
    pass


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


def handle_database_error(e: Exception, operation: str = "database operation") -> None:
    """
    Handle database errors consistently across the application
    
    Args:
        e: The exception that occurred
        operation: Description of the operation that failed
    """
    if isinstance(e, IntegrityError):
        logger.warning(f"Database integrity error during {operation}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data integrity constraint violated. This operation conflicts with existing data."
        )
    elif isinstance(e, SQLAlchemyError):
        logger.error(f"Database error during {operation}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed. Please try again later."
        )
    else:
        logger.error(f"Unexpected error during {operation}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


def safe_database_operation(db: Session, operation_name: str):
    """
    Context manager for safe database operations with automatic rollback
    
    Usage:
        with safe_database_operation(db, "create user"):
            # database operations here
            db.add(new_user)
            db.commit()
    """
    class DatabaseOperationContext:
        def __init__(self, db: Session, operation_name: str):
            self.db = db
            self.operation_name = operation_name
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.db.rollback()
                handle_database_error(exc_val, self.operation_name)
            return False
    
    return DatabaseOperationContext(db, operation_name)


def validate_resource_exists(resource: Any, resource_name: str, resource_id: Any) -> None:
    """
    Validate that a resource exists, raise 404 if not
    
    Args:
        resource: The resource object (None if not found)
        resource_name: Name of the resource for error message
        resource_id: ID of the resource that was searched for
    """
    if not resource:
        logger.warning(f"{resource_name} not found: {resource_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} not found"
        )


def validate_user_permissions(user: Any, required_status: Optional[str] = None) -> None:
    """
    Validate user permissions for an operation
    
    Args:
        user: User object
        required_status: Required user status (e.g., "professor", "admin")
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if required_status and user.status != required_status:
        logger.warning(f"User {user.id} attempted operation requiring {required_status} status")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation requires {required_status} privileges"
        )


def log_operation_success(operation: str, details: Optional[str] = None) -> None:
    """Log successful operations for audit purposes"""
    if details:
        logger.info(f"Operation successful: {operation} - {details}")
    else:
        logger.info(f"Operation successful: {operation}")


def standardize_error_response(
    status_code: int,
    error_message: str,
    details: Optional[str] = None,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create standardized error responses
    
    Args:
        status_code: HTTP status code
        error_message: Main error message
        details: Additional error details
        request_id: Request ID for tracking
    """
    content = {
        "success": False,
        "error": error_message,
        "status_code": status_code
    }
    
    if details:
        content["detail"] = details
    
    if request_id:
        content["request_id"] = request_id
    
    return HTTPException(status_code=status_code, detail=content)


def handle_validation_errors(errors: list) -> HTTPException:
    """
    Handle Pydantic validation errors consistently
    
    Args:
        errors: List of validation error details
    """
    formatted_errors = []
    for error in errors:
        formatted_errors.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "validation_error")
        })
    
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "success": False,
            "error": "Validation Error",
            "errors": formatted_errors,
            "status_code": 422
        }
    )