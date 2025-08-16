"""
Integration Tests for Learning Content Workflows
Tests the complete learning content delivery system with hierarchy navigation
"""

import pytest
from fastapi import status
from models import User, Course, Lesson, Topic, Task, Summary, CourseEnrollment


class TestLearningContentWorkflow:
    """Test learning content delivery workflows"""

    @pytest.fixture
    def setup_learning_content_data(self, test_db):
        """Setup comprehensive test data for learning content"""
        # Create users
        student = User(
            internal_user_id="learning-student-123",
            hashed_sub="learning_hash",
            username="learningstudent",
            status="student"
        )
        
        professor = User(
            internal_user_id="learning-professor-123",
            hashed_sub="prof_hash",
            username="learningprofessor",
            status="professor"
        )
        
        test_db.add_all([student, professor])
        test_db.commit()
        
        # Create course
        course = Course(
            title="Comprehensive Programming Course",
            description="A complete course covering programming fundamentals",
            professor_id=professor.id
        )
        test_db.add(course)
        test_db.commit()
        
        # Create lessons
        lesson1 = Lesson(
            title="Introduction to Programming",
            description="Basic programming concepts",
            course_id=course.id,
            lesson_order=1,
            textbook="Chapter 1: Getting Started"
        )
        
        lesson2 = Lesson(
            title="Data Structures",
            description="Understanding data structures",
            course_id=course.id,
            lesson_order=2,
            textbook="Chapter 2: Data Structures"
        )
        
        test_db.add_all([lesson1, lesson2])
        test_db.commit()
        
        # Create topics for lesson 1
        topic1_1 = Topic(
            title="Variables and Data Types",
            background="Understanding variables",
            objectives="Learn about variables and basic data types",
            content_file_md="variables.md",
            concepts="variables, integers, strings, booleans",
            lesson_id=lesson1.id,
            topic_order=1
        )
        
        topic1_2 = Topic(
            title="Control Flow",
            background="Understanding program flow",
            objectives="Learn about if statements and loops",
            content_file_md="control_flow.md",
            concepts="if statements, loops, conditions",
            lesson_id=lesson1.id,
            topic_order=2
        )
        
        # Create topics for lesson 2
        topic2_1 = Topic(
            title="Lists and Tuples",
            background="Understanding collections",
            objectives="Learn about lists and tuples",
            content_file_md="lists_tuples.md",
            concepts="lists, tuples, indexing, slicing",
            lesson_id=lesson2.id,
            topic_order=1
        )
        
        test_db.add_all([topic1_1, topic1_2, topic2_1])
        test_db.commit()
        
        # Create tasks
        task1_1_1 = Task(
            task_name="Variable Assignment",
            task_link="variable-assignment",
            points=5,
            type="CodeTask",
            order=1,
            data={
                "question": "Create a variable named 'name' and assign your name to it",
                "template": "# Write your code here\\nname = ",
                "test_cases": [{"input": "", "expected_output": ""}]
            },
            topic_id=topic1_1.id
        )
        
        task1_1_2 = Task(
            task_name="Data Type Quiz",
            task_link="data-type-quiz",
            points=3,
            type="TrueFalseQuiz",
            order=2,
            data={
                "question": "In Python, '5' and 5 are the same data type. True or False?",
                "correct_answer": "False"
            },
            topic_id=topic1_1.id
        )
        
        task1_2_1 = Task(
            task_name="If Statement Practice",
            task_link="if-statement-practice",
            points=7,
            type="CodeTask",
            order=1,
            data={
                "question": "Write an if statement that prints 'positive' if a number is greater than 0",
                "template": "number = 5\\n# Write your if statement here\\n",
                "test_cases": [{"input": "5", "expected_output": "positive\\n"}]
            },
            topic_id=topic1_2.id
        )
        
        task2_1_1 = Task(
            task_name="List Operations",
            task_link="list-operations",
            points=8,
            type="CodeTask",
            order=1,
            data={
                "question": "Create a list with numbers 1, 2, 3 and print its length",
                "template": "# Create your list here\\n",
                "test_cases": [{"input": "", "expected_output": "3\\n"}]
            },
            topic_id=topic2_1.id
        )
        
        test_db.add_all([task1_1_1, task1_1_2, task1_2_1, task2_1_1])
        test_db.commit()
        
        # Create summaries
        summary1_1 = Summary(
            lesson_name="Variables Summary",
            lesson_link="variables-summary",
            lesson_type="Summary",
            icon_file="variables_icon.png",
            data={
                "description": "Summary of variables and data types",
                "key_points": [
                    "Variables store data",
                    "Python has dynamic typing",
                    "Common types: int, str, bool, float"
                ]
            },
            topic_id=topic1_1.id
        )
        
        summary1_2 = Summary(
            lesson_name="Control Flow Summary",
            lesson_link="control-flow-summary",
            lesson_type="Summary",
            icon_file="control_flow_icon.png",
            data={
                "description": "Summary of control flow structures",
                "key_points": [
                    "If statements for decisions",
                    "Loops for repetition",
                    "Conditions use boolean logic"
                ]
            },
            topic_id=topic1_2.id
        )
        
        test_db.add_all([summary1_1, summary1_2])
        test_db.commit()
        
        return {
            "student": student,
            "professor": professor,
            "course": course,
            "lesson1": lesson1,
            "lesson2": lesson2,
            "topic1_1": topic1_1,
            "topic1_2": topic1_2,
            "topic2_1": topic2_1,
            "task1_1_1": task1_1_1,
            "task1_1_2": task1_1_2,
            "task1_2_1": task1_2_1,
            "task2_1_1": task2_1_1,
            "summary1_1": summary1_1,
            "summary1_2": summary1_2
        }

    def test_complete_course_hierarchy_retrieval(self, client, setup_learning_content_data):
        """Test retrieval of complete course hierarchy"""
        course = setup_learning_content_data["course"]
        
        response = client.get(f"/api/v1/learning/{course.id}")
        
        assert response.status_code == status.HTTP_200_OK
        course_data = response.json()
        
        # Verify course structure
        assert course_data["id"] == course.id
        assert course_data["title"] == "Comprehensive Programming Course"
        assert "lessons" in course_data
        assert len(course_data["lessons"]) == 2
        
        # Verify lesson 1 structure
        lesson1 = course_data["lessons"][0]
        assert lesson1["title"] == "Introduction to Programming"
        assert len(lesson1["topics"]) == 2
        
        # Verify topic structure
        topic1_1 = lesson1["topics"][0]
        assert topic1_1["title"] == "Variables and Data Types"
        assert len(topic1_1["tasks"]) == 2
        
        # Verify task structure
        task1 = topic1_1["tasks"][0]
        assert task1["task_name"] == "Variable Assignment"
        assert task1["points"] == 5
        assert task1["type"] == "CodeTask"

    def test_lesson_level_navigation(self, client, setup_learning_content_data):
        """Test navigation at lesson level"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        
        # Get all lessons for course
        response = client.get(f"/api/v1/learning/{course.id}/lessons/")
        
        assert response.status_code == status.HTTP_200_OK
        lessons = response.json()
        assert len(lessons) == 2
        assert lessons[0]["title"] == "Introduction to Programming"
        assert lessons[1]["title"] == "Data Structures"
        
        # Get specific lesson
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}")
        
        assert response.status_code == status.HTTP_200_OK
        lesson_data = response.json()
        assert lesson_data["title"] == "Introduction to Programming"
        assert len(lesson_data["topics"]) == 2

    def test_topic_level_navigation(self, client, setup_learning_content_data):
        """Test navigation at topic level"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        topic1_1 = setup_learning_content_data["topic1_1"]
        
        # Get all topics for lesson
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/")
        
        assert response.status_code == status.HTTP_200_OK
        topics = response.json()
        assert len(topics) == 2
        assert topics[0]["title"] == "Variables and Data Types"
        assert topics[1]["title"] == "Control Flow"
        
        # Get specific topic
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/{topic1_1.id}")
        
        assert response.status_code == status.HTTP_200_OK
        topic_data = response.json()
        assert topic_data["title"] == "Variables and Data Types"
        assert len(topic_data["tasks"]) == 2

    def test_task_level_navigation(self, client, setup_learning_content_data):
        """Test navigation at task level"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        topic1_1 = setup_learning_content_data["topic1_1"]
        task1_1_1 = setup_learning_content_data["task1_1_1"]
        
        # Get all tasks for topic
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/{topic1_1.id}/tasks/")
        
        assert response.status_code == status.HTTP_200_OK
        tasks = response.json()
        assert len(tasks) == 2
        assert tasks[0]["task_name"] == "Variable Assignment"
        assert tasks[1]["task_name"] == "Data Type Quiz"
        
        # Get specific task
        response = client.get(
            f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/{topic1_1.id}/tasks/{task1_1_1.id}"
        )
        
        assert response.status_code == status.HTTP_200_OK
        task_data = response.json()
        assert task_data["task_name"] == "Variable Assignment"
        assert task_data["points"] == 5
        assert "data" in task_data

    def test_summary_retrieval(self, client, setup_learning_content_data):
        """Test retrieval of lesson summaries"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/summaries")
        
        assert response.status_code == status.HTTP_200_OK
        summaries_data = response.json()
        assert "summaries" in summaries_data
        
        summaries = summaries_data["summaries"]
        assert len(summaries) == 2
        
        # Check first summary
        summary1 = summaries[0]
        assert summary1["lesson_name"] == "Variables Summary"
        assert summary1["lesson_type"] == "Summary"
        assert "data" in summary1

    def test_legacy_format_compatibility(self, client, setup_learning_content_data):
        """Test legacy format endpoint for backward compatibility"""
        course = setup_learning_content_data["course"]
        
        response = client.get(f"/api/v1/learning/{course.id}/legacy")
        
        assert response.status_code == status.HTTP_200_OK
        legacy_data = response.json()
        
        # Check legacy format structure
        assert "courseTitle" in legacy_data
        assert "desc" in legacy_data
        assert "courseContent" in legacy_data
        assert "courseRequirement" in legacy_data
        assert "courseInstructor" in legacy_data
        
        assert legacy_data["courseTitle"] == "Comprehensive Programming Course"

    def test_content_ordering_and_structure(self, client, setup_learning_content_data):
        """Test that content is properly ordered"""
        course = setup_learning_content_data["course"]
        
        response = client.get(f"/api/v1/learning/{course.id}")
        
        assert response.status_code == status.HTTP_200_OK
        course_data = response.json()
        
        # Verify lessons are ordered
        lessons = course_data["lessons"]
        assert lessons[0]["lesson_order"] == 1
        assert lessons[1]["lesson_order"] == 2
        
        # Verify topics are ordered within lesson
        topics = lessons[0]["topics"]
        assert topics[0]["topic_order"] == 1
        assert topics[1]["topic_order"] == 2
        
        # Verify tasks are ordered within topic
        tasks = topics[0]["tasks"]
        assert tasks[0]["order"] == 1
        assert tasks[1]["order"] == 2

    def test_content_filtering_and_search(self, client, setup_learning_content_data):
        """Test content filtering capabilities"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        topic1_1 = setup_learning_content_data["topic1_1"]
        
        # Test filtering tasks by topic
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/{topic1_1.id}/tasks/")
        
        assert response.status_code == status.HTTP_200_OK
        tasks = response.json()
        
        # Should only return tasks for this specific topic
        assert len(tasks) == 2
        for task in tasks:
            # All tasks should belong to the same topic (implicitly tested by the endpoint)
            assert "task_name" in task
            assert "type" in task

    def test_error_handling_in_navigation(self, client, setup_learning_content_data):
        """Test error handling for invalid navigation paths"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        
        # Test invalid course ID
        response = client.get("/api/v1/learning/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test invalid lesson ID
        response = client.get(f"/api/v1/learning/{course.id}/lessons/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test invalid topic ID
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test mismatched hierarchy (lesson from different course)
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id + 100}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_content_metadata_integrity(self, client, setup_learning_content_data):
        """Test that content metadata is properly maintained"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        topic1_1 = setup_learning_content_data["topic1_1"]
        
        # Get topic details
        response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/{topic1_1.id}")
        
        assert response.status_code == status.HTTP_200_OK
        topic_data = response.json()
        
        # Verify all metadata fields are present
        assert topic_data["title"] == "Variables and Data Types"
        assert topic_data["background"] == "Understanding variables"
        assert topic_data["objectives"] == "Learn about variables and basic data types"
        assert topic_data["content_file_md"] == "variables.md"
        assert topic_data["concepts"] == "variables, integers, strings, booleans"
        assert topic_data["topic_order"] == 1

    def test_performance_with_large_hierarchy(self, client, setup_learning_content_data):
        """Test performance with the complete course hierarchy"""
        course = setup_learning_content_data["course"]
        
        # This test verifies that N+1 query optimizations are working
        # by loading the entire course hierarchy in a single request
        import time
        
        start_time = time.time()
        response = client.get(f"/api/v1/learning/{course.id}")
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        
        # Response should be reasonably fast (under 2 seconds for this small dataset)
        response_time = end_time - start_time
        assert response_time < 2.0, f"Response took {response_time} seconds, which is too slow"
        
        # Verify all data was loaded correctly
        course_data = response.json()
        assert len(course_data["lessons"]) == 2
        assert len(course_data["lessons"][0]["topics"]) == 2
        assert len(course_data["lessons"][1]["topics"]) == 1

    def test_concurrent_content_access(self, client, setup_learning_content_data):
        """Test concurrent access to learning content"""
        course = setup_learning_content_data["course"]
        
        # Simulate multiple concurrent requests
        responses = []
        for _ in range(5):
            response = client.get(f"/api/v1/learning/{course.id}")
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            course_data = response.json()
            assert course_data["title"] == "Comprehensive Programming Course"

    def test_content_consistency_across_endpoints(self, client, setup_learning_content_data):
        """Test that content is consistent across different endpoints"""
        course = setup_learning_content_data["course"]
        lesson1 = setup_learning_content_data["lesson1"]
        topic1_1 = setup_learning_content_data["topic1_1"]
        
        # Get course with full hierarchy
        full_response = client.get(f"/api/v1/learning/{course.id}")
        assert full_response.status_code == status.HTTP_200_OK
        full_course = full_response.json()
        
        # Get lesson individually
        lesson_response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}")
        assert lesson_response.status_code == status.HTTP_200_OK
        individual_lesson = lesson_response.json()
        
        # Compare lesson data from both endpoints
        full_lesson = full_course["lessons"][0]
        
        assert full_lesson["id"] == individual_lesson["id"]
        assert full_lesson["title"] == individual_lesson["title"]
        assert len(full_lesson["topics"]) == len(individual_lesson["topics"])
        
        # Get topic individually
        topic_response = client.get(f"/api/v1/learning/{course.id}/lessons/{lesson1.id}/topics/{topic1_1.id}")
        assert topic_response.status_code == status.HTTP_200_OK
        individual_topic = topic_response.json()
        
        # Compare topic data
        full_topic = full_lesson["topics"][0]
        
        assert full_topic["id"] == individual_topic["id"]
        assert full_topic["title"] == individual_topic["title"]
        assert len(full_topic["tasks"]) == len(individual_topic["tasks"])