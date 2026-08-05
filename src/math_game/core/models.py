"""Small immutable value models and deterministic normalization helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import cast


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
