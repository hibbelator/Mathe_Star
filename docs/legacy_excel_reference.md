# Legacy-Excel-Referenz

Dieses Dokument fasst die fachlich relevante Excel-Logik für `Mathe-Abenteuer` zusammen. Es ersetzt nicht die Zielregeln, sondern konserviert die Legacy-Basis, aus der die neue App abgeleitet wird. Die ursprüngliche Datei `Mathe_002 (1).xlsm` wird nicht mehr benötigt; maßgeblich sind die im Masterplan extrahierten Namen, Presets, Protokollspalten und bekannten Fehler.

Die VBA-Implementierung ist nur historische Referenz. Offensichtliche Excel- oder VBA-Probleme werden nicht portiert. Wenn Zielregel und VBA-Code voneinander abweichen, gilt die Zielregel.

---

## 1. Benannte Excel-Eingaben und Zielmodell

| Excel-Name | Bedeutung | Zielmodell |
|---|---|---|
| `addWk` | Gewicht Addition | `operation_weights.addition` |
| `subWk` | Gewicht Subtraktion | `operation_weights.subtraction` |
| `multWk` | Gewicht Multiplikation | `operation_weights.multiplication` |
| `divWk` | Gewicht Division | `operation_weights.division` |
| `Punkt_Reihen` | erlaubte Reihen, kommasepariert | `allowed_tables` |
| `min_faktor` | kleinster Faktor bzw. Mindestoperand | `factor_min` |
| `max_faktor` | größter zweiter Faktor | `factor_max` |
| `max_erg` | Obergrenze für Addition/Subtraktion | `add_sub_max_result` |
| `Spiel_Typ` | Spielmodus | `mode_key` und Modusparameter |
| `Spielname` | Anzeigename | `GamePresentation.display_name` |
| `Zeit_MaxTime` | Gesamtzeit des Zeitspiels in Minuten | `total_time_seconds` |
| `ZeitTime_MaxTime` | Gesamtzeit bei Gesamt- und Aufgabenzeit | `total_time_seconds` |
| `TimeAndTimePerTask_MaxTime` | Sekunden pro Aufgabe im kombinierten Zeitspiel | `per_task_time_seconds` |
| `MaxTasks` | feste Aufgabenanzahl | `task_count` |
| `MaxCorrect` | Zielzahl richtiger Antworten | `correct_target` |
| `TimePerTask_MaxTime` | Sekunden pro Aufgabe | `per_task_time_seconds` |

Die Excel-Zelle `Game_Typ` verweist auf dieselbe Zelle wie `Spiel_Typ` und hat keine eigenständige fachliche Bedeutung.

---

## 2. Excel-Spieltypen und Zielmodi

| Excel-Wert | Beabsichtigte Bedeutung | Zielmodus |
|---|---|---|
| `Zeit` | feste Gesamtzeit, möglichst viele richtige Aufgaben | `time_attack` |
| `Zeit&Zeit pro Aufgabe` | Gesamtzeit plus Deadline je Aufgabe | `time_attack` mit `per_task_time_seconds` |
| `Aufgaben` | feste Anzahl von Aufgaben, Zeit messen | `task_sprint` |
| `Richtige` | feste Zahl richtiger Antworten erreichen | `target_hunt` |
| `Zeit pro Aufgabe` | Deadline je Aufgabe | `per_task_timer` |
| `Kein Fehler` | Ende beim ersten Fehler | `perfect_run` |

Der zusätzliche Zielmodus `combo` hat kein Excel-Vorbild. Er wird später als eigener, versionierter Modus eingeführt.

---

## 3. Gewichtete Rechenart-Auswahl

Excel erzeugt technisch einen Pool, in dem jede aktivierte Rechenart entsprechend ihrem Gewicht mehrfach vorkommt. Die App muss diesen Pool nicht physisch aufbauen. Fachlich verbindlich ist nur die Wahrscheinlichkeit:

```text
P(Operation) = Gewicht(Operation) / Summe aller Gewichte
```

Verbindliche Validierung für die App:

- Gewichte sind ganze Zahlen größer oder gleich `0`.
- Mindestens ein Gewicht muss größer als `0` sein.
- Negative Gewichte sind ungültig.
- Die Auswahl muss bei festem Zufalls-Seed reproduzierbar sein.

---

## 4. Legacy-kompatibler Generator Version 1

Die erste App-Version verwendet `generator_version = 1`. Diese Version übernimmt die beabsichtigte Legacy-Verteilung, aber nicht die Excel-spezifische Umsetzung.

### 4.1 Addition

