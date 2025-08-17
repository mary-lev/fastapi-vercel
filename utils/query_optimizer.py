"""
Database Query Optimization Utilities
Provides optimized query patterns to prevent N+1 queries and improve performance
"""

from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session, joinedload, selectinload, subqueryload
from sqlalchemy import and_, or_, func, text
from models import Course, Lesson, Topic, Task, User, TaskAttempt, TaskSolution, AIFeedback, CourseEnrollment
from utils.query_monitor import monitor_query_performance, query_performance_context

# ============================================================================
# OPTIMIZED COURSE QUERIES
# ============================================================================


@monitor_query_performance(threshold_ms=500)
def get_course_with_full_hierarchy(db: Session, course_id: int) -> Optional[Course]:
    """
    Get course with complete lesson/topic/task hierarchy in a single query
    Prevents N+1 queries by using appropriate loading strategies
    """
    with query_performance_context("get_course_with_full_hierarchy"):
        return (
            db.query(Course)
            .options(
                # Use joinedload for smaller collections (lessons per course)
                joinedload(Course.lessons)
                .joinedload(Lesson.topics)
                .joinedload(Topic.tasks)
            )
            .filter(Course.id == course_id)
            .first()
        )


@monitor_query_performance(threshold_ms=300)
def get_courses_with_basic_info(db: Session, limit: Optional[int] = None) -> List[Course]:
    """
    Get all courses with basic information only (no heavy relationships)
    Optimized for course listing pages
    """
    with query_performance_context("get_courses_with_basic_info"):
        query = db.query(Course).order_by(Course.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()


@monitor_query_performance(threshold_ms=800)
def get_course_with_lesson_summaries(db: Session, course_id: int) -> Optional[Dict[str, Any]]:
    """
    Get course with lesson summaries (optimized for course overview)
    Uses subqueries to avoid loading full task details
    """
    with query_performance_context("get_course_with_lesson_summaries"):
        # Get course with lesson counts in a single query
        result = (
            db.query(
                Course.id,
                Course.title,
                Course.description,
                Course.created_at,
                func.count(Lesson.id).label("lesson_count"),
            )
            .outerjoin(Lesson)
            .filter(Course.id == course_id)
            .group_by(Course.id, Course.title, Course.description, Course.created_at)
            .first()
        )

        if not result:
            return None

        # Get lesson summaries with task counts
        lessons = (
            db.query(
                Lesson.id,
                Lesson.title,
                Lesson.lesson_order,
                func.count(Task.id).label("task_count"),
                func.sum(Task.points).label("total_points"),
            )
            .outerjoin(Topic)
            .outerjoin(Task)
            .filter(Lesson.course_id == course_id)
            .group_by(Lesson.id, Lesson.title, Lesson.lesson_order)
            .order_by(Lesson.lesson_order)
            .all()
        )

        return {
            "id": result.id,
            "title": result.title,
            "description": result.description,
            "created_at": result.created_at,
            "lesson_count": result.lesson_count,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "lesson_order": lesson.lesson_order,
                    "task_count": lesson.task_count or 0,
                    "total_points": lesson.total_points or 0,
                }
                for lesson in lessons
            ],
        }


# ============================================================================
# OPTIMIZED USER PROGRESS QUERIES
# ============================================================================


