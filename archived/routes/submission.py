from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import func
from pydantic import BaseModel
from models import Task, TaskAttempt, TaskSolution, User, AIFeedback
from db import get_db
from utils.checker import run_code
from utils.evaluator import evaluate_code_submission
from utils.evaluator import evaluate_text_submission  # Assuming an evaluation function for text
from utils.logging_config import logger


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
async def submit_code(request: Request, db: Session = Depends(get_db)):
    try:
        code_submission = await request.json()
        code = code_submission.get("code")
        task_id = code_submission.get("taskId")
        internal_user_id = code_submission.get("userId")
        logger.info(f"Code submission received for user {internal_user_id}, task {task_id}")

        # Validate input
        if not code or not task_id or not internal_user_id:
            logger.warning(f"Invalid submission data: code={bool(code)}, task_id={task_id}, user_id={internal_user_id}")
            raise HTTPException(status_code=400, detail="Invalid submission data")

        # Fetch user and task info
        user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not user:
            logger.error(f"User not found: {internal_user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task not found: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")

        # Run the code
        result = run_code(code)
        logger.debug(f"Code execution result: {result}")
        is_successful = result.get("success", False)

        # Record task attempt
        attempt_count = (
            db.query(TaskAttempt).filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == task.id).count()
        )

        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=task.id,
            attempt_number=attempt_count + 1,
            attempt_content=code,  # Save the code submission as attempt content
            is_successful=is_successful,
            submitted_at=func.now(),
        )
        db.add(task_attempt)

        # If successful, record as a completed solution
        if is_successful:
            existing_solution = (
                db.query(TaskSolution).filter(TaskSolution.user_id == user.id, TaskSolution.task_id == task.id).first()
            )

            if not existing_solution:
                task_solution = TaskSolution(
                    user_id=user.id, task_id=task.id, solution_content=code, completed_at=func.now()
                )
                db.add(task_solution)
                logger.info(f"New solution recorded for user {user.id}, task {task_id}")
            else:
                logger.debug(f"Solution already exists for user {user.id}, task {task_id}")

        db.commit()

        evaluation = evaluate_code_submission(code_submission, result.get("output"), task.data)
        new_feedback = AIFeedback(
            user_id=user.id, task_id=task_id, feedback=evaluation.feedback, task_attempt_id=task_attempt.id
        )
        db.add(new_feedback)
        db.commit()

        logger.info(
            f"Code submission processed successfully for user {user.id}, task {task_id}, successful={is_successful}"
        )
        return evaluation

    except ValueError as e:
        logger.error(f"Validation error in submit_code: {e}")
        raise HTTPException(status_code=400, detail="Invalid submission data")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in submit_code: {e}")
        raise HTTPException(status_code=409, detail="Data conflict occurred")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in submit_code: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in submit_code: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Define the structure of the request body for text submission
class TextSubmission(BaseModel):
    answer: str
    task_id: int
    user_id: int


# Endpoint to handle text submission
@router.post("/api/submit_text")
async def submit_text(request: Request, db: Session = Depends(get_db)):
    try:
        # Parse the incoming JSON data
        text_submission = await request.json()
        answer = text_submission.get("answer")
        task_id = text_submission.get("task_id")
        user_id = text_submission.get("user_id")
        logger.info(f"Text submission received for user {user_id}, task {task_id}")

        # Validate required fields
        if not answer or not task_id or not user_id:
            logger.warning(f"Invalid text submission data: answer={bool(answer)}, task_id={task_id}, user_id={user_id}")
            raise HTTPException(status_code=400, detail="Invalid submission data")

        # Retrieve user and task information
        user = db.query(User).filter(User.internal_user_id == user_id).first()
        if not user:
            logger.error(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task not found: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")

        # Evaluate the answer text for correctness
        evaluation = evaluate_text_submission(answer, task.data)
        is_solved = evaluation.is_solved
        feedback = evaluation.feedback
        logger.debug(f"Text evaluation result: is_solved={is_solved}")

        # Record the task attempt
        attempt_count = (
            db.query(TaskAttempt).filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == task.id).count()
        )

        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=task.id,
            attempt_number=attempt_count + 1,
            attempt_content=answer,
            is_successful=is_solved,
            submitted_at=func.now(),
        )
        db.add(task_attempt)

        db.commit()

        new_feedback = AIFeedback(user_id=user.id, task_id=task.id, feedback=feedback, task_attempt_id=task_attempt.id)
        db.add(new_feedback)

        # If the answer is correct, save it as a solution
        if is_solved:
            existing_solution = (
                db.query(TaskSolution).filter(TaskSolution.user_id == user.id, TaskSolution.task_id == task.id).first()
            )
            if not existing_solution:
                task_solution = TaskSolution(
                    user_id=user.id, task_id=task.id, solution_content=answer, completed_at=func.now()
                )
                db.add(task_solution)
                logger.info(f"New text solution recorded for user {user.id}, task {task_id}")
            else:
                logger.debug(f"Text solution already exists for user {user.id}, task {task_id}")

        # Commit the transaction to save changes to the database
        db.commit()

        logger.info(f"Text submission processed successfully for user {user.id}, task {task_id}, solved={is_solved}")
        # Return evaluation result to the client
        return JSONResponse(content={"is_solved": is_solved, "feedback": feedback})

    except ValueError as e:
        logger.error(f"Validation error in submit_text: {e}")
        raise HTTPException(status_code=400, detail="Invalid submission data")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in submit_text: {e}")
        raise HTTPException(status_code=409, detail="Data conflict occurred")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in submit_text: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in submit_text: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
