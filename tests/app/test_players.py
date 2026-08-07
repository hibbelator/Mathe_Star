from pathlib import Path

import pytest

from math_game.app.database import AppDatabase
from math_game.app.players import PlayerRepository


def test_player_with_optional_image_is_persisted(tmp_path: Path) -> None:
    repository = PlayerRepository(AppDatabase(tmp_path / "app.sqlite3"))

    player = repository.add(" Lina ", tmp_path / "lina.png")

    assert repository.all() == [player]
    assert player.name == "Lina"
    assert player.image_path == str(tmp_path / "lina.png")


def test_player_names_are_unique_ignoring_case(tmp_path: Path) -> None:
    repository = PlayerRepository(AppDatabase(tmp_path / "app.sqlite3"))
    repository.add("Lina")

    with pytest.raises(ValueError, match="bereits"):
        repository.add("lina")
