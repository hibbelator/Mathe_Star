"""Third vertical generator slice: integer multiplication."""

from __future__ import annotations

from dataclasses import dataclass

from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.task import ArithmeticTask
from math_game.generators.contracts import IntegerRandomSource


@dataclass(frozen=True, slots=True)
class MultiplicationTaskGenerator:
    """Create multiplication tasks from the two configured operand ranges."""

    random_source: IntegerRandomSource

    def generate(self, definition: OperationDefinition) -> ArithmeticTask:
        left = self.random_source.randint(definition.left.minimum, definition.left.maximum)
        right = self.random_source.randint(definition.right.minimum, definition.right.maximum)
        return ArithmeticTask(
            operation=ArithmeticOperation.MULTIPLICATION,
            left_operand=left,
            right_operand=right,
            expected_answer=left * right,
        )
