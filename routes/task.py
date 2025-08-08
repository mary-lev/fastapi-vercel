from fastapi import APIRouter, HTTPException, Query, Request, Depends
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import (
    Lesson,
    Topic,
    Task,
    CodeTask,
    Summary,
    TaskSolution,
    User,
    TaskAttempt,
    MultipleSelectQuiz,
    TrueFalseQuiz,
    SingleQuestionTask,
    CodeTask,
)
from db import get_db
from utils.logging_config import logger
from schemas.validation import TaskUpdateSchema

router = APIRouter()


@router.post("/api/updateMultipleSelectTask")
async def update_multiple_select_task(task_data: TaskUpdateSchema, db: Session = Depends(get_db)):
    try:
        task_id = task_data.taskId
        new_question = task_data.newQuestion
        new_options = task_data.newOptions
        new_correct_answers = task_data.newCorrectAnswers

        # Fetch the task from the database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Update the JSON field
        task_data = task.data.copy() if task.data else {}
        task_data["question"] = new_question
        task_data["options"] = [{"id": str(i + 1), "name": option["name"]} for i, option in enumerate(new_options)]
        task_data["correctAnswers"] = new_correct_answers

        # Assign the modified JSON to the task data field
        task.data = task_data

        # Update the `updated_at` timestamp for the task
        task.updated_at = func.now()

        # Commit the changes
        db.commit()
        db.refresh(task)  # Refresh the task to ensure it has the latest data

        logger.info(f"Multiple select task updated successfully: {task_id}")
        return {"message": "Task updated successfully"}

    except ValueError as e:
        logger.error(f"Validation error in update_multiple_select_task: {e}")
        raise HTTPException(status_code=400, detail="Invalid task data")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in update_multiple_select_task: {e}")
        raise HTTPException(status_code=409, detail="Task update conflict")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in update_multiple_select_task: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in update_multiple_select_task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/updateTrueFalseTask")
async def update_true_false_task(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()  # Read the JSON payload
        task_id = data.get("taskId")
        new_question = data.get("newQuestion")
        new_correct_answer = data.get("newCorrectAnswer")

        if not task_id:
            raise HTTPException(status_code=400, detail="Task ID is required.")

        # Fetch the task from the database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Update the JSON field
        task_data = task.data.copy() if task.data else {}
        task_data["question"] = new_question
        task_data["correctAnswers"] = new_correct_answer

        # Assign the modified JSON to the task data field
        task.data = task_data

        # Update the updated_at timestamp for the task
        task.updated_at = func.now()

        # Commit the changes
        db.commit()
        db.refresh(task)  # Refresh the task to ensure it has the latest data

        logger.info(f"True/False task updated successfully: {task_id}")
        return {"message": "True/False task updated successfully"}

    except ValueError as e:
        logger.error(f"Validation error in update_true_false_task: {e}")
        raise HTTPException(status_code=400, detail="Invalid task data")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in update_true_false_task: {e}")
        raise HTTPException(status_code=409, detail="Task update conflict")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in update_true_false_task: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in update_true_false_task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/updateSingleQuestionTask")
async def update_single_question_task(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        task_id = data.get("taskId")
        new_question = data.get("newQuestion")
        points = data.get("newPoints")

        if not task_id or not new_question:
            raise HTTPException(status_code=400, detail="Task ID and new question are required.")

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        task_data = task.data.copy() if task.data else {}
        task_data["question"] = new_question
        task.points = points
        task.data = task_data

        # Update the updated_at timestamp for the task
        task.updated_at = func.now()

        db.commit()
        return {"message": "Task updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/updateCodeTask")
async def update_code_task(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()  # Read the JSON payload
        task_id = data.get("task_id")
        new_code = data.get("newCode")
        new_text = data.get("newText")
        new_title = data.get("newTitle")

        if not task_id:
            raise HTTPException(status_code=400, detail="Task ID is required.")

        # Fetch the task from the database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Update the task fields
        task_data = task.data.copy() if task.data else {}
        task_data["code"] = new_code
        task_data["text"] = new_text
        task.task_name = new_title

        task.data = task_data

        # Update the updated_at timestamp for the task
        task.updated_at = func.now()

        # Commit the changes
        db.commit()
        db.refresh(task)  # Refresh the task to ensure it has the latest data
        return {"message": "Task updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/deactivate-task/{task_id}")
def deactivate_task(task_id: int, db: Session = Depends(get_db)):
    try:
        # Fetch the task from the database
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Set is_active to False instead of deleting the record
        task.is_active = False
        db.commit()

        return {"message": "Task deactivated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/delete-task/{task_id}")
def delete_task_permanently(task_id: int, db: Session = Depends(get_db)):
    try:
        # Fetch the task and delete it
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task not found for deletion: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found.")

        db.delete(task)
        db.commit()
        logger.info(f"Task {task_id} deleted permanently")
        return {"message": "Task deleted permanently"}

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in delete_task_permanently: {e}")
        raise HTTPException(status_code=409, detail="Cannot delete task due to existing references")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in delete_task_permanently: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in delete_task_permanently: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/api/activate-task/{task_id}")
def activate_task(task_id: int, db: Session = Depends(get_db)):
    try:
        # Find the task by ID
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task not found for activation: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found.")

        # Activate the task
        task.is_active = True
        db.commit()
        logger.info(f"Task {task_id} activated successfully")
        return {"message": "Task activated successfully"}

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in activate_task: {e}")
        raise HTTPException(status_code=409, detail="Data conflict occurred")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in activate_task: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in activate_task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/add-code-task")
async def add_code_task(request: Request, db: Session = Depends(get_db)):
    try:
        # Read the JSON payload
        data = await request.json()
        topic_id = data.get("topicId")  # Use lessonId for topic_id
        new_code = data.get("data", {}).get("code")
        new_text = data.get("data", {}).get("text")
        new_title = data.get("lessonName")
        points = data.get("points", 0)
        is_active = data.get("is_active", True)

        # Validate required fields
        if not topic_id or not new_code or not new_title:
            raise HTTPException(status_code=400, detail="Topic ID, code, and title are required.")

        # Fetch the topic from the database
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found.")

        # Generate a unique task_link (can be improved to ensure uniqueness)
        task_link = f"code-task-{topic_id}-{new_title.replace(' ', '-').lower()}"

        # Determine the order of the new task
        max_order = db.query(Task).filter(Task.topic_id == topic_id).order_by(Task.order.desc()).first()
        new_order = max_order.order + 1 if max_order else 1

        # Create a new CodeTask
        new_task = CodeTask(
            topic_id=topic_id,
            type="code_task",
            task_name=new_title,
            task_link=task_link,
            data={"code": new_code, "text": new_text},
            points=points,
            is_active=is_active,
            order=new_order,
        )

        # Add and commit the new task to the database
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        return {"message": "Code task added successfully", "task_id": new_task.id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    try:
        # Fetch the task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task not found: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")

        logger.debug(f"Task {task_id} retrieved successfully")
        return {
            "id": task.id,
            "order": task.order,
            "title": task.task_name,
            "data": task.data,
            "points": task.points,
            "is_active": task.is_active,
            "task_link": task.task_link,
        }

    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        raise HTTPException(status_code=500, detail="Error fetching task data")
