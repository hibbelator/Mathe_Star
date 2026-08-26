import asyncio
import time
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from math_game.app.flet_app import (
    MathAdventureApp,
    layout_metrics,
    normalize_integer_input,
    parse_race_levels,
)
from math_game.app.session import RoundPhase
from math_game.app.stats import ScoreEvent
from math_game.core.contracts import EndReason, GameMode
from math_game.core.presets import EXCEL_PRESETS, DefinedGame
from math_game.core.race import (
    RaceConfig,
    RaceEvent,
    RaceEventKind,
    RaceKind,
    RacerStatus,
    RaceState,
    apply_race_event,
)


@pytest.mark.parametrize("width", [320, 360, 390, 480])
def test_phone_layout_never_exceeds_available_width(width: int) -> None:
    metrics = layout_metrics(width)

    assert metrics.content_width <= width
    assert metrics.track_width <= metrics.content_width - 2 * metrics.padding
    assert metrics.track_width >= 220


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("42", "42"),
        ("0", "0"),
        ("-7", "-7"),
        (" 12 ", "12"),
        ("", ""),
        ("abc", ""),
        ("1.5", "15"),
        ("4-2", "42"),
    ],
)
def test_integer_input_normalization(raw: str, expected: str) -> None:
    assert normalize_integer_input(raw) == expected


def test_rapid_duplicate_submission_is_ignored() -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    dynamic_app.submission_in_progress = True
    dynamic_app.answer_field = SimpleNamespace(value="7")
    dynamic_app._active_session = lambda: (_ for _ in ()).throw(
        AssertionError("duplicate reached the session")
    )

    dynamic_app._on_submit_clicked(None)


@pytest.mark.parametrize(
    ("config", "events", "detail", "status"),
    [
        (RaceConfig(RaceKind.TASKS, task_target=20), [], "Aufgabe 0/20", "läuft"),
        (
            RaceConfig(RaceKind.CORRECT_ANSWERS, correct_target=25),
            [RaceEventKind.CORRECT_ANSWER] * 2,
            "2/25 richtig",
            "läuft",
        ),
        (
            RaceConfig(RaceKind.PERFECT, correct_target=20),
            [RaceEventKind.CORRECT_ANSWER, RaceEventKind.WRONG_ANSWER],
            "Serie 0",
            "nach Fehler ausgeschieden",
        ),
        (
            RaceConfig(RaceKind.TASKS, task_target=20, task_timeout_seconds=5),
            [RaceEventKind.TIMEOUT, RaceEventKind.TIMEOUT],
            "2 Timeouts · Aufgabe 2/20",
            "läuft",
        ),
    ],
)
def test_race_standing_drives_rule_specific_detail_and_status(
    config: RaceConfig,
    events: list[RaceEventKind],
    detail: str,
    status: str,
) -> None:
    state = RaceState.create(["player"])
    for elapsed, kind in enumerate(events, 1):
        state = apply_race_event(config, state, RaceEvent(kind, "player", elapsed))
    standing = (
        state.standings[0]
        if state.standings
        else apply_race_event(
            config, state, RaceEvent(RaceEventKind.TIME_ELAPSED, elapsed_seconds=0)
        ).standings[0]
    )

    dynamic_app: Any = MathAdventureApp
    assert dynamic_app._standing_detail(config, standing) == detail
    assert dynamic_app._standing_status(standing) == status


def test_time_race_uses_elapsed_progress_and_never_calls_timeout_a_finish_line() -> None:
    config = RaceConfig(RaceKind.TIME_LIMIT, duration_seconds=10)
    state = apply_race_event(
        config,
        RaceState.create(["player"]),
        RaceEvent(RaceEventKind.TIME_ELAPSED, elapsed_seconds=10),
    )

    assert state.standings[0].progress == 1
    assert state.standings[0].end_reason is EndReason.TIME_LIMIT_REACHED
    dynamic_app: Any = MathAdventureApp
    assert dynamic_app._standing_status(state.standings[0]) == "Zeit abgelaufen"


