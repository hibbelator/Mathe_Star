from dataclasses import dataclass

import pytest

from math_game.app.session import RoundPhase, RoundSession
from math_game.core.contracts import AnswerStatus, ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import OperandRange
from math_game.core.task import ArithmeticTask


@dataclass
class SequenceGenerator:
    answers: list[int]

    def generate(self, definition: OperationDefinition) -> ArithmeticTask:
        expected_answer = self.answers.pop(0)
        return ArithmeticTask(
            operation=definition.operation,
            left_operand=expected_answer - 1,
            right_operand=1,
            expected_answer=expected_answer,
        )


def make_session(
    *,
    answers: list[int],
    task_count: int = 2,
    max_attempts_per_task: int = 1,
) -> RoundSession:
    return RoundSession(
        generator=SequenceGenerator(answers),
        definition=OperationDefinition(
            operation=ArithmeticOperation.ADDITION,
            left=OperandRange(1, 10),
            right=OperandRange(1, 10),
        ),
        task_count=task_count,
        max_attempts_per_task=max_attempts_per_task,
    )


def test_round_runs_from_start_through_feedback_to_finish() -> None:
    session = make_session(answers=[4, 7])

    session.start()
    assert session.phase is RoundPhase.TASK
    assert session.task_number == 1

    first_feedback = session.submit_answer(" 4 ")
    assert first_feedback.is_correct is True
    assert session.phase is RoundPhase.FEEDBACK
    assert session.correct_count == 1
    assert session.progress == 0.5

    session.advance_to_next_task()
    assert session.phase is RoundPhase.TASK
    assert session.task_number == 2

    second_feedback = session.submit_answer("5")
    assert second_feedback.is_correct is False
    assert second_feedback.expected_answer == 7
    assert session.results[-1].answer_status is AnswerStatus.INCORRECT

    session.advance_to_next_task()
    assert session.phase is RoundPhase.FINISHED
    assert session.current_task is None
    assert session.progress == 1.0


def test_second_chance_allows_retry_on_wrong_answer() -> None:
    session = make_session(answers=[10], task_count=1, max_attempts_per_task=2)
    session.start()

    fb1 = session.submit_answer("5")
    assert fb1.is_correct is False
    assert fb1.attempts_left == 1
    assert fb1.is_task_complete is False
    assert session.phase is RoundPhase.TASK
    assert len(session.results) == 0

    fb2 = session.submit_answer("10")
    assert fb2.is_correct is True
    assert fb2.attempts_left == 0
    assert fb2.is_task_complete is True
    assert session.phase is RoundPhase.FEEDBACK
    assert session.correct_count == 1


@pytest.mark.parametrize(
    ("raw_answer", "message"),
    [
        ("", "Bitte gib zuerst eine Antwort ein."),
        ("vier", "Die Antwort muss eine ganze Zahl sein."),
    ],
)
def test_invalid_answer_keeps_the_current_task(raw_answer: str, message: str) -> None:
    session = make_session(answers=[4])
    session.start()
    current_task = session.current_task

    with pytest.raises(ValueError, match=message):
        session.submit_answer(raw_answer)

    assert session.phase is RoundPhase.TASK
    assert session.current_task is current_task
    assert session.results == []


def test_round_rejects_double_submission_while_feedback_is_visible() -> None:
    session = make_session(answers=[4])
    session.start()
    session.submit_answer("4")

    with pytest.raises(RuntimeError, match="active task"):
        session.submit_answer("4")


def test_start_resets_a_completed_round() -> None:
    session = make_session(answers=[4, 6], task_count=1)
    session.start()
    session.submit_answer("4")
    session.advance_to_next_task()

    session.start()

    assert session.phase is RoundPhase.TASK
    assert session.results == []
    assert session.current_task is not None
    assert session.current_task.expected_answer == 6
