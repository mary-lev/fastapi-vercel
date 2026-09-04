"""
Auth guards on professor/admin routes and student write endpoints.

Every endpoint listed here must reject requests that lack a valid
``Authorization: Bearer <BACKEND_API_KEY>`` header before any handler logic runs.
"""

import pytest
from fastapi.testclient import TestClient

from app import app
from config import settings

pytestmark = pytest.mark.security

# (method, path, json body) — bodies are minimal so a 422 can only come from the missing header
PROFESSOR_ROUTES = [
    ("GET", "/api/v1/professor/users", None),
    ("GET", "/api/v1/professor/analytics/students", None),
    ("GET", "/api/v1/professor/system/stats", None),
    ("GET", "/api/v1/professor/student-forms", None),
    ("POST", "/api/v1/professor/task-generator/generate", {"topic_id": 1, "task_type": "code"}),
]

ADMIN_WRITE_ROUTES = [
    ("PUT", "/api/v1/courses/1/lessons/1/topics/1/tasks/1", {"data": {}}),
    ("DELETE", "/api/v1/students/student-form/some-user", None),
    ("POST", "/api/v1/students/student-form/debug", {}),
]

STUDENT_WRITE_ROUTES = [
    ("POST", "/api/v1/students/some-user/submissions", {"task_id": 1, "submission_data": {}}),
    ("POST", "/api/v1/students/some-user/solutions", {"task_id": 1, "solution_content": "x"}),
    ("POST", "/api/v1/students/some-user/enroll?course_id=1", None),
    ("POST", "/api/v1/students/some-user/compile", {"code": "print(1)", "language": "python"}),
    ("POST", "/api/v1/students/some-user/submit-code", {"task_id": 1, "code": "print(1)", "language": "python"}),
    ("POST", "/api/v1/students/some-user/submit-text", {"task_id": 1, "user_answer": "x"}),
]

GUARDED_ROUTES = PROFESSOR_ROUTES + ADMIN_WRITE_ROUTES + STUDENT_WRITE_ROUTES


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _call(client, method, path, body, headers=None):
    return client.request(method, path, json=body, headers=headers or {})


@pytest.mark.parametrize("method,path,body", GUARDED_ROUTES)
def test_rejects_wrong_api_key(client, method, path, body):
    response = _call(client, method, path, body, {"Authorization": "Bearer definitely-wrong-key"})
    assert response.status_code == 401, response.text


@pytest.mark.parametrize("method,path,body", GUARDED_ROUTES)
def test_rejects_missing_authorization_header(client, method, path, body):
    response = _call(client, method, path, body)
    # 422 is the existing convention for a missing required header (see test_telegram_auth.py);
    # either way the request must not reach the handler.
    assert response.status_code in (401, 422), response.text
    assert "detail" in response.json()


def test_valid_api_key_passes_guard(client):
    response = client.get(
        "/api/v1/professor/system/stats", headers={"Authorization": f"Bearer {settings.BACKEND_API_KEY}"}
    )
    assert response.status_code not in (401, 422), response.text


def test_local_professor_tools_are_not_mounted(client):
    # /generation-materials exists only in routes/professor_local.py, which must stay local-only
    response = client.get("/api/v1/professor/generation-materials", headers={"Authorization": f"Bearer {settings.BACKEND_API_KEY}"})
    assert response.status_code == 404