def test_race_tick_updates_only_live_panel_and_keeps_answer_field(monkeypatch: Any) -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    answer_field = SimpleNamespace(value="17")
    panel = SimpleNamespace(content="old", update_calls=0)
    panel.update = lambda: setattr(panel, "update_calls", panel.update_calls + 1)
    dynamic_app.ghost_tick_generation = 4
    dynamic_app.dialog_open = False
    dynamic_app.race_state = object()
    # A visible correct/wrong feedback must not stop the recurring race clock.
    dynamic_app.session = SimpleNamespace(phase=RoundPhase.TASK, feedback=object())
    dynamic_app.race_live_panel = panel
    dynamic_app.answer_field = answer_field
    dynamic_app._build_race_panel = lambda: SimpleNamespace(content="new")
    dynamic_app.render = lambda: (_ for _ in ()).throw(AssertionError("full render"))

    sleeps = [0]

    async def immediate_sleep(_: float) -> None:
        sleeps[0] += 1
        if sleeps[0] == 2:
            dynamic_app.session.phase = RoundPhase.FINISHED

    monkeypatch.setattr("math_game.app.flet_app.asyncio.sleep", immediate_sleep)
    asyncio.run(dynamic_app._ghost_tick(4))

    assert panel.content == "new"
    assert panel.update_calls == 1
    assert answer_field.value == "17"


def test_async_race_loop_refreshes_repeatedly_and_replays_opponent_events(
    monkeypatch: Any,
) -> None:
    """The clock, rather than answer submissions, drives several live frames."""

    now = [0.0]
    sleeps = [0]
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    dynamic_app.ghost_tick_generation = 7
    dynamic_app.dialog_open = False
    dynamic_app.round_started_at = 0.0
    dynamic_app.race_state = SimpleNamespace(config=RaceConfig(RaceKind.TASKS, task_target=3))
    dynamic_app.session = SimpleNamespace(phase=RoundPhase.TASK)
    dynamic_app.race_live_panel = SimpleNamespace()
    opponent_events = [ScoreEvent(1.0, True, 1, task_completed=True)]
    visible_progress: list[int] = []

    def unexpected_submit(_: object) -> None:
        raise AssertionError("tick submitted an answer")

    dynamic_app._on_submit_clicked = unexpected_submit

    def refresh() -> None:
        snapshot = dynamic_app._race_snapshot(
            [("player", "Du", "", ""), ("ghost", "Mia", "", "")],
            [[], opponent_events],
            now[0],
        )
        opponent = next(item for item in snapshot.standings if item.racer_id == "ghost")
        visible_progress.append(opponent.completed_tasks)

    async def controlled_sleep(seconds: float) -> None:
        assert seconds == 0.5
        now[0] += seconds
        sleeps[0] += 1
        if sleeps[0] == 4:
            dynamic_app.session.phase = RoundPhase.FINISHED

    dynamic_app._refresh_race_panel = refresh
    monkeypatch.setattr("math_game.app.flet_app.asyncio.sleep", controlled_sleep)
    monkeypatch.setattr("math_game.app.flet_app.time.monotonic", lambda: now[0])

    asyncio.run(dynamic_app._ghost_tick(7))

    assert visible_progress == [0, 1, 1]


def test_race_task_is_cancelled_for_dialog_and_navigation_then_rescheduled() -> None:
    class FakeTask:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    scheduled: list[tuple[object, int]] = []
    tasks: list[FakeTask] = []

    def run_task(handler: object, generation: int) -> FakeTask:
        scheduled.append((handler, generation))
        task = FakeTask()
        tasks.append(task)
        return task

    dynamic_app.page = SimpleNamespace(run_task=run_task)
    dynamic_app.ghost_tick_task = None
    dynamic_app.ghost_tick_generation = 0
    dynamic_app.dialog_open = False
    dynamic_app.dialog_paused_at = 0.0
    dynamic_app.round_started_at = time.monotonic()
    dynamic_app.race_state = object()
    dynamic_app.session = SimpleNamespace(phase=RoundPhase.TASK, feedback=None)
    dynamic_app.special_mode = None
    dynamic_app.special_deadline_timer = None
    dynamic_app.auto_advance_timer = None
    dynamic_app._cancel_special_deadline = lambda: None
    dynamic_app.render = lambda: None

    dynamic_app._schedule_ghost_tick()
    first_generation = scheduled[-1][1]
    dynamic_app._pause_for_dialog()
    assert tasks[0].cancelled

    dynamic_app._resume_after_dialog()
    assert scheduled[-1][1] > first_generation
    resumed_task = tasks[-1]

    dynamic_app._navigate("menu")
    assert resumed_task.cancelled
    assert dynamic_app.ghost_tick_task is None
    assert dynamic_app.ghost_tick_generation > scheduled[-1][1]


def test_race_levels_accept_ranges_and_individual_runners() -> None:
    assert parse_race_levels("3-5") == [3, 4, 5]
    assert parse_race_levels("1, 5, 9") == [1, 5, 9]
    assert parse_race_levels("2, 2, 4") == [2, 4]


