from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Enum, Boolean, JSON, BigInteger, Text
from sqlalchemy import Table, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from datetime import datetime
import uuid

Base = declarative_base()

# Existing Enums and Models


class UserStatus(enum.Enum):
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    internal_user_id = Column(String, index=True)
    hashed_sub = Column(String, unique=True, index=True)
    username = Column(String, unique=False, index=True, default="Anonymous")
    first_name = Column(String, nullable=True)  # User's first name
    last_name = Column(String, nullable=True)  # User's last name
    status = Column(Enum(UserStatus), index=True, nullable=True)
    telegram_user_id = Column(BigInteger, nullable=True, unique=True, index=True)


class TelegramLinkToken(Base):
    __tablename__ = "telegram_link_tokens"

    jti = Column(String, primary_key=True)  # JWT ID for single-use tracking
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)

    # Telegram user info for user creation
    telegram_username = Column(String, nullable=True)  # Telegram username (without @)
    first_name = Column(String, nullable=True)  # User's first name from Telegram
    last_name = Column(String, nullable=True)  # User's last name from Telegram


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="enrollments")
    course = relationship("Course", backref="enrollments")

    # Ensure unique enrollment per user-course pair
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="unique_user_course_enrollment"),)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Tag name, e.g., "easy", "data analysis"


task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# Polymorphic Task Model
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    task_name = Column(String, nullable=False)
    task_link = Column(String, nullable=False, index=True)
    points = Column(Integer, nullable=True)
    type = Column(String(50), nullable=False)
    order = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Dynamic task generation fields
    is_generated = Column(Boolean, default=False, nullable=False)
    generated_for_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    generation_prompt = Column(Text, nullable=True)
    ai_model_used = Column(String(50), nullable=True)

    # Attempt limit fields
    max_attempts = Column(Integer, nullable=True)  # NULL means unlimited
    attempt_strategy = Column(String(20), default="unlimited", nullable=False)  # 'unlimited', 'single'

    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "task"}

    tags = relationship("Tag", secondary=task_tags, backref="tasks", cascade="all")
    ai_feedbacks = relationship("AIFeedback", back_populates="related_task", cascade="all, delete-orphan")
    attempts = relationship("TaskAttempt", back_populates="related_task", cascade="all, delete-orphan")
    solutions = relationship("TaskSolution", back_populates="related_task", cascade="all, delete-orphan")

    def get_attempt_count(self, user_id: int, db) -> int:
        """Get the number of attempts a user has made on this task"""
        from sqlalchemy import func

        return (
            db.query(func.count(TaskAttempt.id))
            .filter(TaskAttempt.task_id == self.id, TaskAttempt.user_id == user_id)
            .scalar()
            or 0
        )

    def can_attempt(self, user_id: int, db) -> bool:
        """Check if user can make another attempt"""
        if self.attempt_strategy == "unlimited":
            return True
        attempt_count = self.get_attempt_count(user_id, db)
        return attempt_count < (self.max_attempts or 0)

    def is_completed_by_user(self, user_id: int, db) -> bool:
        """Check if user has successfully completed this task"""
        return (
            db.query(TaskAttempt)
            .filter(TaskAttempt.task_id == self.id, TaskAttempt.user_id == user_id, TaskAttempt.is_successful == True)
            .first()
            is not None
        )


