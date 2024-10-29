import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pydantic import BaseModel
from models import Task, TaskAttempt, TaskSolution, User  # Import models as needed
from db import SessionLocal
from utils.task_generator import generate_tasks

router = APIRouter()

@router.post("/generate_new_tasks")
async def generate_new_tasks(
    topic_id: int, 
    num_tasks: int, 
    material: str = "Harry Potter",
    add_quizzes: bool = False,
    add_previous_tasks: bool = True,
):
    # db: Session = SessionLocal()
    try:
        # Generate new tasks
        tasks = generate_tasks(
            topic_id, 
            num_tasks,
            add_quizzes,
            add_previous_tasks,
            material
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # finally:
    #     db.close()

    return JSONResponse(content={"tasks": tasks})