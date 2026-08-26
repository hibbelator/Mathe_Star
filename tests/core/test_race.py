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


def _replay(config: RaceConfig, *events: RaceEvent) -> RaceState:
    """Replay facts without involving wall-clock time or background workers."""

    state = RaceState.create(["Ada", "Bert"])
    for event in events:
        state = apply_race_event(config, state, event)
    return state


@pytest.mark.parametrize(
    "answers",
    [
        (RaceEventKind.CORRECT_ANSWER,) * 3,
        (RaceEventKind.WRONG_ANSWER,) * 3,
        (
            RaceEventKind.WRONG_ANSWER,
            RaceEventKind.CORRECT_ANSWER,
            RaceEventKind.WRONG_ANSWER,
        ),
    ],
)
def test_task_sprint_finishes_after_exactly_completed_task_target(
    answers: tuple[RaceEventKind, ...],
) -> None:
    config = RaceConfig(RaceKind.TASKS, task_target=3)
    state = RaceState.create(["Ada"])

    for number, answer in enumerate(answers, 1):
        state = apply_race_event(config, state, RaceEvent(answer, "Ada", float(number)))
        assert state.finished is (number == 3)

    assert state.racers[0].completed_tasks == 3
    assert state.racers[0].correct_answers == answers.count(RaceEventKind.CORRECT_ANSWER)


def test_target_hunt_ignores_wrong_answers_for_finish_line() -> None:
    config = RaceConfig(RaceKind.CORRECT_ANSWERS, correct_target=2)
    state = _replay(
        config,
        RaceEvent(RaceEventKind.WRONG_ANSWER, "Ada", 1),
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 2),
        RaceEvent(RaceEventKind.WRONG_ANSWER, "Ada", 3),
    )
    assert not state.finished

    state = apply_race_event(config, state, RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 4))
    assert state.finished
    assert state.racers[0].correct_answers == 2
    assert state.racers[0].completed_tasks == 4


def test_time_race_finishes_every_racer_together_and_ranks_correct_then_time() -> None:
    config = RaceConfig(RaceKind.TIME_LIMIT, duration_seconds=10, wrong_answer_penalty=-2)
    state = _replay(
        config,
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Bert", 2),
        RaceEvent(RaceEventKind.WRONG_ANSWER, "Bert", 3),
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 4),
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 6),
    )
    state = apply_race_event(
        config, state, RaceEvent(RaceEventKind.TIME_ELAPSED, elapsed_seconds=10)
    )

    assert state.finished
    assert {racer.finish_time for racer in state.racers} == {10}
    assert all(racer.end_reason is EndReason.TIME_LIMIT_REACHED for racer in state.racers)
    assert [standing.racer_id for standing in state.standings] == ["Ada", "Bert"]


@pytest.mark.parametrize("failure", [RaceEventKind.WRONG_ANSWER, RaceEventKind.TIMEOUT])
def test_perfect_run_only_eliminates_racer_with_first_final_failure(
    failure: RaceEventKind,
) -> None:
    state = _replay(
        RaceConfig(RaceKind.PERFECT, correct_target=3),
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 1),
        RaceEvent(failure, "Ada", 2),
    )

    assert state.racers[0].status is RacerStatus.ELIMINATED
    assert state.racers[1].status is RacerStatus.RACING
    assert not state.finished


def test_task_timeout_is_distinct_and_advances_task_progress() -> None:
    config = RaceConfig(RaceKind.TASKS, task_target=2, task_timeout_seconds=5)
    state = apply_race_event(
        config,
        RaceState.create(["Ada"]),
        RaceEvent(RaceEventKind.TIMEOUT, "Ada", 5),
    )

    racer = state.racers[0]
    assert racer.timeouts == racer.errors == racer.completed_tasks == 1
    assert racer.correct_answers == 0
    assert progress(config, racer) == 0.5
    assert not state.finished


def test_wrong_answer_penalty_changes_only_score_at_event_time() -> None:
    config = RaceConfig(RaceKind.TASKS, task_target=3, wrong_answer_penalty=-4)
    state = apply_race_event(
        config,
        RaceState.create(["Ada"]),
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 1),
    )
    before = state.racers[0]
    state = apply_race_event(config, state, RaceEvent(RaceEventKind.WRONG_ANSWER, "Ada", 2))
    after = state.racers[0]

    assert (before.score, before.completed_tasks, before.correct_answers) == (1, 1, 1)
    assert (after.score, after.completed_tasks, after.correct_answers) == (-3, 2, 1)


def test_equal_standings_share_rank_and_have_stable_identifier_order() -> None:
    config = RaceConfig(RaceKind.TASKS, task_target=3)
    state = _replay(
        config,
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Bert", 1),
        RaceEvent(RaceEventKind.CORRECT_ANSWER, "Ada", 1),
    )

    assert [(item.racer_id, item.rank) for item in state.standings] == [
        ("Ada", 1),
        ("Bert", 1),
    ]


def test_every_game_mode_has_a_tested_race_rule_or_explicit_unavailability() -> None:
    expected = {
        GameMode.PRACTICE: None,
        GameMode.TIMED: RaceKind.TIME_LIMIT,
        GameMode.FIXED_TASKS: RaceKind.TASKS,
        GameMode.MISTAKE_REVIEW: None,
        GameMode.TIME_ATTACK: RaceKind.TIME_LIMIT,
        GameMode.TASK_SPRINT: RaceKind.TASKS,
        GameMode.PERFECT_RUN: RaceKind.PERFECT,
        GameMode.TARGET_HUNT: RaceKind.CORRECT_ANSWERS,
        GameMode.PER_TASK_TIMER: RaceKind.TASKS,
        GameMode.COMBO: RaceKind.COMBO,
        GameMode.BLITZ: RaceKind.TIME_LIMIT,
        GameMode.ACCURACY: RaceKind.TASKS,
        GameMode.PLUMI_ENDLESS: None,
        GameMode.WARM_UP: None,
    }
    assert set(expected) == set(GameMode)

    for mode, kind in expected.items():
        availability = race_config_for_game(_game(mode))
        assert availability.available is (kind is not None), mode
        if kind is None:
            assert availability.config is None
            assert mode.value in (availability.reason or "")
        else:
            assert availability.config is not None
            assert availability.config.kind is kind
