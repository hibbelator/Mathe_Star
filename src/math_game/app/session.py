"""Small, explicit round orchestration for the playable UI slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from math_game.core.clock import Clock, SystemClock
from math_game.core.contracts import AnswerStatus, EndReason
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import TaskResult
from math_game.core.task import ArithmeticTask
from math_game.generators.contracts import TaskGenerator


class RoundPhase(StrEnum):
    """Visible phases required by the end-to-end round."""

    READY = "ready"
    TASK = "task"
    FEEDBACK = "feedback"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class RoundConfiguration:
    """Independent finish conditions for a round.

    More than one condition may be supplied; the first one observed wins.  A
    per-task deadline completes a task as incorrect, while ``total_duration``
    is the optional outer boundary that actually ends the round.
    """

    completed_task_target: int | None = None
    correct_answer_target: int | None = None
    total_duration: timedelta | None = None
    finish_on_first_incorrect: bool = False
    per_task_duration: timedelta | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("completed_task_target", self.completed_task_target),
            ("correct_answer_target", self.correct_answer_target),
        ):
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive when set")
        for name, value in (
            ("total_duration", self.total_duration),
            ("per_task_duration", self.per_task_duration),
        ):
            if value is not None and value <= timedelta(0):
                raise ValueError(f"{name} must be positive when set")
        if not any(
            (
                self.completed_task_target,
                self.correct_answer_target,
                self.total_duration,
                self.finish_on_first_incorrect,
            )
        ):
            raise ValueError("at least one round finish condition must be configured")


@dataclass(frozen=True, slots=True)
class AnswerFeedback:
    """Immediate feedback for the answer most recently submitted."""

    is_correct: bool
    given_answer: int
    expected_answer: int
    attempts_left: int = 0
    is_task_complete: bool = True


@dataclass(slots=True)
class RoundSession:
    """Coordinate a configured round independently from Flet widgets."""

    generator: TaskGenerator
    definition: OperationDefinition
    task_count: int = 5
    max_attempts_per_task: int = 1
    configuration: RoundConfiguration | None = None
    clock: Clock = field(default_factory=SystemClock)
    phase: RoundPhase = field(init=False, default=RoundPhase.READY)
    current_task: ArithmeticTask | None = field(init=False, default=None)
    feedback: AnswerFeedback | None = field(init=False, default=None)
    results: list[TaskResult] = field(init=False, default_factory=lambda: list[TaskResult]())
    attempts_on_current_task: int = field(init=False, default=0)
    end_reason: EndReason | None = field(init=False, default=None)
    started_at: datetime | None = field(init=False, default=None)
    task_started_at: datetime | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.task_count <= 0:
            raise ValueError("task_count must be positive")
        if self.max_attempts_per_task <= 0:
            raise ValueError("max_attempts_per_task must be positive")
        if self.configuration is None:
            self.configuration = RoundConfiguration(completed_task_target=self.task_count)

    @property
    def task_number(self) -> int:
        """Return the one-based number of the task currently visible."""

        return len(self.results) + (self.current_task is not None)

    @property
    def correct_count(self) -> int:
        """Return the number of correctly completed tasks in this round."""

        return sum(result.answer_status is AnswerStatus.CORRECT for result in self.results)

    @property
    def progress(self) -> float:
        """Return progress towards the configured primary target."""

        config = self._configuration
        if config.completed_task_target:
            return min(1.0, len(self.results) / config.completed_task_target)
        if config.correct_answer_target:
            return min(1.0, self.correct_count / config.correct_answer_target)
        if config.total_duration and self.started_at:
            return min(1.0, (self.clock.now() - self.started_at) / config.total_duration)
        return 0.0

    @property
    def _configuration(self) -> RoundConfiguration:
        assert self.configuration is not None
        return self.configuration

    def start(self) -> None:
        """Start a fresh round and generate its first task."""

        self.results.clear()
        self.feedback = None
        self.end_reason = None
        self.attempts_on_current_task = 0
        now = self.clock.now()
        self.started_at = now
        self.current_task = self.generator.generate(self.definition)
        self.task_started_at = now
        self.phase = RoundPhase.TASK
        self._evaluate_completion(now)

    def submit_answer(self, raw_answer: str) -> AnswerFeedback:
        """Validate and record one integer answer, then expose feedback."""

        now = self.clock.now()
        self._process_time(now)
        self._ensure_active_task()

        normalized_answer = raw_answer.strip()
        if not normalized_answer:
            raise ValueError("Bitte gib zuerst eine Antwort ein.")
        try:
            given_answer = int(normalized_answer)
        except ValueError as error:
            raise ValueError("Die Antwort muss eine ganze Zahl sein.") from error

        assert self.current_task is not None
        self.attempts_on_current_task += 1
        is_correct = given_answer == self.current_task.expected_answer
        attempts_left = max(0, self.max_attempts_per_task - self.attempts_on_current_task)
        is_task_complete = is_correct or attempts_left == 0
        if is_task_complete:
            self._record_result(is_correct, given_answer, now)

        self.feedback = AnswerFeedback(
            is_correct,
            given_answer,
            self.current_task.expected_answer,
            attempts_left,
            is_task_complete,
        )
        self.phase = RoundPhase.FEEDBACK if is_task_complete else RoundPhase.TASK
        self._evaluate_completion(now)
        return self.feedback

    def advance_to_next_task(self) -> None:
        """Advance to the next task unless a configured condition has ended the round."""

        now = self.clock.now()
        self._process_time(now)
        if self._evaluate_completion(now):
            return
        if self.phase is not RoundPhase.FEEDBACK:
            raise RuntimeError("the next task can only follow completed-task feedback")
        self.feedback = None
        self.attempts_on_current_task = 0
        self.current_task = self.generator.generate(self.definition)
        self.task_started_at = now
        self.phase = RoundPhase.TASK
        self._evaluate_completion(now)

    def on_timer_event(self) -> bool:
        """Process deterministic total/per-task timer expiry.

        Returns whether the round is finished.  A per-task timeout leaves
        feedback visible so the caller can advance in the normal way.
        """

        now = self.clock.now()
        self._process_time(now)
        return self._evaluate_completion(now)

    def continue_round(self) -> None:
        """Backwards compatibility helper for existing callers."""

        self.advance_to_next_task()

    def _ensure_active_task(self) -> None:
        if self.phase is not RoundPhase.TASK or self.current_task is None:
            raise RuntimeError("an answer can only be submitted for an active task")

    def _record_result(self, correct: bool, given_answer: int, now: datetime) -> None:
        assert self.current_task is not None
        elapsed = now - (self.task_started_at or now)
        self.results.append(
            TaskResult(
                task_id=f"task-{len(self.results) + 1}",
                answer_status=AnswerStatus.CORRECT if correct else AnswerStatus.INCORRECT,
                expected_answer=self.current_task.expected_answer,
                given_answer=given_answer,
                elapsed_ms=max(0, int(elapsed.total_seconds() * 1000)),
            )
        )

    def _process_time(self, now: datetime) -> None:
        if self.phase is RoundPhase.FINISHED:
            return
        if self._evaluate_completion(now):
            return
        config = self._configuration
        if (
            config.per_task_duration
            and self.phase is RoundPhase.TASK
            and self.current_task is not None
            and self.task_started_at is not None
            and now - self.task_started_at >= config.per_task_duration
        ):
            self._record_result(False, 0, now)
            self.feedback = AnswerFeedback(False, 0, self.current_task.expected_answer, 0, True)
            self.phase = RoundPhase.FEEDBACK
            self._evaluate_completion(now)

    def _evaluate_completion(self, now: datetime) -> bool:
        """Apply every end condition in one place and persist the first cause."""

        if self.phase is RoundPhase.FINISHED:
            return True
        config = self._configuration
        reason: EndReason | None = None
        if (
            self.started_at
            and config.total_duration
            and now - self.started_at >= config.total_duration
        ):
            reason = EndReason.TIME_LIMIT_REACHED
        elif config.completed_task_target and len(self.results) >= config.completed_task_target:
            reason = EndReason.TASK_TARGET_REACHED
        elif config.correct_answer_target and self.correct_count >= config.correct_answer_target:
            reason = EndReason.CORRECT_TARGET_REACHED
        elif (
            config.finish_on_first_incorrect
            and self.results
            and self.results[-1].answer_status is AnswerStatus.INCORRECT
        ):
            reason = EndReason.FIRST_ERROR
        if reason is not None:
            self.end_reason = reason
            self.current_task = None
            self.task_started_at = None
            self.phase = RoundPhase.FINISHED
            return True
        return False
