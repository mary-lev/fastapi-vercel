from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from models import Lesson, Topic, Task, Summary  # Assuming models are defined in models.py
from db import SessionLocal

router = APIRouter()

@router.get("/api/lessons/{lesson_id}")
def get_lesson_data(lesson_id: int):
    db: Session = SessionLocal()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Fetch topics and sort by topic order
        topics = (
            db.query(Topic)
            .filter(Topic.lesson_id == lesson_id)
            .order_by(Topic.topic_order)  # Sort topics by 'topic_order' field
            .all()
        )

        # Fetch summaries for each topic
        summaries = {
            summary.topic_id: summary
            for summary in db.query(Summary).filter(Summary.topic_id.in_([topic.id for topic in topics])).all()
        }

        # Fetch tasks and sort by task order
        tasks = (
            db.query(Task)
            .filter(Task.topic_id.in_([topic.id for topic in topics]))
            .order_by(Task.order)  # Sort tasks by 'order' field
            .all()
        )

        # Serialize and organize the data
        lesson_data = {
            "lesson": [
                {
                    "id": topic.id,
                    "title": topic.title,
                    "summary": {
                        "background": topic.background,
                        "objectives": topic.objectives,
                        "content": topic.content_file_md,
                        "concepts": topic.concepts,
                    },
                    "listItem": (
                        [
                            {
                                "lessonType": "Summary",
                                "lssonLink": summaries[topic.id].lesson_link,
                                "lessonName": summaries[topic.id].lesson_name,
                                "data": summaries[topic.id].data,
                                "points": 0,  # Summary has no points
                                "order": 0,  # Set order as 0 to make it first
                            }
                        ] if topic.id in summaries else []
                    ) + sorted(  # Add Summary if it exists
                        [
                            {
                                "lessonType": task.type,
                                "lssonLink": task.task_link,
                                "lessonName": task.task_name,
                                "data": task.data,
                                "points": task.points,
                                "order": task.order,
                            }
                            for task in tasks
                            if task.topic_id == topic.id
                        ],
                        key=lambda x: x["order"]
                    ),
                }
                for topic in topics
            ]
        }

        return lesson_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
