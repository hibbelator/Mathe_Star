# Mathe-Abenteuer – zentraler Projektplan

**Stand:** 2026-08-05  
**Projekt:** Mathe-Abenteuer  
**Zielplattform:** private Android-App als direkt installierbare APK  
**Package-ID:** `de.familie.matheabenteuer`  
**Technikziel:** Python 3.13, Flet 0.86.x, SQLite, pytest, Ruff, Pyright

Dieses Dokument ist die zentrale Fortschritts- und Planungsübersicht für das Projekt. Es soll bei jeder Sitzung aktualisiert werden, damit Gesamtplan, aktueller Stand, offene Aufgaben, Entscheidungen, Teststatus und nächste Einstiegspunkte dauerhaft sichtbar bleiben.

Die fachliche Grundlage ist der vom Auftraggeber bereitgestellte Masterplan vom 5. August 2026. Die ursprüngliche Excel-Datei wird nicht mehr benötigt; die extrahierten Legacy-Regeln und die nicht zu übernehmenden Excel-Fehler sind im Masterplan bereits verbindlich zusammengefasst.

---

## 1. Zielbild

Mathe-Abenteuer wird eine vollständig offline nutzbare private Android-App für Mathematiktraining. Die App soll ohne Konto, Werbung, Telemetrie, Cloud-Dienste oder Netzwerkfunktionen funktionieren. Sie wird direkt als APK installiert und später über APK-Updates aktualisiert.

Die App soll fachlich zuverlässig, schnell bedienbar und kindgerecht motivierend sein, aber nicht wie eine Kleinkinder-App wirken. Die Architektur bleibt bewusst klein und vertikal nach Spielmodi geschnitten, damit spätere Erweiterungen wartbar bleiben und kein zentraler Spielablauf-Monolith entsteht.

---

## 2. Normative Reihenfolge der Anforderungen

Bei Widersprüchen gilt folgende Reihenfolge:

1. Verbindliche Zielregeln aus dem Masterplan.
2. Definierte Abnahmekriterien und Tests.
3. Normalisierte Beschreibung der Excel-Fachlogik.
4. VBA-Referenzcode als historische Quelle.

Bekannte Excel-Fehler dürfen nicht portiert werden.

---

## 3. Architektur-Leitplanken

### 3.1 Core

Der Core darf nur universelle Verträge und Infrastruktur enthalten:

- `GameDefinition`, Normalisierung und stabile Definition-ID,
- universeller Aufgabengenerator,
- grundlegende Validierung,
- Clock- und Random-Protokolle,
- standardisierte Start- und Ergebnisverträge,
- SQLite-Persistenz,
- App-Einstellungen,
- Plugin-Registry,
- gemeinsame App-Navigation.

Der Core enthält keine konkrete Moduswertung und keine visuellen Spielmotive.

### 3.2 Spielmodi

Jeder Spielmodus bleibt ein isoliertes Plugin mit eigener Flet-unabhängiger State-Machine. Änderungen in einem Modus dürfen keine Änderungen in anderen Modi erzwingen.

Verboten sind gemeinsame Basisklassen wie:

- `BaseGameController`,
- `BaseGameScreen`,
- gemeinsame Vererbungshierarchien für Timer, Wertung, Feedback, Animation oder Spielablauf.

Das Projekt folgt bewusst dem Prinzip: **WET vor DRY, wenn eine Abstraktion die Modi koppeln würde.**

---

## 4. Verbindliche Versionen und IDs

| Thema | Aktueller Zielwert | Status |
|---|---:|---|
| Regelversion | `1` | geplant |
| Generatorversion | `1` | geplant |
| Ergebnis-Schemaversion | `1` | geplant |
| Datenbankschema-Version | noch nicht implementiert | offen |
| Android-Package-ID | `de.familie.matheabenteuer` | festgelegt |
| App-Name | `Mathe-Abenteuer` | festgelegt |

Wichtig: Package-ID und Signaturschlüssel dürfen nach der ersten dauerhaft genutzten APK nicht mehr geändert werden, wenn Updates ohne Datenverlust installiert werden sollen.

