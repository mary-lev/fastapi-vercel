from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from models import Lesson, Topic, Task, Summary, TaskSolution, User, UserStatus
from schemas import SummarySchema  # Pydantic schema
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

        # Determine if user is a student
        is_student = user.status == UserStatus.STUDENT

        lesson_data = {"lesson": []}

        # Iterate over topics and add each to lesson_data
        for topic_idx, topic in enumerate(topics):
            topic_data = {
                "id": topic.id,
                "title": topic.title,
                "listItem": [],
            }

            # Get the tasks for the current topic and add nextUrl and prevUrl
            topic_tasks = [task for task in tasks if task.topic_id == topic.id]
            for task_idx, task in enumerate(topic_tasks):
                # Filter out inactive tasks if the user is a student
                if is_student and not task.is_active:
                    continue

                task_data = {
                    "id": task.id,
                    "lessonType": task.type,
                    "lssonLink": task.task_link,
                    "lessonName": task.task_name,
                    "data": task.data,
                    "points": task.points,
                    "order": task.order,
                    "isSolved": task.id in solved_task_ids,
                    "is_active": task.is_active,
                }

                # Set prevUrl
                if task_idx == 0:
                    task_data["prevUrl"] = None
                else:
                    task_data["prevUrl"] = topic_tasks[task_idx - 1].task_link

                # Set nextUrl
                if task_idx == len(topic_tasks) - 1:
                    if topic_idx < len(topics) - 1:
                        next_topic = topics[topic_idx + 1]
                        next_topic_tasks = [t for t in tasks if t.topic_id == next_topic.id]
                        task_data["nextUrl"] = next_topic_tasks[0].task_link if next_topic_tasks else None
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



@router.get("/api/lessons/{lesson_id}/summaries", response_model=dict)
def get_summaries(lesson_id: int):
    db: Session = SessionLocal()
    summaries = (
        db.query(Summary)
        .join(Topic, Summary.topic_id == Topic.id)
        .filter(Topic.lesson_id == lesson_id)
        .options(joinedload(Summary.topic))  # Load the related Topic
        .all()
    )

    # Convert SQLAlchemy models to Pydantic models, including topic title
    summaries_data = [
        SummarySchema(
            **summary.__dict__,
            topic_title=summary.topic.title  # Add the topic title from the relationship
        )
        for summary in summaries
    ]
    return {"summaries": summaries_data}

@router.put("/lessons/{lesson_id}/rebuild-task-links", response_model=dict)
def rebuild_task_links(lesson_id: int):
    db: Session = SessionLocal()
    # Fetch lesson with all topics and tasks
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Loop through each topic in the lesson
    for topic in lesson.topics:
        # Get all tasks for the topic, ordered by created_at
        tasks = db.query(Task).filter(Task.topic_id == topic.id).order_by(Task.created_at).all()

        # Rebuild task_link and update task.order for each task
        for index, task in enumerate(tasks, start=1):
            new_task_link = f"{topic.id}-{index}"
            task.task_link = new_task_link  # Update the task_link
            task.order = index  # Update the task order

        # Commit the changes to the database
        db.commit()

    return {"status": "Task links and order successfully rebuilt"}



@router.get("/api/lessons/{lesson_id}/full_data")
def get_full_lesson_data(lesson_id: int):
    db: Session = SessionLocal()
    try:
        # Get lesson and user by ID
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        # user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        # if not user:
        #     raise HTTPException(status_code=404, detail="User not found")

        # Determine if the user is a student and only fetch active tasks if so
        # is_student = user.status == "STUDENT"

        # Get all topics and summaries for the lesson
        topics = list(db.query(Topic).filter(Topic.lesson_id == lesson_id).order_by(Topic.topic_order).all())
        summaries = list(
            db.query(Summary)
            .join(Topic, Summary.topic_id == Topic.id)
            .filter(Topic.lesson_id == lesson_id)
            .all()
        )

        # Get tasks, filtering active tasks only for students
        task_query = db.query(Task).filter(Task.topic_id.in_([topic.id for topic in topics]))
        # if is_student:
        #     task_query = task_query.filter(Task.is_active == True)

        tasks = list(task_query.order_by(Task.topic_id, Task.order).all())

        # Fetch user's solved task IDs
        # solved_task_ids = {
        #     solution.task_id for solution in db.query(TaskSolution).filter(TaskSolution.user_id == user.id).all()
        # }

        # Build JSON-serializable lesson data
        lesson_data = {
            "lesson": {
                "id": lesson.id,
                "title": lesson.title,
                "topics": []
            },
            "summaries": [
                {
                    "id": summary.id,
                    "title": summary.lesson_name,
                    "data": summary.data,
                    "topic_id": summary.topic_id,
                    "topic_title": db.query(Topic.title).filter(Topic.id == summary.topic_id).scalar() 
                }
                for summary in summaries
            ],
        }

        # Organize topics and tasks, then calculate cross-topic navigation links
        all_tasks = []
        topic_data_list = []
        for topic in topics:
            topic_tasks = [
                {
                    "id": task.id,
                    "order": task.order,
                    "title": task.task_name,
                    "type": task.type,
                    "data": task.data,
                    "points": task.points,
                    "is_active": task.is_active,  # Pass is_active status
                    # "is_solved": task.id in solved_task_ids,  # Mark as solved if in user's solved tasks
                    "task_link": task.task_link,
                    "prevUrl": None,  # Initialize with None, will update later
                    "nextUrl": None
                }
                for task in tasks if task.topic_id == topic.id
            ]
            all_tasks.extend(topic_tasks)

            topic_data = {
                "id": topic.id,
                "title": topic.title,
                "tasks": topic_tasks,
            }
            topic_data_list.append(topic_data)

        # Set prevUrl and nextUrl for all tasks in `all_tasks`
        for i, task_data in enumerate(all_tasks):
            if i > 0:
                task_data["prevUrl"] = all_tasks[i - 1]["task_link"]
            if i < len(all_tasks) - 1:
                task_data["nextUrl"] = all_tasks[i + 1]["task_link"]

        # Assign updated tasks with navigation back to topic_data_list
        for topic_data in topic_data_list:
            for task_data in topic_data["tasks"]:
                matching_task = next((t for t in all_tasks if t["id"] == task_data["id"]), None)
                if matching_task:
                    task_data["prevUrl"] = matching_task["prevUrl"]
                    task_data["nextUrl"] = matching_task["nextUrl"]

        lesson_data["lesson"]["topics"] = topic_data_list

        return lesson_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
