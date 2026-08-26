from pathlib import Path

from math_game.app.database import AppDatabase
from math_game.app.players import PlayerRepository
from math_game.app.stats import (
    RoundStatistic,
    ScoreEvent,
    StatisticsRepository,
    computer_competitor,
)
from math_game.core.race import RaceConfig, RaceKind


def test_statistics_persist_and_choose_best_round(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    player = PlayerRepository(database).add("Mia")
    repository = StatisticsRepository(database)
    repository.add(RoundStatistic(player.id, "game", "Spiel", "sha256:same", 7, 10, 20.0))
    repository.add(RoundStatistic(player.id, "renamed", "Neu", "sha256:same", 9, 10, 30.0))

    loaded = repository.load()
    assert len(loaded) == 2
    assert loaded[0].accuracy == 0.9
    assert repository.best_by_game()["sha256:same"] == loaded[0]


def test_statistics_never_compare_different_definitions_or_players(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    players = PlayerRepository(database)
    mia, ben = players.add("Mia"), players.add("Ben")
    repository = StatisticsRepository(database)
    repository.add(RoundStatistic(mia.id, "game", "Spiel", "sha256:a", 5, 10, 10.0))
    repository.add(RoundStatistic(mia.id, "game", "Spiel", "sha256:b", 9, 10, 10.0))
    repository.add(RoundStatistic(ben.id, "game", "Spiel", "sha256:a", 10, 10, 10.0))

    best = repository.best_by_game(mia.id)

    assert set(best) == {"sha256:a", "sha256:b"}
    assert best["sha256:a"].correct == 5


def test_dashboard_summary_calculates_score_history_and_trend(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    player = PlayerRepository(database).add("Mia")
    repository = StatisticsRepository(database)
    repository.add(
        RoundStatistic(player.id, "game", "Spiel", "sha256:a", 5, 10, 40.0, "2026-01-01")
    )
    repository.add(
        RoundStatistic(player.id, "game", "Spiel", "sha256:a", 9, 10, 30.0, "2026-01-02")
    )
    repository.add(
        RoundStatistic(player.id, "game", "Spiel", "sha256:other", 10, 10, 1.0, "2026-01-03")
    )

    summary = repository.summary(player.id, "sha256:a")

    assert summary is not None
    assert len(summary.rounds) == 2
    assert summary.average_accuracy == 0.7
    assert summary.best_accuracy == 0.9
    assert summary.average_seconds == 35.0
    assert summary.accuracy_trend == 0.4
    assert summary.best_score == 1095


def test_leaderboard_uses_best_round_per_player_for_identical_game(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    players = PlayerRepository(database)
    mia, ben = players.add("Mia"), players.add("Ben")
    repository = StatisticsRepository(database)
    repository.add(RoundStatistic(mia.id, "game", "Spiel", "sha256:a", 8, 10, 30.0))
    repository.add(RoundStatistic(mia.id, "game", "Spiel", "sha256:a", 9, 10, 30.0))
    repository.add(RoundStatistic(ben.id, "game", "Spiel", "sha256:a", 10, 10, 50.0))
    repository.add(RoundStatistic(ben.id, "game", "Spiel", "sha256:b", 10, 10, 1.0))

    leaderboard = repository.leaderboard("sha256:a")

    assert [entry.player_name for entry in leaderboard] == ["Ben", "Mia"]
    assert [entry.rank for entry in leaderboard] == [1, 2]
    assert leaderboard[0].score == 1200
    assert leaderboard[1].score == 1095


def test_live_score_events_and_explicit_score_survive_round_trip(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    player = PlayerRepository(database).add("Mia")
    repository = StatisticsRepository(database)
    events = (ScoreEvent(1.5, True, 1), ScoreEvent(3.0, False, 0))
    repository.add(
        RoundStatistic(
            player.id,
            "game",
            "Spiel",
            "sha256:a",
            1,
            2,
            3.0,
            events=events,
            score_value=0,
        )
    )

    loaded = repository.load(player.id)[0]

    assert loaded.events == events
    assert loaded.score == 0
    assert repository.best_round(player.id, "sha256:a") == loaded


def test_complete_event_shape_survives_round_trip(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    player = PlayerRepository(database).add("Mia")
    repository = StatisticsRepository(database)
    event = ScoreEvent(
        2.5,
        True,
        3,
        task_id="task-7",
        task_number=7,
        event_kind="correct_answer",
        task_completed=True,
        correct_answers=5,
        completed_tasks=7,
        combo=2,
        end_reason="task_target_reached",
    )
    repository.add(
        RoundStatistic(player.id, "game", "Spiel", "sha256:a", 5, 7, 2.5, events=(event,))
    )

    loaded = repository.load(player.id)[0]

    assert loaded.events == (event,)
    assert loaded.event_schema_version == 2


def test_historical_events_are_filtered_by_concrete_race_rule(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    player = PlayerRepository(database).add("Mia")
    repository = StatisticsRepository(database)
    repository.add(
        RoundStatistic(
            player.id,
            "game",
            "Spiel",
            "sha256:a",
            1,
            1,
            2.0,
            events=(ScoreEvent(1.0, True, 1),),
            event_schema_version=1,
        )
    )

    answer_race = RaceConfig(RaceKind.CORRECT_ANSWERS, correct_target=1)
    task_race = RaceConfig(RaceKind.TASKS, task_target=1)

    assert len(repository.race_competitors("sha256:a", answer_race)) == 1
    assert repository.race_competitors("sha256:a", race=task_race) == []


def test_race_uses_requested_number_of_best_runs_from_identical_game(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    players = PlayerRepository(database)
    mia, ben, lio = players.add("Mia"), players.add("Ben", icon="🦊"), players.add("Lio")
    repository = StatisticsRepository(database)

    def add_run(player_id: int, definition_hash: str, score: int) -> None:
        repository.add(
            RoundStatistic(
                player_id,
                "game",
                "Spiel",
                definition_hash,
                1,
                1,
                2.0,
                events=(ScoreEvent(1.0, True, score),),
                score_value=score,
            )
        )

    add_run(mia.id, "sha256:a", 4)
    add_run(ben.id, "sha256:a", 7)
    add_run(lio.id, "sha256:a", 5)
    add_run(mia.id, "sha256:other", 99)

    competitors = repository.race_competitors("sha256:a", limit=2)

    assert [item.player_name for item in competitors] == ["Ben", "Lio"]
    assert [item.statistic.score for item in competitors] == [7, 5]
    assert [item.player_icon for item in competitors] == ["🦊", "🙂"]


def test_computer_rival_is_fallible_repeatable_and_level_scaled() -> None:
    race = RaceConfig(RaceKind.TASKS, task_target=20)
    easy = computer_competitor("sha256:a", race, level=1, seed=4)
    hard = computer_competitor("sha256:a", race, level=10, seed=4)
    repeated = computer_competitor("sha256:a", race, level=10, seed=4)

    assert easy.player_name.endswith("P10%")
    assert hard.player_name.endswith("P90%")
    assert hard.statistic.events == repeated.statistic.events
    assert any(not event.correct for event in hard.statistic.events)
    assert hard.statistic.score > easy.statistic.score


def test_linear_computer_rival_has_regular_event_intervals() -> None:
    rival = computer_competitor(
        "sha256:a",
        RaceConfig(RaceKind.TASKS, task_target=10),
        level=5,
        variable=False,
    )
    times = [event.elapsed_seconds for event in rival.statistic.events]
    intervals = [round(right - left, 6) for left, right in zip([0.0, *times], times, strict=False)]

    assert len(set(intervals)) == 1


def test_timeout_event_and_penalized_score_survive_without_rewriting_counters(
    tmp_path: Path,
) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    player = PlayerRepository(database).add("Mia")
    repository = StatisticsRepository(database)
    events = (
        ScoreEvent(
            1.0,
            True,
            1,
            task_number=1,
            event_kind="correct_answer",
            task_completed=True,
            correct_answers=1,
            completed_tasks=1,
            combo=1,
        ),
        ScoreEvent(
            6.0,
            False,
            -2,
            task_number=2,
            event_kind="timeout",
            task_completed=True,
            correct_answers=1,
            completed_tasks=2,
            combo=0,
        ),
    )
    repository.add(
        RoundStatistic(
            player.id,
            "timer",
            "Aufgaben-Timer",
            "sha256:timer",
            correct=1,
            total=2,
            elapsed_seconds=6.0,
            events=events,
            score_value=-2,
        )
    )

    loaded = repository.load(player.id)[0]

    assert loaded.score == -2
    assert loaded.events[-1].event_kind == "timeout"
    assert loaded.events[-1].correct_answers == 1
    assert loaded.events[-1].completed_tasks == 2


def test_race_competitors_reject_incomplete_or_unknown_historical_events(
    tmp_path: Path,
) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    player = PlayerRepository(database).add("Mia")
    repository = StatisticsRepository(database)
    race = RaceConfig(RaceKind.TASKS, task_target=2)

    for definition_hash, event in (
        (
            "sha256:incomplete",
            ScoreEvent(1.0, True, 1, event_kind="correct_answer", task_completed=True),
        ),
        (
            "sha256:unknown",
            ScoreEvent(
                1.0,
                True,
                1,
                event_kind="legacy_bonus",
                task_completed=True,
                correct_answers=1,
                completed_tasks=1,
                combo=1,
            ),
        ),
    ):
        repository.add(
            RoundStatistic(
                player.id,
                "game",
                "Spiel",
                definition_hash,
                1,
                1,
                1.0,
                events=(event,),
            )
        )
        assert repository.race_competitors(definition_hash, race=race) == []
