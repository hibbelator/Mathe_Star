from dataclasses import dataclass, field

import pytest

from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import OperandRange
from math_game.generators.addition import AdditionTaskGenerator


@dataclass
class StubRandomSource:
    values: list[int]
    calls: list[tuple[int, int]] = field(default_factory=lambda: [])

    def randint(self, minimum: int, maximum: int) -> int:
        self.calls.append((minimum, maximum))
        return self.values.pop(0)


def test_addition_uses_both_ranges_and_calculates_expected_answer() -> None:
    random_source = StubRandomSource(values=[3, 12])
    generator = AdditionTaskGenerator(random_source)
    definition = OperationDefinition(
        operation=ArithmeticOperation.ADDITION,
        left=OperandRange(1, 5),
        right=OperandRange(10, 20),
    )

    task = generator.generate(definition)

    assert random_source.calls == [(1, 5), (10, 20)]
    assert task.left_operand == 3
    assert task.right_operand == 12
    assert task.expected_answer == 15
    assert task.prompt == "3 + 12"


def test_addition_rejects_a_definition_for_another_operation() -> None:
    generator = AdditionTaskGenerator(StubRandomSource(values=[]))
    definition = OperationDefinition(
        operation=ArithmeticOperation.MULTIPLICATION,
        left=OperandRange(1, 5),
        right=OperandRange(1, 5),
    )

    with pytest.raises(ValueError, match="requires an addition definition"):
        generator.generate(definition)
