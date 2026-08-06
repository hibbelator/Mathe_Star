"""Small, explicit round orchestration for the first playable UI slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from math_game.core.contracts import AnswerStatus
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import TaskResult
from math_game.core.task import ArithmeticTask
from math_game.generators.contracts import TaskGenerator


class RoundPhase(StrEnum):
    """Visible phases required by the first end-to-end round."""

    READY = "ready"
    TASK = "task"
    FEEDBACK = "feedback"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class AnswerFeedback:
    """Immediate feedback for the answer most recently submitted."""

    is_correct: bool
    given_answer: int
    expected_answer: int


@dataclass(slots=True)
class RoundSession:
    """Coordinate one fixed-length round independently from Flet widgets."""

    generator: TaskGenerator
    definition: OperationDefinition
    task_count: int = 5
    phase: RoundPhase = field(init=False, default=RoundPhase.READY)
    current_task: ArithmeticTask | None = field(init=False, default=None)
    feedback: AnswerFeedback | None = field(init=False, default=None)
    results: list[TaskResult] = field(init=False, default_factory=lambda: [])

    def __post_init__(self) -> None:
        if self.task_count <= 0:
            raise ValueError("task_count must be positive")

    @property
    def task_number(self) -> int:
        """Return the one-based number of the task currently visible."""

        return min(len(self.results) + 1, self.task_count)

    @property
    def correct_count(self) -> int:
        """Return the number of correct answers in this round."""

        return sum(result.answer_status is AnswerStatus.CORRECT for result in self.results)

    @property
    def progress(self) -> float:
        """Return completed progress as a value between zero and one."""

        return len(self.results) / self.task_count

    def start(self) -> None:
        """Start a fresh round and generate its first task."""

        self.results.clear()
        self.feedback = None
        self.current_task = self.generator.generate(self.definition)
        self.phase = RoundPhase.TASK

    def submit_answer(self, raw_answer: str) -> AnswerFeedback:
        """Validate and record one integer answer, then expose feedback."""

        if self.phase is not RoundPhase.TASK or self.current_task is None:
            raise RuntimeError("an answer can only be submitted for an active task")

        normalized_answer = raw_answer.strip()
        if not normalized_answer:
            raise ValueError("Bitte gib zuerst eine Antwort ein.")
        try:
            given_answer = int(normalized_answer)
        except ValueError as error:
            raise ValueError("Die Antwort muss eine ganze Zahl sein.") from error

        is_correct = given_answer == self.current_task.expected_answer
        self.results.append(
            TaskResult(
                task_id=f"task-{len(self.results) + 1}",
                answer_status=AnswerStatus.CORRECT if is_correct else AnswerStatus.INCORRECT,
                expected_answer=self.current_task.expected_answer,
                given_answer=given_answer,
                elapsed_ms=0,
            )
        )
        self.feedback = AnswerFeedback(
            is_correct=is_correct,
            given_answer=given_answer,
            expected_answer=self.current_task.expected_answer,
        )
        self.phase = RoundPhase.FEEDBACK
        return self.feedback

    def continue_round(self) -> None:
        """Advance after feedback or finish when all tasks are answered."""

        if self.phase is not RoundPhase.FEEDBACK:
            raise RuntimeError("the round can only continue after feedback")

        self.feedback = None
        if len(self.results) >= self.task_count:
            self.current_task = None
            self.phase = RoundPhase.FINISHED
            return

        self.current_task = self.generator.generate(self.definition)
        self.phase = RoundPhase.TASK
