# pyright: basic, reportMissingImports=false
"""Four-area Flet application for playing and maintaining defined games."""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable

import flet as ft

from math_game.app.players import Player, PlayerRepository
from math_game.app.session import RoundPhase, RoundSession
from math_game.app.stats import (
    RaceCompetitor,
    RoundStatistic,
    ScoreEvent,
    StatisticsRepository,
    computer_competitor,
)
from math_game.core.contracts import ArithmeticOperation, GameMode
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import DefinitionHash, OperandRange
from math_game.core.presets import DefinedGame, GameRepository, OperationWeights
from math_game.core.task import ArithmeticTask
from math_game.generators import DefinedGameTaskGenerator
from math_game.generators.random_source import PythonRandomSource
from math_game.modes import AccuracyMode, BlitzMode, PluMiEndlessMode, WarmUpMode
from math_game.modes.accuracy import AccuracyPhase
from math_game.modes.blitz import BlitzPhase
from math_game.modes.plumi_endless import EndlessPhase
from math_game.modes.warm_up import WarmUpPhase

BACKGROUND, INK, PRIMARY, SUCCESS = "#F4F7FF", "#17223B", "#536DFE", "#168F68"
WARNING, ERROR, CARD, MUTED = "#E67E22", "#C2415B", "#FFFFFF", "#52607A"


def parse_race_levels(raw_value: str) -> list[int]:
    """Parse one level, a range, or individually selected computer levels."""

    raw_parts = [part.strip() for part in raw_value.split(",") if part.strip()]
    if not raw_parts:
        raise ValueError("Bitte gib mindestens eine Computerstufe an.")
    levels: list[int] = []
    for part in raw_parts:
        if "-" in part:
            bounds = [value.strip() for value in part.split("-", 1)]
            start, end = (int(value) for value in bounds)
            if start > end:
                raise ValueError("Bei einem Bereich muss die kleinere Stufe zuerst stehen.")
            levels.extend(range(start, end + 1))
        else:
            levels.append(int(part))
    levels = list(dict.fromkeys(levels))
    if any(level not in range(1, 11) for level in levels):
        raise ValueError("Computerstufen müssen zwischen 1 und 10 liegen.")
    if len(levels) > 8:
        raise ValueError("Bitte wähle höchstens 8 Computergegner.")
    return levels


