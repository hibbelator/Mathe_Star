import pytest

from math_game.modes.accuracy import AccuracyMode, AccuracyPhase
from math_game.modes.blitz import BlitzMode, BlitzPhase
from math_game.modes.plumi_endless import EndlessPhase, PluMiEndlessMode
from math_game.modes.warm_up import WarmUpMode, WarmUpPhase


def test_blitz_stops_at_deadline_and_keeps_session_leaderboard() -> None:
    mode = BlitzMode(30)
    mode.start(100.0)
    assert mode.submit(4, 4, 129.9)
    assert mode.tick(130.0)
    assert mode.phase is BlitzPhase.FINISHED
    assert mode.leaderboard == [1]
    mode.start(200.0)
    mode.submit(2, 2, 201.0)
    mode.submit(3, 3, 202.0)
    mode.tick(230.0)
    assert mode.leaderboard == [2, 1]


def test_blitz_duration_is_intentionally_short() -> None:
    with pytest.raises(ValueError, match="30 und 60"):
        BlitzMode(90)


def test_accuracy_scores_only_the_quote() -> None:
    mode = AccuracyMode(task_count=3)
    mode.start()
    mode.submit(1, 1)
    mode.submit(0, 2)
    mode.submit(3, 3)
    assert mode.phase is AccuracyPhase.FINISHED
    assert mode.accuracy == 2 / 3


def test_plumi_endless_finishes_on_exactly_the_third_error() -> None:
    mode = PluMiEndlessMode()
    mode.start()
    assert mode.submit(4, 4)
    assert not mode.submit(0, 1)
    assert not mode.submit(0, 1)
    assert mode.phase is EndlessPhase.PLAYING
    assert not mode.submit(0, 1)
    assert mode.phase is EndlessPhase.FINISHED
    assert mode.score == 1


def test_warm_up_hands_over_after_exactly_sixty_seconds() -> None:
    mode = WarmUpMode()
    mode.start(10.0)
    assert mode.submit(2, 2, 69.9)
    assert mode.tick(70.0)
    assert mode.phase is WarmUpPhase.MAIN_GAME_READY
