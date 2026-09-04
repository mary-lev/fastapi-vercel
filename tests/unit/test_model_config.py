"""
OpenAI model names come from config (FEEDBACK_MODEL / GENERATION_MODEL), and
the calls pass only parameters the gpt-5 family accepts.
"""

from types import SimpleNamespace

import pytest

from config import settings

pytestmark = pytest.mark.unit


class _ParseRecorder:
    """Stands in for client.beta.chat.completions / client.chat.completions."""

    def __init__(self, parsed=None, content="Meets requirements. Отлично."):
        self.calls = []
        self._parsed = parsed
        self._content = content

    def _reply(self):
        message = SimpleNamespace(parsed=self._parsed, content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self._reply()

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._reply()


def _client(recorder):
    completions = SimpleNamespace(completions=recorder)
    return SimpleNamespace(beta=SimpleNamespace(chat=completions), chat=completions)


def test_settings_expose_model_names():
    assert settings.FEEDBACK_MODEL
    assert settings.GENERATION_MODEL


def test_code_feedback_uses_configured_feedback_model(monkeypatch):
    import utils.evaluator as evaluator

    recorder = _ParseRecorder(parsed=SimpleNamespace(feedback="ok", is_solved=True))
    monkeypatch.setattr(evaluator, "client", _client(recorder))
    monkeypatch.setattr(settings, "FEEDBACK_MODEL", "test-feedback-model")

    task = SimpleNamespace(task_name="t", data={"text": "print hello"})
    result = evaluator.evaluate_code_submission({"code": "print('hello')"}, "hello\n", task, language="English")

    assert result.is_solved is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["model"] == "test-feedback-model"


def test_assignment_review_uses_feedback_model_and_supported_params(monkeypatch, tmp_path):
    import routes.assignments as assignments

    recorder = _ParseRecorder()
    monkeypatch.setattr(assignments, "openai_client", _client(recorder))
    monkeypatch.setattr(assignments, "OPENAI_ENABLED", True)
    monkeypatch.setattr(settings, "FEEDBACK_MODEL", "test-feedback-model")

    code_file = tmp_path / "solution.py"
    code_file.write_text("print('hi')\n", encoding="utf-8")
    task = SimpleNamespace(id=1, task_name="t", task_description="print hi", task_summary=None, data={"text": "print hi"})

    assignments.validate_python_code(task, str(code_file), language="English")

    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["model"] == "test-feedback-model"
    assert "temperature" not in call, "gpt-5 models reject non-default temperature"
    assert "max_tokens" not in call, "gpt-5 models need max_completion_tokens, not max_tokens"
    assert call.get("max_completion_tokens") == 1000
