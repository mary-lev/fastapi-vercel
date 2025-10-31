"""
Assignment Submission Router
Handles file uploads and text submissions for assignment tasks
"""

import os
import shutil
import base64
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import User, Task, TaskSolution
from db import get_db
# No auth dependencies needed - we handle user resolution manually
from utils.structured_logging import get_logger
from config import settings

router = APIRouter()
logger = get_logger("routes.assignments")

# OpenAI client for screenshot validation
OPENAI_ENABLED = bool(settings.OPENAI_API_KEY)
if OPENAI_ENABLED:
    from openai import OpenAI
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ScreenshotValidation(BaseModel):
    """Result of screenshot validation"""
    is_valid: bool
    feedback: str
    contains_error: bool = False

# Configuration
UPLOAD_DIR = "uploads/assignments"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/zip"
}

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_file_extension(content_type: str) -> str:
    """Get file extension from MIME type"""
    extensions = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
        "application/zip": ".zip"
    }
    return extensions.get(content_type, "")


def validate_python_screenshot(file_path: str) -> ScreenshotValidation:
    """
    Validate Python installation screenshot using LLM (similar to evaluator.py pattern)

    Args:
        file_path: Path to the uploaded screenshot

    Returns:
        ScreenshotValidation with feedback in Russian
    """
    if not OPENAI_ENABLED:
        return ScreenshotValidation(
            is_valid=True,
            feedback="Скриншот загружен успешно! Преподаватель проверит его вручную.",
            contains_error=False
        )

    try:
        # Encode image to base64
        with open(file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        # Get MIME type
        extension = os.path.splitext(file_path)[1].lower()
        mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif'}
        mime_type = mime_types.get(extension, 'image/jpeg')

        # Simple prompt in Russian for screenshot analysis
        system_prompt = """Ты - помощник преподавателя по программированию.
Твоя задача - проверить скриншот установки Python и дать краткую обратную связь студенту.

ВАЖНО: Отвечай ТОЛЬКО на русском языке. Используй вежливую форму обращения (вы, вам, вас).

Проверь скриншот на наличие:
1. Окна терминала/командной строки
2. Команды python --version или python3 --version
3. Вывода с версией Python (например "Python 3.11.5")
4. Или ошибки при установке/запуске Python

Дай краткий ответ (2-3 предложения):
- Если видна версия Python - поздравь студента с успешной установкой
- Если видна ошибка - дай короткую инструкцию как её исправить
- Если не видно ни версии, ни ошибки - попроси переделать скриншот"""

        user_prompt = "Проанализируй этот скриншот установки Python и дай краткую обратную связь студенту:"

        # Call OpenAI Vision API with structured output
        completion = openai_client.beta.chat.completions.parse(
            model="gpt-5-mini",  # Using GPT-5 Mini for vision
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                                "detail": "low"  # Use low detail for faster/cheaper processing
                            }
                        }
                    ]
                }
            ],
            response_format=ScreenshotValidation,
        )

        result = completion.choices[0].message.parsed
        logger.info(f"Screenshot validation completed", extra={
            "is_valid": result.is_valid,
            "contains_error": result.contains_error
        })

        return result

    except Exception as e:
        logger.error(f"Screenshot validation failed: {str(e)}")
        # Return neutral response on error
        return ScreenshotValidation(
            is_valid=True,
            feedback="Скриншот загружен! Преподаватель проверит его дополнительно.",
            contains_error=False
        )


