"""Stable domain contracts shared by generators, modes and adapters.

This module intentionally contains no generator, persistence or UI logic.  It
only defines vocabulary that must remain comparable across plugins and future
frontends.
"""

from __future__ import annotations

from enum import StrEnum


class ArithmeticOperation(StrEnum):
    """Supported arithmetic operation families for task definitions."""

    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"


class AnswerStatus(StrEnum):
    """Canonical answer status values used by all game modes."""

    UNANSWERED = "unanswered"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    WRONG_RESULT = "wrong_result"
    NO_INPUT = "no_input"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class GameMode(StrEnum):
    """Known game mode contract names, without implementing mode behavior."""

    PRACTICE = "practice"
    TIMED = "timed"
    FIXED_TASKS = "fixed_tasks"
    MISTAKE_REVIEW = "mistake_review"
    TIME_ATTACK = "time_attack"
    TASK_SPRINT = "task_sprint"
    PERFECT_RUN = "perfect_run"
    TARGET_HUNT = "target_hunt"
    PER_TASK_TIMER = "per_task_timer"
    COMBO = "combo"
    BLITZ = "blitz"
    ACCURACY = "accuracy"
    PLUMI_ENDLESS = "plumi_endless"
    WARM_UP = "warm_up"


class ComparisonScope(StrEnum):
    """Scope in which two runs may be compared."""

    SAME_DEFINITION = "same_definition"
    SAME_DEFINITION_AND_MODE = "same_definition_and_mode"


class EndReason(StrEnum):
    """Standard end reasons for a future GameSessionResult."""

    COMPLETED = "completed"
    TIME_LIMIT_REACHED = "time_limit_reached"
    FIRST_ERROR = "first_error"
    TARGET_REACHED = "target_reached"
    TASK_TARGET_REACHED = "task_target_reached"
    CORRECT_TARGET_REACHED = "correct_target_reached"
    COMBO_TARGET_REACHED = "combo_target_reached"
    ABORTED = "aborted"
