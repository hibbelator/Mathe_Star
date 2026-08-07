"""Untimed mode in which accuracy is the only score."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AccuracyPhase(StrEnum):
    READY = "ready"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass(slots=True)
class AccuracyMode:
    """Evaluate a fixed number of tasks without any clock or speed bonus."""

    task_count: int = 20
    phase: AccuracyPhase = field(init=False, default=AccuracyPhase.READY)
    correct_count: int = field(init=False, default=0)
    answered_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if self.task_count <= 0:
            raise ValueError("Die Aufgabenanzahl muss positiv sein.")

    def start(self) -> None:
        self.correct_count = self.answered_count = 0
        self.phase = AccuracyPhase.PLAYING

    def submit(self, given_answer: int, expected_answer: int) -> bool:
        if self.phase is not AccuracyPhase.PLAYING:
            raise RuntimeError("Der Genauigkeits-Modus läuft nicht.")
        correct = given_answer == expected_answer
        self.answered_count += 1
        self.correct_count += int(correct)
        if self.answered_count == self.task_count:
            self.phase = AccuracyPhase.FINISHED
        return correct

    @property
    def accuracy(self) -> float:
        return self.correct_count / self.answered_count if self.answered_count else 0.0
