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
# Course Instructor schemas
class CourseInstructorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    image: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    social_links: Optional[List[Dict[str, str]]] = None  # Array of {platform, url}
    is_primary: bool = False
    display_order: int = 1


class CourseInstructorCreate(CourseInstructorBase):
    course_id: int = Field(..., gt=0)


class CourseInstructorResponse(CourseInstructorBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    course_overview: Optional[str] = None  # Extended description
    learning_objectives: Optional[List[str]] = None  # Array of learning goals
    requirements: Optional[List[str]] = None  # Array of requirements
    target_audience: Optional[List[str]] = None  # Array of target audience
    duration_weeks: Optional[int] = Field(None, ge=1, le=52)
    difficulty_level: Optional[str] = Field(None, regex="^(beginner|intermediate|advanced)$")
    course_image: Optional[str] = None  # Course cover image URL
    # Enrollment management
    enrollment_open_date: Optional[datetime] = None  # When enrollment opens
    enrollment_close_date: Optional[datetime] = None  # When enrollment closes
    max_enrollments: Optional[int] = Field(None, ge=1)  # Maximum students allowed


class CourseCreate(CourseBase):
    professor_id: int = Field(..., gt=0)


class CourseResponse(CourseBase):
    id: int
    professor_id: int
    instructors: Optional[List[CourseInstructorResponse]] = None
    # Computed enrollment fields (not in database, calculated by API)
    enrollment_status: Optional[str] = None  # "open", "closed", "not_yet_open"
    is_enrollment_open: Optional[bool] = None  # True/False for enrollment availability
    current_enrollments: Optional[int] = None  # Current number of enrolled students
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Extended Course Response for detailed course information including lessons
class CourseDetailResponse(CourseResponse):
    lessons: Optional[List[Dict]] = None  # Will be populated with lesson data

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


# ===============================================================================
# Learning Analytics Schemas
# ===============================================================================

# Task-Level Analysis Schema (for OpenAI structured output)
class TaskAnalysisSchema(BaseModel):
    """Schema for task-level analysis structured output from LLM"""
    error_patterns: List[str] = Field(
        ...,
        description="List of 2-3 specific error patterns observed",
        min_items=0,
        max_items=5
    )
    learning_progression: str = Field(
        ...,
        description="Classification of learning progression",
        regex="^(immediate_success|struggle_then_breakthrough|persistent_difficulty)$"
    )
    concept_gaps: List[str] = Field(
        ...,
        description="List of 2-3 specific concept gaps requiring reinforcement",
        min_items=0,
        max_items=5
    )
    strengths: List[str] = Field(
        ...,
        description="List of 1-2 demonstrated strengths",
        min_items=0,
        max_items=3
    )
    help_needed: bool = Field(
        ...,
        description="Whether student needs instructor intervention"
    )
    difficulty_level: str = Field(
        ...,
        description="Assessment of task difficulty appropriateness",
        regex="^(too_easy|appropriate|too_hard)$"
    )


# Lesson-Level Analysis Schema (for OpenAI structured output)
class LessonAnalysisSchema(BaseModel):
    """Schema for lesson-level analysis structured output from LLM"""
    mastered_concepts: List[str] = Field(
        ...,
        description="List of 2-4 concepts mastered across tasks",
        min_items=0,
        max_items=6
    )
    struggling_concepts: List[str] = Field(
        ...,
        description="List of 2-4 concepts student is struggling with",
        min_items=0,
        max_items=6
    )
    pacing: str = Field(
        ...,
        description="Assessment of lesson pacing appropriateness",
        regex="^(too_fast|appropriate|too_slow)$"
    )
    retention_score: float = Field(
        ...,
        description="Score 0.0-1.0 indicating concept retention from early to late tasks",
        ge=0.0,
        le=1.0
    )
    help_seeking_pattern: str = Field(
        ...,
        description="Assessment of student's help-seeking behavior",
        regex="^(too_frequent|appropriate|too_rare)$"
    )
    topic_dependencies_issues: List[str] = Field(
        ...,
        description="List of topic dependency problems identified",
        min_items=0,
        max_items=5
    )


# Course-Level Analysis Schema (for OpenAI structured output)
class ConceptGraph(BaseModel):
    """Nested schema for concept mastery graph"""
    strong_foundations: List[str] = Field(
        ...,
        description="Concepts with high retention and transfer",
        min_items=0,
        max_items=10
    )
    weak_connections: List[str] = Field(
        ...,
        description="Topic transitions where student struggled",
        min_items=0,
        max_items=10
    )


class PracticeRecommendation(BaseModel):
    """Nested schema for personalized practice recommendations"""
    concept: str = Field(..., min_length=1, max_length=200)
    difficulty: str = Field(..., regex="^(beginner|intermediate|advanced)$")
    count: int = Field(..., ge=1, le=10, description="Recommended number of practice tasks")


class CourseProfileSchema(BaseModel):
    """Schema for course-level profile structured output from LLM"""
    core_strengths: List[str] = Field(
        ...,
        description="2-3 programming skills consistently demonstrated",
        min_items=0,
        max_items=5
    )
    persistent_weaknesses: List[str] = Field(
        ...,
        description="2-3 concepts remaining challenging across lessons",
        min_items=0,
        max_items=5
    )
    learning_velocity: str = Field(
        ...,
        description="Overall learning velocity assessment",
        regex="^(rapid_improvement|steady_progress|plateaued|declining)$"
    )
    resilience_score: float = Field(
        ...,
        description="Score 0.0-1.0 indicating recovery from failures",
        ge=0.0,
        le=1.0
    )
    preferred_learning_style: str = Field(
        ...,
        description="Identified preferred learning style",
        regex="^(visual_with_examples|trial_and_error|concept_first|pattern_recognition)$"
    )
    readiness_for_advanced: bool = Field(
        ...,
        description="Whether student is ready for advanced topics"
    )
    concept_graph: ConceptGraph = Field(
        ...,
        description="Map of concept mastery strengths and weaknesses"
    )
    recommended_practice: List[PracticeRecommendation] = Field(
        ...,
        description="2-3 personalized practice recommendations",
        min_items=0,
        max_items=5
    )
