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

Ein Rennen ist ein Vergleich mehrerer gleichzeitig gespielter oder aufgezeichneter Läufe. Die Rennanzeige darf zwar Punkte in eine Streckenposition umrechnen, diese Darstellung definiert aber weder das Ziel noch die Platzierung. Maßgeblich sind ausschließlich die nachstehenden Regeln des jeweiligen `GameMode`.

Alle Teilnehmer starten auf derselben logischen Startzeit. Eine gemeinsame Dauer läuft daher auch für einen Teilnehmer weiter, der gerade keine Antwort abgibt. Bei einer festen Aufgabenanzahl bedeutet „abgeschlossene Aufgabe“ jeder endgültig behandelte Aufgabenslot: eine richtige oder falsche Antwort, Überspringen und – sofern der Modus eine Aufgabenuhr besitzt – ein Timeout. Ein Abbruch durch den Benutzer oder eine unterbrochene, nicht wiederaufgenommene Aufzeichnung ist ein `DNF` (nicht im Ziel). Ein `DNF` wird hinter allen regelgerecht beendeten Läufen eingeordnet; mehrere `DNF` teilen sich den letzten Rang und dürfen nicht als Sieger gelten.

Wenn eine unten genannte gemeinsame Außengrenze erreicht ist, werden noch offene Teilnehmerläufe mit ihrem exakt zu diesem Zeitpunkt erreichten Stand beendet. Das gesamte Rennen endet, sobald alle Teilnehmerläufe beendet sind, oder sofort an dieser gemeinsamen Außengrenze. So kann weder ein ausgefallener Teilnehmer noch ein prinzipiell endloser Modus das Rennen unbegrenzt offenhalten.

### Allgemeine Vergleichs- und Gleichstandsregeln

Ein aufgezeichneter Lauf ist nur dann ein zulässiger Gegner, wenn die Aufzeichnung vollständig genug ist, um Fortschritt, Endgrund, Endzeit und alle Rangschlüssel des Modus erneut zu bestimmen. Außerdem müssen folgende Merkmale exakt übereinstimmen:

- `game_definition_id` und `GameMode`,
- die Version dieser Rennregeln,
- alle wirksamen Rennparameter, insbesondere Aufgabenanzahl, gemeinsame Dauer, Zeit pro Aufgabe, Richtig-Ziel, Combo-Ziel und etwaige Außengrenze,
- die Identität der Aufgabenfolge beziehungsweise ein Seed samt Generatorversion, aus denen dieselbe Folge zweifelsfrei reproduziert werden kann.

Die Forderung nach derselben Aufgabenfolge gilt auch dann, wenn zwei Definitionen nur dieselben Zahlenbereiche und Gewichte besitzen: gleiche Verteilungen allein garantieren noch keinen fairen direkten Vergleich. Timeout-, Fehler-, Skip- und Antwortereignisse müssen mit monotonen Zeitstempeln vorliegen. Ein Lauf aus einem anderen Modus darf auch dann nicht verwendet werden, wenn seine sichtbare Punktzahl zufällig passt. Die modusspezifischen Abschnitte nennen zusätzliche Voraussetzungen.

Die Rangfolge wird lexikographisch nach den beim Modus genannten Schlüsseln bestimmt: Zuerst entscheidet der erste Schlüssel, nur bei Gleichheit der nächste. Stimmen **alle** genannten Schlüssel überein, liegt ein echter Gleichstand vor. Die Teilnehmer erhalten dann denselben Wettbewerbsrang; der folgende Rang wird um die Anzahl der gleich Platzierten versetzt (beispielsweise `1, 1, 3`). Namen, Speicherreihenfolge oder technische IDs sind niemals heimliche Tie-Breaker.

### `PRACTICE`

`PRACTICE` ist zunächst **nicht rennfähig**. Freies Üben kann Aufgaben adaptiv auswählen, wiederholen oder ohne einheitliches Ende fortsetzen; damit gibt es weder ein gemeinsames Rennziel noch einen fairen Fortschritts- und Rangbegriff. Der eigene Lauf endet nach den Übungsregeln beziehungsweise durch Abbruch, ein gesamtes Rennen findet nicht statt. Entsprechend sind keine aufgezeichneten Läufe als Renngegner kompatibel. Eine spätere Aktivierung setzt eine für alle Teilnehmer identische, vorab festgelegte Aufgabenfolge und eine eigene versionierte Ziel-, End- und Rangregel voraus.

