from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import os

from db import get_db
from models import ContactMessage, User
from utils.logging_config import logger

router = APIRouter()

# Mock data storage (in production, this would be a database)
mock_users = {}
mock_homeworks = []
mock_stats = {"total_users": 150, "active_users": 120, "average_score": 78.5, "total_homeworks": 8}

# API Key for authentication from environment
API_KEY = os.getenv("TELEGRAM_BOT_API_KEY")
if not API_KEY:
    raise ValueError("TELEGRAM_BOT_API_KEY environment variable is required")


# Pydantic models for request/response
class UserModel(BaseModel):
    id: int
    telegram_user_id: int
    first_name: str
    username: str
    email: str
    total_score: int
    homework_score: int
    quiz_score: int
    participation_score: int
    homeworks_completed: int
    total_homeworks: int
    streak_weeks: int
    notifications_enabled: bool


class HomeworkModel(BaseModel):
    id: int
    title: str
    due_date: str
    status: str


class ProgressResponse(BaseModel):
    user: UserModel
    next_homework: Optional[HomeworkModel] = None
    motivational_message: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: Optional[Dict] = None


class NotificationUpdate(BaseModel):
    enabled: bool


class ContactMessageRequest(BaseModel):
    text: str
    anonymous: bool = False
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None
    first_name: Optional[str] = None
    page_url: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class ContactMessageResponse(BaseModel):
    id: int
    status: str
    message: str
    created_at: datetime


