"""Student form submission endpoints"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

from db import get_db
from models import StudentFormSubmission, User
from utils.logging_config import logger

router = APIRouter()


# Pydantic models for request/response validation
class StudentFormRequest(BaseModel):
    user_id: str = Field(..., description="Internal user ID (UUID string)")

    # Question 1: Programming experience
    programming_experience: str = Field(..., min_length=1, max_length=200)
    other_language: Optional[str] = Field(None, max_length=100)

    # Question 2: Operating system
    operating_system: str = Field(..., min_length=1, max_length=100)

    # Question 3: Software installation
    software_installation: str = Field(..., min_length=1, max_length=200)

    # Question 4: Python confidence (1-5 scale)
    python_confidence: int = Field(..., ge=1, le=5)

    # Question 5: Problem solving approach (multiple choice)
    problem_solving_approach: List[str] = Field(..., min_items=1, max_items=10)

    # Question 6: Learning preferences (multiple choice)
    learning_preferences: List[str] = Field(..., min_items=1, max_items=10)

    # Question 7: New device approach
    new_device_approach: str = Field(..., min_length=1, max_length=200)

    # Question 8: Study time commitment
    study_time_commitment: str = Field(..., min_length=1, max_length=100)

    # Question 9: Homework schedule
    homework_schedule: str = Field(..., min_length=1, max_length=100)

    # Question 10: Preferred study times (multiple choice)
    preferred_study_times: List[str] = Field(..., min_items=1, max_items=10)

    # Question 11: Study organization
    study_organization: str = Field(..., min_length=1, max_length=200)

    # Question 12: Help seeking preference
    help_seeking_preference: str = Field(..., min_length=1, max_length=200)

    # Question 13: Additional comments (optional)
    additional_comments: Optional[str] = Field(None, max_length=1000)

    @field_validator("problem_solving_approach", "learning_preferences", "preferred_study_times")
    def validate_non_empty_strings(cls, v):
        if not v:  # Allow empty arrays for now to debug
            raise ValueError("At least one item is required")
        # Filter out empty strings and validate remaining items
        filtered = [item for item in v if isinstance(item, str) and item.strip()]
        if not filtered:
            raise ValueError("At least one non-empty item is required")
        return filtered

    @field_validator("other_language", mode="before")
    def validate_other_language(cls, v):
        # Convert empty string to None for optional field
        return None if v == "" else v

    @field_validator("additional_comments", mode="before")
    def validate_additional_comments(cls, v):
        # Convert empty string to None for optional field
        return None if v == "" else v


class StudentFormResponse(BaseModel):
    id: int
    user_id: int
    submitted_at: datetime
    message: str


class StudentFormSummary(BaseModel):
    id: int
    user_id: int
    programming_experience: str
    operating_system: str
    python_confidence: int
    study_time_commitment: str
    submitted_at: datetime
    updated_at: datetime


@router.post("/student-form", response_model=StudentFormResponse)
async def submit_student_form(form_data: StudentFormRequest, db: Session = Depends(get_db)):
    """
    Submit student intake form

    This endpoint receives and stores student intake form submissions.
    Each user can only have one submission (updates existing if resubmitted).
    """
    try:
        logger.info(f"Processing student form submission for internal_user_id: {form_data.user_id}")
        logger.info(f"Form data received: {form_data.dict()}")

        # Find user by internal_user_id (UUID string)
        user = db.query(User).filter(User.internal_user_id == form_data.user_id).first()
        if not user:
            logger.warning(f"User not found for internal_user_id: {form_data.user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check if user already has a submission (use the actual integer user ID)
        existing_submission = db.query(StudentFormSubmission).filter(StudentFormSubmission.user_id == user.id).first()

        if existing_submission:
            logger.info(f"Updating existing form submission {existing_submission.id} for user {form_data.user_id}")

            # Update existing submission
            for field, value in form_data.dict(exclude={"user_id"}).items():
                setattr(existing_submission, field, value)

            existing_submission.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(existing_submission)

            return StudentFormResponse(
                id=existing_submission.id,
                user_id=existing_submission.user_id,
                submitted_at=existing_submission.submitted_at,
                message="Student form updated successfully",
            )
        else:
            # Create new submission
            logger.info(f"Creating new form submission for user {form_data.user_id}")

            submission = StudentFormSubmission(
                user_id=user.id,  # Use the integer primary key
                programming_experience=form_data.programming_experience,
                other_language=form_data.other_language,
                operating_system=form_data.operating_system,
                software_installation=form_data.software_installation,
                python_confidence=form_data.python_confidence,
                problem_solving_approach=form_data.problem_solving_approach,
                learning_preferences=form_data.learning_preferences,
                new_device_approach=form_data.new_device_approach,
                study_time_commitment=form_data.study_time_commitment,
                homework_schedule=form_data.homework_schedule,
                preferred_study_times=form_data.preferred_study_times,
                study_organization=form_data.study_organization,
                help_seeking_preference=form_data.help_seeking_preference,
                additional_comments=form_data.additional_comments,
            )

            db.add(submission)
            db.commit()
            db.refresh(submission)

            logger.info(f"Student form submission created successfully with ID: {submission.id}")

            return StudentFormResponse(
                id=submission.id,
                user_id=submission.user_id,
                submitted_at=submission.submitted_at,
                message="Student form submitted successfully",
            )

    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in submit_student_form: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data integrity constraint violation")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in submit_student_form: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in submit_student_form: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/student-form/{internal_user_id}", response_model=Dict[str, Any])
async def get_student_form(internal_user_id: str, db: Session = Depends(get_db)):
    """
    Retrieve student form submission by internal user ID

    Returns the complete form submission data for a specific user.
    """
    try:
        # Find user by internal_user_id first
        user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        submission = db.query(StudentFormSubmission).filter(StudentFormSubmission.user_id == user.id).first()

        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student form submission not found")

        # Convert to dictionary for response
        submission_data = {
            "id": submission.id,
            "user_id": submission.user_id,
            "programming_experience": submission.programming_experience,
            "other_language": submission.other_language,
            "operating_system": submission.operating_system,
            "software_installation": submission.software_installation,
            "python_confidence": submission.python_confidence,
            "problem_solving_approach": submission.problem_solving_approach,
            "learning_preferences": submission.learning_preferences,
            "new_device_approach": submission.new_device_approach,
            "study_time_commitment": submission.study_time_commitment,
            "homework_schedule": submission.homework_schedule,
            "preferred_study_times": submission.preferred_study_times,
            "study_organization": submission.study_organization,
            "help_seeking_preference": submission.help_seeking_preference,
            "additional_comments": submission.additional_comments,
            "submitted_at": submission.submitted_at,
            "updated_at": submission.updated_at,
        }

        logger.info(f"Retrieved student form submission for user {internal_user_id}")
        return submission_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving student form: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve student form")


@router.get("/student-forms", response_model=Dict[str, Any])
async def get_all_student_forms(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """
    Retrieve all student form submissions (Admin endpoint)

    Returns paginated list of all student form submissions for administrative purposes.
    """
    try:
        query = db.query(StudentFormSubmission).order_by(StudentFormSubmission.submitted_at.desc())

        total_count = query.count()
        submissions = query.offset(offset).limit(limit).all()

        submissions_data = []
        for submission in submissions:
            # Return summary data for list view
            submissions_data.append(
                {
                    "id": submission.id,
                    "user_id": submission.user_id,
                    "programming_experience": submission.programming_experience,
                    "operating_system": submission.operating_system,
                    "python_confidence": submission.python_confidence,
                    "study_time_commitment": submission.study_time_commitment,
                    "submitted_at": submission.submitted_at,
                    "updated_at": submission.updated_at,
                }
            )

        logger.info(f"Retrieved {len(submissions_data)} student form submissions")

        return {
            "submissions": submissions_data,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(submissions_data)) < total_count,
            },
        }

    except Exception as e:
        logger.error(f"Error retrieving student forms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve student forms"
        )


@router.delete("/student-form/{internal_user_id}")
async def delete_student_form(internal_user_id: str, db: Session = Depends(get_db)):
    """
    Delete student form submission by internal user ID

    Allows removal of a student's form submission data.
    """
    try:
        # Find user by internal_user_id first
        user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        submission = db.query(StudentFormSubmission).filter(StudentFormSubmission.user_id == user.id).first()

        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student form submission not found")

        db.delete(submission)
        db.commit()

        logger.info(f"Deleted student form submission for user {internal_user_id}")

        return {"message": f"Student form submission deleted for user {internal_user_id}"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting student form: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete student form")


@router.post("/student-form/debug")
async def debug_student_form(request: Request):
    """
    Debug endpoint to see exactly what data is being sent
    """
    try:
        body = await request.body()
        logger.info(f"Raw request body: {body}")

        import json

        json_data = json.loads(body)
        logger.info(f"Parsed JSON data: {json_data}")

        # Check each required field
        required_fields = [
            "user_id",
            "programming_experience",
            "operating_system",
            "software_installation",
            "python_confidence",
            "problem_solving_approach",
            "learning_preferences",
            "new_device_approach",
            "study_time_commitment",
            "homework_schedule",
            "preferred_study_times",
            "study_organization",
            "help_seeking_preference",
        ]

        missing_fields = []
        field_types = {}

        for field in required_fields:
            if field not in json_data:
                missing_fields.append(field)
            else:
                field_types[field] = {"value": json_data[field], "type": type(json_data[field]).__name__}

        return {
            "status": "debug_success",
            "received_fields": list(json_data.keys()),
            "missing_required_fields": missing_fields,
            "field_details": field_types,
            "raw_body_length": len(body),
        }

    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return {"error": str(e), "raw_body": str(body)}