def test_race_dialog_uses_page_close_for_cancel_and_start(monkeypatch: Any) -> None:
    class ImmediateTimer:
        def __init__(self, _: float, callback: Any) -> None:
            self.callback = callback

        def start(self) -> None:
            self.callback()

    monkeypatch.setattr("math_game.app.flet_app.threading.Timer", ImmediateTimer)
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    calls: list[tuple[str, object]] = []
    page = SimpleNamespace()

    def open_dialog(dialog: object) -> None:
        calls.append(("open", dialog))

    def close_dialog(dialog: object) -> None:
        calls.append(("close", dialog))

    def start_game(game: object, **_: object) -> None:
        calls.append(("start", game))

    def race_competitors(*_: object) -> list[object]:
        return []

    page.open = open_dialog
    page.close = close_dialog
    dynamic_app.page = page
    dynamic_app.active_player = None
    dynamic_app.dialog_open = False
    dynamic_app.dialog_paused_at = 0.0
    dynamic_app.round_started_at = 0.0
    dynamic_app.race_state = None
    dynamic_app.session = None
    dynamic_app.special_mode = None
    dynamic_app.special_deadline_timer = None
    dynamic_app._cancel_ghost_tick = lambda: None
    dynamic_app._cancel_auto_advance = lambda: None
    dynamic_app.statistics = SimpleNamespace(race_competitors=race_competitors)
    dynamic_app._start_game = start_game

    dynamic_app._configure_race(EXCEL_PRESETS[0])
    dialog: Any = calls[-1][1]
    dialog.actions[0].on_click(None)
    assert calls[-1] == ("close", dialog)

    dynamic_app._configure_race(EXCEL_PRESETS[0])
    dialog = calls[-1][1]
    dialog.update = lambda: None
    dialog.actions[1].on_click(None)

    assert calls[-2] == ("close", dialog)
    assert calls[-1] == ("start", EXCEL_PRESETS[0])


def _race_dialog(game: DefinedGame) -> tuple[Any, Any, list[Any]]:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    page = SimpleNamespace(opened=None, update=lambda: None)

    def open_dialog(dialog: object) -> None:
        page.opened = dialog

    def close_dialog(_: object) -> None:
        return None

    def race_competitors(*_: object) -> list[object]:
        return []

    def start_game(*_args: object, **_kwargs: object) -> None:
        return None

    page.open = open_dialog
    page.close = close_dialog
    dynamic_app.page = page
    dynamic_app.active_player = None
    dynamic_app.dialog_open = False
    dynamic_app.dialog_paused_at = 0.0
    dynamic_app.round_started_at = 0.0
    dynamic_app.race_state = None
    dynamic_app.session = None
    dynamic_app.special_mode = None
    dynamic_app.special_deadline_timer = None
    dynamic_app._cancel_ghost_tick = lambda: None
    dynamic_app._cancel_auto_advance = lambda: None
    dynamic_app.statistics = SimpleNamespace(race_competitors=race_competitors)
    dynamic_app._start_game = start_game

    dynamic_app._configure_race(game)
    dialog = page.opened
    return dynamic_app, dialog, dialog.content.content.controls


@pytest.mark.parametrize(
    ("game", "explanation", "editable_target"),
    [
        (
            replace(EXCEL_PRESETS[0], mode=GameMode.TASK_SPRINT, task_count=17),
            "Ziellinie nach 17 Aufgaben",
            False,
        ),
        (
            replace(EXCEL_PRESETS[0], mode=GameMode.TIME_ATTACK, duration_seconds=90),
            "Gemeinsames Rennende nach 90 Sekunden",
            False,
        ),
        (
            replace(EXCEL_PRESETS[0], mode=GameMode.TARGET_HUNT, correct_target=12),
            "Ziellinie nach 12 richtigen Antworten",
            True,
        ),
        (
            replace(EXCEL_PRESETS[0], mode=GameMode.PERFECT_RUN, correct_target=20),
            "Dein Lauf endet beim ersten endgültigen Fehler",
            False,
        ),
        (
            replace(
                EXCEL_PRESETS[0],
                mode=GameMode.PER_TASK_TIMER,
                task_count=14,
                per_task_seconds=8,
            ),
            "Deadline pro Aufgabe: 8 Sekunden · äußere Rennbegrenzung: 14 Aufgaben",
            False,
        ),
    ],
)
def test_race_dialog_explains_each_supported_mode_and_only_edits_target_hunt(
    game: DefinedGame, explanation: str, editable_target: bool
) -> None:
    _, dialog, controls = _race_dialog(game)

    assert explanation in [getattr(control, "value", None) for control in controls]
    target_fields = [
        control
        for control in controls
        if getattr(control, "label", None) == "Richtige Antworten bis zur Ziellinie"
    ]
    assert bool(target_fields) is editable_target
    assert dialog.actions[1].disabled is False


