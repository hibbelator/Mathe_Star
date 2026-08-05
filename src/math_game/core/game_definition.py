"""Comparable game definition contracts.

A game definition describes every fachlich relevant setting that makes two game
sessions comparable.  Presentation details live in ``GamePresentation`` and do
not participate in the stable definition hash.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, cast

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
    """Immutable, comparable game definition from the masterplan."""

    id: str
    mode_key: GameMode
    rules_version: int
    generator_version: int
    operation_weights: OperationWeights
    allowed_tables: tuple[int, ...]
    factor_min: int
    factor_max: int
    add_sub_max_result: int
    missing_positions: tuple[int, ...]
    total_time_seconds: float | None
    per_task_time_seconds: float | None
    task_count: int | None
    correct_target: int | None
    penalty_seconds: float
    combo_rules: ComboRules | None = None

    def __post_init__(self) -> None:
        if self.rules_version <= 0:
            raise ValueError("rules_version must be positive")
        if self.generator_version <= 0:
            raise ValueError("generator_version must be positive")
        if self.factor_min <= 0:
            raise ValueError("factor_min must be positive")
        if self.factor_max < self.factor_min:
            raise ValueError("factor_max must be greater than or equal to factor_min")
        if self.add_sub_max_result < 0:
            raise ValueError("add_sub_max_result must not be negative")
        if self.penalty_seconds < 0:
            raise ValueError("penalty_seconds must not be negative")
        self._validate_optional_positive("total_time_seconds", self.total_time_seconds)
        self._validate_optional_positive("per_task_time_seconds", self.per_task_time_seconds)
        self._validate_optional_positive_int("task_count", self.task_count)
        self._validate_optional_positive_int("correct_target", self.correct_target)
        if not self.missing_positions:
            raise ValueError("missing_positions must not be empty")
        if any(position not in _VALID_MISSING_POSITIONS for position in self.missing_positions):
            raise ValueError("missing_positions may only contain 1, 2 or 3")
        if len(set(self.missing_positions)) != len(self.missing_positions):
            raise ValueError("missing_positions must not contain duplicates")
        if any(table <= 0 for table in self.allowed_tables):
            raise ValueError("allowed_tables may only contain positive integers")
        if len(set(self.allowed_tables)) != len(self.allowed_tables):
            raise ValueError("allowed_tables must not contain duplicates")
        if tuple(sorted(self.allowed_tables)) != self.allowed_tables:
            raise ValueError("allowed_tables must be sorted for canonical comparison")
        if self.operation_weights.uses_tables() and not self.allowed_tables:
            raise ValueError("allowed_tables must not be empty for multiplication or division")
        if self.mode_key is GameMode.PER_TASK_TIMER and self.per_task_time_seconds is None:
            raise ValueError("per_task_timer requires per_task_time_seconds")
        if self.mode_key is GameMode.PER_TASK_TIMER and (
            self.task_count is None and self.total_time_seconds is None
        ):
            raise ValueError("per_task_timer requires task_count or total_time_seconds")
        if self.mode_key is GameMode.TIME_ATTACK and self.total_time_seconds is None:
            raise ValueError("time_attack requires total_time_seconds")
        if self.mode_key is GameMode.TASK_SPRINT and self.task_count is None:
            raise ValueError("task_sprint requires task_count")
        if self.mode_key is GameMode.TARGET_HUNT and self.correct_target is None:
            raise ValueError("target_hunt requires correct_target")
        if self.mode_key is GameMode.COMBO and (
            self.task_count is None or self.combo_rules is None
        ):
            raise ValueError("combo requires task_count and combo_rules")
        expected_id = self.compute_id()
        if not self.id:
            object.__setattr__(self, "id", expected_id)
        elif self.id != expected_id:
            raise ValueError("id must match the normalized definition hash")

    @staticmethod
    def _validate_optional_positive(name: str, value: float | None) -> None:
        if value is not None and value <= 0:
            raise ValueError(f"{name} must be positive when set")

    @staticmethod
    def _validate_optional_positive_int(name: str, value: int | None) -> None:
        if value is not None and value <= 0:
            raise ValueError(f"{name} must be positive when set")

    def normalized_payload(self) -> dict[str, object]:
        """Return the normative payload that participates in the definition hash."""

        payload = {
            "mode_key": self.mode_key,
            "rules_version": self.rules_version,
            "generator_version": self.generator_version,
            "operation_weights": self.operation_weights,
            "allowed_tables": self.allowed_tables,
            "factor_min": self.factor_min,
            "factor_max": self.factor_max,
            "add_sub_max_result": self.add_sub_max_result,
            "missing_positions": self.missing_positions,
            "total_time_seconds": self._normalized_total_time_seconds(),
            "per_task_time_seconds": self._normalized_per_task_time_seconds(),
            "task_count": self._normalized_task_count(),
            "correct_target": self._normalized_correct_target(),
            "penalty_seconds": self._normalized_penalty_seconds(),
            "combo_rules": self._normalized_combo_rules(),
        }
        return cast(dict[str, object], normalize_for_hash(payload))

    def compute_id(self) -> str:
        """Compute the SHA-256 definition id from the normalized payload."""

        return DefinitionHash.from_payload(self.normalized_payload()).value

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
