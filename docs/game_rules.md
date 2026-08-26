# Verbindliche Spielregeln

Dieses Dokument beschreibt die fachlichen Zielregeln, die ab Sitzung 1 gelten. Addition und Subtraktion sind inzwischen als einzelne Generatoren implementiert. Ein vollständiger Generatorverbund und konkrete Modusabläufe existieren noch nicht.

Soweit dieses Dokument von VBA-Details abweicht, ist die Abweichung beabsichtigt. Bekannte Excel-Fehler werden nicht übernommen.

---

## 1. Rechenarten und Gewichte

Die App unterstützt diese Rechenarten:

- `addition`,
- `subtraction`,
- `multiplication`,
- `division`.

Eine `GameDefinition` enthält die Gewichte dieser Rechenarten als `OperationWeights`. Gewichte müssen ganze Zahlen größer oder gleich `0` sein. Mindestens ein Gewicht muss größer als `0` sein.

Die Auswahlwahrscheinlichkeit lautet:

```text
P(Operation) = Gewicht(Operation) / Summe aller Gewichte
```

Ein physisch aufgeblähter Auswahlpool ist nicht erforderlich. Wichtig ist die fachlich identische Verteilung und Reproduzierbarkeit bei festem Seed.

---

## 2. GameDefinition

Eine vollständige Kombination aus Recheninhalt und Modusparametern bildet eine unveränderliche `GameDefinition`. Direkte Rekorde und Vergleiche dürfen nur innerhalb derselben `game_definition_id` erfolgen.

Zwei Ergebnisse sind nur dann direkt vergleichbar, wenn sie auf derselben normalisierten Spieldefinition beruhen. Der Definitions-Hash wird aus dem kanonischen JSON der Definition gebildet. Dadurch sind Vergleiche unabhängig von Python-Objektidentitäten, Prozesszustand oder Dictionary-Reihenfolgen.

## Generierung in Sitzung 2A

Der erste implementierte Durchstich ist die Addition. Linker und rechter Operand werden jeweils innerhalb ihres eigenen, inklusiven `OperandRange` ausgewählt. Die erwartete Antwort ist die ganzzahlige Summe beider Werte. Eine Additionsdefinition darf deshalb beispielsweise den linken Bereich `1..5` mit dem rechten Bereich `10..20` kombinieren; der Generator darf diese Bereiche weder vertauschen noch zusammenfassen.

Der Generator erzeugt genau eine fachliche Aufgabe pro Aufruf. Auswahl zwischen mehreren Operationsdefinitionen, Vermeidung von Wiederholungen, Schwierigkeitsprogression, Punktevergabe und Abbruchbedingungen sind keine Generatoraufgaben und bleiben für spätere Pakete offen.

## Subtraktion in Sitzung 2B

Bei `allow_negative_results = true` werden linker und rechter Operand unabhängig aus ihren jeweiligen inklusiven Bereichen gewählt. Das Ergebnis ist `left_operand - right_operand` und darf kleiner als null sein.

Bei `allow_negative_results = false` muss jede erzeugte Aufgabe ein Ergebnis größer oder gleich null besitzen. Die Reihenfolge der Operanden wird dabei nicht nachträglich vertauscht, weil dadurch die Bedeutung unterschiedlicher linker und rechter Bereiche verloren ginge. Stattdessen zieht der Generator ausschließlich aus dem Teil der Bereiche, in dem der linke Operand mindestens so groß wie der rechte sein kann. Gibt es kein solches Paar, ist die Definition für diesen Generator unerfüllbar und die Erzeugung schlägt unmittelbar fehl.

---

## 3. Rennregeln

### Allgemeine Vergleichs- und Gleichstandsregeln

Rennen und Ranglisten dürfen nur Aufzeichnungen vergleichen, deren normalisierte Spieldefinition, Modus und versionierte Rennregel kompatibel sind. Wo ein Modus eine vorab festgelegte Aufgabenfolge verlangt, muss auch diese Folge identisch sein. Zuerst entscheidet das jeweilige Rennziel; die in der Tabelle genannte Zeit oder Sekundärwertung löst einen Gleichstand nur innerhalb dieses gemeinsamen Vergleichsrahmens. Bleiben danach alle Rangmerkmale gleich, teilen sich die Teilnehmenden den Rang.

