# schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class UserStatus(str, Enum):
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    status: Optional[UserStatus] = None


class UserCreate(UserBase):
    internal_user_id: str = Field(..., min_length=1, max_length=255)
    hashed_sub: str = Field(..., min_length=1, max_length=255)
    telegram_user_id: Optional[int] = None


class UserResponse(UserBase):
    id: int
    internal_user_id: str
    telegram_user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# Task schemas
class TaskBase(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=255)
    task_link: str = Field(..., min_length=1, max_length=255)
    points: Optional[int] = Field(None, ge=0)
    order: int = Field(..., ge=0)
    data: Dict = Field(..., description="Task configuration data")
    is_active: bool = True


class TaskCreate(TaskBase):
    type: str = Field(..., min_length=1, max_length=50)
    topic_id: int = Field(..., gt=0)


class TaskResponse(TaskBase):
    id: int
    type: str
    topic_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Task Attempt schemas
class TaskAttemptBase(BaseModel):
    attempt_number: int = Field(..., ge=1)
    is_successful: bool = False
    attempt_content: Optional[str] = Field(None, max_length=50000)


class TaskAttemptCreate(TaskAttemptBase):
    user_id: int = Field(..., gt=0)
    task_id: int = Field(..., gt=0)


class TaskAttemptResponse(TaskAttemptBase):
    id: int
    user_id: int
    task_id: int
    submitted_at: datetime
    
    class Config:
        from_attributes = True


# Task Solution schemas
class TaskSolutionBase(BaseModel):
    solution_content: str = Field(..., min_length=1, max_length=50000)


class TaskSolutionCreate(TaskSolutionBase):
    user_id: int = Field(..., gt=0)
    task_id: int = Field(..., gt=0)


class TaskSolutionResponse(TaskSolutionBase):
    id: int
    user_id: int
    task_id: int
    completed_at: datetime
    
    class Config:
        from_attributes = True


# AI Feedback schemas
class AIFeedbackBase(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=10000)


class AIFeedbackCreate(AIFeedbackBase):
    task_id: int = Field(..., gt=0)
    task_attempt_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)


class AIFeedbackResponse(AIFeedbackBase):
    id: int
    task_id: int
    task_attempt_id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Course schemas
class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class CourseCreate(CourseBase):
    professor_id: int = Field(..., gt=0)


class CourseResponse(CourseBase):
    id: int
    professor_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Lesson schemas
class LessonBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    lesson_order: int = Field(..., ge=0)
    textbook: Optional[str] = Field(None, max_length=500)
    start_date: Optional[datetime] = None


class LessonCreate(LessonBase):
    course_id: int = Field(..., gt=0)


class LessonResponse(LessonBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Topic schemas
class TopicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    background: Optional[str] = Field(None, max_length=1000)
    objectives: Optional[str] = Field(None, max_length=1000)
    content_file_md: Optional[str] = Field(None, max_length=500)
    concepts: Optional[str] = Field(None, max_length=1000)
    topic_order: int = Field(..., ge=0)


class TopicCreate(TopicBase):
    lesson_id: int = Field(..., gt=0)


class TopicResponse(TopicBase):
    id: int
    lesson_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Summary schemas
class SummaryBase(BaseModel):
    lesson_name: str = Field(..., min_length=1, max_length=255)
    lesson_link: str = Field(..., min_length=1, max_length=255)
    lesson_type: str = Field(default="Summary", max_length=100)
    icon_file: Optional[str] = Field(None, max_length=500)
    data: Dict = Field(..., description="Summary content data")


class SummaryCreate(SummaryBase):
    topic_id: int = Field(..., gt=0)


class SummaryResponse(SummaryBase):
    id: int
    topic_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# For backward compatibility
class SummarySchema(SummaryResponse):
    topic_title: str  # Additional field for the topic title
    
    class Config:
        from_attributes = True


# Contact Message schemas
class ContactMessageBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    anonymous: bool = False
    page_url: Optional[str] = Field(None, max_length=500)
    attachments: Optional[Dict] = None


class ContactMessageCreate(ContactMessageBase):
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    user_id: Optional[int] = None


class ContactMessageResponse(ContactMessageBase):
    id: int
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    status: str
    user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# Course Enrollment schemas
class CourseEnrollmentBase(BaseModel):
    pass


class CourseEnrollmentCreate(CourseEnrollmentBase):
    user_id: int = Field(..., gt=0)
    course_id: int = Field(..., gt=0)


class CourseEnrollmentResponse(CourseEnrollmentBase):
    id: int
    user_id: int
    course_id: int
    enrolled_at: datetime
    
    class Config:
        from_attributes = True


# Tag schemas
class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: int
    
    class Config:
        from_attributes = True
