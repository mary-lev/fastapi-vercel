from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from models import Lesson, Topic, Task, CodeTask, Summary, TaskSolution, User
from db import SessionLocal

router = APIRouter()


@router.post("/api/updateMultipleSelectTask")
async def update_multiple_select_task(request: Request):
    db: Session = SessionLocal()
    try:
        data = await request.json()  # Parse JSON request body
        task_id = data.get("taskId")
        new_question = data.get("newQuestion")
        new_options = data.get("newOptions")
        new_correct_answers = data.get("newCorrectAnswers")

        # Validate request data
        if not task_id:
            raise HTTPException(status_code=400, detail="Task ID is required.")
        
        # Fetch the task from the database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

       # Update the JSON field
        task_data = task.data.copy() if task.data else {}
        task_data["question"] = new_question
        task_data["options"] = [{"id": str(i+1), "name": option["name"]} for i, option in enumerate(new_options)]
        task_data["correctAnswers"] = new_correct_answers

        # Assign the modified JSON to the task data field
        task.data = task_data

        # Update the `updated_at` timestamp for the task
        task.updated_at = func.now()

        # Commit the changes
        db.commit()
        db.refresh(task)  # Refresh the task to ensure it has the latest data

        return {"message": "Task updated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/api/updateTrueFalseTask")
async def update_true_false_task(request: Request):
    db: Session = SessionLocal()

    try:
        data = await request.json()  # Read the JSON payload
        task_id = data.get("taskId")
        new_question = data.get("newQuestion")
        new_correct_answer = data.get("newCorrectAnswer")
        print(data)

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

        return {"message": "True/False task updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/api/updateSingleQuestionTask")
async def update_single_question_task(request: Request):
    db: Session = SessionLocal()
    try:
        data = await request.json()
        print(data)
        task_id = data.get("taskId")
        new_question = data.get("newQuestion")
        points = data.get("newPoints")

        if not task_id or not new_question:
            raise HTTPException(status_code=400, detail="Task ID and new question are required.")

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        task.data["question"] = new_question
        task.points = points

        db.commit()
        return {"message": "Task updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()

@router.post("/api/updateCodeTask")
async def update_code_task(request: Request):
    db: Session = SessionLocal()
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
        task.data["code"] = new_code
        task.data["text"] = new_text
        task.task_name = new_title

        db.commit()
        return {"message": "Task updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/api/delete-task/{task_id}")
def delete_task(task_id: int):
    db: Session = SessionLocal()
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


@router.put("/api/activate-task/{task_id}")
def activate_task(task_id: int):
    db: Session = SessionLocal()
    try:
        # Find the task by ID
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")

        # Activate the task
        task.is_active = True
        db.commit()
        return {"message": "Task activated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
