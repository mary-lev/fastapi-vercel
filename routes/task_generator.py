import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import func
from pydantic import BaseModel
from models import Task, TaskAttempt, TaskSolution, User  # Import models as needed
from db import get_db
from utils.task_generator import generate_tasks
from utils.logging_config import logger

router = APIRouter()


class GenerateTasksRequest(BaseModel):
    topic_id: int
    num_tasks: int
    material: str
    add_quizzes: bool
    add_previous_tasks: bool


@router.post("/generate_new_tasks")
async def generate_new_tasks(request: GenerateTasksRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"Generating {request.num_tasks} tasks for topic {request.topic_id}")

        tasks = generate_tasks(
            topic_id=request.topic_id,
            num_tasks=request.num_tasks,
            add_quizzes=request.add_quizzes,
            add_previous_tasks=request.add_previous_tasks,
            material=request.material,
        )

        logger.info(f"Successfully generated {len(tasks)} tasks for topic {request.topic_id}")
        return JSONResponse(content={"tasks": tasks})

    except ValueError as e:
        logger.error(f"Validation error in generate_new_tasks: {e}")
        raise HTTPException(status_code=400, detail="Invalid task generation parameters")
    except Exception as e:
        logger.error(f"Unexpected error in generate_new_tasks: {e}")
        raise HTTPException(status_code=500, detail="Task generation failed")