### `TIMED` und `TIME_ATTACK`

Beide Modi sind rennfähige **Zeitrennen**. Das Rennziel ist die in der Definition festgelegte gemeinsame `duration_seconds`; der Fortschritt auf der Strecke ist `min(verstrichene Rennzeit / duration_seconds, 1)`. Die Zeitposition zeigt also, wie weit die Runde fortgeschritten ist, während die Wertung separat geführt wird. Der eigene Lauf und das gesamte Rennen enden am gemeinsamen Zeitlimit.

Es gewinnt die höchste Punktwertung bei Zeitende. Bei gleicher Punktwertung herrscht ein echter Gleichstand; Antworttempo oder die Zahl bearbeiteter Aufgaben brechen ihn nicht nachträglich. Aufgezeichnete Gegner benötigen neben den allgemeinen Kompatibilitätsmerkmalen dieselbe Dauer und eine Wertung, die lückenlos bis zum gemeinsamen Zeitende rekonstruiert werden kann. `TIMED` und `TIME_ATTACK` sind trotz identischer Rennmechanik verschiedene Modi und daher nicht untereinander kompatibel.

### `FIXED_TASKS` und `TASK_SPRINT`

Beide Modi sind rennfähige **Aufgaben-Sprints**. Zielgröße ist die feste positive `task_count`; die Ziellinie wird genau mit dem Abschluss des letzten Aufgabenslots erreicht. Der Fortschritt ist `abgeschlossene Aufgaben / task_count`. Er hängt weder von der Punktzahl noch davon ab, wie viele dieser Aufgaben richtig waren. Der eigene Lauf endet an der Ziellinie. Das Rennen endet, sobald alle Teilnehmer im Ziel sind; für Verbindungsabbrüche muss die Rennkonfiguration zusätzlich eine gemeinsame positive Außengrenze enthalten, an der offene Läufe `DNF` werden.

Zuerst werden alle Finisher nach ihrer Zielzeit aufsteigend eingeordnet. Identische Zielzeiten ergeben denselben Rang; Punkte sind kein Tie-Breaker eines Aufgaben-Sprints. Danach folgen `DNF` nach der allgemeinen Regel. Kompatible Aufzeichnungen müssen insbesondere dieselbe Aufgabenanzahl, dieselbe Außengrenze und Ereignisse für alle abgeschlossenen Slots besitzen. `FIXED_TASKS` und `TASK_SPRINT` bleiben getrennte Kompatibilitätsgruppen.

### `MISTAKE_REVIEW`

`MISTAKE_REVIEW` ist zunächst **nicht rennfähig**, weil die Aufgabenfolge aus der individuellen Fehlerhistorie entsteht. Es gibt deshalb kein teilnehmerübergreifendes Ziel, keinen vergleichbaren Fortschritt, kein gemeinsames Rennende und keine Rangfolge; Aufzeichnungen anderer Personen sind keine kompatiblen Gegner. Der eigene Review-Lauf endet nach seinen normalen Wiederholungsregeln oder durch Abbruch. Rennfähigkeit darf erst eingeführt werden, wenn alle Teilnehmer exakt denselben vorab eingefrorenen Review-Satz in derselben Reihenfolge erhalten und dafür eine versionierte Ziel- und Rangregel festgelegt wurde.

### `TARGET_HUNT`

`TARGET_HUNT` ist rennfähig. Das Ziel ist die feste positive Anzahl `correct_target` richtiger Antworten. Fortschritt ist `min(Anzahl richtiger Antworten / correct_target, 1)`; falsche Antworten und Timeouts erhöhen ihn nicht. Der eigene Lauf endet im Zeitpunkt der Antwort, mit der das Ziel erreicht wird. Das gesamte Rennen endet, wenn alle das Ziel erreicht haben, spätestens aber an einer in der Rennkonfiguration verpflichtend festgelegten gemeinsamen positiven Außengrenze.

Zielerreicher werden nach ihrer Zielzeit aufsteigend sortiert. Wer die Außengrenze ohne Zielerreichung erreicht, folgt danach, sortiert nach der Zahl richtiger Antworten absteigend; bei gleicher Zahl besteht Gleichstand. Ein echter Abbruch bleibt `DNF` und liegt dahinter. Gegneraufzeichnungen müssen dasselbe Richtig-Ziel und dieselbe Außengrenze besitzen sowie den Zeitpunkt jeder richtigen Antwort belegen.

### `PER_TASK_TIMER`

