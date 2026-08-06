"""Second vertical generator slice: integer subtraction."""

from __future__ import annotations

from dataclasses import dataclass

from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.task import ArithmeticTask
from math_game.generators.contracts import IntegerRandomSource


@dataclass(frozen=True, slots=True)
class SubtractionTaskGenerator:
    """Create subtraction tasks while respecting the negative-result rule."""

    random_source: IntegerRandomSource

    def generate(self, definition: OperationDefinition) -> ArithmeticTask:
        if definition.operation is not ArithmeticOperation.SUBTRACTION:
            raise ValueError("SubtractionTaskGenerator requires a subtraction definition")

        if definition.allow_negative_results:
            left = self.random_source.randint(
                definition.left.minimum,
                definition.left.maximum,
            )
            right = self.random_source.randint(
                definition.right.minimum,
                definition.right.maximum,
            )
        else:
            left, right = self._generate_non_negative_operands(definition)

        return ArithmeticTask(
            operation=ArithmeticOperation.SUBTRACTION,
            left_operand=left,
            right_operand=right,
            expected_answer=left - right,
        )

    def _generate_non_negative_operands(
        self,
        definition: OperationDefinition,
    ) -> tuple[int, int]:
        """Select a valid pair directly, without an unbounded retry loop."""

        valid_left_minimum = max(definition.left.minimum, definition.right.minimum)
        if valid_left_minimum > definition.left.maximum:
            raise ValueError("operand ranges cannot produce a non-negative subtraction result")

        left = self.random_source.randint(valid_left_minimum, definition.left.maximum)
        valid_right_maximum = min(definition.right.maximum, left)
        right = self.random_source.randint(definition.right.minimum, valid_right_maximum)
        return left, right
