import pytest

from math_game.core.contracts import AnswerStatus
from math_game.core.models import TaskResult


def test_task_result_uses_the_canonical_answer_status() -> None:
    result = TaskResult(
        task_id="task-1",
        answer_status=AnswerStatus.CORRECT,
        expected_answer=4,
        given_answer=4,
        elapsed_ms=250,
    )

    assert result.answer_status is AnswerStatus.CORRECT


def test_task_result_rejects_negative_elapsed_time() -> None:
    with pytest.raises(ValueError, match="elapsed_ms must not be negative"):
        TaskResult(
            task_id="task-1",
            answer_status=AnswerStatus.UNANSWERED,
            expected_answer=4,
            given_answer=None,
            elapsed_ms=-1,
        )
