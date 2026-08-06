# Roadmap zur ersten Beta

## Ziel und Zeitrahmen

Die erste Beta soll in **höchstens drei weiteren Umsetzungssitzungen** erreicht werden. Der aktuelle Stand nach Sitzung 2B ist ein ausreichend getestetes fachliches Fundament mit Generatoren für Addition und Subtraktion. Ab jetzt liegt der Schwerpunkt nicht auf weiteren Varianten der Zufallszahlenerzeugung, sondern auf einem vollständigen, fühlbaren Produkterlebnis: spielen, antworten, unmittelbares Feedback erhalten, Fortschritt erkennen und eine Runde motiviert abschließen.

Eine Sitzung bezeichnet dabei ein fokussiertes Arbeitspaket mit einem vorab festgelegten Abnahmetor. Da Implementierung, Tests und Dokumentation weitgehend automatisiert unterstützt werden, werden zusammengehörige Arbeiten bewusst gebündelt. Die Roadmap zerlegt nicht jede kleine technische Klasse in eine eigene Sitzung.

## Definition der ersten Beta

Die Beta ist erreicht, wenn eine Testperson ohne Kenntnis des Codes die Anwendung starten und eine vollständige Runde absolvieren kann. Sie umfasst:

- eine lokal startbare Flet-Anwendung,
- einen klaren Startbildschirm und eine Übungsauswahl für Addition und Subtraktion,
- eine kurze Runde mit verständlicher Aufgabenanzeige und großer Zahleneingabe,
- Bedienung per Maus beziehungsweise Touch und per Tastatur,
- sofortiges, freundliches Feedback für richtige und falsche Antworten,
- sichtbaren Rundenfortschritt und eine einfache Erfolgsserie,
- einen Abschlussbildschirm mit verständlicher Zusammenfassung,
- robuste Behandlung leerer, ungültiger und sehr schneller Eingaben,
- automatisierte Tests für die Spiellogik sowie mindestens einen UI-Smoke-Test,
- eine dokumentierte Start- und Testanleitung.

Für diese Beta nicht erforderlich sind SQLite-Langzeitspeicherung, Benutzerkonten, Cloud-Synchronisierung, Multiplikation, Division, adaptive Schwierigkeit, eine Plugin-Oberfläche oder ein veröffentlichungsreifer Android-Build. Diese Funktionen dürfen die Prüfung des zentralen Spielgefühls nicht verzögern.

## Sitzung 3: Spielbarer vertikaler UI-Durchstich

**Status:** Implementiert. Die UI-unabhängige Rundensteuerung und der vollständige Flet-Pfad sind im Repository vorhanden. Die automatisierten Session-Tests bestehen. Der visuelle Lauf und der geforderte Screenshot müssen noch in einer Umgebung mit installierbarer Flet-Abhängigkeit bestätigt werden; die aktuelle Ausführungsumgebung konnte das Paket wegen gesperrtem Netzwerk nicht beziehen.

Sitzung 3 liefert nicht nur ein UI-Gerüst, sondern eine von Anfang bis Ende spielbare Runde. Dafür werden Flet als Oberflächentechnologie, eine kleine Session-Orchestrierung und genau die Screens implementiert, die für den Durchstich benötigt werden:

1. Start und Wahl zwischen Addition und Subtraktion,
2. Erzeugen und Anzeigen einer Aufgabe,
3. Eingabe und Abgabe einer Antwort,
4. Wechsel zur nächsten Aufgabe,
5. Abschluss nach einer festen, kurzen Aufgabenzahl.

Die Session-Orchestrierung darf klein und explizit bleiben. Sie muss Aufgaben, aktuelle Position und beantwortete Ergebnisse verwalten, aber noch keine universelle State-Machine für sämtliche späteren Spielmodi darstellen. Der bestehende Core bleibt unabhängig von Flet; UI-spezifischer Zustand liegt im Anwendungspaket.

**Verification Gate 3:** Eine Runde mit Addition oder Subtraktion lässt sich über die Flet-Oberfläche vollständig durchspielen. Kernlogik und Navigation sind automatisiert getestet. Ein Screenshot dokumentiert den sichtbaren Stand.

## Sitzung 4: Spielgefühl, Feedback und Motivation

**Status:** Nächstes Arbeitspaket.

Sitzung 4 konzentriert sich auf die eigentliche Produktqualität. Die Oberfläche erhält eine klare visuelle Hierarchie, großzügige Touch-Ziele, konsistente Abstände und eine gut lesbare Aufgabenpräsentation. Eingaben reagieren unmittelbar. Richtiges Lösen wird positiv bestätigt; falsche Antworten werden verständlich korrigiert, ohne den Spieler zu bestrafen oder zu beschämen.

Zusätzlich werden ein sichtbarer Fortschritt, eine kleine Erfolgsserie und zurückhaltende Übergänge zwischen Aufgaben ergänzt. Feedback soll nicht nur über Farbe vermittelt werden, damit Kontrastschwächen oder deaktivierte Animationen die Verständlichkeit nicht beeinträchtigen. Wo die Zielplattform es sinnvoll erlaubt, kann akustisches oder haptisches Feedback über einen Adapter vorbereitet werden; echtes Vibrationsfeedback ist jedoch kein Beta-Blocker.

**Verification Gate 4:** Jede Eingabe erzeugt sofort eindeutiges visuelles Feedback. Fokus, Tastaturbedienung, Touch-Ziele, Kontrast und schnelle Mehrfacheingaben sind geprüft. Eine komplette Runde fühlt sich zusammenhängend an und zeigt jederzeit Fortschritt.

## Sitzung 5: Ergebnispräsentation und Beta-Härtung

Sitzung 5 schließt die Motivationsschleife und stabilisiert die Anwendung. Der Abschlussbildschirm zeigt mindestens richtige Antworten, Gesamtzahl, Erfolgsserie und eine freundliche nächste Handlung wie „Noch einmal“ oder „Andere Übung“. Fehlerhafte Aufgaben können innerhalb der laufenden Runde gezielt erneut angeboten werden, sofern dies ohne versteckte Langzeitpersistenz möglich ist.

Danach wird der gesamte Beta-Pfad auf leere Eingaben, ungültige Zeichen, wiederholtes Bestätigen, Fenstergrößen, Neustart einer Runde und sauberes Beenden geprüft. Dokumentation und Startkommando werden verifiziert. Neue fachliche Rechenarten werden nur aufgenommen, wenn alle Beta-Kriterien bereits erfüllt sind und sie keine Stabilisierung verdrängen.

**Verification Gate 5 / Beta:** Die Beta-Definition dieses Dokuments ist vollständig erfüllt, alle automatisierten Prüfungen laufen erfolgreich, und der visuelle Endstand ist mit aktuellen Screenshots dokumentiert. Bekannte Einschränkungen sind im Handover festgehalten.

## Priorität nach der Beta

Erst das Feedback aus der Beta entscheidet die nächste Reihenfolge. Wahrscheinliche Kandidaten sind lokale Fortschrittsspeicherung, Multiplikation, ein gezielter Fehlerwiederholungsmodus und anschließend Division mit einer eigenen fachlichen Spezifikation. Ein Android-Build wird dann priorisiert, wenn die Desktop- beziehungsweise lokale Flet-Version ein überzeugendes Spielgefühl nachweist.
