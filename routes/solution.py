from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from models import Task, TaskSolution, TaskAttempt, User  # Adjust model imports as needed
from db import SessionLocal

router = APIRouter()

@router.post("/api/insertTaskSolution")
async def insert_task_solution(request: Request):
    db: Session = SessionLocal()
    try:
        data = await request.json()
        print(data)
        internal_user_id = data.get("userId")  # UUID from the frontend
        task_link = data.get("lessonName")
        is_successful = data.get("isSuccessful", False)  # Whether the attempt was successful
        solution_content = data.get("solutionContent", "")  # Solution content from the frontend

        # Validate input
        if not internal_user_id or not task_link:
            raise HTTPException(status_code=400, detail="Invalid input data")

        # Fetch the user ID using the UUID from the User model
        user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get the task by task link
        task = db.query(Task).filter(Task.task_link == task_link).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Fetch the number of previous attempts for this user-task pair
        attempt_count = db.query(TaskAttempt).filter(
            TaskAttempt.user_id == user.id,
            TaskAttempt.task_id == task.id
        ).count()

        # Record the task attempt, including the attempt content
        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=task.id,
            attempt_number=attempt_count + 1,
            is_successful=is_successful,
            attempt_content=solution_content,  # Store the attempt content
            submitted_at=func.now()
        )

        db.add(task_attempt)
        
        # If the attempt is successful and no solution exists, save it as a completed task
        if is_successful:
            existing_solution = db.query(TaskSolution).filter(
                TaskSolution.user_id == user.id,
                TaskSolution.task_id == task.id
            ).first()

            if not existing_solution:
                task_solution = TaskSolution(
                    user_id=user.id,
                    task_id=task.id,
                    solution_content=solution_content,  # Store the content of the successful attempt
                    completed_at=func.now()
                )
                db.add(task_solution)

        db.commit()

        return {"message": "Task attempt recorded successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
