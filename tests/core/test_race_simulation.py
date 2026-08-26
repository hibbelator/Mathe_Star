from math_game.core.contracts import EndReason
from math_game.core.race import RaceConfig, RaceEventKind, RaceKind, RacerStatus
from math_game.core.race_simulation import simulate_race


def kinds(config: RaceConfig, *, level: int = 5, seed: int = 1) -> list[RaceEventKind]:
    return [item.event.kind for item in simulate_race(config, level=level, seed=seed).events]


def finish_time(config: RaceConfig, level: int, seed: int) -> float:
    value = simulate_race(config, level=level, seed=seed).state.racers[0].finish_time
    assert value is not None
    return value


def test_task_sprint_completes_exactly_the_configured_number_of_tasks() -> None:
    result = simulate_race(RaceConfig(RaceKind.TASKS, task_target=12), level=4, seed=8)

    assert len(result.events) == 12
    assert result.state.racers[0].completed_tasks == 12
    assert result.state.racers[0].end_reason is EndReason.TASK_TARGET_REACHED


def test_time_race_has_no_late_answers_and_finishes_at_shared_limit() -> None:
    result = simulate_race(RaceConfig(RaceKind.TIME_LIMIT, duration_seconds=20), level=6, seed=2)

    assert result.events[-1].event.kind is RaceEventKind.TIME_ELAPSED
    assert result.events[-1].event.elapsed_seconds == 20
    assert all((item.event.elapsed_seconds or 0) <= 20 for item in result.events)
    assert result.state.racers[0].finish_time == 20


def test_target_hunt_reaches_correct_answer_target_via_engine() -> None:
    result = simulate_race(RaceConfig(RaceKind.CORRECT_ANSWERS, correct_target=15), level=3, seed=3)

    assert result.state.racers[0].correct_answers == 15
    assert result.state.racers[0].status is RacerStatus.FINISHED


def test_perfect_run_stops_on_first_final_error() -> None:
    result = simulate_race(RaceConfig(RaceKind.PERFECT, correct_target=100), level=1, seed=1)

    assert result.events[-1].event.kind is RaceEventKind.WRONG_ANSWER
    assert result.state.racers[0].status is RacerStatus.ELIMINATED
    assert result.state.racers[0].end_reason is EndReason.FIRST_ERROR


def test_task_deadline_creates_timeout_events() -> None:
    config = RaceConfig(RaceKind.TASKS, task_target=5, task_timeout_seconds=1)

    assert kinds(config) == [RaceEventKind.TIMEOUT] * 5


def test_combo_errors_reset_streak_before_engine_reaches_target() -> None:
    result = simulate_race(RaceConfig(RaceKind.COMBO, combo_target=5), level=2, seed=7)
    streaks = [item.racer.streak for item in result.events]

    assert 0 in streaks
    assert streaks[-1] == 5
    assert result.state.racers[0].end_reason is EndReason.COMBO_TARGET_REACHED


def test_level_strength_is_statistical_and_not_a_per_race_guarantee() -> None:
    # A one-task heat preserves enough natural variance for an occasional upset;
    # averaging many seeded heats still exposes the level advantage.
    config = RaceConfig(RaceKind.TASKS, task_target=1)
    easy_times = [finish_time(config, 1, seed) for seed in range(40)]
    hard_times = [finish_time(config, 10, seed) for seed in range(40)]

    assert sum(hard_times) < sum(easy_times)
    assert any(hard > easy for hard, easy in zip(hard_times, easy_times, strict=True))
