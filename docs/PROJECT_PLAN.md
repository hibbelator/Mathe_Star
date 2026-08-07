# Mathe-Abenteuer – zentraler Projektplan

**Stand:** 2026-08-07
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
| Projektstruktur | erledigt | `README.md`, `pyproject.toml`, `src/math_game` und `tests/core` sind vorhanden. |
| Dokumentation | begonnen | Zentrales Planungsdokument sowie Legacy-, Spielregel-, Architektur-, Entscheidungs- und Handover-Dokumente sind vorhanden; Legacy- und Spielregel-Dokumente wurden an den Masterplan angepasst. |
| Domain-Modelle | erledigt für Gate 1A | Core-Modelle wurden an das Zielmodell angepasst: `OperationWeights`, `ComboRules`, `GameDefinition`, `GamePresentation`, `MathTask`, `TaskAttempt`, `ResultSummary`, `GameSessionResult`. |
| Definition-Hash | erledigt für Gate 1A | Hashbildung nutzt das normalisierte `GameDefinition`-Payload; Präsentationsdaten sind getrennt und ungenutzte Modusfelder werden kanonisch normalisiert. |
| Generator v1 | begonnen | Addition, Subtraktion, Multiplikation, Division und gewichtete Definitionen sind spielbar; vollständige Legacy-Lücken bleiben zu prüfen. |
| Headless `time_attack` | offen | Erst nach Freigabe nach Gate 1A. |
| SQLite-Persistenz | offen | Sitzung 2, Phase A. |
| Flet-App-Shell | begonnen | Viergeteilter Einstieg, Definitionseditor, Spielrunde und einfache JSON-Statistik sind vorhanden. |
| Android Debug-APK | offen | Sitzung 2, Phase C. |
| Weitere Spielmodi | begonnen | Vier Post-Beta-Modi ohne SQLite sind als isolierte headless Module umgesetzt. |
| Statistik, Backup, Release | begonnen | Vorläufige lokale JSON-Rundenstatistik vorhanden; SQLite, Backup und Release bleiben offen. |

---

## 6. Sitzungsplan und Fortschritt

### Sitzung 1 – Fundament und headless Zeitrennen

#### 1A: Dokumentation, Domain-Verträge und Hash

Status: **offen**

Aufgaben:

- [x] Projektstruktur anlegen.
- [x] `docs/legacy_excel_reference.md` erstellen und an die verbindliche Legacy-Basis anpassen.
- [x] `docs/game_rules.md` erstellen und an die Ziel-Spielregeln anpassen.
- [x] `docs/architecture.md` erstellen.
- [x] `docs/decisions.md` erstellen.
- [x] `docs/HANDOVER.md` erstellen.
- [x] Domain-Modelle implementieren.
- [x] Plugin- und Clock-Verträge implementieren.
- [x] Normalisierung der `GameDefinition` implementieren.
- [x] Stabile Definition-ID per kanonischem JSON und SHA-256 implementieren.
- [x] Hash-Tests schreiben und auf zentrale Pflichtfälle erweitern.

Verification Gate 1A:

- [x] Modelle vorgelegt.
- [x] JSON-Schemata vorgelegt.
- [x] Hash-Felder dokumentiert.
- [x] Plugin-Vertrag dokumentiert.
- [x] Echte offene Widersprüche dokumentiert.
- [x] Noch kein Generator implementiert.
- [x] Noch kein Spielmodus implementiert.
- [x] Noch keine Datenbank implementiert.
- [x] Noch keine Flet-UI implementiert.

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

1. Verification Gate 1A fachlich abnehmen lassen.
2. Nach ausdrücklicher Freigabe Generatorversion 1 implementieren.
3. Validierung unmöglicher Generator-Konfigurationen implementieren.
4. Danach `time_attack` als isolierte headless State-Machine beginnen.
5. Weiterhin keine Datenbank, keine Flet-UI und kein Android-Build vor der dafür vorgesehenen Sitzung beginnen.

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
- Ob `allowed_tables` sortiert und dedupliziert wird; die Dokumentation tendiert zu einer kanonischen, validierten Tuple-Darstellung.
- Welche Standardwerte für `penalty_seconds` je Modus gelten.
- Welche Combo-Regeln als Standarddefinition gespeichert werden.
- Keine harten fachlichen Widersprüche für Gate 1A bekannt. `allowed_tables` wird für die Hashbildung als sortiertes, dedupliziertes Tuple validiert; diese Entscheidung ist in Tests und Modellvalidierung verankert.

---

## 9. Test- und Qualitätsstatus

Tests sind eingerichtet und laufen für die Gate-1A-Core-Basis. Letzter Lauf nach der Domainmodell-Anpassung: `python -m pytest` mit `15 passed`; `python -m ruff check .`, `python -m ruff format --check .` und `python -m pyright` erfolgreich.

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
| 2026-08-05 | Nächster offener Dokumentationsschritt erledigt: `legacy_excel_reference.md` und `game_rules.md` wurden an die verbindliche Legacy-Basis und die Ziel-Spielregeln angepasst. | erledigt |
| 2026-08-05 | Core-Domainmodelle, Antwortstatus, Zielmodus-Keys, Ergebnisverträge, Hash-Normalisierung und Hash-Tests an den Masterplan angepasst. | erledigt |
| 2026-08-07 | Viergeteiltes Hauptmenü, Excel-Presets, Editor, gewichteter Generator und vorläufige Rundenstatistik ergänzt. | begonnen |
| 2026-08-07 | Post-Beta-Plan in zwei Phasen gegliedert; Blitzrunde, Genauigkeit, PluMi Endless und Warm-up als getrennte headless Ablaufmodule implementiert. | erledigt |

## 10.1 Post-Beta-Erweiterungen

### Phase 1: keine SQLite-Abhängigkeit

- [x] Blitzrunde mit 30–60 Sekunden Zeitfenster und sitzungslokalem Leaderboard.
- [x] Genauigkeits-Modus ohne Zeitwertung.
- [x] PluMi Endless bis zum dritten Fehler.
- [x] 60-Sekunden-Warm-up mit expliziter Übergabe an das Hauptspiel.
- [x] Die vier Modi über eine eigene Flet-Ansicht spielbar machen; die fachlichen
  State-Machines bleiben dennoch getrennt.

Die Ablaufimplementierungen liegen getrennt unter `math_game/modes`. Sie teilen
weder eine Basisklasse noch eine State-Machine. Gemeinsame Verträge beschränken
sich weiterhin auf universelle Core-Typen.

### Phase 2: benötigt SQLite nach ADR-010

- [ ] Ghost-Modus gegen den persönlichen Vorwochenwert.
- [ ] Personal-Best-Tracker je Rechenart.
- [ ] Tages-Streak mit Freeze-Token.
- [ ] Stärken-/Schwächen-Heatmap.
- [ ] Spaced-Repetition-Fehlerwiederholung nach 1, 3 und 7 Tagen.
- [ ] Trendlinie „Richtige pro Minute“.

Diese Punkte werden erst begonnen, wenn das SQLite-Schema Sessions und
Aufgabenversuche dauerhaft, versioniert und testbar abbildet.

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
