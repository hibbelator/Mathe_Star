"""Task generator for complete Excel-style game definitions."""

from __future__ import annotations

from dataclasses import dataclass

from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import OperandRange
from math_game.core.presets import DefinedGame
from math_game.core.task import ArithmeticTask
from math_game.generators.contracts import IntegerRandomSource


@dataclass(frozen=True, slots=True)
class DefinedGameTaskGenerator:
    """Select an operation by its weight and apply the legacy operand rules."""

    random_source: IntegerRandomSource
    game: DefinedGame

    def generate(self, definition: OperationDefinition) -> ArithmeticTask:
        del definition
        operation = self._choose_operation()
        if operation is ArithmeticOperation.DIVISION:
            quotient = self._random_table()
            divisor = self.random_source.randint(self.game.factor_min, self.game.factor_max)
            return ArithmeticTask(
                operation=operation,
                left_operand=quotient * divisor,
                right_operand=divisor,
                expected_answer=quotient,
            )

        if operation is ArithmeticOperation.MULTIPLICATION:
            definition = OperationDefinition(
                operation=operation,
                left=OperandRange(min(self.game.allowed_tables), max(self.game.allowed_tables)),
                right=OperandRange(self.game.factor_min, self.game.factor_max),
            )
            # Pick explicitly to support non-contiguous table lists.
            left = self._random_table()
            right = self.random_source.randint(definition.right.minimum, definition.right.maximum)
            return ArithmeticTask(
                operation=operation,
                left_operand=left,
                right_operand=right,
                expected_answer=left * right,
            )

        if operation is ArithmeticOperation.ADDITION:
            left = self.random_source.randint(
                self.game.factor_min, self.game.max_result - self.game.factor_min
            )
            right = self.random_source.randint(self.game.factor_min, self.game.max_result - left)
            return ArithmeticTask(
                operation=operation,
                left_operand=left,
                right_operand=right,
                expected_answer=left + right,
            )
        left = self.random_source.randint(self.game.factor_min, self.game.max_result - 1)
        right = self.random_source.randint(self.game.factor_min, left)
        return ArithmeticTask(
            operation=operation,
            left_operand=left,
            right_operand=right,
            expected_answer=left - right,
        )

    def _choose_operation(self) -> ArithmeticOperation:
        weights = self.game.weights
        choices = (
            (ArithmeticOperation.ADDITION, weights.addition),
            (ArithmeticOperation.SUBTRACTION, weights.subtraction),
            (ArithmeticOperation.MULTIPLICATION, weights.multiplication),
            (ArithmeticOperation.DIVISION, weights.division),
        )
        draw = self.random_source.randint(1, sum(weight for _, weight in choices))
        cumulative = 0
        for operation, weight in choices:
            cumulative += weight
            if draw <= cumulative:
                return operation
        raise RuntimeError("weighted operation selection failed")

    def _random_table(self) -> int:
        index = self.random_source.randint(0, len(self.game.allowed_tables) - 1)
        return self.game.allowed_tables[index]
