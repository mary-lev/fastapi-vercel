"""
Local Professor Content Management API
No authentication required - for local development only
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from db import get_db
from models import Course, Lesson, Topic, Task, CourseInstructor
from utils.task_generator import generate_tasks as ai_generate_tasks
from utils.structured_logging import get_logger
import json

logger = get_logger("professor_local")

router = APIRouter(prefix="/api/v1/professor", tags=["Local Professor Tools"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TaskReorderRequest(BaseModel):
    """Request to reorder tasks within a topic"""
    task_ids: List[int] = Field(..., description="Task IDs in new order")


class TaskGenerationRequest(BaseModel):
    """Enhanced task generation request with all options"""
    topic_id: int
    num_tasks: int = Field(5, ge=1, le=10)
    task_types: List[str] = ["code"]
    material_theme: Optional[str] = "general academic"
    difficulty: str = Field("mixed", pattern="^(easy|medium|hard|mixed)$")
    
    # Context options
    include_previous_lessons: bool = True  # Include concepts from previous lessons
    include_current_tasks: bool = True     # Consider existing tasks in this topic
    include_previous_topics: bool = True   # Include earlier topics in current lesson
    
    # Additional context
    custom_instructions: Optional[str] = None  # Professor's custom instructions
    additional_materials: Optional[str] = None  # Extra materials/examples to consider
    focus_concepts: Optional[List[str]] = None  # Specific concepts to emphasize
    avoid_concepts: Optional[List[str]] = None  # Concepts to avoid (not yet taught)
    
    # Output options
    preview_only: bool = True  # Don't save to database immediately


class BulkTaskCreate(BaseModel):
    """Create multiple tasks at once"""
    tasks: List[Dict[str, Any]]
    topic_id: int
    auto_order: bool = True  # Automatically assign order numbers


# ============================================================================
# COURSE BROWSING ENDPOINTS
# ============================================================================

@router.get("/courses")
async def get_all_courses(db: Session = Depends(get_db)):
    """Get all courses for local editing"""
    courses = db.query(Course).options(
        joinedload(Course.instructors),
        joinedload(Course.lessons)
    ).all()
    
    return [{
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "course_overview": c.course_overview,
        "learning_objectives": c.learning_objectives or [],
        "lesson_count": len(c.lessons),
        "instructor": c.instructors[0].name if c.instructors else "No instructor",
        "enrollment_status": c.get_enrollment_status() if hasattr(c, 'get_enrollment_status') else "open"
    } for c in courses]


@router.get("/courses/{course_id}")
async def get_course(course_id: int, db: Session = Depends(get_db)):
    """Get single course with lessons"""
    course = db.query(Course).options(
        joinedload(Course.lessons).joinedload(Lesson.topics)
    ).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(404, "Course not found")
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "course_overview": course.course_overview,
        "learning_objectives": course.learning_objectives or [],
        "requirements": course.requirements or [],
        "lesson_count": len(course.lessons),
        "instructor": course.instructors[0].name if course.instructors else "No instructor",
        "lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "order": lesson.lesson_order,
                "topics": [
                    {
                        "id": topic.id,
                        "title": topic.title,
                        "background": topic.background,
                        "objectives": topic.objectives,
                        "concepts": topic.concepts,
                        "order": topic.topic_order,
                    } for topic in sorted(lesson.topics, key=lambda t: t.topic_order)
                ]
            } for lesson in sorted(course.lessons, key=lambda l: l.lesson_order)
        ]
    }


@router.get("/lessons/{lesson_id}/topics")
async def get_lesson_topics(lesson_id: int, db: Session = Depends(get_db)):
    """Get all topics for a lesson"""
    lesson = db.query(Lesson).options(
        joinedload(Lesson.topics)
    ).filter(Lesson.id == lesson_id).first()
    
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    
    return [
        {
            "id": topic.id,
            "title": topic.title,
            "background": topic.background,
            "objectives": topic.objectives,
            "concepts": topic.concepts,
            "order": topic.topic_order,
        } for topic in sorted(lesson.topics, key=lambda t: t.topic_order)
    ]


@router.get("/topics/{topic_id}/tasks")
async def get_topic_tasks(topic_id: int, db: Session = Depends(get_db)):
    """Get all tasks for a topic"""
    topic = db.query(Topic).options(
        joinedload(Topic.tasks)
    ).filter(Topic.id == topic_id).first()
    
    if not topic:
        raise HTTPException(404, "Topic not found")
    
    return [
        {
            "id": task.id,
            "task_name": task.task_name,
            "type": task.type,
            "points": task.points,
            "is_active": task.is_active,
            "order": task.order,
            "data": task.data,
        } for task in sorted(topic.tasks, key=lambda t: t.order)
    ]


@router.post("/tasks/generate")
async def generate_tasks_for_react(
    params: dict,
    db: Session = Depends(get_db)
):
    """Task generation endpoint that matches React app expectations"""
    try:
        logger.info(f"React app task generation for topic {params.get('topic_id')}")
        
        # Convert React params to our internal format
        request_data = {
            "topic_id": params.get("topic_id"),
            "num_tasks": params.get("num_tasks", 3),
            "task_types": params.get("task_types", ["code_task"]),
            "material_theme": params.get("material_theme", ""),
            "difficulty": params.get("difficulty", "beginner"),
            "include_previous_lessons": params.get("include_previous_lessons", False),
            "include_current_tasks": params.get("include_current_tasks", False),
            "include_previous_topics": params.get("include_previous_topics", False),
            "custom_instructions": params.get("custom_instructions", ""),
            "additional_materials": params.get("additional_materials", ""),
            "focus_concepts": params.get("focus_concepts", []),
            "avoid_concepts": params.get("avoid_concepts", []),
            "preview_only": params.get("preview_only", True),
        }
        
        # Use the existing task generation logic with correct parameters
        generated_tasks = ai_generate_tasks(
            topic_id=request_data["topic_id"],
            num_tasks=request_data["num_tasks"],
            add_quizzes=("true_false" in request_data["task_types"] or "multiple_select" in request_data["task_types"]),
            add_previous_tasks=request_data.get("include_current_tasks", False),
            material=request_data.get("material_theme", "general academic"),
            db=db
        )
        
        # Get topic info for response
        topic = db.query(Topic).filter(Topic.id == request_data["topic_id"]).first()
        existing_tasks_count = len(topic.tasks) if topic else 0
        
        # Format response to match React app expectations
        response = {
            "success": True,
            "tasks": [
                {
                    "lessonName": task["name"],
                    "lessonType": task["type"],
                    "points": task.get("points", 5),
                    "topic_id": request_data["topic_id"],
                    "data": task.get("data", {}),
                    "is_active": True,
                }
                for task in generated_tasks
            ],
            "count": len(generated_tasks),
            "topic_id": request_data["topic_id"],
            "topic_title": topic.title if topic else "Unknown Topic",
            "existing_tasks_count": existing_tasks_count,
            "context_used": {
                "previous_lessons": request_data.get("include_previous_lessons", False),
                "current_tasks": request_data.get("include_current_tasks", False),
                "previous_topics": request_data.get("include_previous_topics", False),
                "material_theme": request_data.get("material_theme", ""),
                "custom_instructions": bool(request_data.get("custom_instructions")),
            },
            "message": f"Generated {len(generated_tasks)} tasks successfully"
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in task generation: {str(e)}")
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "topic_id": params.get("topic_id"),
            "topic_title": "Unknown Topic",
            "existing_tasks_count": 0,
            "context_used": {},
            "message": f"Task generation failed: {str(e)}"
        }


@router.put("/topics/{topic_id}/tasks/reorder")
async def reorder_topic_tasks(
    topic_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    """Reorder tasks within a topic"""
    try:
        task_ids = data.get("task_ids", [])
        
        # Update task order based on position in array
        for index, task_id in enumerate(task_ids):
            task = db.query(Task).filter(Task.id == task_id, Task.topic_id == topic_id).first()
            if task:
                task.order = index + 1
        
        db.commit()
        
        return {"success": True, "message": "Tasks reordered successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error reordering tasks: {str(e)}")
        return {"success": False, "message": f"Failed to reorder tasks: {str(e)}"}


@router.get("/courses/{course_id}/full")
async def get_course_with_content(course_id: int, db: Session = Depends(get_db)):
    """Get complete course structure with all content"""
    course = db.query(Course).options(
        joinedload(Course.lessons).joinedload(Lesson.topics).joinedload(Topic.tasks)
    ).filter(Course.id == course_id).first()
    
    if not course:
        raise HTTPException(404, "Course not found")
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "course_overview": course.course_overview,
        "learning_objectives": course.learning_objectives or [],
        "requirements": course.requirements or [],
        "lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "order": lesson.lesson_order,
                "topics": [
                    {
                        "id": topic.id,
                        "title": topic.title,
                        "background": topic.background,
                        "objectives": topic.objectives,
                        "concepts": topic.concepts,
                        "order": topic.topic_order,
                        "tasks": sorted([
                            {
                                "id": task.id,
                                "task_name": task.task_name,
                                "type": task.type,
                                "points": task.points,
                                "is_active": task.is_active,
                                "order": task.order,
                                "data": task.data
                            }
                            for task in topic.tasks
                        ], key=lambda x: x["order"])  # Ensure tasks are sorted by order
                    }
                    for topic in sorted(lesson.topics, key=lambda x: x.topic_order)
                ]
            }
            for lesson in sorted(course.lessons, key=lambda x: x.lesson_order)
        ]
    }


# ============================================================================
# TASK GENERATION ENDPOINTS
# ============================================================================

@router.post("/generate-tasks")
async def generate_tasks_preview(
    request: TaskGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Enhanced task generation with full context control
    
    Features:
    - Include/exclude previous lessons
    - Include/exclude current tasks
    - Add custom instructions
    - Provide additional materials
    - Focus on specific concepts
    """
    try:
        logger.info(f"Generating tasks for topic {request.topic_id} with params: {request.dict()}")
        
        # Get topic information
        topic = db.query(Topic).filter(Topic.id == request.topic_id).first()
        if not topic:
            raise HTTPException(404, "Topic not found")
        
        # Build enhanced material string
        material = request.material_theme or "general academic"
        if request.additional_materials:
            material = f"{material}. Additional context: {request.additional_materials}"
        
        # Build custom instructions for the AI
        custom_context = []
        if request.custom_instructions:
            custom_context.append(f"Professor instructions: {request.custom_instructions}")
        if request.focus_concepts:
            custom_context.append(f"Focus on these concepts: {', '.join(request.focus_concepts)}")
        if request.avoid_concepts:
            custom_context.append(f"Avoid these concepts (not yet taught): {', '.join(request.avoid_concepts)}")
        
        # Enhance the material with custom context
        if custom_context:
            material = f"{material}. {' '.join(custom_context)}"
        
        # Generate tasks with all context options
        generated = ai_generate_tasks(
            topic_id=request.topic_id,
            num_tasks=request.num_tasks,
            material=material,
            add_quizzes="quiz" in request.task_types,
            add_previous_tasks=request.include_current_tasks,  # This includes existing tasks in prompt
            db=db if not request.preview_only else None  # Don't save if preview only
        )
        
        # Get existing tasks for comparison
        existing_tasks = db.query(Task).filter(Task.topic_id == request.topic_id).all()
        
        return {
            "success": True,
            "tasks": generated,
            "count": len(generated),
            "topic_id": request.topic_id,
            "topic_title": topic.title,
            "existing_tasks_count": len(existing_tasks),
            "context_used": {
                "previous_lessons": request.include_previous_lessons,
                "current_tasks": request.include_current_tasks,
                "previous_topics": request.include_previous_topics,
                "material_theme": request.material_theme,
                "custom_instructions": bool(request.custom_instructions)
            },
            "message": "Tasks generated successfully. Review and approve to save."
        }
        
    except Exception as e:
        logger.error(f"Error generating tasks: {str(e)}")
        raise HTTPException(500, f"Task generation failed: {str(e)}")


