"""Shared SQLite connection and schema for all durable application data."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = 2


def default_data_directory() -> Path:
    """Return Flet's private application directory, with a desktop fallback."""

    app_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    return Path(app_storage) if app_storage else Path.home() / ".math_game"


@dataclass(frozen=True, slots=True)
class AppDatabase:
    """Own the local database path and initialise its versioned schema."""

    path: Path = field(default_factory=lambda: default_data_directory() / "math_game.sqlite3")

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
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version > SCHEMA_VERSION:
            raise RuntimeError(
                f"database schema {current_version} is newer than supported {SCHEMA_VERSION}"
            )
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
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
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
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(round_statistics)")}
        if "events_json" not in columns:
            connection.execute(
                "ALTER TABLE round_statistics ADD COLUMN events_json TEXT NOT NULL DEFAULT '[]'"
            )
        if "score_value" not in columns:
            connection.execute("ALTER TABLE round_statistics ADD COLUMN score_value INTEGER")
        if "event_schema_version" not in columns:
            # Existing JSON rows have the compact v1 structure.  Keeping that fact
            # explicit lets rule-specific replay reject them instead of guessing.
            connection.execute(
                "ALTER TABLE round_statistics "
                "ADD COLUMN event_schema_version INTEGER NOT NULL DEFAULT 1"
            )
        player_columns = {row["name"] for row in connection.execute("PRAGMA table_info(players)")}
        if "icon" not in player_columns:
            connection.execute("ALTER TABLE players ADD COLUMN icon TEXT NOT NULL DEFAULT '🙂'")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
