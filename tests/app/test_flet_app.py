from types import SimpleNamespace
from typing import Any

from math_game.app.flet_app import MathAdventureApp, parse_race_levels
from math_game.app.session import RoundPhase


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
