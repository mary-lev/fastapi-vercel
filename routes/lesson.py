from fastapi import APIRouter, HTTPException, Query
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

        lesson_data = {"lesson": []}

        # Iterate over topics and add each to lesson_data
        for topic_idx, topic in enumerate(topics):
            topic_data = {
                "id": topic.id,
                "title": topic.title,
                "summary": {
                    "background": topic.background,
                    "objectives": topic.objectives,
                    "content": topic.content_file_md,
                    "concepts": topic.concepts,
                },
                "listItem": [],
            }

            # Add the summary as the first item, if it exists
            if topic.id in summaries:
                summary = summaries[topic.id]
                summary_data = {
                    "lessonType": "Summary",
                    "lssonLink": summary.lesson_link,
                    "lessonName": summary.lesson_name,
                    "data": summary.data,
                    "points": 0,
                    "order": 0,
                    "isSolved": False,
                }

                # Set prevUrl for summary
                if topic_idx > 0:
                    prev_topic = topics[topic_idx - 1]
                    last_task_of_prev_topic = max(
                        [task for task in tasks if task.topic_id == prev_topic.id],
                        key=lambda t: t.order,
                        default=None
                    )
                    summary_data["prevUrl"] = last_task_of_prev_topic.task_link if last_task_of_prev_topic else None
                else:
                    summary_data["prevUrl"] = None

                # Set nextUrl for summary
                first_task_in_topic = next(
                    (task for task in tasks if task.topic_id == topic.id), None
                )
                summary_data["nextUrl"] = first_task_in_topic.task_link if first_task_in_topic else None

                topic_data["listItem"].append(summary_data)

            # Get the tasks for the current topic and add nextUrl and prevUrl
            topic_tasks = [task for task in tasks if task.topic_id == topic.id]
            for task_idx, task in enumerate(topic_tasks):
                task_data = {
                    "lessonType": task.type,
                    "lssonLink": task.task_link,
                    "lessonName": task.task_name,
                    "data": task.data,
                    "points": task.points,
                    "order": task.order,
                    "isSolved": task.id in solved_task_ids,
                }

                # Set prevUrl
                if task_idx == 0:
                    task_data["prevUrl"] = summaries[topic.id].lesson_link if topic.id in summaries else None
                else:
                    task_data["prevUrl"] = topic_tasks[task_idx - 1].task_link

                # Set nextUrl
                if task_idx == len(topic_tasks) - 1:
                    if topic_idx < len(topics) - 1:
                        next_topic = topics[topic_idx + 1]
                        task_data["nextUrl"] = summaries[next_topic.id].lesson_link if next_topic.id in summaries else None
                    else:
                        task_data["nextUrl"] = None
                else:
                    task_data["nextUrl"] = topic_tasks[task_idx + 1].task_link

                topic_data["listItem"].append(task_data)

            # Add topic data to lesson_data
            lesson_data["lesson"].append(topic_data)

        return lesson_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
