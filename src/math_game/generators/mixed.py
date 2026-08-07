"""Generator combining addition, subtraction, and multiplication tasks."""

from __future__ import annotations

from dataclasses import dataclass

from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.task import ArithmeticTask
from math_game.generators.addition import AdditionTaskGenerator
from math_game.generators.contracts import IntegerRandomSource, TaskGenerator
from math_game.generators.multiplication import MultiplicationTaskGenerator
from math_game.generators.subtraction import SubtractionTaskGenerator


@dataclass(frozen=True, slots=True)
class MixedTaskGenerator:
    """Select dynamically between addition, subtraction, and multiplication generators."""

    random_source: IntegerRandomSource

    def generate(self, definition: OperationDefinition) -> ArithmeticTask:
        op_choice = self.random_source.randint(1, 3)
        if op_choice == 1:
            generator: TaskGenerator = AdditionTaskGenerator(self.random_source)
            target_op = ArithmeticOperation.ADDITION
        elif op_choice == 2:
            generator = SubtractionTaskGenerator(self.random_source)
            target_op = ArithmeticOperation.SUBTRACTION
        else:
            generator = MultiplicationTaskGenerator(self.random_source)
            target_op = ArithmeticOperation.MULTIPLICATION

        op_def = OperationDefinition(
            operation=target_op,
            left=definition.left,
            right=definition.right,
            allow_negative_results=False,
        )
        return generator.generate(op_def)
