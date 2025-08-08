from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import random
import os

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


# Additional utility endpoint for testing
@router.get("/api/test/health")
async def health_check():
    """
    Health check endpoint for testing
    """
    return {"status": "healthy", "message": "Telegram bot API is running"}
