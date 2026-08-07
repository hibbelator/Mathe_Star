"""Durable round statistics, kept independent of the Flet user interface."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast


@dataclass(frozen=True, slots=True)
class RoundStatistic:
    game_id: str
    game_name: str
    correct: int
    total: int
    elapsed_seconds: float
    played_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if self.correct < 0 or self.total <= 0 or self.correct > self.total:
            raise ValueError("Ungültiges Rundenergebnis.")
        if self.elapsed_seconds < 0:
            raise ValueError("Die Spielzeit darf nicht negativ sein.")

    @property
    def accuracy(self) -> float:
        return self.correct / self.total


@dataclass(slots=True)
class StatisticsRepository:
    path: Path = field(default_factory=lambda: Path.home() / ".math_game" / "statistics.json")

    def load(self) -> list[RoundStatistic]:
        if not self.path.exists():
            return []
        raw: object = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Die Statistikdatei muss eine Liste enthalten.")
        items = cast(list[dict[str, object]], raw)
        return [
            RoundStatistic(
                game_id=str(item["game_id"]),
                game_name=str(item["game_name"]),
                correct=int(cast(int | str, item["correct"])),
                total=int(cast(int | str, item["total"])),
                elapsed_seconds=float(cast(float | int | str, item["elapsed_seconds"])),
                played_at=str(item["played_at"]),
            )
            for item in items
        ]

    def add(self, statistic: RoundStatistic) -> None:
        statistics = self.load()
        statistics.append(statistic)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([asdict(item) for item in statistics], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def best_by_game(self) -> dict[str, RoundStatistic]:
        best: dict[str, RoundStatistic] = {}
        for item in self.load():
            previous = best.get(item.game_id)
            score = (item.accuracy, item.correct, -item.elapsed_seconds)
            if previous is None or score > (
                previous.accuracy,
                previous.correct,
                -previous.elapsed_seconds,
            ):
                best[item.game_id] = item
        return best
