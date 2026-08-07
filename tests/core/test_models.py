import inspect
from dataclasses import MISSING, fields, is_dataclass

import pytest

from math_game.core import models
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


def test_core_models_dataclass_field_ordering() -> None:
    """Verify no required field follows a default field in any core model dataclass."""

    for name, cls in inspect.getmembers(models, inspect.isclass):
        if is_dataclass(cls) and cls.__module__ == models.__name__:
            seen_default = False
            for f in fields(cls):
                has_default = f.default is not MISSING or f.default_factory is not MISSING
                if has_default:
                    seen_default = True
                elif seen_default:
                    pytest.fail(
                        f"Dataclass {name} has non-default field '{f.name}' "
                        "following a field with a default"
                    )
