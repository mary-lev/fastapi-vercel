from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pydantic import BaseModel
from models import Task, TaskAttempt, TaskSolution, User  # Import models as needed
from db import SessionLocal
from utils.checker import run_code
from utils.evaluator import evaluate_code_submission
from utils.evaluator import evaluate_text_submission  # Assuming an evaluation function for text


router = APIRouter()

class CodeSubmission(BaseModel):
    code: str
    language: str
    task_id: int
    user_id: int

@router.post("/api/compile")
async def compile_code(request: Request):
    try:
        code_submission = await request.json()
        code = code_submission.get("code")

        if not code:
            raise HTTPException(status_code=400, detail="No code provided")

        # Run the code and return the output
        result = run_code(code)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/submit")
async def submit_code(request: Request):
    db: Session = SessionLocal()
    try:
        code_submission = await request.json()
        code = code_submission.get("code")
        task_id = code_submission.get("lessonItem").get("id")
        internal_user_id = code_submission.get("userId")

        # Validate input
        if not code or not task_id or not internal_user_id:
            raise HTTPException(status_code=400, detail="Invalid submission data")

        # Fetch user and task info
        user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Run the code
        result = run_code(code)
        is_successful = result.get("success", False)

        # Record task attempt
        attempt_count = db.query(TaskAttempt).filter(
            TaskAttempt.user_id == user.id,
            TaskAttempt.task_id == task.id
        ).count()

        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=task.id,
            attempt_number=attempt_count + 1,
            attempt_content=code,  # Save the code submission as attempt content
            is_successful=is_successful,
            submitted_at=func.now()
        )
        db.add(task_attempt)

        # If successful, record as a completed solution
        if is_successful:
            existing_solution = db.query(TaskSolution).filter(
                TaskSolution.user_id == user.id,
                TaskSolution.task_id == task.id
            ).first()

            if not existing_solution:
                task_solution = TaskSolution(
                    user_id=user.id,
                    task_id=task.id,
                    solution_content=code,
                    completed_at=func.now()
                )
                db.add(task_solution)

        db.commit()

        evaluation = evaluate_code_submission(code_submission, result.get("output"), task.data)
        return evaluation

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()



# Define the structure of the request body for text submission
class TextSubmission(BaseModel):
    answer: str
    task_id: int
    user_id: int


# Endpoint to handle text submission
@router.post("/api/submit_text")
async def submit_text(request: Request):
    db: Session = SessionLocal()
    try:
        # Parse the incoming JSON data
        text_submission = await request.json()
        answer = text_submission.get("answer")
        task_id = text_submission.get("task_id")
        user_id = text_submission.get("user_id")

        # Validate required fields
        if not answer or not task_id or not user_id:
            raise HTTPException(status_code=400, detail="Invalid submission data")

        # Retrieve user and task information
        user = db.query(User).filter(User.internal_user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Evaluate the answer text for correctness
        evaluation = evaluate_text_submission(answer, task.data)
        is_solved = evaluation.is_solved
        feedback = evaluation.feedback
        print(f"Answer: {answer}, Correct: {is_solved}, Feedback: {feedback}")

        # Record the task attempt
        attempt_count = db.query(TaskAttempt).filter(
            TaskAttempt.user_id == user.id,
            TaskAttempt.task_id == task.id
        ).count()

        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=task.id,
            attempt_number=attempt_count + 1,
            attempt_content=answer,
            is_successful=is_solved,
            submitted_at=func.now()
        )
        db.add(task_attempt)

        # If the answer is correct, save it as a solution
        if is_solved:
            existing_solution = db.query(TaskSolution).filter(
                TaskSolution.user_id == user.id,
                TaskSolution.task_id == task.id
            ).first()
            if not existing_solution:
                task_solution = TaskSolution(
                    user_id=user.id,
                    task_id=task.id,
                    solution_content=answer,
                    completed_at=func.now()
                )
                db.add(task_solution)

        # Commit the transaction to save changes to the database
        db.commit()

        # Return evaluation result to the client
        return JSONResponse(
            content={
                "is_solved": is_solved,
                "feedback": feedback
            }
        )

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
