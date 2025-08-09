"""
FastAPI Application with Restructured Hierarchical API
Version 2.0 - Implements the new modular router architecture

This version consolidates the flat router structure into logical service boundaries:
- Learning Content Service (/api/v1/courses)
- Student Progress Service (/api/v1/users) 
- Professor Analytics Service (/api/v1/admin)
- Authentication Service (/api/v1/auth)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import new consolidated routers
from routes import learning, student, professor, auth

# Create FastAPI instance with custom docs and OpenAPI URL
app = FastAPI(
    title="Educational Platform API",
    description="Hierarchical API for educational content management and student progress tracking",
    version="2.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# CORS configuration
origins = [
    "http://localhost:3000",  # Next.js frontend on port 3000
    "http://localhost:3001",  # If your frontend runs on port 3001
    "http://localhost:3002",  # If your frontend runs on port 3002
    "http://localhost:8000",  # FastAPI backend on port 8000
    "https://frontend-template-lilac.vercel.app",  # Vercel frontend address
    "https://dhdk.vercel.app",  # Vercel frontend address
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with hierarchical structure
app.include_router(
    learning.router, 
    prefix="/api/v1/courses", 
    tags=["📚 Learning Content"]
)

app.include_router(
    student.router, 
    prefix="/api/v1/users", 
    tags=["👨‍🎓 Student Progress"]
)

app.include_router(
    professor.router, 
    prefix="/api/v1/admin", 
    tags=["👨‍🏫 Professor Analytics"]
)

app.include_router(
    auth.router, 
    prefix="/api/v1/auth", 
    tags=["🔐 Authentication"]
)

# Legacy support router (for backward compatibility)
app.include_router(
    learning.router, 
    prefix="/api/courses",
    tags=["📚 Legacy - Learning Content"],
    include_in_schema=False  # Hide from docs
)

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint providing API information and available services
    """
    return {
        "message": "Educational Platform API v2.0",
        "version": "2.0.0",
        "architecture": "Hierarchical Service-Oriented",
        "services": {
            "learning_content": {
                "prefix": "/api/v1/courses",
                "description": "Course structure and content management",
                "endpoints": [
                    "GET /api/v1/courses/",
                    "GET /api/v1/courses/{course_id}",
                    "GET /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/{task_id}"
                ]
            },
            "student_progress": {
                "prefix": "/api/v1/users",
                "description": "User progress tracking and submissions",
                "endpoints": [
                    "GET /api/v1/users/{user_id}/profile",
                    "GET /api/v1/users/{user_id}/courses/{course_id}/progress",
                    "POST /api/v1/users/{user_id}/submissions"
                ]
            },
            "professor_analytics": {
                "prefix": "/api/v1/admin",
                "description": "Analytics and administrative functions",
                "endpoints": [
                    "GET /api/v1/admin/analytics/students",
                    "GET /api/v1/admin/analytics/tasks/completion",
                    "GET /api/v1/admin/student-forms"
                ]
            },
            "authentication": {
                "prefix": "/api/v1/auth",
                "description": "User authentication and session management",
                "endpoints": [
                    "POST /api/v1/auth/telegram/link",
                    "POST /api/v1/auth/telegram/complete",
                    "POST /api/v1/auth/sessions/refresh"
                ]
            }
        },
        "legacy_support": {
            "available": True,
            "prefix": "/api/courses",
            "note": "Legacy endpoints available for backward compatibility"
        },
        "documentation": "/docs",
        "openapi_schema": "/openapi.json"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    System health check endpoint
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "learning_content": "operational",
            "student_progress": "operational", 
            "professor_analytics": "operational",
            "authentication": "operational"
        }
    }


# API information endpoint
@app.get("/api")
async def api_info():
    """
    API information and service discovery endpoint
    """
    return {
        "api_version": "2.0.0",
        "architecture": "Hierarchical Service-Oriented",
        "base_url": "/api/v1",
        "services": [
            {
                "name": "learning_content",
                "prefix": "/api/v1/courses",
                "status": "active"
            },
            {
                "name": "student_progress", 
                "prefix": "/api/v1/users",
                "status": "active"
            },
            {
                "name": "professor_analytics",
                "prefix": "/api/v1/admin", 
                "status": "active"
            },
            {
                "name": "authentication",
                "prefix": "/api/v1/auth",
                "status": "active"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)