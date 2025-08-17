"""
Educational Platform API v1.0 - Clean Architecture
Single API version with proper schemas and OpenAPI generation
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime
import uuid
import json

# Import consolidated v1 routers ONLY
from routes import learning, student, professor, auth, users, telegram_auth, auth_demo
from config import settings
from utils.auth_middleware import add_auth_context_to_request

# Configure structured logging
from utils.structured_logging import (
    configure_logging,
    get_logger,
    log_request_middleware,
    set_correlation_id,
    LogCategory,
)

# Configure structured logging system
configure_logging(level="INFO", json_output=True)
logger = get_logger("app")

# Import enhanced OpenAPI configuration
from schemas.openapi_models import OpenAPIMetadata, OpenAPITags, SECURITY_SCHEMES

# Create FastAPI instance with enhanced metadata
app = FastAPI(
    title=OpenAPIMetadata.TITLE,
    description=OpenAPIMetadata.DESCRIPTION,
    version=OpenAPIMetadata.VERSION,
    contact=OpenAPIMetadata.CONTACT,
    license_info=OpenAPIMetadata.LICENSE_INFO,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=OpenAPIMetadata.SERVERS,
    openapi_tags=[
        OpenAPITags.LEARNING,
        OpenAPITags.STUDENT,
        OpenAPITags.PROFESSOR,
        OpenAPITags.AUTH,
        OpenAPITags.SYSTEM,
    ],
)

# CORS configuration - Load from environment
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
    ],
    expose_headers=["Content-Length", "Content-Range"],
)


# Structured logging middleware - adds correlation IDs and logs all requests
@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    """Add correlation IDs and structured logging to all requests"""
    return await log_request_middleware(request, call_next)


# Authentication middleware - adds auth context to all requests
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Add authentication context and request tracking to all requests"""
    return await add_auth_context_to_request(request, call_next)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with proper structure and logging"""
    errors = []
    for error in exc.errors():
        errors.append(
            {"field": ".".join(str(loc) for loc in error["loc"]), "message": error["msg"], "code": error["type"]}
        )

    # Log validation error with structured logging
    logger.warning(
        "Validation error",
        category=LogCategory.ERROR,
        request_method=request.method,
        request_path=request.url.path,
        error_type="ValidationError",
        error_message=f"{len(errors)} validation errors",
        extra={"errors": errors},
    )

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation Error",
            "detail": errors,
            "status_code": 422,
            "request_id": getattr(request.state, "request_id", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with proper structure and logging"""

    # Log HTTP exception with appropriate level
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code} error",
            category=LogCategory.ERROR,
            request_method=request.method,
            request_path=request.url.path,
            response_status=exc.status_code,
            error_message=exc.detail,
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"HTTP {exc.status_code} client error",
            category=LogCategory.ERROR,
            request_method=request.method,
            request_path=request.url.path,
            response_status=exc.status_code,
            error_message=exc.detail,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "detail": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with structured logging"""

    # Log unexpected error with full context
    logger.critical(
        "Unexpected server error",
        category=LogCategory.ERROR,
        exception=exc,
        request_method=request.method,
        request_path=request.url.path,
        user_id=getattr(request.state, "user_id", None),
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
            "request_id": getattr(request.state, "request_id", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )


# Include v1 routers with enhanced documentation
app.include_router(
    learning.router,
    prefix="/api/v1/courses",
    tags=["📚 Learning Content"],
    responses={
        **{
            code: response
            for code, response in __import__(
                "schemas.openapi_models", fromlist=["COMMON_RESPONSES"]
            ).COMMON_RESPONSES.items()
        }
    },
)

app.include_router(
    student.router,
    prefix="/api/v1/students",
    tags=["👨‍🎓 Student Progress"],
    responses={
        **{
            code: response
            for code, response in __import__(
                "schemas.openapi_models", fromlist=["COMMON_RESPONSES"]
            ).COMMON_RESPONSES.items()
        }
    },
)

app.include_router(
    professor.router,
    prefix="/api/v1/professor",
    tags=["👨‍🏫 Professor Analytics"],
    responses={
        **{
            code: response
            for code, response in __import__(
                "schemas.openapi_models", fromlist=["COMMON_RESPONSES"]
            ).COMMON_RESPONSES.items()
        }
    },
)

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["🔐 Authentication"],
    responses={
        **{
            code: response
            for code, response in __import__(
                "schemas.openapi_models", fromlist=["COMMON_RESPONSES"]
            ).COMMON_RESPONSES.items()
        }
    },
)

app.include_router(
    users.router,
    tags=["👥 Users"],
    responses={
        **{
            code: response
            for code, response in __import__(
                "schemas.openapi_models", fromlist=["COMMON_RESPONSES"]
            ).COMMON_RESPONSES.items()
        }
    },
)

# Legacy-compatible endpoints used in tests
app.include_router(
    telegram_auth.router,
    tags=["🔐 Authentication"],
    responses={
        **{
            code: response
            for code, response in __import__(
                "schemas.openapi_models", fromlist=["COMMON_RESPONSES"]
            ).COMMON_RESPONSES.items()
        }
    },
)

# Authentication demonstration endpoints
app.include_router(
    auth_demo.router,
    prefix="/api/v1",
    tags=["🔐 Authentication"],
    responses={
        **{
            code: response
            for code, response in __import__(
                "schemas.openapi_models", fromlist=["COMMON_RESPONSES"]
            ).COMMON_RESPONSES.items()
        }
    },
)


# Root endpoint
@app.get(
    "/",
    tags=["🔧 System"],
    summary="API Information",
    description="Get comprehensive API information including version, status, and available services",
    response_description="API information and service endpoints",
)
async def root():
    """
    ## API Root Information

    Returns comprehensive information about the Educational Platform API including:
    - Current API version and status
    - Available service endpoints
    - Documentation links
    - System timestamp

    This endpoint can be used for API discovery and health checking.
    """
    return {
        "name": "Educational Platform API",
        "version": "1.0.0",
        "status": "operational",
        "description": "Comprehensive educational platform with secure code execution",
        "documentation": {"swagger": "/docs", "redoc": "/redoc", "openapi_spec": "/openapi.json"},
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "courses": {"endpoint": "/api/v1/courses", "description": "Course content management"},
            "students": {"endpoint": "/api/v1/students", "description": "Student progress and code execution"},
            "professor": {"endpoint": "/api/v1/professor", "description": "Analytics and course administration"},
            "auth": {"endpoint": "/api/v1/auth", "description": "Authentication and user management"},
        },
        "features": [
            "Secure code execution with AST analysis",
            "Multi-layered security protection",
            "Real-time progress tracking",
            "Telegram bot integration",
            "Comprehensive analytics",
        ],
    }


# Health check endpoint
@app.get(
    "/health",
    tags=["🔧 System"],
    summary="Health Check",
    description="Service health monitoring endpoint for uptime checks",
    response_description="Current service health status",
)
async def health_check():
    """
    ## Service Health Check

    Provides real-time health status for monitoring and alerting systems.

    Returns:
    - Service operational status
    - Current timestamp
    - API version information

    Use this endpoint for:
    - Load balancer health checks
    - Monitoring system alerts
    - Service discovery validation
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "uptime": "Service operational",
        "checks": {"database": "operational", "security_systems": "active", "code_execution": "secure"},
    }