@router.post("/submit")
async def submit_assignment(
    task_id: int = Form(...),
    user_id: str = Form(...),
    content: Optional[str] = Form(None),
    course_id: str = Form(default="1"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Submit an assignment with optional file upload

    Args:
        task_id: ID of the assignment task
        user_id: Internal user ID
        content: Text content of the submission
        course_id: Course ID (for organization)
        file: Optional file upload
        db: Database session
        current_user: Authenticated user

    Returns:
        Submission details with file info if uploaded
    """
    try:
        logger.info(f"Assignment submission started", extra={
            "user_id": user_id,
            "task_id": task_id,
            "has_file": file is not None,
            "has_content": content is not None
        })

        # Validate that we have at least content or file
        if not content and not file:
            raise HTTPException(
                status_code=400,
                detail="Either content or file must be provided"
            )

        # Verify user exists - use the auth utility function
        from utils.auth_middleware import resolve_user_by_id as resolve_user_func
        user = resolve_user_func(user_id, db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Check if task type is assignment_submission
        if task.type != "assignment_submission":
            logger.warning(f"Attempt to submit file for non-assignment task", extra={
                "task_id": task_id,
                "task_type": task.type
            })

        # Handle file upload if present
        file_path = None
        file_name = None
        file_size = None
        file_type = None

        if file:
            # Validate file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning

            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size ({file_size} bytes) exceeds maximum allowed ({MAX_FILE_SIZE} bytes)"
                )

            # Validate file type
            file_type = file.content_type
            if file_type not in ALLOWED_FILE_TYPES:
                raise HTTPException(
                    status_code=415,
                    detail=f"File type {file_type} not allowed. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"
                )

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = get_file_extension(file_type)
            safe_filename = f"user_{user.id}_task_{task_id}_{timestamp}{extension}"
            file_path = os.path.join(UPLOAD_DIR, safe_filename)
            file_name = file.filename

            # Save file
            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                logger.info(f"File uploaded successfully", extra={
                    "file_path": file_path,
                    "file_size": file_size
                })
            except Exception as e:
                logger.error(f"File upload failed: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to save file")

        # Create or update task solution
        existing_solution = db.query(TaskSolution).filter(
            TaskSolution.user_id == user.id,
            TaskSolution.task_id == task_id
        ).first()

        if existing_solution:
            # Update existing solution
            existing_solution.solution_content = content or existing_solution.solution_content
            existing_solution.completed_at = datetime.now()
            existing_solution.is_correct = True  # Assignments are marked as submitted, not right/wrong
            existing_solution.points_earned = task.points

            if file_path:
                # Delete old file if exists
                if existing_solution.file_path and os.path.exists(existing_solution.file_path):
                    try:
                        os.remove(existing_solution.file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete old file: {str(e)}")

                existing_solution.file_path = file_path
                existing_solution.file_name = file_name
                existing_solution.file_size = file_size
                existing_solution.file_type = file_type

            solution = existing_solution
        else:
            # Create new solution
            solution = TaskSolution(
                task_id=task_id,
                user_id=user.id,
                solution_content=content or "",
                is_correct=True,
                points_earned=task.points,
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                file_type=file_type
            )
            db.add(solution)

        # Flush to get solution.id before validation
        db.flush()

        # Validate screenshot if it's an image (for Python installation task)
        validation_feedback = None
        if file_path and file_type and file_type.startswith('image/'):
            # Only validate for assignment_submission tasks
            if task.type == "assignment_submission":
                try:
                    validation = validate_python_screenshot(file_path)
                    validation_feedback = validation.feedback

                    # Update solution with validation results
                    if validation.is_valid and not validation.contains_error:
                        # Success - award full points
                        solution.is_correct = True
                        solution.points_earned = task.points
                    elif validation.contains_error:
                        # Contains error - partial points, needs manual review
                        solution.is_correct = False
                        solution.points_earned = int(task.points * 0.5)  # 50% for attempt

                    # Append validation feedback to solution content
                    if solution.solution_content:
                        solution.solution_content += f"\n\n[Автоматическая проверка]\n{validation.feedback}"
                    else:
                        solution.solution_content = f"[Автоматическая проверка]\n{validation.feedback}"

                    logger.info(f"Screenshot validated", extra={
                        "solution_id": solution.id,
                        "is_valid": validation.is_valid,
                        "contains_error": validation.contains_error
                    })
                except Exception as e:
                    logger.warning(f"Validation failed, continuing without it: {str(e)}")

        # Commit AFTER validation updates
        db.commit()
        db.refresh(solution)

        logger.info(f"Assignment submitted successfully", extra={
            "solution_id": solution.id,
            "user_id": user_id,
            "task_id": task_id
        })

        response = {
            "success": True,
            "solution_id": solution.id,
            "task_id": task_id,
            "user_id": user_id,
            "file_uploaded": file_path is not None,
            "file_name": file_name,
            "file_size": file_size,
            "points_earned": solution.points_earned,
            "is_correct": solution.is_correct,
            "submitted_at": solution.completed_at.isoformat()
        }

        # Include validation feedback if available
        if validation_feedback:
            response["validation_feedback"] = validation_feedback

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assignment submission failed: {str(e)}", extra={
            "user_id": user_id,
            "task_id": task_id
        })
        # Clean up uploaded file if database operation failed
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit assignment: {str(e)}")


@router.get("/{solution_id}/file")
async def get_assignment_file(
    solution_id: int,
    user_id: str = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Get file URL for an assignment submission

    Args:
        solution_id: ID of the task solution
        user_id: User ID making the request (for authorization)
        db: Database session

    Returns:
        File information including download path
    """
    solution = db.query(TaskSolution).filter(TaskSolution.id == solution_id).first()

    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Verify requesting user
    from utils.auth_middleware import resolve_user_by_id as resolve_user_func
    requesting_user = resolve_user_func(user_id, db)
    if not requesting_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check authorization (user can only access their own submissions or professor can access all)
    if solution.user_id != requesting_user.id and requesting_user.status.value not in ["professor", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")

    if not solution.file_path:
        raise HTTPException(status_code=404, detail="No file uploaded for this solution")

    if not os.path.exists(solution.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return {
        "file_name": solution.file_name,
        "file_size": solution.file_size,
        "file_type": solution.file_type,
        "file_path": solution.file_path,
        "uploaded_at": solution.completed_at.isoformat()
    }