@monitor_query_performance(threshold_ms=600)
def get_user_course_progress_optimized(db: Session, user_id: Union[int, str], course_id: int) -> Dict[str, Any]:
    """
    Get comprehensive user progress for a course using optimized queries
    Avoids N+1 queries by using batch operations
    """
    with query_performance_context("get_user_course_progress_optimized"):
        # Get all tasks for the course in one query
        tasks_query = (
            db.query(
                Task.id,
                Task.task_name,
                Task.points,
                Topic.id.label("topic_id"),
                Topic.title.label("topic_title"),
                Lesson.id.label("lesson_id"),
                Lesson.title.label("lesson_title"),
            )
            .join(Topic)
            .join(Lesson)
            .filter(Lesson.course_id == course_id)
            .order_by(Lesson.lesson_order, Topic.topic_order, Task.order)
        )

        tasks = tasks_query.all()
        task_ids = [task.id for task in tasks]

        if not task_ids:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "total_points": 0,
                "earned_points": 0,
                "progress_percentage": 0,
                "lessons": [],
            }

        # Get user solutions for all tasks in one query
        solutions = (
            db.query(TaskSolution.task_id, TaskSolution.is_correct)
            .filter(TaskSolution.user_id == user_id, TaskSolution.task_id.in_(task_ids))
            .all()
        )

        # Create solution lookup
        solution_map = {sol.task_id: sol.is_correct for sol in solutions}

        # Calculate progress
        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if solution_map.get(task.id, False))
        total_points = sum(task.points for task in tasks)
        earned_points = sum(task.points for task in tasks if solution_map.get(task.id, False))

        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Group by lessons
        lessons_dict = {}
        for task in tasks:
            lesson_id = task.lesson_id
            if lesson_id not in lessons_dict:
                lessons_dict[lesson_id] = {
                    "id": lesson_id,
                    "title": task.lesson_title,
                    "tasks": [],
                    "completed_tasks": 0,
                    "total_tasks": 0,
                    "earned_points": 0,
                    "total_points": 0,
                }

            lesson = lessons_dict[lesson_id]
            is_completed = solution_map.get(task.id, False)

            lesson["tasks"].append(
                {
                    "id": task.id,
                    "title": task.task_name,
                    "points": task.points,
                    "topic_id": task.topic_id,
                    "topic_title": task.topic_title,
                    "completed": is_completed,
                }
            )

            lesson["total_tasks"] += 1
            lesson["total_points"] += task.points

            if is_completed:
                lesson["completed_tasks"] += 1
                lesson["earned_points"] += task.points

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "total_points": total_points,
            "earned_points": earned_points,
            "progress_percentage": round(progress_percentage, 2),
            "lessons": list(lessons_dict.values()),
        }


@monitor_query_performance(threshold_ms=400)
def get_user_solutions_batch(db: Session, user_id: Union[int, str], task_ids: List[int]) -> Dict[int, TaskSolution]:
    """
    Get user solutions for multiple tasks in a single query
    Returns a dictionary mapping task_id -> solution
    """
    with query_performance_context("get_user_solutions_batch"):
        solutions = (
            db.query(TaskSolution).filter(TaskSolution.user_id == user_id, TaskSolution.task_id.in_(task_ids)).all()
        )

        return {sol.task_id: sol for sol in solutions}


# ============================================================================
# OPTIMIZED ANALYTICS QUERIES
# ============================================================================


@monitor_query_performance(threshold_ms=1000)
def get_course_analytics_optimized(db: Session, course_id: int) -> Dict[str, Any]:
    """
    Get comprehensive course analytics using efficient aggregation queries
    """
    with query_performance_context("get_course_analytics_optimized"):
        # Get basic course stats
        course_stats = (
            db.query(
                func.count(func.distinct(Task.id)).label("total_tasks"),
                func.sum(Task.points).label("total_points"),
                func.count(func.distinct(Topic.id)).label("total_topics"),
                func.count(func.distinct(Lesson.id)).label("total_lessons"),
            )
            .select_from(Task)
            .join(Topic)
            .join(Lesson)
            .filter(Lesson.course_id == course_id)
            .first()
        )

        # Get student enrollment and completion stats
        enrollment_stats = (
            db.query(func.count(func.distinct(CourseEnrollment.user_id)).label("enrolled_students"))
            .filter(CourseEnrollment.course_id == course_id)
            .first()
        )

        # Get completion statistics
        completion_stats = (
            db.query(
                func.count(func.distinct(TaskSolution.user_id)).label("active_students"),
                func.count(TaskSolution.id).label("total_submissions"),
                func.count(TaskSolution.id).filter(TaskSolution.is_correct == True).label("successful_submissions"),
            )
            .join(Task)
            .join(Topic)
            .join(Lesson)
            .filter(Lesson.course_id == course_id)
            .first()
        )

        return {
            "course_id": course_id,
            "total_tasks": course_stats.total_tasks or 0,
            "total_points": course_stats.total_points or 0,
            "total_topics": course_stats.total_topics or 0,
            "total_lessons": course_stats.total_lessons or 0,
            "enrolled_students": enrollment_stats.enrolled_students or 0,
            "active_students": completion_stats.active_students or 0,
            "total_submissions": completion_stats.total_submissions or 0,
            "successful_submissions": completion_stats.successful_submissions or 0,
            "success_rate": (
                (completion_stats.successful_submissions / completion_stats.total_submissions * 100)
                if completion_stats.total_submissions > 0
                else 0
            ),
        }


