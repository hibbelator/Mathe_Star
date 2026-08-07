"""Short, speed-focused round with a session-local leaderboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BlitzPhase(StrEnum):
    READY = "ready"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass(slots=True)
class BlitzMode:
    """Count correct answers until the strict 30–60 second deadline."""

    duration_seconds: int = 45
    phase: BlitzPhase = field(init=False, default=BlitzPhase.READY)
    started_at: float = field(init=False, default=0)
    correct_count: int = field(init=False, default=0)
    wrong_count: int = field(init=False, default=0)
    leaderboard: list[int] = field(init=False, default_factory=lambda: [])

    def __post_init__(self) -> None:
        if not 30 <= self.duration_seconds <= 60:
            raise ValueError("Eine Blitzrunde muss zwischen 30 und 60 Sekunden dauern.")

    def start(self, now: float) -> None:
        self.started_at, self.correct_count, self.wrong_count = now, 0, 0
        self.phase = BlitzPhase.PLAYING

    def submit(self, given_answer: int, expected_answer: int, now: float) -> bool:
        if self.tick(now):
            raise RuntimeError("Die Blitzrunde ist bereits beendet.")
        correct = given_answer == expected_answer
        if correct:
            self.correct_count += 1
        else:
            self.wrong_count += 1
        return correct

    def tick(self, now: float) -> bool:
        if self.phase is BlitzPhase.PLAYING and now - self.started_at >= self.duration_seconds:
            self.phase = BlitzPhase.FINISHED
            self.leaderboard.append(self.correct_count)
            self.leaderboard.sort(reverse=True)
        return self.phase is BlitzPhase.FINISHED

    def seconds_left(self, now: float) -> float:
        if self.phase is BlitzPhase.READY:
            return float(self.duration_seconds)
        return max(0.0, self.duration_seconds - (now - self.started_at))