class TrueFalseQuiz(Task):
    __tablename__ = "true_false_quizzes"
    id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    # Define the polymorphic identity and any additional properties for this model
    __mapper_args__ = {"polymorphic_identity": "true_false_quiz"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override defaults for quiz type
        if "attempt_strategy" not in kwargs:
            self.attempt_strategy = "single"
        if "max_attempts" not in kwargs:
            self.max_attempts = 1


class MultipleSelectQuiz(Task):
    __tablename__ = "multiple_select_quizzes"
    id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "multiple_select_quiz"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override defaults for quiz type - single attempt only
        if "attempt_strategy" not in kwargs:
            self.attempt_strategy = "single"
        if "max_attempts" not in kwargs:
            self.max_attempts = 1


class CodeTask(Task):
    __tablename__ = "code_tasks"
    id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "code_task"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Code tasks have unlimited attempts by default
        if "attempt_strategy" not in kwargs:
            self.attempt_strategy = "unlimited"
        if "max_attempts" not in kwargs:
            self.max_attempts = None  # NULL = unlimited


class SingleQuestionTask(Task):
    __tablename__ = "single_question_tasks"
    id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "single_question_task"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Single question tasks are quizzes - single attempt only
        if "attempt_strategy" not in kwargs:
            self.attempt_strategy = "single"
        if "max_attempts" not in kwargs:
            self.max_attempts = 1


class TaskAttempt(Base):
    __tablename__ = "task_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, default=func.now(), nullable=False)
    is_successful = Column(Boolean, default=False)
    attempt_content = Column(Text, nullable=True)  # Changed to Text for longer content

    user = relationship("User", backref="task_attempts")
    related_task = relationship("Task", back_populates="attempts")

    # Add composite index for common queries
    __table_args__ = (
        Index("idx_task_attempts_user_task", "user_id", "task_id"),
        Index("idx_task_attempts_submitted_at", "submitted_at"),
    )


class TaskSolution(Base):
    __tablename__ = "task_solutions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    solution_content = Column(Text, nullable=False)  # Changed to Text and made not nullable
    completed_at = Column(DateTime, default=func.now(), nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    points_earned = Column(Integer, nullable=True)

    user = relationship("User", backref="task_solutions")
    related_task = relationship("Task", back_populates="solutions")

    # Add composite index for common queries
    __table_args__ = (
        Index("idx_task_solutions_user_task", "user_id", "task_id"),
        Index("idx_task_solutions_completed_at", "completed_at"),
    )


class TaskGenerationRequest(Base):
    __tablename__ = "task_generation_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_task_attempt_id = Column(Integer, ForeignKey("task_attempts.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, generating, completed, failed
    error_analysis = Column(JSON, nullable=True)  # Store analysis of what went wrong
    generated_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="generation_requests")
    source_attempt = relationship("TaskAttempt", backref="generation_requests")
    topic = relationship("Topic", backref="generation_requests")
    generated_task = relationship("Task", foreign_keys=[generated_task_id], backref="generation_request")

    # Add indexes for common queries
    __table_args__ = (
        Index("idx_generation_requests_user_status", "user_id", "status"),
        Index("idx_generation_requests_created_at", "created_at"),
    )


# Existing Models for Courses, Lessons, etc.
class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)

    # Extended course information fields
    course_overview = Column(Text, nullable=True)  # Extended description for overview section
    learning_objectives = Column(JSON, nullable=True)  # Array of learning goals
    requirements = Column(JSON, nullable=True)  # Array of course requirements
    target_audience = Column(JSON, nullable=True)  # Array of target audience descriptions

    # Course metadata
    duration_weeks = Column(Integer, nullable=True)  # Estimated course duration
    difficulty_level = Column(String(20), nullable=True)  # beginner, intermediate, advanced
    course_image = Column(String, nullable=True)  # Course cover image URL

    # Enrollment management
    enrollment_open_date = Column(DateTime, nullable=True)  # When enrollment opens
    enrollment_close_date = Column(DateTime, nullable=True)  # When enrollment closes
    max_enrollments = Column(Integer, nullable=True)  # Maximum number of students (optional capacity limit)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    lessons = relationship("Lesson", order_by="Lesson.lesson_order", back_populates="course")
    instructors = relationship("CourseInstructor", back_populates="course", cascade="all, delete-orphan")

    def is_enrollment_open(self) -> bool:
        """Check if enrollment is currently open for this course"""
        from datetime import datetime

        now = datetime.utcnow()

        # If no dates are set, enrollment is open by default
        if not self.enrollment_open_date and not self.enrollment_close_date:
            return True

        # Check if current time is within enrollment period
        enrollment_started = not self.enrollment_open_date or now >= self.enrollment_open_date
        enrollment_not_ended = not self.enrollment_close_date or now <= self.enrollment_close_date

        return enrollment_started and enrollment_not_ended

    def get_enrollment_status(self) -> str:
        """Get human-readable enrollment status"""
        from datetime import datetime

        now = datetime.utcnow()

        if not self.enrollment_open_date and not self.enrollment_close_date:
            return "open"

        if self.enrollment_open_date and now < self.enrollment_open_date:
            return "not_yet_open"
        elif self.enrollment_close_date and now > self.enrollment_close_date:
            return "closed"
        else:
            return "open"