def test_target_hunt_validates_its_explicit_race_variant() -> None:
    game = replace(EXCEL_PRESETS[0], mode=GameMode.TARGET_HUNT, correct_target=12)
    _, dialog, controls = _race_dialog(game)
    target = next(
        control
        for control in controls
        if getattr(control, "label", None) == "Richtige Antworten bis zur Ziellinie"
    )
    error = controls[-1]

    target.value = "0"
    dialog.actions[1].on_click(None)

    assert error.value == "Das Rennziel muss mindestens 1 richtige Antwort sein."


def test_non_race_mode_names_reason_and_disables_start() -> None:
    game = replace(EXCEL_PRESETS[0], mode=GameMode.PRACTICE)
    _, dialog, controls = _race_dialog(game)

    explanations = [getattr(control, "value", None) for control in controls]
    assert "Der Modus practice unterstützt keine Rennen." in explanations
    assert dialog.actions[1].disabled is True


def test_changed_target_hunt_limit_gets_a_distinct_comparison_hash() -> None:
    game = replace(EXCEL_PRESETS[0], mode=GameMode.TARGET_HUNT, correct_target=12)
    original = RaceConfig(RaceKind.CORRECT_ANSWERS, correct_target=12)
    variant = RaceConfig(RaceKind.CORRECT_ANSWERS, correct_target=25)

    dynamic_app: Any = MathAdventureApp
    original_hash = dynamic_app._race_comparison_hash(game, original)
    variant_hash = dynamic_app._race_comparison_hash(game, variant)

    assert original_hash != game.definition_hash()
    assert variant_hash != original_hash


def test_next_task_updates_existing_controls_without_full_render() -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    session = SimpleNamespace(
        current_task=SimpleNamespace(prompt="8 + 7 = ?"),
        task_number=2,
        task_count=10,
        correct_count=1,
        results=[object()],
        progress=0.1,
        feedback=None,
    )
    dynamic_app.session = session
    dynamic_app.active_game = EXCEL_PRESETS[0]
    dynamic_app.live_score_events = []
    dynamic_app.round_started_at = time.monotonic()
    dynamic_app.task_number_text = SimpleNamespace(value="old")
    dynamic_app.task_score_text = SimpleNamespace(value="old")
    dynamic_app.task_progress = SimpleNamespace(value=0.0)
    dynamic_app.task_prompt = SimpleNamespace(value="old")
    dynamic_app.task_feedback = SimpleNamespace(
        visible=True, padding=0, border_radius=0, bgcolor=None, content=None
    )
    dynamic_app.task_action = SimpleNamespace(text="old", on_click=None, visible=False)
    dynamic_app.answer_field = SimpleNamespace(
        value="17", disabled=True, error_text="old", focus=lambda: None
    )
    dynamic_app.page = SimpleNamespace(update=lambda: None)
    dynamic_app.render = lambda: (_ for _ in ()).throw(AssertionError("full render"))

    dynamic_app._update_task_controls()

    assert dynamic_app.task_prompt.value == "8 + 7 = ?"
    assert dynamic_app.answer_field.value == ""
    assert dynamic_app.task_action.text == "Antwort prüfen"


def test_task_view_mounts_answer_field_before_render_focuses_it() -> None:
    """The answer field must belong to the page when render calls focus()."""

    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    dynamic_app.page = SimpleNamespace(width=390)
    dynamic_app.session = SimpleNamespace(
        current_task=SimpleNamespace(prompt="8 + 7"),
        task_number=1,
        task_count=10,
        correct_count=0,
        results=[],
        progress=0.0,
        feedback=None,
    )
    dynamic_app.active_game = EXCEL_PRESETS[0]
    dynamic_app.live_score_events = []
    dynamic_app.round_started_at = time.monotonic()
    dynamic_app.race_state = None

    view = dynamic_app._task_view()

    assert dynamic_app.answer_field in view.controls


