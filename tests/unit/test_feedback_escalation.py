"""
Feedback escalation: Socratic questions for the first failures, direct help from the
second failure on the same task, a worked example from the fourth.
"""

from types import SimpleNamespace

import pytest

import utils.evaluator as evaluator

pytestmark = pytest.mark.unit


def _attempt(number, ok, code="x = 1", feedback="hint"):
    return SimpleNamespace(
        attempt_number=number, is_successful=ok, attempt_content=code,
        ai_feedback=[SimpleNamespace(feedback=feedback)],
    )


def test_first_failures_stay_socratic():
    text = evaluator.get_socratic_instructions(True, attempt_count=1, failed_count=1)
    assert "SOCRATIC" in text
    assert "NEVER provide working code" in text


def test_second_failure_switches_to_direct_help():
    text = evaluator.get_socratic_instructions(True, attempt_count=2, failed_count=2)
    assert "DIRECT HELP" in text
    assert "NEVER provide working code" not in text
    assert "name the exact" in text.lower()


def test_fourth_failure_gives_worked_example():
    text = evaluator.get_socratic_instructions(True, attempt_count=4, failed_count=4)
    assert "WORKED EXAMPLE" in text
    assert "NEVER provide working code" not in text


def test_system_prompt_for_direct_help_does_not_hide_solution():
    socratic = evaluator.build_system_prompt("lang", evaluator.get_socratic_instructions(True, 0, 0), True, help_mode="socratic")
    direct = evaluator.build_system_prompt("lang", evaluator.get_socratic_instructions(True, 2, 2), True, help_mode="direct")
    assert "discover solutions themselves" in socratic
    assert "Guides without revealing solution" not in direct
    assert "discover solutions themselves" not in direct


def test_prompt_sent_to_model_escalates_after_two_failures(monkeypatch):
    calls = []

    class _Completions:
        def parse(self, **kw):
            calls.append(kw)
            parsed = SimpleNamespace(feedback="ok", is_solved=False)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))])

    monkeypatch.setattr(evaluator, "client", SimpleNamespace(beta=SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))))
    task = SimpleNamespace(task_name="t", data={"text": "convert year_str"})

    evaluator.provide_code_feedback("print(1917 + 1)", "1918\n", task, "Russian", previous_attempts=[_attempt(1, False)])
    evaluator.provide_code_feedback("print(1917 + 1)", "1918\n", task, "Russian", previous_attempts=[_attempt(1, False), _attempt(2, False)])

    first_system = calls[0]["messages"][0]["content"]
    second_system = calls[1]["messages"][0]["content"]
    assert "SOCRATIC" in first_system and "DIRECT HELP" not in first_system
    assert "DIRECT HELP" in second_system
    # the user message must not ask for Socratic questioning once we are in direct-help mode
    assert "Socratic" not in calls[1]["messages"][1]["content"]
