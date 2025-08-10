"""
Comprehensive Pydantic schemas for API v1
This is the single source of truth for all API contracts
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"


class TaskType(str, Enum):
    CODE = "code_task"
    TRUE_FALSE = "true_false_quiz"
    MULTIPLE_SELECT = "multiple_select_quiz"
    SINGLE_QUESTION = "single_question_task"


# ============================================================================
# BASE MODELS
# ============================================================================

class BaseResponse(BaseModel):
    """Base response with common fields"""
    success: bool = True
    message: Optional[str] = None


class PaginationParams(BaseModel):
    """Common pagination parameters"""
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# ============================================================================
# USER MODELS
# ============================================================================

class UserBase(BaseModel):
    username: str
    status: UserRole


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    internal_user_id: str
    telegram_user_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)


class UserLoginResponse(BaseResponse):
    user: UserResponse
    token: Optional[str] = None


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    status: Optional[UserRole] = None


# ============================================================================
# COURSE MODELS
# ============================================================================

class CourseBase(BaseModel):
    title: str
    description: str


class CourseCreate(CourseBase):
    pass


class CourseResponse(CourseBase):
    id: int
    lesson_count: int = 0
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CourseListResponse(BaseResponse):
    courses: List[CourseResponse]
    total: int


class CourseDetailResponse(CourseResponse):
    """Extended course info with instructor and requirements"""
    instructor_name: str
    instructor_title: str
    requirements: List[str]
    objectives: List[str]


# ============================================================================
# LESSON MODELS
# ============================================================================

class LessonBase(BaseModel):
    title: str
    lesson_number: int
    start_date: Optional[datetime] = None


class LessonResponse(LessonBase):
    id: int
    course_id: int
    topic_count: int = 0
    is_available: bool = True
    
    model_config = ConfigDict(from_attributes=True)


class LessonListResponse(BaseResponse):
    lessons: List[LessonResponse]
    course_id: int


# ============================================================================
# TOPIC MODELS
# ============================================================================

class TopicBase(BaseModel):
    title: str
    background: Optional[str] = None
    objectives: Optional[str] = None
    content_file_md: Optional[str] = None


class TopicResponse(TopicBase):
    id: int
    lesson_id: int
    topic_order: int
    task_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class TopicDetailResponse(TopicResponse):
    """Topic with tasks included"""
    tasks: List['TaskResponse'] = []


# ============================================================================
# TASK MODELS
# ============================================================================

class TaskBase(BaseModel):
    task_name: str
    task_type: TaskType
    points: int = Field(..., ge=0, le=100)
    order: int
    is_active: bool = True


class TaskResponse(TaskBase):
    id: int
    task_link: str
    topic_id: int
    data: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class TaskCreateRequest(TaskBase):
    topic_id: int
    data: Dict[str, Any] = Field(..., description="Task-specific data")


class TaskUpdateRequest(BaseModel):
    task_name: Optional[str] = None
    points: Optional[int] = Field(None, ge=0, le=100)
    data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


# ============================================================================
# TASK ATTEMPT/SOLUTION MODELS
# ============================================================================

class TaskAttemptBase(BaseModel):
    task_id: int
    attempt_content: Dict[str, Any]


class TaskAttemptRequest(TaskAttemptBase):
    user_id: str  # internal_user_id


class TaskAttemptResponse(TaskAttemptBase):
    id: int
    user_id: int
    created_at: datetime
    score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class TaskSolutionBase(BaseModel):
    task_id: int
    solution_content: Dict[str, Any]
    is_correct: bool


class TaskSolutionRequest(TaskSolutionBase):
    user_id: str  # internal_user_id


class TaskSolutionResponse(TaskSolutionBase):
    id: int
    user_id: int
    created_at: datetime
    points_earned: int = 0
    task_name: Optional[str] = None
    task_type: Optional[TaskType] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PROGRESS & ANALYTICS MODELS
# ============================================================================

class UserProgressResponse(BaseModel):
    user_id: str
    course_id: int
    total_points: int
    completed_tasks: int
    total_tasks: int
    completion_percentage: float
    last_activity: Optional[datetime] = None
    lessons_progress: List[Dict[str, Any]] = []


class UserSolutionsResponse(BaseResponse):
    solutions: List[TaskSolutionResponse]
    total_points: int
    total_solutions: int


class TaskAnalyticsResponse(BaseModel):
    task_id: int
    task_name: str
    total_attempts: int
    unique_users: int
    success_rate: float
    average_score: float
    average_time_seconds: Optional[float] = None


# ============================================================================
# ENROLLMENT MODELS
# ============================================================================

class EnrollmentRequest(BaseModel):
    course_id: int
    user_id: str  # internal_user_id


class EnrollmentResponse(BaseResponse):
    enrollment_id: int
    enrolled_at: datetime
    course: CourseResponse


# ============================================================================
# AI FEEDBACK MODELS
# ============================================================================

class AIFeedbackRequest(BaseModel):
    task_attempt_id: int
    feedback_type: str = "code_review"


class AIFeedbackResponse(BaseModel):
    id: int
    task_attempt_id: int
    feedback_content: str
    score: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SESSION RECORDING MODELS
# ============================================================================

class SessionRecordingRequest(BaseModel):
    session_id: str
    user_id: str
    events: List[Dict[str, Any]] = Field(..., max_length=10000)
    session_duration: Optional[int] = Field(None, gt=0)


class SessionRecordingResponse(BaseResponse):
    session_id: str
    recorded_at: datetime


# ============================================================================
# TELEGRAM AUTH MODELS
# ============================================================================

class TelegramLinkRequest(BaseModel):
    telegram_user_id: int
    telegram_username: Optional[str] = None


class TelegramLinkResponse(BaseResponse):
    link_token: str
    expires_at: datetime
    link_url: str


class TelegramCompleteRequest(BaseModel):
    token: str


class TelegramCompleteResponse(BaseResponse):
    user: UserResponse
    session_token: Optional[str] = None


# ============================================================================
# ERROR MODELS
# ============================================================================

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[Union[str, List[ErrorDetail]]] = None
    status_code: int
    request_id: Optional[str] = None


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

class BatchTaskCreateRequest(BaseModel):
    topic_id: int
    tasks: List[TaskCreateRequest]


class BatchTaskResponse(BaseResponse):
    created: List[TaskResponse]
    failed: List[Dict[str, Any]] = []


class BatchUserEnrollRequest(BaseModel):
    course_id: int
    user_ids: List[str]


class BatchEnrollResponse(BaseResponse):
    enrolled: List[str]
    failed: List[Dict[str, str]] = []


# ============================================================================
# PROFESSOR/ADMIN MODELS
# ============================================================================

class StudentAnalyticsResponse(BaseModel):
    student_id: str
    username: str
    total_points: int
    tasks_completed: int
    average_score: float
    last_active: Optional[datetime] = None
    course_progress: Dict[int, float] = {}


class CourseAnalyticsResponse(BaseModel):
    course_id: int
    total_students: int
    active_students: int
    average_progress: float
    total_tasks: int
    completion_rate: float
    top_performers: List[StudentAnalyticsResponse] = []


class SystemStatsResponse(BaseModel):
    total_users: int
    total_courses: int
    total_tasks: int
    total_attempts: int
    active_sessions: int
    database_size_mb: float
    api_version: str = "1.0.0"


# Update forward references
TopicDetailResponse.model_rebuild()