from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.sql import func, case
from sqlalchemy.orm import Session
from models import Task, TaskSolution, TaskAttempt, User, Lesson, Topic, Course  # Adjust model imports as needed
from db import SessionLocal

router = APIRouter()

@router.post("/api/insertTaskSolution")
async def insert_task_solution(request: Request):
    db: Session = SessionLocal()
    try:
        data = await request.json()
        internal_user_id = data.get("userId")  # UUID from the frontend
        task_link = data.get("lessonName")
        is_successful = data.get("isSuccessful", False)  # Whether the attempt was successful
        solution_content = data.get("solutionContent", "")  # Solution content from the frontend

        # Validate input
        if not internal_user_id or not task_link:
            raise HTTPException(status_code=400, detail="Invalid input data")

        # Fetch the user ID using the UUID from the User model
        user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get the task by task link
        task = db.query(Task).filter(Task.task_link == task_link).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Fetch the number of previous attempts for this user-task pair
        attempt_count = db.query(TaskAttempt).filter(
            TaskAttempt.user_id == user.id,
            TaskAttempt.task_id == task.id
        ).count()

        # Record the task attempt, including the attempt content
        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=task.id,
            attempt_number=attempt_count + 1,
            is_successful=is_successful,
            attempt_content=solution_content,  # Store the attempt content
            submitted_at=func.now()
        )

        db.add(task_attempt)
        
        # If the attempt is successful and no solution exists, save it as a completed task
        if is_successful:
            existing_solution = db.query(TaskSolution).filter(
                TaskSolution.user_id == user.id,
                TaskSolution.task_id == task.id
            ).first()

            if not existing_solution:
                task_solution = TaskSolution(
                    user_id=user.id,
                    task_id=task.id,
                    solution_content=solution_content,  # Store the content of the successful attempt
                    completed_at=func.now()
                )
                db.add(task_solution)

        db.commit()

        return {"message": "Task attempt recorded successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.get("/api/getTopicSolutions/{internal_user_id}")
def get_topic_solutions(internal_user_id: str):
    db: Session = SessionLocal()
    try:
        # Fetch the user by internal_user_id
        user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Query to aggregate task solutions by topic, ordered by topic_order
        topic_solutions = (
            db.query(
                Lesson.id.label("lesson_id"),  # Use lesson_id instead of topic_id
                Topic.topic_order.label("topic_order"),
                Lesson.start_date.label("lesson_start_date"),
                Topic.title.label("topic_name"),
                func.count(Task.id).label("total_tasks"),  # Total tasks in topic
                func.sum(Task.points).label("total_possible_points"),  # Total points in topic
                func.count(case((TaskSolution.id.isnot(None), 1))).label("solved_tasks"),  # Solved tasks by user
                func.coalesce(func.sum(case((TaskSolution.id.isnot(None), Task.points), else_=0)), 0).label("points_obtained")  # Points obtained by user
            )
            .join(Task, Task.topic_id == Topic.id)
            .join(Lesson, Lesson.id == Topic.lesson_id)
            .outerjoin(
                TaskSolution,
                (TaskSolution.task_id == Task.id) & (TaskSolution.user_id == user.id)
            )
            .group_by(Lesson.id, Topic.id, Lesson.start_date, Topic.title, Topic.topic_order)
            .order_by(Topic.id)  # Sort by topic_order
            .all()
        )

        # Format the results as a list of dictionaries
        topic_solution_list = [
            {
                "lesson_id": topic.lesson_id,
                "lesson_start_date": topic.lesson_start_date,
                "topic_name": topic.topic_name,
                "total_tasks": topic.total_tasks,
                "total_possible_points": topic.total_possible_points,
                "solved_tasks": topic.solved_tasks,
                "points_obtained": topic.points_obtained,
            }
            for topic in topic_solutions
        ]

        return {"topics": topic_solution_list}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.get("/api/getCourseTaskOverview/{course_id}")
def get_course_task_overview(course_id: int):
    db: Session = SessionLocal()
    try:
        # Check if the course exists
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Query to aggregate task attempts and solutions for each task grouped by topic
        task_overview = (
            db.query(
                Topic.id.label("topic_id"),
                Topic.title.label("topic_name"),
                Topic.lesson_id.label("lesson_id"),
                Task.id.label("task_id"),
                Task.task_name.label("task_name"),
                Task.task_link.label("task_link"),
                func.count(TaskAttempt.id).label("total_attempts"),  # Total attempts made
                func.count(case((TaskSolution.id.isnot(None), 1))).label("total_solutions")  # Completed tasks
            )
            .select_from(Course)  # Start from Course
            .join(Lesson, Lesson.course_id == Course.id)  # Explicit join to Lesson
            .join(Topic, Topic.lesson_id == Lesson.id)  # Explicit join to Topic
            .join(Task, Task.topic_id == Topic.id)  # Explicit join to Task
            .outerjoin(TaskSolution, TaskSolution.task_id == Task.id)  # Left join to TaskSolution
            .outerjoin(TaskAttempt, TaskAttempt.task_id == Task.id)  # Left join to TaskAttempt
            .filter(Course.id == course_id)  # Filter by course
            .group_by(Topic.id, Topic.title, Task.id, Task.task_name)
            .order_by(Topic.id, Task.id)
            .all()
        )

        # Format the results as a list of dictionaries
        task_overview_list = [
            {
                "lesson_id": row.lesson_id,
                "topic_id": row.topic_id,
                "topic_name": row.topic_name,
                "task_id": row.task_id,
                "task_name": row.task_name,
                "task_link": row.task_link,
                "total_attempts": row.total_attempts,
                "total_solutions": row.total_solutions,
            }
            for row in task_overview
        ]

        return {"tasks_by_topic": task_overview_list}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