def test_resize_updates_mounted_shell_without_full_render() -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    updates: list[str] = []
    dynamic_app.page = SimpleNamespace(width=360)
    dynamic_app.root_container = SimpleNamespace(
        width=760,
        padding=32,
        border_radius=28,
        update=lambda: updates.append("updated"),
    )
    dynamic_app.render = lambda: (_ for _ in ()).throw(AssertionError("full render"))

    dynamic_app._on_resize(None)

    metrics = layout_metrics(360)
    assert dynamic_app.root_container.width == metrics.content_width
    assert dynamic_app.root_container.padding == metrics.padding
    assert dynamic_app.root_container.border_radius == 18
    assert updates == ["updated"]


def test_players_view_stages_file_picker_until_old_page_is_cleaned() -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    pending: list[object] = []

    def no_players() -> list[object]:
        return []

    dynamic_app.page = SimpleNamespace(width=390, overlay=[])
    dynamic_app.pending_overlay_controls = pending
    dynamic_app.player_error = ""
    dynamic_app.players = SimpleNamespace(all=no_players)

    dynamic_app._players_view()

    assert dynamic_app.page.overlay == []
    assert len(pending) == 1
    assert type(pending[0]).__name__ == "FilePicker"


def test_recording_end_is_not_presented_as_finish_line() -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    dynamic_app.race_state = SimpleNamespace(config=RaceConfig(RaceKind.TASKS, task_target=3))
    identities = [("player", "Du", "", ""), ("ghost", "Mia", "", "")]
    events = [[], [ScoreEvent(1.0, True, 1, task_completed=True)]]

    state = dynamic_app._race_snapshot(identities, events, elapsed=2.0)
    ghost = next(item for item in state.standings if item.racer_id == "ghost")

    assert ghost.status is RacerStatus.RECORDING_ENDED
    assert dynamic_app._standing_status(ghost) == "Aufzeichnung beendet"
    assert ghost.end_reason is EndReason.COMPLETED


def test_dialog_pause_excludes_time_from_player_and_opponent_progress(monkeypatch: Any) -> None:
    now = [10.0]
    monkeypatch.setattr("math_game.app.flet_app.time.monotonic", lambda: now[0])
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    dynamic_app.dialog_open = False
    dynamic_app.dialog_paused_at = 0.0
    dynamic_app.round_started_at = 1.0
    dynamic_app.race_state = SimpleNamespace(
        config=RaceConfig(RaceKind.TIME_LIMIT, duration_seconds=20)
    )
    dynamic_app.session = SimpleNamespace(phase=RoundPhase.TASK, feedback=None)
    dynamic_app.special_mode = None
    dynamic_app.live_score_events = []
    dynamic_app._cancel_ghost_tick = lambda: None
    dynamic_app._cancel_auto_advance = lambda: None
    dynamic_app._cancel_special_deadline = lambda: None
    dynamic_app._schedule_ghost_tick = lambda: None

    before = dynamic_app._race_snapshot(
        [("player", "Du", "", ""), ("ghost", "Mia", "", "")], [[], []], 9.0
    )
    dynamic_app._pause_for_dialog()
    now[0] = 110.0
    dynamic_app._resume_after_dialog()
    elapsed = now[0] - dynamic_app.round_started_at
    after = dynamic_app._race_snapshot(
        [("player", "Du", "", ""), ("ghost", "Mia", "", "")], [[], []], elapsed
    )

    assert elapsed == 9.0
    assert [item.progress for item in after.standings] == [
        item.progress for item in before.standings
    ]


def test_finished_render_cancels_ghost_task_and_auto_advance_timer() -> None:
    class FakeTimer:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    ghost, advance = FakeTimer(), FakeTimer()
    dynamic_app.ghost_tick_task = ghost
    dynamic_app.ghost_tick_generation = 2
    dynamic_app.auto_advance_timer = advance
    dynamic_app.special_mode = None
    dynamic_app.session = SimpleNamespace(phase=RoundPhase.FINISHED)
    dynamic_app.statistic_saved = True
    dynamic_app.active_game = None
    dynamic_app.active_player = None
    dynamic_app.answer_field = None
    dynamic_app.dialog_open = False
    dynamic_app.race_state = SimpleNamespace()

    def add_control(_: object) -> None:
        return None

    dynamic_app.page = SimpleNamespace(
        clean=lambda: None, add=add_control, update=lambda: None, overlay=[]
    )
    dynamic_app._finished_view = lambda: SimpleNamespace()

    dynamic_app.render()

    assert ghost.cancelled and advance.cancelled
    assert dynamic_app.ghost_tick_task is None
    assert dynamic_app.ghost_tick_generation == 3
    assert dynamic_app.auto_advance_timer is None
