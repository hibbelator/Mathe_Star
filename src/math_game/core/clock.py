"""Clock contracts for deterministic core code and replaceable adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Protocol implemented by real and fake clocks."""

    def now(self) -> datetime:
        """Return the current timezone-aware timestamp."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class SystemClock:
    """Production clock adapter, isolated behind the Clock protocol."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)
