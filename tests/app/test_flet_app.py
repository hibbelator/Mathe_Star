from types import SimpleNamespace
from typing import Any

from math_game.app.flet_app import MathAdventureApp, parse_race_levels
from math_game.app.session import RoundPhase
from math_game.core.presets import EXCEL_PRESETS


def test_race_tick_updates_only_live_panel_and_keeps_answer_field() -> None:
    app = MathAdventureApp.__new__(MathAdventureApp)
    dynamic_app: Any = app
    answer_field = SimpleNamespace(value="17")
    panel = SimpleNamespace(content="old", update_calls=0)
    panel.update = lambda: setattr(panel, "update_calls", panel.update_calls + 1)
    dynamic_app.ghost_tick_timer = object()
    dynamic_app.race_competitors = [object()]
    dynamic_app.session = SimpleNamespace(phase=RoundPhase.TASK, feedback=None)
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
    dynamic_app.statistics = SimpleNamespace(race_competitors=race_competitors)
    dynamic_app._start_game = start_game

    dynamic_app._configure_race(EXCEL_PRESETS[0])
    dialog: Any = calls[-1][1]
    dialog.actions[0].on_click(None)
    assert calls[-1] == ("close", dialog)

    dynamic_app._configure_race(EXCEL_PRESETS[0])
    dialog = calls[-1][1]
    dialog.actions[1].on_click(None)

    assert calls[-2] == ("close", dialog)
    assert calls[-1] == ("start", EXCEL_PRESETS[0])
