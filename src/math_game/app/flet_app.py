# pyright: basic, reportMissingImports=false
"""Flet user interface for the Mathe-Abenteuer application."""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable

import flet as ft

from math_game.app.session import RoundPhase, RoundSession
from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import OperandRange
from math_game.generators import (
    AdditionTaskGenerator,
    MixedTaskGenerator,
    MultiplicationTaskGenerator,
    SubtractionTaskGenerator,
)
from math_game.generators.contracts import TaskGenerator
from math_game.generators.random_source import PythonRandomSource

BACKGROUND = "#F4F7FF"
INK = "#17223B"
PRIMARY = "#536DFE"
SUCCESS = "#168F68"
WARNING = "#E67E22"
ERROR = "#C2415B"
CARD = "#FFFFFF"


class MathAdventureApp:
    """Render the configurable round and inline feedback UI into a Flet page."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.session: RoundSession | None = None
        self.answer_field: ft.TextField | None = None
        self.auto_advance_timer: threading.Timer | None = None

        # Configurable Options (Defaults)
        self.selected_operation: str = "addition"
        self.selected_max_range: int = 20
        self.selected_task_count: int = 5
        self.allow_second_chance: bool = True

        page.title = "Mathe-Abenteuer"
        page.bgcolor = BACKGROUND
        page.padding = 24
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.on_keyboard_event = self._on_keyboard
        self.render()

    def render(self) -> None:
        self._cancel_auto_advance()
        self.page.clean()
        if self.session is None or self.session.phase is RoundPhase.READY:
            content = self._start_options_view()
        elif self.session.phase is RoundPhase.FINISHED:
            content = self._finished_view()
        else:
            content = self._task_view()

        self.page.add(
            ft.Container(
                width=580,
                padding=32,
                bgcolor=CARD,
                border_radius=28,
                content=content,
            )
        )
        self.page.update()

        if (
            self.answer_field is not None
            and self.session is not None
            and self.session.phase is RoundPhase.TASK
        ):
            self.answer_field.focus()

    def _start_options_view(self) -> ft.Column:
        """Render the configuration options screen before starting a round."""

        operation_dropdown = ft.Dropdown(
            label="Rechenart",
            value=self.selected_operation,
            options=[
                ft.dropdown.Option("addition", "Addition (+)"),
                ft.dropdown.Option("subtraction", "Subtraktion (−)"),
                ft.dropdown.Option("multiplication", "Einmaleins (×)"),
                ft.dropdown.Option("mixed", "Gemischt (+, −, ×)"),
            ],
            on_change=lambda e: setattr(self, "selected_operation", e.control.value),
        )

        range_dropdown = ft.Dropdown(
            label="Zahlenraum bis",
            value=str(self.selected_max_range),
            options=[
                ft.dropdown.Option("10", "bis 10"),
                ft.dropdown.Option("20", "bis 20"),
                ft.dropdown.Option("50", "bis 50"),
                ft.dropdown.Option("100", "bis 100"),
            ],
            on_change=lambda e: setattr(self, "selected_max_range", int(e.control.value)),
        )

        count_dropdown = ft.Dropdown(
            label="Anzahl Aufgaben",
            value=str(self.selected_task_count),
            options=[
                ft.dropdown.Option("5", "5 Aufgaben"),
                ft.dropdown.Option("10", "10 Aufgaben"),
                ft.dropdown.Option("15", "15 Aufgaben"),
                ft.dropdown.Option("20", "20 Aufgaben"),
            ],
            on_change=lambda e: setattr(self, "selected_task_count", int(e.control.value)),
        )

        second_chance_switch = ft.Switch(
            label="2. Chance bei Fehler (Zweiter Versuch erlaubt)",
            value=self.allow_second_chance,
            on_change=lambda e: setattr(self, "allow_second_chance", e.control.value),
        )

        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.Text("🧭", size=54),
                ft.Text("Mathe-Abenteuer", size=36, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text(
                    "Passe deine Übung an und starte deine Runde.",
                    size=16,
                    color="#52607A",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Divider(height=1, color="#E6EAFE"),
                operation_dropdown,
                range_dropdown,
                count_dropdown,
                second_chance_switch,
                ft.Container(height=10),
                self._action_button("🚀 Abenteuer starten", self._start_custom_session),
            ],
        )

    def _task_view(self) -> ft.Column:
        """Render active task with inline feedback directly below the input."""

        session = self._active_session()
        task = session.current_task
        if task is None:
            raise RuntimeError("task view requires an active task")

        controls: list[ft.Control] = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        f"Aufgabe {session.task_number} von {session.task_count}",
                        color="#52607A",
                        size=16,
                    ),
                    ft.Text(
                        f"Richtig: {session.correct_count}",
                        color=SUCCESS,
                        weight=ft.FontWeight.BOLD,
                        size=16,
                    ),
                ],
            ),
            ft.ProgressBar(value=session.progress, color=PRIMARY, bgcolor="#E6EAFE"),
            ft.Text(task.prompt, size=48, weight=ft.FontWeight.BOLD, color=INK),
        ]

        feedback = session.feedback

        # Answer Field (disabled only when showing final wrong answer feedback)
        field_disabled = (
            feedback is not None and feedback.is_task_complete and not feedback.is_correct
        )
        self.answer_field = ft.TextField(
            label="Deine Antwort",
            text_align=ft.TextAlign.CENTER,
            text_size=28,
            autofocus=True,
            disabled=field_disabled,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._on_submit_clicked,
        )
        controls.append(self.answer_field)

        # Inline Feedback Widget
        if feedback is not None:
            if feedback.is_correct:
                inline_feedback = ft.Container(
                    padding=12,
                    bgcolor="#E6F4EA",
                    border_radius=12,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text("✓", size=24, color=SUCCESS, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Richtig! Super gelöst.",
                                size=18,
                                color=SUCCESS,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                )
                self._schedule_auto_advance(0.8)
            elif not feedback.is_task_complete:
                inline_feedback = ft.Container(
                    padding=12,
                    bgcolor="#FEF9E7",
                    border_radius=12,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text("⚠️", size=22),
                            ft.Text(
                                "Nicht ganz. Du hast noch 1 Versuch!",
                                size=16,
                                color=WARNING,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                )
            else:
                inline_feedback = ft.Container(
                    padding=12,
                    bgcolor="#FCE8E6",
                    border_radius=12,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Text(
                                f"✕ Die richtige Antwort ist {feedback.expected_answer}.",
                                size=18,
                                color=ERROR,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                )
            controls.append(inline_feedback)

        # Action Buttons
        if feedback is not None and feedback.is_task_complete and not feedback.is_correct:
            controls.append(
                self._action_button("Nächste Aufgabe (Enter)", lambda _: self._next_task())
            )
        elif feedback is None or not feedback.is_task_complete:
            controls.append(self._action_button("Antwort prüfen", self._on_submit_clicked))

        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=18,
            controls=controls,
        )

    def _finished_view(self) -> ft.Column:
        session = self._active_session()
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=22,
            controls=[
                ft.Text("🏁", size=58),
                ft.Text("Runde geschafft!", size=34, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text(
                    f"Du hast {session.correct_count} von {session.task_count} "
                    "Aufgaben richtig gelöst.",
                    size=20,
                    color="#52607A",
                    text_align=ft.TextAlign.CENTER,
                ),
                self._action_button(
                    "Noch einmal spielen", lambda _: self._start_custom_session(None)
                ),
                ft.TextButton(
                    "Einstellungen ändern", on_click=lambda _: self._choose_another()
                ),
            ],
        )

    def _action_button(
        self,
        label: str,
        handler: Callable[[object], None],
    ) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            text=label,
            on_click=handler,
            width=360,
            height=54,
            bgcolor=PRIMARY,
            color="white",
        )

    def _start_custom_session(self, _: object) -> None:
        self._cancel_auto_advance()
        random_src = PythonRandomSource()
        op_type = self.selected_operation

        if op_type == "addition":
            generator: TaskGenerator = AdditionTaskGenerator(random_src)
            op = ArithmeticOperation.ADDITION
        elif op_type == "subtraction":
            generator = SubtractionTaskGenerator(random_src)
            op = ArithmeticOperation.SUBTRACTION
        elif op_type == "multiplication":
            generator = MultiplicationTaskGenerator(random_src)
            op = ArithmeticOperation.MULTIPLICATION
        else:
            generator = MixedTaskGenerator(random_src)
            op = ArithmeticOperation.ADDITION

        definition = OperationDefinition(
            operation=op,
            left=OperandRange(1, self.selected_max_range),
            right=OperandRange(1, self.selected_max_range),
            allow_negative_results=False,
        )

        max_attempts = 2 if self.allow_second_chance else 1
        self.session = RoundSession(
            generator=generator,
            definition=definition,
            task_count=self.selected_task_count,
            max_attempts_per_task=max_attempts,
        )
        self.session.start()
        self.render()

    def _on_submit_clicked(self, _: object) -> None:
        if self.answer_field is None:
            return
        try:
            feedback = self._active_session().submit_answer(self.answer_field.value or "")
        except ValueError as error:
            self.answer_field.error_text = str(error)
            self.answer_field.focus()
            self.page.update()
            return

        if not feedback.is_correct and not feedback.is_task_complete:
            # Second chance attempt: clear answer field for retry
            self.answer_field.value = ""
            self.answer_field.error_text = None

        self.render()

    def _next_task(self) -> None:
        self._cancel_auto_advance()
        self._active_session().advance_to_next_task()
        self.render()

    def _schedule_auto_advance(self, delay_seconds: float) -> None:
        self._cancel_auto_advance()
        self.auto_advance_timer = threading.Timer(delay_seconds, self._next_task)
        self.auto_advance_timer.start()

    def _cancel_auto_advance(self) -> None:
        if self.auto_advance_timer is not None:
            self.auto_advance_timer.cancel()
            self.auto_advance_timer = None

    def _choose_another(self) -> None:
        self._cancel_auto_advance()
        self.session = None
        self.render()

    def _on_keyboard(self, event: ft.KeyboardEvent) -> None:
        if event.key == "Enter" and self.session is not None:
            feedback = self.session.feedback
            if feedback is not None and feedback.is_task_complete:
                self._next_task()

    def _active_session(self) -> RoundSession:
        if self.session is None:
            raise RuntimeError("no active round")
        return self.session


def main(page: ft.Page) -> None:
    """Create the Mathe-Abenteuer application on a Flet page."""

    MathAdventureApp(page)


def run() -> None:
    """Launch the local Flet application."""

    use_web = "--web" in sys.argv or os.getenv("FLET_VIEW") in {"web", "1", "true"}
    view = ft.AppView.WEB_BROWSER if use_web else ft.AppView.FLET_APP
    ft.app(target=main, view=view)


if __name__ == "__main__":
    run()
