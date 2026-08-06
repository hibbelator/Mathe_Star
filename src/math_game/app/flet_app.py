# pyright: basic, reportMissingImports=false
"""Flet user interface for the first playable Mathe-Abenteuer round."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from math_game.app.session import RoundPhase, RoundSession
from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import OperandRange
from math_game.generators import AdditionTaskGenerator, SubtractionTaskGenerator
from math_game.generators.contracts import TaskGenerator
from math_game.generators.random_source import PythonRandomSource

BACKGROUND = "#F4F7FF"
INK = "#17223B"
PRIMARY = "#536DFE"
SUCCESS = "#168F68"
ERROR = "#C2415B"
CARD = "#FFFFFF"


class MathAdventureApp:
    """Render the four explicit round phases into one Flet page."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.session: RoundSession | None = None
        self.answer_field: ft.TextField | None = None

        page.title = "Mathe-Abenteuer"
        page.bgcolor = BACKGROUND
        page.padding = 24
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.on_keyboard_event = self._on_keyboard
        self.render()

    def render(self) -> None:
        self.page.clean()
        if self.session is None or self.session.phase is RoundPhase.READY:
            content = self._start_view()
        elif self.session.phase is RoundPhase.TASK:
            content = self._task_view()
        elif self.session.phase is RoundPhase.FEEDBACK:
            content = self._feedback_view()
        else:
            content = self._finished_view()

        self.page.add(
            ft.Container(
                width=560,
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

    def _start_view(self) -> ft.Column:
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=22,
            controls=[
                ft.Text("🧭", size=54),
                ft.Text("Mathe-Abenteuer", size=36, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text(
                    "Wähle deinen Weg und löse fünf kurze Aufgaben.",
                    size=18,
                    color="#52607A",
                    text_align=ft.TextAlign.CENTER,
                ),
                self._action_button("Addition entdecken", self._start_addition),
                self._action_button("Subtraktion meistern", self._start_subtraction),
            ],
        )

    def _task_view(self) -> ft.Column:
        session = self._active_session()
        task = session.current_task
        if task is None:
            raise RuntimeError("task phase requires a current task")

        self.answer_field = ft.TextField(
            label="Deine Antwort",
            text_align=ft.TextAlign.CENTER,
            text_size=28,
            autofocus=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=self._submit,
        )
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=24,
            controls=[
                ft.Text(
                    f"Aufgabe {session.task_number} von {session.task_count}",
                    color="#52607A",
                    size=16,
                ),
                ft.ProgressBar(value=session.progress, color=PRIMARY, bgcolor="#E6EAFE"),
                ft.Text(task.prompt, size=48, weight=ft.FontWeight.BOLD, color=INK),
                self.answer_field,
                self._action_button("Antwort prüfen", self._submit),
                ft.Text("Enter funktioniert ebenfalls", size=13, color="#758099"),
            ],
        )

    def _feedback_view(self) -> ft.Column:
        session = self._active_session()
        feedback = session.feedback
        if feedback is None:
            raise RuntimeError("feedback phase requires answer feedback")

        if feedback.is_correct:
            symbol, heading, detail, color = "✓", "Richtig!", "Stark gelöst.", SUCCESS
        else:
            symbol, heading, detail, color = (
                "→",
                "Fast geschafft",
                f"Die richtige Antwort ist {feedback.expected_answer}.",
                ERROR,
            )
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.Text(symbol, size=64, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(heading, size=34, weight=ft.FontWeight.BOLD, color=INK),
                ft.Text(detail, size=20, color="#52607A", text_align=ft.TextAlign.CENTER),
                ft.Text(
                    f"{session.correct_count} von {len(session.results)} richtig",
                    size=16,
                    color="#52607A",
                ),
                self._action_button("Weiter", self._continue),
            ],
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
                self._action_button("Noch einmal", self._restart),
                ft.TextButton("Andere Übung wählen", on_click=self._choose_another),
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
            height=56,
            bgcolor=PRIMARY,
            color="white",
        )

    def _start_addition(self, _: object) -> None:
        definition = OperationDefinition(
            operation=ArithmeticOperation.ADDITION,
            left=OperandRange(1, 20),
            right=OperandRange(1, 20),
        )
        self._start_session(AdditionTaskGenerator(PythonRandomSource()), definition)

    def _start_subtraction(self, _: object) -> None:
        definition = OperationDefinition(
            operation=ArithmeticOperation.SUBTRACTION,
            left=OperandRange(1, 20),
            right=OperandRange(1, 20),
            allow_negative_results=False,
        )
        self._start_session(SubtractionTaskGenerator(PythonRandomSource()), definition)

    def _start_session(self, generator: TaskGenerator, definition: OperationDefinition) -> None:
        self.session = RoundSession(generator=generator, definition=definition, task_count=5)
        self.session.start()
        self.render()

    def _submit(self, _: object) -> None:
        if self.answer_field is None:
            return
        try:
            self._active_session().submit_answer(self.answer_field.value or "")
        except ValueError as error:
            self.answer_field.error_text = str(error)
            self.answer_field.focus()
            self.page.update()
            return
        self.answer_field = None
        self.render()

    def _continue(self, _: object) -> None:
        self._active_session().continue_round()
        self.render()

    def _restart(self, _: object) -> None:
        self._active_session().start()
        self.render()

    def _choose_another(self, _: object) -> None:
        self.session = None
        self.render()

    def _on_keyboard(self, event: ft.KeyboardEvent) -> None:
        if (
            event.key == "Enter"
            and self.session is not None
            and self.session.phase is RoundPhase.FEEDBACK
        ):
            self._continue(event)

    def _active_session(self) -> RoundSession:
        if self.session is None:
            raise RuntimeError("no active round")
        return self.session


def main(page: ft.Page) -> None:
    """Create the Mathe-Abenteuer application on a Flet page."""

    MathAdventureApp(page)


def run() -> None:
    """Launch the local Flet application."""

    ft.app(target=main)


if __name__ == "__main__":
    run()
