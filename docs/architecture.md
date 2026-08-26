# Architektur

## Feature-Slicing

Die Entwicklung erfolgt entlang vertikaler, überprüfbarer Scheiben. Sitzung 1 war eine reine Fundament-Scheibe: Dokumentation, Projektstruktur, Domain-Verträge, Normalisierung und Hashbildung. Sitzung 2A ergänzte darauf den ersten ausführbaren Durchstich für Addition. Sitzung 2B prüft dieselbe Grenze mit Subtraktion und macht dabei erstmals eine fachliche Einschränkung der gültigen Ergebnismenge wirksam.

Ab Sitzung 3 wird vertikal durch das Produkt statt horizontal durch weitere Rechenarten geschnitten. Eine Scheibe umfasst deshalb Oberfläche, minimale Orchestrierung, bestehende Generatoren und automatisierte Prüfung gemeinsam. Das Ziel ist eine erste Beta nach höchstens drei weiteren Sitzungen. Zusätzliche Abstraktionen oder Rechenarten werden nur vorgezogen, wenn sie für den sichtbaren Beta-Pfad erforderlich sind.

## UI- und Anwendungsverantwortung

Die Flet-Oberfläche darf Core-Modelle lesen und Aktionen an eine kleine Anwendungssteuerung weiterreichen, aber keine Rechenergebnisse selbst bestimmen. Die Anwendungssteuerung verwaltet den Ablauf einer Runde, während Widgets Darstellung, Fokus und Eingabe verantworten. Diese Trennung ermöglicht schnelle visuelle Iteration, ohne das UI durch eine vorzeitig allgemeine Modus- oder Plugin-Architektur auszubremsen.

Für die Beta ist ein klarer, expliziter Ablauf wertvoller als eine universelle State-Machine. Erst wenn mindestens zwei tatsächlich unterschiedliche Abläufe existieren, soll eine gemeinsame Modusabstraktion aus dem beobachteten Bedarf herausgezogen werden.

Sitzung 3 setzt diese Grenze mit `RoundSession` konkret um. Die Klasse kennt ausschließlich die vier für den sichtbaren Durchstich benötigten Phasen `ready`, `task`, `feedback` und `finished`. Sie validiert Eingaben, zeichnet Ergebnisse auf und steuert den Aufgabenwechsel, importiert aber kein Flet. Der Flet-Adapter rendert den Zustand und leitet Benutzerereignisse weiter. Dadurch bleibt der Ablauf ohne grafische Laufzeit schnell testbar, während die Oberfläche in Sitzung 4 frei gestaltet werden kann.

## Core-Verantwortung

Der Core ist für die stabile Sprache der Domäne verantwortlich:

- Rechenarten und Antwortstatus als kanonische Werte.
- Spieldefinitionen als unveränderliche Verträge.
- Normalisierung und Definition-Hash für Vergleichbarkeit.
- Uhrzeit-Zugriff nur über ein Protokoll, damit Fachlogik testbar bleibt.

Der Core speichert keine Daten und kennt keine Benutzeroberfläche. Er stellt mit `ArithmeticTask` lediglich das unveränderliche Ergebnis einer Generierung bereit. Die Erzeugungslogik selbst liegt außerhalb des Core im Paket `math_game.generators`.

## Generatorgrenze

Ein Generator nimmt eine einzelne `OperationDefinition` entgegen und liefert eine vollständig aufgelöste `ArithmeticTask`. Zufall wird über das schmale Protokoll `IntegerRandomSource` injiziert. Der produktive Adapter kapselt eine eigene Instanz von `random.Random`; Tests können stattdessen eine vorhersagbare Quelle verwenden. So hängen weder Tests noch spätere Wiederholungsfunktionen vom globalen Zustand des Python-Zufallsmoduls ab.

Der Additionsgenerator validiert die Rechenart, zieht jeden Operanden aus seinem jeweils eigenen inklusiven Bereich und berechnet die erwartete Antwort. Er verwaltet ausdrücklich weder Aufgabennummern noch Punktestand, Zeitlimit oder Antwortstatus. Diese Verantwortungen gehören in eine spätere Session-Orchestrierung.

Der Subtraktionsgenerator zieht bei erlaubten negativen Ergebnissen ebenfalls unabhängig aus beiden Bereichen. Ohne negative Ergebnisse berechnet er dagegen zuerst einen gültigen Bereich für den linken Operanden und begrenzt danach den rechten Operanden auf höchstens den gezogenen linken Wert. Existiert kein gültiges Paar, endet die Erzeugung vor dem ersten Zufallszug mit einem fachlichen Fehler. Diese Konstruktion vermeidet unbeschränkte Retry-Schleifen und macht auch unmögliche Definitionen deterministisch behandelbar.

## Plugin-Isolation

Plugins dürfen später Generatoren, Modi oder Integrationen bereitstellen. Sie müssen jedoch gegen die Core-Verträge arbeiten. Ein Plugin darf die Bedeutung eines Antwortstatus oder eines Definitions-Hashes nicht verändern. Dadurch bleibt die Vergleichbarkeit über verschiedene Erweiterungen hinweg erhalten.

## Statistikereignisse und historische Renngegner

Neue Statistikereignisse speichern neben Rennzeit, Antwortstatus und Punktestand auch die
Aufgabenkennung beziehungsweise Aufgabennummer, Ereignisart, den endgültigen
Aufgabenabschluss sowie die kumulierten Werte für richtige Antworten, abgeschlossene
Aufgaben und Combo. Eine optionale Endursache kann den Abschluss eines Laufs erklären.
Diese Fakten sind absichtlich redundant: Ein Renn-Replay muss weder Aufgabenabschlüsse
noch Zielzeitpunkte aus einem Score erraten.

Die Datenbankmigration bewahrt ältere Statistiken unverändert und kennzeichnet deren
kompakte Ereignisstruktur als Version 1. Solche Läufe können weiterhin in Bestenlisten und
Auswertungen erscheinen. Als Renngegner sind sie nur für Regeln verwendbar, die sich aus
den tatsächlich gespeicherten Antwortfolgen ableiten lassen: Rennen auf richtige Antworten,
fehlerfreie Läufe und Combo-Rennen. Für Rennen nach abgeschlossenen Aufgaben fehlen die
Informationen über Mehrfachversuche; für Zeitlimit-Rennen fehlt ein ausdrückliches
Zeitablauf-/Endereignis. Diese alten Läufe werden daher für diese konkreten Regeln nicht als
Gegner angeboten. Ereignisse der Version 2 werden nur verwendet, wenn alle für das Replay
benötigten kumulierten Zähler und Abschlussangaben vorhanden sind. Der Definitions-Hash
bleibt in jedem Fall die erste Vergleichbarkeitsgrenze.
