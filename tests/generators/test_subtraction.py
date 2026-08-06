from dataclasses import dataclass, field

import pytest

from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import OperandRange
from math_game.generators.subtraction import SubtractionTaskGenerator

DEFAULT_RANGE = OperandRange(1, 10)


@dataclass
class StubRandomSource:
    values: list[int]
    calls: list[tuple[int, int]] = field(default_factory=lambda: [])

    def randint(self, minimum: int, maximum: int) -> int:
        self.calls.append((minimum, maximum))
        return self.values.pop(0)


def subtraction_definition(
    *,
    left: OperandRange = DEFAULT_RANGE,
    right: OperandRange = DEFAULT_RANGE,
    allow_negative_results: bool = False,
) -> OperationDefinition:
    return OperationDefinition(
        operation=ArithmeticOperation.SUBTRACTION,
        left=left,
        right=right,
        allow_negative_results=allow_negative_results,
    )


def test_subtraction_constrains_both_draws_when_result_must_not_be_negative() -> None:
    random_source = StubRandomSource(values=[6, 4])
    generator = SubtractionTaskGenerator(random_source)

    task = generator.generate(
        subtraction_definition(
            left=OperandRange(1, 8),
            right=OperandRange(3, 10),
        )
    )

    assert random_source.calls == [(3, 8), (3, 6)]
    assert task.left_operand == 6
    assert task.right_operand == 4
    assert task.expected_answer == 2
    assert task.prompt == "6 − 4"


def test_subtraction_draws_independently_when_negative_results_are_allowed() -> None:
    random_source = StubRandomSource(values=[2, 7])
    generator = SubtractionTaskGenerator(random_source)

    task = generator.generate(
        subtraction_definition(
            left=OperandRange(1, 3),
            right=OperandRange(5, 9),
            allow_negative_results=True,
        )
    )

    assert random_source.calls == [(1, 3), (5, 9)]
    assert task.expected_answer == -5


def test_subtraction_rejects_ranges_without_a_non_negative_pair() -> None:
    random_source = StubRandomSource(values=[])
    generator = SubtractionTaskGenerator(random_source)

    with pytest.raises(ValueError, match="cannot produce a non-negative"):
        generator.generate(
            subtraction_definition(
                left=OperandRange(1, 2),
                right=OperandRange(3, 4),
            )
        )

    assert random_source.calls == []


def test_subtraction_accepts_a_single_non_negative_boundary_pair() -> None:
    random_source = StubRandomSource(values=[2, 2])
    generator = SubtractionTaskGenerator(random_source)

    task = generator.generate(
        subtraction_definition(
            left=OperandRange(2, 2),
            right=OperandRange(2, 4),
        )
    )

    assert random_source.calls == [(2, 2), (2, 2)]
    assert task.expected_answer == 0


def test_subtraction_rejects_a_definition_for_another_operation() -> None:
    generator = SubtractionTaskGenerator(StubRandomSource(values=[]))
    definition = OperationDefinition(
        operation=ArithmeticOperation.ADDITION,
        left=OperandRange(1, 5),
        right=OperandRange(1, 5),
    )

    with pytest.raises(ValueError, match="requires a subtraction definition"):
        generator.generate(definition)
