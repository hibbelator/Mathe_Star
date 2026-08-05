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
