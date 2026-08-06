# Architekturentscheidungen

## ADR-001: Core zuerst, Ausführung später

**Entscheidung:** Sitzung 1 implementiert nur Domain-Verträge, Normalisierung und Hash-Modelle.

**Begründung:** Ein stabiler Core verhindert, dass UI, Datenbank oder Generatorlogik frühzeitig fachliche Begriffe verwässern.

## ADR-002: Definition-Hash über kanonisches JSON

**Entscheidung:** Spieldefinitionen werden normalisiert, als kanonisches JSON serialisiert und mit SHA-256 gehasht.

**Begründung:** Diese Strategie ist transparent, plattformneutral und stabil gegenüber Dictionary-Reihenfolgen.

## ADR-003: Keine Abhängigkeiten im Core

**Entscheidung:** Die Session-1-Core-Modelle verwenden nur die Python-Standardbibliothek.

**Begründung:** Der Core soll leicht testbar und später in unterschiedlichen Laufzeitumgebungen verwendbar bleiben.

## ADR-004: Addition als erster Generator-Durchstich

**Entscheidung:** Der erste konkrete Generator unterstützt nur ganzzahlige Addition. Weitere Rechenarten werden nicht durch bedingte Zweige vorweggenommen, sondern folgen als eigene, fachlich geprüfte Durchstiche.

**Begründung:** Addition besitzt keine zusätzlichen Fragen zu Resten, Vorzeichen oder exakter Teilbarkeit. Dadurch kann zuerst die Grenze zwischen Definition, Zufallsquelle und erzeugter Aufgabe verifiziert werden.

## ADR-005: Zufall als injizierter Vertrag

**Entscheidung:** Generatoren greifen nicht auf den globalen Zustand des Moduls `random` zu. Sie erhalten eine `IntegerRandomSource`; der Standardadapter besitzt eine unabhängige `random.Random`-Instanz.

**Begründung:** Fachtests können dadurch feste Werte vorgeben und zugleich prüfen, mit welchen Bereichsgrenzen ein Generator arbeitet. Später lassen sich Seeds, Wiederholungen oder alternative Zufallsquellen ergänzen, ohne den Generatorvertrag zu ändern.

## ADR-006: Spieldefinitionen sind tief genug unveränderlich

**Entscheidung:** Beim Erzeugen einer `GameDefinition` werden Metadaten defensiv kopiert und über eine schreibgeschützte Sicht gehalten. Antwortergebnisse verwenden den kanonischen Enum `AnswerStatus` statt eines beliebigen Strings.

**Begründung:** Eine von außen veränderte Metadaten-Dictionary darf den Hash eines bereits bestehenden Objekts nicht nachträglich ändern. Ebenso darf das typisierte Modell keine Statuswerte zulassen, die außerhalb des dokumentierten Vertrags liegen.

## ADR-007: Gültige Subtraktionspaare ohne Wiederholungsziehung

**Entscheidung:** Wenn negative Ergebnisse verboten sind, wird kein beliebiges Operandenpaar gezogen und anschließend verworfen. Stattdessen muss der linke Operand mindestens so groß wie das Minimum des rechten Bereichs sein. Nach seinem Zug wird die Obergrenze des rechten Operanden auf den linken Wert begrenzt. Gibt es schon für den linken Operanden keinen gültigen Bereich, schlägt die Generierung unmittelbar mit `ValueError` fehl.

**Begründung:** Eine Retry-Schleife könnte bei unmöglichen Definitionen niemals terminieren und bei ungünstigen Bereichen eine unvorhersagbare Zahl von Zufallszügen verbrauchen. Das direkte Konstruieren eines gültigen Paars garantiert Terminierung, ist mit kontrollierten Zufallsquellen exakt testbar und verändert die in der Definition festgelegten absoluten Bereichsgrenzen nicht.

**Konsequenz:** Die gültigen Operandenpaare sind nicht als Gesamtmenge gleichverteilt: Zunächst wird ein gültiger linker Operand gleichverteilt gezogen, anschließend ein für diesen Wert gültiger rechter Operand. Falls später eine Gleichverteilung über alle gültigen Paare fachlich verlangt wird, benötigt dies eine eigene Entscheidung und einen entsprechend erweiterten Zufallsvertrag.

## ADR-008: Produktdurchstich vor weiteren Rechenarten

**Entscheidung:** Nach Addition und Subtraktion werden Multiplikation und Division bis nach dem ersten spielbaren UI-Durchstich zurückgestellt. Die erste Beta wird in höchstens drei weiteren Sitzungen geplant: spielbarer Ablauf, Spielgefühl und Feedback sowie Beta-Härtung und Ergebnispräsentation.

**Begründung:** Die Generatorgrenze ist mit einer einfachen und einer regelbehafteten Rechenart ausreichend verifiziert. Der größte verbleibende Produktwert und das größte Projektrisiko liegen nun in Bedienbarkeit, visueller Präsentation, unmittelbarem Feedback und Motivation. Weitere isolierte Generatoren würden diese Fragen nicht beantworten.

**Konsequenz:** Flet-Code und eine kleine konkrete Rundensteuerung sind ab Sitzung 3 ausdrücklich erwünscht. SQLite, eine generische Plugin-Infrastruktur und eine universelle Spielmodus-State-Machine bleiben außerhalb der Beta, solange sie nicht durch einen beobachtbaren Nutzerbedarf begründet sind.

## ADR-009: Explizite Rundensteuerung hinter der Flet-Oberfläche

**Entscheidung:** Die erste UI verwendet eine konkrete `RoundSession` mit vier Phasen. Sie bleibt unabhängig von Flet und wird über Methoden für Start, Antwortabgabe und Fortsetzung gesteuert. Die Oberfläche rendert diese Zustände, enthält aber weder Antwortbewertung noch Aufgabenerzeugung.

**Begründung:** Der vollständige Produktpfad soll schnell entstehen und trotzdem zuverlässig testbar bleiben. Eine UI-unabhängige Steuerung verhindert, dass Widget-Tests die einzige Absicherung der Spiellogik werden. Vier konkrete Phasen sind für die Beta verständlicher und kostengünstiger als eine vorzeitig konfigurierbare State-Machine.

**Konsequenz:** Zeitmessung ist in Sitzung 3 noch nicht Bestandteil des sichtbaren Ablaufs; `elapsed_ms` wird vorläufig mit null erfasst. Motivation, Serienlogik, verfeinertes Feedback und mögliche Übergangsanimationen werden in Sitzung 4 auf dem bestehenden Ablauf ergänzt.
