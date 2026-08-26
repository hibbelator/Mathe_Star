"""Deterministic, frontend-independent rules for multiplayer races.

Time never passes implicitly in this module.  The caller reports elapsed time
as an event, which makes replaying a race produce exactly the same result.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from math_game.core.contracts import EndReason, GameMode
from math_game.core.presets import DefinedGame


class RaceKind(StrEnum):
    TASKS = "tasks"
    CORRECT_ANSWERS = "correct_answers"
    TIME_LIMIT = "time_limit"
    PERFECT = "perfect"
    COMBO = "combo"


class RaceEventKind(StrEnum):
    CORRECT_ANSWER = "correct_answer"
    WRONG_ANSWER = "wrong_answer"
    TIMEOUT = "timeout"
    ABORT = "abort"
    TIME_ELAPSED = "time_elapsed"


class RacerStatus(StrEnum):
    RACING = "racing"
    FINISHED = "finished"
    ELIMINATED = "eliminated"
    ABORTED = "aborted"


@dataclass(frozen=True, slots=True)
class RaceConfig:
    kind: RaceKind
    task_target: int | None = None
    correct_target: int | None = None
    duration_seconds: float | None = None
    combo_target: int | None = None
    wrong_answer_penalty: int = 0
    task_timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        supplied = {
            "task_target": self.task_target,
            "correct_target": self.correct_target,
            "duration_seconds": self.duration_seconds,
            "combo_target": self.combo_target,
        }
        required = {
            RaceKind.TASKS: "task_target",
            RaceKind.CORRECT_ANSWERS: "correct_target",
            RaceKind.TIME_LIMIT: "duration_seconds",
            RaceKind.PERFECT: "correct_target",
            RaceKind.COMBO: "combo_target",
        }[self.kind]
        if supplied[required] is None:
            raise ValueError(f"{required} is required for {self.kind.value}")
        extras = [
            name for name, value in supplied.items() if name != required and value is not None
        ]
        if extras:
            raise ValueError(f"unexpected targets for {self.kind.value}: {', '.join(extras)}")
        if any(value is not None and value <= 0 for value in supplied.values()):
            raise ValueError("race targets must be positive")
        if self.wrong_answer_penalty > 0:
            raise ValueError("wrong_answer_penalty must be zero or negative")
        if self.task_timeout_seconds is not None and self.task_timeout_seconds <= 0:
            raise ValueError("task_timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class RaceEvent:
    kind: RaceEventKind
    racer_id: str | None = None
    elapsed_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.kind is RaceEventKind.TIME_ELAPSED:
            if self.racer_id is not None or self.elapsed_seconds is None:
                raise ValueError("time-elapsed events need elapsed_seconds and no racer_id")
        elif self.racer_id is None:
            raise ValueError("racer events need racer_id")
        if self.elapsed_seconds is not None and self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must not be negative")


@dataclass(frozen=True, slots=True)
class RacerState:
    racer_id: str
    score: int = 0
    correct_answers: int = 0
    completed_tasks: int = 0
    errors: int = 0
    streak: int = 0
    elapsed_seconds: float = 0
    finish_time: float | None = None
    status: RacerStatus = RacerStatus.RACING
    end_reason: EndReason | None = None


@dataclass(frozen=True, slots=True)
class RaceStanding:
    racer_id: str
    rank: int
    status: RacerStatus
    progress: float
    sort_key: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class RaceState:
    racers: tuple[RacerState, ...]
    standings: tuple[RaceStanding, ...] = ()
    winner_id: str | None = None
    finished: bool = False
    end_reason: EndReason | None = None

    @classmethod
    def create(cls, racer_ids: tuple[str, ...] | list[str]) -> RaceState:
        if not racer_ids or len(set(racer_ids)) != len(racer_ids):
            raise ValueError("racer ids must be non-empty and unique")
        if any(not racer_id.strip() for racer_id in racer_ids):
            raise ValueError("racer ids must not be blank")
        return cls(tuple(RacerState(racer_id) for racer_id in racer_ids))


@dataclass(frozen=True, slots=True)
class RaceAvailability:
    available: bool
    config: RaceConfig | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.available != (self.config is not None):
            raise ValueError("available races need a config; unavailable races must not have one")
        if not self.available and not self.reason:
            raise ValueError("unavailable races need a reason")


def race_config_for_game(game: DefinedGame) -> RaceAvailability:
    """Translate a known game mode without inventing a points fallback."""

    try:
        if game.mode in {GameMode.FIXED_TASKS, GameMode.TASK_SPRINT, GameMode.ACCURACY}:
            return RaceAvailability(True, RaceConfig(RaceKind.TASKS, task_target=game.task_count))
        if game.mode is GameMode.PER_TASK_TIMER:
            return RaceAvailability(
                True,
                RaceConfig(
                    RaceKind.TASKS,
                    task_target=game.task_count,
                    task_timeout_seconds=game.per_task_seconds,
                ),
            )
        if game.mode is GameMode.TARGET_HUNT:
            return RaceAvailability(
                True, RaceConfig(RaceKind.CORRECT_ANSWERS, correct_target=game.correct_target)
            )
        if game.mode in {GameMode.TIMED, GameMode.TIME_ATTACK, GameMode.BLITZ}:
            return RaceAvailability(
                True,
                RaceConfig(
                    RaceKind.TIME_LIMIT,
                    duration_seconds=game.duration_seconds,
                    wrong_answer_penalty=game.wrong_answer_penalty,
                ),
            )
        if game.mode is GameMode.PERFECT_RUN:
            return RaceAvailability(
                True, RaceConfig(RaceKind.PERFECT, correct_target=game.correct_target)
            )
        if game.mode is GameMode.COMBO:
            return RaceAvailability(
                True, RaceConfig(RaceKind.COMBO, combo_target=game.correct_target)
            )
    except ValueError as error:
        return RaceAvailability(False, reason=f"Ungültige Rennkonfiguration: {error}")
    return RaceAvailability(False, reason=f"Der Modus {game.mode.value} unterstützt keine Rennen.")


def progress(config: RaceConfig, racer: RacerState) -> float:
    """Return rule-specific subject progress, always clamped to ``0..1``."""

    numerator, denominator = {
        RaceKind.TASKS: (racer.completed_tasks, config.task_target),
        RaceKind.CORRECT_ANSWERS: (racer.correct_answers, config.correct_target),
        RaceKind.TIME_LIMIT: (racer.elapsed_seconds, config.duration_seconds),
        RaceKind.PERFECT: (racer.correct_answers, config.correct_target),
        RaceKind.COMBO: (racer.streak, config.combo_target),
    }[config.kind]
    assert denominator is not None
    return min(1.0, max(0.0, numerator / denominator))


def apply_race_event(config: RaceConfig, state: RaceState, event: RaceEvent) -> RaceState:
    """Apply one input and derive participant completion, ranking and winner."""

    if state.finished:
        return state
    racers = list(state.racers)
    if event.kind is RaceEventKind.TIME_ELAPSED:
        assert event.elapsed_seconds is not None
        racers = [_at_elapsed(racer, event.elapsed_seconds) for racer in racers]
    else:
        index = next((i for i, racer in enumerate(racers) if racer.racer_id == event.racer_id), -1)
        if index < 0:
            raise KeyError(f"unknown racer: {event.racer_id}")
        racers[index] = _apply_to_racer(config, racers[index], event)

    racers = [_finish_if_needed(config, racer) for racer in racers]
    race_finished = _race_finished(config, racers, event)
    reason = _race_end_reason(config, racers, event) if race_finished else None
    standings = _standings(config, racers)
    winner = (
        standings[0].racer_id
        if race_finished and standings and reason is not EndReason.ABORTED
        else None
    )
    return RaceState(tuple(racers), standings, winner, race_finished, reason)


def _apply_to_racer(config: RaceConfig, racer: RacerState, event: RaceEvent) -> RacerState:
    if racer.status is not RacerStatus.RACING:
        return racer
    elapsed = max(racer.elapsed_seconds, event.elapsed_seconds or racer.elapsed_seconds)
    if event.kind is RaceEventKind.ABORT:
        return replace(
            racer,
            elapsed_seconds=elapsed,
            finish_time=elapsed,
            status=RacerStatus.ABORTED,
            end_reason=EndReason.ABORTED,
        )
    if event.kind is RaceEventKind.CORRECT_ANSWER:
        return replace(
            racer,
            score=racer.score + 1,
            correct_answers=racer.correct_answers + 1,
            completed_tasks=racer.completed_tasks + 1,
            streak=racer.streak + 1,
            elapsed_seconds=elapsed,
        )
    return replace(
        racer,
        score=racer.score + config.wrong_answer_penalty,
        completed_tasks=racer.completed_tasks + 1,
        errors=racer.errors + 1,
        streak=0,
        elapsed_seconds=elapsed,
    )


def _at_elapsed(racer: RacerState, elapsed: float) -> RacerState:
    return replace(racer, elapsed_seconds=max(racer.elapsed_seconds, elapsed))


def _finish_if_needed(config: RaceConfig, racer: RacerState) -> RacerState:
    if racer.status is not RacerStatus.RACING:
        return racer
    reason: EndReason | None = None
    status = RacerStatus.FINISHED
    if config.kind is RaceKind.TASKS and racer.completed_tasks >= (config.task_target or 0):
        reason = EndReason.TASK_TARGET_REACHED
    elif config.kind in {RaceKind.CORRECT_ANSWERS, RaceKind.PERFECT} and racer.correct_answers >= (
        config.correct_target or 0
    ):
        reason = EndReason.CORRECT_TARGET_REACHED
    elif config.kind is RaceKind.COMBO and racer.streak >= (config.combo_target or 0):
        reason = EndReason.COMBO_TARGET_REACHED
    elif config.kind is RaceKind.PERFECT and racer.errors:
        reason, status = EndReason.FIRST_ERROR, RacerStatus.ELIMINATED
    elif config.kind is RaceKind.TIME_LIMIT and racer.elapsed_seconds >= (
        config.duration_seconds or 0
    ):
        reason = EndReason.TIME_LIMIT_REACHED
    if reason is None:
        return racer
    return replace(racer, finish_time=racer.elapsed_seconds, status=status, end_reason=reason)


def _race_finished(config: RaceConfig, racers: list[RacerState], event: RaceEvent) -> bool:
    if event.kind is RaceEventKind.ABORT:
        return True
    if config.kind is RaceKind.TIME_LIMIT:
        return all(racer.status is not RacerStatus.RACING for racer in racers)
    return any(racer.status is RacerStatus.FINISHED for racer in racers) or all(
        racer.status is not RacerStatus.RACING for racer in racers
    )


def _race_end_reason(config: RaceConfig, racers: list[RacerState], event: RaceEvent) -> EndReason:
    if event.kind is RaceEventKind.ABORT:
        return EndReason.ABORTED
    finisher = next((racer for racer in racers if racer.status is RacerStatus.FINISHED), None)
    if finisher and finisher.end_reason:
        return finisher.end_reason
    return EndReason.FIRST_ERROR if config.kind is RaceKind.PERFECT else EndReason.COMPLETED


def _standings(config: RaceConfig, racers: list[RacerState]) -> tuple[RaceStanding, ...]:
    def key(racer: RacerState) -> tuple[float, ...]:
        # More progress/correct/score is better; fewer errors and less time break ties.
        return (
            -progress(config, racer),
            -racer.correct_answers,
            -racer.score,
            racer.errors,
            racer.finish_time if racer.finish_time is not None else racer.elapsed_seconds,
        )

    ordered = sorted(racers, key=lambda racer: (*key(racer), racer.racer_id))
    result: list[RaceStanding] = []
    previous: tuple[float, ...] | None = None
    rank = 0
    for position, racer in enumerate(ordered, 1):
        racer_key = key(racer)
        if racer_key != previous:
            rank = position
        result.append(
            RaceStanding(racer.racer_id, rank, racer.status, progress(config, racer), racer_key)
        )
        previous = racer_key
    return tuple(result)
