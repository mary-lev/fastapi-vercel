from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from models import Lesson, Topic, Task, Summary, TaskSolution, User
from db import SessionLocal

router = APIRouter()

@router.get("/api/lessons/{lesson_id}")
def get_lesson_data(
    lesson_id: int,
    user_id: str = Query(..., alias="user_id"),  # Define user_id as a required query param
):
    db: Session = SessionLocal()
    print(f"Fetching lesson data for lesson_id={lesson_id} and user_id={user_id}")
    try:
        # Get lesson by ID
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        # Fetch topics and sort by topic order
        topics = (
            db.query(Topic)
            .filter(Topic.lesson_id == lesson_id)
            .order_by(Topic.topic_order)
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
            .order_by(Task.order)
            .all()
        )

        # Get user by internal_user_id
        user = db.query(User).filter(User.internal_user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Fetch user's solved tasks
        solved_task_ids = {solution.task_id for solution in db.query(TaskSolution).filter(TaskSolution.user_id == user.id).all()}

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
                                "points": 0,
                                "order": 0,
                                "isSolved": False,  # Summaries are not solvable
                            }
                        ] if topic.id in summaries else []
                    ) + sorted(
                        [
                            {
                                "lessonType": task.type,
                                "lssonLink": task.task_link,
                                "lessonName": task.task_name,
                                "data": task.data,
                                "points": task.points,
                                "order": task.order,
                                "isSolved": task.id in solved_task_ids,  # Check if task is solved
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
