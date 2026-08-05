from dataclasses import replace

import pytest

from math_game.core.contracts import AnswerStatus, ArithmeticOperation, EndReason, GameMode
from math_game.core.game_definition import (
    ComboRules,
    ComboThreshold,
    GameDefinition,
    GamePresentation,
    OperationWeights,
)
from math_game.core.models import (
    GameSessionResult,
    MathTask,
    ResultSummary,
    TaskAttempt,
    canonical_json,
    normalize_for_hash,
)


def plus_minus_definition(**overrides: object) -> GameDefinition:
    values: dict[str, object] = {
        "id": "",
        "mode_key": GameMode.TIME_ATTACK,
        "rules_version": 1,
        "generator_version": 1,
        "operation_weights": OperationWeights(addition=100, subtraction=100),
        "allowed_tables": (),
        "factor_min": 3,
        "factor_max": 9,
        "add_sub_max_result": 20,
        "missing_positions": (1, 2, 3),
        "total_time_seconds": 60.0,
        "per_task_time_seconds": None,
        "task_count": None,
        "correct_target": None,
        "penalty_seconds": 0.0,
        "combo_rules": None,
    }
    values.update(overrides)
    return GameDefinition(**values)  # type: ignore[arg-type]


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


def test_answer_status_contract_matches_masterplan_values() -> None:
    assert [status.value for status in AnswerStatus] == [
        "correct",
        "wrong_result",
        "no_input",
        "timeout",
        "cancelled",
    ]


def test_mode_contract_matches_target_mode_keys() -> None:
    assert {mode.value for mode in GameMode} == {
        "time_attack",
        "task_sprint",
        "perfect_run",
        "target_hunt",
        "per_task_timer",
        "combo",
    }


def test_definition_hash_is_stable_for_equivalent_definition() -> None:
    first = plus_minus_definition()
    second = plus_minus_definition(id=first.id)

    assert first.definition_hash() == second.definition_hash()
    assert first.definition_hash().algorithm == "sha256"
    assert len(first.definition_hash().value) == 64


def test_definition_rejects_mismatching_id() -> None:
    with pytest.raises(ValueError, match="id must match"):
        plus_minus_definition(id="not-the-real-hash")


def test_definition_hash_ignores_presentation_data() -> None:
    definition = plus_minus_definition()
    first_presentation = GamePresentation(
        display_name="Plus und Minus bis 20",
        visual_theme="rocket_blue",
        is_favorite=True,
        sort_order=1,
    )
    second_presentation = GamePresentation(
        display_name="Neuer Name",
        visual_theme="rocket_red",
        is_favorite=False,
        sort_order=99,
    )

    assert first_presentation != second_presentation
    assert definition.id == plus_minus_definition(id=definition.id).id


def test_definition_hash_changes_when_number_space_changes() -> None:
    base = plus_minus_definition()
    changed = plus_minus_definition(add_sub_max_result=30)

    assert base.id != changed.id


def test_definition_hash_changes_when_time_changes() -> None:
    base = plus_minus_definition()
    changed = plus_minus_definition(total_time_seconds=120.0)

    assert base.id != changed.id


def test_definition_hash_changes_when_penalty_is_relevant() -> None:
    base = plus_minus_definition(
        mode_key=GameMode.TASK_SPRINT,
        total_time_seconds=999.0,
        task_count=20,
        penalty_seconds=2.0,
    )
    changed = plus_minus_definition(
        mode_key=GameMode.TASK_SPRINT,
        total_time_seconds=999.0,
        task_count=20,
        penalty_seconds=5.0,
    )

    assert base.id != changed.id


def test_irrelevant_unused_total_time_does_not_change_task_sprint_hash() -> None:
    first = plus_minus_definition(
        mode_key=GameMode.TASK_SPRINT,
        total_time_seconds=60.0,
        task_count=20,
        penalty_seconds=2.0,
    )
    second = plus_minus_definition(
        mode_key=GameMode.TASK_SPRINT,
        total_time_seconds=999.0,
        task_count=20,
        penalty_seconds=2.0,
    )

    assert first.id == second.id
    assert first.normalized_payload()["total_time_seconds"] is None


def test_definition_hash_changes_when_generator_version_changes() -> None:
    base = plus_minus_definition()
    changed = plus_minus_definition(generator_version=2)

    assert base.id != changed.id


def test_definition_validates_allowed_tables_for_multiplication() -> None:
    with pytest.raises(ValueError, match="allowed_tables"):
        plus_minus_definition(
            operation_weights=OperationWeights(multiplication=1),
            allowed_tables=(),
        )


def test_combo_definition_requires_combo_rules_and_hashes_thresholds() -> None:
    combo = plus_minus_definition(
        mode_key=GameMode.COMBO,
        operation_weights=OperationWeights(multiplication=1),
        allowed_tables=(3, 4, 5),
        task_count=30,
        total_time_seconds=123.0,
        combo_rules=ComboRules(
            base_points=100,
            thresholds=(
                ComboThreshold(1, 1),
                ComboThreshold(5, 2),
                ComboThreshold(10, 3),
                ComboThreshold(15, 4),
            ),
        ),
    )
    changed = replace(combo, id="", combo_rules=ComboRules(base_points=200))

    assert combo.id != changed.id
    assert combo.normalized_payload()["total_time_seconds"] is None


def test_result_summary_enforces_attempt_count_invariant() -> None:
    ResultSummary(
        attempt_count=3,
        correct_count=1,
        wrong_count=1,
        no_input_count=1,
        timeout_count=0,
        elapsed_seconds=10.0,
        penalty_seconds=2.0,
        effective_seconds=12.0,
    )

    with pytest.raises(ValueError, match="attempt_count"):
        ResultSummary(
            attempt_count=4,
            correct_count=1,
            wrong_count=1,
            no_input_count=1,
            timeout_count=0,
            elapsed_seconds=10.0,
            penalty_seconds=2.0,
            effective_seconds=12.0,
        )


def test_task_attempt_and_session_result_contracts_are_immutable() -> None:
    task = MathTask(
        task_id="task-1",
        sequence_number=1,
        operation=ArithmeticOperation.ADDITION,
        operand_left=5,
        operand_right=7,
        result=12,
        missing_position=3,
        displayed_task="5 + 7 = ___",
        expected_answer=12,
    )
    attempt = TaskAttempt(
        task=task,
        entered_answer=12,
        status=AnswerStatus.CORRECT,
        response_time_seconds=1.5,
        event_time_monotonic=42.0,
        streak_after=1,
        points=100,
    )
    summary = ResultSummary(
        attempt_count=1,
        correct_count=1,
        wrong_count=0,
        no_input_count=0,
        timeout_count=0,
        elapsed_seconds=1.5,
        penalty_seconds=0.0,
        effective_seconds=1.5,
        score=100,
        longest_streak=1,
    )
    from datetime import UTC, datetime

    result = GameSessionResult(
        session_id="session-1",
        game_definition_id=plus_minus_definition().id,
        mode_key=GameMode.TIME_ATTACK.value,
        started_at_utc=datetime(2026, 8, 5, tzinfo=UTC),
        finished_at_utc=datetime(2026, 8, 5, 0, 0, 2, tzinfo=UTC),
        end_reason=EndReason.COMPLETED,
        summary=summary,
        attempts=(attempt,),
        random_seed=123,
    )

    assert result.attempts == (attempt,)
    assert result.result_schema_version == 1
