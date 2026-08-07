from pathlib import Path

from math_game.app.database import AppDatabase
from math_game.app.players import PlayerRepository
from math_game.app.stats import RoundStatistic, StatisticsRepository


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
