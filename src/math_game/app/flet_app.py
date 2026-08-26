# pyright: basic, reportMissingImports=false
"""Four-area Flet application for playing and maintaining defined games."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import asdict, dataclass
from pathlib import Path

import flet as ft

from math_game.app.database import AppDatabase
from math_game.app.players import Player, PlayerRepository
from math_game.app.session import RoundPhase, RoundSession
from math_game.app.stats import (
    RaceCompetitor,
    RoundStatistic,
    ScoreEvent,
    StatisticsRepository,
    computer_competitor,
)
from math_game.core.contracts import ArithmeticOperation, EndReason, GameMode
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import DefinitionHash, OperandRange
from math_game.core.presets import DefinedGame, GameRepository, OperationWeights
from math_game.core.race import (
    RaceConfig,
    RaceEvent,
    RaceEventKind,
    RaceKind,
    RacerStatus,
    RaceStanding,
    RaceState,
    apply_race_event,
    race_config_for_game,
)
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


@dataclass(frozen=True, slots=True)
class LayoutMetrics:
    """Dimensions shared by all responsive views."""

    content_width: float
    padding: float
    track_width: float
    compact: bool


def layout_metrics(page_width: float | None) -> LayoutMetrics:
    """Calculate overflow-safe dimensions for phone, tablet and desktop."""

    width = max(280.0, page_width or 760.0)
    padding = 12.0 if width < 400 else 20.0 if width < 700 else 32.0
    content_width = min(760.0, width - (8.0 if width < 700 else 32.0))
    return LayoutMetrics(
        content_width,
        padding,
        max(220.0, content_width - 2 * padding - 20),
        width < 480,
    )


def normalize_integer_input(value: str, *, allow_negative: bool = True) -> str:
    """Keep only an optional leading minus and decimal digits."""

    stripped = value.strip()
    sign = "-" if allow_negative and stripped.startswith("-") else ""
    return sign + re.sub(r"\D", "", stripped)


@dataclass(frozen=True, slots=True)
class RaceController:
    """All UI state belonging to one concretely configured race."""

    config: RaceConfig
    competitors: tuple[RaceCompetitor, ...]
    vehicle: str
    comparison_hash: str


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
        self.ghost_tick_task: Future[None] | None = None
        self.ghost_tick_generation = 0
        self.race_live_panel: ft.Container | None = None
        self.dialog_open = False
        self.dialog_paused_at = 0.0
        self.task_number_text: ft.Text | None = None
        self.task_score_text: ft.Text | None = None
        self.task_progress: ft.ProgressBar | None = None
        self.task_prompt: ft.Text | None = None
        self.task_feedback: ft.Container | None = None
        self.task_action: ft.ElevatedButton | None = None
        self.root_container: ft.Container | None = None
        self.pending_overlay_controls: list[ft.Control] = []
        self.round_started_at = 0.0
        self.statistic_saved = False
        self.editor_fields: dict[str, ft.TextField | ft.Dropdown] = {}
        self.editor_error = ""
        self.player_error = ""
        self.editor_seed: dict[str, str] | None = None
        self.live_score_events: list[ScoreEvent] = []
        self.race_state: RaceController | None = None
        self.special_mode: AccuracyMode | BlitzMode | PluMiEndlessMode | WarmUpMode | None = None
        self.special_generator: DefinedGameTaskGenerator | None = None
        self.special_task: ArithmeticTask | None = None
        self.special_feedback = ""
        self.submission_in_progress = False
        self.paused = False
        page.title = "Mathe-Abenteuer"
        page.bgcolor, page.padding = BACKGROUND, 24
        # The central card can be taller than a small laptop or phone viewport.
        # Scrolling the page (rather than only selected subsections) keeps every
        # menu action and dialog entry reachable.
        page.scroll = ft.ScrollMode.AUTO
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.on_keyboard_event = self._on_keyboard
        page.on_resized = self._on_resize
        page.on_view_pop = self._on_android_back
        if hasattr(page, "on_app_lifecycle_state_change"):
            page.on_app_lifecycle_state_change = self._on_lifecycle_change
        self.render()

    def render(self) -> None:
        self._cancel_auto_advance()
        # A render can be the transition to the result screen.  Cancel the old
        # recurring race callback first; a live task schedules exactly one new
        # callback below, while a finished round deliberately schedules none.
        self._cancel_ghost_tick()
        self.pending_overlay_controls = []
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
        metrics = layout_metrics(getattr(self.page, "width", None))
        root_container = ft.Container(
            width=metrics.content_width,
            padding=metrics.padding,
            bgcolor=CARD,
            border_radius=18 if metrics.compact else 28,
            content=content,
        )
        # Build the complete replacement before clearing the current page. If
        # constructing a view fails, the last usable menu remains visible.
        self.page.clean()
        # Some views need non-visual controls such as FilePicker in the page
        # overlay. Attach them only after clean(): adding them while the old
        # page is still mounted would make clean() immediately detach them.
        self.page.overlay.extend(self.pending_overlay_controls)
        self.root_container = root_container
        self.page.add(root_container)
        self.page.update()
        if (
            self.answer_field is not None
            and self.session is not None
            and self.session.phase is RoundPhase.TASK
        ):
            self.answer_field.focus()
        if (
            not self.dialog_open
            and self.race_state is not None
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
        image = ft.TextField(label="Profilbild (optional)", read_only=True, expand=True)

        def selected(event: ft.FilePickerResultEvent) -> None:
            if not event.files or not event.files[0].path:
                return
            source = event.files[0].path
            target_dir = AppDatabase().path.parent / "profile_images"
            target_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(source).suffix.lower() or ".img"
            target = target_dir / f"profile-{time.time_ns()}{suffix}"
            shutil.copy2(source, target)
            image.value = str(target)
            image.update()

        picker = ft.FilePicker(on_result=selected)
        # render() must first clean the previous page and only then attach this
        # non-visual control. Otherwise Flet removes the freshly created picker
        # during the same navigation event and can abort the player view update.
        self.pending_overlay_controls.append(picker)
        icon = ft.Dropdown(
            label="Spielericon",
            value="🙂",
            options=[
                ft.dropdown.Option(value, f"{value} {label}")
                for value, label in (
                    ("🙂", "Fröhlich"),
                    ("😎", "Cool"),
                    ("🤓", "Schlau"),
                    ("🧒", "Kind"),
                    ("👧", "Mädchen"),
                    ("👦", "Junge"),
                    ("🦊", "Fuchs"),
                    ("🐼", "Panda"),
                    ("🐯", "Tiger"),
                    ("🦁", "Löwe"),
                    ("🐸", "Frosch"),
                    ("🦄", "Einhorn"),
                    ("🐲", "Drache"),
                    ("🧙", "Zauberer"),
                    ("🥷", "Ninja"),
                    ("🦸", "Superheld"),
                    ("👩‍🚀", "Astronautin"),
                    ("👨‍🚀", "Astronaut"),
                )
            ],
        )
        controls: list[ft.Control] = [
            name,
            icon,
            ft.Row(
                wrap=True,
                controls=[
                    image,
                    ft.OutlinedButton(
                        "Bild auswählen",
                        height=48,
                        on_click=lambda _: picker.pick_files(
                            allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE
                        ),
                    ),
                ],
            ),
        ]
        if self.player_error:
            controls.append(ft.Text(self.player_error, color=ERROR))

        def create(_: object) -> None:
            try:
                self.active_player = self.players.add(
                    name.value or "", image.value or None, icon.value or "🙂"
                )
                self.player_error = ""
                self._navigate("menu")
            except ValueError as error:
                self.player_error = str(error)
                self.render()

        controls.append(self._action_button("Spieler anlegen", create))
        for player in self.players.all():
            avatar: ft.Control = ft.CircleAvatar(content=ft.Text(player.icon, size=22))
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
        self.task_number_text = ft.Text(
            f"{self.active_game.name if self.active_game else 'Spiel'} · "
            f"Aufgabe {session.task_number}/{session.task_count}",
            color=MUTED,
        )
        self.task_score_text = ft.Text(
            f"✓ {session.correct_count}   ✕ {wrong_count}   ⭐ {current_points} P   "
            f"{'⏳' if timed else '⏱️'} {elapsed:.0f} s",
            color=PRIMARY,
            weight=ft.FontWeight.BOLD,
        )
        self.task_progress = ft.ProgressBar(
            value=session.progress, color=PRIMARY, bgcolor="#E6EAFE"
        )
        self.task_prompt = ft.Text(task.prompt, size=48, weight=ft.FontWeight.BOLD, color=INK)
        controls: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    self.task_number_text,
                    self.task_score_text,
                ],
            ),
            self.task_progress,
            *self._race_controls(),
            self.task_prompt,
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
            input_filter=ft.InputFilter(regex_string=r"^-?\d*$", allow=True),
            on_change=self._sanitize_answer,
            on_submit=self._on_submit_clicked,
        )
        # Keep the field in the control tree before render() tries to focus it.
        # Flet rejects updates (including focus) for detached controls, which
        # otherwise aborts the click handler and leaves web and Android clients
        # on the empty page produced by page.clean().
        controls.append(self.answer_field)
        task_feedback = ft.Container(visible=False)
        self.task_feedback = task_feedback
        controls.append(task_feedback)
        if feedback:
            if feedback.is_correct:
                task_feedback.content = ft.Text(
                    "✓ Richtig! Super gelöst.", size=18, color=SUCCESS, weight=ft.FontWeight.BOLD
                )
                task_feedback.bgcolor = "#E6F4EA"
                task_feedback.visible = True
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
        self.task_action = self._action_button("Antwort prüfen", self._on_submit_clicked)
        controls.append(self.task_action)
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
        self.live_score_events, self.race_state = [], None
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
            input_filter=ft.InputFilter(regex_string=r"^-?\d*$", allow=True),
            on_change=self._sanitize_answer,
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
        if self.submission_in_progress:
            return
        if self.answer_field is None or self.special_task is None or self.special_mode is None:
            return
        self.submission_in_progress = True
        try:
            answer = int((self.answer_field.value or "").strip())
        except ValueError:
            self.submission_in_progress = False
            self.answer_field.error_text = "Die Antwort muss eine ganze Zahl sein."
            self.page.update()
            self.answer_field.focus()
            return
        mode, expected, now = self.special_mode, self.special_task.expected_answer, time.monotonic()
        try:
            if isinstance(mode, BlitzMode | WarmUpMode):
                correct = mode.submit(answer, expected, now)
            else:
                correct = mode.submit(answer, expected)
        except RuntimeError:
            self.submission_in_progress = False
            self.render()
            return
        self.special_feedback = "✓ Richtig!" if correct else f"✕ Richtig wäre {expected}."
        self._append_score_event(correct)
        if not self._special_finished(mode):
            self._next_special_task()
        self.submission_in_progress = False
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
        if self.race_state is None:
            self.race_live_panel = None
            return []
        self.race_live_panel = self._build_race_panel()
        return [self.race_live_panel]

    def _build_race_panel(self) -> ft.Container:
        """Build only the moving race area, independently of the answer form."""

        if self.race_state is None:
            raise RuntimeError("race panel requires a configured race")
        elapsed = max(0.0, time.monotonic() - self.round_started_at)
        own_name = self.active_player.name if self.active_player else "Du"
        own_icon = self.active_player.icon if self.active_player else "🙂"
        identities = [("player", own_name, own_icon, self.race_state.vehicle)]
        event_sets = [self.live_score_events]
        opponent_vehicles = (
            "🏎️",
            "🚀",
            "🛸",
            "🚲",
            "🐉",
            "🛶",
            "🐆",
            "🦄",
            "🏍️",
            "🛹",
            "🛼",
            "🚁",
            "🦖",
            "🐎",
            "🦅",
            "🐬",
        )
        for index, competitor in enumerate(self.race_state.competitors):
            identities.append(
                (
                    f"opponent-{index}",
                    competitor.player_name,
                    competitor.player_icon,
                    opponent_vehicles[index % len(opponent_vehicles)],
                )
            )
            event_sets.append(list(competitor.statistic.events))
        state = self._race_snapshot(identities, event_sets, elapsed)
        standings = {standing.racer_id: standing for standing in state.standings}
        own_rank = standings["player"].rank
        tracks = [
            self._race_track(name, player_icon, vehicle, standings[racer_id], racer_id == "player")
            for racer_id, name, player_icon, vehicle in identities
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
                                f"Platz {own_rank}/{len(identities)} · "
                                f"{self._race_summary(self.race_state.config)}",
                                color=PRIMARY,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    ft.Text("Fortschritt und Rang folgen der jeweiligen Rennregel.", color=MUTED),
                    *tracks,
                ],
            ),
        )

    def _race_track(
        self,
        name: str,
        player_icon: str,
        vehicle: str,
        standing: RaceStanding,
        is_player: bool,
    ) -> ft.Control:
        if self.race_state is None:
            raise RuntimeError("race track requires a configured race")
        progress = standing.progress
        track_width = layout_metrics(getattr(self.page, "width", None)).track_width
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
                            ft.Text(player_icon, size=22),
                            ft.Text(name, expand=True, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"Platz {standing.rank} · {self._standing_status(standing)} · "
                                f"{self._standing_detail(self.race_state.config, standing)}",
                                size=11,
                                color=MUTED,
                            ),
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

    def _race_snapshot(
        self,
        identities: list[tuple[str, str, str, str]],
        event_sets: list[list[ScoreEvent]],
        elapsed: float,
    ) -> RaceState:
        """Replay visible facts and let the race engine derive every standing."""

        assert self.race_state is not None
        config = self.race_state.config
        state = RaceState.create([identity[0] for identity in identities])
        timeline = sorted(
            (
                event.elapsed_seconds,
                racer_id,
                event,
            )
            for (racer_id, *_), events in zip(identities, event_sets, strict=True)
            for event in events
            if event.elapsed_seconds <= elapsed and event.task_completed is not False
        )
        for event_time, racer_id, score_event in timeline:
            try:
                kind = RaceEventKind(
                    score_event.event_kind
                    or (
                        RaceEventKind.CORRECT_ANSWER
                        if score_event.correct
                        else RaceEventKind.WRONG_ANSWER
                    )
                )
            except ValueError:
                kind = (
                    RaceEventKind.CORRECT_ANSWER
                    if score_event.correct
                    else RaceEventKind.WRONG_ANSWER
                )
            state = apply_race_event(config, state, RaceEvent(kind, racer_id, event_time))
        state = apply_race_event(
            config, state, RaceEvent(RaceEventKind.TIME_ELAPSED, elapsed_seconds=elapsed)
        )
        # A ghost must never be presented as having crossed a line merely because
        # its recording has no more events.
        if not state.finished:
            for (racer_id, *_), events in zip(identities[1:], event_sets[1:], strict=True):
                if events and elapsed >= events[-1].elapsed_seconds:
                    state = apply_race_event(
                        config,
                        state,
                        RaceEvent(
                            RaceEventKind.RECORDING_ENDED, racer_id, events[-1].elapsed_seconds
                        ),
                    )
        return state

    @staticmethod
    def _standing_status(standing: RaceStanding) -> str:
        target_reasons = {
            EndReason.TASK_TARGET_REACHED,
            EndReason.CORRECT_TARGET_REACHED,
            EndReason.COMBO_TARGET_REACHED,
        }
        if standing.status is RacerStatus.FINISHED and standing.end_reason in target_reasons:
            return "im Ziel"
        if standing.end_reason is EndReason.TIME_LIMIT_REACHED:
            return "Zeit abgelaufen"
        if standing.status is RacerStatus.ELIMINATED:
            return "nach Fehler ausgeschieden"
        if standing.status is RacerStatus.ABORTED:
            return "abgebrochen"
        if standing.status is RacerStatus.RECORDING_ENDED:
            return "Aufzeichnung beendet"
        return "läuft"

    @staticmethod
    def _standing_detail(config: RaceConfig, standing: RaceStanding) -> str:
        if config.kind is RaceKind.TASKS:
            tasks = f"Aufgabe {standing.completed_tasks}/{config.task_target}"
            if config.task_timeout_seconds is not None:
                return f"{standing.timeouts} Timeouts · {tasks}"
            return tasks
        if config.kind is RaceKind.CORRECT_ANSWERS:
            return f"{standing.correct_answers}/{config.correct_target} richtig"
        if config.kind is RaceKind.TIME_LIMIT:
            remaining = max(0, round((config.duration_seconds or 0) - standing.elapsed_seconds))
            return f"Noch {remaining} s · {standing.score} Punkte"
        if config.kind is RaceKind.PERFECT:
            return f"Serie {standing.streak}"
        return f"Serie {standing.streak}/{config.combo_target}"

    @staticmethod
    def _race_kind_name(config: RaceConfig) -> str:
        if config.kind is RaceKind.TASKS and config.task_timeout_seconds is not None:
            return "Aufgabenzeitmodus"
        return {
            RaceKind.TASKS: "Aufgaben-Sprint",
            RaceKind.CORRECT_ANSWERS: "Zieljagd",
            RaceKind.TIME_LIMIT: "Zeitspiel",
            RaceKind.PERFECT: "Perfect Run",
            RaceKind.COMBO: "Serienrennen",
        }[config.kind]

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
                *self._race_result_controls(),
                *self._race_controls(),
                *self._dashboard_controls(
                    self.race_state.comparison_hash
                    if self.race_state is not None
                    else game.definition_hash(),
                    highlight_latest=True,
                ),
                self._action_button(
                    "Rennen noch einmal" if self.race_state else "Noch einmal spielen",
                    lambda _: self._start_game(
                        game,
                        race_config=self.race_state.config if self.race_state else None,
                        competitors=(
                            list(self.race_state.competitors) if self.race_state else None
                        ),
                        race_vehicle=self.race_state.vehicle if self.race_state else "🚀",
                    ),
                ),
                ft.TextButton("Zur Spieleauswahl", on_click=lambda _: self._choose_another()),
            ],
        )

    def _race_result_controls(self) -> list[ft.Control]:
        """Explain the race result without replacing the ordinary game statistics."""

        if self.race_state is None:
            return []
        elapsed = max(0.0, time.monotonic() - self.round_started_at)
        own_name = self.active_player.name if self.active_player else "Du"
        identities = [("player", own_name, "", "")]
        event_sets = [self.live_score_events]
        for index, competitor in enumerate(self.race_state.competitors):
            identities.append((f"opponent-{index}", competitor.player_name, "", ""))
            event_sets.append(list(competitor.statistic.events))
        state = self._race_snapshot(identities, event_sets, elapsed)
        names = {racer_id: name for racer_id, name, *_ in identities}
        winner = names.get(state.winner_id, "Kein Gewinner") if state.winner_id else "Kein Gewinner"
        winner_standing = next(
            (standing for standing in state.standings if standing.racer_id == state.winner_id),
            state.standings[0],
        )
        cause = self._standing_status(winner_standing)
        if state.end_reason is EndReason.ABORTED:
            cause = "abgebrochen"
        return [
            ft.Container(
                padding=16,
                bgcolor="#EEF7F3",
                border_radius=16,
                border=ft.border.all(1, "#B9DECF"),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text("🏁 Rennergebnis", size=21, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Rennart: {self._race_kind_name(self.race_state.config)}"),
                        ft.Text(f"Endursache: {cause}"),
                        ft.Text(f"Gewinner: {winner}", weight=ft.FontWeight.BOLD, color=SUCCESS),
                        ft.Text(
                            "Leistung: "
                            + self._standing_detail(self.race_state.config, winner_standing)
                        ),
                        ft.Text(
                            "Tie-Breaker: richtige Antworten, Punkte, weniger Fehler, kürzere Zeit",
                            color=MUTED,
                            size=12,
                        ),
                    ],
                ),
            )
        ]

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

    @staticmethod
    def _format_duration(seconds: float) -> str:
        seconds = float(seconds)
        if seconds >= 60 and seconds % 60 == 0:
            minutes = int(seconds // 60)
            return f"{minutes} Minute" if minutes == 1 else f"{minutes} Minuten"
        value = int(seconds) if seconds.is_integer() else seconds
        return f"{value} Sekunde" if seconds == 1 else f"{value} Sekunden"

    @classmethod
    def _race_summary(cls, config: RaceConfig) -> str:
        if config.kind is RaceKind.TASKS:
            if config.task_timeout_seconds is not None:
                return (
                    f"Deadline pro Aufgabe: {cls._format_duration(config.task_timeout_seconds)} · "
                    f"äußere Rennbegrenzung: {config.task_target} Aufgaben"
                )
            return f"Ziellinie nach {config.task_target} Aufgaben"
        if config.kind is RaceKind.TIME_LIMIT:
            assert config.duration_seconds is not None
            return f"Gemeinsames Rennende nach {cls._format_duration(config.duration_seconds)}"
        if config.kind is RaceKind.CORRECT_ANSWERS:
            return f"Ziellinie nach {config.correct_target} richtigen Antworten"
        if config.kind is RaceKind.PERFECT:
            return "Dein Lauf endet beim ersten endgültigen Fehler"
        return f"Ziellinie nach {config.combo_target} richtigen Antworten in Folge"

    @staticmethod
    def _race_progress_target(config: RaceConfig) -> float:
        return float(
            config.task_target
            or config.correct_target
            or config.duration_seconds
            or config.combo_target
            or 1
        )

    @staticmethod
    def _race_comparison_hash(game: DefinedGame, config: RaceConfig) -> str:
        """Keep runs with changed race limits out of the original history bucket."""

        return DefinitionHash.from_payload(
            {"game": game.definition_hash(), "race": asdict(config)}
        ).as_uri()

    def _configure_race(self, game: DefinedGame) -> None:
        self._pause_for_dialog()
        availability = race_config_for_game(game)
        initial_config = availability.config
        comparison_hash = (
            self._race_comparison_hash(game, initial_config) if initial_config is not None else ""
        )
        recorded = self.statistics.race_competitors(comparison_hash, 8, initial_config)
        own_summary = (
            self.statistics.summary(self.active_player.id, comparison_hash)
            if self.active_player and initial_config is not None
            else None
        )
        personal_best = (
            self.statistics.best_round(self.active_player.id, comparison_hash)
            if self.active_player and initial_config is not None
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
        target = (
            ft.TextField(
                label="Richtige Antworten bis zur Ziellinie",
                value=str(initial_config.correct_target),
                helper_text="Nur bei der Zieljagd darf diese Rennvariante angepasst werden.",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            if initial_config is not None and initial_config.kind is RaceKind.CORRECT_ANSWERS
            else None
        )
        mode_explanation = ft.Text(
            self._race_summary(initial_config)
            if initial_config is not None
            else availability.reason or "Dieser Modus ist nicht rennfähig.",
            color=PRIMARY if initial_config is not None else ERROR,
            weight=ft.FontWeight.BOLD,
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
                    ("🏍️", "Motorrad"),
                    ("🛹", "Skateboard"),
                    ("🚁", "Hubschrauber"),
                    ("🦖", "Dinosaurier"),
                    ("🐎", "Pferd"),
                    ("🐬", "Delfin"),
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
            scrollable=True,
            title=ft.Text("🏁 Rennen gegen Computergegner"),
            content=ft.Container(
                width=min(520, layout_metrics(getattr(self.page, "width", None)).track_width),
                content=ft.Column(
                    tight=True,
                    spacing=10,
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
                        mode_explanation,
                        *([target] if target is not None else []),
                        vehicle,
                        error_text,
                    ],
                ),
            ),
        )

        def close(_: object) -> None:
            # Dialogs opened through Page.open() live in the page overlay. Merely
            # setting ``open`` to False leaves that overlay registered in Flet and
            # can keep its modal barrier in front of the game. Page.close() removes
            # it through the matching public API and performs the required update.
            self.page.close(dialog)
            self._resume_after_dialog()

        def start(_: object) -> None:
            try:
                count = int(opponent_count.value or "3")
                if initial_config is None:
                    raise ValueError(availability.reason or "Diese Rennart ist nicht verfügbar.")
                race_config = initial_config
                if target is not None:
                    correct_target = int(target.value or "0")
                    if correct_target <= 0:
                        raise ValueError("Das Rennziel muss mindestens 1 richtige Antwort sein.")
                    race_config = RaceConfig(
                        RaceKind.CORRECT_ANSWERS,
                        correct_target=correct_target,
                        wrong_answer_penalty=initial_config.wrong_answer_penalty,
                        task_timeout_seconds=initial_config.task_timeout_seconds,
                    )
                selected_hash = self._race_comparison_hash(game, race_config)
                selected_source = source.value or "computer_static"
                if selected_source == "recorded":
                    competitors = self.statistics.race_competitors(
                        selected_hash, count, race_config
                    )
                else:
                    selected_levels = parse_race_levels(levels.value or "")
                    if selected_source == "computer_history" and own_summary is None:
                        raise ValueError("Für diesen Gegner fehlt noch eine eigene Runde.")
                    baseline = (
                        sum(item.score for item in own_summary.rounds) / len(own_summary.rounds)
                        if selected_source == "computer_history" and own_summary
                        else None
                    )
                    competitors = [
                        computer_competitor(
                            selected_hash,
                            race_config,
                            level=computer_level,
                            baseline_points=baseline,
                            seed=index + int(self._race_progress_target(race_config)),
                            variable=bool(variable.value),
                        )
                        for index, computer_level in enumerate(selected_levels)
                    ]
                    if include_personal_best.value and personal_best is not None:
                        competitors.insert(
                            0,
                            RaceCompetitor(
                                f"{self.active_player.name} · persönlicher Rekord"
                                if self.active_player
                                else "Persönlicher Rekord",
                                personal_best,
                                self.active_player.icon if self.active_player else "🙂",
                            ),
                        )
                if not competitors:
                    raise ValueError("Keine aufgezeichneten Gegner verfügbar.")
            except ValueError as error:
                error_text.value = str(error) or "Bitte prüfe die Eingaben."
                self.page.update()
                return
            self.page.close(dialog)
            self.dialog_open = False

            def begin_race() -> None:
                self._start_game(
                    game,
                    race_config=race_config,
                    competitors=competitors,
                    race_vehicle=vehicle.value or "🚀",
                )

            # Give Flet one client update to remove the modal barrier before the
            # game view is changed. Otherwise both updates can overtake each other.
            threading.Timer(0.12, begin_race).start()

        dialog.actions = [
            ft.TextButton("Abbrechen", on_click=close),
            ft.ElevatedButton(
                "Rennen starten", on_click=start, disabled=not availability.available
            ),
        ]
        self.page.open(dialog)

    def _start_game(
        self,
        game: DefinedGame | None,
        *,
        race_config: RaceConfig | None = None,
        competitors: list[RaceCompetitor] | None = None,
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
        count = (
            race_config.correct_target
            if race_config is not None and race_config.kind is RaceKind.CORRECT_ANSWERS
            else game.task_count or game.correct_target or 20
        )
        assert count is not None
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
        self.race_state = (
            RaceController(
                race_config,
                tuple(competitors or ()),
                race_vehicle,
                self._race_comparison_hash(game, race_config),
            )
            if race_config is not None
            else None
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
                (
                    self.race_state.comparison_hash
                    if self.race_state is not None
                    else self.active_game.definition_hash()
                ),
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
            text=label,
            on_click=handler,
            width=min(420, layout_metrics(getattr(self.page, "width", None)).track_width),
            height=54,
            bgcolor=PRIMARY,
            color="white",
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
        race_state = self.race_state

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
                    race_config=race_state.config if race_state else None,
                    competitors=list(race_state.competitors) if race_state else None,
                    race_vehicle=race_state.vehicle if race_state else "🚀",
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
        self._pause_for_dialog()
        dialog = ft.AlertDialog(modal=True, title=ft.Text(title), content=ft.Text(message))

        def close(_: object) -> None:
            self.page.close(dialog)
            self._resume_after_dialog()

        def confirm(_: object) -> None:
            self.page.close(dialog)
            self.dialog_open = False
            threading.Timer(0.12, action).start()

        dialog.actions = [
            ft.TextButton("Abbrechen", on_click=close),
            ft.ElevatedButton("Ja, fortfahren", on_click=confirm),
        ]
        self.page.open(dialog)

    def _pause_for_dialog(self) -> None:
        """Pause live movement and elapsed race time while a modal has focus."""

        if self.dialog_open:
            return
        self.dialog_open = True
        self.dialog_paused_at = time.monotonic()
        self._cancel_ghost_tick()
        self._cancel_auto_advance()
        self._cancel_special_deadline()

    def _resume_after_dialog(self) -> None:
        if not self.dialog_open:
            return
        paused_for = max(0.0, time.monotonic() - self.dialog_paused_at)
        if self.round_started_at:
            self.round_started_at += paused_for
        if isinstance(self.special_mode, BlitzMode | WarmUpMode):
            self.special_mode.started_at += paused_for
        self.dialog_open = False
        if self.race_state is not None and self.session and self.session.phase is RoundPhase.TASK:
            self._schedule_ghost_tick()
        if self.session and self.session.feedback and self.session.feedback.is_correct:
            self._schedule_auto_advance(0.8)
        if isinstance(self.special_mode, BlitzMode | WarmUpMode):
            remaining = max(
                0.0,
                self.special_mode.duration_seconds
                - (time.monotonic() - self.special_mode.started_at),
            )
            self.special_deadline_timer = threading.Timer(remaining, self._special_deadline_reached)
            self.special_deadline_timer.start()

    def _choose_another(self) -> None:
        self.session, self.active_game, self.view = None, None, "play"
        self.render()

    def _on_submit_clicked(self, _: object) -> None:
        if self.submission_in_progress:
            return
        if self.answer_field is None:
            return
        self.submission_in_progress = True
        try:
            feedback = self._active_session().submit_answer(self.answer_field.value or "")
        except (ValueError, RuntimeError) as error:
            self.submission_in_progress = False
            if isinstance(error, RuntimeError):
                return
            self.answer_field.error_text = str(error)
            self.page.update()
            self.answer_field.focus()
            return
        self._append_score_event(feedback.is_correct)
        self.submission_in_progress = False
        if self._active_session().phase is RoundPhase.FINISHED:
            self.render()
            return
        if not feedback.is_correct and not feedback.is_task_complete:
            self.answer_field.value = ""
        self._update_task_controls()

    def _update_task_controls(self) -> None:
        """Update only changing task widgets without rebuilding the whole page."""

        session = self._active_session()
        task = session.current_task
        if (
            task is None
            or self.task_number_text is None
            or self.task_score_text is None
            or self.task_progress is None
            or self.task_prompt is None
            or self.task_feedback is None
            or self.task_action is None
            or self.answer_field is None
        ):
            self.render()
            return
        number_text = self.task_number_text
        score_text = self.task_score_text
        progress = self.task_progress
        prompt = self.task_prompt
        feedback_box = self.task_feedback
        action = self.task_action
        answer = self.answer_field
        points = self.live_score_events[-1].points_after if self.live_score_events else 0
        wrong = len(session.results) - session.correct_count
        elapsed = max(0.0, time.monotonic() - self.round_started_at)
        timed = bool(self.active_game and self.active_game.duration_seconds)
        number_text.value = (
            f"{self.active_game.name if self.active_game else 'Spiel'} · "
            f"Aufgabe {session.task_number}/{session.task_count}"
        )
        score_text.value = (
            f"✓ {session.correct_count}   ✕ {wrong}   ⭐ {points} P   "
            f"{'⏳' if timed else '⏱️'} {elapsed:.0f} s"
        )
        progress.value = session.progress
        prompt.value = task.prompt
        feedback = session.feedback
        feedback_box.visible = feedback is not None
        feedback_box.padding = 12
        feedback_box.border_radius = 12
        if feedback is None:
            answer.value = ""
            answer.disabled = False
            answer.error_text = None
            action.text = "Antwort prüfen"
            action.on_click = self._on_submit_clicked
            action.visible = True
        elif feedback.is_correct:
            feedback_box.bgcolor = "#E6F4EA"
            feedback_box.content = ft.Text(
                "✓ Richtig! Super gelöst.", size=18, color=SUCCESS, weight=ft.FontWeight.BOLD
            )
            action.visible = False
            self._schedule_auto_advance(0.8)
        elif not feedback.is_task_complete:
            feedback_box.bgcolor = "#FEF9E7"
            feedback_box.content = ft.Text(
                "⚠️ Nicht ganz. Du hast noch 1 Versuch!",
                size=18,
                color=WARNING,
                weight=ft.FontWeight.BOLD,
            )
        else:
            feedback_box.bgcolor = "#FCE8E6"
            feedback_box.content = ft.Text(
                f"✕ Die richtige Antwort ist {feedback.expected_answer}.",
                size=18,
                color=ERROR,
                weight=ft.FontWeight.BOLD,
            )
            answer.disabled = True
            action.text = "Nächste Aufgabe (Enter)"
            action.on_click = lambda _: self._next_task()
            action.visible = True
        self.page.update()
        if feedback is None:
            answer.focus()

    def _append_score_event(self, correct: bool) -> None:
        game = self.active_game
        if game is None:
            return
        previous = self.live_score_events[-1].points_after if self.live_score_events else 0
        points = previous + (1 if correct else game.wrong_answer_penalty)
        session = self.session
        previous_correct = (
            self.live_score_events[-1].correct_answers or 0 if self.live_score_events else 0
        )
        previous_completed = (
            self.live_score_events[-1].completed_tasks or 0 if self.live_score_events else 0
        )
        previous_combo = self.live_score_events[-1].combo or 0 if self.live_score_events else 0
        task_completed = bool(session and session.feedback and session.feedback.is_task_complete)
        completed_tasks = previous_completed + int(task_completed)
        end_reason = (
            session.end_reason.value
            if session is not None and session.end_reason is not None
            else None
        )
        self.live_score_events.append(
            ScoreEvent(
                elapsed_seconds=max(0.0, time.monotonic() - self.round_started_at),
                correct=correct,
                points_after=points,
                task_number=(
                    session.task_number if session is not None else len(self.live_score_events) + 1
                ),
                event_kind=(
                    RaceEventKind.CORRECT_ANSWER.value
                    if correct
                    else RaceEventKind.WRONG_ANSWER.value
                ),
                task_completed=task_completed,
                correct_answers=previous_correct + int(correct),
                completed_tasks=completed_tasks,
                combo=previous_combo + 1 if correct else 0,
                end_reason=end_reason,
            )
        )
        if self.race_state is not None and not self.dialog_open:
            self._refresh_race_panel()

    def _next_task(self) -> None:
        self._cancel_auto_advance()
        self._active_session().advance_to_next_task()
        if self._active_session().phase is RoundPhase.FINISHED:
            self.render()
        else:
            self._update_task_controls()

    def _schedule_auto_advance(self, seconds: float) -> None:
        self._cancel_auto_advance()
        self.auto_advance_timer = threading.Timer(seconds, self._next_task)
        self.auto_advance_timer.start()

    def _cancel_auto_advance(self) -> None:
        if self.auto_advance_timer:
            self.auto_advance_timer.cancel()
            self.auto_advance_timer = None

    def _schedule_ghost_tick(self) -> None:
        """Start one Flet-owned live-update loop for the current race view."""

        self._cancel_ghost_tick()
        generation = self.ghost_tick_generation
        self.ghost_tick_task = self.page.run_task(self._ghost_tick, generation)

    async def _ghost_tick(self, generation: int) -> None:
        """Refresh the race panel until this particular loop becomes obsolete."""

        while generation == self.ghost_tick_generation:
            await asyncio.sleep(0.5)
            if generation != self.ghost_tick_generation or not self._race_tick_is_active():
                return
            self._refresh_race_panel()

    def _race_tick_is_active(self) -> bool:
        return (
            not self.dialog_open
            and self.race_state is not None
            and self.session is not None
            and self.session.phase is RoundPhase.TASK
            and self.race_live_panel is not None
        )

    def _refresh_race_panel(self) -> None:
        """Refresh positions immediately while retaining the rest of the task UI."""

        if self.race_live_panel is None:
            return
        refreshed = self._build_race_panel()
        self.race_live_panel.content = refreshed.content
        self.race_live_panel.update()

    def _cancel_ghost_tick(self) -> None:
        # Incrementing first also invalidates a coroutine which is just waking
        # up and cannot be cancelled before it next gets CPU time.
        self.ghost_tick_generation += 1
        if self.ghost_tick_task is not None:
            self.ghost_tick_task.cancel()
            self.ghost_tick_task = None

    def _on_keyboard(self, event: ft.KeyboardEvent) -> None:
        if (
            event.key == "Enter"
            and self.session
            and self.session.feedback
            and self.session.feedback.is_task_complete
        ):
            self._next_task()

    def _sanitize_answer(self, _: object) -> None:
        """Defensively normalise input because Android keyboards vary."""

        if self.answer_field is None:
            return
        normalized = normalize_integer_input(self.answer_field.value or "")
        if normalized != self.answer_field.value:
            self.answer_field.value = normalized
            self.answer_field.update()

    def _on_resize(self, _: object) -> None:
        """Resize the mounted card without rebuilding the complete page.

        Browser scrollbars and Android system UI can emit resize events while a
        menu click is already replacing the view. A second full ``render()`` in
        that situation used to clear the new view again and could leave the
        client white. Updating the responsive shell in place avoids that race.
        """

        root_container = self.root_container
        if root_container is None:
            return
        metrics = layout_metrics(getattr(self.page, "width", None))
        root_container.width = metrics.content_width
        root_container.padding = metrics.padding
        root_container.border_radius = 18 if metrics.compact else 28
        root_container.update()

    def _on_lifecycle_change(self, event: object) -> None:
        """Pause all wall-clock UI work while Android is in the background."""

        state = str(getattr(event, "data", getattr(event, "state", ""))).lower()
        if any(value in state for value in ("paused", "inactive", "detached", "hidden")):
            if not self.paused:
                self.paused = True
                self._pause_for_dialog()
            return
        if "resumed" in state and self.paused:
            self.paused = False
            self._resume_after_dialog()
            self.render()

    def _on_android_back(self, _: object) -> None:
        """Require confirmation before Android Back abandons a running round."""

        if self.session is not None or self.special_mode is not None:
            self._confirm_menu()
        elif self.view != "menu":
            self._navigate("menu")

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
