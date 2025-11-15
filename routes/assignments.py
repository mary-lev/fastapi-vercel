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
# Use /tmp for serverless environments (Vercel), local path otherwise
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads/assignments" if os.getenv("VERCEL") else "uploads/assignments")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/x-python",  # Python scripts
    "application/x-python-code",  # Alternative Python MIME type
    "application/zip"
}

# Lazy directory creation - only when needed, not at import time
def ensure_upload_dir():
    """Ensure upload directory exists (lazy initialization)"""
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create upload directory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload directory not available. Please contact administrator."
        )


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
        "text/x-python": ".py",
        "application/x-python-code": ".py",
        "application/zip": ".zip"
    }
    return extensions.get(content_type, "")


def validate_python_code(
    task: Task,
    file_path: str,
    language: str = "Russian",
    user_id: int = None,
    db: Session = None,
    student_first_name: str = None
) -> ScreenshotValidation:
    """
    Validate a Python code file using OpenAI.

    IMPORTANT: Does NOT execute the code - only reads and validates content.
    Safe to use with student submissions.

    Args:
        task: Task object with requirements
        file_path: Path to the .py file
        language: Feedback language (Russian/English)
        user_id: Student ID for personalized feedback
        db: Database session to check previous attempts
        student_first_name: Student's first name for personalization

    Returns:
        ScreenshotValidation object with validation results
    """
    try:
        # SAFELY read the file content as text (NO EXECUTION!)
        with open(file_path, 'r', encoding='utf-8') as f:
            code_content = f.read()

        # Security check: limit file size for LLM processing
        MAX_CODE_LENGTH = 10000  # ~10KB of code
        if len(code_content) > MAX_CODE_LENGTH:
            return ScreenshotValidation(
                is_valid=False,
                feedback="Файл слишком большой для проверки (максимум 10KB кода)." if language == "Russian"
                        else "File too large for validation (max 10KB of code).",
                contains_error=True
            )

        # Get task requirements
        task_description = task.task_description or task.task_summary or "No description"

        # Get previous attempts for context
        previous_feedback = []
        if db and user_id:
            from models import AIFeedback
            prev_attempts = db.query(AIFeedback).filter(
                AIFeedback.user_id == user_id,
                AIFeedback.task_id == task.id
            ).order_by(AIFeedback.created_at.desc()).limit(3).all()
            previous_feedback = [attempt.feedback for attempt in prev_attempts if attempt.feedback]

        # Build prompt for code review
        name_greeting = f"{student_first_name}, " if student_first_name else ""

        system_prompt = f"""You are a supportive Python programming instructor reviewing student code submissions.

Language: {language}
Teaching approach: Socratic method - guide students to discover issues themselves

IMPORTANT SECURITY NOTE:
- You are reviewing CODE AS TEXT only
- DO NOT attempt to execute, run, or interpret the code
- Only provide static analysis and feedback

Your task:
1. Check if the code meets the assignment requirements
2. Identify syntax errors, logic errors, or style issues
3. Provide constructive, specific feedback
4. If the code is mostly correct, mark as valid
5. If it has significant errors or doesn't meet requirements, mark as invalid"""

        user_prompt = f"""Assignment Requirements:
{task_description}

Student's Python Code:
```python
{code_content}
```

{"Previous feedback given to this student:" if previous_feedback else ""}
{chr(10).join(f"- {fb[:200]}" for fb in previous_feedback[:2]) if previous_feedback else ""}

Please review this code and provide feedback in {language}.

Structure your response as:
1. **Overall Assessment**: Does it meet requirements? (Yes/No with brief reason)
2. **Specific Issues** (if any): List concrete problems with line numbers
3. **Strengths**: What did the student do well?
4. **Next Steps**: 1-2 specific suggestions for improvement

Keep feedback encouraging and specific. Start with "{name_greeting}" if addressing the student."""

        # Call OpenAI for validation
        response = openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        feedback = response.choices[0].message.content.strip()

        # Determine if valid based on feedback content
        # Look for positive indicators
        is_valid = any(indicator in feedback.lower() for indicator in [
            "meets requirements", "соответствует требованиям",
            "correct", "правильно", "отлично",
            "well done", "хорошая работа",
            "successfully", "успешно"
        ])

        # Look for error indicators
        contains_error = any(indicator in feedback.lower() for indicator in [
            "error", "ошибка", "incorrect", "неправильно",
            "missing", "отсутствует", "problem", "проблема",
            "does not meet", "не соответствует"
        ])

        return ScreenshotValidation(
            is_valid=is_valid and not contains_error,
            feedback=feedback,
            contains_error=contains_error
        )

    except UnicodeDecodeError:
        return ScreenshotValidation(
            is_valid=False,
            feedback="Ошибка чтения файла. Убедитесь, что файл содержит корректный Python код в UTF-8." if language == "Russian"
                    else "Error reading file. Ensure the file contains valid Python code in UTF-8.",
            contains_error=True
        )
    except Exception as e:
        logger.error(f"Python code validation failed: {str(e)}")
        return ScreenshotValidation(
            is_valid=False,
            feedback=f"Ошибка при проверке кода: {str(e)}" if language == "Russian"
                    else f"Error validating code: {str(e)}",
            contains_error=True
        )


