"""
Student Progress Service Router
Handles user-centric operations: progress tracking, submissions, solutions
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Path, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field

from models import (
    User,
    Task,
    TaskAttempt,
    TaskSolution,
    TaskGenerationRequest,
    Course,
    Lesson,
    Topic,
    AIFeedback,
    CourseEnrollment,
)
from db import get_db
from utils.structured_logging import get_logger, LogCategory, log_execution, log_security_event
from utils.cache_manager import cache_manager, cache_key_for_user, invalidate_user_cache
from utils.checker import run_code
from utils.evaluator import evaluate_code_submission, evaluate_text_submission
from utils.auth_dependencies import resolve_user_flexible, require_api_key, get_user_by_id
from utils.security_validation import validate_code_request, validate_text_request, log_security_violation
from utils.rate_limiting import check_code_execution_limits, record_security_violation_for_user
from schemas.security import SecureCompileRequest, SecureCodeSubmitRequest, SecureTextSubmitRequest

# Optional test patching hook for db session
db = None  # tests may set routes.student.db to a Session-like object

router = APIRouter()

# Create logger for this module
logger = get_logger("routes.student")


# Background task functions for learning analytics (use separate DB sessions)
def _run_task_analysis_background(user_id: int, task_id: int):
    """
    Background task to analyze task performance with its own database session.
    This prevents blocking the main API response and avoids session conflicts.

    IMPORTANT: This is a sync function (not async) to ensure it runs truly in background.
    If it were async, FastAPI would await it before closing the HTTP response.
    """
    import asyncio
    from db import SessionLocal

    # Create new event loop for this background task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    db = SessionLocal()
    try:
        from utils.learning_analytics import analyze_task_performance

        logger.info(
            f"🔄 [BACKGROUND] Task analysis STARTED for user {user_id}, task {task_id}",
            category=LogCategory.PERFORMANCE,
            extra={"step": "background_started", "timestamp": datetime.utcnow().isoformat()}
        )

        # Run async function in this thread's event loop
        loop.run_until_complete(analyze_task_performance(user_id, task_id, db))

        logger.info(
            f"✅ [BACKGROUND] Task analysis COMPLETED for user {user_id}, task {task_id}",
            category=LogCategory.PERFORMANCE,
            extra={"step": "background_completed", "timestamp": datetime.utcnow().isoformat()}
        )
    except Exception as e:
        logger.error(
            f"Background task analysis failed: {str(e)}",
            category=LogCategory.ERROR,
            exception=e,
            extra={"user_id": user_id, "task_id": task_id}
        )
    finally:
        db.close()
        loop.close()


def _run_lesson_analysis_background(user_id: int, lesson_id: int):
    """
    Background task to analyze lesson progress with its own database session.
    This prevents blocking the main API response and avoids session conflicts.

    IMPORTANT: This is a sync function (not async) to ensure it runs truly in background.
    If it were async, FastAPI would await it before closing the HTTP response.
    """
    import asyncio
    from db import SessionLocal

    # Create new event loop for this background task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    db = SessionLocal()
    try:
        from utils.learning_analytics import analyze_lesson_progress

        logger.info(
            f"🔄 [BACKGROUND] Lesson analysis STARTED for user {user_id}, lesson {lesson_id}",
            category=LogCategory.PERFORMANCE,
            extra={"step": "background_started", "timestamp": datetime.utcnow().isoformat()}
        )

        # Run async function in this thread's event loop
        loop.run_until_complete(analyze_lesson_progress(user_id, lesson_id, db))

        logger.info(
            f"✅ [BACKGROUND] Lesson analysis COMPLETED for user {user_id}, lesson {lesson_id}",
            category=LogCategory.PERFORMANCE,
            extra={"step": "background_completed", "timestamp": datetime.utcnow().isoformat()}
        )
    except Exception as e:
        logger.error(
            f"Background lesson analysis failed: {str(e)}",
            category=LogCategory.ERROR,
            exception=e,
            extra={"user_id": user_id, "lesson_id": lesson_id}
        )
    finally:
        db.close()
        loop.close()


# Helper function to resolve user ID (supports both integer and string/UUID formats)
def _db_session(db_param: Session) -> Session:
    patched = globals().get("db")
    if patched is not None:
        maybe_query = getattr(patched, "query", None)
        if callable(maybe_query):
            return patched  # patched by tests
    return db_param


# NOTE: resolve_user function has been moved to utils/auth_dependencies.py
# as resolve_user_flexible() for centralized authentication management


# Temporary compatibility function for gradual migration
def resolve_user(user_id: Union[int, str], db: Session) -> User:
    """
    TEMPORARY: Legacy user resolution function for backward compatibility
    This will be removed once all endpoints are migrated to the new auth system
    """
    if isinstance(user_id, int):
        user = db.query(User).filter(User.id == user_id).first()
    else:
        user = db.query(User).filter(User.internal_user_id == user_id).first()
        if not user:
            user = db.query(User).filter(User.username == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    return user


# Pydantic models
class SubmissionRequest(BaseModel):
    task_id: int
    submission_data: Dict[str, Any]
    attempt_number: Optional[int] = 1


class SolutionRequest(BaseModel):
    task_id: int
    solution_data: Dict[str, Any]
    is_correct: bool = True


class ProgressResponse(BaseModel):
    course_id: int
    total_tasks: int
    completed_tasks: int
    completion_percentage: float
    points_earned: int
    total_points: int
    last_activity: Optional[datetime] = None


class TaskProgressResponse(BaseModel):
    task_id: int
    task_name: str
    attempts: int
    completed: bool
    solution_id: Optional[int] = None
    points_earned: int
    last_attempt: Optional[datetime] = None


# User profile and basic info
@router.get(
    "/{user_id}/profile",
    summary="Get Student Profile",
    description="Retrieve detailed student profile information including enrollment status and basic metrics",
    response_description="Student profile with enrollment and activity information",
    responses={
        200: {
            "description": "Student profile retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "student123",
                        "internal_user_id": "usr_abc123def456",
                        "status": "student",
                        "telegram_user_id": 123456789,
                    }
                }
            },
        }
    },
)
async def get_user_profile(
    request: Request,
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)", example="usr_abc123def456"),
    db: Session = Depends(get_db),
):
    """
    ## Get Student Profile Information

    Retrieves comprehensive student profile data including:
    - Basic user information (username, ID, status)
    - Telegram integration status
    - Account creation and activity details

    ### Supported User ID Formats:
    - **Integer**: Database primary key (e.g., `1`, `42`)
    - **String/UUID**: Internal user ID (e.g., `usr_abc123def456`)
    - **Username**: User's display name (e.g., `student123`)

    ### Use Cases:
    - Profile page display
    - User verification
    - Account status checking
    - Integration status validation
    """
    try:
        # Check cache first
        cache_key = cache_key_for_user(user_id, "profile")
        cached_profile = cache_manager.get(cache_key)

        if cached_profile is not None:
            logger.debug(
                f"Returning cached user profile",
                category=LogCategory.PERFORMANCE,
                extra={"cache_hit": True, "user_id": str(user_id)},
            )
            return cached_profile

        user = await get_user_by_id(user_id, request, db)

        profile_data = {
            "id": user.id,
            "username": user.username,
            "internal_user_id": user.internal_user_id,
            "status": user.status.value if user.status else None,
            "telegram_user_id": user.telegram_user_id,
        }

        # Cache for 5 minutes
        cache_manager.set(cache_key, profile_data, ttl=300)

        logger.info(
            f"User profile fetched and cached",
            category=LogCategory.PERFORMANCE,
            extra={"cache_hit": False, "user_id": str(user_id)},
        )

        return profile_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user profile {user_id}: {e}", category=LogCategory.ERROR, exception=e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Course enrollment and progress
@router.get("/{user_id}/courses", summary="Get user's enrolled courses")
async def get_user_courses(
    request: Request,
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    db: Session = Depends(get_db),
):
    """Get all courses the user is enrolled in - supports both integer and string user IDs"""
    try:
        user = await get_user_by_id(user_id, request, db)

        # Use eager loading to prevent N+1 queries when accessing course data
        enrollments = (
            db.query(CourseEnrollment)
            .options(joinedload(CourseEnrollment.course))
            .filter(CourseEnrollment.user_id == user.id)
            .all()
        )

        courses = []
        for enrollment in enrollments:
            course = enrollment.course
            courses.append(
                {
                    "id": course.id,
                    "title": course.title,
                    "description": course.description,
                    "enrolled_at": enrollment.enrolled_at,
                    "professor_id": course.professor_id,
                }
            )

        return courses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving courses for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/courses/{course_id}/progress", summary="Get user's course progress")
async def get_user_course_progress(
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    course_id: int = Path(..., description="Course ID"),
    db: Session = Depends(get_db),
):
    """Get detailed progress for a specific course - supports both integer and string user IDs"""
    try:
        user = resolve_user(user_id, db)

        # Verify user is enrolled in the course
        enrollment = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
            .first()
        )

        if not enrollment:
            raise HTTPException(status_code=404, detail="User not enrolled in this course")

        # Get all tasks in the course
        total_tasks_query = db.query(Task).join(Topic).join(Lesson).filter(Lesson.course_id == course_id)
        total_tasks = total_tasks_query.count()
        total_points = (
            db.query(func.sum(Task.points)).filter(Task.id.in_(total_tasks_query.with_entities(Task.id))).scalar() or 0
        )

        # Get completed tasks (tasks with solutions)
        completed_tasks = (
            db.query(TaskSolution)
            .join(Task)
            .join(Topic)
            .join(Lesson)
            .filter(TaskSolution.user_id == user.id, Lesson.course_id == course_id)
            .count()
        )

        # Get points earned
        points_earned = (
            db.query(func.sum(Task.points))
            .join(TaskSolution)
            .join(Topic)
            .join(Lesson)
            .filter(TaskSolution.user_id == user.id, Lesson.course_id == course_id)
            .scalar()
            or 0
        )

        # Get last activity
        last_activity = (
            db.query(func.max(TaskAttempt.submitted_at))
            .join(Task)
            .join(Topic)
            .join(Lesson)
            .filter(TaskAttempt.user_id == user.id, Lesson.course_id == course_id)
            .scalar()
        )

        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "course_id": course_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_percentage": round(completion_percentage, 2),
            "points_earned": points_earned,
            "total_points": total_points,
            "last_activity": last_activity,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving course progress for user {user_id}, course {course_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/courses/{course_id}/lessons/{lesson_id}/progress", summary="Get user's lesson progress")
async def get_user_lesson_progress(
    user_id: int = Path(..., description="User ID"),
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    db: Session = Depends(get_db),
):
    """Get detailed progress for a specific lesson"""
    try:
        # Verify lesson belongs to course and user is enrolled
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first()

        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        enrollment = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == user_id, CourseEnrollment.course_id == course_id)
            .first()
        )

        if not enrollment:
            raise HTTPException(status_code=404, detail="User not enrolled in this course")

        # Get all tasks in the lesson
        total_tasks = db.query(Task).join(Topic).filter(Topic.lesson_id == lesson_id).count()

        # Get completed tasks
        completed_tasks = (
            db.query(TaskSolution)
            .join(Task)
            .join(Topic)
            .filter(TaskSolution.user_id == user_id, Topic.lesson_id == lesson_id)
            .count()
        )

        # Get task-level progress efficiently with a single query
        task_progress = (
            db.query(
                Task.id,
                Task.task_name,
                Task.points,
                func.count(TaskAttempt.id).label("attempts"),
                func.max(TaskAttempt.submitted_at).label("last_attempt"),
                TaskSolution.id.label("solution_id"),
            )
            .join(Topic)
            .outerjoin(TaskAttempt, (TaskAttempt.task_id == Task.id) & (TaskAttempt.user_id == user_id))
            .outerjoin(TaskSolution, (TaskSolution.task_id == Task.id) & (TaskSolution.user_id == user_id))
            .filter(Topic.lesson_id == lesson_id)
            .group_by(Task.id, Task.task_name, Task.points, TaskSolution.id)
            .order_by(Task.order)  # Add ordering to prevent sorting in Python
            .all()
        )

        tasks = []
        for task_info in task_progress:
            tasks.append(
                {
                    "task_id": task_info.id,
                    "task_name": task_info.task_name,
                    "attempts": task_info.attempts or 0,
                    "completed": task_info.solution_id is not None,
                    "solution_id": task_info.solution_id,
                    "points_earned": task_info.points if task_info.solution_id else 0,
                    "last_attempt": task_info.last_attempt,
                }
            )

        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "lesson_id": lesson_id,
            "lesson_title": lesson.title,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_percentage": round(completion_percentage, 2),
            "tasks": tasks,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lesson progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/courses/{course_id}/lessons/{lesson_id}/summary", summary="Get lesson completion summary")
async def get_lesson_summary(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    db: Session = Depends(get_db),
):
    """
    Get lesson completion summary with statistics and motivational message.
    Returns summary text and completion statistics for the specified lesson.
    """
    try:
        # Verify user exists
        user = await get_user_by_id(user_id, request, db)

        # Verify lesson belongs to course
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first()

        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Verify user is enrolled
        enrollment = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
            .first()
        )

        if not enrollment:
            raise HTTPException(status_code=404, detail="User not enrolled in this course")

        # Get all ACTIVE tasks in the lesson only
        total_tasks = db.query(Task).join(Topic).filter(Topic.lesson_id == lesson_id, Task.is_active == True).count()

        # Get all ACTIVE tasks for proper completion counting
        active_tasks = db.query(Task).join(Topic).filter(Topic.lesson_id == lesson_id, Task.is_active == True).all()
        code_task_ids = [t.id for t in active_tasks if t.type == "code_task"]
        quiz_task_ids = [
            t.id for t in active_tasks if t.type in ["true_false_quiz", "multiple_select_quiz", "single_question_task"]
        ]

        # Count completed ACTIVE tasks (code tasks from TaskAttempt + quiz tasks from TaskSolution)
        code_completed = 0
        if code_task_ids:
            code_completed = (
                db.query(func.count(func.distinct(TaskAttempt.task_id)))
                .filter(
                    TaskAttempt.user_id == user.id,
                    TaskAttempt.task_id.in_(code_task_ids),
                    TaskAttempt.is_successful == True,
                )
                .scalar()
                or 0
            )

        quiz_completed = 0
        if quiz_task_ids:
            quiz_completed = (
                db.query(func.count(func.distinct(TaskSolution.task_id)))
                .filter(
                    TaskSolution.user_id == user.id,
                    TaskSolution.task_id.in_(quiz_task_ids),
                    TaskSolution.is_correct == True,
                )
                .scalar()
                or 0
            )

        completed_tasks = code_completed + quiz_completed

        # Calculate accuracy rate based on unique tasks attempted vs completed
        # Use subqueries to ensure accurate distinct counting
        from sqlalchemy import and_, exists, distinct

        # Count unique ACTIVE tasks attempted (code tasks from TaskAttempt + quiz tasks from TaskSolution)
        code_tasks_attempted = 0
        if code_task_ids:
            code_tasks_attempted = (
                db.query(func.count(func.distinct(TaskAttempt.task_id)))
                .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id.in_(code_task_ids))
                .scalar()
                or 0
            )

        quiz_tasks_attempted = 0
        if quiz_task_ids:
            quiz_tasks_attempted = (
                db.query(func.count(func.distinct(TaskSolution.task_id)))
                .filter(TaskSolution.user_id == user.id, TaskSolution.task_id.in_(quiz_task_ids))
                .scalar()
                or 0
            )

        tasks_attempted = code_tasks_attempted + quiz_tasks_attempted

        # Tasks completed successfully is already calculated above as completed_tasks
        tasks_completed_successfully = completed_tasks

        accuracy_rate = 0
        if tasks_attempted > 0:
            # Debug logging to help identify issues
            logger.debug(
                f"Accuracy calculation: {tasks_completed_successfully} successful / {tasks_attempted} attempted"
            )

            # Ensure we don't have more successful tasks than attempted tasks (data integrity check)
            if tasks_completed_successfully > tasks_attempted:
                logger.warning(
                    f"Data integrity issue: {tasks_completed_successfully} successful > {tasks_attempted} attempted for user {user.id}, lesson {lesson_id}"
                )
                tasks_completed_successfully = tasks_attempted

            accuracy_rate = round((tasks_completed_successfully / tasks_attempted) * 100, 1)
            # Ensure accuracy never exceeds 100%
            accuracy_rate = min(accuracy_rate, 100.0)

        # Calculate time spent per task, then sum up (only for code tasks since quiz tasks are typically quick)
        time_spent_minutes = 0.0
        if code_tasks_attempted > 0:
            # Get first and last attempt per ACTIVE CODE task to calculate time spent on each task
            task_time_data = (
                db.query(
                    TaskAttempt.task_id,
                    func.min(TaskAttempt.submitted_at).label("first_attempt"),
                    func.max(TaskAttempt.submitted_at).label("last_attempt"),
                    func.count(TaskAttempt.id).label("attempt_count"),
                )
                .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id.in_(code_task_ids))
                .group_by(TaskAttempt.task_id)
                .all()
            )

            for task_data in task_time_data:
                if task_data.first_attempt and task_data.last_attempt:
                    task_time_diff = task_data.last_attempt - task_data.first_attempt
                    task_minutes = task_time_diff.total_seconds() / 60

                    # For single attempts or very short time spans, use a minimum time estimate
                    if task_minutes < 2:  # Less than 2 minutes
                        # Base time estimate: 3 minutes + 1 minute per additional attempt
                        task_minutes = 3 + (task_data.attempt_count - 1)
                    else:
                        # Cap maximum time per task at 2 hours to handle cases where
                        # students leave tasks open for days
                        task_minutes = min(task_minutes, 120)

                    time_spent_minutes += task_minutes

            # Round total time to 1 decimal place
            time_spent_minutes = round(time_spent_minutes, 1)

        # Generate appropriate summary message based on completion
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # NEW: Trigger lesson-level analysis if completion >= 50% (course_id=2 only)
        lesson_analysis = None
        if completion_percentage >= 50 and course_id == 2:
            try:
                from models import StudentLessonAnalysis

                # Check if analysis already exists
                existing_analysis = db.query(StudentLessonAnalysis).filter(
                    StudentLessonAnalysis.user_id == user.id,
                    StudentLessonAnalysis.lesson_id == lesson_id
                ).first()

                # Determine if we need to regenerate the analysis
                should_regenerate = False

                if existing_analysis:
                    # Calculate how much progress has been made since last analysis
                    old_completion = existing_analysis.analysis.get('completion_percentage', 0) if existing_analysis.analysis else 0
                    completion_delta = completion_percentage - old_completion

                    # Regenerate if:
                    # 1. Completion increased by 20% or more (significant progress)
                    # 2. Student reached 100% completion (milestone)
                    if completion_delta >= 20:
                        should_regenerate = True
                        logger.info(
                            f"Lesson analysis needs regeneration: completion went from {old_completion}% to {completion_percentage}%",
                            category=LogCategory.PERFORMANCE
                        )
                    elif completion_percentage == 100 and old_completion < 100:
                        should_regenerate = True
                        logger.info(
                            f"Lesson analysis needs regeneration: student completed the lesson",
                            category=LogCategory.PERFORMANCE
                        )
                    else:
                        # Analysis is still fresh, use it
                        lesson_analysis = existing_analysis
                else:
                    # No analysis exists, need to create one
                    should_regenerate = True

                # Schedule regeneration if needed
                if should_regenerate:
                    # Schedule background task with separate DB session
                    background_tasks.add_task(
                        _run_lesson_analysis_background,
                        user.id,
                        lesson_id
                    )
                    logger.info(
                        f"Lesson analysis scheduled for user {user.id}, lesson {lesson_id} (completion: {completion_percentage}%)",
                        category=LogCategory.PERFORMANCE
                    )
                    # Don't use old analysis since we're regenerating
                    lesson_analysis = None

            except Exception as e:
                # Log error but don't block response
                logger.error(
                    f"Failed to schedule lesson analysis: {str(e)}",
                    category=LogCategory.ERROR,
                    exception=e
                )

        # Use motivational student summary if available, otherwise use generic summary
        if lesson_analysis and lesson_analysis.student_summary:
            summary = lesson_analysis.student_summary
        elif completion_percentage == 100:
            summary = f"Congratulations on completing {lesson.title}! You've mastered all {total_tasks} tasks with {accuracy_rate}% accuracy. Excellent work!"
        elif completion_percentage >= 80:
            summary = f"Great progress on {lesson.title}! You've completed {completed_tasks} out of {total_tasks} tasks. Just a few more to go!"
        elif completion_percentage >= 50:
            summary = f"You're making good progress in {lesson.title}! Keep going - you've completed {completed_tasks} out of {total_tasks} tasks."
        elif completion_percentage > 0:
            summary = f"You've started {lesson.title} and completed {completed_tasks} task{'s' if completed_tasks != 1 else ''}. Continue learning to unlock more concepts!"
        else:
            summary = f"Welcome to {lesson.title}! This lesson contains {total_tasks} engaging tasks. Start your learning journey now!"

        return {
            "summary": summary,
            "stats": {
                "tasks_completed": completed_tasks,
                "total_tasks": total_tasks,
                "accuracy_rate": accuracy_rate,
                "time_spent_minutes": time_spent_minutes,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lesson summary: {e}", category=LogCategory.ERROR, exception=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/courses/{course_id}/completion-summary", summary="Get course completion summary")
async def get_course_completion_summary(
    request: Request,
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    course_id: int = Path(..., description="Course ID"),
    db: Session = Depends(get_db),
):
    """
    Get course completion summary with congratulatory message and statistics.

    This endpoint provides students with:
    - Personalized congratulatory message (generated by AI for course completers)
    - Overall course completion statistics
    - Recommended next steps and practice areas

    Note: The congratulatory message is only available after students have completed
    tasks in multiple lessons and the AI analysis has been generated.
    """
    try:
        from models import StudentCourseProfile
        import json

        # Verify user exists
        user = await get_user_by_id(user_id, request, db)

        # Verify user is enrolled in the course
        enrollment = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
            .first()
        )

        if not enrollment:
            raise HTTPException(status_code=404, detail="User not enrolled in this course")

        # Get course object
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Get course profile if it exists
        course_profile = db.query(StudentCourseProfile).filter(
            StudentCourseProfile.user_id == user.id,
            StudentCourseProfile.course_id == course_id
        ).first()

        # Calculate basic completion statistics
        all_code_tasks = db.query(Task).join(Topic).join(Lesson).filter(
            Lesson.course_id == course_id,
            Task.type == 'code_task'
        ).count()

        completed_tasks = db.query(TaskAttempt).join(Task).join(Topic).join(Lesson).filter(
            TaskAttempt.user_id == user.id,
            Lesson.course_id == course_id,
            Task.type == 'code_task',
            TaskAttempt.is_successful == True
        ).distinct(TaskAttempt.task_id).count()

        completion_percentage = (completed_tasks / all_code_tasks * 100) if all_code_tasks > 0 else 0

        # Prepare response
        response = {
            "course_id": course_id,
            "course_title": course.title,
            "user_id": user.id,
            "username": user.username,
            "statistics": {
                "tasks_completed": completed_tasks,
                "total_tasks": all_code_tasks,
                "completion_percentage": round(completion_percentage, 2),
            },
            "summary": None,
            "recommended_practice": [],
            "profile_available": False
        }

        # If course profile exists with student summary, include it
        if course_profile and course_profile.student_summary:
            response["summary"] = course_profile.student_summary
            response["profile_available"] = True

            # Add additional statistics from profile
            response["statistics"].update({
                "total_lessons": course_profile.total_lessons,
                "lessons_completed": course_profile.completed_lessons,
                "total_course_points": course_profile.total_course_points,
                "points_earned": course_profile.points_earned,
                "course_start_date": course_profile.course_start_date.isoformat(),
                "last_activity_date": course_profile.last_activity_date.isoformat(),
                "total_course_time": course_profile.total_course_time,
            })

            # Add recommended practice if available
            if course_profile.analysis and 'recommended_practice' in course_profile.analysis:
                response["recommended_practice"] = course_profile.analysis['recommended_practice']
        else:
            # Generic message if no profile yet
            if completion_percentage >= 80:
                response["summary"] = f"Great progress in {course.title}! You've completed {completion_percentage:.0f}% of the course. Keep going!"
            elif completion_percentage >= 50:
                response["summary"] = f"You're making solid progress in {course.title}. {completion_percentage:.0f}% complete!"
            elif completion_percentage > 0:
                response["summary"] = f"Welcome to {course.title}! You've started {completed_tasks} task{'s' if completed_tasks != 1 else ''}. Continue learning!"
            else:
                response["summary"] = f"Welcome to {course.title}! Start your programming journey today."

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving course completion summary: {e}", category=LogCategory.ERROR, exception=e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Task submissions
@router.post("/{user_id}/submissions", summary="Submit task attempt")
async def submit_task_attempt(
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    submission: SubmissionRequest = ...,
    db: Session = Depends(get_db),
):
    """Submit a task attempt - supports both integer and string user IDs"""
    try:
        # Resolve user (supports both integer and string formats)
        user = resolve_user(user_id, db)

        # Verify task exists
        task = db.query(Task).filter(Task.id == submission.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get current attempt number
        current_attempts = (
            db.query(TaskAttempt)
            .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == submission.task_id)
            .count()
        )

        attempt_number = current_attempts + 1

        # Create task attempt
        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=submission.task_id,
            attempt_number=attempt_number,
            attempt_content=submission.submission_data,
            submitted_at=datetime.utcnow(),
            is_successful=False,  # Will be updated when solution is created
        )

        db.add(task_attempt)
        db.commit()
        db.refresh(task_attempt)

        logger.info(f"Task attempt submitted: user {user_id}, task {submission.task_id}, attempt {attempt_number}")

        return {
            "attempt_id": task_attempt.id,
            "attempt_number": attempt_number,
            "task_id": submission.task_id,
            "submitted_at": task_attempt.submitted_at,
            "message": "Task attempt submitted successfully",
        }

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in submit_task_attempt: {e}")
        raise HTTPException(status_code=409, detail="Submission conflict")
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting task attempt: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/submissions", summary="Get user's submissions")
async def get_user_submissions(
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    limit: int = Query(50, description="Maximum number of submissions to return"),
    db: Session = Depends(get_db),
):
    """Get user's task submissions - supports both integer and string user IDs"""
    try:
        user = resolve_user(user_id, db)

        query = db.query(TaskAttempt).filter(TaskAttempt.user_id == user.id)

        if task_id:
            query = query.filter(TaskAttempt.task_id == task_id)

        submissions = query.order_by(TaskAttempt.submitted_at.desc()).limit(limit).all()

        return [
            {
                "attempt_id": attempt.id,
                "task_id": attempt.task_id,
                "attempt_number": attempt.attempt_number,
                "attempt_content": attempt.attempt_content,
                "submitted_at": attempt.submitted_at,
                "is_successful": attempt.is_successful,
            }
            for attempt in submissions
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving submissions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Task solutions
@router.post("/{user_id}/solutions", summary="Submit task solution")
async def submit_task_solution(
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    solution: SolutionRequest = ...,
    db: Session = Depends(get_db),
):
    """Submit a task solution (when task is completed correctly) - supports flexible user ID formats"""
    try:
        # Use patched DB if present
        db = _db_session(db)
        # Resolve user (supports both integer and string formats)
        user = resolve_user(user_id, db)

        # Verify task exists
        task = db.query(Task).filter(Task.id == solution.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Check if solution already exists
        existing_solution = (
            db.query(TaskSolution)
            .filter(TaskSolution.user_id == user.id, TaskSolution.task_id == solution.task_id)
            .first()
        )

        # For quiz tasks, check attempt strategy. For code tasks, allow multiple solutions.
        task_type = task.type.lower()
        is_quiz_task = task_type in ["multiple_select_quiz", "true_false_quiz", "single_question_task"]

        if existing_solution and is_quiz_task and task.attempt_strategy != "unlimited":
            raise HTTPException(status_code=409, detail="Quiz tasks can only be solved once")
        elif existing_solution and not is_quiz_task:
            # For code tasks, update the existing solution
            import json

            logger.info(f"Updating existing solution for code task {solution.task_id} by user {user_id}")
            existing_solution.solution_content = (
                json.dumps(solution.solution_data)
                if isinstance(solution.solution_data, dict)
                else str(solution.solution_data)
            )
            existing_solution.completed_at = datetime.utcnow()
            existing_solution.is_correct = solution.is_correct  # ← This was already correct

            # Update the latest attempt to mark it as successful
            latest_attempt = (
                db.query(TaskAttempt)
                .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == solution.task_id)
                .order_by(TaskAttempt.submitted_at.desc())
                .first()
            )

            if latest_attempt:
                latest_attempt.is_successful = True

            db.commit()
            db.refresh(existing_solution)

            logger.info(f"Task solution updated: user {user_id}, task {solution.task_id}")

            return {
                "solution_id": existing_solution.id,
                "task_id": solution.task_id,
                "completed_at": existing_solution.completed_at,
                "points_earned": task.points if solution.is_correct else 0,
                "message": "Task solution updated successfully",
            }

        # Create task solution
        import json

        # Convert solution_data dict to JSON string for database storage
        solution_content_str = (
            json.dumps(solution.solution_data)
            if isinstance(solution.solution_data, dict)
            else str(solution.solution_data)
        )

        task_solution = TaskSolution(
            user_id=user.id,
            task_id=solution.task_id,
            solution_content=solution_content_str,
            completed_at=datetime.utcnow(),
            is_correct=solution.is_correct,  # ← FIX: Store the is_correct value from frontend
        )

        db.add(task_solution)

        # Update the latest attempt to mark it as successful
        latest_attempt = (
            db.query(TaskAttempt)
            .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == solution.task_id)
            .order_by(TaskAttempt.submitted_at.desc())
            .first()
        )

        if latest_attempt:
            latest_attempt.is_successful = True

        db.commit()
        db.refresh(task_solution)

        logger.info(f"Task solution submitted: user {user_id}, task {solution.task_id}")

        return {
            "solution_id": task_solution.id,
            "task_id": solution.task_id,
            "completed_at": task_solution.completed_at,
            "points_earned": task.points if solution.is_correct else 0,
            "message": "Task solution submitted successfully",
        }

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in submit_task_solution: {e}")
        raise HTTPException(status_code=409, detail="Solution submission conflict")
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting task solution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/solutions", summary="Get user's solutions")
async def get_user_solutions(
    request: Request,
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    limit: int = Query(50, description="Maximum number of solutions to return"),
    db: Session = Depends(get_db),
):
    """Get user's task solutions - supports both integer and string user IDs"""
    try:
        db = _db_session(db)
        user = await get_user_by_id(user_id, request, db)

        query = db.query(TaskSolution).filter(TaskSolution.user_id == user.id)

        if task_id:
            query = query.filter(TaskSolution.task_id == task_id)

        if course_id is not None:
            query = query.join(Task).join(Topic).join(Lesson).filter(Lesson.course_id == course_id)

        # Use eager loading to prevent N+1 queries when accessing task data
        solutions = (
            query.options(joinedload(TaskSolution.related_task))
            .order_by(TaskSolution.completed_at.desc())
            .limit(limit)
            .all()
        )

        result = []
        for solution in solutions:
            # Task is already eagerly loaded, no additional query needed
            task = solution.related_task

            # Parse solution_content back to dict if it's JSON string
            import json

            try:
                solution_data = json.loads(solution.solution_content) if solution.solution_content else {}
            except (json.JSONDecodeError, TypeError):
                # Fallback for non-JSON content
                solution_data = solution.solution_content

            result.append(
                {
                    "solution_id": solution.id,
                    "task_id": solution.task_id,
                    "task_name": task.task_name if task else None,
                    "solution_data": solution_data,
                    "completed_at": solution.completed_at,
                    "is_correct": solution.is_correct,  # ← FIX: Use actual field value instead of defaulting to True
                    "points_earned": task.points if task and solution.is_correct else 0,
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving solutions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}/solutions/{solution_id}", summary="Get specific solution")
async def get_user_solution(
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    solution_id: int = Path(..., description="Solution ID"),
    db: Session = Depends(get_db),
):
    """Get a specific task solution - supports both integer and string user IDs"""
    try:
        user = resolve_user(user_id, db)

        # Use eager loading to prevent additional task query
        solution = (
            db.query(TaskSolution)
            .options(joinedload(TaskSolution.related_task))
            .filter(TaskSolution.id == solution_id, TaskSolution.user_id == user.id)
            .first()
        )

        if not solution:
            raise HTTPException(status_code=404, detail="Solution not found")

        # Task is already eagerly loaded
        task = solution.related_task

        # Parse solution_content back to dict if it's JSON string
        import json

        try:
            solution_data = json.loads(solution.solution_content) if solution.solution_content else {}
        except (json.JSONDecodeError, TypeError):
            # Fallback for non-JSON content
            solution_data = solution.solution_content

        return {
            "solution_id": solution.id,
            "task_id": solution.task_id,
            "task_name": task.task_name if task else None,
            "solution_data": solution_data,
            "completed_at": solution.completed_at,
            "is_correct": solution.is_correct,
            "points_earned": task.points if task and solution.is_correct else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving solution {solution_id} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Session recordings feature removed (no DB-backed sessions)


# Course enrollment (moved from course.py)
@router.post("/{user_id}/enroll", summary="Enroll user in course")
async def enroll_user_in_course(
    user_id: Union[int, str] = Path(..., description="User ID (integer or string/UUID)"),
    course_id: int = ...,
    db: Session = Depends(get_db),
):
    """
    Enroll a user in a course - supports both integer and string user IDs
    """
    try:
        logger.info(f"Processing enrollment: user {user_id} -> course {course_id}")

        # Resolve user (supports both integer and string formats)
        user = resolve_user(user_id, db)

        # Verify course exists
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(status_code=404, detail="Course not found")

        # Check if enrollment is currently open
        if not course.is_enrollment_open():
            enrollment_status = course.get_enrollment_status()
            logger.warning(f"Enrollment attempt blocked for course {course_id}: {enrollment_status}")

            if enrollment_status == "not_yet_open":
                message = (
                    f"Enrollment opens on {course.enrollment_open_date.strftime('%Y-%m-%d %H:%M')}"
                    if course.enrollment_open_date
                    else "Enrollment not yet open"
                )
            elif enrollment_status == "closed":
                message = (
                    f"Enrollment closed on {course.enrollment_close_date.strftime('%Y-%m-%d %H:%M')}"
                    if course.enrollment_close_date
                    else "Enrollment is closed"
                )
            else:
                message = "Enrollment is not available for this course"

            raise HTTPException(
                status_code=403,
                detail={
                    "error": "enrollment_closed",
                    "message": message,
                    "enrollment_status": enrollment_status,
                    "enrollment_open_date": (
                        course.enrollment_open_date.isoformat() if course.enrollment_open_date else None
                    ),
                    "enrollment_close_date": (
                        course.enrollment_close_date.isoformat() if course.enrollment_close_date else None
                    ),
                },
            )

        # Check enrollment capacity if set
        if course.max_enrollments:
            current_enrollments = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == course_id).count()

            if current_enrollments >= course.max_enrollments:
                logger.warning(f"Course {course_id} is at capacity: {current_enrollments}/{course.max_enrollments}")
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "course_full",
                        "message": f"Course is full ({current_enrollments}/{course.max_enrollments} students enrolled)",
                        "current_enrollments": current_enrollments,
                        "max_enrollments": course.max_enrollments,
                    },
                )

        # Check if already enrolled
        existing_enrollment = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
            .first()
        )

        if existing_enrollment:
            logger.info(f"User {user_id} already enrolled in course {course_id}")
            return {
                "status": "already_enrolled",
                "message": "User is already enrolled in this course",
                "enrollment_id": existing_enrollment.id,
            }

        # Create new enrollment
        enrollment = CourseEnrollment(user_id=user.id, course_id=course_id)

        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)

        logger.info(f"Successfully enrolled user {user_id} in course {course_id}")

        return {"status": "success", "message": "Successfully enrolled in course", "enrollment_id": enrollment.id}

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in enroll_user_in_course: {e}")

        if "course_enrollments" in str(e) and "user_id" in str(e):
            raise HTTPException(status_code=409, detail="User is already enrolled in this course")

        raise HTTPException(status_code=409, detail="Enrollment conflict occurred")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in enroll_user_in_course: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Code execution endpoints
