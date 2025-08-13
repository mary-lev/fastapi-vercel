"""
Professor Analytics Service Router
Handles analytics, administrative functions, and course management for professors
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from pydantic import BaseModel

from models import User, Task, TaskAttempt, TaskSolution, Course, Topic, Lesson, StudentFormSubmission
from db import get_db
from utils.logging_config import logger

router = APIRouter()


# Pydantic models
class TaskGenerationRequest(BaseModel):
    topic_id: int
    task_type: str
    difficulty: str = "medium"
    count: int = 1


class StudentFormResponse(BaseModel):
    id: int
    user_id: int
    programming_experience: str
    operating_system: str
    python_confidence: int
    submitted_at: datetime

    class Config:
        from_attributes = True


# Analytics endpoints (migrated from analysis.py)
@router.get("/analytics/students", summary="Get comprehensive student analytics")
def get_student_analytics(start_date: str = "2024-11-12", db: Session = Depends(get_db)):
    """
    Get comprehensive analytics about student engagement and performance.
    Returns metrics like completion rates, attempt patterns, time spent, and abandonment rates.

    Args:
        start_date: Filter students who started after this date (default: "2024-11-12")
    """
    try:
        analytics = {
            "overall_metrics": {},
            "student_metrics": [],
            "task_difficulty_metrics": {},
            "engagement_trends": {},
            "topic_performance": {},
        }

        # 1. Overall course metrics
        total_students = db.query(func.count(User.id)).scalar()
        total_tasks = db.query(func.count(Task.id)).scalar()
        total_attempts = db.query(func.count(TaskAttempt.id)).scalar()
        total_solutions = db.query(func.count(TaskSolution.id)).scalar()

        analytics["overall_metrics"] = {
            "total_students": total_students,
            "total_tasks": total_tasks,
            "total_attempts": total_attempts,
            "total_solutions": total_solutions,
            "average_completion_rate": (
                (total_solutions / (total_students * total_tasks) * 100) if total_students and total_tasks else 0
            ),
        }

        # Get the first attempt date for each student
        first_attempts = (
            db.query(User.id, func.min(TaskAttempt.submitted_at).label("first_attempt"))
            .join(TaskAttempt)
            .group_by(User.id)
            .subquery()
        )

        # 2. Individual student metrics - only for students who started after start_date
        student_metrics = (
            db.query(
                User.id,
                User.username,
                func.count(func.distinct(TaskSolution.id)).label("completed_tasks"),
                func.count(func.distinct(TaskAttempt.id)).label("total_attempts"),
                func.sum(Task.points).label("total_points"),
                func.max(TaskAttempt.submitted_at).label("last_activity"),
                first_attempts.c.first_attempt,
            )
            .join(first_attempts, User.id == first_attempts.c.id)
            .filter(first_attempts.c.first_attempt >= start_date)
            .outerjoin(TaskSolution, TaskSolution.user_id == User.id)
            .outerjoin(TaskAttempt, TaskAttempt.user_id == User.id)
            .outerjoin(Task, Task.id == TaskSolution.task_id)
            .group_by(User.id, User.username, first_attempts.c.first_attempt)
            .all()
        )

        analytics["student_metrics"] = [
            {
                "user_id": student.id,
                "username": student.username,
                "completed_tasks": student.completed_tasks,
                "total_attempts": student.total_attempts,
                "average_attempts_per_task": round(student.total_attempts / total_tasks if total_tasks else 0, 2),
                "completion_rate": round(student.completed_tasks / total_tasks * 100 if total_tasks else 0, 2),
                "total_points": student.total_points or 0,
                "last_activity": student.last_activity.isoformat() if student.last_activity else None,
            }
            for student in student_metrics
        ]

        # Get first attempts for each task-user combination
        first_task_attempts = (
            db.query(
                TaskAttempt.task_id, TaskAttempt.user_id, func.min(TaskAttempt.submitted_at).label("first_attempt_time")
            )
            .group_by(TaskAttempt.task_id, TaskAttempt.user_id)
            .subquery()
        )

        # Calculate task time and abandonment metrics
        task_time_metrics = (
            db.query(
                Task.id,
                Task.task_name,
                # Calculate average time between first attempt and solution
                func.avg(
                    case(
                        (
                            TaskSolution.id.isnot(None),
                            func.extract("epoch", TaskSolution.completed_at - first_task_attempts.c.first_attempt_time)
                            / 3600,
                        ),
                        else_=None,
                    )
                ).label("avg_completion_time_hours"),
                # Calculate abandonment rate
                (
                    1
                    - func.count(func.distinct(TaskSolution.id)) * 1.0 / func.count(func.distinct(TaskAttempt.user_id))
                ).label("abandonment_rate"),
            )
            .join(TaskAttempt, TaskAttempt.task_id == Task.id)
            .join(
                first_task_attempts,
                and_(first_task_attempts.c.task_id == Task.id, first_task_attempts.c.user_id == TaskAttempt.user_id),
            )
            .outerjoin(TaskSolution, and_(TaskSolution.task_id == Task.id, TaskSolution.user_id == TaskAttempt.user_id))
            .group_by(Task.id, Task.task_name)
            .subquery()
        )

        # 3. Task difficulty metrics
        task_metrics = (
            db.query(
                Task.id,
                Task.task_name,
                func.count(TaskAttempt.id).label("attempt_count"),
                func.count(func.distinct(TaskSolution.id)).label("solution_count"),
                func.avg(case((TaskSolution.id.isnot(None), TaskAttempt.attempt_number), else_=None)).label(
                    "avg_attempts_to_solve"
                ),
                task_time_metrics.c.avg_completion_time_hours,
                task_time_metrics.c.abandonment_rate,
            )
            .outerjoin(TaskAttempt, TaskAttempt.task_id == Task.id)
            .outerjoin(TaskSolution, TaskSolution.task_id == Task.id)
            .outerjoin(task_time_metrics, task_time_metrics.c.id == Task.id)
            .group_by(
                Task.id,
                Task.task_name,
                task_time_metrics.c.avg_completion_time_hours,
                task_time_metrics.c.abandonment_rate,
            )
            .all()
        )

        analytics["task_difficulty_metrics"] = {
            task.task_name: {
                "total_attempts": task.attempt_count,
                "successful_solutions": task.solution_count,
                "success_rate": (task.solution_count / task.attempt_count * 100) if task.attempt_count else 0,
                "avg_attempts_to_solve": round(float(task.avg_attempts_to_solve or 0), 2),
                "avg_completion_time_hours": round(float(task.avg_completion_time_hours or 0), 2),
                "abandonment_rate": round(float(task.abandonment_rate or 0) * 100, 2),
            }
            for task in task_metrics
        }

        # 4. Topic performance analysis
        topic_metrics = (
            db.query(
                Topic.title,
                func.count(func.distinct(Task.id)).label("total_tasks"),
                func.count(func.distinct(TaskSolution.id)).label("completed_tasks"),
                func.avg(case((TaskSolution.id.isnot(None), TaskAttempt.attempt_number), else_=None)).label(
                    "avg_attempts_per_completion"
                ),
            )
            .join(Task, Task.topic_id == Topic.id)
            .outerjoin(TaskSolution, TaskSolution.task_id == Task.id)
            .outerjoin(TaskAttempt, TaskAttempt.task_id == Task.id)
            .group_by(Topic.id, Topic.title)
            .all()
        )

        analytics["topic_performance"] = {
            topic.title: {
                "total_tasks": topic.total_tasks,
                "completed_tasks": topic.completed_tasks,
                "completion_rate": (
                    (topic.completed_tasks / (topic.total_tasks * total_students) * 100) if total_students else 0
                ),
                "avg_attempts_per_completion": round(float(topic.avg_attempts_per_completion or 0), 2),
            }
            for topic in topic_metrics
        }

        # 5. Time-based engagement trends
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        daily_engagement = (
            db.query(
                func.date_trunc("day", TaskAttempt.submitted_at).label("date"),
                func.count(func.distinct(TaskAttempt.user_id)).label("active_users"),
                func.count(TaskAttempt.id).label("total_attempts"),
                func.count(func.distinct(TaskSolution.id)).label("solutions_submitted"),
            )
            .outerjoin(TaskSolution, TaskSolution.task_id == TaskAttempt.task_id)
            .filter(TaskAttempt.submitted_at >= week_ago)
            .group_by(func.date_trunc("day", TaskAttempt.submitted_at))
            .order_by(func.date_trunc("day", TaskAttempt.submitted_at))
            .all()
        )

        analytics["engagement_trends"] = {
            str(day.date): {
                "active_users": day.active_users,
                "total_attempts": day.total_attempts,
                "solutions_submitted": day.solutions_submitted,
                "engagement_score": (day.active_users / total_students * 100) if total_students else 0,
            }
            for day in daily_engagement
        }

        return analytics

    except Exception as e:
        logger.error(f"Error in get_student_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/tasks/daily", summary="Get daily task analytics")
def get_task_daily_analytics(start_date: str = "2024-11-12", db: Session = Depends(get_db)):
    """
    Get daily statistics for each task's attempts and solutions.

    Args:
        start_date: Filter attempts after this date (default: "2024-11-12")
    """
    try:
        # Get daily task attempts and solutions
        daily_task_metrics = (
            db.query(
                Task.id,
                Task.task_name,
                func.date_trunc("day", TaskAttempt.submitted_at).label("date"),
                func.count(TaskAttempt.id).label("attempts"),
                func.count(func.distinct(TaskSolution.id)).label("solutions"),
                func.count(func.distinct(TaskAttempt.user_id)).label("unique_users"),
            )
            .join(TaskAttempt, TaskAttempt.task_id == Task.id)
            .outerjoin(
                TaskSolution,
                and_(
                    TaskSolution.task_id == Task.id,
                    TaskSolution.user_id == TaskAttempt.user_id,
                    func.date_trunc("day", TaskSolution.completed_at)
                    == func.date_trunc("day", TaskAttempt.submitted_at),
                ),
            )
            .filter(TaskAttempt.submitted_at >= start_date)
            .group_by(Task.id, Task.task_name, func.date_trunc("day", TaskAttempt.submitted_at))
            .order_by(Task.id, func.date_trunc("day", TaskAttempt.submitted_at))
            .all()
        )

        # Format the results by task
        task_metrics = {}
        for metric in daily_task_metrics:
            if metric.task_name not in task_metrics:
                task_metrics[metric.task_name] = []

            task_metrics[metric.task_name].append(
                {
                    "date": metric.date.isoformat(),
                    "attempts": metric.attempts,
                    "solutions": metric.solutions,
                    "unique_users": metric.unique_users,
                    "success_rate": (metric.solutions / metric.attempts * 100) if metric.attempts > 0 else 0,
                }
            )

        return task_metrics

    except Exception as e:
        logger.error(f"Error in get_task_daily_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/tasks/completion", summary="Get task completion analytics")
def get_task_completion_analytics(start_date: str = "2024-11-12", db: Session = Depends(get_db)):
    """
    Get detailed completion statistics for each task including attempts distribution and time patterns.

    Args:
        start_date: Filter attempts after this date (default: "2024-11-12")
    """
    try:
        # Get first attempts for each task-user combination
        first_attempts = (
            db.query(
                TaskAttempt.task_id, TaskAttempt.user_id, func.min(TaskAttempt.submitted_at).label("first_attempt_time")
            )
            .filter(TaskAttempt.submitted_at >= start_date)
            .group_by(TaskAttempt.task_id, TaskAttempt.user_id)
            .subquery()
        )

        # Calculate detailed task metrics
        task_metrics = (
            db.query(
                Task.id,
                Task.task_name,
                Topic.title.label("topic"),
                func.count(func.distinct(TaskAttempt.user_id)).label("total_users"),
                func.count(TaskAttempt.id).label("total_attempts"),
                func.count(func.distinct(TaskSolution.id)).label("successful_solutions"),
                func.avg(TaskAttempt.attempt_number).label("avg_attempts"),
                func.max(TaskAttempt.attempt_number).label("max_attempts"),
                # Time metrics
                func.avg(
                    case(
                        (
                            TaskSolution.id.isnot(None),
                            func.extract("epoch", TaskSolution.completed_at - first_attempts.c.first_attempt_time)
                            / 3600,
                        ),
                        else_=None,
                    )
                ).label("avg_completion_time_hours"),
                # Attempts distribution
                func.count(case((TaskAttempt.attempt_number == 1, 1))).label("first_attempts"),
                func.count(case((TaskAttempt.attempt_number > 1, 1))).label("retry_attempts"),
                # Time of day patterns
                func.count(case((func.extract("hour", TaskAttempt.submitted_at).between(9, 17), 1))).label(
                    "business_hours_attempts"
                ),
                func.count(case((~func.extract("hour", TaskAttempt.submitted_at).between(9, 17), 1))).label(
                    "after_hours_attempts"
                ),
            )
            .join(Topic, Topic.id == Task.topic_id)
            .join(TaskAttempt, TaskAttempt.task_id == Task.id)
            .join(
                first_attempts,
                and_(first_attempts.c.task_id == Task.id, first_attempts.c.user_id == TaskAttempt.user_id),
            )
            .outerjoin(TaskSolution, and_(TaskSolution.task_id == Task.id, TaskSolution.user_id == TaskAttempt.user_id))
            .filter(TaskAttempt.submitted_at >= start_date)
            .group_by(Task.id, Task.task_name, Topic.title)
            .all()
        )

        return {
            metric.id: {
                "topic": metric.topic,
                "engagement_metrics": {
                    "total_users": metric.total_users,
                    "total_attempts": metric.total_attempts,
                    "successful_solutions": metric.successful_solutions,
                    "success_rate": (
                        (metric.successful_solutions / metric.total_attempts * 100) if metric.total_attempts > 0 else 0
                    ),
                    "completion_rate": (
                        (metric.successful_solutions / metric.total_users * 100) if metric.total_users > 0 else 0
                    ),
                },
                "attempt_metrics": {
                    "avg_attempts": round(float(metric.avg_attempts or 0), 2),
                    "max_attempts": metric.max_attempts,
                    "first_time_attempts": metric.first_attempts,
                    "retry_attempts": metric.retry_attempts,
                    "retry_rate": (
                        (metric.retry_attempts / metric.total_attempts * 100) if metric.total_attempts > 0 else 0
                    ),
                },
                "time_metrics": {
                    "avg_completion_time_hours": round(float(metric.avg_completion_time_hours or 0), 2),
                    "business_hours_attempts": metric.business_hours_attempts,
                    "after_hours_attempts": metric.after_hours_attempts,
                    "business_hours_ratio": (
                        (metric.business_hours_attempts / metric.total_attempts * 100)
                        if metric.total_attempts > 0
                        else 0
                    ),
                },
            }
            for metric in task_metrics
        }

    except Exception as e:
        logger.error(f"Error in get_task_completion_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/tasks/{task_id}/progress", summary="Get task progress analytics")
def get_task_progress_analytics(task_id: int, start_date: str = "2024-11-12", db: Session = Depends(get_db)):
    """
    Get detailed progress analytics for a specific task including user progression patterns.

    Args:
        task_id: The ID of the task to analyze
        start_date: Filter attempts after this date (default: "2024-11-12")
    """
    try:
        # Get task details
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get all attempts for this task
        attempts = (
            db.query(
                TaskAttempt.user_id,
                TaskAttempt.attempt_number,
                TaskAttempt.submitted_at,
                TaskAttempt.is_successful,
                TaskSolution.completed_at,
            )
            .outerjoin(
                TaskSolution,
                and_(TaskSolution.task_id == TaskAttempt.task_id, TaskSolution.user_id == TaskAttempt.user_id),
            )
            .filter(TaskAttempt.task_id == task_id, TaskAttempt.submitted_at >= start_date)
            .order_by(TaskAttempt.user_id, TaskAttempt.submitted_at)
            .all()
        )

        # Calculate progression patterns
        user_patterns = {}
        for attempt in attempts:
            if attempt.user_id not in user_patterns:
                user_patterns[attempt.user_id] = {"attempts": [], "completion_time": None, "total_time_spent": 0}

            pattern = user_patterns[attempt.user_id]
            pattern["attempts"].append(
                {
                    "number": attempt.attempt_number,
                    "timestamp": attempt.submitted_at.isoformat(),
                    "successful": attempt.is_successful,
                }
            )

            if attempt.completed_at and not pattern["completion_time"]:
                pattern["completion_time"] = attempt.completed_at.isoformat()

            # Calculate time between attempts
            if len(pattern["attempts"]) > 1:
                time_diff = attempt.submitted_at - datetime.fromisoformat(pattern["attempts"][-2]["timestamp"])
                pattern["total_time_spent"] += time_diff.total_seconds() / 3600

        return {
            "task_name": task.task_name,
            "user_patterns": user_patterns,
            "summary": {
                "total_users": len(user_patterns),
                "completed_users": len([p for p in user_patterns.values() if p["completion_time"]]),
                "avg_attempts_to_complete": (
                    sum(len(p["attempts"]) for p in user_patterns.values()) / len(user_patterns) if user_patterns else 0
                ),
                "avg_time_spent_hours": (
                    sum(p["total_time_spent"] for p in user_patterns.values()) / len(user_patterns)
                    if user_patterns
                    else 0
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_task_progress_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Student form management (migrated from student_form.py)
@router.get("/student-forms", response_model=List[StudentFormResponse], summary="Get all student forms")
async def get_student_forms(
    limit: int = Query(100, description="Maximum number of forms to return"), db: Session = Depends(get_db)
):
    """Get all student form submissions"""
    try:
        forms = db.query(StudentFormSubmission).order_by(StudentFormSubmission.submitted_at.desc()).limit(limit).all()

        return forms

    except Exception as e:
        logger.error(f"Error retrieving student forms: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/student-forms/{user_id}", response_model=StudentFormResponse, summary="Get student form by user")
async def get_student_form_by_user(user_id: int, db: Session = Depends(get_db)):
    """Get student form submission for a specific user"""
    try:
        form = db.query(StudentFormSubmission).filter(StudentFormSubmission.user_id == user_id).first()

        if not form:
            raise HTTPException(status_code=404, detail="Student form not found")

        return form

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving student form for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Task generation (placeholder for future implementation)
@router.post("/task-generator/generate", summary="Generate new tasks")
async def generate_tasks(request: TaskGenerationRequest, db: Session = Depends(get_db)):
    """Generate new tasks using AI (placeholder for future implementation)"""
    try:
        # Verify topic exists
        topic = db.query(Topic).filter(Topic.id == request.topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Placeholder response - actual AI generation would be implemented here
        return {
            "message": f"Task generation request received for topic {request.topic_id}",
            "topic_title": topic.title,
            "task_type": request.task_type,
            "difficulty": request.difficulty,
            "count": request.count,
            "status": "pending",
            "note": "Task generation feature is not yet implemented",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_tasks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/task-generator/templates", summary="Get task generation templates")
async def get_task_templates():
    """Get available task generation templates"""
    return {
        "templates": [
            {
                "type": "CodeTask",
                "name": "Programming Exercise",
                "description": "Generate coding tasks with test cases",
                "difficulties": ["beginner", "intermediate", "advanced"],
            },
            {
                "type": "MultipleSelectQuiz",
                "name": "Multiple Choice Quiz",
                "description": "Generate multiple choice questions",
                "difficulties": ["easy", "medium", "hard"],
            },
            {
                "type": "TrueFalseQuiz",
                "name": "True/False Questions",
                "description": "Generate true/false questions",
                "difficulties": ["easy", "medium", "hard"],
            },
        ]
    }


# User management for administrators
@router.get("/users", summary="Get all users (admin only)")
async def get_all_users(
    limit: int = Query(100, description="Maximum number of users to return"),
    status: Optional[str] = Query(None, description="Filter by user status"),
    db: Session = Depends(get_db),
):
    """Get all users with optional filtering"""
    try:
        query = db.query(User)

        if status:
            query = query.filter(User.status == status)

        users = query.order_by(User.id).limit(limit).all()

        return [
            {
                "id": user.id,
                "username": user.username,
                "internal_user_id": user.internal_user_id,
                "status": user.status.value if user.status else None,
                "telegram_user_id": user.telegram_user_id,
            }
            for user in users
        ]

    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# System health and statistics
@router.get("/system/stats", summary="Get system statistics")
async def get_system_stats(db: Session = Depends(get_db)):
    """Get overall system statistics"""
    try:
        stats = {
            "total_users": db.query(func.count(User.id)).scalar(),
            "total_courses": db.query(func.count(Course.id)).scalar(),
            "total_lessons": db.query(func.count(Lesson.id)).scalar(),
            "total_topics": db.query(func.count(Topic.id)).scalar(),
            "total_tasks": db.query(func.count(Task.id)).scalar(),
            "total_attempts": db.query(func.count(TaskAttempt.id)).scalar(),
            "total_solutions": db.query(func.count(TaskSolution.id)).scalar(),
            "active_users_last_7_days": db.query(func.count(func.distinct(TaskAttempt.user_id)))
            .filter(TaskAttempt.submitted_at >= datetime.utcnow() - timedelta(days=7))
            .scalar(),
        }

        return stats

    except Exception as e:
        logger.error(f"Error retrieving system stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