`PER_TASK_TIMER` ist rennfähig, wenn sowohl `task_count` als auch `per_task_seconds` festgelegt sind. Ziel ist die feste Zahl von Aufgabenslots. Jede Aufgabe hat eine eigene Deadline; verstreicht sie ohne endgültige Antwort, muss ein `TIMEOUT`-Ereignis aufgezeichnet werden, das den Slot abschließt und unmittelbar zur nächsten Aufgabe weiterführt. Ein Timeout darf weder verschwinden noch bloß als Anzeigeeffekt behandelt werden. Fortschritt ist `abgeschlossene Slots / task_count`, einschließlich der durch Timeout abgeschlossenen Slots.

Als eindeutige äußere Begrenzung gilt ab dem gemeinsamen Start `task_count * per_task_seconds`. Der eigene Lauf endet nach dem letzten Slot oder an dieser Begrenzung; das gesamte Rennen endet, wenn alle Läufe beendet sind, spätestens an derselben Begrenzung. Die Rangfolge lautet: Anzahl richtiger Antworten absteigend, Anzahl Timeouts aufsteigend, Endzeit aufsteigend. Sind alle drei Werte gleich, teilen sich die Teilnehmer den Rang. Kompatible Aufzeichnungen benötigen dieselbe Slotzahl und Aufgabendauer und müssen insbesondere jedes Deadline- und Timeout-Ereignis enthalten.

### `PERFECT_RUN`

`PERFECT_RUN` ist als Ausscheidungsrennen rennfähig. Zielgröße und Fortschritt sind die Länge der seit dem Start ununterbrochenen fehlerfreien Serie. Der erste **endgültige** Fehler – eine falsche abgegebene Antwort, `SKIPPED` oder `TIMEOUT`, nicht aber eine noch korrigierbare Eingabe – beendet den eigenen Lauf sofort. Damit auch mehrere weiterhin perfekte Läufe sicher vergleichbar enden, legt die Rennkonfiguration verpflichtend eine gemeinsame maximale Aufgabenanzahl fest; mit deren Abschluss endet ein noch fehlerfreier Lauf. Das gesamte Rennen endet nach dem Fehler beziehungsweise Grenzabschluss aller Teilnehmer.

Die längste fehlerfreie Serie gewinnt. Bei gleicher Serienlänge besteht Gleichstand; der bloß spätere Zeitpunkt eines gleich weit gekommenen Fehlers erzeugt keinen Vorteil. Gegneraufzeichnungen müssen dieselbe maximale Aufgabenanzahl besitzen und den Status jedes Slots bis zum ersten Fehler oder Grenzabschluss enthalten.

### `COMBO`

`COMBO` verwendet verbindlich eine **Combo-Ziel-Regel** und ist damit rennfähig: Die Rennkonfiguration legt ein positives Combo-Ziel und eine positive gemeinsame Maximaldauer fest. Jede richtige Antwort erhöht die aktuelle Combo um eins; jede falsche Antwort, `SKIPPED` oder `TIMEOUT` setzt sie auf null. Zielgröße ist das Combo-Ziel, Fortschritt ist `min(aktuelle Combo / Combo-Ziel, 1)`.

Der eigene Lauf endet beim erstmaligen Erreichen des Combo-Ziels oder an der Maximaldauer; das gesamte Rennen endet, wenn alle das Ziel erreicht haben, spätestens am gemeinsamen Zeitlimit. Zielerreicher werden nach Zielzeit aufsteigend platziert. Danach folgen Teilnehmer ohne Ziel nach ihrer höchsten im Lauf erreichten Combo absteigend; gleiche Best-Combos sind Gleichstände. Abbrüche sind nachrangige `DNF`. Kompatible Gegner benötigen dasselbe Combo-Ziel und Zeitlimit sowie eine vollständige Antwortfolge, aus der aktuelle und beste Combo rekonstruiert werden können.

### `BLITZ`

`BLITZ` wird entsprechend dem bestehenden Controller als kurzes, rennfähiges Zeitrennen von 30 bis 60 Sekunden eingeordnet. Zielgröße ist seine gemeinsame `duration_seconds`, Fortschritt ist der Anteil der verstrichenen Dauer. Eigener Lauf und Gesamtrennen enden am Zeitlimit. Es gewinnt die Anzahl richtiger Antworten; falsche Antworten erhöhen sie nicht. Bei derselben Anzahl richtiger Antworten besteht Gleichstand. Kompatible Aufzeichnungen brauchen exakt dieselbe Blitzdauer und müssen bis zum Zeitende reichen. Sie sind nicht mit `TIMED` oder `TIME_ATTACK` austauschbar.