@router.post("/generate-tasks/advanced")
async def generate_tasks_with_full_context(
    topic_id: int = Body(...),
    num_tasks: int = Body(5),
    instructions: str = Body(None, description="Custom instructions for AI"),
    additional_context: str = Body(None, description="Additional materials or examples"),
    db: Session = Depends(get_db)
):
    """
    Advanced generation endpoint with maximum context
    Analyzes entire course structure to generate contextually appropriate tasks
    """
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    
    lesson = db.query(Lesson).filter(Lesson.id == topic.lesson_id).first()
    course = db.query(Course).filter(Course.id == lesson.course_id).first()
    
    # Get all previous content
    all_previous_tasks = []
    for prev_lesson in course.lessons:
        if prev_lesson.lesson_order <= lesson.lesson_order:
            for prev_topic in prev_lesson.topics:
                if prev_topic.id != topic_id:  # Don't include current topic
                    all_previous_tasks.extend([
                        {"task_name": t.task_name, "type": t.type}
                        for t in prev_topic.tasks
                    ])
    
    # Build comprehensive context
    context = {
        "course_title": course.title,
        "course_objectives": course.learning_objectives,
        "current_lesson": lesson.title,
        "current_topic": topic.title,
        "topic_concepts": topic.concepts,
        "previous_tasks_count": len(all_previous_tasks),
        "custom_instructions": instructions,
        "additional_context": additional_context
    }
    
    # Generate with full context
    material = f"Course: {course.title}. Lesson: {lesson.title}. "
    if instructions:
        material += f"Instructions: {instructions}. "
    if additional_context:
        material += f"Additional context: {additional_context}"
    
    generated = ai_generate_tasks(
        topic_id=topic_id,
        num_tasks=num_tasks,
        material=material,
        add_previous_tasks=True,
        db=None  # Preview only
    )
    
    return {
        "tasks": generated,
        "context": context,
        "message": "Tasks generated with full course context"
    }


