"""
Task attempt management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from db import get_db
from models import Task, TaskAttempt, User

router = APIRouter()


@router.get("/api/v1/tasks/{task_id}/attempt-status")
async def get_attempt_status(task_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Get the attempt status for a user on a specific task.
    Returns information about attempts used, remaining, and completion status.
    """
    # Get the task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get attempt count and check if completed
    attempts = db.query(TaskAttempt).filter(TaskAttempt.task_id == task_id, TaskAttempt.user_id == user_id).all()

    attempt_count = len(attempts)
    is_completed = any(a.is_successful for a in attempts)

    # Determine if user can make another attempt
    can_attempt = False
    if task.attempt_strategy == "unlimited":
        can_attempt = not is_completed  # Can attempt until successful
    else:
        # For 'single' strategy
        can_attempt = attempt_count < (task.max_attempts or 0) and not is_completed

    return {
        "task_id": task_id,
        "task_type": task.type,
        "attempt_strategy": task.attempt_strategy,
        "max_attempts": task.max_attempts,
        "attempts_used": attempt_count,
        "can_attempt": can_attempt,
        "is_completed": is_completed,
        "message": _get_status_message(task, attempt_count, is_completed),
    }


def _get_status_message(task: Task, attempts_used: int, is_completed: bool) -> str:
    """Generate a user-friendly status message"""
    if is_completed:
        return "Task completed successfully!"

    if task.attempt_strategy == "unlimited":
        return f"Attempt {attempts_used + 1} - Unlimited attempts available"

    remaining = (task.max_attempts or 0) - attempts_used
    if remaining <= 0:
        return "Maximum attempts reached. No more attempts available."
    elif remaining == 1:
        return "Last attempt remaining. Make it count!"
    else:
        return f"{remaining} attempts remaining"