### `ACCURACY`

`ACCURACY` wird entsprechend dem bestehenden Controller als ungestopptes, rennfähiges Genauigkeitsrennen über eine feste `task_count` eingeordnet (der Controller verwendet standardmäßig 20). Zielgröße ist diese Aufgabenanzahl, Fortschritt ist `beantwortete Aufgaben / task_count`, und der eigene Lauf endet mit der letzten Antwort. Das gesamte Rennen endet nach der letzten Antwort aller Teilnehmer; eine positive gemeinsame Außengrenze muss Hänger als `DNF` abschließen.

Es gewinnt die höchste Genauigkeit `richtige Antworten / beantwortete Aufgaben`; bei der für Finisher gleichen Aufgabenanzahl ist das gleichbedeutend mit der höchsten Zahl richtiger Antworten. Geschwindigkeit ist ausdrücklich kein Tie-Breaker: gleiche Genauigkeit bedeutet gleichen Rang. Aufzeichnungen benötigen dieselbe Aufgabenanzahl und Außengrenze sowie sämtliche Antwortstatus.

### `PLUMI_ENDLESS`

`PLUMI_ENDLESS` wird entsprechend dem bestehenden Controller als rennfähiges Ausdauer-/Highscore-Rennen eingeordnet. Der Teilnehmerlauf endet unmittelbar mit dem verbindlich dritten endgültigen Fehler. Weil ein fehlerfreier Lauf sonst endlos wäre, muss die Rennkonfiguration zusätzlich eine positive gemeinsame Maximaldauer festlegen; an ihr enden verbleibende Läufe. Das gesamte Rennen endet nach dem dritten Fehler aller Teilnehmer, spätestens an dieser Maximaldauer.

Die Zielgröße ist die bis zum Laufende erzielte Zahl richtiger Antworten. Während des Rennens wird der Fortschritt für die Anzeige relativ zum besten aktuell oder in den kompatiblen Gegneraufzeichnungen bekannten Endwert dargestellt; das ist eine dynamische Anzeige und keine vorgetäuschte Ziellinie. Die Rangfolge lautet: richtige Antworten absteigend, beste fehlerfreie Serie absteigend. Sind beide gleich, besteht Gleichstand. Gegneraufzeichnungen müssen genau die Drei-Fehler-Regel, dieselbe Maximaldauer und alle Antworten bis zum dritten Fehler oder Zeitende enthalten.

### `WARM_UP`

`WARM_UP` wird entsprechend dem bestehenden Controller als rennfähiges 60-Sekunden-Zeitrennen mit leichten Aufgaben eingeordnet, auch wenn es außerhalb eines Rennens lediglich auf das Hauptspiel vorbereitet. Zielgröße ist die feste gemeinsame Dauer von 60 Sekunden, Fortschritt ist `min(verstrichene Zeit / 60 Sekunden, 1)`. Eigener Lauf und Gesamtrennen enden gemeinsam bei 60 Sekunden; der anschließende Wechsel zum Hauptspiel gehört nicht mehr zum Warm-up-Rennen.

Es gewinnt die Zahl richtiger Antworten; bei gleicher Zahl besteht Gleichstand. Kompatible Gegner müssen aus einem eigenständig aufgezeichneten `WARM_UP` mit derselben leichten Aufgabenfolge stammen und Ereignisse bis zum 60-Sekunden-Ende enthalten. Ergebnisse des danach gestarteten Hauptspiels dürfen nicht eingerechnet werden.

### Bedeutung von `wrong_answer_penalty`

`wrong_answer_penalty` verändert **ausschließlich die Punktwertung**. Die Strafe zieht weder eine bereits richtige Antwort ab noch macht sie eine abgeschlossene Aufgabe wieder offen. Sie verändert nicht die Zähler für richtige Antworten oder abgeschlossene Aufgaben, setzt nur dort eine Combo zurück, wo die Combo-Regel dies ausdrücklich verlangt, und verschiebt insbesondere niemals die Ziellinie eines `FIXED_TASKS`- oder `TASK_SPRINT`-Rennens. Ein Modus, dessen Rangregel nicht die Punktwertung verwendet, erhält durch diese Einstellung keinen versteckten zusätzlichen Rangschlüssel.