@monitor_query_performance(threshold_ms=800)
def get_student_performance_summary(db: Session, course_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get student performance summary for a course
    Optimized to avoid N+1 queries when displaying student lists
    """
    with query_performance_context("get_student_performance_summary"):
        # Single query to get all student performance data
        results = (
            db.query(
                User.id,
                User.username,
                User.internal_user_id,
                func.count(TaskSolution.id).label("total_submissions"),
                func.count(TaskSolution.id).filter(TaskSolution.is_correct == True).label("correct_submissions"),
                func.sum(Task.points).filter(TaskSolution.is_correct == True).label("total_points"),
                func.max(TaskSolution.created_at).label("last_activity"),
            )
            .join(CourseEnrollment, User.id == CourseEnrollment.user_id)
            .outerjoin(TaskSolution, User.id == TaskSolution.user_id)
            .outerjoin(Task, TaskSolution.task_id == Task.id)
            .outerjoin(Topic, Task.topic_id == Topic.id)
            .outerjoin(Lesson, Topic.lesson_id == Lesson.id)
            .filter(
                CourseEnrollment.course_id == course_id, or_(Lesson.course_id == course_id, Lesson.course_id.is_(None))
            )
            .group_by(User.id, User.username, User.internal_user_id)
            .order_by(func.count(TaskSolution.id).filter(TaskSolution.is_correct == True).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": result.id,
                "username": result.username,
                "internal_user_id": result.internal_user_id,
                "total_submissions": result.total_submissions or 0,
                "correct_submissions": result.correct_submissions or 0,
                "total_points": result.total_points or 0,
                "last_activity": result.last_activity.isoformat() if result.last_activity else None,
                "success_rate": (
                    (result.correct_submissions / result.total_submissions * 100) if result.total_submissions > 0 else 0
                ),
            }
            for result in results
        ]


# ============================================================================
# BATCH OPERATIONS
# ============================================================================


@monitor_query_performance(threshold_ms=1000)
def batch_create_task_attempts(db: Session, attempts_data: List[Dict[str, Any]]) -> List[TaskAttempt]:
    """
    Create multiple task attempts in a single batch operation
    More efficient than individual inserts
    """
    with query_performance_context("batch_create_task_attempts"):
        attempts = [TaskAttempt(**data) for data in attempts_data]
        db.add_all(attempts)
        db.flush()  # Get IDs without committing
        return attempts


@monitor_query_performance(threshold_ms=800)
def batch_update_user_progress(db: Session, user_progress_updates: List[Dict[str, Any]]) -> None:
    """
    Update multiple user progress records in batch
    Uses bulk update for better performance
    """
    with query_performance_context("batch_update_user_progress"):
        if user_progress_updates:
            # Use bulk update for better performance
            db.bulk_update_mappings(TaskSolution, user_progress_updates)


# ============================================================================
# QUERY HINTS AND OPTIMIZATIONS
# ============================================================================


def get_optimized_task_query(db: Session, course_id: int):
    """
    Get a pre-optimized query for tasks in a course
    Can be further filtered or modified as needed
    """
    return (
        db.query(Task)
        .join(Topic)
        .join(Lesson)
        .filter(Lesson.course_id == course_id)
        .options(joinedload(Task.topic), selectinload(Task.attempts), selectinload(Task.solutions))
        .order_by(Lesson.lesson_order, Topic.topic_order, Task.order)
    )


def add_user_solution_counts(query, user_id: Union[int, str]):
    """
    Add user solution counts to a task query
    Helper function to extend queries with user-specific data
    """
    return (
        query.add_columns(
            func.count(TaskSolution.id)
            .filter(and_(TaskSolution.task_id == Task.id, TaskSolution.user_id == user_id))
            .label("user_solutions"),
            func.max(TaskSolution.created_at)
            .filter(and_(TaskSolution.task_id == Task.id, TaskSolution.user_id == user_id))
            .label("last_solution_date"),
        )
        .outerjoin(TaskSolution, and_(TaskSolution.task_id == Task.id, TaskSolution.user_id == user_id))
        .group_by(Task.id)
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def warm_query_cache(db: Session, course_id: int):
    """
    Warm up query cache by running common queries
    Useful for improving response times after deployment
    """
    with query_performance_context("warm_query_cache"):
        # Warm up course hierarchy
        get_course_with_full_hierarchy(db, course_id)

        # Warm up analytics
        get_course_analytics_optimized(db, course_id)

        # Warm up student performance
        get_student_performance_summary(db, course_id, limit=10)
