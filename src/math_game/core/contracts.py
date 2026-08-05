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
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class GameMode(StrEnum):
    """Known game mode contract names, without implementing mode behavior."""

    PRACTICE = "practice"
    TIMED = "timed"
    FIXED_TASKS = "fixed_tasks"
    MISTAKE_REVIEW = "mistake_review"


class ComparisonScope(StrEnum):
    """Scope in which two runs may be compared."""

    SAME_DEFINITION = "same_definition"
    SAME_DEFINITION_AND_MODE = "same_definition_and_mode"
