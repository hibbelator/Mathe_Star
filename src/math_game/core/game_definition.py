"""Comparable game definition contracts.

A game definition describes every fachlich relevant setting that makes two game
sessions comparable.  Presentation details live in ``GamePresentation`` and do
not participate in the stable definition hash.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import cast

from math_game.core.contracts import GameMode
from math_game.core.models import DefinitionHash, normalize_for_hash

_VALID_MISSING_POSITIONS: Final[set[int]] = {1, 2, 3}


@dataclass(frozen=True, slots=True)
class OperationWeights:
    """Integer operation weights used for weighted operation selection."""

    addition: int = 0
    subtraction: int = 0
    multiplication: int = 0
    division: int = 0

    def __post_init__(self) -> None:
        weights = (self.addition, self.subtraction, self.multiplication, self.division)
        if any(weight < 0 for weight in weights):
            raise ValueError("operation weights must not be negative")
        if sum(weights) <= 0:
            raise ValueError("at least one operation weight must be greater than zero")

    def uses_tables(self) -> bool:
        """Return whether multiplication or division can be selected."""

        return self.multiplication > 0 or self.division > 0


@dataclass(frozen=True, slots=True)
class ComboThreshold:
    """Combo multiplier starting at a minimum streak length."""

    streak_from: int
    multiplier: int

    def __post_init__(self) -> None:
        if self.streak_from <= 0:
            raise ValueError("streak_from must be positive")
        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")


@dataclass(frozen=True, slots=True)
class ComboRules:
    """Deterministic point rules for the combo mode."""

    base_points: int = 100
    thresholds: tuple[ComboThreshold, ...] = (
        ComboThreshold(1, 1),
        ComboThreshold(5, 2),
        ComboThreshold(10, 3),
        ComboThreshold(15, 4),
    )

    def __post_init__(self) -> None:
        if self.base_points <= 0:
            raise ValueError("base_points must be positive")
        if not self.thresholds:
            raise ValueError("at least one combo threshold is required")
        ordered = tuple(sorted(self.thresholds, key=lambda threshold: threshold.streak_from))
        if ordered != self.thresholds:
            raise ValueError("combo thresholds must be sorted by streak_from")
        if len({threshold.streak_from for threshold in self.thresholds}) != len(self.thresholds):
            raise ValueError("combo thresholds must not contain duplicate streak_from values")


@dataclass(frozen=True, slots=True)
class GamePresentation:
    """Mutable presentation metadata stored outside the definition hash."""

    display_name: str
    visual_theme: str
    is_visible: bool = True
    is_favorite: bool = False
    sort_order: int = 0

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ValueError("display_name must not be blank")
        if not self.visual_theme.strip():
            raise ValueError("visual_theme must not be blank")
        if self.sort_order < 0:
            raise ValueError("sort_order must not be negative")


@dataclass(frozen=True, slots=True)
class GameDefinition:
    """Stable domain contract with a deterministic definition hash."""

    identifier: str
    title: str
    operations: tuple[OperationDefinition, ...]
    mode: GameMode
    task_count: int | None = None
    duration_seconds: int | None = None
    metadata: Mapping[str, str] = field(default_factory=lambda: {})
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
        if self.schema_version <= 0:
            raise ValueError("schema_version must be positive")

        # ``frozen=True`` alone does not protect a mutable mapping supplied by
        # callers.  A defensive copy keeps a definition (and therefore its
        # hash) stable throughout its lifetime.
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def normalized_payload(self) -> dict[str, object]:
        """Return the normative payload that participates in the definition hash."""

        return cast(
            dict[str, object],
            normalize_for_hash(
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
            ),
        )

    def definition_hash(self) -> DefinitionHash:
        """Calculate the stable SHA-256 hash for this definition."""

        return DefinitionHash(algorithm="sha256", value=self.id)

    def _normalized_total_time_seconds(self) -> float | None:
        if self.mode_key in {GameMode.TIME_ATTACK, GameMode.PERFECT_RUN, GameMode.PER_TASK_TIMER}:
            return self.total_time_seconds
        return None

    def _normalized_per_task_time_seconds(self) -> float | None:
        if self.mode_key in {GameMode.TIME_ATTACK, GameMode.PER_TASK_TIMER}:
            return self.per_task_time_seconds
        return None

    def _normalized_task_count(self) -> int | None:
        if self.mode_key in {GameMode.TASK_SPRINT, GameMode.PER_TASK_TIMER, GameMode.COMBO}:
            return self.task_count
        return None

    def _normalized_correct_target(self) -> int | None:
        if self.mode_key is GameMode.TARGET_HUNT:
            return self.correct_target
        return None

    def _normalized_penalty_seconds(self) -> float:
        if self.mode_key in {GameMode.TASK_SPRINT, GameMode.TARGET_HUNT}:
            return self.penalty_seconds
        return 0.0

    def _normalized_combo_rules(self) -> ComboRules | None:
        if self.mode_key is GameMode.COMBO:
            return self.combo_rules
        return None
