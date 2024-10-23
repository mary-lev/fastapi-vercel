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
