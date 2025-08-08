import pytest


def test_basic_functionality():
    """Basic test to verify pytest is working"""
    assert 2 + 2 == 4


def test_imports_work():
    """Test that we can import our application modules"""
    from models import User, Task
    from schemas.validation import TaskSolutionCreate

    # Basic instantiation test
    task_data = TaskSolutionCreate(
        userId="test-user", lessonName="test-lesson", isSuccessful=True, solutionContent="print('hello')"
    )

    assert task_data.userId == "test-user"
    assert task_data.isSuccessful == True


def test_app_import():
    """Test that the FastAPI app can be imported"""
    from app import app

    assert app is not None
    assert hasattr(app, "include_router")
