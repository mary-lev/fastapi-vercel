from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime


class TaskSolutionCreate(BaseModel):
    """Schema for creating task solutions"""

    userId: str = Field(..., min_length=1, max_length=255, description="User UUID")
    lessonName: str = Field(..., min_length=1, max_length=500, description="Task link/identifier")
    isSuccessful: bool = Field(default=False, description="Whether the attempt was successful")
    solutionContent: str = Field(default="", max_length=10000, description="Solution content")

    @validator("userId")
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v.strip()

    @validator("lessonName")
    def validate_lesson_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Lesson name cannot be empty")
        return v.strip()

    @validator("solutionContent")
    def validate_solution_content(cls, v):
        if len(v) > 10000:
            raise ValueError("Solution content too long (max 10000 characters)")
        return v


class TaskUpdateSchema(BaseModel):
    """Schema for updating tasks"""

    taskId: int = Field(..., gt=0, description="Task ID")
    newQuestion: str = Field(..., min_length=5, max_length=1000, description="Updated question")
    newOptions: List[Dict[str, str]] = Field(..., min_items=2, max_items=10, description="Answer options")
    newCorrectAnswers: List[str] = Field(..., min_items=1, description="Correct answer IDs")

    @validator("newQuestion")
    def validate_question(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("Question must be at least 5 characters")
        return v.strip()

    @validator("newOptions")
    def validate_options(cls, v):
        if len(v) < 2:
            raise ValueError("Must provide at least 2 options")
        for option in v:
            if "name" not in option or len(option["name"].strip()) < 1:
                raise ValueError("Each option must have a non-empty name")
        return v

    @validator("newCorrectAnswers")
    def validate_correct_answers(cls, v):
        if not v:
            raise ValueError("Must provide at least one correct answer")
        return v


class UserRegistrationSchema(BaseModel):
    """Schema for user registration"""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, max_length=100, description="Password")
    email: Optional[str] = Field(None, max_length=255, description="Email address")

    @validator("username")
    def validate_username(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v.lower().strip()

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class SessionRecordingSchema(BaseModel):
    """Schema for session recording data"""

    user_id: str = Field(..., description="User identifier")
    events: List[Dict] = Field(..., max_items=10000, description="Session events")
    session_duration: Optional[int] = Field(None, gt=0, description="Session duration in seconds")

    @validator("events")
    def validate_events(cls, v):
        if len(v) > 10000:
            raise ValueError("Too many events in session (max 10000)")
        return v


class TaskAttemptSchema(BaseModel):
    """Schema for task attempt validation"""

    task_id: int = Field(..., gt=0, description="Task ID")
    user_id: str = Field(..., min_length=1, description="User ID")
    attempt_content: str = Field(..., max_length=50000, description="Attempt content")

    @validator("attempt_content")
    def validate_attempt_content(cls, v):
        if len(v) > 50000:
            raise ValueError("Attempt content too long (max 50000 characters)")
        return v


class CourseCreateSchema(BaseModel):
    """Schema for creating courses"""

    title: str = Field(..., min_length=1, max_length=200, description="Course title")
    description: str = Field(..., max_length=2000, description="Course description")
    professor_id: int = Field(..., gt=0, description="Professor user ID")

    @validator("title")
    def validate_title(cls, v):
        return v.strip()

    @validator("description")
    def validate_description(cls, v):
        return v.strip()


class LessonCreateSchema(BaseModel):
    """Schema for creating lessons"""

    title: str = Field(..., min_length=1, max_length=200, description="Lesson title")
    description: str = Field(..., max_length=2000, description="Lesson description")
    course_id: int = Field(..., gt=0, description="Course ID")
    lesson_order: int = Field(..., ge=1, description="Lesson order")
    textbook: Optional[str] = Field(None, max_length=500, description="Textbook reference")
    start_date: Optional[datetime] = Field(None, description="Lesson start date")

    @validator("title", "description")
    def validate_text_fields(cls, v):
        return v.strip()
