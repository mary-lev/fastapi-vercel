"""
Learning Content Service Router
Handles the hierarchical course structure: courses → lessons → topics → tasks
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from typing import List, Optional
from pydantic import BaseModel

from models import Course, Lesson, Topic, Task, Summary
from db import get_db
from utils.structured_logging import get_logger, LogCategory
from utils.cache_manager import cache_manager, cache_key_for_course, invalidate_course_cache

logger = get_logger("routes.learning")
from schemas.validation import TaskUpdateSchema
from config import settings
import json

router = APIRouter()


# Pydantic models for responses
class TaskResponse(BaseModel):
    id: int
    task_name: str
    type: str  # Field name matches database column
    points: Optional[int] = None
    order: int
    data: Optional[dict] = None

    class Config:
        from_attributes = True


class TopicResponse(BaseModel):
    id: int
    title: str
    background: Optional[str] = None
    objectives: Optional[str] = None
    content_file_md: Optional[str] = None
    concepts: Optional[str] = None
    topic_order: int
    tasks: List[TaskResponse] = []

    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    lesson_order: int
    textbook: Optional[str] = None
    start_date: Optional[datetime] = None
    topics: List[TopicResponse] = []

    class Config:
        from_attributes = True


class CourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    professor_id: int
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True


# Course level endpoints
@router.get(
    "/", 
    summary="List All Courses",
    description="Retrieve a comprehensive list of all available courses with enrollment information",
    response_description="List of courses with basic information and enrollment status",
    responses={
        200: {
            "description": "Courses retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "title": "Computational Thinking and Programming",
                            "description": "Introduction to programming concepts using Python",
                            "created_at": "2024-01-15T10:30:00Z",
                            "professor_id": 1
                        }
                    ]
                }
            }
        }
    }
)
async def get_courses(db: Session = Depends(get_db)):
    """
    ## List All Available Courses
    
    Retrieves a comprehensive list of all courses available in the educational platform.
    
    ### Returns:
    - **Course ID**: Unique identifier for the course
    - **Title**: Course name and subject area
    - **Description**: Detailed course overview
    - **Creation Date**: When the course was created
    - **Professor ID**: Course instructor identifier
    
    ### Use Cases:
    - Course catalog display
    - Enrollment selection
    - Course discovery
    - Administrative overview
    
    ### Features:
    - Performance optimized with efficient queries
    - Includes all active courses
    - Basic course metadata for quick overview
    - **Cached for performance** (1 hour TTL)
    """
    try:
        # Check cache first
        cache_key = "courses:list:all"
        cached_courses = cache_manager.get(cache_key)
        
        if cached_courses is not None:
            logger.debug(
                "Returning cached course list",
                category=LogCategory.PERFORMANCE,
                extra={"cache_hit": True, "count": len(cached_courses)}
            )
            return cached_courses
        
        # Query database
        courses = db.query(Course).all()
        result = [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "created_at": course.created_at,
                "professor_id": course.professor_id,
            }
            for course in courses
        ]
        
        # Cache the result
        cache_manager.set(cache_key, result, ttl=3600)  # 1 hour cache
        
        logger.info(
            "Course list fetched and cached",
            category=LogCategory.PERFORMANCE,
            extra={"cache_hit": False, "count": len(result)}
        )
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving courses: {e}", category=LogCategory.ERROR, exception=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{course_id}", response_model=CourseResponse, summary="Get course details")
async def get_course(course_id: int = Path(..., description="Course ID"), db: Session = Depends(get_db)):
    """Get course details with full lesson/topic/task hierarchy - cached for performance"""
    try:
        # Check cache first
        cache_key = cache_key_for_course(course_id, "full_details")
        cached_course = cache_manager.get(cache_key)
        
        if cached_course is not None:
            logger.debug(
                f"Returning cached course details",
                category=LogCategory.PERFORMANCE,
                extra={"cache_hit": True, "course_id": course_id}
            )
            return cached_course
        
        # Use eager loading to prevent N+1 queries
        course = (
            db.query(Course)
            .options(joinedload(Course.lessons).joinedload(Lesson.topics).joinedload(Topic.tasks))
            .filter(Course.id == course_id)
            .first()
        )
        if not course:
            logger.warning(f"Course not found: {course_id}", category=LogCategory.BUSINESS)
            raise HTTPException(status_code=404, detail="Course not found")

        # Build the hierarchical response
        course_data = {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
            "professor_id": course.professor_id,
            "lessons": [],
        }

        for lesson in course.lessons:
            lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "lesson_order": lesson.lesson_order,
                "textbook": lesson.textbook,
                "start_date": lesson.start_date,
                "topics": [],
            }

            for topic in lesson.topics:
                topic_data = {
                    "id": topic.id,
                    "title": topic.title,
                    "background": topic.background,
                    "objectives": topic.objectives,
                    "content_file_md": topic.content_file_md,
                    "concepts": topic.concepts,
                    "topic_order": topic.topic_order,
                    "tasks": [],
                }

                for task in topic.tasks.order_by(Task.order):
                    task_data = {
                        "id": task.id,
                        "task_name": task.task_name,
                        "type": task.type,
                        "points": task.points,
                        "order": task.order,
                        "data": task.data,
                    }
                    topic_data["tasks"].append(task_data)

                lesson_data["topics"].append(topic_data)

            course_data["lessons"].append(lesson_data)

        # Cache the result for 30 minutes
        cache_manager.set(cache_key, course_data, ttl=1800)
        
        logger.info(
            f"Course details fetched and cached",
            category=LogCategory.PERFORMANCE,
            extra={"cache_hit": False, "course_id": course_id}
        )

        return course_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_course: {e}", category=LogCategory.ERROR, exception=e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Legacy endpoint for compatibility (mirrors current /api/courses/{course_id})
@router.get("/{course_id}/legacy", summary="Get course data (legacy format)")
async def get_course_legacy_format(course_id: int, db: Session = Depends(get_db)):
    """
    Legacy format endpoint for backward compatibility
    Returns the same format as the original /api/courses/{course_id}
    """
    try:
        # Use eager loading for the entire hierarchy to prevent N+1 queries
        course = (
            db.query(Course)
            .options(joinedload(Course.lessons).joinedload(Lesson.topics))
            .filter(Course.id == course_id)
            .first()
        )
        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(status_code=404, detail="Course not found")

        logger.info(f"Course data retrieved: {course_id}")

        return {
            "id": course.id,
            "courseTitle": course.title,
            "desc": course.description,
            "userImg": "/images/client/avatar-02.png",
            "userName": " Silvio Peroni ",
            "userCategory": "DHDK",
            "courseOverview": [
                {
                    "title": "What you'll learn",
                    "desc": "At the end of the course, the student knows the high-level principles, as well as the historical and theoretical backgrounds, for solving problems efficiently by using computational tools and information-processing agents. The student is able to understand and use the main data structures for organising information, to develop algorithms for addressing computational-related tasks, and to implement such algorithms in a specific programming language.",
                    "descTwo": "The course is organised in a series of lectures. Each lecture introduces a specific topic, includes mentions to some related historical facts and to people (indicated between squared brackets) who have provided interesting insights on the subject. The lectures are accompanied by several hands-on sessions for learning the primary constructs of the programming language that will be used for implementing and running the various algorithms proposed.",
                    "overviewList": [
                        {"listItem": "Understand and apply the principles of computational thinking and abstraction."},
                        {
                            "listItem": "Gain proficiency in Python programming, including variables, assignments, loops, and conditional statements."
                        },
                        {
                            "listItem": "Use Python data structures like lists, stacks, queues, sets, and dictionaries to organize and manipulate information.."
                        },
                        {
                            "listItem": "Implement various algorithms—including brute-force, recursive, divide and conquer, dynamic programming, and greedy algorithms—in Python."
                        },
                        {
                            "listItem": "Analyze the computational cost and complexity of algorithms to understand the limits of computation."
                        },
                        {
                            "listItem": "Apply algorithms to data structures such as trees and graphs to solve complex problems in the digital humanities."
                        },
                        {"listItem": "Develop and implement algorithms from scratch using flowcharts and pseudocode."},
                        {
                            "listItem": "Build a portfolio of Python programs that address computational tasks relevant to digital humanities projects.."
                        },
                    ],
                }
            ],
            "courseContent": [
                {
                    "title": "Course Content",
                    "contentList": [
                        {
                            "id": lesson.id,
                            "title": lesson.title,
                            "time": lesson.start_date.strftime("%d/%m/%Y") if lesson.start_date else "TBD",
                            "collapsed": False,
                            "isShow": True,
                            "expand": True,
                            "listItem": [
                                {
                                    "text": topic.title,
                                    "status": lesson.start_date <= datetime.now() if lesson.start_date else False,
                                }
                                # Topics are already eagerly loaded
                                for topic in sorted(lesson.topics, key=lambda t: t.topic_order)
                            ],
                        }
                        # Lessons are already eagerly loaded
                        for lesson in sorted(course.lessons, key=lambda l: l.lesson_order)
                    ],
                }
            ],
            "courseRequirement": [
                {
                    "title": "Requirements",
                    "detailsList": [
                        {"listItem": "No prior programming experience needed."},
                        {"listItem": "Basic computer skills"},
                        {"listItem": "Interest in Digital Humanities"},
                        {"listItem": "Willingness to participate actively"},
                    ],
                },
                {
                    "title": "Description",
                    "detailsList": [
                        {"listItem": "Learn the fundamentals of computational thinking and problem-solving."},
                        {"listItem": "Develop proficiency in Python programming from scratch."},
                        {"listItem": "Implement algorithms and data structures to organize and process information."},
                        {"listItem": "Apply computational methods to address tasks in the digital humanities."},
                    ],
                },
            ],
            "courseInstructor": [
                {
                    "title": "Professor",
                    "body": [
                        # TODO: Replace with database query for professor information
                        json.loads(settings.PROFESSOR_INFO)
                    ],
                }
            ],
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_course_legacy_format: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        logger.error(f"Unexpected error in get_course_legacy_format: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Lesson level endpoints
@router.get("/{course_id}/lessons/", summary="List course lessons")
async def get_course_lessons(course_id: int = Path(..., description="Course ID"), db: Session = Depends(get_db)):
    """Get all lessons for a specific course"""
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        lessons = db.query(Lesson).filter(Lesson.course_id == course_id).order_by(Lesson.lesson_order).all()

        return [
            {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "lesson_order": lesson.lesson_order,
                "textbook": lesson.textbook,
                "start_date": lesson.start_date,
            }
            for lesson in lessons
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lessons for course {course_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{course_id}/lessons/{lesson_id}", summary="Get lesson details")
async def get_lesson(
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    db: Session = Depends(get_db),
):
    """Get lesson details with topics and tasks"""
    try:
        # Use eager loading to prevent N+1 queries when accessing topics and tasks
        lesson = (
            db.query(Lesson)
            .options(joinedload(Lesson.topics).joinedload(Topic.tasks))
            .filter(Lesson.id == lesson_id, Lesson.course_id == course_id)
            .first()
        )

        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        lesson_data = {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "lesson_order": lesson.lesson_order,
            "textbook": lesson.textbook,
            "start_date": lesson.start_date,
            "topics": [],
        }

        # Topics and tasks are already eagerly loaded, so no additional queries
        for topic in sorted(lesson.topics, key=lambda t: t.topic_order):
            topic_data = {
                "id": topic.id,
                "title": topic.title,
                "background": topic.background,
                "objectives": topic.objectives,
                "content_file_md": topic.content_file_md,
                "concepts": topic.concepts,
                "topic_order": topic.topic_order,
                "tasks": [],
            }

            # Sort tasks in Python to avoid additional query
            for task in sorted(topic.tasks, key=lambda t: t.order):
                task_data = {
                    "id": task.id,
                    "task_name": task.task_name,
                    "type": task.type,
                    "points": task.points,
                    "order": task.order,
                    "data": task.data,
                }
                topic_data["tasks"].append(task_data)

            lesson_data["topics"].append(topic_data)

        return lesson_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lesson {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Topic level endpoints
@router.get("/{course_id}/lessons/{lesson_id}/topics/", summary="List lesson topics")
async def get_lesson_topics(
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    db: Session = Depends(get_db),
):
    """Get all topics for a specific lesson"""
    try:
        # Verify lesson exists and belongs to course
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first()

        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        topics = db.query(Topic).filter(Topic.lesson_id == lesson_id).order_by(Topic.topic_order).all()

        return [
            {
                "id": topic.id,
                "title": topic.title,
                "background": topic.background,
                "objectives": topic.objectives,
                "content_file_md": topic.content_file_md,
                "concepts": topic.concepts,
                "topic_order": topic.topic_order,
            }
            for topic in topics
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving topics for lesson {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{course_id}/lessons/{lesson_id}/topics/{topic_id}", summary="Get topic details")
async def get_topic(
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    topic_id: int = Path(..., description="Topic ID"),
    db: Session = Depends(get_db),
):
    """Get topic details with tasks"""
    try:
        # Verify the full hierarchy with eager loading for tasks
        topic = (
            db.query(Topic)
            .options(joinedload(Topic.tasks))
            .join(Lesson)
            .filter(Topic.id == topic_id, Topic.lesson_id == lesson_id, Lesson.course_id == course_id)
            .first()
        )

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        topic_data = {
            "id": topic.id,
            "title": topic.title,
            "background": topic.background,
            "objectives": topic.objectives,
            "content_file_md": topic.content_file_md,
            "concepts": topic.concepts,
            "topic_order": topic.topic_order,
            "tasks": [],
        }

        # Tasks are already eagerly loaded, sort in Python
        for task in sorted(topic.tasks, key=lambda t: t.order):
            task_data = {
                "id": task.id,
                "task_name": task.task_name,
                "type": task.type,
                "points": task.points,
                "order": task.order,
                "data": task.data,
            }
            topic_data["tasks"].append(task_data)

        return topic_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Task level endpoints
@router.get("/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/", summary="List topic tasks")
async def get_topic_tasks(
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    topic_id: int = Path(..., description="Topic ID"),
    db: Session = Depends(get_db),
):
    """Get all tasks for a specific topic"""
    try:
        # Verify the full hierarchy
        topic = (
            db.query(Topic)
            .join(Lesson)
            .filter(Topic.id == topic_id, Topic.lesson_id == lesson_id, Lesson.course_id == course_id)
            .first()
        )

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        tasks = db.query(Task).filter(Task.topic_id == topic_id).order_by(Task.order).all()

        return [
            {
                "id": task.id,
                "task_name": task.task_name,
                "type": task.type,
                "points": task.points,
                "order": task.order,
                "data": task.data,
            }
            for task in tasks
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tasks for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/{task_id}", summary="Get task details")
async def get_task(
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    topic_id: int = Path(..., description="Topic ID"),
    task_id: int = Path(..., description="Task ID"),
    db: Session = Depends(get_db),
):
    """Get task details"""
    try:
        # Verify the full hierarchy
        task = (
            db.query(Task)
            .join(Topic)
            .join(Lesson)
            .filter(
                Task.id == task_id,
                Task.topic_id == topic_id,
                Topic.lesson_id == lesson_id,
                Lesson.course_id == course_id,
            )
            .first()
        )

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "id": task.id,
            "task_name": task.task_name,
            "type": task.type,
            "points": task.points,
            "order": task.order,
            "data": task.data,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Get summaries for a lesson
@router.get("/{course_id}/lessons/{lesson_id}/summaries", summary="Get lesson summaries")
async def get_lesson_summaries(
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    db: Session = Depends(get_db),
):
    """
    Get summaries for all topics in a lesson
    """
    from sqlalchemy.orm import joinedload

    # Verify course and lesson exist
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.course_id == course_id).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get summaries for the lesson
    summaries = (
        db.query(Summary)
        .join(Topic, Summary.topic_id == Topic.id)
        .filter(Topic.lesson_id == lesson_id)
        .options(joinedload(Summary.topic))
        .all()
    )

    # Format response
    summaries_data = []
    for summary in summaries:
        summaries_data.append(
            {
                "id": summary.id,
                "lesson_name": summary.lesson_name,
                "lesson_link": summary.lesson_link,
                "lesson_type": summary.lesson_type,
                "icon_file": summary.icon_file,
                "data": summary.data,
                "topic_id": summary.topic_id,
                "topic_title": summary.topic.title,
                "created_at": summary.created_at,
            }
        )

    return {"summaries": summaries_data}


# Task management endpoints (for professors)
@router.put("/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/{task_id}", summary="Update task")
async def update_task(
    task_data: TaskUpdateSchema,
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    topic_id: int = Path(..., description="Topic ID"),
    task_id: int = Path(..., description="Task ID"),
    db: Session = Depends(get_db),
):
    """
    Update task data - migrated from original task.py
    """
    try:
        # Verify the full hierarchy
        task = (
            db.query(Task)
            .join(Topic)
            .join(Lesson)
            .filter(
                Task.id == task_id,
                Task.topic_id == topic_id,
                Topic.lesson_id == lesson_id,
                Lesson.course_id == course_id,
            )
            .first()
        )

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update the JSON field based on task type
        task_json = task.data.copy() if task.data else {}

        if task.type == "MultipleSelectQuiz":
            task_json["question"] = task_data.newQuestion
            task_json["options"] = [
                {"id": str(i + 1), "name": option["name"]} for i, option in enumerate(task_data.newOptions)
            ]
            task_json["correctAnswers"] = task_data.newCorrectAnswers

        task.data = task_json
        task.updated_at = func.now()

        db.commit()
        logger.info(f"Task {task_id} updated successfully")

        return {"message": "Task updated successfully", "task_id": task_id}

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in update_task: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in update_task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
