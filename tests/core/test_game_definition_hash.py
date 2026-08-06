from math_game.core.contracts import ArithmeticOperation, GameMode
from math_game.core.game_definition import GameDefinition, OperationDefinition
from math_game.core.models import OperandRange, canonical_json, normalize_for_hash


def test_normalization_sorts_mapping_keys_and_serializes_enums() -> None:
    payload = {
        "z": ArithmeticOperation.ADDITION,
        "a": {"b": 2, "a": 1},
        "tuple": (3, 4),
    }

    assert normalize_for_hash(payload) == {
        "a": {"a": 1, "b": 2},
        "tuple": [3, 4],
        "z": "addition",
    }
    assert canonical_json(payload) == '{"a":{"a":1,"b":2},"tuple":[3,4],"z":"addition"}'


def test_definition_hash_is_stable_for_equivalent_metadata_order() -> None:
    operation = OperationDefinition(
        operation=ArithmeticOperation.MULTIPLICATION,
        left=OperandRange(1, 10),
        right=OperandRange(1, 10),
    )
    first = GameDefinition(
        identifier="times-small",
        title="Small multiplication",
        operations=(operation,),
        mode=GameMode.FIXED_TASKS,
        task_count=20,
        metadata={"level": "1", "source": "masterplan"},
    )
    second = GameDefinition(
        identifier="times-small",
        title="Small multiplication",
        operations=(operation,),
        mode=GameMode.FIXED_TASKS,
        task_count=20,
        metadata={"source": "masterplan", "level": "1"},
    )

    assert first.definition_hash() == second.definition_hash()
    assert first.definition_hash().algorithm == "sha256"
    assert len(first.definition_hash().value) == 64


def test_definition_hash_changes_when_definition_changes() -> None:
    operation = OperationDefinition(
        operation=ArithmeticOperation.ADDITION,
        left=OperandRange(1, 5),
        right=OperandRange(1, 5),
    )
    base = GameDefinition(
        identifier="add-small",
        title="Small addition",
        operations=(operation,),
        mode=GameMode.PRACTICE,
    )
    changed = GameDefinition(
        identifier="add-small",
        title="Small addition",
        operations=(operation,),
        mode=GameMode.PRACTICE,
        task_count=10,
    )

    assert base.definition_hash() != changed.definition_hash()


def test_definition_copies_metadata_to_keep_its_hash_stable() -> None:
    metadata = {"level": "1"}
    definition = GameDefinition(
        identifier="add-small",
        title="Small addition",
        operations=(
            OperationDefinition(
                operation=ArithmeticOperation.ADDITION,
                left=OperandRange(1, 5),
                right=OperandRange(1, 5),
            ),
        ),
        mode=GameMode.PRACTICE,
        metadata=metadata,
    )
    original_hash = definition.definition_hash()

    metadata["level"] = "2"

    assert definition.metadata == {"level": "1"}
    assert definition.definition_hash() == original_hash
