# Legacy-Excel-Referenz

Dieses Dokument konserviert die fachlich relevanten Aussagen aus dem zuletzt bereitgestellten Masterplan, insbesondere aus Kapitel 2, Kapitel 3 sowie Anhang A und B. Die ehemalige Datei `Mathe_002 (1).xlsm` ist für Sitzung 1 ausdrücklich keine normative Quelle mehr.

## Kapitel 2: Fachlicher Bestand

Die Legacy-Anwendung wird als Referenz für eine Kopfrechen- und Übungslogik verstanden. Maßgeblich ist nicht die technische Excel-Implementierung, sondern die beobachtbare Domäne: Aufgaben werden aus einer verbindlichen Definition abgeleitet, Antworten erhalten einen eindeutigen Status und Ergebnisse dürfen nur verglichen werden, wenn die zugrunde liegende Definition identisch ist.

Wichtige Begriffe:

- **Aufgabendefinition**: beschreibt Rechenart, Zahlenräume und optionale Grenzen.
- **Spieldefinition**: bündelt Aufgabendefinitionen mit Modusparametern.
- **Antwortstatus**: beschreibt den fachlichen Zustand einer Aufgabe nach Interaktion.
- **Definitions-Hash**: stabile Identität einer Spieldefinition für Vergleichbarkeit.

## Kapitel 3: Zielbild der Neuimplementierung

Die Neuimplementierung wird in kleine, überprüfbare Scheiben zerlegt. Der Kern enthält ausschließlich stabile Domänenverträge, Normalisierung und Hashbildung. Generatoren, Spielmodi, Persistenz, UI und Build-Ziele werden erst nach Verification Gate 1A ergänzt.

Sitzung 1 endet bewusst früh: Es soll noch kein spielbares Produkt entstehen. Stattdessen wird die gemeinsame Sprache der Domäne festgelegt, damit spätere Generatoren und Oberflächen gegen dieselben Verträge arbeiten.

## Anhang A: Zielregeln in Kurzform

- Rechenarten sind Addition, Subtraktion, Multiplikation und Division.
- Eine Antwort ist unbeantwortet, korrekt, falsch, übersprungen oder durch Zeitablauf beendet.
- Spielmodi sind zunächst nur Vertragsnamen, keine implementierte Ablaufsteuerung.
- Vergleichbarkeit entsteht über denselben normalisierten Definitionsinhalt und dessen SHA-256-Hash.

## Anhang B: Technische Leitplanken

- Der Core darf keine UI-, Datenbank- oder Plattformabhängigkeiten besitzen.
- Hashes müssen deterministisch und unabhängig von Dictionary-Einfügereihenfolgen sein.
- Plugins dürfen später erweitert werden, müssen aber über stabile Core-Verträge integriert werden.
- Tests in Sitzung 1 beschränken sich auf Normalisierung und Definition-Hash.
