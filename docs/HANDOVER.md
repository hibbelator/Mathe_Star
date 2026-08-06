# Handover nach Sitzung 3 / Verification Gate 3

## In Sitzung 3 umgesetzt

Der erste spielbare Produktdurchstich ist implementiert. Die Flet-Anwendung beginnt mit einer Auswahl zwischen Addition und Subtraktion, startet eine Runde mit fünf Aufgaben, nimmt ganzzahlige Antworten entgegen und zeigt nach jeder Abgabe ein eindeutiges Richtig-/Falsch-Feedback. Nach der fünften Aufgabe folgt ein Abschlussbildschirm mit Ergebnis sowie Aktionen für eine neue Runde oder eine andere Übung.

Die neue `RoundSession` hält den Ablauf aus der Oberfläche heraus. Sie verwaltet die Phasen `ready`, `task`, `feedback` und `finished`, erzeugt Aufgaben über den bestehenden `TaskGenerator`-Vertrag und speichert kanonische `TaskResult`-Werte. Leere und nicht-ganzzahlige Eingaben bleiben auf derselben Aufgabe und liefern eine verständliche Meldung. Eine zweite Abgabe während der Feedbackphase wird auf Modellebene verhindert.

Die Anwendung ist über den Projekteinstiegspunkt `math-game` sowie direkt über `python -m math_game.app.flet_app` startbar. Flet ist als Laufzeitabhängigkeit deklariert. Der UI-Code bleibt ein Adapter; Generatoren, Antwortbewertung und Rundenfortschritt sind unabhängig von Widgets automatisiert testbar.

## Stand von Verification Gate 3

Der funktionale Durchstich und die automatisierten Tests sind abgeschlossen. Pytest, Ruff, Pyright und `git diff --check` laufen ohne Befund. In der aktuellen Arbeitsumgebung war Flet nicht vorinstalliert und konnte wegen gesperrtem Paketnetzwerk nicht nachgeladen werden. Deshalb konnten der reale Flet-Start, ein UI-Smoke-Test gegen die installierte Bibliothek und der vorgeschriebene Screenshot hier noch nicht ausgeführt werden. Diese drei visuellen Laufzeitprüfungen bleiben als klar abgegrenzte Gate-3-Verifikation offen; es fehlt keine weitere fachliche Implementierung des Durchstichs.

## Bewusst noch nicht umgesetzt

- keine SQLite- oder andere Langzeitpersistenz,
- keine Multiplikation und Division,
- keine Zeitmessung oder zeitgesteuerten Modi,
- keine adaptive Schwierigkeit oder universelle Modus-State-Machine,
- noch keine ausgearbeitete Serienlogik, Animation, Akustik oder echte Gerätehaptik,
- noch kein veröffentlichungsreifer Desktop- oder Android-Build.

## Nächster Einstiegspunkt: Sitzung 4

Sobald Flet in einer ausführbaren Umgebung verfügbar ist, beginnt Sitzung 4 mit einem visuellen Audit und aktuellen Screenshots des implementierten Pfads. Anschließend liegt der Schwerpunkt auf Interaktionsgefühl und Motivation: klare visuelle Hierarchie, großzügige Touch-Ziele, responsive Größen, Fokusführung, Feedback nicht nur über Farbe, eine sichtbare Erfolgsserie und zurückhaltende Übergänge.

Die bestehende Rundensteuerung soll dabei nur erweitert werden, wenn eine konkrete sichtbare Anforderung dies verlangt. Neue Rechenarten, Persistenz und generische Pluginarbeit dürfen Sitzung 4 nicht verdrängen. Nach Abschluss dieses Pakets verbleibt gemäß Roadmap nur noch Sitzung 5 für Ergebnispräsentation, Härtung und Beta-Abnahme.