class MathAdventureApp:
    """Render navigation, editor, round, feedback and statistics views."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.games = GameRepository()
        self.statistics = StatisticsRepository()
        self.players = PlayerRepository()
        self.active_player: Player | None = self.players.last_used()
        self.view = "menu"
        self.session: RoundSession | None = None
        self.active_game: DefinedGame | None = None
        self.answer_field: ft.TextField | None = None
        self.auto_advance_timer: threading.Timer | None = None
        self.special_deadline_timer: threading.Timer | None = None
        self.ghost_tick_timer: threading.Timer | None = None
        self.race_live_panel: ft.Container | None = None
        self.round_started_at = 0.0
        self.statistic_saved = False
        self.editor_fields: dict[str, ft.TextField | ft.Dropdown] = {}
        self.editor_error = ""
        self.player_error = ""
        self.editor_seed: dict[str, str] | None = None
        self.live_score_events: list[ScoreEvent] = []
        self.race_competitors: list[RaceCompetitor] = []
        self.race_target_points = 0
        self.race_vehicle = "🚀"
        self.special_mode: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode | None = None
        self.special_generator: DefinedGameTaskGenerator | None = None
        self.special_task: ArithmeticTask | None = None
        self.special_feedback = ""
        page.title = "Mathe-Abenteuer"
        page.bgcolor, page.padding = BACKGROUND, 24
        # The central card can be taller than a small laptop or phone viewport.
        # Scrolling the page (rather than only selected subsections) keeps every
        # menu action and dialog entry reachable.
        page.scroll = ft.ScrollMode.AUTO
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.on_keyboard_event = self._on_keyboard
        self.render()

    def render(self) -> None:
        self._cancel_auto_advance()
        self.page.clean()
        if self.special_mode is not None:
            content = self._special_mode_view()
        elif self.session is not None and self.session.phase not in {
            RoundPhase.READY,
            RoundPhase.FINISHED,
        }:
            content = self._task_view()
        elif self.session is not None and self.session.phase is RoundPhase.FINISHED:
            self._record_statistic()
            content = self._finished_view()
        elif self.view == "play":
            content = self._play_defined_games_view()
        elif self.view == "editor":
            content = self._game_editor_view()
        elif self.view == "stats":
            content = self._stats_view()
        elif self.view == "players":
            content = self._players_view()
        else:
            content = self._main_menu_view()
        self.page.add(
            ft.Container(width=760, padding=32, bgcolor=CARD, border_radius=28, content=content)
        )
        self.page.update()
        if (
            self.answer_field is not None
            and self.session is not None
            and self.session.phase is RoundPhase.TASK
        ):
            self.answer_field.focus()
        if (
            self.race_competitors
            and self.session is not None
            and self.session.phase is RoundPhase.TASK
            and self.session.feedback is None
        ):
            self._schedule_ghost_tick()

    def _main_menu_view(self) -> ft.Column:
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Text("🧮 Mathe-Abenteuer", size=36, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text("Wähle aus, was du als Nächstes tun möchtest.", color=MUTED, size=16),
                ft.Divider(color="#E6EAFE"),
                ft.Text(
                    f"Spieler: {self.active_player.name}"
                    if self.active_player
                    else "Bitte zuerst einen Spieler anlegen.",
                    color=SUCCESS if self.active_player else WARNING,
                    weight=ft.FontWeight.BOLD,
                ),
                self._action_button(
                    "👧 Spieler auswählen / anlegen", lambda _: self._navigate("players")
                ),
                self._action_button(
                    "🎮 Definierte Spiele spielen", lambda _: self._navigate("play")
                ),
                self._action_button(
                    "⚙️ Spiele definieren (Optionen)", lambda _: self._navigate("editor")
                ),
                self._action_button("📊 Statistik / Auswertung", lambda _: self._navigate("stats")),
                self._action_button(
                    "🚪 Beenden / App schließen", lambda _: self.page.window.close()
                ),
            ],
        )

    def _play_defined_games_view(self) -> ft.Column:
        cards: list[ft.Control] = [
            ft.Text("Neue Spielmodi", size=22, weight=ft.FontWeight.BOLD),
            ft.ResponsiveRow(
                controls=[
                    self._mode_card("⚡ Blitzrunde", "45 Sekunden Vollgas", "blitz"),
                    self._mode_card("🎯 Genauigkeit", "Ohne Zeitdruck", "accuracy"),
                    self._mode_card("♾️ PluMi Endless", "Bis zum 3. Fehler", "endless"),
                    self._mode_card("🌤️ Warm-up", "60 Sekunden locker starten", "warm_up"),
                ]
            ),
            ft.Divider(),
            ft.Text("Definierte Spiele", size=22, weight=ft.FontWeight.BOLD),
        ]
        for game in self.games.all_games():
            weights = game.weights
            details = (
                f"Gewichte +{weights.addition} −{weights.subtraction} ×{weights.multiplication} "
                f"÷{weights.division} · Max. {game.max_result} · {game.task_count or '∞'} Aufgaben"
            )
            cards.append(
                ft.Container(
                    padding=16,
                    border=ft.border.all(1, "#DCE2FF"),
                    border_radius=14,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Text(game.name, size=20, weight=ft.FontWeight.BOLD),
                                    ft.Text(details, color=MUTED, size=13),
                                ],
                            ),
                            ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                controls=[
                                    ft.ElevatedButton(
                                        "Spielen",
                                        on_click=lambda _, selected=game: self._start_game(
                                            selected
                                        ),
                                    ),
                                    ft.TextButton(
                                        "🏁 Rennen starten",
                                        tooltip="Gegen Computer oder vergangene Läufe antreten",
                                        on_click=lambda _, selected=game: self._configure_race(
                                            selected
                                        ),
                                    ),
                                    ft.Row(
                                        controls=[
                                            ft.IconButton(
                                                icon=ft.Icons.CONTENT_COPY,
                                                tooltip="Als neues Spiel kopieren",
                                                on_click=lambda _, selected=game: (
                                                    self._confirm_copy_game(selected)
                                                ),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE_OUTLINE,
                                                tooltip=(
                                                    "Eigene Spieldefinition löschen"
                                                    if not game.builtin
                                                    else "Mitgelieferte Spiele sind nicht löschbar"
                                                ),
                                                disabled=game.builtin,
                                                on_click=lambda _, selected=game: (
                                                    self._confirm_delete_game(selected)
                                                ),
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )
        return self._section(
            "🎮 Definierte Spiele", "Excel-Presets und eigene Spiele direkt starten.", cards
        )

    def _mode_card(self, title: str, description: str, mode_key: str) -> ft.Container:
        return ft.Container(
            col={"sm": 12, "md": 6},
            padding=14,
            border=ft.border.all(1, "#DCE2FF"),
            border_radius=14,
            content=ft.Column(
                controls=[
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(description, color=MUTED),
                    ft.ElevatedButton(
                        "Starten", on_click=lambda _: self._start_special_mode(mode_key)
                    ),
                ]
            ),
        )

    def _game_editor_view(self) -> ft.Column:
        defaults = {
            "name": "",
            "identifier": "",
            "addition": "1",
            "subtraction": "1",
            "multiplication": "0",
            "division": "0",
            "tables": "3,4,5,6,7,8,9",
            "factor_min": "2",
            "factor_max": "10",
            "max_result": "100",
            "duration": "300",
            "task_count": "20",
            "per_task": "30",
            "target": "40",
            "wrong_penalty": "0",
            "mode": GameMode.TIME_ATTACK.value,
        }
        defaults.update(self.editor_seed or {})
        fields: list[ft.Control] = []
        for key, label in (
            ("name", "Spielname"),
            ("identifier", "Kennung"),
            ("addition", "Gewicht Addition"),
            ("subtraction", "Gewicht Subtraktion"),
            ("multiplication", "Gewicht Multiplikation"),
            ("division", "Gewicht Division"),
            ("tables", "Erlaubte Reihen (kommagetrennt)"),
            ("factor_min", "Min-Faktor"),
            ("factor_max", "Max-Faktor"),
            ("max_result", "Max. Ergebnis"),
            ("duration", "Gesamtzeit (Sekunden)"),
            ("task_count", "Aufgabenanzahl"),
            ("per_task", "Zeit je Aufgabe (Sekunden)"),
            ("target", "Richtige-Ziel"),
            ("wrong_penalty", "Punkte je Fehler (0 oder negativ, z. B. -1)"),
        ):
            field = ft.TextField(label=label, value=defaults[key])
            self.editor_fields[key] = field
            fields.append(field)
        mode = ft.Dropdown(
            label="Spieltyp / Modus",
            value=defaults["mode"],
            options=[
                ft.dropdown.Option(GameMode.TIME_ATTACK.value, "Zeitspiel"),
                ft.dropdown.Option(GameMode.TASK_SPRINT.value, "Aufgaben-Sprint"),
                ft.dropdown.Option(GameMode.PER_TASK_TIMER.value, "Zeit pro Aufgabe"),
                ft.dropdown.Option(GameMode.TARGET_HUNT.value, "Richtige-Ziel"),
                ft.dropdown.Option(GameMode.PERFECT_RUN.value, "Kein Fehler"),
            ],
        )
        self.editor_fields["mode"] = mode
        fields.append(mode)
        controls: list[ft.Control] = [
            ft.ResponsiveRow(
                controls=[ft.Container(content=f, col={"sm": 12, "md": 6}) for f in fields]
            )
        ]
        if self.editor_error:
            controls.append(ft.Text(self.editor_error, color=ERROR))
        controls.append(self._action_button("Spieldefinition speichern", self._save_game))
        custom = self.games.custom_games()
        if custom:
            controls.extend(
                [ft.Divider(), ft.Text("Eigene Spiele", size=20, weight=ft.FontWeight.BOLD)]
            )
            controls.extend(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(game.name),
                        ft.TextButton(
                            "Löschen",
                            on_click=lambda _, game_id=game.identifier: self._delete_game(game_id),
                        ),
                    ],
                )
                for game in custom
            )
        return self._section(
            "⚙️ Spiele definieren", "Alle aus Excel übernommenen Parameter in einer Maske.", controls
        )

    def _stats_view(self) -> ft.Column:
        statistics = self.statistics.load(self.active_player.id) if self.active_player else []
        controls: list[ft.Control] = []
        if not statistics:
            controls.append(
                ft.Text(
                    "Noch keine Runden gespielt. Starte dein erstes definiertes Spiel!", color=MUTED
                )
            )
        seen: set[str] = set()
        for item in statistics:
            if item.definition_hash in seen:
                continue
            seen.add(item.definition_hash)
            controls.extend(
                [
                    ft.Divider(color="#E6EAFE"),
                    ft.Text(item.game_name, size=22, weight=ft.FontWeight.BOLD, color=INK),
                    *self._dashboard_controls(item.definition_hash),
                ]
            )
        return self._section(
            "📊 Statistik / Auswertung",
            "Nur Runden desselben Spielers und exakt derselben Spieldefinition werden verglichen.",
            controls,
        )

    def _players_view(self) -> ft.Column:
        name = ft.TextField(label="Name des Kindes")
        image = ft.TextField(label="Bilddatei (optional)", hint_text="z. B. /Bilder/lina.png")
        controls: list[ft.Control] = [name, image]
        if self.player_error:
            controls.append(ft.Text(self.player_error, color=ERROR))

        def create(_: object) -> None:
            try:
                self.active_player = self.players.add(name.value or "", image.value or None)
                self.player_error = ""
                self._navigate("menu")
            except ValueError as error:
                self.player_error = str(error)
                self.render()

        controls.append(self._action_button("Spieler anlegen", create))
        for player in self.players.all():
            avatar: ft.Control = ft.CircleAvatar(content=ft.Text(player.name[:1].upper()))
            if player.image_path:
                avatar = ft.CircleAvatar(foreground_image_src=player.image_path)
            controls.append(
                ft.ListTile(
                    leading=avatar,
                    title=ft.Text(player.name, weight=ft.FontWeight.BOLD),
                    trailing=ft.ElevatedButton(
                        "Auswählen",
                        on_click=lambda _, selected=player: self._select_player(selected),
                    ),
                )
            )
        return self._section(
            "👧 Spieler",
            "Ein eigenes Profil hält Ergebnisse und Vergleiche sauber getrennt.",
            controls,
        )

    def _select_player(self, player: Player) -> None:
        self.active_player = player
        self.players.remember(player.id)
        self._navigate("menu")

    def _section(self, title: str, subtitle: str, controls: list[ft.Control]) -> ft.Column:
        return ft.Column(
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(title, size=30, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text(subtitle, color=MUTED),
                ft.TextButton("← Hauptmenü", on_click=lambda _: self._navigate("menu")),
                *controls,
            ],
        )

    def _task_view(self) -> ft.Column:
        session = self._active_session()
        task = session.current_task
        if task is None:
            raise RuntimeError("task view requires an active task")
        current_points = self.live_score_events[-1].points_after if self.live_score_events else 0
        wrong_count = len(session.results) - session.correct_count
        elapsed = max(0.0, time.monotonic() - self.round_started_at)
        timed = bool(self.active_game and self.active_game.duration_seconds)
        controls: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        f"{self.active_game.name if self.active_game else 'Spiel'} · "
                        f"Aufgabe {session.task_number}/{session.task_count}",
                        color=MUTED,
                    ),
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Text(
                                f"✓ {session.correct_count}",
                                color=SUCCESS,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(f"✕ {wrong_count}", color=ERROR, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"⭐ {current_points} P", color=PRIMARY, weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                f"{'⏳' if timed else '⏱️'} {elapsed:.0f} s",
                                color=WARNING if timed else MUTED,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                ],
            ),
            ft.ProgressBar(value=session.progress, color=PRIMARY, bgcolor="#E6EAFE"),
            *self._race_controls(),
            ft.Text(task.prompt, size=48, weight=ft.FontWeight.BOLD, color=INK),
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.TextButton("↻ Neustarten", on_click=lambda _: self._confirm_restart()),
                    ft.TextButton("⌂ Zum Menü", on_click=lambda _: self._confirm_menu()),
                ],
            ),
        ]
        feedback = session.feedback
        self.answer_field = ft.TextField(
            label="Deine Antwort",
            text_align=ft.TextAlign.CENTER,
            text_size=28,
            autofocus=True,
            disabled=bool(feedback and feedback.is_task_complete and not feedback.is_correct),
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._on_submit_clicked,
        )
        controls.append(self.answer_field)
        if feedback:
            if feedback.is_correct:
                controls.append(self._feedback("✓ Richtig! Super gelöst.", SUCCESS, "#E6F4EA"))
                self._schedule_auto_advance(0.8)
            elif not feedback.is_task_complete:
                controls.append(
                    self._feedback("⚠️ Nicht ganz. Du hast noch 1 Versuch!", WARNING, "#FEF9E7")
                )
            else:
                controls.append(
                    self._feedback(
                        f"✕ Die richtige Antwort ist {feedback.expected_answer}.", ERROR, "#FCE8E6"
                    )
                )
        if feedback and feedback.is_task_complete and not feedback.is_correct:
            controls.append(
                self._action_button("Nächste Aufgabe (Enter)", lambda _: self._next_task())
            )
        elif feedback is None or not feedback.is_task_complete:
            controls.append(self._action_button("Antwort prüfen", self._on_submit_clicked))
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=18, controls=controls
        )

    def _start_special_mode(self, mode_key: str) -> None:
        if self.active_player is None:
            self.view = "players"
            self.player_error = "Lege bitte zuerst einen Spieler an."
            self.render()
            return
        # The first-grade PluMi preset keeps the warm-up genuinely easy; the
        # regular PluMi range provides the challenge for the other variants.
        game = self.games.all_games()[4 if mode_key == "warm_up" else 3]
        self.active_game = game
        self.special_generator = DefinedGameTaskGenerator(PythonRandomSource(), game)
        now = time.monotonic()
        if mode_key == "blitz":
            controller: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode = BlitzMode(45)
            controller.start(now)
        elif mode_key == "accuracy":
            controller = AccuracyMode(20)
            controller.start()
        elif mode_key == "endless":
            controller = PluMiEndlessMode()
            controller.start()
        else:
            controller = WarmUpMode()
            controller.start(now)
        self.special_mode = controller
        self.special_feedback = ""
        self.round_started_at, self.statistic_saved = time.monotonic(), False
        self.live_score_events, self.race_competitors = [], []
        self._next_special_task()
        self.render()
        if isinstance(controller, BlitzMode | WarmUpMode):
            self.special_deadline_timer = threading.Timer(
                controller.duration_seconds, self._special_deadline_reached
            )
            self.special_deadline_timer.start()

    def _special_mode_view(self) -> ft.Column:
        mode = self.special_mode
        task = self.special_task
        if mode is None or task is None:
            raise RuntimeError("special mode requires a current task")
        finished = self._special_finished(mode)
        if finished:
            return self._special_finished_view(mode)
        if isinstance(mode, BlitzMode):
            status = (
                f"Noch {mode.seconds_left(time.monotonic()):.0f} s · {mode.correct_count} richtig"
            )
        elif isinstance(mode, AccuracyMode):
            status = f"{mode.answered_count}/{mode.task_count} · Quote {mode.accuracy:.0%}"
        elif isinstance(mode, PluMiEndlessMode):
            status = f"Highscore {mode.score} · Fehler {mode.errors}/3"
        else:
            status = f"Warm-up · {mode.correct_count}/{mode.attempted_count} richtig"
        self.answer_field = ft.TextField(
            label="Deine Antwort",
            text_align=ft.TextAlign.CENTER,
            text_size=28,
            autofocus=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._submit_special_answer,
        )
        controls: list[ft.Control] = [
            ft.Text(status, color=MUTED, size=18),
            ft.Text(task.prompt, size=48, weight=ft.FontWeight.BOLD, color=INK),
            self.answer_field,
        ]
        if self.special_feedback:
            controls.append(ft.Text(self.special_feedback, color=SUCCESS, size=18))
        controls.extend(
            [
                self._action_button("Antwort prüfen", self._submit_special_answer),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.TextButton("↻ Neustarten", on_click=lambda _: self._confirm_restart()),
                        ft.TextButton("⌂ Zum Menü", on_click=lambda _: self._confirm_menu()),
                    ],
                ),
            ]
        )
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=18, controls=controls
        )

    def _submit_special_answer(self, _: object) -> None:
        if self.answer_field is None or self.special_task is None or self.special_mode is None:
            return
        try:
            answer = int((self.answer_field.value or "").strip())
        except ValueError:
            self.answer_field.error_text = "Die Antwort muss eine ganze Zahl sein."
            self.page.update()
            return
        mode, expected, now = self.special_mode, self.special_task.expected_answer, time.monotonic()
        try:
            if isinstance(mode, BlitzMode | WarmUpMode):
                correct = mode.submit(answer, expected, now)
            else:
                correct = mode.submit(answer, expected)
        except RuntimeError:
            self.render()
            return
        self.special_feedback = "✓ Richtig!" if correct else f"✕ Richtig wäre {expected}."
        self._append_score_event(correct)
        if not self._special_finished(mode):
            self._next_special_task()
        self.render()

    def _special_finished(
        self, mode: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode
    ) -> bool:
        now = time.monotonic()
        if isinstance(mode, BlitzMode):
            mode.tick(now)
            return mode.phase is BlitzPhase.FINISHED
        if isinstance(mode, WarmUpMode):
            mode.tick(now)
            return mode.phase is WarmUpPhase.MAIN_GAME_READY
        if isinstance(mode, AccuracyMode):
            return mode.phase is AccuracyPhase.FINISHED
        return mode.phase is EndlessPhase.FINISHED

    def _special_finished_view(
        self, mode: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode
    ) -> ft.Column:
        self._record_special_statistic(mode)
        if isinstance(mode, BlitzMode):
            result = (
                f"{mode.correct_count} richtige Antworten · Session-Bestenliste {mode.leaderboard}"
            )
        elif isinstance(mode, AccuracyMode):
            result = f"Trefferquote {mode.accuracy:.0%} ({mode.correct_count}/{mode.task_count})"
        elif isinstance(mode, PluMiEndlessMode):
            result = f"Highscore {mode.score} · beste Serie {mode.best_streak}"
        else:
            result = f"Warm-up geschafft: {mode.correct_count} richtige Antworten"
        action_label = "Hauptspiel starten" if isinstance(mode, WarmUpMode) else "Zur Spieleauswahl"
        action = (
            self._start_main_game_after_warm_up
            if isinstance(mode, WarmUpMode)
            else self._leave_special_mode
        )
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=18,
            controls=[
                ft.Text("🏁 Modus beendet", size=34, weight=ft.FontWeight.BOLD),
                ft.Text(result, size=20, color=MUTED),
                *self._dashboard_controls(
                    self._special_comparison_hash(mode), highlight_latest=True
                ),
                self._action_button(action_label, lambda _: action()),
            ],
        )

    def _next_special_task(self) -> None:
        if self.special_generator is None:
            raise RuntimeError("special generator is not configured")
        definition = OperationDefinition(
            operation=ArithmeticOperation.ADDITION,
            left=OperandRange(1, 20),
            right=OperandRange(1, 20),
        )
        self.special_task = self.special_generator.generate(definition)

    def _leave_special_mode(self) -> None:
        self._cancel_special_deadline()
        self.special_mode = self.special_generator = self.special_task = None
        self.answer_field = None
        self.view = "play"
        self.render()

    def _start_main_game_after_warm_up(self) -> None:
        self._cancel_special_deadline()
        game = self.active_game
        self.special_mode = self.special_generator = self.special_task = None
        self._start_game(game)

    def _special_deadline_reached(self) -> None:
        if self.special_mode is not None:
            self._special_finished(self.special_mode)
            self.render()

    def _cancel_special_deadline(self) -> None:
        if self.special_deadline_timer is not None:
            self.special_deadline_timer.cancel()
            self.special_deadline_timer = None

    def _feedback(self, text: str, color: str, background: str) -> ft.Container:
        return ft.Container(
            padding=12,
            bgcolor=background,
            border_radius=12,
            content=ft.Text(text, size=18, color=color, weight=ft.FontWeight.BOLD),
        )

    def _race_controls(self) -> list[ft.Control]:
        if not self.race_competitors:
            self.race_live_panel = None
            return []
        self.race_live_panel = self._build_race_panel()
        return [self.race_live_panel]

    def _build_race_panel(self) -> ft.Container:
        """Build only the moving race area, independently of the answer form."""

        elapsed = max(0.0, time.monotonic() - self.round_started_at)
        own_points = self.live_score_events[-1].points_after if self.live_score_events else 0
        racers: list[tuple[str, str, int, str]] = [
            ("Du", self.race_vehicle, own_points, "Dein aktueller Lauf")
        ]
        opponent_vehicles = ("🏎️", "🚀", "🛸", "🚲", "🐉", "🛶", "🐆", "🦄")
        for index, competitor in enumerate(self.race_competitors):
            events = competitor.statistic.events
            past = [event for event in events if event.elapsed_seconds <= elapsed]
            points = past[-1].points_after if past else 0
            next_event = next((event for event in events if event.elapsed_seconds > elapsed), None)
            if next_event is None:
                detail = "im Ziel"
            else:
                action = "+ Punkt" if next_event.correct else "Fehler"
                detail = f"{action} bei {next_event.elapsed_seconds:.1f} s"
            racers.append(
                (
                    competitor.player_name,
                    opponent_vehicles[index % len(opponent_vehicles)],
                    points,
                    detail,
                )
            )
        ordered = sorted(racers, key=lambda racer: racer[2], reverse=True)
        own_rank = next(index for index, racer in enumerate(ordered, start=1) if racer[0] == "Du")
        leading_points = ordered[0][2]
        tracks = [
            self._race_track(
                name,
                vehicle,
                points,
                f"{detail} · {leading_points - points} P Rückstand"
                if points < leading_points
                else f"{detail} · in Führung",
                name == "Du",
            )
            for name, vehicle, points, detail in racers
        ]
        return ft.Container(
            padding=16,
            bgcolor="#F3F0FF",
            border_radius=18,
            border=ft.border.all(2, "#B8A7FF"),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("🏁 LIVE-RENNEN", size=19, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"Platz {own_rank}/{len(racers)} · "
                                f"Ziel {self.race_target_points} P",
                                color=PRIMARY,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    ft.Text("Jeder richtige Treffer bringt dich sichtbar nach vorn.", color=MUTED),
                    *tracks,
                ],
            ),
        )

    def _race_track(
        self, name: str, vehicle: str, points: int, detail: str, is_player: bool
    ) -> ft.Control:
        target = max(1, self.race_target_points)
        progress = min(1.0, max(0.0, points / target))
        track_width = 470
        vehicle_left = round(progress * (track_width - 35))
        return ft.Container(
            padding=8,
            bgcolor="#FFFFFF" if is_player else "#FAFAFF",
            border_radius=12,
            border=ft.border.all(2 if is_player else 1, PRIMARY if is_player else "#DDD8F5"),
            content=ft.Column(
                spacing=3,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(name, expand=True, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{points} P · {detail}", size=11, color=MUTED),
                        ]
                    ),
                    ft.Stack(
                        width=track_width,
                        height=34,
                        controls=[
                            ft.Container(
                                top=15,
                                width=track_width,
                                height=5,
                                bgcolor="#DED9F8",
                                border_radius=4,
                            ),
                            ft.Text("🏁", right=0, top=2, size=24),
                            ft.Container(
                                left=vehicle_left, top=0, content=ft.Text(vehicle, size=27)
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _finished_view(self) -> ft.Column:
        session = self._active_session()
        game = self.active_game
        if game is None:
            raise RuntimeError("finished view requires an active game")
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.Text("🏆 Deine Auswertung", size=34, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text(
                    f"{session.correct_count} von {session.task_count} Aufgaben richtig · "
                    f"{session.correct_count / session.task_count:.0%} Trefferquote",
                    size=20,
                    color=MUTED,
                ),
                *self._race_controls(),
                *self._dashboard_controls(game.definition_hash(), highlight_latest=True),
                self._action_button(
                    "Rennen noch einmal" if self.race_competitors else "Noch einmal spielen",
                    lambda _: self._start_game(
                        game,
                        competitors=list(self.race_competitors),
                        target_points=self.race_target_points,
                        race_vehicle=self.race_vehicle,
                    ),
                ),
                ft.TextButton("Zur Spieleauswahl", on_click=lambda _: self._choose_another()),
            ],
        )

    def _dashboard_controls(
        self, definition_hash: str, *, highlight_latest: bool = False
    ) -> list[ft.Control]:
        """Build the reusable result dashboard for one strictly comparable game."""

        player = self.active_player
        if player is None:
            return []
        summary = self.statistics.summary(player.id, definition_hash)
        if summary is None:
            return []
        latest = summary.rounds[0]
        trend_icon = (
            "↗" if summary.accuracy_trend > 0 else "↘" if summary.accuracy_trend < 0 else "→"
        )
        trend_color = SUCCESS if summary.accuracy_trend >= 0 else WARNING
        metric_cards = ft.ResponsiveRow(
            controls=[
                self._metric_card("⭐", "Score", f"{latest.score}", "Punkte dieser Runde"),
                self._metric_card(
                    "🎯", "Beste Quote", f"{summary.best_accuracy:.0%}", "Persönlicher Rekord"
                ),
                self._metric_card(
                    "⏱️", "Ø Zeit", f"{summary.average_seconds:.1f} s", "Alle gleichen Spiele"
                ),
                self._metric_card(
                    trend_icon,
                    "Entwicklung",
                    f"{summary.accuracy_trend:+.0%}",
                    f"über {len(summary.rounds)} Runden",
                    trend_color,
                ),
            ]
        )
        leaderboard = self.statistics.leaderboard(definition_hash)
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        leaderboard_rows: list[ft.Control] = []
        for entry in leaderboard:
            is_active = entry.player_name.casefold() == player.name.casefold()
            leaderboard_rows.append(
                ft.Container(
                    padding=10,
                    bgcolor="#EEF1FF" if is_active else CARD,
                    border_radius=10,
                    content=ft.Row(
                        controls=[
                            ft.Text(medals.get(entry.rank, f"#{entry.rank}"), width=38, size=18),
                            ft.Text(entry.player_name, expand=True, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{entry.accuracy:.0%}", color=MUTED),
                            ft.Text(f"{entry.score} P", color=PRIMARY, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                )
            )
        history_rows: list[ft.Control] = []
        for index, item in enumerate(summary.rounds[:8]):
            label = "Gerade eben" if index == 0 and highlight_latest else item.played_at[:10]
            history_rows.append(
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(label, width=100, color=MUTED, size=12),
                                ft.Text(
                                    f"{item.accuracy:.0%}",
                                    width=48,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"{item.score} Punkte",
                                    expand=True,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                            ]
                        ),
                        ft.ProgressBar(value=item.accuracy, color=SUCCESS, bgcolor="#E6EAFE"),
                    ],
                )
            )
        details = ft.ExpansionTile(
            title=ft.Text("Mehr Details anzeigen", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text("Verlauf, Bestenliste und genaue Vergleichsbasis"),
            controls=[
                ft.Container(
                    padding=12,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Text("📈 Dein Verlauf", size=19, weight=ft.FontWeight.BOLD),
                            *history_rows,
                            ft.Divider(),
                            ft.Text("🏅 Bestenliste", size=19, weight=ft.FontWeight.BOLD),
                            *leaderboard_rows,
                            ft.Text(
                                f"Vergleichsschlüssel: …{definition_hash[-12:]}. "
                                "Nur exakt gleiche Regeln zählen in diese Auswertung.",
                                size=11,
                                color=MUTED,
                            ),
                        ],
                    ),
                )
            ],
        )
        return [
            ft.Container(
                padding=18,
                bgcolor="#F8F9FF",
                border=ft.border.all(1, "#DCE2FF"),
                border_radius=18,
                content=ft.Column(controls=[metric_cards, details]),
            )
        ]

    def _metric_card(
        self, icon: str, label: str, value: str, caption: str, color: str = PRIMARY
    ) -> ft.Container:
        return ft.Container(
            col={"sm": 6, "md": 3},
            padding=12,
            bgcolor=CARD,
            border_radius=14,
            content=ft.Column(
                spacing=3,
                controls=[
                    ft.Text(icon, size=22),
                    ft.Text(label, size=12, color=MUTED),
                    ft.Text(value, size=24, color=color, weight=ft.FontWeight.BOLD),
                    ft.Text(caption, size=10, color=MUTED),
                ],
            ),
        )

    def _save_game(self, _: object) -> None:
        try:
            value = lambda key: self.editor_fields[key].value or ""  # noqa: E731
            game = DefinedGame(
                identifier=value("identifier").strip(),
                name=value("name").strip(),
                weights=OperationWeights(
                    *(
                        int(value(key))
                        for key in ("addition", "subtraction", "multiplication", "division")
                    )
                ),
                allowed_tables=tuple(
                    int(item.strip()) for item in value("tables").split(",") if item.strip()
                ),
                factor_min=int(value("factor_min")),
                factor_max=int(value("factor_max")),
                max_result=int(value("max_result")),
                mode=GameMode(value("mode")),
                duration_seconds=int(value("duration")),
                task_count=int(value("task_count")),
                per_task_seconds=int(value("per_task")),
                correct_target=int(value("target")),
                wrong_answer_penalty=int(value("wrong_penalty")),
            )
            self.games.save(game)
            self.editor_error = ""
            self.editor_seed = None
            self._navigate("play")
        except (ValueError, KeyError) as error:
            self.editor_error = str(error)
            self.render()

    def _delete_game(self, identifier: str) -> None:
        self.games.delete(identifier)
        self.render()

    def _confirm_delete_game(self, game: DefinedGame) -> None:
        if game.builtin:
            return
        self._show_confirmation(
            "Spiel wirklich löschen?",
            f"„{game.name}“ wird dauerhaft aus deinen eigenen Spielen entfernt.",
            lambda: self._delete_game(game.identifier),
        )

    def _confirm_copy_game(self, game: DefinedGame) -> None:
        def copy_to_editor() -> None:
            existing_ids = {existing.identifier for existing in self.games.all_games()}
            base_identifier = f"{game.identifier}-kopie"
            copied_identifier = base_identifier
            copy_number = 2
            while copied_identifier in existing_ids:
                copied_identifier = f"{base_identifier}-{copy_number}"
                copy_number += 1
            self.editor_seed = {
                "name": f"{game.name} – Kopie",
                "identifier": copied_identifier,
                "addition": str(game.weights.addition),
                "subtraction": str(game.weights.subtraction),
                "multiplication": str(game.weights.multiplication),
                "division": str(game.weights.division),
                "tables": ",".join(str(table) for table in game.allowed_tables),
                "factor_min": str(game.factor_min),
                "factor_max": str(game.factor_max),
                "max_result": str(game.max_result),
                "duration": str(game.duration_seconds or 300),
                "task_count": str(game.task_count or 20),
                "per_task": str(game.per_task_seconds or 30),
                "target": str(game.correct_target or 40),
                "wrong_penalty": str(game.wrong_answer_penalty),
                "mode": game.mode.value,
            }
            self.view = "editor"
            self.render()

        self._show_confirmation(
            "Spiel als Vorlage verwenden?",
            f"Alle Regeln von „{game.name}“ werden in ein neues Spiel kopiert. "
            "Das Original bleibt unverändert.",
            copy_to_editor,
        )

    def _configure_race(self, game: DefinedGame) -> None:
        recorded = self.statistics.race_competitors(game.definition_hash(), 8)
        own_summary = (
            self.statistics.summary(self.active_player.id, game.definition_hash())
            if self.active_player
            else None
        )
        personal_best = (
            self.statistics.best_round(self.active_player.id, game.definition_hash())
            if self.active_player
            else None
        )
        if personal_best is not None and not personal_best.events:
            personal_best = None
        source = ft.Dropdown(
            label="Gegnertyp",
            value="computer_static",
            options=[
                ft.dropdown.Option("computer_static", "Computer · statische Stärke"),
                *(
                    [ft.dropdown.Option("computer_history", "Computer · an meinem Ø orientiert")]
                    if own_summary
                    else []
                ),
                *(
                    [ft.dropdown.Option("recorded", "Aufgezeichnete echte Läufe")]
                    if recorded
                    else []
                ),
            ],
        )
        levels = ft.TextField(
            label="Computerstufen",
            value="3-5",
            hint_text="z. B. 3-6 oder 1,5,9",
            helper_text="Bereich oder einzelne Stufen; jede angegebene Stufe ist ein Läufer.",
        )
        opponent_count = ft.Dropdown(
            label="Anzahl bei ‚aufgezeichnete Läufe‘",
            value="3",
            options=[ft.dropdown.Option(str(count), str(count)) for count in range(1, 6)],
        )
        variable = ft.Switch(
            label="Unregelmäßig spielen (mit richtigen und falschen Antworten)", value=True
        )
        include_personal_best = ft.Switch(
            label="Meinen persönlichen Rekord als zusätzlichen Läufer aufnehmen",
            value=False,
            disabled=personal_best is None,
        )
        target = ft.TextField(
            label="Festes Ergebnisziel",
            value=str(game.correct_target or min(game.task_count or 20, 40)),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        vehicle = ft.Dropdown(
            label="Dein Rennfahrzeug",
            value="🚀",
            options=[
                ft.dropdown.Option(icon, f"{icon} {name}")
                for icon, name in (
                    ("🚀", "Rakete"),
                    ("🏎️", "Rennauto"),
                    ("🛸", "UFO"),
                    ("🐉", "Drache"),
                    ("🦄", "Einhorn"),
                )
            ],
        )
        error_text = ft.Text("", color=ERROR)
        history_note = ft.Text(
            "✓ Persönliche Historie verfügbar: Stufe 5 liegt etwas unter deinem Durchschnitt."
            if own_summary
            else (
                "🔒 Der persönliche Durchschnitt wird nach der ersten Runde dieses Spiels "
                "freigeschaltet."
            ),
            color=SUCCESS if own_summary else MUTED,
            size=12,
        )
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("🏁 Rennen gegen Computergegner"),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Text(
                            "Stufen 1–10 entsprechen ungefähr P10 bis P90 einer erreichbaren "
                            "Leistungsverteilung. Auch starke Gegner machen Fehler und wechseln "
                            "ihr Tempo.",
                            color=MUTED,
                        ),
                        source,
                        history_note,
                        ft.Text("Schwierigkeit und Läuferfeld", weight=ft.FontWeight.BOLD),
                        levels,
                        opponent_count,
                        include_personal_best,
                        variable,
                        target,
                        vehicle,
                        error_text,
                    ],
                ),
            ),
        )

        def close(_: object) -> None:
            dialog.open = False
            self.page.update()

        def start(_: object) -> None:
            try:
                count = int(opponent_count.value or "3")
                target_points = int(target.value or "0")
                if target_points <= 0:
                    raise ValueError("Das Rennziel muss mindestens 1 Punkt sein.")
                selected_source = source.value or "computer_static"
                if selected_source == "recorded":
                    competitors = recorded[:count]
                else:
                    selected_levels = parse_race_levels(levels.value or "")
                    if selected_source == "computer_history" and own_summary is None:
                        raise ValueError("Für diesen Gegner fehlt noch eine eigene Runde.")
                    baseline = (
                        sum(item.score for item in own_summary.rounds) / len(own_summary.rounds)
                        if selected_source == "computer_history" and own_summary
                        else None
                    )
                    duration = float(game.duration_seconds or max(30, (game.task_count or 20) * 3))
                    competitors = [
                        computer_competitor(
                            game.definition_hash(),
                            level=computer_level,
                            target_points=target_points,
                            duration_seconds=duration,
                            baseline_points=baseline,
                            seed=index + target_points,
                            variable=bool(variable.value),
                        )
                        for index, computer_level in enumerate(selected_levels)
                    ]
                    if include_personal_best.value and personal_best is not None:
                        competitors.insert(
                            0, RaceCompetitor("Dein persönlicher Rekord", personal_best)
                        )
                if not competitors:
                    raise ValueError("Keine aufgezeichneten Gegner verfügbar.")
            except ValueError as error:
                error_text.value = str(error) or "Bitte prüfe die Eingaben."
                self.page.update()
                return
            dialog.open = False
            self._start_game(
                game,
                competitors=competitors,
                target_points=target_points,
                race_vehicle=vehicle.value or "🚀",
            )

        dialog.actions = [
            ft.TextButton("Abbrechen", on_click=close),
            ft.ElevatedButton("Rennen starten", on_click=start),
        ]
        self.page.open(dialog)

    def _start_game(
        self,
        game: DefinedGame | None,
        *,
        competitors: list[RaceCompetitor] | None = None,
        target_points: int = 0,
        race_vehicle: str = "🚀",
    ) -> None:
        if game is None:
            return
        if self.active_player is None:
            self.view = "players"
            self.player_error = "Lege bitte zuerst einen Spieler an."
            self.render()
            return
        self._cancel_auto_advance()
        self._cancel_ghost_tick()
        definition = OperationDefinition(
            operation=ArithmeticOperation.ADDITION,
            left=OperandRange(game.factor_min, game.max_result),
            right=OperandRange(game.factor_min, game.max_result),
        )
        count = game.task_count or game.correct_target or 20
        self.session = RoundSession(
            generator=DefinedGameTaskGenerator(PythonRandomSource(), game),
            definition=definition,
            task_count=count,
            max_attempts_per_task=2,
        )
        self.active_game, self.round_started_at, self.statistic_saved = (
            game,
            time.monotonic(),
            False,
        )
        self.live_score_events = []
        self.race_competitors = list(competitors or [])
        self.race_target_points = target_points
        self.race_vehicle = race_vehicle
        self.session.start()
        self.render()

    def _record_statistic(self) -> None:
        if self.statistic_saved or self.active_game is None or self.active_player is None:
            return
        session = self._active_session()
        self.statistics.add(
            RoundStatistic(
                self.active_player.id,
                self.active_game.identifier,
                self.active_game.name,
                self.active_game.definition_hash(),
                session.correct_count,
                session.task_count,
                time.monotonic() - self.round_started_at,
                events=tuple(self.live_score_events),
                score_value=(
                    self.live_score_events[-1].points_after if self.live_score_events else 0
                ),
            )
        )
        self.statistic_saved = True

    def _record_special_statistic(
        self, mode: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode
    ) -> None:
        if self.statistic_saved or self.active_game is None or self.active_player is None:
            return
        if isinstance(mode, AccuracyMode):
            correct, total = mode.correct_count, mode.answered_count
        elif isinstance(mode, PluMiEndlessMode):
            correct, total = mode.score, mode.score + mode.errors
        elif isinstance(mode, BlitzMode):
            correct, total = mode.correct_count, mode.correct_count + mode.wrong_count
        else:
            correct, total = mode.correct_count, mode.attempted_count
        if total <= 0:
            return
        comparison_hash = self._special_comparison_hash(mode)
        self.statistics.add(
            RoundStatistic(
                self.active_player.id,
                self.active_game.identifier,
                f"{self.active_game.name} · {type(mode).__name__}",
                comparison_hash,
                correct,
                total,
                time.monotonic() - self.round_started_at,
                events=tuple(self.live_score_events),
                score_value=(
                    self.live_score_events[-1].points_after if self.live_score_events else 0
                ),
            )
        )
        self.statistic_saved = True

    def _special_comparison_hash(
        self, mode: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode
    ) -> str:
        if self.active_game is None:
            raise RuntimeError("special comparison requires an active game")
        return DefinitionHash.from_payload(
            {"game": self.active_game.definition_hash(), "special_mode": type(mode).__name__}
        ).as_uri()

    def _action_button(self, label: str, handler: Callable[[object], None]) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            text=label, on_click=handler, width=420, height=54, bgcolor=PRIMARY, color="white"
        )

    def _navigate(self, view: str) -> None:
        self._cancel_special_deadline()
        self._cancel_ghost_tick()
        self.special_mode = self.special_generator = self.special_task = None
        self.session, self.active_game, self.view = None, None, view
        self.render()

    def _confirm_restart(self) -> None:
        game = self.active_game
        if game is None:
            return
        mode = self.special_mode
        competitors = list(self.race_competitors)
        target_points = self.race_target_points
        race_vehicle = self.race_vehicle

        def restart() -> None:
            if isinstance(mode, BlitzMode):
                self._start_special_mode("blitz")
            elif isinstance(mode, AccuracyMode):
                self._start_special_mode("accuracy")
            elif isinstance(mode, PluMiEndlessMode):
                self._start_special_mode("endless")
            elif isinstance(mode, WarmUpMode):
                self._start_special_mode("warm_up")
            else:
                self._start_game(
                    game,
                    competitors=competitors,
                    target_points=target_points,
                    race_vehicle=race_vehicle,
                )

        self._show_confirmation(
            "Spiel neu starten?",
            "Der aktuelle Fortschritt geht verloren. Möchtest du wirklich neu beginnen?",
            restart,
        )

    def _confirm_menu(self) -> None:
        self._show_confirmation(
            "Zurück zum Menü?",
            "Der aktuelle Fortschritt geht verloren. Möchtest du das Spiel verlassen?",
            lambda: self._navigate("menu"),
        )

    def _show_confirmation(self, title: str, message: str, action: Callable[[], None]) -> None:
        dialog = ft.AlertDialog(modal=True, title=ft.Text(title), content=ft.Text(message))

        def close(_: object) -> None:
            dialog.open = False
            self.page.update()

        def confirm(_: object) -> None:
            dialog.open = False
            action()

        dialog.actions = [
            ft.TextButton("Abbrechen", on_click=close),
            ft.ElevatedButton("Ja, fortfahren", on_click=confirm),
        ]
        self.page.open(dialog)

    def _choose_another(self) -> None:
        self.session, self.active_game, self.view = None, None, "play"
        self.render()

    def _on_submit_clicked(self, _: object) -> None:
        if self.answer_field is None:
            return
        try:
            feedback = self._active_session().submit_answer(self.answer_field.value or "")
        except ValueError as error:
            self.answer_field.error_text = str(error)
            self.page.update()
            return
        self._append_score_event(feedback.is_correct)
        if not feedback.is_correct and not feedback.is_task_complete:
            self.answer_field.value = ""
        self.render()

    def _append_score_event(self, correct: bool) -> None:
        game = self.active_game
        if game is None:
            return
        previous = self.live_score_events[-1].points_after if self.live_score_events else 0
        points = previous + (1 if correct else game.wrong_answer_penalty)
        self.live_score_events.append(
            ScoreEvent(
                elapsed_seconds=max(0.0, time.monotonic() - self.round_started_at),
                correct=correct,
                points_after=points,
            )
        )

    def _next_task(self) -> None:
        self._cancel_auto_advance()
        self._active_session().advance_to_next_task()
        self.render()

    def _schedule_auto_advance(self, seconds: float) -> None:
        self._cancel_auto_advance()
        self.auto_advance_timer = threading.Timer(seconds, self._next_task)
        self.auto_advance_timer.start()

    def _cancel_auto_advance(self) -> None:
        if self.auto_advance_timer:
            self.auto_advance_timer.cancel()
            self.auto_advance_timer = None

    def _schedule_ghost_tick(self) -> None:
        self._cancel_ghost_tick()
        self.ghost_tick_timer = threading.Timer(0.5, self._ghost_tick)
        self.ghost_tick_timer.start()

    def _ghost_tick(self) -> None:
        self.ghost_tick_timer = None
        if (
            self.race_competitors
            and self.session is not None
            and self.session.phase is RoundPhase.TASK
            and self.session.feedback is None
            and self.race_live_panel is not None
        ):
            # Updating the whole page here recreated the TextField every 500 ms and
            # erased an answer while it was being typed.  Replace only the contents
            # of the live race panel; task, focus and input value remain untouched.
            refreshed = self._build_race_panel()
            self.race_live_panel.content = refreshed.content
            self.race_live_panel.update()
            self._schedule_ghost_tick()

    def _cancel_ghost_tick(self) -> None:
        if self.ghost_tick_timer is not None:
            self.ghost_tick_timer.cancel()
            self.ghost_tick_timer = None

    def _on_keyboard(self, event: ft.KeyboardEvent) -> None:
        if (
            event.key == "Enter"
            and self.session
            and self.session.feedback
            and self.session.feedback.is_task_complete
        ):
            self._next_task()

    def _active_session(self) -> RoundSession:
        if self.session is None:
            raise RuntimeError("no active round")
        return self.session


def main(page: ft.Page) -> None:
    MathAdventureApp(page)


def run() -> None:
    use_web = "--web" in sys.argv or os.getenv("FLET_VIEW") in {"web", "1", "true"}
    ft.app(target=main, view=ft.AppView.WEB_BROWSER if use_web else ft.AppView.FLET_APP)


if __name__ == "__main__":
    run()
