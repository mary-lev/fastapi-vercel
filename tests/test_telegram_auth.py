"""Tests for Telegram authentication endpoints"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import app
from db import get_db
from models import Base, User, TelegramLinkToken
from utils.jwt_utils import jwt_manager
from config import settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_telegram_auth.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Return valid API key for testing"""
    return settings.BACKEND_API_KEY


class TestTelegramLinkCreation:
    """Test the /api/auth/telegram/link endpoint"""

    def test_create_link_success(self, client, db_session, valid_api_key):
        """Test successful link creation"""
        telegram_user_id = 12345

        response = client.post(
            "/api/auth/telegram/link",
            json={"telegram_user_id": telegram_user_id},
            headers={"Authorization": f"Bearer {valid_api_key}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "link_url" in data
        assert f"{settings.FRONTEND_BASE_URL}/telegram/complete?token=" in data["link_url"]

        # Verify token was stored in database
        token_record = (
            db_session.query(TelegramLinkToken).filter(TelegramLinkToken.telegram_user_id == telegram_user_id).first()
        )
        assert token_record is not None
        assert not token_record.is_used

    def test_create_link_invalid_api_key(self, client, db_session):
        """Test link creation with invalid API key"""
        response = client.post(
            "/api/auth/telegram/link", json={"telegram_user_id": 12345}, headers={"Authorization": "Bearer invalid-key"}
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_create_link_missing_auth_header(self, client, db_session):
        """Test link creation without authorization header"""
        response = client.post("/api/auth/telegram/link", json={"telegram_user_id": 12345})

        assert response.status_code == 422  # Validation error for missing header

    def test_create_link_invalid_auth_format(self, client, db_session):
        """Test link creation with invalid authorization header format"""
        response = client.post(
            "/api/auth/telegram/link",
            json={"telegram_user_id": 12345},
            headers={"Authorization": "InvalidFormat api-key"},
        )

        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]


class TestTelegramLinkCompletion:
    """Test the /api/auth/telegram/complete endpoint"""

    def test_complete_link_new_user(self, client, db_session, valid_api_key):
        """Test successful link completion with new user creation"""
        telegram_user_id = 67890

        # First create a link
        link_response = client.post(
            "/api/auth/telegram/link",
            json={"telegram_user_id": telegram_user_id},
            headers={"Authorization": f"Bearer {valid_api_key}"},
        )

        # Extract token from link URL
        link_url = link_response.json()["link_url"]
        token = link_url.split("token=")[1]

        # Complete the link
        complete_response = client.post("/api/auth/telegram/complete", json={"token": token})

        assert complete_response.status_code == 200
        data = complete_response.json()

        assert data["status"] == "ok"
        assert data["user"]["telegram_user_id"] == telegram_user_id
        assert "token" in data  # Session token

        # Verify user was created in database
        user = db_session.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        assert user is not None
        assert user.telegram_user_id == telegram_user_id

        # Verify token was marked as used
        token_record = (
            db_session.query(TelegramLinkToken).filter(TelegramLinkToken.telegram_user_id == telegram_user_id).first()
        )
        assert token_record.is_used
        assert token_record.used_at is not None

    def test_complete_link_existing_user(self, client, db_session, valid_api_key):
        """Test link completion with existing user"""
        telegram_user_id = 99999

        # Create existing user
        existing_user = User(
            internal_user_id="existing-user",
            telegram_user_id=telegram_user_id,
            username="existing_user",
            hashed_sub=f"telegram:{telegram_user_id}",
        )
        db_session.add(existing_user)
        db_session.commit()

        # Create and complete link
        link_response = client.post(
            "/api/auth/telegram/link",
            json={"telegram_user_id": telegram_user_id},
            headers={"Authorization": f"Bearer {valid_api_key}"},
        )

        link_url = link_response.json()["link_url"]
        token = link_url.split("token=")[1]

        complete_response = client.post("/api/auth/telegram/complete", json={"token": token})

        assert complete_response.status_code == 200
        data = complete_response.json()

        assert data["status"] == "ok"
        assert data["user"]["id"] == existing_user.id
        assert data["user"]["telegram_user_id"] == telegram_user_id

    def test_complete_link_invalid_token(self, client, db_session):
        """Test link completion with invalid token"""
        response = client.post("/api/auth/telegram/complete", json={"token": "invalid-token"})

        assert response.status_code == 400
        assert response.json()["detail"] == "TOKEN_INVALID"

    def test_complete_link_expired_token(self, client, db_session, valid_api_key):
        """Test link completion with expired token"""
        telegram_user_id = 11111

        # Create an expired token manually
        expired_token_data = jwt_manager.create_link_token(telegram_user_id, expires_minutes=-1)  # Already expired

        # Store token record in database (as if it was created normally)
        token_record = TelegramLinkToken(
            jti=expired_token_data["jti"],
            telegram_user_id=telegram_user_id,
            expires_at=expired_token_data["expires_at"],
            is_used=False,
        )
        db_session.add(token_record)
        db_session.commit()

        response = client.post("/api/auth/telegram/complete", json={"token": expired_token_data["token"]})

        assert response.status_code == 400
        assert response.json()["detail"] == "TOKEN_INVALID"

    def test_complete_link_used_token(self, client, db_session, valid_api_key):
        """Test link completion with already used token"""
        telegram_user_id = 22222

        # Create and use a token
        link_response = client.post(
            "/api/auth/telegram/link",
            json={"telegram_user_id": telegram_user_id},
            headers={"Authorization": f"Bearer {valid_api_key}"},
        )

        link_url = link_response.json()["link_url"]
        token = link_url.split("token=")[1]

        # Use the token once
        first_response = client.post("/api/auth/telegram/complete", json={"token": token})
        assert first_response.status_code == 200

        # Try to use the same token again
        second_response = client.post("/api/auth/telegram/complete", json={"token": token})

        assert second_response.status_code == 400
        assert second_response.json()["detail"] == "TOKEN_USED"


class TestTelegramLinkStatus:
    """Test the /api/auth/telegram/status endpoint"""

    def test_get_status_linked_user(self, client, db_session, valid_api_key):
        """Test status check for linked user"""
        telegram_user_id = 33333

        # Create linked user
        user = User(
            internal_user_id="linked-user",
            telegram_user_id=telegram_user_id,
            username="linked_user",
            hashed_sub=f"telegram:{telegram_user_id}",
        )
        db_session.add(user)
        db_session.commit()

        response = client.get(
            f"/api/auth/telegram/status/{telegram_user_id}", headers={"Authorization": f"Bearer {valid_api_key}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["telegram_user_id"] == telegram_user_id
        assert data["is_linked"] is True
        assert data["user_id"] == user.id
        assert data["username"] == user.username

    def test_get_status_unlinked_user(self, client, db_session, valid_api_key):
        """Test status check for unlinked user"""
        telegram_user_id = 44444

        response = client.get(
            f"/api/auth/telegram/status/{telegram_user_id}", headers={"Authorization": f"Bearer {valid_api_key}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["telegram_user_id"] == telegram_user_id
        assert data["is_linked"] is False
        assert data["user_id"] is None
        assert data["username"] is None


class TestJWTUtils:
    """Test JWT utility functions"""

    def test_create_and_verify_link_token(self):
        """Test JWT token creation and verification"""
        telegram_user_id = 55555

        # Create token
        token_data = jwt_manager.create_link_token(telegram_user_id)
        assert "token" in token_data
        assert "jti" in token_data
        assert "expires_at" in token_data

        # Verify token
        payload = jwt_manager.verify_link_token(token_data["token"])
        assert payload is not None
        assert payload["telegram_user_id"] == telegram_user_id
        assert payload["sub"] == "telegram-link"
        assert payload["jti"] == token_data["jti"]

    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        payload = jwt_manager.verify_link_token("invalid.token.here")
        assert payload is None

    def test_create_and_verify_session_token(self):
        """Test session token creation and verification"""
        user_id = 123
        telegram_user_id = 66666

        # Create session token
        session_token = jwt_manager.create_session_token(user_id, telegram_user_id)

        # Verify session token
        payload = jwt_manager.verify_session_token(session_token)
        assert payload is not None
        assert int(payload["sub"]) == user_id
        assert payload["telegram_user_id"] == telegram_user_id
        assert payload["aud"] == "session"


if __name__ == "__main__":
    pytest.main([__file__])