# Authentication dependency
def verify_api_key(authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key", headers={"WWW-Authenticate": "Bearer"})
    return True


# Helper functions
def generate_mock_user(telegram_user_id: int) -> UserModel:
    """Generate realistic mock user data based on telegram_user_id"""
    # Use telegram_user_id as seed for consistent data
    random.seed(telegram_user_id)

    # Generate consistent names based on user ID
    first_names = ["John", "Emma", "Michael", "Sarah", "David", "Lisa", "James", "Anna", "Robert", "Maria"]
    last_names = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
    ]

    first_name = first_names[telegram_user_id % len(first_names)]
    last_name = last_names[(telegram_user_id // 10) % len(last_names)]
    username = f"{first_name.lower()}_{last_name.lower()}_{telegram_user_id % 1000}"
    email = f"{username}@example.com"

    # Generate scores based on user ID (some variation but realistic)
    base_score = 70 + (telegram_user_id % 30)  # Scores between 70-100
    homework_score = base_score + random.randint(-10, 10)
    quiz_score = base_score + random.randint(-15, 15)
    participation_score = base_score + random.randint(-5, 15)

    # Ensure scores are within 0-100 range
    homework_score = max(0, min(100, homework_score))
    quiz_score = max(0, min(100, quiz_score))
    participation_score = max(0, min(100, participation_score))

    # Calculate total score as average
    total_score = (homework_score + quiz_score + participation_score) // 3

    # Generate other metrics
    homeworks_completed = min(8, max(0, (telegram_user_id % 10)))
    streak_weeks = min(8, max(1, (telegram_user_id % 7) + 1))
    notifications_enabled = bool(telegram_user_id % 2)

    return UserModel(
        id=telegram_user_id,
        telegram_user_id=telegram_user_id,
        first_name=first_name,
        username=username,
        email=email,
        total_score=total_score,
        homework_score=homework_score,
        quiz_score=quiz_score,
        participation_score=participation_score,
        homeworks_completed=homeworks_completed,
        total_homeworks=8,
        streak_weeks=streak_weeks,
        notifications_enabled=notifications_enabled,
    )


def generate_mock_homeworks() -> List[HomeworkModel]:
    """Generate mock homework data"""
    homework_titles = [
        "Introduction to Python Basics",
        "Variables and Data Types",
        "Control Flow and Loops",
        "Functions and Modules",
        "Data Structures in Python",
        "Object-Oriented Programming",
        "Advanced Python Concepts",
        "Final Project",
    ]

    homeworks = []
    base_date = datetime.now() + timedelta(days=1)

    for i, title in enumerate(homework_titles, 1):
        due_date = base_date + timedelta(days=i * 7)  # Weekly assignments
        homeworks.append(HomeworkModel(id=i, title=title, due_date=due_date.strftime("%Y-%m-%d"), status="pending"))

    return homeworks


def generate_motivational_message(user: UserModel) -> str:
    """Generate personalized motivational message based on user performance"""
    if user.total_score >= 90:
        return f"Outstanding work, {user.first_name}! You're in the top tier with a {user.total_score}% average score!"
    elif user.total_score >= 80:
        return (
            f"Great job, {user.first_name}! You're making excellent progress with an {user.total_score}% average score!"
        )
    elif user.total_score >= 70:
        return f"Good progress, {user.first_name}! Keep up the good work with your {user.total_score}% average score."
    elif user.total_score >= 60:
        return f"Keep pushing, {user.first_name}! You're on the right track with a {user.total_score}% average score."
    else:
        return f"Don't give up, {user.first_name}! Every effort counts. Your current score is {user.total_score}%."


# Initialize mock data
def initialize_mock_data():
    """Initialize mock data for testing"""
    global mock_homeworks
    mock_homeworks = generate_mock_homeworks()


# Initialize data on module import
initialize_mock_data()


# Endpoint 1: Get User Data
@router.get("/api/users/{telegram_user_id}", response_model=UserModel)
async def get_user(telegram_user_id: int, _: bool = Depends(verify_api_key)):
    """
    Retrieve user information and performance data
    """
    try:
        # Generate or retrieve user data
        if telegram_user_id not in mock_users:
            mock_users[telegram_user_id] = generate_mock_user(telegram_user_id)

        user = mock_users[telegram_user_id]
        return user

    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error", headers={"X-Error-Code": "SERVER_ERROR"})


# Endpoint 2: Get User Progress
@router.get("/api/users/{telegram_user_id}/progress", response_model=ProgressResponse)
async def get_user_progress(telegram_user_id: int, _: bool = Depends(verify_api_key)):
    """
    Retrieve user progress data including next assignments and motivational messages
    """
    try:
        # Get or create user
        if telegram_user_id not in mock_users:
            mock_users[telegram_user_id] = generate_mock_user(telegram_user_id)

        user = mock_users[telegram_user_id]

        # Find next homework (first pending homework)
        next_homework = None
        for homework in mock_homeworks:
            if homework.status == "pending":
                next_homework = homework
                break

        # Generate motivational message
        motivational_message = generate_motivational_message(user)

        return ProgressResponse(user=user, next_homework=next_homework, motivational_message=motivational_message)

    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error", headers={"X-Error-Code": "SERVER_ERROR"})


# Endpoint 3: Get Upcoming Homeworks
@router.get("/api/homeworks/upcoming")
async def get_upcoming_homeworks(_: bool = Depends(verify_api_key)):
    """
    Retrieve all upcoming homework assignments
    """
    try:
        # Filter only pending homeworks
        upcoming_homeworks = [hw for hw in mock_homeworks if hw.status == "pending"]

        return {"homeworks": upcoming_homeworks}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error", headers={"X-Error-Code": "SERVER_ERROR"})


# Endpoint 4: Update User Notifications
@router.post("/api/users/{telegram_user_id}/notifications")
async def update_user_notifications(
    telegram_user_id: int,
    enabled: bool = Query(..., description="Boolean flag for notifications"),
    _: bool = Depends(verify_api_key),
):
    """
    Update user notification preferences
    """
    try:
        # Get or create user
        if telegram_user_id not in mock_users:
            mock_users[telegram_user_id] = generate_mock_user(telegram_user_id)

        user = mock_users[telegram_user_id]
        user.notifications_enabled = enabled

        status = "enabled" if enabled else "disabled"
        return {"message": f"Notifications {status} successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error", headers={"X-Error-Code": "SERVER_ERROR"})


# Endpoint 5: Get Platform Statistics
@router.get("/api/stats/overview")
async def get_platform_statistics(_: bool = Depends(verify_api_key)):
    """
    Retrieve platform statistics for admin purposes
    """
    try:
        return mock_stats

    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error", headers={"X-Error-Code": "SERVER_ERROR"})


# Endpoint 6: Create Contact Message
@router.post("/api/contact-message", response_model=ContactMessageResponse)
async def create_contact_message(
    message_request: ContactMessageRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """
    Create a new contact message from Telegram bot
    
    This endpoint receives contact messages from the Telegram bot and stores them
    in the database. It handles both anonymous and identified messages.
    """
    try:
        logger.info(f"Received contact message - Anonymous: {message_request.anonymous}, "
                   f"Telegram ID: {message_request.telegram_user_id}")
        
        # Try to find existing user if telegram_user_id is provided
        linked_user = None
        if message_request.telegram_user_id and not message_request.anonymous:
            linked_user = db.query(User).filter(
                User.telegram_user_id == message_request.telegram_user_id
            ).first()
            
            if linked_user:
                logger.info(f"Found linked user: {linked_user.id} for Telegram ID: {message_request.telegram_user_id}")
        
        # Create contact message record
        contact_message = ContactMessage(
            text=message_request.text,
            anonymous=message_request.anonymous,
            telegram_user_id=message_request.telegram_user_id if not message_request.anonymous else None,
            telegram_username=message_request.telegram_username if not message_request.anonymous else None,
            first_name=message_request.first_name if not message_request.anonymous else None,
            page_url=message_request.page_url,
            attachments=message_request.attachments,
            user_id=linked_user.id if linked_user else None,
            status="received"
        )
        
        db.add(contact_message)
        db.commit()
        db.refresh(contact_message)
        
        logger.info(f"Contact message created successfully with ID: {contact_message.id}")
        
        return ContactMessageResponse(
            id=contact_message.id,
            status="success",
            message="Contact message received and stored successfully",
            created_at=contact_message.created_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating contact message: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to store contact message",
            headers={"X-Error-Code": "CONTACT_MESSAGE_FAILED"}
        )


# Endpoint 7: Get Contact Messages (Admin)
@router.get("/api/contact-messages")
async def get_contact_messages(
    limit: int = Query(50, description="Maximum number of messages to return"),
    offset: int = Query(0, description="Number of messages to skip"),
    status: Optional[str] = Query(None, description="Filter by status"),
    anonymous_only: Optional[bool] = Query(None, description="Filter anonymous messages only"),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """
    Retrieve contact messages (Admin endpoint)
    
    This endpoint allows admins to retrieve and manage contact messages
    received from the Telegram bot.
    """
    try:
        query = db.query(ContactMessage)
        
        # Apply filters
        if status:
            query = query.filter(ContactMessage.status == status)
        
        if anonymous_only is not None:
            query = query.filter(ContactMessage.anonymous == anonymous_only)
        
        # Order by most recent first
        query = query.order_by(ContactMessage.created_at.desc())
        
        # Apply pagination
        total_count = query.count()
        messages = query.offset(offset).limit(limit).all()
        
        logger.info(f"Retrieved {len(messages)} contact messages (total: {total_count})")
        
        # Convert to dict format for response
        messages_data = []
        for msg in messages:
            message_dict = {
                "id": msg.id,
                "text": msg.text,
                "anonymous": msg.anonymous,
                "telegram_user_id": msg.telegram_user_id,
                "telegram_username": msg.telegram_username,
                "first_name": msg.first_name,
                "page_url": msg.page_url,
                "attachments": msg.attachments,
                "created_at": msg.created_at,
                "processed_at": msg.processed_at,
                "status": msg.status,
                "user_id": msg.user_id
            }
            messages_data.append(message_dict)
        
        return {
            "messages": messages_data,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(messages)) < total_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving contact messages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve contact messages",
            headers={"X-Error-Code": "CONTACT_MESSAGES_FETCH_FAILED"}
        )


# Endpoint 8: Update Contact Message Status
@router.patch("/api/contact-messages/{message_id}/status")
async def update_contact_message_status(
    message_id: int,
    status: str = Query(..., description="New status for the message"),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """
    Update the status of a contact message
    
    Allows admins to update the processing status of contact messages
    (e.g., 'received' -> 'processing' -> 'handled' -> 'closed')
    """
    try:
        contact_message = db.query(ContactMessage).filter(
            ContactMessage.id == message_id
        ).first()
        
        if not contact_message:
            raise HTTPException(
                status_code=404,
                detail=f"Contact message with ID {message_id} not found"
            )
        
        # Update status and processed_at timestamp if marking as processed
        old_status = contact_message.status
        contact_message.status = status
        
        if status in ['processing', 'handled', 'closed'] and not contact_message.processed_at:
            contact_message.processed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Contact message {message_id} status updated from '{old_status}' to '{status}'")
        
        return {
            "message": f"Status updated successfully from '{old_status}' to '{status}'",
            "message_id": message_id,
            "status": status,
            "processed_at": contact_message.processed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating contact message status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update contact message status",
            headers={"X-Error-Code": "STATUS_UPDATE_FAILED"}
        )


# Additional utility endpoint for testing
@router.get("/api/test/health")
async def health_check():
    """
    Health check endpoint for testing
    """
    return {"status": "healthy", "message": "Telegram bot API is running"}
