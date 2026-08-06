"""Generated arithmetic task values shared by generators and future modes."""

from __future__ import annotations

from dataclasses import dataclass

from math_game.core.contracts import ArithmeticOperation


@dataclass(frozen=True, slots=True)
class ArithmeticTask:
    """One fully resolved arithmetic task, without UI or session state."""

    operation: ArithmeticOperation
    left_operand: int
    right_operand: int
    expected_answer: int

    @property
    def prompt(self) -> str:
        """Return a presentation-neutral, readable expression."""

        symbols = {
            ArithmeticOperation.ADDITION: "+",
            ArithmeticOperation.SUBTRACTION: "−",
            ArithmeticOperation.MULTIPLICATION: "×",
            ArithmeticOperation.DIVISION: "÷",
        }
        return f"{self.left_operand} {symbols[self.operation]} {self.right_operand}"
