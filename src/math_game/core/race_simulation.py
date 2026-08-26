"""Seeded computer inputs for the canonical race engine.

This module only decides *when* a computer answers and whether that input is
correct. Completion, elimination, score, streak and progress remain derived by
``apply_race_event``, exactly as they are for human racers.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from math_game.core.race import (
    RaceConfig,
    RaceEvent,
    RaceEventKind,
    RaceKind,
    RacerState,
    RacerStatus,
    RaceState,
    apply_race_event,
)

SAFETY_ATTEMPT_LIMIT = 10_000


@dataclass(frozen=True, slots=True)
class SimulatedRaceEvent:
    event: RaceEvent
    racer: RacerState


@dataclass(frozen=True, slots=True)
class RaceSimulation:
    events: tuple[SimulatedRaceEvent, ...]
    state: RaceState


def simulate_race(
    config: RaceConfig, *, level: int, seed: int = 0, variable: bool = True
) -> RaceSimulation:
    """Simulate one level 1--10 racer, stopping at rules or the safety limit.

    Higher levels primarily answer faster and have a lower error probability.
    Random sampling intentionally means that strength is statistical, not a
    guarantee that a higher level wins every particular race.
    """

    if not 1 <= level <= 10:
        raise ValueError("Die Computerstufe muss zwischen 1 und 10 liegen.")
    rng = random.Random(seed + level * 7919)
    mean_response = 4.7 - level * 0.10
    error_probability = 0.31 - level * 0.022
    state = RaceState.create(["computer"])
    result: list[SimulatedRaceEvent] = []
    elapsed = 0.0

    for _ in range(SAFETY_ATTEMPT_LIMIT):
        if state.racers[0].status is not RacerStatus.RACING:
            break
        response = mean_response * (rng.uniform(0.65, 1.35) if variable else 1.0)
        deadline = config.task_timeout_seconds
        kind = RaceEventKind.CORRECT_ANSWER
        if deadline is not None and response > deadline:
            response, kind = deadline, RaceEventKind.TIMEOUT
        elif rng.random() < error_probability:
            kind = RaceEventKind.WRONG_ANSWER

        event_time = elapsed + response
        if config.kind is RaceKind.TIME_LIMIT and event_time >= (config.duration_seconds or 0):
            limit = config.duration_seconds or 0
            terminal = RaceEvent(RaceEventKind.TIME_ELAPSED, elapsed_seconds=limit)
            state = apply_race_event(config, state, terminal)
            result.append(SimulatedRaceEvent(terminal, state.racers[0]))
            break

        elapsed = event_time
        event = RaceEvent(kind, "computer", elapsed)
        state = apply_race_event(config, state, event)
        result.append(SimulatedRaceEvent(event, state.racers[0]))

    return RaceSimulation(tuple(result), state)