---

## 5. Gesamtfortschritt

| Bereich | Status | Bemerkung |
|---|---|---|
| Projektstruktur | offen | Noch nicht angelegt, außer diesem Planungsdokument. |
| Dokumentation | begonnen | Zentrales Planungsdokument wurde angelegt. Fach- und Architekturdocs fehlen noch. |
| Domain-Modelle | offen | Für Sitzung 1 vorgesehen. |
| Definition-Hash | offen | Für Sitzung 1 vorgesehen. |
| Generator v1 | offen | Erst nach Verification Gate 1A. |
| Headless `time_attack` | offen | Erst nach Freigabe nach Gate 1A. |
| SQLite-Persistenz | offen | Sitzung 2, Phase A. |
| Flet-App-Shell | offen | Sitzung 2, nach grünen Persistenztests. |
| Android Debug-APK | offen | Sitzung 2, Phase C. |
| Weitere Spielmodi | offen | Sitzungen 3 und 4. |
| Statistik, Backup, Release | offen | Sitzung 5. |

---

## 6. Sitzungsplan und Fortschritt

### Sitzung 1 – Fundament und headless Zeitrennen

#### 1A: Dokumentation, Domain-Verträge und Hash

Status: **offen**

Aufgaben:

- [ ] Projektstruktur anlegen.
- [ ] `docs/legacy_excel_reference.md` erstellen.
- [ ] `docs/game_rules.md` erstellen.
- [ ] `docs/architecture.md` erstellen.
- [ ] `docs/decisions.md` erstellen.
- [ ] `docs/HANDOVER.md` erstellen.
- [ ] Domain-Modelle implementieren.
- [ ] Plugin- und Clock-Verträge implementieren.
- [ ] Normalisierung der `GameDefinition` implementieren.
- [ ] Stabile Definition-ID per kanonischem JSON und SHA-256 implementieren.
- [ ] Hash-Tests schreiben.

Verification Gate 1A:

- [ ] Modelle vorgelegt.
- [ ] JSON-Schemata vorgelegt.
- [ ] Hash-Felder dokumentiert.
- [ ] Plugin-Vertrag dokumentiert.
- [ ] Echte offene Widersprüche dokumentiert.
- [ ] Noch kein Generator implementiert.
- [ ] Noch kein Spielmodus implementiert.
- [ ] Noch keine Datenbank implementiert.
- [ ] Noch keine Flet-UI implementiert.

#### 1B: Generator v1 und headless Zeitrennen

Status: **gesperrt bis Freigabe nach Gate 1A**

Aufgaben nach Freigabe:

- [ ] Generatorversion 1 implementieren.
- [ ] Validierung unmöglicher Konfigurationen implementieren.
- [ ] `time_attack` als isolierte State-Machine implementieren.
- [ ] Test-Harness erstellen.
- [ ] Unit-Tests für Generator schreiben.
- [ ] Unit- und Race-Condition-Tests für `time_attack` schreiben.
- [ ] `docs/HANDOVER.md` aktualisieren.

### Sitzung 2 – vollständiger Android-Vertical-Slice

Status: **offen**

- [ ] SQLite-Schema implementieren.
- [ ] Definitionen append-only speichern.
- [ ] Präsentationsdaten separat änderbar speichern.
- [ ] Sessions append-only speichern.
- [ ] Rekordabfrage nur innerhalb derselben `game_definition_id` implementieren.
- [ ] Persistenztests grün bekommen.
- [ ] Erst danach Flet-App-Shell beginnen.
- [ ] Startseite, Elternbereich, Zahlenblock und Ergebnisbildschirm umsetzen.
- [ ] `time_attack`-UI mit Raketenmotiv umsetzen.
- [ ] Debug-APK erzeugen und dokumentieren.

### Sitzung 3 – Aufgaben-Sprint und perfekte Serie

Status: **offen**

- [ ] `task_sprint` headless implementieren.
- [ ] `task_sprint` testen.
- [ ] `task_sprint`-UI erst nach grünen Logiktests implementieren.
- [ ] `perfect_run` headless implementieren.
- [ ] `perfect_run` testen.
- [ ] `perfect_run`-UI erst nach grünen Logiktests implementieren.

