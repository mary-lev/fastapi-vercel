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

class GenerateTasksRequest(BaseModel):
    topic_id: int
    num_tasks: int
    material: str
    add_quizzes: bool
    add_previous_tasks: bool

@router.post("/generate_new_tasks")
async def generate_new_tasks(request: GenerateTasksRequest):
    try:       
        tasks = generate_tasks(
            topic_id=request.topic_id, 
            num_tasks=request.num_tasks,
            add_quizzes=request.add_quizzes,
            add_previous_tasks=request.add_previous_tasks,
            material=request.material,
            )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    # finally:
    #     db.close()

    return JSONResponse(content={"tasks": tasks})