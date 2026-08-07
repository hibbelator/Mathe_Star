"""Excel-compatible game definitions and local custom-game persistence."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import cast

from math_game.app.database import AppDatabase
from math_game.core.contracts import GameMode
from math_game.core.models import DefinitionHash


@dataclass(frozen=True, slots=True)
class OperationWeights:
    """Relative probabilities for the four arithmetic operations."""

    addition: int = 0
    subtraction: int = 0
    multiplication: int = 0
    division: int = 0

    def __post_init__(self) -> None:
        values = (self.addition, self.subtraction, self.multiplication, self.division)
        if any(value < 0 for value in values):
            raise ValueError("Rechenarten-Gewichte dürfen nicht negativ sein.")
        if not any(values):
            raise ValueError("Mindestens eine Rechenart muss aktiviert sein.")


@dataclass(frozen=True, slots=True)
class DefinedGame:
    """Complete, editable equivalent of one Excel game row and its mode values."""

    identifier: str
    name: str
    weights: OperationWeights
    allowed_tables: tuple[int, ...]
    factor_min: int
    factor_max: int
    max_result: int
    mode: GameMode = GameMode.TIME_ATTACK
    duration_seconds: int | None = 300
    task_count: int | None = 130
    per_task_seconds: int | None = 30
    correct_target: int | None = 40
    builtin: bool = False

    def __post_init__(self) -> None:
        if not self.identifier.strip() or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", self.identifier):
            raise ValueError("Die Kennung darf nur Kleinbuchstaben, Zahlen, _ und - enthalten.")
        if not self.name.strip():
            raise ValueError("Der Spielname darf nicht leer sein.")
        if self.factor_min <= 0 or self.factor_max < self.factor_min:
            raise ValueError("Der Faktorbereich ist ungültig.")
        if self.max_result < self.factor_min:
            raise ValueError("Das maximale Ergebnis ist zu klein.")
        if self.weights.addition and self.max_result < 2 * self.factor_min:
            raise ValueError("Für Addition muss MaxErg mindestens zweimal Min-Faktor sein.")
        if any(table <= 0 for table in self.allowed_tables):
            raise ValueError("Reihen müssen positive ganze Zahlen sein.")
        if (self.weights.multiplication or self.weights.division) and not self.allowed_tables:
            raise ValueError(
                "Für Multiplikation oder Division muss mindestens eine Reihe erlaubt sein."
            )
        for value in (
            self.duration_seconds,
            self.task_count,
            self.per_task_seconds,
            self.correct_target,
        ):
            if value is not None and value <= 0:
                raise ValueError("Moduswerte müssen positiv sein.")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        data = asdict(self)
        data["mode"] = self.mode.value
        data["allowed_tables"] = list(self.allowed_tables)
        return data

    def definition_hash(self) -> str:
        """Identify the complete playable rules, independently of display name."""

        payload = self.to_dict()
        for presentation_field in ("identifier", "name", "builtin"):
            payload.pop(presentation_field)
        return DefinitionHash.from_payload(payload).as_uri()

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DefinedGame:
        """Validate and construct a game loaded from JSON."""

        weights = data.get("weights")
        if not isinstance(weights, dict):
            raise ValueError("Ungültige Rechenarten-Gewichte.")
        raw_tables = data.get("allowed_tables", [])
        if not isinstance(raw_tables, list):
            raise ValueError("Ungültige Liste erlaubter Reihen.")
        typed_weights = cast(dict[str, int], weights)
        typed_tables = cast(list[object], raw_tables)
        return cls(
            identifier=str(data["identifier"]),
            name=str(data["name"]),
            weights=OperationWeights(**typed_weights),
            allowed_tables=tuple(_required_int(value) for value in typed_tables),
            factor_min=_required_int(data["factor_min"]),
            factor_max=_required_int(data["factor_max"]),
            max_result=_required_int(data["max_result"]),
            mode=GameMode(str(data.get("mode", GameMode.TIME_ATTACK.value))),
            duration_seconds=_optional_int(data.get("duration_seconds")),
            task_count=_optional_int(data.get("task_count")),
            per_task_seconds=_optional_int(data.get("per_task_seconds")),
            correct_target=_optional_int(data.get("correct_target")),
            builtin=bool(data.get("builtin", False)),
        )


def _optional_int(value: object) -> int | None:
    return None if value is None else _required_int(value)


def _required_int(value: object) -> int:
    if not isinstance(value, int | str):
        raise ValueError("Ein Zahlenwert in der Spieldefinition ist ungültig.")
    return int(value)


def _preset(
    identifier: str,
    name: str,
    weights: tuple[int, int, int, int],
    tables: range,
    factor_min: int,
    factor_max: int,
    max_result: int,
    minutes: int,
    tasks: int,
) -> DefinedGame:
    return DefinedGame(
        identifier=identifier,
        name=name,
        weights=OperationWeights(*weights),
        allowed_tables=tuple(tables),
        factor_min=factor_min,
        factor_max=factor_max,
        max_result=max_result,
        duration_seconds=minutes * 60,
        task_count=tasks,
        builtin=True,
    )


EXCEL_PRESETS: tuple[DefinedGame, ...] = (
    _preset("anfaenger", "Anfänger", (1, 1, 1, 1), range(3, 20), 3, 20, 1000, 5, 130),
    _preset("mama-zettel", "Mama Zettel", (0, 0, 1, 0), range(3, 10), 2, 10, 100, 1, 100),
    _preset("1er", "1er", (0, 0, 50, 50), range(3, 10), 2, 10, 100, 5, 1),
    _preset("plumi", "PluMi", (100, 100, 0, 0), range(3, 10), 3, 9, 130, 5, 130),
    _preset("plumi_1kl", "PluMi_1Kl", (100, 100, 0, 0), range(3, 10), 3, 9, 20, 5, 130),
    _preset("mama-zettel2", "Mama Zettel2", (0, 0, 100, 100), range(3, 10), 2, 10, 100, 5, 1),
    _preset("mili", "MiLi", (100, 0, 100, 0), range(3, 10), 3, 9, 300, 3, 130),
)


@dataclass(slots=True)
class GameRepository:
    """Combine immutable built-ins with custom definitions stored in SQLite."""

    database: AppDatabase = field(default_factory=AppDatabase)

    def custom_games(self) -> list[DefinedGame]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT definition_json FROM games ORDER BY identifier"
            ).fetchall()
        return [DefinedGame.from_dict(json.loads(str(row["definition_json"]))) for row in rows]

    def all_games(self) -> list[DefinedGame]:
        return [*EXCEL_PRESETS, *self.custom_games()]

    def save(self, game: DefinedGame) -> None:
        if game.builtin:
            raise ValueError("Excel-Presets können nicht überschrieben werden.")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO games(identifier, definition_json, definition_hash)
                   VALUES (?, ?, ?) ON CONFLICT(identifier) DO UPDATE SET
                   definition_json=excluded.definition_json,
                   definition_hash=excluded.definition_hash,
                   updated_at=CURRENT_TIMESTAMP""",
                (
                    game.identifier,
                    json.dumps(game.to_dict(), ensure_ascii=False),
                    game.definition_hash(),
                ),
            )

    def delete(self, identifier: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM games WHERE identifier = ?", (identifier,))