# ============================================================================
# TASK MANAGEMENT ENDPOINTS
# ============================================================================

@router.put("/tasks/{task_id}")
async def update_task(
    task_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update an existing task"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(404, "Task not found")
        
        # Update allowed fields
        updateable_fields = ["task_name", "points", "is_active", "data", "order"]
        for field in updateable_fields:
            if field in data:
                setattr(task, field, data[field])
        
        # Collect data before commit to avoid detached instance issues
        task_response = {
            "id": task.id,
            "task_name": task.task_name,
            "order": task.order,
            "is_active": task.is_active,
            "points": task.points,
            "type": task.type,
            "data": task.data
        }
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Task {task_id} updated successfully",
            "task": task_response
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback on any other error
        db.rollback()
        raise HTTPException(500, f"Failed to update task: {str(e)}")


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    
    topic_id = task.topic_id
    db.delete(task)
    db.commit()
    
    # Reorder remaining tasks
    remaining_tasks = db.query(Task).filter(Task.topic_id == topic_id).order_by(Task.order).all()
    for idx, task in enumerate(remaining_tasks):
        task.order = idx + 1
    db.commit()
    
    return {"success": True, "message": f"Task {task_id} deleted"}


@router.post("/tasks/reorder")
async def reorder_tasks(
    request: TaskReorderRequest,
    db: Session = Depends(get_db)
):
    """
    Reorder tasks within a topic
    
    Accepts a list of task IDs in the desired order
    """
    # Validate all tasks exist and belong to the same topic
    tasks = db.query(Task).filter(Task.id.in_(request.task_ids)).all()
    
    if len(tasks) != len(request.task_ids):
        raise HTTPException(400, "Some task IDs not found")
    
    # Check all tasks belong to same topic
    topic_ids = set(t.topic_id for t in tasks)
    if len(topic_ids) > 1:
        raise HTTPException(400, "Tasks must belong to the same topic")
    
    # Update order based on position in the list
    task_map = {task.id: task for task in tasks}
    for new_order, task_id in enumerate(request.task_ids, 1):
        task_map[task_id].order = new_order
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Reordered {len(request.task_ids)} tasks",
        "new_order": request.task_ids
    }