| GameMode | Rennfähig | Rennziel | Fortschritt | Eigener Lauf endet | Gesamtes Rennen endet | Rangfolge / Gleichstand | Kompatible Aufzeichnungen |
|---|---|---|---|---|---|---|---|
| `PRACTICE` | Nein | Freies Üben | – | Durch Verlassen | Kein Rennen | Keine Rangfolge | Erst bei identischer, vorab festgelegter Aufgabenfolge und versionierter Rennregel fair vergleichbar |
| `TIMED` | Ja | Meiste richtige Antworten | Richtige Antworten | Gemeinsame Maximaldauer | Gemeinsame Maximaldauer | Richtige, dann Zeit; sonst geteilter Rang | `TIMED` und fachlich gleiches `TIME_ATTACK` |
| `FIXED_TASKS` | Ja | `task_count` Aufgaben | Abgeschlossene Aufgaben | An der Aufgaben-Ziellinie | Alle im Ziel oder gemeinsame Maximaldauer | Zielzeit, davor Fortschritt; dann richtige Antworten | `FIXED_TASKS` und fachlich gleicher `TASK_SPRINT` |
| `MISTAKE_REVIEW` | Nein | Fehler gezielt nachüben | – | Wenn die Wiederholung endet | Kein Rennen | Keine Rangfolge | Erst bei identischer, vorab festgelegter Aufgabenfolge und versionierter Rennregel fair vergleichbar |
| `TIME_ATTACK` | Ja | Meiste richtige Antworten | Richtige Antworten | Gemeinsame Maximaldauer | Gemeinsame Maximaldauer | Richtige, dann Zeit; sonst geteilter Rang | `TIME_ATTACK` und fachlich gleiches `TIMED` |
| `TASK_SPRINT` | Ja | `task_count` Aufgaben | Abgeschlossene Aufgaben | An der Aufgaben-Ziellinie | Alle im Ziel oder gemeinsame Maximaldauer | Zielzeit, davor Fortschritt; dann richtige Antworten | `TASK_SPRINT` und fachlich gleicher `FIXED_TASKS` |
| `PERFECT_RUN` | Ja | Längste fehlerfreie Serie | Richtige Aufgaben in Folge | Erster endgültiger Fehler oder Maximaldauer | Alle beendet oder gemeinsame Maximaldauer | Serienlänge, dann Zeit; sonst geteilter Rang | Gleiche Definition, `PERFECT_RUN` und Rennregelversion |
| `TARGET_HUNT` | Ja | `correct_target` Richtige | Richtige Antworten | Ziel erreicht oder Maximaldauer | Alle im Ziel oder gemeinsame Maximaldauer | Zielzeit, davor richtige Antworten | Gleiche Definition, `TARGET_HUNT` und Rennregelversion |
| `PER_TASK_TIMER` | Ja | `task_count` Aufgaben | Abgeschlossene Aufgaben inkl. Timeout-Ereignisse | Ziel oder `task_count * per_task_seconds` | Alle beendet oder diese äußere Begrenzung | Zielzeit, dann richtige Antworten; sonst geteilter Rang | Gleiche Definition, `PER_TASK_TIMER` und Rennregelversion |
| `COMBO` | Ja | Combo-Ziel | Aktuelle Combo | Combo-Ziel oder Maximaldauer | Alle im Ziel oder gemeinsame Maximaldauer | Zielzeit, davor höchste Combo | Gleiche Definition, `COMBO` und Rennregelversion |
| `BLITZ` | Ja | Meiste richtige Antworten | Richtige Antworten | Gemeinsame Blitzdauer | Gemeinsame Blitzdauer | Richtige Antworten; sonst geteilter Rang | Gleiche Definition, `BLITZ` und Rennregelversion |
| `ACCURACY` | Ja | Beste Trefferquote | Abgeschlossene von `task_count` Aufgaben | Nach `task_count` Aufgaben | Alle beendet oder gemeinsame Maximaldauer | Trefferquote, dann richtige Antworten; sonst geteilter Rang | Gleiche Definition, `ACCURACY` und Rennregelversion |
| `PLUMI_ENDLESS` | Ja | Meiste richtige Antworten | Richtige und endgültige Fehler | Dritter endgültiger Fehler oder Maximaldauer | Alle beendet oder gemeinsame Maximaldauer | Richtige, dann beste Serie; sonst geteilter Rang | Gleiche Definition, `PLUMI_ENDLESS` und Rennregelversion |
| `WARM_UP` | Ja | Meiste richtige Antworten | Richtige Antworten | Gemeinsame Warm-up-Dauer | Gemeinsame Warm-up-Dauer | Richtige Antworten; sonst geteilter Rang | Gleiche Definition, `WARM_UP` und Rennregelversion |

Die folgenden modusspezifischen Abschnitte erläutern die verbindlichen Details; die Tabelle dient ausschließlich als knappe, vollständige Übersicht.

`wrong_answer_penalty` beeinflusst ausschließlich die Punktwertung. Der Wert verändert insbesondere weder die Anzahl richtiger Antworten noch die Anzahl abgeschlossener Aufgaben oder die Ziellinie eines Aufgaben-Sprints.

### PRACTICE

`PRACTICE` bleibt ein freier Übungsmodus ohne Rennwertung. Erst eine identische, vorab festgelegte Aufgabenfolge zusammen mit einer versionierten Rennregel würde aus den Ergebnissen einen fairen direkten Vergleich machen.
