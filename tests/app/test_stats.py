from pathlib import Path

from math_game.app.stats import RoundStatistic, StatisticsRepository


def test_statistics_persist_and_choose_best_round(tmp_path: Path) -> None:
    repository = StatisticsRepository(tmp_path / "stats.json")
    repository.add(RoundStatistic("game", "Spiel", 7, 10, 20.0))
    repository.add(RoundStatistic("game", "Spiel", 9, 10, 30.0))

    loaded = repository.load()
    assert len(loaded) == 2
    assert loaded[0].accuracy == 0.7
    assert repository.best_by_game()["game"] == loaded[1]
