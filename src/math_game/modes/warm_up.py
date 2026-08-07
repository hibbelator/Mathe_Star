"""A gentle one-minute preparation round before the selected main game."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class WarmUpPhase(StrEnum):
    READY = "ready"
    PLAYING = "playing"
    MAIN_GAME_READY = "main_game_ready"


@dataclass(slots=True)
class WarmUpMode:
    """Run easy tasks for exactly 60 seconds, then hand over to the main game."""

    duration_seconds: int = 60
    phase: WarmUpPhase = field(init=False, default=WarmUpPhase.READY)
    started_at: float = field(init=False, default=0)
    correct_count: int = field(init=False, default=0)
    attempted_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if self.duration_seconds != 60:
            raise ValueError("Das Warm-up dauert verbindlich 60 Sekunden.")

    def start(self, now: float) -> None:
        self.started_at, self.correct_count, self.attempted_count = now, 0, 0
        self.phase = WarmUpPhase.PLAYING

    def submit(self, given_answer: int, expected_answer: int, now: float) -> bool:
        if self.tick(now):
            raise RuntimeError("Das Warm-up ist bereits abgeschlossen.")
        correct = given_answer == expected_answer
        self.attempted_count += 1
        self.correct_count += int(correct)
        return correct

    def tick(self, now: float) -> bool:
        if self.phase is WarmUpPhase.PLAYING and now - self.started_at >= self.duration_seconds:
            self.phase = WarmUpPhase.MAIN_GAME_READY
        return self.phase is WarmUpPhase.MAIN_GAME_READY
