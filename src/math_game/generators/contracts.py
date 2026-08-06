"""Narrow boundaries that make generators deterministic and testable."""

from __future__ import annotations

from typing import Protocol

from math_game.core.game_definition import OperationDefinition
from math_game.core.task import ArithmeticTask


class IntegerRandomSource(Protocol):
    """Source for uniformly selected integers from an inclusive interval."""

    def randint(self, minimum: int, maximum: int) -> int:
        """Return one integer with ``minimum <= value <= maximum``."""
        ...


class TaskGenerator(Protocol):
    """Generator boundary consumed by future session orchestration."""

    def generate(self, definition: OperationDefinition) -> ArithmeticTask:
        """Generate one task that satisfies the operation definition."""
        ...
