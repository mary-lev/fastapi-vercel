import pytest
from fastapi import status
from schemas.validation import TaskSolutionCreate, TaskUpdateSchema, UserRegistrationSchema


class TestInputValidation:
    """Test input validation using Pydantic schemas"""

    def test_task_solution_validation_success(self):
        """Test valid task solution data"""
        valid_data = {
            "userId": "user-123",
            "lessonName": "lesson-1",
            "isSuccessful": True,
            "solutionContent": "print('hello')",
        }

        schema = TaskSolutionCreate(**valid_data)
        assert schema.userId == "user-123"
        assert schema.lessonName == "lesson-1"
        assert schema.isSuccessful == True

    def test_task_solution_validation_empty_user_id(self):
        """Test empty user ID validation"""
        invalid_data = {
            "userId": "",
            "lessonName": "lesson-1",
            "isSuccessful": True,
            "solutionContent": "print('hello')",
        }

        with pytest.raises(ValueError, match="User ID cannot be empty"):
            TaskSolutionCreate(**invalid_data)

    def test_task_solution_validation_empty_lesson_name(self):
        """Test empty lesson name validation"""
        invalid_data = {
            "userId": "user-123",
            "lessonName": "",
            "isSuccessful": True,
            "solutionContent": "print('hello')",
        }

        with pytest.raises(ValueError, match="Lesson name cannot be empty"):
            TaskSolutionCreate(**invalid_data)

    def test_task_solution_validation_content_too_long(self):
        """Test solution content length validation"""
        invalid_data = {
            "userId": "user-123",
            "lessonName": "lesson-1",
            "isSuccessful": True,
            "solutionContent": "x" * 10001,  # Exceeds 10000 character limit
        }

        with pytest.raises(ValueError, match="Solution content too long"):
            TaskSolutionCreate(**invalid_data)

    def test_task_update_validation_success(self):
        """Test valid task update data"""
        valid_data = {
            "taskId": 1,
            "newQuestion": "What is the capital of France?",
            "newOptions": [{"name": "Paris"}, {"name": "London"}, {"name": "Berlin"}],
            "newCorrectAnswers": ["1"],
        }

        schema = TaskUpdateSchema(**valid_data)
        assert schema.taskId == 1
        assert schema.newQuestion == "What is the capital of France?"
        assert len(schema.newOptions) == 3

    def test_task_update_validation_question_too_short(self):
        """Test question length validation"""
        invalid_data = {
            "taskId": 1,
            "newQuestion": "Hi?",  # Too short
            "newOptions": [{"name": "A"}, {"name": "B"}],
            "newCorrectAnswers": ["1"],
        }

        with pytest.raises(ValueError, match="Question must be at least 5 characters"):
            TaskUpdateSchema(**invalid_data)

    def test_task_update_validation_insufficient_options(self):
        """Test minimum options validation"""
        invalid_data = {
            "taskId": 1,
            "newQuestion": "Valid question?",
            "newOptions": [{"name": "Only one option"}],  # Need at least 2
            "newCorrectAnswers": ["1"],
        }

        with pytest.raises(ValueError, match="Must provide at least 2 options"):
            TaskUpdateSchema(**invalid_data)

    def test_task_update_validation_empty_option_name(self):
        """Test empty option name validation"""
        invalid_data = {
            "taskId": 1,
            "newQuestion": "Valid question?",
            "newOptions": [{"name": "Valid option"}, {"name": ""}],  # Empty name
            "newCorrectAnswers": ["1"],
        }

        with pytest.raises(ValueError, match="Each option must have a non-empty name"):
            TaskUpdateSchema(**invalid_data)

    def test_user_registration_validation_success(self):
        """Test valid user registration data"""
        valid_data = {"username": "testuser123", "password": "password123", "email": "test@example.com"}

        schema = UserRegistrationSchema(**valid_data)
        assert schema.username == "testuser123"
        assert schema.password == "password123"

    def test_user_registration_username_invalid_chars(self):
        """Test username character validation"""
        invalid_data = {
            "username": "user@name",  # Invalid character
            "password": "password123",
        }

        with pytest.raises(ValueError, match="Username can only contain letters, numbers, hyphens, and underscores"):
            UserRegistrationSchema(**invalid_data)

    def test_user_registration_password_too_short(self):
        """Test password length validation"""
        invalid_data = {
            "username": "testuser",
            "password": "12345",  # Too short
        }

        with pytest.raises(ValueError, match="Password must be at least 6 characters"):
            UserRegistrationSchema(**invalid_data)

    def test_user_registration_password_no_digit(self):
        """Test password digit requirement"""
        invalid_data = {
            "username": "testuser",
            "password": "password",  # No digit
        }

        with pytest.raises(ValueError, match="Password must contain at least one digit"):
            UserRegistrationSchema(**invalid_data)


class TestAPIValidationIntegration:
    """Test validation integration with API endpoints"""

    def test_api_validation_error_response(self, client):
        """Test that API returns proper validation error"""
        invalid_data = {
            "userId": "",  # Should trigger validation error
            "lessonName": "test-lesson",
            "isSuccessful": True,
            "solutionContent": "test",
        }

        response = client.post("/api/insertTaskSolution", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "detail" in error_data
        # Should contain validation error details
        assert len(error_data["detail"]) > 0

    def test_api_validation_success_response(self, client, test_db):
        """Test that API accepts valid data"""
        # Setup test data first
        from models import User, Course, Lesson, Topic, Task

        user = User(internal_user_id="test-user-123", hashed_sub="hash123", username="testuser")
        test_db.add(user)
        test_db.commit()

        course = Course(title="Course", description="Test", professor_id=user.id)
        test_db.add(course)
        test_db.commit()

        lesson = Lesson(title="Lesson", description="Test", course_id=course.id, lesson_order=1)
        test_db.add(lesson)
        test_db.commit()

        topic = Topic(
            title="Topic",
            background="bg",
            objectives="obj",
            content_file_md="test.md",
            concepts="concepts",
            lesson_id=lesson.id,
            topic_order=1,
        )
        test_db.add(topic)
        test_db.commit()

        task = Task(
            task_name="Task", task_link="test-task-link", points=5, type="task", order=1, data={}, topic_id=topic.id
        )
        test_db.add(task)
        test_db.commit()

        # Now test with valid data
        valid_data = {
            "userId": "test-user-123",
            "lessonName": "test-task-link",
            "isSuccessful": True,
            "solutionContent": "print('valid solution')",
        }

        response = client.post("/api/insertTaskSolution", json=valid_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Task attempt recorded successfully"