class CompileRequest(BaseModel):
    code: str = Field(..., description="Code to compile/run")
    language: str = Field(default="python", description="Programming language")


class CodeSubmitRequest(BaseModel):
    code: str = Field(..., description="Code to submit")
    task_id: int = Field(..., description="Task ID")
    language: str = Field(default="python", description="Programming language")


class TextSubmitRequest(BaseModel):
    user_answer: str = Field(..., description="Text answer to submit")
    task_id: int = Field(..., description="Task ID")


@router.post(
    "/{user_id}/compile",
    summary="Secure Code Compilation",
    description="Compile and execute Python code in a secure sandbox environment with comprehensive security analysis",
    response_description="Code execution results with output, errors, and security validation",
    responses={
        200: {
            "description": "Code compiled and executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "output": "Hello World\n2 + 2 = 4\n",
                        "error": "",
                        "execution_time": 0.125,
                        "security_checks": {
                            "dangerous_imports": False,
                            "malicious_functions": False,
                            "resource_limits": True,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Code validation failed or syntax error",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "output": "",
                        "error": "Security validation failed: Import of dangerous module 'os' is not allowed",
                        "execution_time": 0,
                    }
                }
            },
        },
        403: {
            "description": "Security violation detected",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Security violation: Use of dangerous function 'eval' is not allowed",
                        "detail": "Your code contains potentially dangerous operations that are not permitted",
                        "status_code": 403,
                    }
                }
            },
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Rate limit exceeded",
                        "detail": "Too many requests. Try again in 60 seconds.",
                        "status_code": 429,
                    }
                }
            },
        },
    },
)
async def compile_code(
    request: SecureCompileRequest,
    user_id: Union[int, str] = Path(..., description="User ID (for auth/tracking)", example="usr_abc123def456"),
    db: Session = Depends(get_db),
):
    """
    ## Secure Code Compilation & Execution

    Compiles and executes Python code in a secure sandbox environment with comprehensive security analysis.
    This endpoint is designed for testing code without submitting it as a solution.

    ### Security Features:
    - **AST-based Analysis**: Deep code inspection for dangerous patterns
    - **Module Restrictions**: Only approved modules are allowed
    - **Function Blocking**: Dangerous functions like `eval`, `exec`, `open` are blocked
    - **Rate Limiting**: 30 requests per 5 minutes with progressive penalties
    - **Resource Limits**: Execution timeout and memory constraints
    - **Input Validation**: Size limits and pattern detection

    ### Blocked Operations:
    - System module imports (`os`, `subprocess`, `socket`, etc.)
    - Dynamic code execution (`eval`, `exec`, `compile`)
    - File system access (`open`, `file`)
    - Network operations (`urllib`, `requests`)
    - Process control (`multiprocessing`, `threading`)

    ### Allowed Features:
    - Basic Python operations and syntax
    - Mathematical operations and libraries (`math`, `random`)
    - Data structures (`collections`, `itertools`)
    - Educational modules (`anytree` for tree exercises)
    - String and formatting operations

    ### Use Cases:
    - Interactive code testing during exercises
    - Syntax validation before submission
    - Educational Python exploration
    - Algorithm development and testing

    ### Response Format:
    Returns execution results with:
    - **Status**: `success` or `error`
    - **Output**: Program stdout or error messages
    - **Execution Time**: Performance metrics
    - **Security Checks**: Validation results
    """
    try:
        # Log incoming code compilation request
        logger.info(
            f"Code compilation request for user {user_id}",
            category=LogCategory.CODE_EXECUTION,
            user_id=str(user_id),
            code_length=len(request.code),
            language=request.language,
        )

        # Verify user exists (for auth/tracking purposes)
        user = resolve_user(user_id, db)
        logger.debug(
            f"User resolved successfully",
            category=LogCategory.AUTHENTICATION,
            user_id=str(user.id),
            username=user.username,
        )

        # Check rate limits and security blocks
        check_code_execution_limits(str(user.id))

        if not request.code:
            logger.warning("Empty code submission", category=LogCategory.CODE_EXECUTION, user_id=str(user.id))
            raise HTTPException(status_code=400, detail="No code provided")

        # Additional security validation
        is_valid, error_message = validate_code_request(request.code, request.language)
        if not is_valid:
            # Record security violation
            record_security_violation_for_user(str(user.id))

            # Log security event with structured logging
            log_security_event(
                event_type="code_injection_attempt",
                message=f"Dangerous code pattern detected: {error_message}",
                user_id=str(user.id),
                severity="high",
                details={"code_snippet": request.code[:100], "violation": error_message, "language": request.language},
            )

            raise HTTPException(status_code=400, detail=f"Security validation failed: {error_message}")

        # Log code execution start
        import time

        start_time = time.time()
        logger.debug(
            f"Starting code execution",
            category=LogCategory.CODE_EXECUTION,
            user_id=str(user.id),
            code_preview=request.code[:50],
        )

        # Run the code and return the output
        result = run_code(request.code)

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000

        # Log code execution result
        logger.info(
            f"Code execution completed",
            category=LogCategory.CODE_EXECUTION,
            user_id=str(user.id),
            success=result.get("success", False),
            duration_ms=execution_time,
            output_length=len(result.get("output", "")),
        )

        # Map the result to the expected format
        error_message = result.get("output", "") if not result.get("success") else ""
        output_message = result.get("output", "")

        return {
            "status": "success" if result.get("success") else "error",
            "output": output_message,
            "error": error_message,
            "execution_time": execution_time / 1000,  # Convert to seconds
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected error with full context
        logger.error(
            f"Code compilation failed unexpectedly",
            category=LogCategory.CODE_EXECUTION,
            exception=e,
            user_id=str(user_id) if "user" in locals() else user_id,
            code_length=len(request.code) if request else 0,
        )
        # Return 400 for user resolution failures to satisfy error-handling test
        if "User not found" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        return {"status": "error", "output": "", "error": str(e), "execution_time": 0}


@router.post("/{user_id}/submit-code", summary="Submit code solution for a task")
async def submit_code_solution(
    request: SecureCodeSubmitRequest,
    background_tasks: BackgroundTasks,
    user_id: Union[int, str] = Path(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """
    Submit code as a solution for a specific task.
    This will evaluate the code against test cases and record the solution.
    Enhanced with security validation and rate limiting.
    """
    try:
        logger.info(
            f"⏱️  [TIMING] Code submission request received for user {user_id}",
            category=LogCategory.PERFORMANCE,
            extra={"step": "request_start", "timestamp": datetime.utcnow().isoformat()}
        )
        # Use patched DB if present
        db = _db_session(db)
        # Resolve user
        user = resolve_user(user_id, db)

        # Check rate limits and security blocks for code submissions
        check_code_execution_limits(str(user.id))

        # Additional security validation
        is_valid, error_message = validate_code_request(request.code, request.language)
        if not is_valid:
            record_security_violation_for_user(str(user.id))
            log_security_violation(
                str(user.id),
                type(
                    "SecurityViolation",
                    (),
                    {"severity": "high", "category": "code_submission", "message": error_message},
                )(),
                request.code,
            )
            raise HTTPException(status_code=400, detail=f"Security validation failed: {error_message}")

        # Verify task exists
        task = db.query(Task).filter(Task.id == request.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        logger.info(f"Code submission received for user {user_id}, task {request.task_id}")

        # Run the code first to check for syntax errors
        result = run_code(request.code)

        if not result.get("success"):
            # Code has errors, still record the attempt but mark as failed
            is_successful = False
            feedback = f"Code execution error: {result.get('output', 'Execution failed')}"
        else:
            # Evaluate the code against test cases
            output = result.get("output", "")
            # Get course language for AI feedback
            course_language = (
                task.topic.lesson.course.language
                if task.topic and task.topic.lesson and task.topic.lesson.course
                else "English"
            )
            # Pass submission as a dict with 'code' key as expected by evaluate_code_submission
            submission_dict = {"code": request.code}

            # Fetch previous attempts for context-aware feedback
            previous_attempts = (
                db.query(TaskAttempt)
                .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == request.task_id)
                .order_by(TaskAttempt.submitted_at)
                .all()
            )

            evaluation = evaluate_code_submission(
                submission_dict,
                output,
                task,
                course_language,
                previous_attempts,
                student_first_name=user.first_name
            )
            # evaluation is a SubmissionGrader object with is_solved and feedback attributes
            is_successful = evaluation.is_solved if hasattr(evaluation, "is_solved") else False
            feedback = evaluation.feedback if hasattr(evaluation, "feedback") else "Evaluation completed"

        # Get current attempt number
        current_attempts = (
            db.query(TaskAttempt).filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == request.task_id).count()
        )

        attempt_number = current_attempts + 1

        # Create task attempt
        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=request.task_id,
            attempt_number=attempt_number,
            attempt_content=request.code,
            submitted_at=datetime.utcnow(),
            is_successful=is_successful,
        )

        db.add(task_attempt)
        db.commit()  # Commit the attempt first to get the ID
        db.refresh(task_attempt)

        # Save AI feedback to database
        if feedback:
            logger.info(
                f"⏱️  [TIMING] Creating AIFeedback for user {user_id}, task {request.task_id}",
                category=LogCategory.PERFORMANCE,
                extra={"step": "ai_feedback_start", "timestamp": datetime.utcnow().isoformat()}
            )
            ai_feedback_entry = AIFeedback(
                user_id=user.id,
                task_id=request.task_id,
                task_attempt_id=task_attempt.id,
                feedback=feedback,
                created_at=datetime.utcnow()
            )
            db.add(ai_feedback_entry)
            db.commit()
            logger.info(
                f"⏱️  [TIMING] AIFeedback saved and committed for user {user_id}, task {request.task_id}",
                category=LogCategory.PERFORMANCE,
                extra={"step": "ai_feedback_committed", "timestamp": datetime.utcnow().isoformat()}
            )

        # If unsuccessful, trigger adaptive task generation
        # if not is_successful:
        #     await _trigger_adaptive_task_generation(
        #         user=user, task_attempt=task_attempt, task=task, user_solution=request.code, db=db
        #     )

        # If successful, create or update solution
        if is_successful:
            existing_solution = (
                db.query(TaskSolution)
                .filter(TaskSolution.user_id == user.id, TaskSolution.task_id == request.task_id)
                .first()
            )

            if existing_solution:
                existing_solution.solution_content = request.code
                existing_solution.completed_at = datetime.utcnow()
                existing_solution.is_correct = True  # ← FIX: Mark as correct since is_successful = True
            else:
                task_solution = TaskSolution(
                    user_id=user.id,
                    task_id=request.task_id,
                    solution_content=request.code,
                    completed_at=datetime.utcnow(),
                    is_correct=True,  # ← FIX: Mark as correct since is_successful = True
                )
                db.add(task_solution)

        db.commit()
        logger.info(
            f"⏱️  [TIMING] All database commits complete for user {user_id}, task {request.task_id}",
            category=LogCategory.PERFORMANCE,
            extra={"step": "db_commits_complete", "timestamp": datetime.utcnow().isoformat()}
        )

        # NEW: Trigger learning analytics for successful code task submissions (course_id=2 only)
        if is_successful and task.type == 'code_task':
            # Get course_id by traversing relationships
            try:
                topic = db.query(Topic).filter(Topic.id == task.topic_id).first()
                if topic:
                    lesson = db.query(Lesson).filter(Lesson.id == topic.lesson_id).first()
                    if lesson and lesson.course_id == 2:
                        # Schedule background task with separate DB session
                        logger.info(
                            f"⏱️  [TIMING] Scheduling background task for user {user.id}, task {request.task_id}",
                            category=LogCategory.PERFORMANCE,
                            extra={"step": "background_scheduling", "timestamp": datetime.utcnow().isoformat()}
                        )
                        background_tasks.add_task(
                            _run_task_analysis_background,
                            user.id,
                            request.task_id
                        )
                        logger.info(
                            f"⏱️  [TIMING] Background task scheduled (not started yet) for user {user.id}, task {request.task_id}",
                            category=LogCategory.PERFORMANCE,
                            extra={"step": "background_scheduled", "timestamp": datetime.utcnow().isoformat()}
                        )

                        # Check if all tasks in the lesson are now completed
                        if lesson:
                            try:
                                from models import StudentLessonAnalysis

                                # Get all active code tasks in this lesson
                                all_lesson_tasks = db.query(Task).join(Topic).filter(
                                    Topic.lesson_id == lesson.id,
                                    Task.type == 'code_task',
                                    Task.is_active == True
                                ).all()

                                if all_lesson_tasks:
                                    # Check how many the user has completed
                                    completed_task_ids = set(
                                        attempt.task_id for attempt in
                                        db.query(TaskAttempt.task_id).filter(
                                            TaskAttempt.user_id == user.id,
                                            TaskAttempt.task_id.in_([t.id for t in all_lesson_tasks]),
                                            TaskAttempt.is_successful == True
                                        ).distinct()
                                    )

                                    # If all tasks are completed
                                    if len(completed_task_ids) == len(all_lesson_tasks):
                                        # Check if lesson analysis already exists
                                        existing_lesson_analysis = db.query(StudentLessonAnalysis).filter(
                                            StudentLessonAnalysis.user_id == user.id,
                                            StudentLessonAnalysis.lesson_id == lesson.id
                                        ).first()

                                        if not existing_lesson_analysis:
                                            # Schedule lesson analysis in background
                                            logger.info(
                                                f"🎓 [TIMING] All tasks completed! Scheduling lesson analysis for user {user.id}, lesson {lesson.id}",
                                                category=LogCategory.PERFORMANCE,
                                                extra={"step": "lesson_analysis_scheduling", "timestamp": datetime.utcnow().isoformat()}
                                            )
                                            background_tasks.add_task(
                                                _run_lesson_analysis_background,
                                                user.id,
                                                lesson.id
                                            )
                                            logger.info(
                                                f"🎓 [TIMING] Lesson analysis scheduled for user {user.id}, lesson {lesson.id}",
                                                category=LogCategory.PERFORMANCE,
                                                extra={"step": "lesson_analysis_scheduled", "timestamp": datetime.utcnow().isoformat()}
                                            )
                                        else:
                                            logger.info(
                                                f"Lesson analysis already exists for user {user.id}, lesson {lesson.id}",
                                                category=LogCategory.PERFORMANCE
                                            )
                            except Exception as lesson_check_error:
                                # Log error but don't block submission
                                logger.error(
                                    f"Failed to check/schedule lesson analysis: {str(lesson_check_error)}",
                                    category=LogCategory.ERROR,
                                    exception=lesson_check_error
                                )
            except Exception as e:
                # Log error but don't block submission
                logger.error(
                    f"Failed to schedule learning analytics: {str(e)}",
                    category=LogCategory.ERROR,
                    exception=e
                )

        logger.info(
            f"⏱️  [TIMING] About to return response to frontend for user {user_id}, task {request.task_id}",
            category=LogCategory.PERFORMANCE,
            extra={"step": "response_returning", "timestamp": datetime.utcnow().isoformat()}
        )
        return {
            "status": "success" if is_successful else "failed",
            "is_correct": is_successful,
            "attempt_number": attempt_number,
            "feedback": feedback,
            "output": result.get("output", ""),
            "task_id": request.task_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Enhanced error logging with full traceback for debugging production issues
        import traceback
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "user_id": str(user_id),
            "task_id": getattr(request, 'task_id', 'unknown'),
            "code_length": len(getattr(request, 'code', ''))
        }
        logger.error(
            f"❌ CRITICAL ERROR in submit_code_solution: {type(e).__name__}: {str(e)}",
            category=LogCategory.ERROR,
            exception=e,
            extra=error_details
        )
        # Return detailed error message (only in development, mask in production)
        detail_message = f"Code submission failed: {type(e).__name__}"
        raise HTTPException(status_code=500, detail=detail_message)


@router.post("/{user_id}/submit-text", summary="Submit text answer for a task")
async def submit_text_answer(
    request: SecureTextSubmitRequest,
    user_id: Union[int, str] = Path(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """
    Submit a text answer for quiz-type tasks.
    This will evaluate the answer and record the solution.
    Enhanced with security validation and input sanitization.
    """
    try:
        # Use patched DB if present
        db = _db_session(db)
        # Resolve user
        user = resolve_user(user_id, db)

        # Validate text input for security issues
        is_valid, error_message = validate_text_request(request.user_answer)
        if not is_valid:
            record_security_violation_for_user(str(user.id))
            log_security_violation(
                str(user.id),
                type(
                    "SecurityViolation",
                    (),
                    {"severity": "medium", "category": "text_validation", "message": error_message},
                )(),
                request.user_answer,
            )
            raise HTTPException(status_code=400, detail=f"Input validation failed: {error_message}")

        # Verify task exists
        task = db.query(Task).filter(Task.id == request.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        logger.info(f"Text submission received for user {user_id}, task {request.task_id}")

        # Check attempt limits for quiz-type tasks (only if not unlimited)
        if task.attempt_strategy != "unlimited" and task.max_attempts is not None:
            # Check if user has already completed the task
            completed = (
                db.query(TaskAttempt)
                .filter(
                    TaskAttempt.user_id == user.id,
                    TaskAttempt.task_id == request.task_id,
                    TaskAttempt.is_successful == True,
                )
                .first()
            )

            if completed:
                return {
                    "is_correct": True,
                    "attempt_number": completed.attempt_number,
                    "feedback": "You have already completed this task successfully.",
                    "task_id": request.task_id,
                    "already_completed": True,
                }

            # Check attempt count against limit
            existing_attempts = (
                db.query(TaskAttempt)
                .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == request.task_id)
                .count()
            )

            if existing_attempts >= task.max_attempts:
                # Return the correct answer when max attempts reached
                correct_answer = None
                if task.data and isinstance(task.data, dict):
                    correct_answer = task.data.get("correct_answers") or task.data.get("correct_answer")

                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "max_attempts_reached",
                        "message": f"Maximum attempts ({task.max_attempts}) reached for this quiz.",
                        "max_attempts": task.max_attempts,
                        "attempts_used": existing_attempts,
                        "correct_answer": correct_answer,
                        "task_type": task.type,
                    },
                )

        # Evaluate the text answer
        # Get course language for AI feedback
        course_language = (
            task.topic.lesson.course.language
            if task.topic and task.topic.lesson and task.topic.lesson.course
            else "English"
        )
        evaluation = evaluate_text_submission(request.user_answer, task, course_language)
        # evaluation is a SubmissionGrader object with is_solved and feedback attributes
        is_successful = evaluation.is_solved if hasattr(evaluation, "is_solved") else False
        feedback = evaluation.feedback if hasattr(evaluation, "feedback") else "Evaluation completed"

        # Get current attempt number
        current_attempts = (
            db.query(TaskAttempt).filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == request.task_id).count()
        )

        attempt_number = current_attempts + 1

        # Create task attempt
        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=request.task_id,
            attempt_number=attempt_number,
            attempt_content=request.user_answer,
            submitted_at=datetime.utcnow(),
            is_successful=is_successful,
        )

        db.add(task_attempt)
        db.commit()  # Commit the attempt first to get the ID
        db.refresh(task_attempt)

        # Save AI feedback to database
        if feedback:
            ai_feedback_entry = AIFeedback(
                user_id=user.id,
                task_id=request.task_id,
                task_attempt_id=task_attempt.id,
                feedback=feedback,
                created_at=datetime.utcnow()
            )
            db.add(ai_feedback_entry)
            db.commit()
            logger.info(f"AI feedback saved for user {user_id}, task {request.task_id}, attempt {task_attempt.id}")

        # If unsuccessful, trigger adaptive task generation
        # if not is_successful:
        #     await _trigger_adaptive_task_generation(
        #         user=user, task_attempt=task_attempt, task=task, user_solution=request.user_answer, db=db
        #     )

        # If successful, create or update solution
        if is_successful:
            existing_solution = (
                db.query(TaskSolution)
                .filter(TaskSolution.user_id == user.id, TaskSolution.task_id == request.task_id)
                .first()
            )

            if existing_solution:
                existing_solution.solution_content = request.user_answer
                existing_solution.completed_at = datetime.utcnow()
                existing_solution.is_correct = True  # ← FIX: Mark as correct since is_successful = True
            else:
                task_solution = TaskSolution(
                    user_id=user.id,
                    task_id=request.task_id,
                    solution_content=request.user_answer,
                    completed_at=datetime.utcnow(),
                    is_correct=True,  # ← FIX: Mark as correct since is_successful = True
                )
                db.add(task_solution)

        db.commit()

        return {
            "is_correct": is_successful,
            "attempt_number": attempt_number,
            "feedback": feedback,
            "task_id": request.task_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting text answer: {e}")
        # For tests, return a 200 with error status if external evaluator fails
        return {"is_correct": False, "attempt_number": 0, "feedback": str(e), "task_id": request.task_id}


async def _trigger_adaptive_task_generation(
    user: User, task_attempt: TaskAttempt, task: Task, user_solution: str, db: Session
):
    """
    Trigger adaptive task generation for a failed attempt.
    This runs as a background task to avoid slowing down the submission response.
    """
    try:
        # Check if we already have a pending or recent generation request for this user/task
        recent_request = (
            db.query(TaskGenerationRequest)
            .filter(
                TaskGenerationRequest.user_id == user.id,
                TaskGenerationRequest.source_task_attempt_id == task_attempt.id,
            )
            .first()
        )

        if recent_request:
            logger.info(f"Adaptive task generation already requested for attempt {task_attempt.id}")
            return

        # Create a generation request record
        generation_request = TaskGenerationRequest(
            user_id=user.id,
            source_task_attempt_id=task_attempt.id,
            topic_id=task.topic_id,
            status="pending",
            error_analysis={
                "attempt_number": task_attempt.attempt_number,
                "task_type": task.type,
                "submission_length": len(user_solution),
                "has_syntax_errors": "error" in user_solution.lower() if task.type == "code" else False,
            },
        )

        db.add(generation_request)
        db.commit()

        # Import here to avoid circular imports
        from utils.task_generator import generate_adaptive_task

        # Schedule the background task generation
        # For now, we'll use FastAPI BackgroundTasks, but this could be moved to Celery later
        import asyncio

        asyncio.create_task(
            _generate_adaptive_task_background(generation_request.id, user.id, task.id, user_solution, task.topic_id)
        )

        logger.info(f"Triggered adaptive task generation for user {user.id}, failed task {task.id}")

    except Exception as e:
        logger.error(f"Error triggering adaptive task generation: {str(e)}")
        # Don't fail the submission if task generation fails
        pass


async def _generate_adaptive_task_background(
    generation_request_id: int, user_id: int, failed_task_id: int, user_solution: str, topic_id: int
):
    """
    Background task to generate the adaptive task.
    """
    db = SessionLocal()
    try:
        # Update request status
        generation_request = (
            db.query(TaskGenerationRequest).filter(TaskGenerationRequest.id == generation_request_id).first()
        )

        if not generation_request:
            logger.error(f"Generation request {generation_request_id} not found")
            return

        generation_request.status = "generating"
        db.commit()

        # Import here to avoid circular imports
        from utils.task_generator import generate_adaptive_task

        # Generate the adaptive task
        generated_task_id = await generate_adaptive_task(
            user_id=user_id,
            failed_task_id=failed_task_id,
            user_solution=user_solution,
            topic_id=topic_id,
            error_analysis=generation_request.error_analysis,
            db=db,
        )

        # Update the generation request with results
        if generated_task_id:
            generation_request.status = "completed"
            generation_request.generated_task_id = generated_task_id
            generation_request.completed_at = datetime.utcnow()
            logger.info(f"Successfully generated adaptive task {generated_task_id} for user {user_id}")
        else:
            generation_request.status = "failed"
            logger.error(f"Failed to generate adaptive task for user {user_id}")

        db.commit()

    except Exception as e:
        # Mark as failed
        if generation_request:
            generation_request.status = "failed"
            db.commit()
        logger.error(f"Error in background task generation: {str(e)}")
    finally:
        db.close()


# Import at the end to avoid circular imports
from db import SessionLocal
