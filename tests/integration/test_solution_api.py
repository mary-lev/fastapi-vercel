import pytest
from fastapi import status
from models import User, Task, TaskSolution, TaskAttempt, Course, Lesson, Topic


class TestSolutionAPI:
    """Test solution API endpoints"""

    @pytest.fixture
    def setup_test_data(self, test_db):
        """Setup test data for solution API tests"""
        # Create user
        user = User(internal_user_id="test-user-123", hashed_sub="hash123", username="testuser")
        test_db.add(user)
        test_db.commit()

        # Create course hierarchy
        course = Course(title="Test Course", description="Test", professor_id=user.id)
        test_db.add(course)
        test_db.commit()

        lesson = Lesson(title="Test Lesson", description="Test", course_id=course.id, lesson_order=1)
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
            task_link="test-task-link",
            points=10,
            type="task",
            order=1,
            data={"question": "What is 2+2?"},
            topic_id=topic.id,
        )
        test_db.add(task)
        test_db.commit()

        return {"user": user, "course": course, "lesson": lesson, "topic": topic, "task": task}

    def test_insert_task_solution_success(self, client, setup_test_data):
        """Test successful task solution insertion"""
        solution_data = {
            "userId": "test-user-123",
            "lessonName": "test-task-link",
            "isSuccessful": True,
            "solutionContent": "print('Hello World')",
        }

        response = client.post("/api/insertTaskSolution", json=solution_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Task attempt recorded successfully"

    def test_insert_task_solution_invalid_user(self, client, setup_test_data):
        """Test task solution with invalid user ID"""
        solution_data = {
            "userId": "invalid-user-id",
            "lessonName": "test-task-link",
            "isSuccessful": True,
            "solutionContent": "print('test')",
        }

        response = client.post("/api/insertTaskSolution", json=solution_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in response.json()["detail"]

    def test_insert_task_solution_invalid_task(self, client, setup_test_data):
        """Test task solution with invalid task link"""
        solution_data = {
            "userId": "test-user-123",
            "lessonName": "invalid-task-link",
            "isSuccessful": True,
            "solutionContent": "print('test')",
        }

        response = client.post("/api/insertTaskSolution", json=solution_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Task not found" in response.json()["detail"]

    def test_insert_task_solution_validation_error(self, client):
        """Test task solution with invalid data"""
        # Missing required fields
        invalid_data = {
            "userId": "",  # Empty user ID should fail validation
            "lessonName": "test-task",
            "isSuccessful": True,
        }

        response = client.post("/api/insertTaskSolution", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_topic_solutions_success(self, client, setup_test_data, test_db):
        """Test getting topic solutions for user"""
        # First insert a solution
        task = setup_test_data["task"]
        user = setup_test_data["user"]

        solution = TaskSolution(user_id=user.id, task_id=task.id, solution_content="test solution")
        test_db.add(solution)
        test_db.commit()

        response = client.get("/api/getTopicSolutions/test-user-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "topics" in data
        assert len(data["topics"]) > 0

        topic_data = data["topics"][0]
        assert "topic_name" in topic_data
        assert "total_tasks" in topic_data
        assert "solved_tasks" in topic_data

    def test_get_topic_solutions_invalid_user(self, client):
        """Test getting topic solutions for invalid user"""
        response = client.get("/api/getTopicSolutions/invalid-user-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in response.json()["detail"]

    def test_get_course_task_overview_success(self, client, setup_test_data):
        """Test getting course task overview"""
        course = setup_test_data["course"]

        response = client.get(f"/api/getCourseTaskOverview/{course.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tasks_by_topic" in data
        assert len(data["tasks_by_topic"]) > 0

        task_data = data["tasks_by_topic"][0]
        assert "task_name" in task_data
        assert "topic_name" in task_data
        assert "total_attempts" in task_data

    def test_get_course_task_overview_invalid_course(self, client):
        """Test getting task overview for invalid course"""
        response = client.get("/api/getCourseTaskOverview/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Course not found" in response.json()["detail"]

    def test_get_user_solutions_success(self, client, setup_test_data, test_db):
        """Test getting all user solutions"""
        user = setup_test_data["user"]
        task = setup_test_data["task"]

        # Create a solution
        solution = TaskSolution(user_id=user.id, task_id=task.id, solution_content="test solution")
        test_db.add(solution)
        test_db.commit()

        response = client.get("/api/getUserSolutions/test-user-123")

        assert response.status_code == status.HTTP_200_OK
        solutions = response.json()
        assert len(solutions) == 1
        assert solutions[0]["solution_content"] == "test solution"

    def test_multiple_task_attempts(self, client, setup_test_data, test_db):
        """Test multiple attempts for same task"""
        solution_data = {
            "userId": "test-user-123",
            "lessonName": "test-task-link",
            "isSuccessful": False,
            "solutionContent": "print('attempt 1')",
        }

        # First attempt
        response1 = client.post("/api/insertTaskSolution", json=solution_data)
        assert response1.status_code == status.HTTP_200_OK

        # Second attempt
        solution_data["solutionContent"] = "print('attempt 2')"
        solution_data["isSuccessful"] = True

        response2 = client.post("/api/insertTaskSolution", json=solution_data)
        assert response2.status_code == status.HTTP_200_OK

        # Check attempts were recorded
        user = setup_test_data["user"]
        task = setup_test_data["task"]

        attempts = (
            test_db.query(TaskAttempt).filter(TaskAttempt.user_id == user.id, TaskAttempt.task_id == task.id).all()
        )

        assert len(attempts) == 2
        assert attempts[0].attempt_number == 1
        assert attempts[1].attempt_number == 2
        assert not attempts[0].is_successful
        assert attempts[1].is_successful
