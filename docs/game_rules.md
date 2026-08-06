# Verbindliche Spielregeln

Dieses Dokument beschreibt die fachlichen Zielregeln, die ab Sitzung 1 gelten. Addition und Subtraktion sind inzwischen als einzelne Generatoren implementiert. Ein vollständiger Generatorverbund und konkrete Modusabläufe existieren noch nicht.

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

## Generierung in Sitzung 2A

Der erste implementierte Durchstich ist die Addition. Linker und rechter Operand werden jeweils innerhalb ihres eigenen, inklusiven `OperandRange` ausgewählt. Die erwartete Antwort ist die ganzzahlige Summe beider Werte. Eine Additionsdefinition darf deshalb beispielsweise den linken Bereich `1..5` mit dem rechten Bereich `10..20` kombinieren; der Generator darf diese Bereiche weder vertauschen noch zusammenfassen.

Der Generator erzeugt genau eine fachliche Aufgabe pro Aufruf. Auswahl zwischen mehreren Operationsdefinitionen, Vermeidung von Wiederholungen, Schwierigkeitsprogression, Punktevergabe und Abbruchbedingungen sind keine Generatoraufgaben und bleiben für spätere Pakete offen.

## Subtraktion in Sitzung 2B

Bei `allow_negative_results = true` werden linker und rechter Operand unabhängig aus ihren jeweiligen inklusiven Bereichen gewählt. Das Ergebnis ist `left_operand - right_operand` und darf kleiner als null sein.

Bei `allow_negative_results = false` muss jede erzeugte Aufgabe ein Ergebnis größer oder gleich null besitzen. Die Reihenfolge der Operanden wird dabei nicht nachträglich vertauscht, weil dadurch die Bedeutung unterschiedlicher linker und rechter Bereiche verloren ginge. Stattdessen zieht der Generator ausschließlich aus dem Teil der Bereiche, in dem der linke Operand mindestens so groß wie der rechte sein kann. Gibt es kein solches Paar, ist die Definition für diesen Generator unerfüllbar und die Erzeugung schlägt unmittelbar fehl.
