"""Durable round statistics, kept independent of the Flet user interface."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from math_game.app.database import AppDatabase


@dataclass(frozen=True, slots=True)
class ScoreEvent:
    elapsed_seconds: float
    correct: bool
    points_after: int

    def __post_init__(self) -> None:
        if self.elapsed_seconds < 0:
            raise ValueError("Der Ereigniszeitpunkt darf nicht negativ sein.")


@dataclass(frozen=True, slots=True)
class RoundStatistic:
    player_id: int
    game_id: str
    game_name: str
    definition_hash: str
    correct: int
    total: int
    elapsed_seconds: float
    played_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    events: tuple[ScoreEvent, ...] = ()
    score_value: int | None = None

    def __post_init__(self) -> None:
        if self.correct < 0 or self.total <= 0 or self.correct > self.total:
            raise ValueError("Ungültiges Rundenergebnis.")
        if self.elapsed_seconds < 0:
            raise ValueError("Die Spielzeit darf nicht negativ sein.")

    @property
    def accuracy(self) -> float:
        return self.correct / self.total

    @property
    def score(self) -> int:
        """Return a child-friendly score comparable within one game definition."""

        if self.score_value is not None:
            return self.score_value
        accuracy_points = round(self.accuracy * 1000)
        task_points = self.correct * 25
        time_penalty = min(round(self.elapsed_seconds), accuracy_points + task_points)
        return max(0, accuracy_points + task_points - time_penalty)


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    """Aggregated values for one player and one exact game definition."""

    rounds: tuple[RoundStatistic, ...]
    average_accuracy: float
    best_accuracy: float
    average_seconds: float
    best_score: int
    accuracy_trend: float


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    rank: int
    player_name: str
    score: int
    accuracy: float
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class RaceCompetitor:
    """One recorded run selected as a live race opponent."""

    player_name: str
    statistic: RoundStatistic


@dataclass(slots=True)
class StatisticsRepository:
    database: AppDatabase = field(default_factory=AppDatabase)

    def load(self, player_id: int | None = None) -> list[RoundStatistic]:
        query = """SELECT player_id, game_id, game_name, definition_hash, correct, total,
                   elapsed_seconds, played_at, events_json, score_value FROM round_statistics"""
        parameters: tuple[object, ...] = ()
        if player_id is not None:
            query += " WHERE player_id = ?"
            parameters = (player_id,)
        query += " ORDER BY played_at DESC, id DESC"
        with self.database.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            RoundStatistic(
                player_id=int(row["player_id"]),
                game_id=str(row["game_id"]),
                game_name=str(row["game_name"]),
                definition_hash=str(row["definition_hash"]),
                correct=int(row["correct"]),
                total=int(row["total"]),
                elapsed_seconds=float(row["elapsed_seconds"]),
                played_at=str(row["played_at"]),
                events=tuple(ScoreEvent(**event) for event in json.loads(row["events_json"])),
                score_value=None if row["score_value"] is None else int(row["score_value"]),
            )
            for row in rows
        ]

    def add(self, statistic: RoundStatistic) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO round_statistics(
                    player_id, game_id, game_name, definition_hash, correct, total,
                    elapsed_seconds, played_at, events_json, score_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    statistic.player_id,
                    statistic.game_id,
                    statistic.game_name,
                    statistic.definition_hash,
                    statistic.correct,
                    statistic.total,
                    statistic.elapsed_seconds,
                    statistic.played_at,
                    json.dumps(
                        [
                            {
                                "elapsed_seconds": event.elapsed_seconds,
                                "correct": event.correct,
                                "points_after": event.points_after,
                            }
                            for event in statistic.events
                        ]
                    ),
                    statistic.score_value,
                ),
            )

    def best_by_game(self, player_id: int | None = None) -> dict[str, RoundStatistic]:
        best: dict[str, RoundStatistic] = {}
        for item in self.load(player_id):
            previous = best.get(item.definition_hash)
            score = (item.accuracy, item.correct, -item.elapsed_seconds)
            if previous is None or score > (
                previous.accuracy,
                previous.correct,
                -previous.elapsed_seconds,
            ):
                best[item.definition_hash] = item
        return best

    def best_round(self, player_id: int, definition_hash: str) -> RoundStatistic | None:
        rounds = [item for item in self.load(player_id) if item.definition_hash == definition_hash]
        return max(
            rounds,
            key=lambda item: (item.score, item.accuracy, -item.elapsed_seconds),
            default=None,
        )

    def race_competitors(self, definition_hash: str, limit: int = 3) -> list[RaceCompetitor]:
        """Return the strongest recorded event-based runs for an exact game."""

        if not 1 <= limit <= 8:
            raise ValueError("Ein Rennen braucht zwischen 1 und 8 Gegnern.")
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT s.player_id, p.name, s.game_id, s.game_name, s.correct, s.total,
                          s.elapsed_seconds, s.played_at, s.events_json, s.score_value
                   FROM round_statistics AS s
                   JOIN players AS p ON p.id = s.player_id
                   WHERE s.definition_hash = ? AND s.events_json != '[]'""",
                (definition_hash,),
            ).fetchall()
        competitors = [
            RaceCompetitor(
                player_name=str(row["name"]),
                statistic=RoundStatistic(
                    player_id=int(row["player_id"]),
                    game_id=str(row["game_id"]),
                    game_name=str(row["game_name"]),
                    definition_hash=definition_hash,
                    correct=int(row["correct"]),
                    total=int(row["total"]),
                    elapsed_seconds=float(row["elapsed_seconds"]),
                    played_at=str(row["played_at"]),
                    events=tuple(
                        ScoreEvent(**event) for event in json.loads(str(row["events_json"]))
                    ),
                    score_value=(None if row["score_value"] is None else int(row["score_value"])),
                ),
            )
            for row in rows
        ]
        competitors.sort(
            key=lambda item: (
                -item.statistic.score,
                -item.statistic.accuracy,
                item.statistic.elapsed_seconds,
            )
        )
        return competitors[:limit]

    def summary(self, player_id: int, definition_hash: str) -> PerformanceSummary | None:
        rounds = tuple(
            item for item in self.load(player_id) if item.definition_hash == definition_hash
        )
        if not rounds:
            return None
        average_accuracy = sum(item.accuracy for item in rounds) / len(rounds)
        average_seconds = sum(item.elapsed_seconds for item in rounds) / len(rounds)
        chronological = tuple(reversed(rounds))
        trend = chronological[-1].accuracy - chronological[0].accuracy
        return PerformanceSummary(
            rounds=rounds,
            average_accuracy=average_accuracy,
            best_accuracy=max(item.accuracy for item in rounds),
            average_seconds=average_seconds,
            best_score=max(item.score for item in rounds),
            accuracy_trend=trend,
        )

    def leaderboard(self, definition_hash: str, limit: int = 5) -> list[LeaderboardEntry]:
        """Return each player's best round, restricted to one exact game definition."""

        if limit <= 0:
            raise ValueError("Das Bestenlisten-Limit muss positiv sein.")
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT s.player_id, p.name, s.correct, s.total, s.elapsed_seconds,
                          s.score_value
                   FROM round_statistics AS s
                   JOIN players AS p ON p.id = s.player_id
                   WHERE s.definition_hash = ?""",
                (definition_hash,),
            ).fetchall()
        best_by_player: dict[int, tuple[str, int, float, float]] = {}
        for row in rows:
            statistic = RoundStatistic(
                player_id=int(row["player_id"]),
                game_id="leaderboard",
                game_name="Bestenliste",
                definition_hash=definition_hash,
                correct=int(row["correct"]),
                total=int(row["total"]),
                elapsed_seconds=float(row["elapsed_seconds"]),
                score_value=None if row["score_value"] is None else int(row["score_value"]),
            )
            candidate = (
                str(row["name"]),
                statistic.score,
                statistic.accuracy,
                statistic.elapsed_seconds,
            )
            previous = best_by_player.get(statistic.player_id)
            if previous is None or (candidate[1], candidate[2], -candidate[3]) > (
                previous[1],
                previous[2],
                -previous[3],
            ):
                best_by_player[statistic.player_id] = candidate
        ordered = sorted(best_by_player.values(), key=lambda item: (-item[1], -item[2], item[3]))
        return [
            LeaderboardEntry(rank, name, score, accuracy, elapsed)
            for rank, (name, score, accuracy, elapsed) in enumerate(ordered[:limit], start=1)
        ]