@router.post("/tasks/bulk-create")
async def create_tasks_bulk(
    request: BulkTaskCreate,
    db: Session = Depends(get_db)
):
    """Save approved tasks to database with automatic ordering"""
    created_tasks = []
    
    # Get the current maximum order for the topic
    max_order = db.query(func.max(Task.order)).filter(
        Task.topic_id == request.topic_id
    ).scalar() or 0
    
    for idx, task_data in enumerate(request.tasks):
        # Set order automatically if requested
        if request.auto_order:
            task_data["order"] = max_order + idx + 1
        
        task = Task(
            task_name=task_data.get("lessonName") or task_data.get("task_name"),
            task_link=task_data.get("task_link", str(max_order + idx + 1)),
            type=task_data.get("lessonType", "Code").lower().replace("quiz", "_quiz"),
            points=task_data.get("points", 10),
            order=task_data.get("order", max_order + idx + 1),
            topic_id=request.topic_id,
            data=task_data.get("data", {}),
            is_active=task_data.get("is_active", False)
        )
        db.add(task)
        created_tasks.append(task)
    
    db.commit()
    
    # Return created tasks with their IDs
    return {
        "success": True,
        "created": len(created_tasks),
        "message": f"Successfully created {len(created_tasks)} tasks",
        "tasks": [
            {
                "id": t.id,
                "task_name": t.task_name,
                "order": t.order,
                "type": t.type
            }
            for t in created_tasks
        ]
    }


