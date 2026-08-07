"""Endless plus/minus high-score mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EndlessPhase(StrEnum):
    READY = "ready"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass(slots=True)
class PluMiEndlessMode:
    """Continue without a task limit and stop immediately after three errors."""

    max_errors: int = 3
    phase: EndlessPhase = field(init=False, default=EndlessPhase.READY)
    score: int = field(init=False, default=0)
    errors: int = field(init=False, default=0)
    best_streak: int = field(init=False, default=0)
    current_streak: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if self.max_errors != 3:
            raise ValueError("PluMi Endless endet verbindlich nach genau drei Fehlern.")

    def start(self) -> None:
        self.score = self.errors = self.best_streak = self.current_streak = 0
        self.phase = EndlessPhase.PLAYING

    def submit(self, given_answer: int, expected_answer: int) -> bool:
        if self.phase is not EndlessPhase.PLAYING:
            raise RuntimeError("PluMi Endless läuft nicht.")
        correct = given_answer == expected_answer
        if correct:
            self.score += 1
            self.current_streak += 1
            self.best_streak = max(self.best_streak, self.current_streak)
        else:
            self.errors += 1
            self.current_streak = 0
            if self.errors == self.max_errors:
                self.phase = EndlessPhase.FINISHED
        return correct
