# Mathe-Abenteuer

`Mathe-Abenteuer` ist der Arbeitstitel für eine neue, testbare Python-Neuimplementierung eines Kopfrechen- und Übungsspiels. Das Repository enthält inzwischen einen ersten durchgehend spielbaren Flet-Durchstich: Übung auswählen, fünf Additions- oder Subtraktionsaufgaben beantworten, direktes Feedback erhalten und die Runde abschließen.

## Ziel dieser Projektphase

Sitzung 3 macht aus dem fachlichen Fundament erstmals ein bedienbares Produktinkrement. Eine kleine, UI-unabhängig getestete Rundensteuerung verbindet die Generatoren mit vier sichtbaren Phasen: Auswahl, Aufgabe, Feedback und Abschluss. Der Schwerpunkt der nächsten Sitzung liegt nicht auf weiteren Rechenarten, sondern auf Spielgefühl, visueller Qualität, Motivation und barrierearmem Feedback.

## Enthalten

- `src`-Layout für das Paket `math_game`.
- Python-Zielversion 3.13.
- Pytest-Konfiguration für Tests unter `tests`.
- Ruff-Konfiguration für Linting und Formatierung.
- Pyright-Konfiguration für statische Typprüfung.
- Dokumentation zu Legacy-Bezug, Spielregeln, Architektur, Entscheidungen und Handover.
- Core-Module für Verträge, Wertobjekte, Game-Definitionen und Clock-Abstraktion.
- Ein präsentationsneutrales Aufgabenmodell und ein Generatorvertrag.
- Generatoren für Addition und Subtraktion als erste vertikale Durchstiche.
- Eine lokal startbare Flet-Oberfläche und eine vollständige Runde mit fünf Aufgaben.
- Direktes Richtig-/Falsch-Feedback, Fortschritt und ein einfacher Abschlussbildschirm.

## Bewusst noch nicht enthalten

- Keine Generatoren für Multiplikation oder Division.
- Keine konkreten State-Machines für Spielmodi.

Diese Begrenzung ist absichtlich: Spätere Sitzungen können dadurch fachliche Funktionen ergänzen, ohne das Fundament neu verhandeln zu müssen.

Spielerprofile, eigene Spieldefinitionen und Rundenergebnisse werden lokal in
`~/.math_game/math_game.sqlite3` gespeichert. Ein Profil besteht aus einem Namen und optional
einem Bildpfad. Statistische Bestleistungen werden über einen Hash der vollständigen
Spielregeln gruppiert; dadurch fließen weder andere Spieler noch nur ähnlich benannte oder
nachträglich veränderte Spiele in einen Vergleich ein.

Direkt nach jeder beendeten Runde erscheint ein Ergebnis-Dashboard mit Score, persönlicher
Bestquote, Durchschnittszeit und Entwicklung. Die aufklappbare Detailansicht ergänzt den
Rundenverlauf und eine Bestenliste. Auch dort bleibt die Vergleichsbasis streng auf dieselbe
Spieldefinition begrenzt, während die persönlichen Kennzahlen nur das aktive Profil betreffen.

## Weg zur ersten Beta

Die weitere Entwicklung ist nicht mehr als Folge einzelner Generatorpakete geplant. Die erste Beta soll in höchstens drei weiteren Sitzungen entstehen: zunächst als vollständig spielbarer Flet-Durchstich, danach mit gezieltem Fokus auf Interaktionsgefühl und motivierendes Feedback und schließlich mit Ergebnispräsentation sowie Stabilisierung. Die konkreten Abnahmekriterien stehen in [`docs/roadmap.md`](docs/roadmap.md).

## Kleines Nutzungsbeispiel

```python
from math_game.core.contracts import ArithmeticOperation
from math_game.core.game_definition import OperationDefinition
from math_game.core.models import OperandRange
from math_game.generators import AdditionTaskGenerator
from math_game.generators.random_source import PythonRandomSource

definition = OperationDefinition(
    operation=ArithmeticOperation.ADDITION,
    left=OperandRange(1, 10),
    right=OperandRange(1, 10),
)
task = AdditionTaskGenerator(PythonRandomSource()).generate(definition)
print(f"{task.prompt} = {task.expected_answer}")
```

Das Beispiel zeigt bewusst nur die Erzeugung. Ob und wann die erwartete Lösung angezeigt wird, ist später Aufgabe einer Oberfläche beziehungsweise einer Spielmodus-Steuerung.

Für eine Subtraktion wird entsprechend `SubtractionTaskGenerator` importiert. Falls negative Ergebnisse nicht erlaubt sind, schränkt er die Ziehbereiche vorab so ein, dass stets `left_operand >= right_operand` gilt. Sind die angegebenen Bereiche dafür unvereinbar, wird sofort ein `ValueError` ausgelöst; der Generator versucht nicht, durch eine möglicherweise endlose Wiederholung zufällig doch eine gültige Aufgabe zu finden.

## Entwicklung

Das Projekt wird mit den Entwicklungsabhängigkeiten installiert und anschließend über das registrierte Kommando gestartet:

```bash
python -m pip install -e .
math-game
```

Alternativ kann die App direkt als Modul gestartet werden:

```bash
python -m math_game.app.flet_app
```

Die automatisierten Prüfungen bleiben:

```bash
python -m pytest
python -m ruff check .
python -m pyright
```

Falls die Werkzeuge noch nicht installiert sind, können sie über die Entwicklungsabhängigkeiten aus `pyproject.toml` bereitgestellt werden.
