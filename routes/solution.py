from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from db import get_db
from psycopg2.extras import RealDictCursor


router = APIRouter(prefix="/api/py")

@router.post("/tasksolution/")
def insert_task_solution(user_id: str, lesson_name: str, db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            INSERT INTO tasksolution (user_id, lesson_name)
            VALUES (%s, %s)
            RETURNING *;
        """, (user_id, lesson_name))
        new_task = cursor.fetchone()
        db.commit()
        return {"new_task": new_task}
    finally:
        cursor.close()

# Endpoint to get solved tasks for a user
@router.get("/tasksolution/{user_id}")
def get_user_solved_tasks(user_id: str, db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT lesson_name FROM tasksolution WHERE user_id = %s;", (user_id,))
        tasks = cursor.fetchall()
        lesson_names = [task['lesson_name'] for task in tasks]
        return {"solved_tasks": lesson_names}
    finally:
        cursor.close()
