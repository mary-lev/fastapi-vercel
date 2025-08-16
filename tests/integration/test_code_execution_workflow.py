"""
Comprehensive Integration Tests for Code Execution Workflows
Tests the complete end-to-end flow of code execution with security validation
"""

import pytest
import time
from fastapi import status
from models import User, Task, Course, Lesson, Topic, TaskAttempt, TaskSolution
from utils.rate_limiting import rate_limiter


class TestCodeExecutionWorkflow:
    """Test complete code execution workflows"""

    @pytest.fixture
    def setup_code_execution_test_data(self, test_db):
        """Setup test data for code execution tests"""
        # Create user
        user = User(
            internal_user_id="code-test-user-123",
            hashed_sub="hash123",
            username="codetestuser",
            status="student"
        )
        test_db.add(user)
        test_db.commit()

        # Create course hierarchy
        course = Course(title="Programming Course", description="Python Programming", professor_id=user.id)
        test_db.add(course)
        test_db.commit()

        lesson = Lesson(title="Python Basics", description="Introduction to Python", course_id=course.id, lesson_order=1)
        test_db.add(lesson)
        test_db.commit()

        topic = Topic(
            title="Variables and Functions",
            background="Learn about variables",
            objectives="Understand variables and functions",
            content_file_md="variables.md",
            concepts="variables, functions",
            lesson_id=lesson.id,
            topic_order=1,
        )
        test_db.add(topic)
        test_db.commit()

        # Create a code task
        code_task = Task(
            task_name="Hello World",
            task_link="hello-world-task",
            points=10,
            type="CodeTask",
            order=1,
            data={
                "question": "Write a program that prints 'Hello, World!'",
                "test_cases": [
                    {"input": "", "expected_output": "Hello, World!\\n"}
                ]
            },
            topic_id=topic.id,
        )
        test_db.add(code_task)
        test_db.commit()

        return {"user": user, "course": course, "lesson": lesson, "topic": topic, "task": code_task}

    def test_complete_code_execution_workflow_success(self, client, setup_code_execution_test_data):
        """Test complete successful code execution workflow"""
        user = setup_code_execution_test_data["user"]
        task = setup_code_execution_test_data["task"]
        
        # Step 1: Compile safe code
        compile_request = {
            "code": "print('Hello, World!')",
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=compile_request)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["status"] == "success"
        assert "Hello, World!" in result["output"]
        
        # Step 2: Submit code solution
        submit_request = {
            "code": "print('Hello, World!')",
            "task_id": task.id,
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-code", json=submit_request)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["is_correct"] == True
        assert result["attempt_number"] == 1
        
        # Step 3: Verify solution was saved
        response = client.get(f"/api/v1/students/{user.internal_user_id}/solutions?task_id={task.id}")
        
        assert response.status_code == status.HTTP_200_OK
        solutions = response.json()
        assert len(solutions) == 1
        assert solutions[0]["task_id"] == task.id

    def test_security_violation_workflow(self, client, setup_code_execution_test_data):
        """Test workflow when security violations occur"""
        user = setup_code_execution_test_data["user"]
        
        # Reset rate limiter for clean test
        rate_limiter.violations.clear()
        rate_limiter.blocked_users.clear()
        
        # Attempt 1: Try dangerous code
        dangerous_code = {
            "code": "import os; os.system('rm -rf /')",
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=dangerous_code)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Security validation failed" in response.json()["detail"]
        
        # Attempt 2: Another dangerous code to increase violation count
        dangerous_code2 = {
            "code": "exec('malicious code')",
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=dangerous_code2)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Security validation failed" in response.json()["detail"]

    def test_rate_limiting_workflow(self, client, setup_code_execution_test_data):
        """Test rate limiting workflow"""
        user = setup_code_execution_test_data["user"]
        
        # Reset rate limiter for clean test
        rate_limiter.requests.clear()
        rate_limiter.violations.clear()
        rate_limiter.blocked_users.clear()
        
        safe_code = {
            "code": "print('test')",
            "language": "python"
        }
        
        # Make many requests to trigger rate limit (30 requests per 5 minutes)
        success_count = 0
        for i in range(35):  # Exceed the limit
            response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=safe_code)
            
            if response.status_code == status.HTTP_200_OK:
                success_count += 1
            elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                assert "Rate limit exceeded" in response.json()["detail"]
                break
        
        # Should have succeeded for the first 30 requests, then hit rate limit
        assert success_count == 30

    def test_multiple_code_submission_attempts(self, client, setup_code_execution_test_data, test_db):
        """Test multiple submission attempts for the same task"""
        user = setup_code_execution_test_data["user"]
        task = setup_code_execution_test_data["task"]
        
        # Attempt 1: Incorrect solution
        incorrect_request = {
            "code": "print('Wrong answer')",
            "task_id": task.id,
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-code", json=incorrect_request)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["is_correct"] == False
        assert result["attempt_number"] == 1
        
        # Attempt 2: Correct solution
        correct_request = {
            "code": "print('Hello, World!')",
            "task_id": task.id,
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-code", json=correct_request)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["is_correct"] == True
        assert result["attempt_number"] == 2
        
        # Verify both attempts are recorded
        attempts = test_db.query(TaskAttempt).filter(
            TaskAttempt.user_id == user.id,
            TaskAttempt.task_id == task.id
        ).all()
        
        assert len(attempts) == 2
        assert attempts[0].attempt_number == 1
        assert attempts[0].is_successful == False
        assert attempts[1].attempt_number == 2
        assert attempts[1].is_successful == True

    def test_text_submission_workflow(self, client, setup_code_execution_test_data, test_db):
        """Test text answer submission workflow"""
        user = setup_code_execution_test_data["user"]
        
        # Create a quiz task
        quiz_task = Task(
            task_name="Python Quiz",
            task_link="python-quiz-task",
            points=5,
            type="TrueFalseQuiz",
            order=2,
            data={
                "question": "Python is a programming language. True or False?",
                "correct_answer": "True"
            },
            topic_id=setup_code_execution_test_data["topic"].id,
        )
        test_db.add(quiz_task)
        test_db.commit()
        
        # Submit correct answer
        text_request = {
            "user_answer": "True",
            "task_id": quiz_task.id
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-text", json=text_request)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["is_correct"] == True
        assert result["attempt_number"] == 1

    def test_xss_protection_in_text_submission(self, client, setup_code_execution_test_data):
        """Test XSS protection in text submissions"""
        user = setup_code_execution_test_data["user"]
        task = setup_code_execution_test_data["task"]
        
        # Attempt XSS attack
        xss_request = {
            "user_answer": "<script>alert('xss')</script>",
            "task_id": task.id
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-text", json=xss_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Input validation failed" in response.json()["detail"]

    def test_sql_injection_protection_in_text_submission(self, client, setup_code_execution_test_data):
        """Test SQL injection protection in text submissions"""
        user = setup_code_execution_test_data["user"]
        task = setup_code_execution_test_data["task"]
        
        # Attempt SQL injection
        sql_injection_request = {
            "user_answer": "'; DROP TABLE users; --",
            "task_id": task.id
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-text", json=sql_injection_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Input validation failed" in response.json()["detail"]

    def test_user_progress_tracking_workflow(self, client, setup_code_execution_test_data, test_db):
        """Test complete user progress tracking workflow"""
        user = setup_code_execution_test_data["user"]
        course = setup_code_execution_test_data["course"]
        lesson = setup_code_execution_test_data["lesson"]
        task = setup_code_execution_test_data["task"]
        
        # Enroll user in course
        enrollment_request = {
            "course_id": course.id
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/enroll", json=enrollment_request)
        assert response.status_code == status.HTTP_200_OK
        
        # Check initial progress
        response = client.get(f"/api/v1/students/{user.internal_user_id}/courses/{course.id}/progress")
        
        assert response.status_code == status.HTTP_200_OK
        progress = response.json()
        assert progress["total_tasks"] == 1
        assert progress["completed_tasks"] == 0
        assert progress["completion_percentage"] == 0.0
        
        # Complete the task
        submit_request = {
            "code": "print('Hello, World!')",
            "task_id": task.id,
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/submit-code", json=submit_request)
        assert response.status_code == status.HTTP_200_OK
        
        # Check updated progress
        response = client.get(f"/api/v1/students/{user.internal_user_id}/courses/{course.id}/progress")
        
        assert response.status_code == status.HTTP_200_OK
        progress = response.json()
        assert progress["total_tasks"] == 1
        assert progress["completed_tasks"] == 1
        assert progress["completion_percentage"] == 100.0
        assert progress["points_earned"] == 10

    def test_concurrent_user_isolation(self, client, test_db):
        """Test that multiple users are properly isolated"""
        # Create two users
        user1 = User(internal_user_id="user1", hashed_sub="hash1", username="user1", status="student")
        user2 = User(internal_user_id="user2", hashed_sub="hash2", username="user2", status="student")
        test_db.add_all([user1, user2])
        test_db.commit()
        
        # Create course structure
        course = Course(title="Isolation Test", description="Test", professor_id=user1.id)
        test_db.add(course)
        test_db.commit()
        
        lesson = Lesson(title="Test Lesson", description="Test", course_id=course.id, lesson_order=1)
        test_db.add(lesson)
        test_db.commit()
        
        topic = Topic(
            title="Test Topic", lesson_id=lesson.id, topic_order=1,
            background="Test", objectives="Test", content_file_md="test.md", concepts="test"
        )
        test_db.add(topic)
        test_db.commit()
        
        task = Task(
            task_name="Isolation Task", task_link="isolation-task", points=10,
            type="CodeTask", order=1, data={"question": "Test"}, topic_id=topic.id
        )
        test_db.add(task)
        test_db.commit()
        
        # Both users submit different solutions
        solution1 = {
            "code": "print('User 1 solution')",
            "task_id": task.id,
            "language": "python"
        }
        
        solution2 = {
            "code": "print('User 2 solution')",
            "task_id": task.id,
            "language": "python"
        }
        
        # Submit as user1
        response1 = client.post(f"/api/v1/students/{user1.internal_user_id}/submit-code", json=solution1)
        assert response1.status_code == status.HTTP_200_OK
        
        # Submit as user2
        response2 = client.post(f"/api/v1/students/{user2.internal_user_id}/submit-code", json=solution2)
        assert response2.status_code == status.HTTP_200_OK
        
        # Check that solutions are properly isolated
        response1 = client.get(f"/api/v1/students/{user1.internal_user_id}/solutions?task_id={task.id}")
        assert response1.status_code == status.HTTP_200_OK
        user1_solutions = response1.json()
        assert len(user1_solutions) == 1
        assert "User 1 solution" in user1_solutions[0]["solution_data"]
        
        response2 = client.get(f"/api/v1/students/{user2.internal_user_id}/solutions?task_id={task.id}")
        assert response2.status_code == status.HTTP_200_OK
        user2_solutions = response2.json()
        assert len(user2_solutions) == 1
        assert "User 2 solution" in user2_solutions[0]["solution_data"]

    def test_error_recovery_workflow(self, client, setup_code_execution_test_data):
        """Test error recovery and graceful handling"""
        user = setup_code_execution_test_data["user"]
        
        # Test syntax error recovery
        syntax_error_code = {
            "code": "print('missing quote)",
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=syntax_error_code)
        
        assert response.status_code == status.HTTP_200_OK  # Should not crash
        result = response.json()
        assert result["status"] == "error"
        assert "error" in result or "output" in result
        
        # Test that user can still submit valid code after error
        valid_code = {
            "code": "print('Hello, World!')",
            "language": "python"
        }
        
        response = client.post(f"/api/v1/students/{user.internal_user_id}/compile", json=valid_code)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["status"] == "success"
        assert "Hello, World!" in result["output"]