def validate_assignment_screenshot(
    task: Task,
    file_path: str,
    language: str = "Russian",
    user_id: int = None,
    db: Session = None,
    student_first_name: str = None
) -> ScreenshotValidation:
    """
    Validate assignment screenshot using LLM with task-specific instructions.

    This function follows the same pattern as evaluate_code_submission in evaluator.py,
    adapting prompts dynamically based on the task description and supporting attempt history.

    Args:
        task: Task object containing description and instructions
        file_path: Path to the uploaded screenshot
        language: Language for feedback (default: Russian)
        user_id: User ID for fetching previous attempts (optional)
        db: Database session for fetching previous attempts (optional)
        student_first_name: Student's first name for personalization (optional)

    Returns:
        ScreenshotValidation with feedback in specified language
    """
    if not OPENAI_ENABLED:
        return ScreenshotValidation(
            is_valid=True,
            feedback="Скриншот загружен успешно! Преподаватель проверит его вручную." if language == "Russian"
                     else "Screenshot uploaded successfully! Professor will review manually.",
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

        # Fetch previous attempts if user_id and db are provided
        previous_attempts = None
        if user_id and db:
            from models import TaskAttempt
            previous_attempts = (
                db.query(TaskAttempt)
                .filter(TaskAttempt.user_id == user_id, TaskAttempt.task_id == task.id)
                .order_by(TaskAttempt.submitted_at)
                .all()
            )

        # Use the enhanced evaluator function from utils/evaluator.py
        from utils.evaluator import provide_screenshot_feedback

        result = provide_screenshot_feedback(
            image_base64=base64_image,
            mime_type=mime_type,
            task=task,
            language=language,
            previous_attempts=previous_attempts,
            student_first_name=student_first_name
        )

        # Convert SubmissionGrader to ScreenshotValidation
        validation_result = ScreenshotValidation(
            is_valid=result.is_solved,
            feedback=result.feedback,
            contains_error=not result.is_solved  # If not solved, consider it contains error
        )

        logger.info(f"Screenshot validation completed", extra={
            "task_id": task.id,
            "task_name": task.task_name if hasattr(task, 'task_name') else "Assignment",
            "is_valid": validation_result.is_valid,
            "contains_error": validation_result.contains_error,
            "has_attempt_history": previous_attempts is not None and len(previous_attempts) > 0
        })

        return validation_result

    except Exception as e:
        logger.error(f"Screenshot validation failed: {str(e)}")
        # Return neutral response on error
        fallback_message = (
            "Скриншот загружен! Преподаватель проверит его дополнительно." if language == "Russian"
            else "Screenshot uploaded! Professor will review additionally."
        )
        return ScreenshotValidation(
            is_valid=True,
            feedback=fallback_message,
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
            # Ensure upload directory exists (lazy initialization)
            ensure_upload_dir()

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

        # Create TaskAttempt record (for consistency with code tasks and to track attempt history)
        from models import TaskAttempt

        # Get current attempt number
        current_attempts = (
            db.query(TaskAttempt)
            .filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == task_id)
            .count()
        )
        attempt_number = current_attempts + 1

        # Create attempt record with file info in attempt_content
        attempt_content = f"File: {file.filename if file else 'No file'}"
        if content:
            attempt_content = f"{content}\n\n{attempt_content}"

        task_attempt = TaskAttempt(
            user_id=user.id,
            task_id=task_id,
            attempt_number=attempt_number,
            attempt_content=attempt_content,
            submitted_at=datetime.now(),
            is_successful=False  # Will be updated after validation
        )
        db.add(task_attempt)
        db.flush()  # Get attempt ID for later use

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

        # Validate uploaded files based on type
        validation_feedback = None

        # Get course language for feedback (default to Russian)
        course_language = (
            task.topic.lesson.course.language
            if task.topic and task.topic.lesson and task.topic.lesson.course
            else "Russian"
        )

        if file_path and file_type and task.type == "assignment_submission":
            # IMAGE VALIDATION: Screenshots
            if file_type.startswith('image/'):
                try:
                    validation = validate_assignment_screenshot(
                        task=task,
                        file_path=file_path,
                        language=course_language,
                        user_id=user.id,
                        db=db,
                        student_first_name=user.first_name if hasattr(user, 'first_name') else None
                    )
                    validation_feedback = validation.feedback

                    # Update solution with validation results
                    if validation.is_valid and not validation.contains_error:
                        # Success - award full points
                        solution.is_correct = True
                        solution.points_earned = task.points
                        task_attempt.is_successful = True
                    elif validation.contains_error:
                        # Contains error - partial points, needs manual review
                        solution.is_correct = False
                        solution.points_earned = int(task.points * 0.5)  # 50% for attempt
                        task_attempt.is_successful = False

                    # Append validation feedback to solution content
                    feedback_label = "[Автоматическая проверка скриншота]" if course_language == "Russian" else "[Screenshot Validation]"
                    if solution.solution_content:
                        solution.solution_content += f"\n\n{feedback_label}\n{validation.feedback}"
                    else:
                        solution.solution_content = f"{feedback_label}\n{validation.feedback}"

                    # Save AI feedback to database
                    from models import AIFeedback
                    if validation.feedback:
                        ai_feedback_entry = AIFeedback(
                            user_id=user.id,
                            task_id=task_id,
                            task_attempt_id=task_attempt.id,
                            feedback=validation.feedback,
                            created_at=datetime.now()
                        )
                        db.add(ai_feedback_entry)

                    logger.info(f"Screenshot validated", extra={
                        "solution_id": solution.id,
                        "task_id": task.id,
                        "user_id": user.id,
                        "attempt_number": attempt_number,
                        "is_valid": validation.is_valid,
                        "contains_error": validation.contains_error
                    })
                except Exception as e:
                    logger.warning(f"Screenshot validation failed: {str(e)}")
                    # On validation error, accept submission but mark for manual review
                    task_attempt.is_successful = True

            # PYTHON CODE VALIDATION: .py files
            elif file_type in ['text/x-python', 'application/x-python-code'] or file_path.endswith('.py'):
                try:
                    validation = validate_python_code(
                        task=task,
                        file_path=file_path,
                        language=course_language,
                        user_id=user.id,
                        db=db,
                        student_first_name=user.first_name if hasattr(user, 'first_name') else None
                    )
                    validation_feedback = validation.feedback

                    # Update solution with validation results
                    # Award full points if code is valid OR just has minor issues
                    if validation.is_valid:
                        # Code meets requirements - full points
                        solution.is_correct = True
                        solution.points_earned = task.points
                        task_attempt.is_successful = True
                    elif validation.contains_error:
                        # Code has errors but shows effort - still award full points
                        # Students learn better with encouragement and can improve iteratively
                        solution.is_correct = True
                        solution.points_earned = task.points
                        task_attempt.is_successful = True
                    else:
                        # Fallback: award full points for submission
                        solution.is_correct = True
                        solution.points_earned = task.points
                        task_attempt.is_successful = True

                    # Append validation feedback to solution content
                    feedback_label = "[Автоматическая проверка кода]" if course_language == "Russian" else "[Code Review]"
                    if solution.solution_content:
                        solution.solution_content += f"\n\n{feedback_label}\n{validation.feedback}"
                    else:
                        solution.solution_content = f"{feedback_label}\n{validation.feedback}"

                    # Save AI feedback to database
                    from models import AIFeedback
                    if validation.feedback:
                        ai_feedback_entry = AIFeedback(
                            user_id=user.id,
                            task_id=task_id,
                            task_attempt_id=task_attempt.id,
                            feedback=validation.feedback,
                            created_at=datetime.now()
                        )
                        db.add(ai_feedback_entry)

                    logger.info(f"Python code validated", extra={
                        "solution_id": solution.id,
                        "task_id": task.id,
                        "user_id": user.id,
                        "attempt_number": attempt_number,
                        "is_valid": validation.is_valid,
                        "contains_error": validation.contains_error,
                        "code_length": len(open(file_path, 'r', encoding='utf-8').read())
                    })
                except Exception as e:
                    logger.warning(f"Python code validation failed: {str(e)}")
                    # On validation error, accept submission but mark for manual review
                    task_attempt.is_successful = True

            # OTHER FILE TYPES: Accept without validation (PDF, DOC, TXT, ZIP)
            else:
                task_attempt.is_successful = True
                logger.info(f"Assignment submitted without validation", extra={
                    "task_id": task_id,
                    "user_id": user.id,
                    "file_type": file_type
                })

        # NO FILE: Text-only submission
        else:
            task_attempt.is_successful = True
            logger.info(f"Text-only assignment submitted", extra={
                "task_id": task_id,
                "user_id": user.id,
                "has_content": bool(content)
            })

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
            "attempt_number": attempt_number,
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
