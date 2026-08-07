from pathlib import Path

import pytest

from math_game.app.database import AppDatabase
from math_game.core.contracts import GameMode
from math_game.core.presets import EXCEL_PRESETS, DefinedGame, GameRepository, OperationWeights


def test_excel_presets_contain_reference_names_and_values() -> None:
    assert [game.name for game in EXCEL_PRESETS] == [
        "Anfänger",
        "Mama Zettel",
        "1er",
        "PluMi",
        "PluMi_1Kl",
        "Mama Zettel2",
        "MiLi",
    ]
    beginner = EXCEL_PRESETS[0]
    assert beginner.weights == OperationWeights(1, 1, 1, 1)
    assert beginner.allowed_tables == tuple(range(3, 20))
    assert beginner.duration_seconds == 300


def test_weights_require_a_non_negative_active_operation() -> None:
    with pytest.raises(ValueError):
        OperationWeights()
    with pytest.raises(ValueError):
        OperationWeights(addition=-1)


def test_repository_round_trip_and_replace(tmp_path: Path) -> None:
    repository = GameRepository(AppDatabase(tmp_path / "games.sqlite3"))
    game = DefinedGame(
        "mein-spiel",
        "Mein Spiel",
        OperationWeights(addition=1),
        (),
        2,
        10,
        20,
        GameMode.TASK_SPRINT,
        task_count=10,
    )
    repository.save(game)
    replacement = DefinedGame(
        "mein-spiel", "Neuer Name", OperationWeights(subtraction=1), (), 2, 10, 20, task_count=5
    )
    repository.save(replacement)

    assert repository.custom_games() == [replacement]
    assert len(repository.all_games()) == len(EXCEL_PRESETS) + 1


def test_multiplication_needs_tables() -> None:
    with pytest.raises(ValueError, match="Reihe"):
        DefinedGame("invalid", "Ungültig", OperationWeights(multiplication=1), (), 2, 10, 100)


def test_wrong_answer_penalty_is_part_of_definition_and_must_not_be_positive() -> None:
    base = DefinedGame("base", "Basis", OperationWeights(addition=1), (), 2, 10, 20)
    penalized = DefinedGame(
        "penalty",
        "Basis",
        OperationWeights(addition=1),
        (),
        2,
        10,
        20,
        wrong_answer_penalty=-1,
    )

    assert base.wrong_answer_penalty == 0
    assert base.definition_hash() != penalized.definition_hash()
    with pytest.raises(ValueError, match="negative"):
        DefinedGame(
            "invalid-penalty",
            "Ungültig",
            OperationWeights(addition=1),
            (),
            2,
            10,
            20,
            wrong_answer_penalty=1,
        )
