"""Durable round statistics, kept independent of the Flet user interface."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from math_game.app.database import AppDatabase
from math_game.core.race import RaceConfig, RaceEventKind, RaceKind
from math_game.core.race_simulation import simulate_race


@dataclass(frozen=True, slots=True)
class ScoreEvent:
    elapsed_seconds: float
    correct: bool
    points_after: int
    task_id: str | None = None
    task_number: int | None = None
    event_kind: str | None = None
    task_completed: bool | None = None
    correct_answers: int | None = None
    completed_tasks: int | None = None
    combo: int | None = None
    end_reason: str | None = None

    def __post_init__(self) -> None:
        if self.elapsed_seconds < 0:
            raise ValueError("Der Ereigniszeitpunkt darf nicht negativ sein.")
        if self.task_number is not None and self.task_number <= 0:
            raise ValueError("Die Aufgabennummer muss positiv sein.")
        for value in (self.correct_answers, self.completed_tasks, self.combo):
            if value is not None and value < 0:
                raise ValueError("Ereigniszähler dürfen nicht negativ sein.")

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ScoreEvent:
        """Read both the compact historical shape and the complete event shape."""

        return cls(**{name: data[name] for name in cls.__dataclass_fields__ if name in data})  # type: ignore[arg-type]

    def as_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


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
    event_schema_version: int = 2

    def __post_init__(self) -> None:
        if self.correct < 0 or self.total <= 0 or self.correct > self.total:
            raise ValueError("Ungültiges Rundenergebnis.")
        if self.elapsed_seconds < 0:
            raise ValueError("Die Spielzeit darf nicht negativ sein.")
        if self.event_schema_version <= 0:
            raise ValueError("Die Ereignis-Schemaversion muss positiv sein.")

    def events_support(self, race: RaceConfig) -> bool:
        """Whether the stored facts can replay the selected rule without guesses."""

        if not self.events:
            return False
        if self.event_schema_version >= 2:
            required = all(
                event.event_kind is not None
                and event.event_kind in RaceEventKind
                and event.task_completed is not None
                and event.correct_answers is not None
                and event.completed_tasks is not None
                and event.combo is not None
                for event in self.events
            )
            return required
        # Version 1 recorded only answer correctness, score and the actual event time.
        # That is sufficient for answer/perfect/combo races, but not for task races
        # (one task could have several attempts) or a time-limit finish event.
        return race.kind in {
            RaceKind.CORRECT_ANSWERS,
            RaceKind.PERFECT,
            RaceKind.COMBO,
        }

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
    player_icon: str = "🤖"


def computer_competitor(
    definition_hash: str,
    race: RaceConfig,
    *,
    level: int,
    baseline_points: float | None = None,
    seed: int = 0,
    variable: bool = True,
) -> RaceCompetitor:
    """Create a fallible computer run evaluated by the regular race engine.

    Levels are percentile-like strength labels. Level 10 is roughly the 90th
    percentile: difficult, but still a fallible and variably paced machine.
    """

    del baseline_points  # Kept as a source-selection compatibility hint for the UI.
    simulation = simulate_race(race, level=level, seed=seed, variable=variable)
    events = tuple(
        ScoreEvent(
            item.event.elapsed_seconds or 0.0,
            item.event.kind is RaceEventKind.CORRECT_ANSWER,
            item.racer.score,
            task_number=index,
            event_kind=item.event.kind.value,
            task_completed=item.event.kind is not RaceEventKind.TIME_ELAPSED,
            correct_answers=item.racer.correct_answers,
            completed_tasks=item.racer.completed_tasks,
            combo=item.racer.streak,
            end_reason=item.racer.end_reason.value if item.racer.end_reason else None,
        )
        for index, item in enumerate(simulation.events, 1)
    )
    racer = simulation.state.racers[0]
    answer_events = [
        event for event in events if event.event_kind != RaceEventKind.TIME_ELAPSED.value
    ]
    statistic = RoundStatistic(
        player_id=0,
        game_id="computer",
        game_name="Computergegner",
        definition_hash=definition_hash,
        correct=racer.correct_answers,
        total=max(1, len(answer_events)),
        elapsed_seconds=racer.elapsed_seconds,
        events=events,
        score_value=racer.score,
    )
    computer_icons = ("🤖", "👾", "🦾", "🧠", "⚙️")
    # A seed produces the same opponent on every replay, while different race
    # slots still feel like a small, varied field.  Keep these labels deliberately
    # short: technical descriptions such as percentile and level belong in the
    # setup dialog, not beside the moving racer on a phone-sized track.
    computer_names = (
        "Nova",
        "Keks",
        "Momo",
        "Blitz",
        "Pixel",
        "Zora",
        "Fips",
        "Loki",
        "Pico",
        "Trix",
        "Nino",
        "Flitz",
        "Juno",
        "Puck",
        "Roxy",
        "Mika",
        "Turbo",
    )
    computer_name = computer_names[(seed * 5 + level * 3) % len(computer_names)]
    return RaceCompetitor(
        computer_name,
        statistic,
        computer_icons[(level - 1) % len(computer_icons)],
    )


@dataclass(slots=True)
class StatisticsRepository:
    database: AppDatabase = field(default_factory=AppDatabase)

    def load(self, player_id: int | None = None) -> list[RoundStatistic]:
        query = """SELECT player_id, game_id, game_name, definition_hash, correct, total,
                   elapsed_seconds, played_at, events_json, score_value, event_schema_version
                   FROM round_statistics"""
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
                events=tuple(
                    ScoreEvent.from_dict(event) for event in json.loads(row["events_json"])
                ),
                score_value=None if row["score_value"] is None else int(row["score_value"]),
                event_schema_version=int(row["event_schema_version"]),
            )
            for row in rows
        ]

    def add(self, statistic: RoundStatistic) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO round_statistics(
                    player_id, game_id, game_name, definition_hash, correct, total,
                    elapsed_seconds, played_at, events_json, score_value, event_schema_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    statistic.player_id,
                    statistic.game_id,
                    statistic.game_name,
                    statistic.definition_hash,
                    statistic.correct,
                    statistic.total,
                    statistic.elapsed_seconds,
                    statistic.played_at,
                    json.dumps([event.as_dict() for event in statistic.events]),
                    statistic.score_value,
                    statistic.event_schema_version,
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

    def race_competitors(
        self,
        definition_hash: str,
        limit: int | RaceConfig = 3,
        race: RaceConfig | None = None,
    ) -> list[RaceCompetitor]:
        """Return exact-definition runs whose facts support the concrete race rule."""

        # Accept the concrete rule as the second positional argument as well as by
        # keyword, while retaining the original ``(hash, limit)`` public API.
        if isinstance(limit, RaceConfig):
            if race is not None:
                raise ValueError("Die Rennregel darf nur einmal angegeben werden.")
            race, limit = limit, 3
        if not 1 <= limit <= 8:
            raise ValueError("Ein Rennen braucht zwischen 1 und 8 Gegnern.")
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT s.player_id, p.name, p.icon, s.game_id, s.game_name, s.correct, s.total,
                          s.elapsed_seconds, s.played_at, s.events_json, s.score_value,
                          s.event_schema_version
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
                        ScoreEvent.from_dict(event) for event in json.loads(str(row["events_json"]))
                    ),
                    score_value=(None if row["score_value"] is None else int(row["score_value"])),
                    event_schema_version=int(row["event_schema_version"]),
                ),
                player_icon=str(row["icon"]),
            )
            for row in rows
        ]
        if race is not None:
            competitors = [item for item in competitors if item.statistic.events_support(race)]
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
