"""Small immutable value models and deterministic normalization helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping


def normalize_for_hash(value: Any) -> Any:
    """Return a JSON-compatible canonical representation for hashing.

    Normalization is deliberately conservative: dictionaries are sorted by key,
    tuples become lists, enum values become their wire values and dataclasses are
    converted through their fields.  This keeps definition hashes stable across
    Python processes and independent from insertion order.
    """

    if is_dataclass(value):
        return normalize_for_hash(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): normalize_for_hash(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, tuple):
        return [normalize_for_hash(item) for item in value]
    if isinstance(value, list):
        return [normalize_for_hash(item) for item in value]
    if isinstance(value, set | frozenset):
        return [normalize_for_hash(item) for item in sorted(value, key=repr)]
    return value


def canonical_json(value: Any) -> str:
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
    def from_payload(cls, payload: Any) -> "DefinitionHash":
        digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        return cls(algorithm="sha256", value=digest)

    def as_uri(self) -> str:
        """Return a compact namespaced representation for storage or logs."""

        return f"{self.algorithm}:{self.value}"


@dataclass(frozen=True, slots=True)
class OperandRange:
    """Inclusive integer range for operands in a task definition."""

    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if self.minimum > self.maximum:
            raise ValueError("minimum must be less than or equal to maximum")


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Result contract for one answered or unresolved task."""

    task_id: str
    answer_status: str
    expected_answer: int | float | str
    given_answer: int | float | str | None
    elapsed_ms: int

    def __post_init__(self) -> None:
        if self.elapsed_ms < 0:
            raise ValueError("elapsed_ms must not be negative")
