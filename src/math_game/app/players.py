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
    icon: str = "🙂"


@dataclass(slots=True)
class PlayerRepository:
    database: AppDatabase = field(default_factory=AppDatabase)

    def all(self) -> list[Player]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, image_path, icon FROM players ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [
            Player(int(row["id"]), str(row["name"]), row["image_path"], str(row["icon"]))
            for row in rows
        ]

    def add(self, name: str, image_path: str | Path | None = None, icon: str = "🙂") -> Player:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Der Spielername darf nicht leer sein.")
        normalized_image = str(image_path).strip() if image_path else None
        normalized_icon = icon.strip() or "🙂"
        if len(normalized_icon) > 8:
            raise ValueError("Bitte wähle ein einzelnes Spielericon aus.")
        with self.database.connect() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO players(name, image_path, icon) VALUES (?, ?, ?)",
                    (normalized_name, normalized_image, normalized_icon),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("Diesen Spielernamen gibt es bereits.") from error
            player_id = cursor.lastrowid
        if player_id is None:
            raise RuntimeError("Spieler konnte nicht gespeichert werden.")
        player = Player(player_id, normalized_name, normalized_image, normalized_icon)
        self.remember(player.id)
        return player

    def last_used(self) -> Player | None:
        """Restore the profile that was active when the app was last used."""

        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT p.id, p.name, p.image_path, p.icon FROM players AS p
                   JOIN app_settings AS s ON s.value = CAST(p.id AS TEXT)
                   WHERE s.key = 'last_player_id'"""
            ).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT id, name, image_path, icon FROM players ORDER BY id DESC LIMIT 1"
                ).fetchone()
        return (
            None
            if row is None
            else Player(int(row["id"]), str(row["name"]), row["image_path"], str(row["icon"]))
        )

    def remember(self, player_id: int) -> None:
        with self.database.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM players WHERE id = ?", (player_id,)
            ).fetchone()
            if exists is None:
                raise ValueError("Der ausgewählte Spieler existiert nicht.")
            connection.execute(
                """INSERT INTO app_settings(key, value) VALUES ('last_player_id', ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (str(player_id),),
            )
