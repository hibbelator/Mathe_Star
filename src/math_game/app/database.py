"""Shared SQLite connection and schema for all durable application data."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppDatabase:
    """Own the local database path and initialise its versioned schema."""

    path: Path = field(default_factory=lambda: Path.home() / ".math_game" / "math_game.sqlite3")

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema(connection)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                image_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS games (
                identifier TEXT PRIMARY KEY,
                definition_json TEXT NOT NULL,
                definition_hash TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS round_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                game_id TEXT NOT NULL,
                game_name TEXT NOT NULL,
                definition_hash TEXT NOT NULL,
                correct INTEGER NOT NULL,
                total INTEGER NOT NULL,
                elapsed_seconds REAL NOT NULL,
                played_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS statistics_comparison
            ON round_statistics(player_id, definition_hash, played_at);
            """
        )
