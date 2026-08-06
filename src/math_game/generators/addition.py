"""First vertical generator slice: integer addition."""

from __future__ import annotations

from dataclasses import dataclass

from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.task import ArithmeticTask
from math_game.generators.contracts import IntegerRandomSource


@dataclass(frozen=True, slots=True)
class AdditionTaskGenerator:
    """Create addition tasks from the two configured operand ranges."""

    random_source: IntegerRandomSource

    def generate(self, definition: OperationDefinition) -> ArithmeticTask:
        if definition.operation is not ArithmeticOperation.ADDITION:
            raise ValueError("AdditionTaskGenerator requires an addition definition")

        left = self.random_source.randint(definition.left.minimum, definition.left.maximum)
        right = self.random_source.randint(definition.right.minimum, definition.right.maximum)
        return ArithmeticTask(
            operation=ArithmeticOperation.ADDITION,
            left_operand=left,
            right_operand=right,
            expected_answer=left + right,
        )
