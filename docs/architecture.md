# Architektur

## Feature-Slicing

Die Entwicklung erfolgt entlang vertikaler, überprüfbarer Scheiben. Sitzung 1 ist eine reine Fundament-Scheibe: Dokumentation, Projektstruktur, Domain-Verträge, Normalisierung und Hashbildung. Alles, was ein Spiel tatsächlich ausführt, wird nach Verification Gate 1A geplant.

## Core-Verantwortung

Der Core ist für die stabile Sprache der Domäne verantwortlich:

- Rechenarten und Antwortstatus als kanonische Werte.
- Spieldefinitionen als unveränderliche Verträge.
- Normalisierung und Definition-Hash für Vergleichbarkeit.
- Uhrzeit-Zugriff nur über ein Protokoll, damit Fachlogik testbar bleibt.

Der Core erzeugt keine Aufgaben, speichert keine Daten und kennt keine Benutzeroberfläche.

## Plugin-Isolation

Plugins dürfen später Generatoren, Modi oder Integrationen bereitstellen. Sie müssen jedoch gegen die Core-Verträge arbeiten. Ein Plugin darf die Bedeutung eines Antwortstatus oder eines Definitions-Hashes nicht verändern. Dadurch bleibt die Vergleichbarkeit über verschiedene Erweiterungen hinweg erhalten.
