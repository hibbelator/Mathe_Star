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
