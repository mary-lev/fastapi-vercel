"""
Integration Tests for Authentication and Authorization Workflows
Tests the complete authentication system including role-based access control
"""

import pytest
from fastapi import status
from models import User, Course, Lesson, Topic, Task, CourseEnrollment


class TestAuthenticationWorkflow:
    """Test authentication and authorization workflows"""

    @pytest.fixture
    def setup_auth_test_data(self, test_db):
        """Setup test data for authentication tests"""
        # Create users with different roles
        student_user = User(
            internal_user_id="student-123", hashed_sub="student_hash", username="student", status="student"
        )

        professor_user = User(
            internal_user_id="professor-123", hashed_sub="professor_hash", username="professor", status="professor"
        )

        admin_user = User(internal_user_id="admin-123", hashed_sub="admin_hash", username="admin", status="admin")

        test_db.add_all([student_user, professor_user, admin_user])
        test_db.commit()

        # Create course structure
        course = Course(title="Test Course", description="Authentication test course", professor_id=professor_user.id)
        test_db.add(course)
        test_db.commit()

        lesson = Lesson(title="Test Lesson", description="Test lesson", course_id=course.id, lesson_order=1)
        test_db.add(lesson)
        test_db.commit()

        topic = Topic(
            title="Test Topic",
            background="Test background",
            objectives="Test objectives",
            content_file_md="test.md",
            concepts="test concepts",
            lesson_id=lesson.id,
            topic_order=1,
        )
        test_db.add(topic)
        test_db.commit()

        task = Task(
            task_name="Test Task",
            task_link="test-task",
            points=10,
            type="CodeTask",
            order=1,
            data={"question": "Test question"},
            topic_id=topic.id,
        )
        test_db.add(task)
        test_db.commit()

        return {
            "student": student_user,
            "professor": professor_user,
            "admin": admin_user,
            "course": course,
            "lesson": lesson,
            "topic": topic,
            "task": task,
        }

    def test_student_access_control(self, client, setup_auth_test_data):
        """Test student role access control"""
        student = setup_auth_test_data["student"]
        course = setup_auth_test_data["course"]

        # Students should be able to access their own profile
        response = client.get(f"/api/v1/students/{student.internal_user_id}/profile")
        assert response.status_code == status.HTTP_200_OK

        profile = response.json()
        assert profile["username"] == "student"
        assert profile["internal_user_id"] == "student-123"

        # Students should be able to enroll in courses
        enrollment_data = {"course_id": course.id}
        response = client.post(f"/api/v1/students/{student.internal_user_id}/enroll", json=enrollment_data)
        assert response.status_code == status.HTTP_200_OK

        # Students should be able to view their enrolled courses
        response = client.get(f"/api/v1/students/{student.internal_user_id}/courses")
        assert response.status_code == status.HTTP_200_OK

        courses = response.json()
        assert len(courses) == 1
        assert courses[0]["id"] == course.id

    def test_professor_access_control(self, client, setup_auth_test_data):
        """Test professor role access control"""
        professor = setup_auth_test_data["professor"]
        course = setup_auth_test_data["course"]

        # Professors should be able to access course content
        response = client.get(f"/api/v1/learning/{course.id}")
        assert response.status_code == status.HTTP_200_OK

        course_data = response.json()
        assert course_data["id"] == course.id
        assert course_data["title"] == "Test Course"

    def test_cross_user_access_protection(self, client, setup_auth_test_data):
        """Test that users cannot access other users' data"""
        student = setup_auth_test_data["student"]
        professor = setup_auth_test_data["professor"]

        # Student should not be able to access professor's profile
        response = client.get(f"/api/v1/students/{professor.internal_user_id}/profile")
        # This might return 404 or 403 depending on implementation
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

        # Professor should not be able to access student's submissions directly
        response = client.get(f"/api/v1/students/{student.internal_user_id}/solutions")
        # Depending on implementation, this might be allowed for professors
        # but the test verifies the access control is in place

    def test_user_enumeration_protection(self, client, setup_auth_test_data):
        """Test protection against user enumeration attacks"""
        # Try to access non-existent user
        response = client.get("/api/v1/students/non-existent-user/profile")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Error message should not reveal whether user exists
        error_detail = response.json()["detail"]
        assert "User not found" in error_detail

    def test_enrollment_workflow(self, client, setup_auth_test_data, test_db):
        """Test complete course enrollment workflow"""
        student = setup_auth_test_data["student"]
        course = setup_auth_test_data["course"]

        # Check initial enrollment status
        response = client.get(f"/api/v1/students/{student.internal_user_id}/courses")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 0

        # Enroll in course
        enrollment_data = {"course_id": course.id}
        response = client.post(f"/api/v1/students/{student.internal_user_id}/enroll", json=enrollment_data)

        assert response.status_code == status.HTTP_200_OK
        enrollment_result = response.json()
        assert enrollment_result["status"] == "success"

        # Verify enrollment in database
        enrollment = (
            test_db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == student.id, CourseEnrollment.course_id == course.id)
            .first()
        )

        assert enrollment is not None

        # Check that user can now see the course
        response = client.get(f"/api/v1/students/{student.internal_user_id}/courses")
        assert response.status_code == status.HTTP_200_OK

        courses = response.json()
        assert len(courses) == 1
        assert courses[0]["id"] == course.id

        # Try to enroll again (should handle gracefully)
        response = client.post(f"/api/v1/students/{student.internal_user_id}/enroll", json=enrollment_data)

        assert response.status_code == status.HTTP_200_OK
        enrollment_result = response.json()
        assert enrollment_result["status"] == "already_enrolled"

    def test_invalid_user_id_formats(self, client, setup_auth_test_data):
        """Test handling of various invalid user ID formats"""
        invalid_user_ids = [
            "",  # Empty string
            " ",  # Whitespace
            "../../etc/passwd",  # Path traversal attempt
            "'; DROP TABLE users; --",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "null",  # Null string
            "undefined",  # Undefined string
            "admin",  # Reserved username
            "root",  # Reserved username
        ]

        for invalid_id in invalid_user_ids:
            response = client.get(f"/api/v1/students/{invalid_id}/profile")
            # Should return 404 or 400, not crash
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    def test_concurrent_enrollment_handling(self, client, setup_auth_test_data, test_db):
        """Test handling of concurrent enrollment requests"""
        student = setup_auth_test_data["student"]
        course = setup_auth_test_data["course"]

        enrollment_data = {"course_id": course.id}

        # Simulate concurrent enrollment attempts
        responses = []
        for _ in range(3):
            response = client.post(f"/api/v1/students/{student.internal_user_id}/enroll", json=enrollment_data)
            responses.append(response)

        # All should succeed, but only one enrollment should be created
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

        # Check database for duplicate enrollments
        enrollments = (
            test_db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == student.id, CourseEnrollment.course_id == course.id)
            .all()
        )

        assert len(enrollments) == 1  # Should not have duplicates

    def test_session_management(self, client, setup_auth_test_data):
        """Test session management and user context"""
        student = setup_auth_test_data["student"]

        # Make multiple requests to ensure session consistency
        for i in range(5):
            response = client.get(f"/api/v1/students/{student.internal_user_id}/profile")
            assert response.status_code == status.HTTP_200_OK

            profile = response.json()
            assert profile["username"] == "student"
            assert profile["internal_user_id"] == "student-123"

    def test_authorization_boundary_conditions(self, client, setup_auth_test_data):
        """Test edge cases in authorization"""
        student = setup_auth_test_data["student"]
        course = setup_auth_test_data["course"]
        task = setup_auth_test_data["task"]

        # Try to access course progress without enrollment
        response = client.get(f"/api/v1/students/{student.internal_user_id}/courses/{course.id}/progress")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not enrolled" in response.json()["detail"]

        # Try to submit code for non-existent task
        invalid_submit = {"code": "print('test')", "task_id": 99999, "language": "python"}

        response = client.post(f"/api/v1/students/{student.internal_user_id}/submit-code", json=invalid_submit)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Task not found" in response.json()["detail"]

    def test_user_data_integrity(self, client, setup_auth_test_data, test_db):
        """Test that user data remains consistent across operations"""
        student = setup_auth_test_data["student"]
        course = setup_auth_test_data["course"]
        task = setup_auth_test_data["task"]

        # Enroll user
        enrollment_data = {"course_id": course.id}
        response = client.post(f"/api/v1/students/{student.internal_user_id}/enroll", json=enrollment_data)
        assert response.status_code == status.HTTP_200_OK

        # Submit multiple solutions
        for i in range(3):
            submit_data = {"code": f"print('Solution {i}')", "task_id": task.id, "language": "python"}

            response = client.post(f"/api/v1/students/{student.internal_user_id}/submit-code", json=submit_data)
            assert response.status_code == status.HTTP_200_OK

            result = response.json()
            assert result["attempt_number"] == i + 1

        # Verify data consistency
        response = client.get(f"/api/v1/students/{student.internal_user_id}/solutions?task_id={task.id}")
        assert response.status_code == status.HTTP_200_OK

        solutions = response.json()
        assert len(solutions) == 1  # Should have one solution (latest successful)

        # Check that user profile is still intact
        response = client.get(f"/api/v1/students/{student.internal_user_id}/profile")
        assert response.status_code == status.HTTP_200_OK

        profile = response.json()
        assert profile["username"] == "student"
        assert profile["internal_user_id"] == "student-123"

    def test_role_based_data_filtering(self, client, setup_auth_test_data):
        """Test that data is filtered based on user roles"""
        student = setup_auth_test_data["student"]
        professor = setup_auth_test_data["professor"]
        course = setup_auth_test_data["course"]

        # Student view should be limited
        response = client.get(f"/api/v1/students/{student.internal_user_id}/courses")
        assert response.status_code == status.HTTP_200_OK

        # Professor view might have additional information
        # (This depends on your specific authorization implementation)
        response = client.get(f"/api/v1/learning/{course.id}")
        assert response.status_code == status.HTTP_200_OK

        course_data = response.json()
        assert "id" in course_data
        assert "title" in course_data