### Sitzung 4 – Zieljagd, Aufgabenzeit und Combo

Status: **offen**

- [ ] `target_hunt` einzeln implementieren und testen.
- [ ] `per_task_timer` einzeln implementieren und testen.
- [ ] `combo` einzeln implementieren und testen.
- [ ] UIs jeweils erst nach grünen headless Tests erstellen.

### Sitzung 5 – Statistik, Backup und Release

Status: **offen**

- [ ] Statistiken pro Definition implementieren.
- [ ] Allgemeine Lernübersicht getrennt von Rekorden implementieren.
- [ ] Backup-Export implementieren.
- [ ] Atomaren Backup-Import implementieren.
- [ ] Bedienung auf kleinen und großen Displays prüfen.
- [ ] Hintergrund/Vordergrund, Zurück-Taste und Abbruch prüfen.
- [ ] Ton, Vibration und reduzierte Animation finalisieren.
- [ ] Signierten Release-Build dokumentieren.
- [ ] Signaturschlüssel-Sicherung dokumentieren.
- [ ] Debug-Code und zentrale TODOs entfernen.

---

## 7. Aktuelle Todos

### Sofort als Nächstes

1. `README.md` und minimale Projektstruktur anlegen.
2. Fachliche Dokumentation aus dem Masterplan in `docs/legacy_excel_reference.md` und `docs/game_rules.md` aufteilen.
3. Architekturregeln in `docs/architecture.md` dokumentieren.
4. Erste Entscheidungen in `docs/decisions.md` festhalten.
5. Core-Domainmodelle und Verträge für Verification Gate 1A implementieren.

### Blockiert bis Freigabe

- Generatorversion 1.
- `time_attack`-State-Machine.
- Persistenz.
- Flet-UI.
- Android-Build.

---

## 8. Offene fachliche Klärungen

Aktuell sind keine harten Widersprüche bekannt, die das zentrale Planungsdokument blockieren.

Für Sitzung 1A sollten dennoch bewusst geprüft und dokumentiert werden:

- Welche Felder je Modus für den Definition-Hash relevant sind.
- Wie nicht genutzte Zeit- und Zielwerte kanonisch auf `None` normalisiert werden.
- Ob `allowed_tables` sortiert, dedupliziert oder exakt in eingegebener Reihenfolge gehasht wird.
- Welche Standardwerte für `penalty_seconds` je Modus gelten.
- Welche Combo-Regeln als Standarddefinition gespeichert werden.

---

## 9. Test- und Qualitätsstatus

Noch keine Tests eingerichtet.

Geplante Qualitätsbefehle nach Einrichtung:

```bash
pytest
ruff check .
ruff format --check .
pyright
```

Jede Sitzung muss die tatsächlich ausgeführten Befehle und Ergebnisse zusätzlich in `docs/HANDOVER.md` dokumentieren.

---

## 10. Änderungsprotokoll

| Datum | Änderung | Status |
|---|---|---|
| 2026-08-05 | Zentrales Planungsdokument `docs/PROJECT_PLAN.md` angelegt. | erledigt |

---

## 11. Pflege-Regeln für dieses Dokument

Dieses Dokument muss aktualisiert werden, wenn:

- eine Sitzung beginnt oder endet,
- ein Verification Gate erreicht wird,
- ein Bereich von offen auf begonnen oder erledigt wechselt,
- neue technische oder fachliche Entscheidungen getroffen werden,
- Tests eingerichtet oder geändert werden,
- bekannte Einschränkungen entstehen,
- der nächste Einstiegspunkt wechselt.

Der Zweck ist nicht, jede Codezeile zu erklären. Der Zweck ist, jederzeit schnell zu sehen:

- Was ist das Gesamtziel?
- Was ist fertig?
- Was ist offen?
- Was ist bewusst noch gesperrt?
- Was darf als Nächstes gemacht werden?
- Welche Qualitätsprüfungen gelten aktuell?
