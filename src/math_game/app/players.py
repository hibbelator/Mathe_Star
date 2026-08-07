"""Player profiles stored in the shared SQLite database."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from math_game.app.database import AppDatabase


@dataclass(frozen=True, slots=True)
class Player:
    id: int
    name: str
    image_path: str | None = None


@dataclass(slots=True)
class PlayerRepository:
    database: AppDatabase = field(default_factory=AppDatabase)

    def all(self) -> list[Player]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, image_path FROM players ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [Player(int(row["id"]), str(row["name"]), row["image_path"]) for row in rows]

    def add(self, name: str, image_path: str | Path | None = None) -> Player:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Der Spielername darf nicht leer sein.")
        normalized_image = str(image_path).strip() if image_path else None
        with self.database.connect() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO players(name, image_path) VALUES (?, ?)",
                    (normalized_name, normalized_image),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("Diesen Spielernamen gibt es bereits.") from error
            player_id = cursor.lastrowid
        if player_id is None:
            raise RuntimeError("Spieler konnte nicht gespeichert werden.")
        return Player(player_id, normalized_name, normalized_image)
