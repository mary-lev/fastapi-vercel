"""
Submitting a solution for the same task twice must not create two task_solutions rows.

Uses the app's own test engine (NODE_ENV=test -> SQLite, tables auto-created in db.py)
rather than the conftest fixtures, whose teardown relies on a removed SQLAlchemy API.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import app
from config import settings
from db import SessionLocal
from models import Course, Lesson, MultipleSelectQuiz, TaskSolution, Topic, User, UserStatus

pytestmark = pytest.mark.integration

AUTH = {"Authorization": f"Bearer {settings.BACKEND_API_KEY}"}


@pytest.fixture
def quiz_and_user():
    db = SessionLocal()
    tag = uuid.uuid4().hex[:8]
    user = User(internal_user_id=f"dedup-{tag}", username=f"dedup-{tag}", hashed_sub=f"h-{tag}", status=UserStatus.STUDENT)
    db.add(user)
    db.flush()
    course = Course(title=f"c-{tag}", description="", professor_id=user.id)
    db.add(course)
    db.flush()
    lesson = Lesson(title="l", description="", course_id=course.id, lesson_order=1)
    db.add(lesson)
    db.flush()
    topic = Topic(title="t", lesson_id=lesson.id, topic_order=1)
    db.add(topic)
    db.flush()
    quiz = MultipleSelectQuiz(
        task_name="q", task_link=f"{topic.id}-1", points=5, order=1, data={"question": "?", "options": []},
        topic_id=topic.id, attempt_strategy="unlimited",
    )
    db.add(quiz)
    db.commit()
    ids = {"user": user.internal_user_id, "user_id": user.id, "task_id": quiz.id}
    db.close()
    yield ids
    db = SessionLocal()
    db.query(TaskSolution).filter(TaskSolution.task_id == ids["task_id"]).delete()
    db.commit()
    db.close()


def _post(client, ids, is_correct):
    return client.post(
        f"/api/v1/students/{ids['user']}/solutions",
        json={"task_id": ids["task_id"], "solution_data": {"answer": [1]}, "is_correct": is_correct},
        headers=AUTH,
    )


def test_repeated_quiz_submission_keeps_one_solution_row(quiz_and_user):
    ids = quiz_and_user
    with TestClient(app) as client:
        first = _post(client, ids, True)
        second = _post(client, ids, True)
        third = _post(client, ids, False)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert third.status_code == 200, third.text

    db = SessionLocal()
    rows = db.query(TaskSolution).filter(TaskSolution.user_id == ids["user_id"], TaskSolution.task_id == ids["task_id"]).all()
    db.close()
    assert len(rows) == 1
    assert rows[0].is_correct is False  # latest submission wins
