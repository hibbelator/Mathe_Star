import time
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from math_game.app.flet_app import MathAdventureApp, parse_race_levels
from math_game.app.session import RoundPhase
from math_game.core.contracts import GameMode
from math_game.core.presets import EXCEL_PRESETS, DefinedGame
from math_game.core.race import RaceConfig, RaceKind


def test_race_tick_updates_only_live_panel_and_keeps_answer_field() -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    answer_field = SimpleNamespace(value="17")
    panel = SimpleNamespace(content="old", update_calls=0)
    panel.update = lambda: setattr(panel, "update_calls", panel.update_calls + 1)
    dynamic_app.ghost_tick_timer = object()
    dynamic_app.dialog_open = False
    dynamic_app.race_state = object()
    # A visible correct/wrong feedback must not stop the recurring race clock.
    dynamic_app.session = SimpleNamespace(phase=RoundPhase.TASK, feedback=object())
    dynamic_app.race_live_panel = panel
    dynamic_app.answer_field = answer_field
    dynamic_app._build_race_panel = lambda: SimpleNamespace(content="new")
    dynamic_app._schedule_ghost_tick = lambda: None
    dynamic_app.render = lambda: (_ for _ in ()).throw(AssertionError("full render"))

    dynamic_app._ghost_tick()

    assert panel.content == "new"
    assert panel.update_calls == 1
    assert answer_field.value == "17"


def test_race_levels_accept_ranges_and_individual_runners() -> None:
    assert parse_race_levels("3-5") == [3, 4, 5]
    assert parse_race_levels("1, 5, 9") == [1, 5, 9]
    assert parse_race_levels("2, 2, 4") == [2, 4]


def test_race_dialog_uses_page_close_for_cancel_and_start() -> None:
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
    time.sleep(0.2)

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
