from __future__ import annotations

import pytest

from math_game.core.contracts import EndReason, GameMode
from math_game.core.presets import DefinedGame, OperationWeights
from math_game.core.race import (
    RaceConfig,
    RaceEvent,
    RaceEventKind,
    RaceKind,
    RacerStatus,
    RaceState,
    apply_race_event,
    progress,
    race_config_for_game,
)


def test_config_accepts_only_the_target_belonging_to_its_rule() -> None:
    RaceConfig(RaceKind.TASKS, task_target=3)
    with pytest.raises(ValueError, match="task_target is required"):
        RaceConfig(RaceKind.TASKS, correct_target=3)
    with pytest.raises(ValueError, match="unexpected targets"):
        RaceConfig(RaceKind.TASKS, task_target=3, duration_seconds=10)


def test_task_race_finishes_and_breaks_equal_progress_by_correct_answers() -> None:
    config = RaceConfig(RaceKind.TASKS, task_target=2)
    state = RaceState.create(["Ada", "Bert"])
    state = apply_race_event(config, state, RaceEvent(RaceEventKind.WRONG_ANSWER, "Ada", 1))
    state = apply_race_event(config, state, RaceEvent(RaceEventKind.CORRECT_ANSWER, "Bert", 2))
    state = apply_race_event(config, state, RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 3))

    assert state.finished
    assert state.end_reason is EndReason.TASK_TARGET_REACHED
    assert state.winner_id == "Ada"
    assert state.racers[0].finish_time == 3
    assert state.standings[0].progress == 1


def test_perfect_race_eliminates_one_racer_but_continues() -> None:
    config = RaceConfig(RaceKind.PERFECT, correct_target=2)
    state = RaceState.create(["Ada", "Bert"])
    state = apply_race_event(config, state, RaceEvent(RaceEventKind.TIMEOUT, "Ada", 1))
    assert not state.finished
    assert state.racers[0].status is RacerStatus.ELIMINATED
    assert state.racers[0].end_reason is EndReason.FIRST_ERROR

    state = apply_race_event(config, state, RaceEvent(RaceEventKind.CORRECT_ANSWER, "Bert", 2))
    state = apply_race_event(config, state, RaceEvent(RaceEventKind.CORRECT_ANSWER, "Bert", 3))
    assert state.winner_id == "Bert"
    assert state.end_reason is EndReason.CORRECT_TARGET_REACHED


def test_time_is_an_explicit_event_and_progress_is_clamped() -> None:
    config = RaceConfig(RaceKind.TIME_LIMIT, duration_seconds=10)
    state = RaceState.create(["Ada"])
    state = apply_race_event(
        config, state, RaceEvent(RaceEventKind.TIME_ELAPSED, elapsed_seconds=12)
    )
    assert state.finished
    assert state.end_reason is EndReason.TIME_LIMIT_REACHED
    assert progress(config, state.racers[0]) == 1


def test_standing_is_a_complete_ui_projection_and_counts_timeouts() -> None:
    config = RaceConfig(RaceKind.TASKS, task_target=3, task_timeout_seconds=5)
    state = apply_race_event(
        config,
        RaceState.create(["Ada"]),
        RaceEvent(RaceEventKind.TIMEOUT, "Ada", 4),
    )

    standing = state.standings[0]
    assert standing.completed_tasks == 1
    assert standing.timeouts == 1
    assert standing.errors == 1
    assert standing.elapsed_seconds == 4
    assert standing.end_reason is None


def test_abort_has_no_winner() -> None:
    state = apply_race_event(
        RaceConfig(RaceKind.COMBO, combo_target=3),
        RaceState.create(["Ada", "Bert"]),
        RaceEvent(RaceEventKind.ABORT, "Ada", 1),
    )
    assert state.finished
    assert state.end_reason is EndReason.ABORTED
    assert state.winner_id is None


def _game(mode: GameMode, *, task_count: int | None = 5) -> DefinedGame:
    return DefinedGame(
        identifier="race-test",
        name="Race test",
        weights=OperationWeights(addition=1),
        allowed_tables=(),
        factor_min=1,
        factor_max=10,
        max_result=20,
        mode=mode,
        duration_seconds=30,
        task_count=task_count,
        correct_target=4,
    )


def test_factory_maps_supported_mode_and_explicitly_rejects_unsupported_mode() -> None:
    available = race_config_for_game(_game(GameMode.TASK_SPRINT))
    assert available.available and available.config == RaceConfig(RaceKind.TASKS, task_target=5)

    unavailable = race_config_for_game(_game(GameMode.PRACTICE))
    assert not unavailable.available
    assert unavailable.config is None
    assert "practice" in (unavailable.reason or "")


def test_factory_reports_missing_required_value_as_unavailable() -> None:
    unavailable = race_config_for_game(_game(GameMode.TASK_SPRINT, task_count=None))
    assert not unavailable.available
    assert "task_target" in (unavailable.reason or "")
