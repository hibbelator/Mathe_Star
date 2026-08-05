# Mathe-Abenteuer

`Mathe-Abenteuer` ist der Arbeitstitel für eine neue, testbare Python-Neuimplementierung eines Kopfrechen- und Übungsspiels. Dieses Repository enthält in Sitzung 1A/1B bewusst nur das Fundament: Projektkonfiguration, Dokumentation, stabile Core-Verträge und Tests für deterministische Normalisierung sowie Definition-Hashes.

## Ziel dieser Projektphase

Die erste Scheibe erzeugt noch kein spielbares Produkt. Stattdessen werden die Begriffe festgelegt, gegen die spätere Generatoren, Spielmodi, Oberflächen und Persistenzschichten implementiert werden können. Der Core beschreibt, was eine Spieldefinition ist, welche Rechenarten und Statuswerte erlaubt sind und wie Vergleichbarkeit über einen stabilen Hash entsteht.

## Enthalten

- `src`-Layout für das Paket `math_game`.
- Python-Zielversion 3.13.
- Pytest-Konfiguration für Tests unter `tests`.
- Ruff-Konfiguration für Linting und Formatierung.
- Pyright-Konfiguration für statische Typprüfung.
- Dokumentation zu Legacy-Bezug, Spielregeln, Architektur, Entscheidungen und Handover.
- Core-Module für Verträge, Wertobjekte, Game-Definitionen und Clock-Abstraktion.

## Bewusst noch nicht enthalten

- Keine Flet-App und kein UI-Code.
- Keine SQLite-Persistenz.
- Keine Generatorimplementierung.
- Keine konkreten State-Machines für Spielmodi.

Diese Begrenzung ist absichtlich: Spätere Sitzungen können dadurch fachliche Funktionen ergänzen, ohne das Fundament neu verhandeln zu müssen.

## Entwicklung

```bash
python -m pytest
python -m ruff check .
python -m pyright
```

Falls die Werkzeuge noch nicht installiert sind, können sie über die Entwicklungsabhängigkeiten aus `pyproject.toml` bereitgestellt werden.
