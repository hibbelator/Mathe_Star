"""Comparable game definition contracts.

A game definition describes *what* may be generated, not *how* tasks are
produced.  The definition hash is the stable identity used to compare sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from math_game.core.contracts import ArithmeticOperation, GameMode
from math_game.core.models import DefinitionHash, OperandRange, normalize_for_hash


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    """Allowed operand range for a single arithmetic operation."""

    operation: ArithmeticOperation
    left: OperandRange
    right: OperandRange
    allow_negative_results: bool = False
    allow_remainders: bool = False


@dataclass(frozen=True, slots=True)
class GameDefinition:
    """Stable, hashable domain contract for comparable math game sessions."""

    identifier: str
    title: str
    operations: tuple[OperationDefinition, ...]
    mode: GameMode
    task_count: int | None = None
    duration_seconds: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("identifier must not be blank")
        if not self.title.strip():
            raise ValueError("title must not be blank")
        if not self.operations:
            raise ValueError("at least one operation is required")
        if self.task_count is not None and self.task_count <= 0:
            raise ValueError("task_count must be positive when set")
        if self.duration_seconds is not None and self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive when set")

    def normalized_payload(self) -> dict[str, object]:
        """Return the normative payload that participates in the definition hash."""

        return normalize_for_hash(
            {
                "schema_version": self.schema_version,
                "identifier": self.identifier,
                "title": self.title,
                "operations": self.operations,
                "mode": self.mode,
                "task_count": self.task_count,
                "duration_seconds": self.duration_seconds,
                "metadata": self.metadata,
            }
        )

    def definition_hash(self) -> DefinitionHash:
        """Calculate the stable SHA-256 hash for this definition."""

        return DefinitionHash.from_payload(self.normalized_payload())
