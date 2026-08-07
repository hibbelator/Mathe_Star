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


def test_last_selected_player_is_restored(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    repository = PlayerRepository(database)
    lina = repository.add("Lina")
    ben = repository.add("Ben")
    repository.remember(lina.id)

    assert PlayerRepository(database).last_used() == lina
    repository.remember(ben.id)
    assert PlayerRepository(database).last_used() == ben


def test_player_icon_is_persisted_and_restored(tmp_path: Path) -> None:
    database = AppDatabase(tmp_path / "app.sqlite3")
    repository = PlayerRepository(database)

    player = repository.add("Lina", icon="🦊")

    assert repository.all()[0].icon == "🦊"
    assert repository.last_used() == player
