"""Small immutable value models and deterministic normalization helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import cast

from math_game.core.contracts import AnswerStatus


def normalize_for_hash(value: object) -> object:
    """Return a JSON-compatible canonical representation for hashing.

    Normalization is deliberately conservative: dictionaries are sorted by key,
    tuples become lists, enum values become their wire values and dataclasses are
    converted through their fields.  This keeps definition hashes stable across
    Python processes and independent from insertion order.
    """

    if is_dataclass(value) and not isinstance(value, type):
        field_values = {field.name: getattr(value, field.name) for field in fields(value)}
        return normalize_for_hash(field_values)
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

    task_id: str
    answer_status: AnswerStatus
    expected_answer: int | float | str
    given_answer: int | float | str | None
    elapsed_ms: int

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
