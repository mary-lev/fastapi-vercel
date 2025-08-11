"""
Tests for v1 API endpoints
Ensures all critical endpoints are working correctly
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from app import app

client = TestClient(app)


# Test data
TEST_USER_ID = "test_user_123"
TEST_CODE = "print('Hello, World!')"
TEST_TASK_ID = 1


class TestHealthEndpoints:
    """Test system health and availability"""

    def test_root_endpoint(self):
        """Test root endpoint is accessible"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["version"] == "1.0.0"

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_openapi_schema(self):
        """Test OpenAPI schema is accessible"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


class TestCompileEndpoint:
    """Test code compilation endpoint"""

    @patch("routes.student.resolve_user")
    @patch("routes.student.run_code")
    def test_compile_success(self, mock_run_code, mock_resolve_user):
        """Test successful code compilation"""
        # Mock user resolution
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        # Mock code execution
        mock_run_code.return_value = {"success": True, "output": "Hello, World!\n"}

        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/compile", json={"code": TEST_CODE, "language": "python"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["output"] == "Hello, World!\n"
        assert data["error"] == ""

    @patch("routes.student.resolve_user")
    @patch("routes.student.run_code")
    def test_compile_syntax_error(self, mock_run_code, mock_resolve_user):
        """Test code compilation with syntax error"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        mock_run_code.return_value = {"success": False, "output": "SyntaxError: invalid syntax"}

        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/compile",
            json={"code": "print('Hello", "language": "python"},  # Missing closing quote
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "SyntaxError" in data["error"]

    @patch("routes.student.resolve_user")
    def test_compile_empty_code(self, mock_resolve_user):
        """Test compilation with empty code"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        response = client.post(f"/api/v1/students/{TEST_USER_ID}/compile", json={"code": "", "language": "python"})

        assert response.status_code == 400
        assert "No code provided" in response.text


class TestSubmitCodeEndpoint:
    """Test code submission endpoint"""

    @patch("routes.student.resolve_user")
    @patch("routes.student.run_code")
    @patch("routes.student.evaluate_code_submission")
    @patch("routes.student.db")
    def test_submit_code_success(self, mock_db, mock_evaluate, mock_run_code, mock_resolve_user):
        """Test successful code submission"""
        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        mock_task = MagicMock()
        mock_task.id = TEST_TASK_ID
        mock_db.query().filter().first.return_value = mock_task
        mock_db.query().filter().count.return_value = 0  # First attempt

        mock_run_code.return_value = {"success": True, "output": "42\n"}

        mock_evaluation = MagicMock()
        mock_evaluation.is_solved = True
        mock_evaluation.feedback = "Correct! Well done."
        mock_evaluate.return_value = mock_evaluation

        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/submit-code",
            json={"code": "print(42)", "task_id": TEST_TASK_ID, "language": "python"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["is_correct"] == True
        assert data["feedback"] == "Correct! Well done."
        assert data["attempt_number"] == 1

    @patch("routes.student.resolve_user")
    @patch("routes.student.run_code")
    @patch("routes.student.db")
    def test_submit_code_with_error(self, mock_db, mock_run_code, mock_resolve_user):
        """Test code submission with runtime error"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        mock_task = MagicMock()
        mock_task.id = TEST_TASK_ID
        mock_db.query().filter().first.return_value = mock_task
        mock_db.query().filter().count.return_value = 1  # Second attempt

        mock_run_code.return_value = {"success": False, "output": "NameError: name 'x' is not defined"}

        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/submit-code",
            json={"code": "print(x)", "task_id": TEST_TASK_ID, "language": "python"},  # Undefined variable
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["is_correct"] == False
        assert "NameError" in data["feedback"]
        assert data["attempt_number"] == 2


class TestSubmitTextEndpoint:
    """Test text submission endpoint"""

    @patch("routes.student.resolve_user")
    @patch("routes.student.evaluate_text_submission")
    @patch("routes.student.db")
    def test_submit_text_correct(self, mock_db, mock_evaluate, mock_resolve_user):
        """Test correct text submission"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        mock_task = MagicMock()
        mock_task.id = TEST_TASK_ID
        mock_db.query().filter().first.return_value = mock_task
        mock_db.query().filter().count.return_value = 0

        mock_evaluation = MagicMock()
        mock_evaluation.is_solved = True
        mock_evaluation.feedback = "Excellent answer!"
        mock_evaluate.return_value = mock_evaluation

        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/submit-text",
            json={"user_answer": "Python is a high-level programming language", "task_id": TEST_TASK_ID},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] == True
        assert data["feedback"] == "Excellent answer!"


class TestCourseEndpoints:
    """Test course-related endpoints"""

    def test_get_courses(self):
        """Test fetching all courses"""
        response = client.get("/api/v1/courses/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "id" in data[0]
            assert "title" in data[0]

    def test_get_course_by_id(self):
        """Test fetching specific course"""
        response = client.get("/api/v1/courses/1")
        # May return 404 if course doesn't exist, which is valid
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["id"] == 1


class TestStudentProgressEndpoints:
    """Test student progress endpoints"""

    @patch("routes.student.resolve_user")
    @patch("routes.student.db")
    def test_get_user_solutions(self, mock_db, mock_resolve_user):
        """Test fetching user solutions"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        mock_solutions = []
        mock_db.query().filter().all.return_value = mock_solutions

        response = client.get(f"/api/v1/students/{TEST_USER_ID}/solutions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestErrorHandling:
    """Test error handling and validation"""

    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/compile",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/submit-code", json={"code": TEST_CODE}  # Missing task_id
        )
        assert response.status_code == 422

    @patch("routes.student.resolve_user")
    def test_user_not_found(self, mock_resolve_user):
        """Test handling when user doesn't exist"""
        mock_resolve_user.side_effect = Exception("User not found")

        response = client.post(
            f"/api/v1/students/nonexistent_user/compile", json={"code": TEST_CODE, "language": "python"}
        )
        # Should handle gracefully
        assert response.status_code in [404, 500]


# Performance tests
class TestPerformance:
    """Test performance and timeout handling"""

    @patch("routes.student.resolve_user")
    @patch("routes.student.run_code")
    def test_code_execution_timeout(self, mock_run_code, mock_resolve_user):
        """Test handling of code execution timeout"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_resolve_user.return_value = mock_user

        mock_run_code.return_value = {
            "success": False,
            "output": "Execution timed out. Possible infinite loop detected.",
        }

        response = client.post(
            f"/api/v1/students/{TEST_USER_ID}/compile",
            json={"code": "while True: pass", "language": "python"},  # Infinite loop
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "timed out" in data["error"].lower()


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([__file__, "-v", "--cov=routes", "--cov-report=term-missing"])