@router.post("/tasks/bulk-toggle-active")
async def toggle_tasks_active_status(
    task_ids: List[int] = Body(...),
    is_active: bool = Body(...),
    db: Session = Depends(get_db)
):
    """Toggle active status for multiple tasks"""
    tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
    
    for task in tasks:
        task.is_active = is_active
    
    db.commit()
    
    return {
        "success": True,
        "updated": len(tasks),
        "is_active": is_active,
        "message": f"Updated {len(tasks)} tasks"
    }


# ============================================================================
# COURSE/LESSON/TOPIC MANAGEMENT
# ============================================================================

@router.put("/courses/{course_id}")
async def update_course(
    course_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update course metadata"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    
    # Update allowed fields
    updateable_fields = [
        "title", "description", "course_overview", 
        "learning_objectives", "requirements", "target_audience",
        "difficulty_level", "duration_weeks"
    ]
    
    for field in updateable_fields:
        if field in data:
            setattr(course, field, data[field])
    
    course.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Course updated"}


@router.put("/lessons/{lesson_id}")
async def update_lesson(
    lesson_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update lesson information"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    
    updateable_fields = ["title", "description", "lesson_order", "textbook"]
    for field in updateable_fields:
        if field in data:
            setattr(lesson, field, data[field])
    
    db.commit()
    
    return {"success": True, "message": "Lesson updated"}


@router.put("/topics/{topic_id}")
async def update_topic(
    topic_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update topic information"""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    
    updateable_fields = [
        "title", "background", "objectives", 
        "concepts", "topic_order", "content_file_md"
    ]
    
    for field in updateable_fields:
        if field in data:
            setattr(topic, field, data[field])
    
    db.commit()
    
    return {"success": True, "message": "Topic updated"}


def regenerate_task_ids_in_lesson(lesson_id: int, db: Session):
    """Regenerate task_link IDs for all tasks in a lesson to ensure uniqueness"""
    # Get all topics in the lesson, ordered by topic_order
    topics = db.query(Topic).filter(Topic.lesson_id == lesson_id).order_by(Topic.topic_order).all()
    
    for topic in topics:
        # Get all tasks in the topic, ordered by order
        tasks = db.query(Task).filter(Task.topic_id == topic.id).order_by(Task.order).all()
        
        # Regenerate task_link for each task
        for task_index, task in enumerate(tasks):
            new_task_link = f"{topic.id}-{task_index + 1}"
            task.task_link = new_task_link
    
    db.commit()


@router.put("/topics/{topic_id}/move")
async def move_topic_to_lesson(
    topic_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Move a topic to a different lesson"""
    try:
        # Get the topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(404, "Topic not found")
        
        new_lesson_id = data.get("lesson_id")
        if not new_lesson_id:
            raise HTTPException(400, "lesson_id is required")
        
        # Verify the target lesson exists
        target_lesson = db.query(Lesson).filter(Lesson.id == new_lesson_id).first()
        if not target_lesson:
            raise HTTPException(404, "Target lesson not found")
        
        # Get the current lesson to check if they're in the same course
        current_lesson = db.query(Lesson).filter(Lesson.id == topic.lesson_id).first()
        if not current_lesson:
            raise HTTPException(404, "Current lesson not found")
            
        # Ensure both lessons are in the same course
        if current_lesson.course_id != target_lesson.course_id:
            raise HTTPException(400, "Cannot move topic between different courses")
        
        old_lesson_id = topic.lesson_id
        
        # Get the highest order in the target lesson
        max_order_result = db.query(func.max(Topic.topic_order)).filter(Topic.lesson_id == new_lesson_id).scalar()
        new_order = (max_order_result or 0) + 1
        
        # Update the topic
        topic.lesson_id = new_lesson_id
        topic.topic_order = new_order
        
        db.commit()
        
        # Regenerate task IDs in both the source and target lessons to ensure uniqueness
        if old_lesson_id != new_lesson_id:
            regenerate_task_ids_in_lesson(old_lesson_id, db)
            regenerate_task_ids_in_lesson(new_lesson_id, db)
        
        return {
            "success": True, 
            "message": f"Topic moved from lesson {old_lesson_id} to lesson {new_lesson_id}",
            "topic_id": topic_id,
            "new_lesson_id": new_lesson_id,
            "new_order": new_order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error moving topic: {str(e)}")


@router.delete("/topics/{topic_id}")
async def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db)
):
    """Delete a topic and all its tasks"""
    try:
        # Get the topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(404, "Topic not found")
        
        # Count tasks that will be deleted
        task_count = db.query(Task).filter(Task.topic_id == topic_id).count()
        
        # Delete all tasks in the topic first (due to foreign key constraints)
        db.query(Task).filter(Task.topic_id == topic_id).delete()
        
        # Delete the topic
        db.delete(topic)
        db.commit()
        
        return {
            "success": True,
            "message": f"Topic '{topic.title}' and {task_count} tasks deleted successfully",
            "deleted_tasks": task_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error deleting topic: {str(e)}")


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/stats/course/{course_id}")
async def get_course_statistics(course_id: int, db: Session = Depends(get_db)):
    """Get statistics about course content"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    
    total_tasks = 0
    active_tasks = 0
    task_types = {}
    
    for lesson in course.lessons:
        for topic in lesson.topics:
            for task in topic.tasks:
                total_tasks += 1
                if task.is_active:
                    active_tasks += 1
                task_type = task.type
                task_types[task_type] = task_types.get(task_type, 0) + 1
    
    return {
        "course_id": course_id,
        "course_title": course.title,
        "lesson_count": len(course.lessons),
        "topic_count": sum(len(l.topics) for l in course.lessons),
        "total_tasks": total_tasks,
        "active_tasks": active_tasks,
        "inactive_tasks": total_tasks - active_tasks,
        "task_types": task_types,
        "average_tasks_per_topic": round(total_tasks / max(sum(len(l.topics) for l in course.lessons), 1), 2)
    }


@router.get("/generation-materials")
async def get_available_materials():
    """Get list of available material themes for task generation"""
    from utils.task_generator import suggested_material
    
    return {
        "default_materials": suggested_material,
        "custom_materials_supported": True,
        "examples": [
            "Harry Potter",
            "Classical Italian Literature",  
            "Jane Austen novels",
            "Popular TV series",
            "Historical events",
            "Scientific discoveries",
            "Art history",
            "Music theory"
        ],
        "instructions": "You can use any theme or material. The AI will adapt the tasks accordingly."
    }


logger.info("Professor local routes initialized")