```text
num1 ∈ [factor_min, add_sub_max_result - factor_min]
num2 ∈ [factor_min, add_sub_max_result - num1]
result = num1 + num2
```

Eigenschaften:

- beide Operanden sind mindestens `factor_min`,
- das Ergebnis ist höchstens `add_sub_max_result`,
- die Summenverteilung ist nicht gleichmäßig, bleibt aber aus Legacy-Kompatibilitätsgründen erhalten.

Gültigkeitsbedingung:

```text
add_sub_max_result >= 2 * factor_min
```

### 4.2 Subtraktion

```text
num1 ∈ [factor_min, add_sub_max_result - 1]
num2 ∈ [factor_min, num1]
result = num1 - num2
```

Eigenschaften:

- Ergebnisse sind nie negativ,
- `0` ist erlaubt,
- `factor_max` beeinflusst Addition und Subtraktion in Generatorversion 1 nicht.

Gültigkeitsbedingung:

```text
add_sub_max_result - 1 >= factor_min
```

### 4.3 Multiplikation

```text
num1 ∈ allowed_tables
num2 ∈ [factor_min, factor_max]
result = num1 * num2
```

`add_sub_max_result` begrenzt Multiplikation in Generatorversion 1 nicht.

### 4.4 Division

```text
quotient ∈ allowed_tables
divisor ∈ [factor_min, factor_max]
dividend = quotient * divisor
result = quotient
```

Dadurch entstehen ausschließlich ganzzahlige Divisionen ohne Rest. Die Darstellung ist:

```text
dividend : divisor = quotient
```

`add_sub_max_result` begrenzt Division in Generatorversion 1 nicht.

---

## 5. Erlaubte Reihen

Excel liest `Punkt_Reihen` als kommaseparierte Liste, zum Beispiel:

```text
3,4,5,6,7,8,9
```

Die App normalisiert daraus eine validierte Liste positiver Ganzzahlen, zum Beispiel:

```python
allowed_tables = (3, 4, 5, 6, 7, 8, 9)
```

Die Legacy-Logik verwendete bei leerer Eingabe heimlich `(2, 3, 4, 5, 6, 7, 8, 9)`. Die App soll keine versteckte Voreinstellung verwenden. Wenn Multiplikation oder Division aktiviert ist, muss eine leere `allowed_tables`-Liste vor Spielbeginn als ungültig erkannt werden.

---

## 6. Gesuchtes Feld

Nach der Aufgabenbildung wählt Excel gleichverteilt eine Position aus `1`, `2` oder `3`.

| Wert | Gesucht |
|---|---|
| `1` | erster Operand |
| `2` | zweiter Operand |
| `3` | Ergebnis |

Beispiele:

```text
___ + 7 = 12
5 + ___ = 12
5 + 7 = ___
```

Diese Zufallsentscheidung gehört zum Generator und muss mit demselben gespeicherten Seed reproduzierbar sein.

---

## 7. Aufgaben- und Antwortzählung

Die Excel-Variable `tasksCompleted` zählt tatsächlich alle ausgewerteten Aufgaben, nicht nur richtige Antworten.

Für die App gelten diese normalisierten Begriffe:

```text
attempt_count = correct_count + wrong_count + no_input_count + timeout_count
```

`CANCELLED` ist ein Session- oder Abbruchstatus und zählt nicht als ausgewertete Aufgabe.

---

## 8. Legacy-TaskLog als fachliche Referenz

Die App importiert keine bestehenden Excel-Protokolle. Das Tabellenblatt `TaskLog` dient nur als Referenz für `TaskAttempt`.

| Spalte | Bedeutung |
|---|---|
| A | Spielnummer |
| B | Datum/Uhrzeit |
| C | Antwortzeit in Sekunden |
| D | erster Operand |
| E | Operator |
| F | zweiter Operand |
| G | Ergebnis |
| H | gesuchte Position 1–3 |
| I | Excel-Spieltyp |
| J | Fehlerart |
| K | Spielname |

Die App ersetzt die globale Spielnummer durch eine Session-ID, in der Regel eine UUID.

---

## 9. Excel-Presets

Die Excel-Presets definieren Recheninhalte. Der Spielmodus wurde separat gewählt.

