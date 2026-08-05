# Verbindliche Spielregeln

Dieses Dokument beschreibt die fachlichen Zielregeln, die ab Sitzung 1 gelten. Es implementiert noch keinen Generator und keinen Modusablauf, sondern legt die später einzuhaltenden Verträge fest.

## Rechenarten

Zulässige Rechenarten sind:

1. Addition
2. Subtraktion
3. Multiplikation
4. Division

Jede Rechenart wird über eine Operationdefinition mit linkem und rechtem Operandenbereich beschrieben. Zusätzliche Eigenschaften wie negative Ergebnisse oder Divisionen mit Rest sind Teil der Definition und damit hashrelevant.

## Antwortstatus

Jede Aufgabe besitzt genau einen kanonischen Antwortstatus:

- `unanswered`: Es liegt noch keine Antwort vor.
- `correct`: Die gegebene Antwort entspricht der erwarteten Antwort.
- `incorrect`: Die gegebene Antwort ist fachlich falsch.
- `skipped`: Die Aufgabe wurde bewusst übersprungen.
- `timeout`: Die Aufgabe wurde durch Zeitablauf beendet.

## Spielmodi

Für Sitzung 1 werden Spielmodi nur als Vertragsnamen modelliert:

- `practice`
- `timed`
- `fixed_tasks`
- `mistake_review`

Die konkrete Ablaufsteuerung dieser Modi ist ausdrücklich nicht Bestandteil von Verification Gate 1A.

## Vergleichbarkeit

Zwei Ergebnisse sind nur dann direkt vergleichbar, wenn sie auf derselben normalisierten Spieldefinition beruhen. Der Definitions-Hash wird aus dem kanonischen JSON der Definition gebildet. Dadurch sind Vergleiche unabhängig von Python-Objektidentitäten, Prozesszustand oder Dictionary-Reihenfolgen.
