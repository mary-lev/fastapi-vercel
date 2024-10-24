from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from models import Lesson, Topic, Task, Summary, TaskSolution, User
from db import SessionLocal

router = APIRouter()

@router.get("/api/topics")
def get_topics_data():
    db: Session = SessionLocal()
    try:
        # Fetch all lessons and their topics
        lessons = db.query(Lesson).all()

        # Format the result as you want
        lesson_data = []
        for lesson in lessons:
            # Fetch related topics for the lesson
            topics = db.query(Topic).filter(Topic.lesson_id == lesson.id).order_by(Topic.topic_order).all()

            lesson_data.append({
                "lesson": f"{lesson.id}. {lesson.title}",
                "topics": [{"title": topic.title, "concepts": topic.concepts} for topic in topics]
            })

        return lesson_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/topics/{topic_id}")
def get_topic_data(topic_id: int):
    db: Session = SessionLocal()
    try:
        # Fetch the topic by ID
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Fetch related tasks for the topic
        tasks = db.query(Task).filter(Task.topic_id == topic_id).order_by(Task.order).all()

        # Format the result as you want
        topic_data = {
            "title": topic.title,
            "concepts": topic.concepts,
            "tasks": [{"question": task.data.get("question"), "options": task.data.get("options")} for task in tasks]
        }

        return topic_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/topics/generate_new_tasks")
def generate_new_tasks(topic_id: int, num_tasks: int):
    from utils.task_generator import generate_tasks
    db: Session = SessionLocal()
    try:
        # Generate new tasks for the specified topic
        tasks = generate_tasks(topic_id, num_tasks)
        return {"tasks": tasks}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()