| Name | Add | Sub | Mult | Div | Reihen | Min | Max | Add/Sub max. Ergebnis |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| Anfänger | 1 | 1 | 1 | 1 | 3–19 | 3 | 20 | 1000 |
| Mama Zettel | 0 | 0 | 1 | 0 | 3–9 | 2 | 10 | 100 |
| 1er | 0 | 0 | 50 | 50 | 3–9 | 2 | 10 | 100 |
| PluMi | 100 | 100 | 0 | 0 | 3–9 | 3 | 9 | 130 |
| PluMi_1Kl | 100 | 100 | 0 | 0 | 3–9 | 3 | 9 | 20 |
| Mama Zettel2 | 0 | 0 | 100 | 100 | 3–9 | 2 | 10 | 100 |
| MiLi | 100 | 0 | 100 | 0 | 3–9 | 3 | 9 | 300 |

Zusätzlich gespeicherte Moduswerte:

| Name | Zeit Minuten | Aufgaben | Kombi-Zeit Minuten | Sekunden je Aufgabe kombiniert | Sekunden je Aufgabe | Ziel richtige |
|---|---:|---:|---:|---:|---:|---:|
| Anfänger | 5 | 130 | 5 | 30 | 30 | 40 |
| Mama Zettel | 1 | 100 | 5 | 30 | 35 | 40 |
| 1er | 5 | 1 | 5 | 30 | 30 | 40 |
| PluMi | 5 | 130 | 5 | 30 | 30 | 40 |
| PluMi_1Kl | 5 | 130 | 5 | 30 | 30 | 40 |
| Mama Zettel2 | 5 | 1 | 5 | 30 | 30 | 40 |
| MiLi | 3 | 130 | 5 | 30 | 30 | 40 |

Die aktuell ausgewählte Excel-Konfiguration war `Mama Zettel` mit Spieltyp `Zeit`. Die aktive Zelle `MaxCorrect` enthielt unabhängig von der Preset-Tabelle den Wert `20`; diese Inkonsistenz wird nicht als verbindliche Preset-Regel übernommen.

---

## 10. Bekannte Excel-Fehler, die nicht portiert werden

### 10.1 Keine Eingabe wird überschrieben

Excel setzt zunächst `Keine Eingabe`, wandelt den leeren Wert dann aber zu `0` um und überschreibt den Fehler meistens mit `Rechenfehler`. Die App muss stattdessen unterscheiden:

- leere Bestätigung → `NO_INPUT`,
- abgelaufene Deadline → `TIMEOUT`,
- eingegebene falsche Zahl → `WRONG_RESULT`,
- Status bleibt nach der Auswertung unverändert.

### 10.2 Defekter Modus „Zeit pro Aufgabe“

Excel liest `maxTimePerTask`, prüft aber später die nie gesetzte Variable `maxTimeTask`. Die App verwendet ausschließlich `per_task_time_seconds`. Für den reinen Aufgabenzeitmodus gilt außerdem: mindestens `task_count` oder `total_time_seconds` muss gesetzt sein; Standard ist `task_count = 20`.

### 10.3 Unsicherer Excel-Timer

Excel nutzt verkettete globale `Application.OnTime`-Aufrufe. Die App verwendet stattdessen eine monotone Clock als einzige fachliche Zeitquelle. UI-Ticks dürfen nur Anzeigen aktualisieren und müssen nach Spielende ignoriert werden.

### 10.4 Gesamtzeit nur nach Antwort geprüft

Excel beendet Zeitspiele erst nach einer Antwort. Die App beendet ein Spiel bei erreichter Deadline auch ohne Eingabe. Für `time_attack` zählt eine offene Aufgabe bei Gesamtzeitablauf ohne eigenes Aufgabenlimit nicht automatisch als falsch.

### 10.5 Fehlerhafte TaskLog-Kopfzeile

Excel schreibt beim Anlegen von `TaskLog` in Spalte D versehentlich den Variablenwert `rechenfehler`. Die App verwendet ein neues JSON-Ergebnisschema und übernimmt diesen Fehler nicht.

### 10.6 Fehlerhafte Spielnummer beim ersten Fehler

Im Modus `Kein Fehler` kann Excel beim ersten Fehler eine falsche Spielnummer protokollieren. Die App verwendet eine Session-ID statt einer globalen laufenden Spielnummer.

### 10.7 Excel-Einstellungen werden nicht wiederhergestellt

Excel deaktiviert Berechnung und Bildschirmaktualisierung nicht zuverlässig rückstandsfrei. Diese Excel-spezifischen Befehle haben in der App keine Entsprechung.

### 10.8 Mitternachts- und Ereignisprobleme

Excel mischt `Now`, `Time` und `Timer`; `Timer` kann bei Mitternacht zurückspringen. Die App verwendet `Clock.monotonic()` für Laufzeiten und `Clock.utc_now()` für Zeitstempel.
