import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ["TELEGRAM_BOT_API_KEY"] = "test_api_key"
os.environ["NODE_ENV"] = "test"
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_DATABASE"] = "test_db"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["OPENAI_API_KEY"] = "test_openai_key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app import app
from db import get_db
from base import Base

# Test database URL - use SQLite in memory for fast tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})  # SQLite specific
    Base.metadata.create_all(bind=engine)
    yield engine
    # Cleanup
    try:
        os.remove("./test.db")
    except FileNotFoundError:
        pass


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create fresh session for each test
    session = TestingSessionLocal()

    yield session

    # Cleanup after each test
    session.close()
    # Clear all tables
    for table in reversed(Base.metadata.sorted_tables):
        test_engine.execute(table.delete())


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with test database"""

    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "internal_user_id": "test-user-123",
        "hashed_sub": "hashed_sub_123",
        "username": "testuser",
        "status": "student",
    }


@pytest.fixture
def sample_task_solution_data():
    """Sample task solution data for testing"""
    return {
        "userId": "test-user-123",
        "lessonName": "test-task-link",
        "isSuccessful": True,
        "solutionContent": "print('Hello World')",
    }
