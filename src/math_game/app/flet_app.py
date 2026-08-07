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
from math_game.app.stats import RoundStatistic, StatisticsRepository
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


class MathAdventureApp:
    """Render navigation, editor, round, feedback and statistics views."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.games = GameRepository()
        self.statistics = StatisticsRepository()
        self.players = PlayerRepository()
        self.active_player: Player | None = next(iter(self.players.all()), None)
        self.view = "menu"
        self.session: RoundSession | None = None
        self.active_game: DefinedGame | None = None
        self.answer_field: ft.TextField | None = None
        self.auto_advance_timer: threading.Timer | None = None
        self.special_deadline_timer: threading.Timer | None = None
        self.round_started_at = 0.0
        self.statistic_saved = False
        self.editor_fields: dict[str, ft.TextField | ft.Dropdown] = {}
        self.editor_error = ""
        self.player_error = ""
        self.special_mode: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode | None = None
        self.special_generator: DefinedGameTaskGenerator | None = None
        self.special_task: ArithmeticTask | None = None
        self.special_feedback = ""
        page.title = "Mathe-Abenteuer"
        page.bgcolor, page.padding = BACKGROUND, 24
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
                            ft.ElevatedButton(
                                "Spielen",
                                on_click=lambda _, selected=game: self._start_game(selected),
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
        }
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
        ):
            field = ft.TextField(label=label, value=defaults[key])
            self.editor_fields[key] = field
            fields.append(field)
        mode = ft.Dropdown(
            label="Spieltyp / Modus",
            value=GameMode.TIME_ATTACK.value,
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
        for item in statistics:
            controls.append(
                ft.ListTile(
                    title=ft.Text(item.game_name, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(
                        f"{item.correct}/{item.total} richtig · {item.accuracy:.0%} · "
                        f"{item.elapsed_seconds:.1f} s · "
                        f"Vergleichsgruppe {item.definition_hash[-8:]}"
                    ),
                    trailing=ft.Text(item.played_at[:10]),
                )
            )
        return self._section(
            "📊 Statistik / Auswertung",
            "Nur Runden desselben Spielers und exakt derselben Spieldefinition "
            "werden verglichen.",
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
        controls: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        f"{self.active_game.name if self.active_game else 'Spiel'} · "
                        f"Aufgabe {session.task_number}/{session.task_count}",
                        color=MUTED,
                    ),
                    ft.Text(
                        f"Richtig: {session.correct_count}",
                        color=SUCCESS,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
            ),
            ft.ProgressBar(value=session.progress, color=PRIMARY, bgcolor="#E6EAFE"),
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

    def _finished_view(self) -> ft.Column:
        session = self._active_session()
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.Text("🏁 Runde geschafft!", size=34, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text(
                    f"{session.correct_count} von {session.task_count} Aufgaben richtig · "
                    f"{session.correct_count / session.task_count:.0%} Trefferquote",
                    size=20,
                    color=MUTED,
                ),
                self._action_button(
                    "Noch einmal spielen", lambda _: self._start_game(self.active_game)
                ),
                ft.TextButton("Zur Spieleauswahl", on_click=lambda _: self._choose_another()),
            ],
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
            )
            self.games.save(game)
            self.editor_error = ""
            self._navigate("play")
        except (ValueError, KeyError) as error:
            self.editor_error = str(error)
            self.render()

    def _delete_game(self, identifier: str) -> None:
        self.games.delete(identifier)
        self.render()

    def _start_game(self, game: DefinedGame | None) -> None:
        if game is None:
            return
        if self.active_player is None:
            self.view = "players"
            self.player_error = "Lege bitte zuerst einen Spieler an."
            self.render()
            return
        self._cancel_auto_advance()
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
        comparison_hash = DefinitionHash.from_payload(
            {"game": self.active_game.definition_hash(), "special_mode": type(mode).__name__}
        ).as_uri()
        self.statistics.add(
            RoundStatistic(
                self.active_player.id,
                self.active_game.identifier,
                f"{self.active_game.name} · {type(mode).__name__}",
                comparison_hash,
                correct,
                total,
                time.monotonic() - self.round_started_at,
            )
        )
        self.statistic_saved = True

    def _action_button(self, label: str, handler: Callable[[object], None]) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            text=label, on_click=handler, width=420, height=54, bgcolor=PRIMARY, color="white"
        )

    def _navigate(self, view: str) -> None:
        self._cancel_special_deadline()
        self.special_mode = self.special_generator = self.special_task = None
        self.session, self.active_game, self.view = None, None, view
        self.render()

    def _confirm_restart(self) -> None:
        game = self.active_game
        if game is None:
            return
        mode = self.special_mode

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
                self._start_game(game)

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
        if not feedback.is_correct and not feedback.is_task_complete:
            self.answer_field.value = ""
        self.render()

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
