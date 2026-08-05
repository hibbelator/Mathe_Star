# Handover nach Verification Gate 1A

## Aktueller Stand

Der nächste größere Schritt wurde erledigt: Die Core-Domainmodelle und Verträge wurden an den verbindlichen Masterplan angepasst. Die alten Platzhalterbegriffe wie `practice`, `timed`, `incorrect` und `skipped` sind aus den zentralen Verträgen entfernt. Stattdessen verwendet der Core jetzt die Zielmodus-Keys und Antwortstatuswerte aus dem Masterplan.

Die `GameDefinition` bildet nun die fachlich vergleichsrelevanten Einstellungen ab: Modus, Regel- und Generatorversion, Rechenart-Gewichte, erlaubte Reihen, Faktorgrenzen, Additions-/Subtraktionsobergrenze, gesuchte Positionen, Zeit- und Zielparameter, Strafsekunden und optionale Combo-Regeln. Präsentationsdaten liegen in `GamePresentation` und beeinflussen den Hash nicht.

Die Hashbildung normalisiert den fachlich relevanten Payload. Nicht verwendete Modusfelder werden kanonisch ausgeblendet, damit beispielsweise ein alter `total_time_seconds`-Wert bei einem Aufgaben-Sprint den Hash nicht verändert. Eine nicht leere manuell gesetzte `id` muss zum berechneten Hash passen; andernfalls wird die Definition abgelehnt.

## Geänderte Dateien

- `src/math_game/core/contracts.py`
- `src/math_game/core/game_definition.py`
- `src/math_game/core/models.py`
- `tests/core/test_game_definition_hash.py`
- `docs/PROJECT_PLAN.md`
- `docs/HANDOVER.md`

## Ausgeführte Checks

```bash
python -m ruff format .
python -m ruff check .
python -m pyright
python -m pytest
```

Ergebnis: Alle Checks erfolgreich. `pytest` meldete `15 passed`.

## Architekturstatus

Verification Gate 1A ist aus Umsetzungssicht erreicht:

- Domain-Modelle vorhanden.
- Antwortstatuswerte an Masterplan angepasst.
- Zielmodus-Keys an Masterplan angepasst.
- `GameDefinition`-Normalisierung und SHA-256-ID vorhanden.
- Präsentationsdaten vom Hash getrennt.
- Standardisierte Ergebnisverträge vorhanden.
- Tests für zentrale Hash- und Vertragsregeln vorhanden.

Weiterhin bewusst nicht umgesetzt:

- kein Generator,
- keine Generatorvalidierung,
- keine konkrete Spielmodus-State-Machine,
- keine Datenbank,
- keine Flet-UI,
- kein Android-Build.

## Bekannte Einschränkungen

Die Validierung der Rechenregeln ist noch nicht vollständig. Generator-spezifische Bedingungen wie `add_sub_max_result >= 2 * factor_min` für Addition oder `add_sub_max_result - 1 >= factor_min` für Subtraktion sind dokumentiert, werden aber erst mit Generatorversion 1 und der Validierungsschicht umgesetzt.

Die `GameSessionResult`-, `MathTask`- und `TaskAttempt`-Modelle sind Ergebnis- und Austauschverträge. Sie erzeugen noch keine Aufgaben und führen noch keine State-Machine aus.

## Nächster Einstiegspunkt

Vor dem nächsten Codex-Schritt sollte Gate 1A fachlich freigegeben werden. Nach Freigabe ist der nächste Umsetzungsschritt Generatorversion 1 inklusive Konfigurationsvalidierung. Danach darf `time_attack` als isolierte headless State-Machine folgen.
