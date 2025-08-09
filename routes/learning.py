"""
Learning Content Service Router
Handles the hierarchical course structure: courses → lessons → topics → tasks
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import func
from typing import List, Optional
from pydantic import BaseModel

from models import (
    Course, Lesson, Topic, Task, Summary, TaskSolution, User,
    CodeTask, MultipleSelectQuiz, TrueFalseQuiz, SingleQuestionTask
)
from db import get_db
from utils.logging_config import logger
from schemas.validation import TaskUpdateSchema

router = APIRouter()


# Pydantic models for responses
class TaskResponse(BaseModel):
    id: int
    task_name: str
    task_type: str
    points: int
    order: int
    data: dict = None
    
    class Config:
        from_attributes = True


class TopicResponse(BaseModel):
    id: int
    title: str
    background: str = None
    objectives: str = None
    content_file_md: str = None
    concepts: str = None
    topic_order: int
    tasks: List[TaskResponse] = []
    
    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    id: int
    title: str
    description: str = None
    lesson_order: int
    textbook: str = None
    start_date: datetime = None
    topics: List[TopicResponse] = []
    
    class Config:
        from_attributes = True


class CourseResponse(BaseModel):
    id: int
    title: str
    description: str = None
    created_at: datetime
    updated_at: datetime
    professor_id: int
    lessons: List[LessonResponse] = []
    
    class Config:
        from_attributes = True


# Course level endpoints
@router.get("/", summary="List all courses")
async def get_courses(db: Session = Depends(get_db)):
    """Get all courses with basic information"""
    try:
        courses = db.query(Course).all()
        return [{
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "created_at": course.created_at,
            "professor_id": course.professor_id
        } for course in courses]
    except Exception as e:
        logger.error(f"Error retrieving courses: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{course_id}", response_model=CourseResponse, summary="Get course details")
async def get_course(
    course_id: int = Path(..., description="Course ID"), 
    db: Session = Depends(get_db)
):
    """Get course details with full lesson/topic/task hierarchy"""
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(status_code=404, detail="Course not found")

        # Build the hierarchical response
        course_data = {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
            "professor_id": course.professor_id,
            "lessons": []
        }
        
        for lesson in course.lessons:
            lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "lesson_order": lesson.lesson_order,
                "textbook": lesson.textbook,
                "start_date": lesson.start_date,
                "topics": []
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
                    "tasks": []
                }
                
                for task in topic.tasks.order_by(Task.order):
                    task_data = {
                        "id": task.id,
                        "task_name": task.task_name,
                        "task_type": task.task_type,
                        "points": task.points,
                        "order": task.order,
                        "data": task.data
                    }
                    topic_data["tasks"].append(task_data)
                
                lesson_data["topics"].append(topic_data)
            
            course_data["lessons"].append(lesson_data)
        
        return course_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_course: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Legacy endpoint for compatibility (mirrors current /api/courses/{course_id})  
@router.get("/{course_id}/legacy", summary="Get course data (legacy format)")
async def get_course_legacy_format(course_id: int, db: Session = Depends(get_db)):
    """
    Legacy format endpoint for backward compatibility
    Returns the same format as the original /api/courses/{course_id}
    """
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
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
                        {"listItem": "Gain proficiency in Python programming, including variables, assignments, loops, and conditional statements."},
                        {"listItem": "Use Python data structures like lists, stacks, queues, sets, and dictionaries to organize and manipulate information.."},
                        {"listItem": "Implement various algorithms—including brute-force, recursive, divide and conquer, dynamic programming, and greedy algorithms—in Python."},
                        {"listItem": "Analyze the computational cost and complexity of algorithms to understand the limits of computation."},
                        {"listItem": "Apply algorithms to data structures such as trees and graphs to solve complex problems in the digital humanities."},
                        {"listItem": "Develop and implement algorithms from scratch using flowcharts and pseudocode."},
                        {"listItem": "Build a portfolio of Python programs that address computational tasks relevant to digital humanities projects.."},
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
                                for topic in lesson.topics
                            ],
                        }
                        for lesson in course.lessons
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
                        {
                            "id": 1,
                            "img": "/images/client/avatar-02.png",
                            "name": "Silvio Peroni",
                            "type": "Director of Second Cycle Degree in Digital Humanities and Digital Knowledge",
                            "desc": "Associate Professor / Department of Classical Philology and Italian Studies",
                            "social": [
                                {"link": "https://x.com/essepuntato", "icon": "twitter"},
                                {"link": "https://www.linkedin.com/in/essepuntato/", "icon": "linkedin"},
                            ],
                        }
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
async def get_course_lessons(
    course_id: int = Path(..., description="Course ID"),
    db: Session = Depends(get_db)
):
    """Get all lessons for a specific course"""
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
            
        lessons = db.query(Lesson).filter(Lesson.course_id == course_id).order_by(Lesson.lesson_order).all()
        
        return [{
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "lesson_order": lesson.lesson_order,
            "textbook": lesson.textbook,
            "start_date": lesson.start_date
        } for lesson in lessons]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lessons for course {course_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{course_id}/lessons/{lesson_id}", summary="Get lesson details")
async def get_lesson(
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    db: Session = Depends(get_db)
):
    """Get lesson details with topics and tasks"""
    try:
        lesson = db.query(Lesson).filter(
            Lesson.id == lesson_id,
            Lesson.course_id == course_id
        ).first()
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        lesson_data = {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "lesson_order": lesson.lesson_order,
            "textbook": lesson.textbook,
            "start_date": lesson.start_date,
            "topics": []
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
                "tasks": []
            }
            
            for task in topic.tasks.order_by(Task.order):
                task_data = {
                    "id": task.id,
                    "task_name": task.task_name,
                    "task_type": task.task_type,
                    "points": task.points,
                    "order": task.order,
                    "data": task.data
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
    db: Session = Depends(get_db)
):
    """Get all topics for a specific lesson"""
    try:
        # Verify lesson exists and belongs to course
        lesson = db.query(Lesson).filter(
            Lesson.id == lesson_id,
            Lesson.course_id == course_id
        ).first()
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
            
        topics = db.query(Topic).filter(Topic.lesson_id == lesson_id).order_by(Topic.topic_order).all()
        
        return [{
            "id": topic.id,
            "title": topic.title,
            "background": topic.background,
            "objectives": topic.objectives,
            "content_file_md": topic.content_file_md,
            "concepts": topic.concepts,
            "topic_order": topic.topic_order
        } for topic in topics]
        
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
    db: Session = Depends(get_db)
):
    """Get topic details with tasks"""
    try:
        # Verify the full hierarchy
        topic = db.query(Topic).join(Lesson).filter(
            Topic.id == topic_id,
            Topic.lesson_id == lesson_id,
            Lesson.course_id == course_id
        ).first()
        
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
            "tasks": []
        }
        
        for task in topic.tasks.order_by(Task.order):
            task_data = {
                "id": task.id,
                "task_name": task.task_name,
                "task_type": task.task_type,
                "points": task.points,
                "order": task.order,
                "data": task.data
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
    db: Session = Depends(get_db)
):
    """Get all tasks for a specific topic"""
    try:
        # Verify the full hierarchy
        topic = db.query(Topic).join(Lesson).filter(
            Topic.id == topic_id,
            Topic.lesson_id == lesson_id,
            Lesson.course_id == course_id
        ).first()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
            
        tasks = db.query(Task).filter(Task.topic_id == topic_id).order_by(Task.order).all()
        
        return [{
            "id": task.id,
            "task_name": task.task_name,
            "task_type": task.task_type,
            "points": task.points,
            "order": task.order,
            "data": task.data
        } for task in tasks]
        
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
    db: Session = Depends(get_db)
):
    """Get task details"""
    try:
        # Verify the full hierarchy
        task = db.query(Task).join(Topic).join(Lesson).filter(
            Task.id == task_id,
            Task.topic_id == topic_id,
            Topic.lesson_id == lesson_id,
            Lesson.course_id == course_id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "id": task.id,
            "task_name": task.task_name,
            "task_type": task.task_type,
            "points": task.points,
            "order": task.order,
            "data": task.data,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Task management endpoints (for professors)
@router.put("/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/{task_id}", summary="Update task")
async def update_task(
    task_data: TaskUpdateSchema,
    course_id: int = Path(..., description="Course ID"),
    lesson_id: int = Path(..., description="Lesson ID"),
    topic_id: int = Path(..., description="Topic ID"),
    task_id: int = Path(..., description="Task ID"),
    db: Session = Depends(get_db)
):
    """
    Update task data - migrated from original task.py
    """
    try:
        # Verify the full hierarchy
        task = db.query(Task).join(Topic).join(Lesson).filter(
            Task.id == task_id,
            Task.topic_id == topic_id,
            Topic.lesson_id == lesson_id,
            Lesson.course_id == course_id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update the JSON field based on task type
        task_json = task.data.copy() if task.data else {}
        
        if task.task_type == "MultipleSelectQuiz":
            task_json["question"] = task_data.newQuestion
            task_json["options"] = [{"id": str(i + 1), "name": option["name"]} for i, option in enumerate(task_data.newOptions)]
            task_json["correctAnswers"] = task_data.newCorrectAnswers

        task.data = task_json
        task.updated_at = func.now()

        db.commit()
        logger.info(f"Task {task_id} updated successfully")
        
        return {"message": "Task updated successfully", "task_id": task_id}
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in update_task: {e}")
        raise HTTPException(status_code=409, detail="Task update conflict")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in update_task: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in update_task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")