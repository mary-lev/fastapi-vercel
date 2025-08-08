import pytest
from sqlalchemy.exc import IntegrityError
from models import User, Task, TaskSolution, TaskAttempt, Course, Lesson, Topic, UserStatus


class TestUserModel:
    """Test User model operations"""

    def test_create_user(self, test_db, sample_user_data):
        """Test creating a user"""
        user = User(**sample_user_data)
        test_db.add(user)
        test_db.commit()

        assert user.id is not None
        assert user.internal_user_id == "test-user-123"
        assert user.username == "testuser"

    def test_user_unique_hashed_sub(self, test_db):
        """Test that hashed_sub must be unique"""
        user1 = User(internal_user_id="user1", hashed_sub="same_hash", username="user1")
        user2 = User(internal_user_id="user2", hashed_sub="same_hash", username="user2")

        test_db.add(user1)
        test_db.commit()

        test_db.add(user2)
        with pytest.raises(IntegrityError):
            test_db.commit()


class TestTaskModel:
    """Test polymorphic Task model"""

    def test_create_task(self, test_db):
        """Test creating a basic task"""
        # First create required dependencies
        course = Course(title="Test Course", description="Test", professor_id=1)
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

        assert task.id is not None
        assert task.task_name == "Test Task"
        assert task.points == 10
        assert task.is_active == True  # Default value


class TestTaskSolutionModel:
    """Test TaskSolution model"""

    def test_create_task_solution(self, test_db):
        """Test creating a task solution"""
        # Create dependencies
        user = User(internal_user_id="test-user", hashed_sub="hash123", username="testuser")
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

        task = Task(task_name="Task", task_link="task-link", points=5, type="task", order=1, data={}, topic_id=topic.id)
        test_db.add(task)
        test_db.commit()

        solution = TaskSolution(user_id=user.id, task_id=task.id, solution_content="print('solution')")
        test_db.add(solution)
        test_db.commit()

        assert solution.id is not None
        assert solution.solution_content == "print('solution')"
        assert solution.completed_at is not None


class TestCourseHierarchy:
    """Test Course -> Lesson -> Topic -> Task hierarchy"""

    def test_course_lesson_relationship(self, test_db):
        """Test Course-Lesson relationship"""
        course = Course(title="Test Course", description="Test", professor_id=1)
        test_db.add(course)
        test_db.commit()

        lesson1 = Lesson(title="Lesson 1", description="Test", course_id=course.id, lesson_order=1)
        lesson2 = Lesson(title="Lesson 2", description="Test", course_id=course.id, lesson_order=2)

        test_db.add_all([lesson1, lesson2])
        test_db.commit()

        # Test relationship
        assert len(course.lessons) == 2
        assert lesson1.course == course
        assert lesson2.course == course

    def test_lesson_topic_relationship(self, test_db):
        """Test Lesson-Topic relationship"""
        course = Course(title="Course", description="Test", professor_id=1)
        test_db.add(course)
        test_db.commit()

        lesson = Lesson(title="Lesson", description="Test", course_id=course.id, lesson_order=1)
        test_db.add(lesson)
        test_db.commit()

        topic1 = Topic(
            title="Topic 1",
            background="bg1",
            objectives="obj1",
            content_file_md="topic1.md",
            concepts="concepts1",
            lesson_id=lesson.id,
            topic_order=1,
        )
        topic2 = Topic(
            title="Topic 2",
            background="bg2",
            objectives="obj2",
            content_file_md="topic2.md",
            concepts="concepts2",
            lesson_id=lesson.id,
            topic_order=2,
        )

        test_db.add_all([topic1, topic2])
        test_db.commit()

        # Test relationship
        assert len(lesson.topics) == 2
        assert topic1.lesson == lesson
        assert topic2.lesson == lesson
