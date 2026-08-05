"""Stable domain vocabulary shared by generators, modes and adapters.

The contracts in this module intentionally contain no generator, persistence or
UI logic.  They are the common language used by the future app shell, headless
mode state machines and tests.
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
    """Canonical answer status values required by the masterplan."""

    CORRECT = "correct"
    WRONG_RESULT = "wrong_result"
    NO_INPUT = "no_input"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class GameMode(StrEnum):
    """Target game mode keys.

    These are identifiers only.  No mode state machine is implemented in
    Verification Gate 1A.
    """

    TIME_ATTACK = "time_attack"
    TASK_SPRINT = "task_sprint"
    PERFECT_RUN = "perfect_run"
    TARGET_HUNT = "target_hunt"
    PER_TASK_TIMER = "per_task_timer"
    COMBO = "combo"


class EndReason(StrEnum):
    """Standard end reasons for a future GameSessionResult."""

    COMPLETED = "completed"
    TIME_LIMIT_REACHED = "time_limit_reached"
    FIRST_ERROR = "first_error"
    TARGET_REACHED = "target_reached"
    ABORTED = "aborted"
