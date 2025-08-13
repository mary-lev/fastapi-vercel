# FastAPI Router Structure Reorganization

## Current Issues with Flat Router Structure

**Current structure:**
```python
app.include_router(submission.router, tags=["Submissions"])
app.include_router(users.router, tags=["Users"])
app.include_router(solution.router, tags=["Solutions"])
app.include_router(lesson.router, tags=["Lessons"])
app.include_router(task_generator.router, tags=["Task Generator"])
app.include_router(topics.router, tags=["Topics"])
app.include_router(task.router, tags=["Tasks"])
app.include_router(course.router, tags=["Courses"])
app.include_router(session.router, tags=["Sessions"])
app.include_router(telegram_bot.router, tags=["Telegram Bot"])
app.include_router(telegram_auth.router, tags=["Telegram Auth"])
app.include_router(student_form.router, tags=["Student Forms"])
```

**Problems:**
1. **No logical hierarchy** - courses, lessons, tasks are separate but should be nested
2. **Inconsistent patterns** - some endpoints are resource-focused, others are action-focused
3. **Hard to scale** - adding new features requires new top-level routers
4. **Poor discoverability** - relationships between resources aren't clear

## Proposed Hierarchical Structure

### Option A: Resource-Centric Hierarchy (Recommended)

```python
# Core learning content hierarchy
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses"])
# Includes: /courses/{course_id}/lessons/{lesson_id}/tasks/{task_id}

# User-centric data and interactions  
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
# Includes: /users/{user_id}/courses/{course_id}/progress

# Authentication & Sessions
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
# Includes: /auth/telegram, /auth/sessions

# Administrative functions
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administration"])
# Includes: /admin/task-generator, /admin/student-forms
```

### Detailed URL Structure

#### 1. Course Hierarchy with Topics (courses.router)
```
/api/v1/courses/
├── GET /courses/                                                    # List all courses
├── GET /courses/{course_id}                                         # Get course details
├── GET /courses/{course_id}/lessons/                                # List course lessons  
├── GET /courses/{course_id}/lessons/{lesson_id}                     # Get lesson details
├── GET /courses/{course_id}/lessons/{lesson_id}/topics/             # List lesson topics
├── GET /courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}   # Get topic details
├── GET /courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/              # List topic tasks
└── GET /courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/{task_id}     # Get task details
```

#### 2. User-Centric Data (users.router)
```
/api/v1/users/{user_id}/
├── GET /users/{user_id}/profile/                    # User profile
├── GET /users/{user_id}/courses/                    # User's enrolled courses
├── GET /users/{user_id}/courses/{course_id}/progress/                                        # Course progress
├── GET /users/{user_id}/courses/{course_id}/lessons/{lesson_id}/progress/                   # Lesson progress
├── GET /users/{user_id}/courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/progress/ # Topic progress
├── POST /users/{user_id}/solutions/                 # Submit solution
├── GET /users/{user_id}/solutions/                  # Get user solutions
├── GET /users/{user_id}/solutions/{solution_id}     # Get specific solution
├── POST /users/{user_id}/submissions/               # Submit task attempt
├── GET /users/{user_id}/submissions/                # Get user submissions
└── GET /users/{user_id}/sessions/                   # User sessions
```

#### 3. Authentication (auth.router)
```
/api/v1/auth/
├── POST /auth/login                                 # Standard login
├── POST /auth/logout                                # Logout
├── POST /auth/telegram/initiate                     # Start Telegram auth
├── POST /auth/telegram/complete                     # Complete Telegram auth
├── GET /auth/telegram/status                        # Check Telegram auth status
└── POST /auth/sessions/refresh                      # Refresh session
```

#### 4. Administration (admin.router)  
```
/api/v1/admin/
├── POST /admin/task-generator/generate              # Generate tasks
├── GET /admin/task-generator/templates              # Get generation templates
├── POST /admin/student-forms/                       # Create student form
├── GET /admin/student-forms/                        # List student forms
├── GET /admin/users/                                # Manage users (admin only)
└── GET /admin/analytics/                            # System analytics
```

### Alternative: Mixed Approach (Option B)

If you prefer more flexibility:

```python
# Core resources (traditional REST)
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses"])
app.include_router(lessons.router, prefix="/api/v1/lessons", tags=["Lessons"]) 
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])

# User interactions (user-centric)
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

# Specialized functionality
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administration"])
```

## Implementation Strategy

### Phase 1: Consolidate Related Routers

**Merge these existing routers:**
- `solution.router` + `submission.router` → `users.router` (user-centric actions)
- `telegram_bot.router` + `telegram_auth.router` + `session.router` → `auth.router`
- `task_generator.router` + `student_form.router` → `admin.router`

### Phase 2: Implement Hierarchical Structure

**Create new consolidated routers:**

#### courses.py (Main hierarchy)
```python
from fastapi import APIRouter, Depends
from . import lessons, tasks, topics

router = APIRouter()

# Course endpoints
@router.get("/")
async def get_courses(): ...

@router.get("/{course_id}")  
async def get_course(course_id: int): ...

# Include sub-routers with proper nesting
router.include_router(
    lessons.router, 
    prefix="/{course_id}/lessons",
    tags=["Lessons"]
)
```

#### lessons.py (Nested under courses)
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_lessons(course_id: int): ...

@router.get("/{lesson_id}")
async def get_lesson(course_id: int, lesson_id: int): ...

# Topics nested under lessons  
router.include_router(
    topics.router,
    prefix="/{lesson_id}/topics",
    tags=["Topics"] 
)
```

#### topics.py (Nested under lessons)
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_topics(course_id: int, lesson_id: int): ...

@router.get("/{topic_id}")
async def get_topic(course_id: int, lesson_id: int, topic_id: int): ...

# Tasks nested under topics
router.include_router(
    tasks.router,
    prefix="/{topic_id}/tasks", 
    tags=["Tasks"]
)
```

### Phase 3: User-Centric Endpoints

#### users.py (User interactions)
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/{user_id}/courses/{course_id}/progress")
async def get_user_course_progress(user_id: str, course_id: int): ...

@router.post("/{user_id}/solutions")  
async def submit_solution(user_id: str, solution_data: dict): ...

@router.post("/{user_id}/submissions")
async def submit_task_attempt(user_id: str, submission_data: dict): ...
```

## Benefits of Hierarchical Structure

1. **Intuitive URLs**: `/courses/1/lessons/2/topics/3/tasks/4` clearly shows the complete hierarchy
2. **Better Organization**: Related functionality is grouped together
3. **Scalability**: Easy to add new nested resources
4. **RESTful**: Follows REST conventions and HTTP semantics
5. **Auto-documentation**: OpenAPI docs will show clear hierarchy
6. **Frontend-friendly**: URLs match your frontend routing structure

## Migration Steps

1. **Create new consolidated router files** (courses.py, users.py, auth.py, admin.py)
2. **Move existing endpoints** to appropriate new routers
3. **Update URL patterns** to follow hierarchical structure  
4. **Add route aliases** for backward compatibility during transition
5. **Update frontend API calls** to use new endpoints
6. **Remove old routers** after successful migration
7. **Update API documentation**

## Recommended Final Structure

```python
# main.py
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses & Learning"])
app.include_router(users.router, prefix="/api/v1/users", tags=["User Data & Progress"])  
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administration"])

# Optional: Keep some flat endpoints for simple operations
app.include_router(health.router, prefix="/api/v1/health", tags=["System Health"])
```

This structure is **much cleaner**, follows **REST best practices**, and will make your API **easier to understand and maintain**.