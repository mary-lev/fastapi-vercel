"""
Enhanced OpenAPI Documentation Models
Provides detailed API documentation with examples, security schemas, and response models
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Import base models
from .api_models import (
    UserRole,
    TaskType,
    BaseResponse,
    UserResponse,
    CourseResponse,
    LessonResponse,
    TopicResponse,
    TaskResponse,
    TaskSolutionResponse,
    ErrorResponse,
    ErrorDetail,
)

# ============================================================================
# OPENAPI DOCUMENTATION ENHANCEMENTS
# ============================================================================


class OpenAPITags:
    """Centralized tag definitions for OpenAPI documentation"""

    LEARNING = {
        "name": "📚 Learning Content",
        "description": """
        **Course Content Management**
        
        Manage the hierarchical educational content structure:
        - **Courses**: Top-level educational programs
        - **Lessons**: Structured learning modules within courses  
        - **Topics**: Specific subject areas within lessons
        - **Tasks**: Interactive exercises and assessments
        
        ### Features:
        - Hierarchical content organization
        - Progress tracking
        - Content availability management
        - Performance optimization with eager loading
        """,
    }

    STUDENT = {
        "name": "👨‍🎓 Student Progress",
        "description": """
        **Student Learning Management**
        
        Track and manage student progress through educational content:
        - **Code Execution**: Secure Python code compilation and testing
        - **Task Solutions**: Student submissions and scoring
        - **Progress Tracking**: Individual and course-wide analytics
        - **Security**: Multi-layered protection against code injection
        
        ### Security Features:
        - AST-based code analysis
        - Rate limiting with progressive penalties
        - Input sanitization and validation
        - Execution timeouts and resource limits
        """,
    }

    PROFESSOR = {
        "name": "👨‍🏫 Professor Analytics",
        "description": """
        **Course Administration & Analytics**
        
        Comprehensive tools for educators to manage courses and analyze student performance:
        - **Student Analytics**: Individual and aggregate performance metrics
        - **Course Management**: Content creation and modification
        - **Progress Monitoring**: Real-time tracking of student engagement
        - **Reporting**: Detailed analytics and insights
        
        ### Analytics Features:
        - Real-time performance dashboards
        - Completion rate tracking
        - Time-on-task analysis
        - Difficulty assessment
        """,
    }

    AUTH = {
        "name": "🔐 Authentication",
        "description": """
        **User Authentication & Authorization**
        
        Secure authentication system supporting multiple methods:
        - **Username/Password**: Traditional authentication
        - **Telegram Integration**: Seamless bot authentication
        - **Role-based Access**: Student, Professor, and Admin roles
        - **Session Management**: Secure token-based sessions
        
        ### Security Features:
        - Hash-based user identification
        - JWT token authentication
        - Rate-limited login attempts
        - Cross-platform compatibility
        """,
    }

    SYSTEM = {
        "name": "🔧 System",
        "description": """
        **System Information & Health**
        
        System monitoring and information endpoints:
        - **Health Checks**: Service availability monitoring
        - **API Information**: Version and endpoint discovery
        - **System Statistics**: Usage and performance metrics
        
        ### Monitoring:
        - Real-time health status
        - API version information
        - Service endpoint discovery
        """,
    }


# ============================================================================
# REQUEST/RESPONSE EXAMPLES
# ============================================================================


class APIExamples:
    """Centralized API examples for documentation"""

    # User Examples
    USER_LOGIN_REQUEST = {"username": "student123", "password": "secure_password"}

    USER_LOGIN_RESPONSE = {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": 1,
            "internal_user_id": "usr_abc123def456",
            "username": "student123",
            "status": "student",
            "telegram_user_id": None,
        },
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    }

    # Course Examples
    COURSE_RESPONSE = {
        "id": 1,
        "title": "Computational Thinking and Programming",
        "description": "Introduction to programming concepts using Python",
        "lesson_count": 12,
        "created_at": "2024-01-15T10:30:00Z",
    }

    COURSE_LIST_RESPONSE = {"success": True, "courses": [COURSE_RESPONSE], "total": 1}

    # Task Examples
    TASK_SOLUTION_REQUEST = {
        "task_id": 1,
        "user_id": "usr_abc123def456",
        "solution_content": {"code": "print('Hello, World!')", "language": "python"},
        "is_correct": True,
    }

    TASK_SOLUTION_RESPONSE = {
        "id": 1,
        "task_id": 1,
        "user_id": 1,
        "solution_content": {"code": "print('Hello, World!')", "language": "python", "output": "Hello, World!\n"},
        "is_correct": True,
        "points_earned": 10,
        "task_name": "Hello World Exercise",
        "task_type": "code_task",
        "created_at": "2024-01-15T14:30:00Z",
    }

    # Code Execution Examples
    CODE_COMPILE_REQUEST = {
        "code": "print('Hello World')\nresult = 2 + 2\nprint(f'2 + 2 = {result}')",
        "language": "python",
    }

    CODE_COMPILE_RESPONSE = {
        "success": True,
        "output": "Hello World\n2 + 2 = 4\n",
        "execution_time": 0.125,
        "memory_usage": "12.4 MB",
        "error": None,
    }

    # Security Examples
    SECURITY_VIOLATION_RESPONSE = {
        "success": False,
        "error": "Security violation: Import of dangerous module 'os' is not allowed",
        "detail": "Your code contains potentially dangerous operations that are not permitted",
        "status_code": 403,
        "request_id": "req_xyz789",
    }

    RATE_LIMIT_RESPONSE = {
        "success": False,
        "error": "Rate limit exceeded",
        "detail": "Too many requests. Try again in 60 seconds.",
        "status_code": 429,
        "request_id": "req_abc123",
    }

    # Error Examples
    VALIDATION_ERROR_RESPONSE = {
        "success": False,
        "error": "Validation Error",
        "detail": [{"field": "code", "message": "Field required", "code": "missing"}],
        "status_code": 422,
        "request_id": "req_def456",
    }

    NOT_FOUND_RESPONSE = {
        "success": False,
        "error": "Resource not found",
        "detail": "The requested course was not found",
        "status_code": 404,
        "request_id": "req_ghi789",
    }


# ============================================================================
# ENHANCED RESPONSE MODELS WITH EXAMPLES
# ============================================================================


class EnhancedCourseResponse(CourseResponse):
    """Course response with enhanced documentation"""

    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": APIExamples.COURSE_RESPONSE})


class EnhancedCourseListResponse(BaseResponse):
    """Course list response with examples"""

    courses: List[EnhancedCourseResponse] = Field(..., description="List of courses available to the user")
    total: int = Field(..., description="Total number of courses")

    model_config = ConfigDict(json_schema_extra={"example": APIExamples.COURSE_LIST_RESPONSE})


class EnhancedTaskSolutionResponse(TaskSolutionResponse):
    """Task solution response with enhanced documentation"""

    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": APIExamples.TASK_SOLUTION_RESPONSE})


class CodeExecutionResponse(BaseResponse):
    """Code execution response with security information"""

    output: str = Field(..., description="Program output from code execution", example="Hello World\n2 + 2 = 4\n")
    execution_time: float = Field(..., description="Execution time in seconds", example=0.125)
    memory_usage: Optional[str] = Field(None, description="Memory usage during execution", example="12.4 MB")
    error: Optional[str] = Field(None, description="Error message if execution failed", example=None)
    security_checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Security validation results",
        example={"dangerous_imports": False, "malicious_functions": False, "resource_limits": True},
    )

    model_config = ConfigDict(json_schema_extra={"example": APIExamples.CODE_COMPILE_RESPONSE})


class SecurityViolationResponse(ErrorResponse):
    """Security violation error response"""

    violation_type: str = Field(..., description="Type of security violation detected")
    blocked_content: Optional[str] = Field(None, description="The specific content that was blocked")

    model_config = ConfigDict(json_schema_extra={"example": APIExamples.SECURITY_VIOLATION_RESPONSE})


class RateLimitResponse(ErrorResponse):
    """Rate limiting error response"""

    retry_after: int = Field(..., description="Seconds to wait before retrying")
    requests_remaining: int = Field(0, description="Number of requests remaining in current window")

    model_config = ConfigDict(json_schema_extra={"example": APIExamples.RATE_LIMIT_RESPONSE})


# ============================================================================
# OPENAPI DOCUMENTATION METADATA
# ============================================================================


class OpenAPIMetadata:
    """Enhanced OpenAPI metadata for better documentation"""

    TITLE = "🎓 Educational Platform API"

    DESCRIPTION = """
    ## Educational Platform API v1.0
    
    A comprehensive, secure API for managing educational content, student progress, and course administration.
    
    ### 🚀 Key Features
    
    - **Hierarchical Content**: Courses → Lessons → Topics → Tasks
    - **Secure Code Execution**: Multi-layered security with AST analysis
    - **Progress Tracking**: Real-time student analytics
    - **Authentication**: Multi-method auth with Telegram integration
    - **Performance**: Optimized queries with eager loading
    
    ### 🔒 Security Features
    
    - **Code Injection Protection**: AST-based analysis blocks dangerous operations
    - **Rate Limiting**: Progressive penalties with user isolation
    - **Input Validation**: XSS, SQL injection, and malicious pattern detection
    - **Resource Management**: Execution timeouts and memory limits
    
    ### 📊 Analytics & Monitoring
    
    - **Student Progress**: Individual and aggregate performance metrics
    - **Course Analytics**: Completion rates and engagement tracking
    - **Real-time Monitoring**: Health checks and system statistics
    
    ### 🔗 Integration Support
    
    - **Telegram Bot**: Seamless mobile integration
    - **Multiple Authentication**: Username/password, OAuth, magic links
    - **API Versioning**: Backward-compatible endpoint evolution
    
    ### 📚 Educational Focus
    
    Designed specifically for computational thinking and programming education with:
    - Safe Python code execution environment
    - Interactive coding exercises
    - Automated feedback and scoring
    - Progress tracking and analytics
    
    ---
    
    **API Version**: 1.0.0  
    **Documentation**: [Swagger UI](/docs) | [ReDoc](/redoc)  
    **Support**: Check the repository for issues and contributions
    """

    VERSION = "1.0.0"

    CONTACT = {
        "name": "Educational Platform API",
        "url": "https://github.com/anthropics/claude-code",
        "email": "support@example.com",
    }

    LICENSE_INFO = {"name": "MIT License", "url": "https://opensource.org/licenses/MIT"}

    SERVERS = [
        {"url": "https://fastapi-vercel-lake.vercel.app", "description": "Production server"},
        {"url": "http://localhost:8000", "description": "Development server"},
    ]


# ============================================================================
# SECURITY SCHEMAS FOR OPENAPI
# ============================================================================

SECURITY_SCHEMES = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT token authentication. Include token in Authorization header.",
    },
    "UserAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-User-ID",
        "description": "User identification for request context",
    },
}

# Common response schemas for all endpoints
COMMON_RESPONSES = {
    400: {
        "description": "Bad Request - Invalid input data",
        "content": {
            "application/json": {
                "schema": ErrorResponse.model_json_schema(),
                "example": APIExamples.VALIDATION_ERROR_RESPONSE,
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication required",
        "content": {
            "application/json": {
                "schema": ErrorResponse.model_json_schema(),
                "example": {
                    "success": False,
                    "error": "Authentication required",
                    "detail": "Please provide valid authentication credentials",
                    "status_code": 401,
                },
            }
        },
    },
    403: {
        "description": "Forbidden - Security violation or insufficient permissions",
        "content": {
            "application/json": {
                "schema": SecurityViolationResponse.model_json_schema(),
                "example": APIExamples.SECURITY_VIOLATION_RESPONSE,
            }
        },
    },
    404: {
        "description": "Not Found - Resource does not exist",
        "content": {
            "application/json": {"schema": ErrorResponse.model_json_schema(), "example": APIExamples.NOT_FOUND_RESPONSE}
        },
    },
    422: {
        "description": "Validation Error - Request data validation failed",
        "content": {
            "application/json": {
                "schema": ErrorResponse.model_json_schema(),
                "example": APIExamples.VALIDATION_ERROR_RESPONSE,
            }
        },
    },
    429: {
        "description": "Rate Limit Exceeded - Too many requests",
        "content": {
            "application/json": {
                "schema": RateLimitResponse.model_json_schema(),
                "example": APIExamples.RATE_LIMIT_RESPONSE,
            }
        },
    },
    500: {
        "description": "Internal Server Error - Unexpected server error",
        "content": {
            "application/json": {
                "schema": ErrorResponse.model_json_schema(),
                "example": {
                    "success": False,
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred. Please try again later.",
                    "status_code": 500,
                },
            }
        },
    },
}