class CourseInstructor(Base):
    __tablename__ = "course_instructors"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    # Instructor information
    name = Column(String(255), nullable=False)  # Full name
    title = Column(String(255), nullable=True)  # Professional title/role
    bio = Column(Text, nullable=True)  # Biography text
    image = Column(String, nullable=True)  # Profile photo URL
    email = Column(String(255), nullable=True)  # Contact email

    # Social media links stored as JSON
    social_links = Column(JSON, nullable=True)  # Array of {platform, url} objects

    # Metadata
    is_primary = Column(Boolean, default=False, nullable=False)  # Primary instructor flag
    display_order = Column(Integer, default=1, nullable=False)  # Display order
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    course = relationship("Course", back_populates="instructors")

    # Table constraints
    __table_args__ = (Index("idx_course_instructors_course_order", "course_id", "display_order"),)


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    lesson_order = Column(Integer, nullable=False)
    textbook = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True, default=func.now())

    topics = relationship("Topic", order_by="Topic.id", back_populates="lesson")
    course = relationship("Course", back_populates="lessons")  # Add this line


class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    background = Column(String, index=True)
    objectives = Column(String, index=True)
    content_file_md = Column(String, index=True)
    concepts = Column(String, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    topic_order = Column(Integer, nullable=False)

    lesson = relationship("Lesson", back_populates="topics")  # Add this line
    tasks = relationship("Task", backref="topic", lazy="select", order_by="Task.order")
    summary = relationship("Summary", uselist=False, back_populates="topic")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    lesson_name = Column(String, nullable=False)
    lesson_link = Column(String, nullable=False, unique=True)
    lesson_type = Column(String, default="Summary", nullable=False)
    icon_file = Column(String, nullable=True)
    data = Column(JSON, nullable=False)  # Storing description, items, textbooks in JSON
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationship with Topic
    topic = relationship("Topic", back_populates="summary")


# Session recording model is no longer used


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    task_attempt_id = Column(
        Integer, ForeignKey("task_attempts.id"), nullable=False
    )  # Made not nullable - feedback should always reference an attempt
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feedback = Column(Text, nullable=False)  # Changed to Text for longer feedback content
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", backref="ai_feedbacks")
    related_task = relationship("Task", back_populates="ai_feedbacks")
    task_attempt = relationship("TaskAttempt", backref="ai_feedback")

    # Add indexes for common queries
    __table_args__ = (
        Index("idx_ai_feedback_user_task", "user_id", "task_id"),
        Index("idx_ai_feedback_attempt", "task_attempt_id"),
        Index("idx_ai_feedback_created_at", "created_at"),
    )


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    anonymous = Column(Boolean, default=False, nullable=False)
    telegram_user_id = Column(BigInteger, nullable=True, index=True)
    telegram_username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    page_url = Column(String, nullable=True)
    attachments = Column(JSON, nullable=True)  # Store attachment data as JSON
    created_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)  # When message was processed/handled
    status = Column(String, default="received", nullable=False)  # received, processing, handled, etc.

    # Optional: link to user if they have an account
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="contact_messages")


class StudentFormSubmission(Base):
    __tablename__ = "student_form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Question 1: Programming experience
    programming_experience = Column(String, nullable=False)
    other_language = Column(String, nullable=True)  # When "other" is selected

    # Question 2: Operating system
    operating_system = Column(String, nullable=False)

    # Question 3: Software installation
    software_installation = Column(String, nullable=False)

    # Question 4: Python confidence (1-5 scale)
    python_confidence = Column(Integer, nullable=False)

    # Question 5: Problem solving approach (multiple choice - stored as JSON array)
    problem_solving_approach = Column(JSON, nullable=False)

    # Question 6: Learning preferences (multiple choice - stored as JSON array)
    learning_preferences = Column(JSON, nullable=False)

    # Question 7: New device approach
    new_device_approach = Column(String, nullable=False)

    # Question 8: Study time commitment
    study_time_commitment = Column(String, nullable=False)

    # Question 9: Homework schedule
    homework_schedule = Column(String, nullable=False)

    # Question 10: Preferred study times (multiple choice - stored as JSON array)
    preferred_study_times = Column(JSON, nullable=False)

    # Question 11: Study organization
    study_organization = Column(String, nullable=False)

    # Question 12: Help seeking preference
    help_seeking_preference = Column(String, nullable=False)

    # Question 13: Additional comments (optional)
    additional_comments = Column(String, nullable=True)

    # Metadata
    submitted_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to User
    user = relationship("User", backref="student_form_submissions")