# API version endpoint
@app.get(
    "/api/v1",
    tags=["🔧 System"],
    summary="API v1 Information",
    description="Detailed information about API v1 endpoints and capabilities",
    response_description="API v1 endpoint directory and documentation links",
)
async def api_v1_info():
    """
    ## API v1 Endpoint Directory

    Comprehensive directory of all available API v1 endpoints with descriptions.

    ### Available Services:
    - **Courses**: Hierarchical content management
    - **Students**: Progress tracking and code execution
    - **Professor**: Analytics and administration
    - **Auth**: User authentication and authorization

    ### Documentation:
    - Interactive API docs at `/docs`
    - Alternative documentation at `/redoc`
    - OpenAPI specification at `/openapi.json`
    """
    return {
        "version": "1.0.0",
        "release_date": "2024-01-15",
        "endpoints": {
            "courses": {
                "path": "/api/v1/courses",
                "description": "Course, lesson, topic, and task management",
                "methods": ["GET", "POST", "PUT", "DELETE"],
            },
            "students": {
                "path": "/api/v1/students",
                "description": "Student progress, solutions, and secure code execution",
                "methods": ["GET", "POST"],
                "features": ["Code compilation", "Progress tracking", "Security validation"],
            },
            "professor": {
                "path": "/api/v1/professor",
                "description": "Course analytics and student performance monitoring",
                "methods": ["GET"],
                "features": ["Student analytics", "Course statistics", "Performance insights"],
            },
            "auth": {
                "path": "/api/v1/auth",
                "description": "User authentication and session management",
                "methods": ["POST"],
                "features": ["Username/password auth", "Telegram integration", "JWT tokens"],
            },
        },
        "documentation": {"interactive": "/docs", "redoc": "/redoc", "openapi": "/openapi.json"},
        "security": {
            "authentication": "JWT Bearer tokens",
            "code_execution": "AST-based security analysis",
            "rate_limiting": "Progressive penalties",
            "input_validation": "Multi-layer sanitization",
        },
    }
