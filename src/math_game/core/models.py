"""Small immutable value models and deterministic normalization helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from enum import Enum
from typing import cast

from math_game.core.contracts import AnswerStatus, ArithmeticOperation, EndReason


def normalize_for_hash(value: object) -> object:
    """Return a JSON-compatible canonical representation for hashing.

    Normalization is deliberately conservative: dictionaries are sorted by key,
    tuples become lists, enum values become their wire values and dataclasses are
    converted through their fields.  This keeps definition hashes stable across
    Python processes and independent from insertion order.
    """

    if is_dataclass(value) and not isinstance(value, type):
        return normalize_for_hash(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {
            str(key): normalize_for_hash(mapping[key])
            for key in sorted(mapping, key=lambda item: str(item))
        }
    if isinstance(value, tuple):
        tuple_value = cast(tuple[object, ...], value)
        return [normalize_for_hash(item) for item in tuple_value]
    if isinstance(value, list):
        list_value = cast(list[object], value)
        return [normalize_for_hash(item) for item in list_value]
    if isinstance(value, set | frozenset):
        set_value = cast(set[object] | frozenset[object], value)
        return [normalize_for_hash(item) for item in sorted(set_value, key=repr)]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def canonical_json(value: object) -> str:
    """Serialize a value to the canonical JSON form used for hashes."""

    return json.dumps(
        normalize_for_hash(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclass(frozen=True, slots=True)
class DefinitionHash:
    """SHA-256 hash over a normalized game definition payload."""

    algorithm: str
    value: str

    @classmethod
    def from_payload(cls, payload: object) -> DefinitionHash:
        digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        return cls(algorithm="sha256", value=digest)

    def as_uri(self) -> str:
        """Return a compact namespaced representation for storage or logs."""

        return f"{self.algorithm}:{self.value}"


@dataclass(frozen=True, slots=True)
class MathTask:
    """Serializable arithmetic task contract produced by a future generator."""

    task_id: str
    sequence_number: int
    operation: ArithmeticOperation
    operand_left: int
    operand_right: int
    result: int
    missing_position: int
    displayed_task: str
    expected_answer: int

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be blank")
        if self.sequence_number <= 0:
            raise ValueError("sequence_number must be positive")
        if self.missing_position not in {1, 2, 3}:
            raise ValueError("missing_position must be 1, 2 or 3")


@dataclass(frozen=True, slots=True)
class TaskAttempt:
    """Result of exactly one evaluated task attempt."""

    task: MathTask
    entered_answer: int | None
    status: AnswerStatus
    response_time_seconds: float
    event_time_monotonic: float
    streak_before: int = 0
    streak_after: int = 0
    multiplier: int = 1
    points: int = 0

    def __post_init__(self) -> None:
        if self.response_time_seconds < 0:
            raise ValueError("response_time_seconds must not be negative")
        if self.event_time_monotonic < 0:
            raise ValueError("event_time_monotonic must not be negative")
        if self.streak_before < 0 or self.streak_after < 0:
            raise ValueError("streak values must not be negative")
        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")
        if self.points < 0:
            raise ValueError("points must not be negative")


@dataclass(frozen=True, slots=True)
class ResultSummary:
    """Common summary fields stored for a finished game session."""

    attempt_count: int
    correct_count: int
    wrong_count: int
    no_input_count: int
    timeout_count: int
    elapsed_seconds: float
    penalty_seconds: float
    effective_seconds: float
    score: int = 0
    longest_streak: int = 0
    highest_combo: int = 0

    def __post_init__(self) -> None:
        if self.attempt_count != (
            self.correct_count + self.wrong_count + self.no_input_count + self.timeout_count
        ):
            raise ValueError("attempt_count must equal the sum of evaluated answer statuses")
        for name, value in {
            "attempt_count": self.attempt_count,
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "no_input_count": self.no_input_count,
            "timeout_count": self.timeout_count,
            "score": self.score,
            "longest_streak": self.longest_streak,
            "highest_combo": self.highest_combo,
        }.items():
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        for name, value in {
            "elapsed_seconds": self.elapsed_seconds,
            "penalty_seconds": self.penalty_seconds,
            "effective_seconds": self.effective_seconds,
        }.items():
            if value < 0:
                raise ValueError(f"{name} must not be negative")


@dataclass(frozen=True, slots=True)
class GameSessionResult:
    """Standardized result envelope returned once by a future mode plugin."""

    session_id: str
    game_definition_id: str
    mode_key: str
    started_at_utc: datetime
    finished_at_utc: datetime
    end_reason: EndReason
    summary: ResultSummary
    attempts: tuple[TaskAttempt, ...]
    random_seed: int
    result_schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("session_id must not be blank")
        if not self.game_definition_id.strip():
            raise ValueError("game_definition_id must not be blank")
        if not self.mode_key.strip():
            raise ValueError("mode_key must not be blank")
        if self.finished_at_utc < self.started_at_utc:
            raise ValueError("finished_at_utc must not be before started_at_utc")
        if self.result_schema_version <= 0:
            raise ValueError("result_schema_version must be positive")
