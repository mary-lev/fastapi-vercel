"""
FastAPI Application v2.0 - Clean Architecture
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

# Import consolidated v1 routers ONLY
from routes import learning, student, professor, auth

# Import schemas for error handling
from schemas.api_models import ErrorResponse, ErrorDetail

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI instance with enhanced metadata
app = FastAPI(
    title="Educational Platform API",
    description="""
    ## 🎓 Educational Platform API v1.0
    
    A comprehensive API for managing educational content, student progress, and course administration.
    
    ### Services:
    - **📚 Learning Content**: Course, lesson, topic, and task management
    - **👨‍🎓 Student Progress**: Progress tracking, solutions, and attempts
    - **👨‍🏫 Professor Analytics**: Student analytics and course management
    - **🔐 Authentication**: User authentication and Telegram integration
    
    ### Features:
    - Type-safe API with Pydantic models
    - OpenAPI 3.0 specification
    - Comprehensive error handling
    - Request/response validation
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://your-api.vercel.app", "description": "Production server"},
    ],
)

# CORS configuration - Configure based on your deployment
origins = [
    "http://localhost:3000",  # Next.js frontend development
    "http://localhost:3001",  # Alternative frontend port
    "http://localhost:3002",  # Alternative frontend port
    "http://localhost:8000",  # API documentation
    "https://frontend-template-lilac.vercel.app",  # Production frontend
    "https://dhdk.vercel.app",  # Production frontend alternate
    # Add your Telegram Web App origin if needed
    "https://web.telegram.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# Middleware for request tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracking"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Process request and measure time
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Add headers to response
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request details
    logger.info(
        f"Request {request_id}: {request.method} {request.url.path} "
        f"completed in {process_time:.3f}s with status {response.status_code}"
    )
    
    return response


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with proper schema"""
    errors = []
    for error in exc.errors():
        errors.append(ErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            code=error["type"]
        ))
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Validation Error",
            detail=errors,
            status_code=422,
            request_id=getattr(request.state, "request_id", None)
        ).model_dump()
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with proper schema"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code,
            request_id=getattr(request.state, "request_id", None)
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred. Please try again later.",
            status_code=500,
            request_id=getattr(request.state, "request_id", None)
        ).model_dump()
    )


# Include v1 routers with proper prefixes and tags
app.include_router(
    learning.router,
    prefix="/api/v1/courses",
    tags=["📚 Learning Content"],
)

app.include_router(
    student.router,
    prefix="/api/v1/students",
    tags=["👨‍🎓 Student Progress"],
)

app.include_router(
    professor.router,
    prefix="/api/v1/professor",
    tags=["👨‍🏫 Professor Analytics"],
)

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["🔐 Authentication"],
)


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint providing API information
    """
    return {
        "name": "Educational Platform API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "openapi_spec": "/openapi.json",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


# API version endpoint
@app.get("/api/v1", tags=["System"])
async def api_v1_info():
    """
    API v1 information and available endpoints
    """
    return {
        "version": "1.0.0",
        "endpoints": {
            "courses": "/api/v1/courses",
            "students": "/api/v1/students",
            "professor": "/api/v1/professor",
            "auth": "/api/v1/auth",
        },
        "documentation": "/docs",
        "openapi": "/openapi.json",
    }


# NO LEGACY ROUTES - CLEAN ARCHITECTURE
# All endpoints use v1 API with proper schemas
# Frontend and bot must use /api/v1/* endpoints