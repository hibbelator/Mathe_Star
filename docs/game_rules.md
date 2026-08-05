# Verbindliche Spielregeln

Dieses Dokument beschreibt die fachlichen Zielregeln für `Mathe-Abenteuer`. Es ist konkreter als die Legacy-Referenz und legt fest, wie die neue App die beabsichtigte Rechen- und Spiellogik behandeln soll.

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

Mindestfelder:

```python
@dataclass(frozen=True)
class GameDefinition:
    id: str
    mode_key: str
    rules_version: int
    generator_version: int

    operation_weights: OperationWeights
    allowed_tables: tuple[int, ...]
    factor_min: int
    factor_max: int
    add_sub_max_result: int
    missing_positions: tuple[int, ...]

    total_time_seconds: float | None
    per_task_time_seconds: float | None
    task_count: int | None
    correct_target: int | None
    penalty_seconds: float
    combo_rules: ComboRules | None
```

Darstellungsdaten wie Anzeigename, Motiv, Favorit, Sichtbarkeit und Sortierung gehören nicht in den Hash-Inhalt. Sie werden separat als `GamePresentation` behandelt.

---

## 3. Definition-ID und Vergleichbarkeit

Die `game_definition_id` entsteht aus einem normalisierten JSON-Payload:

```python
canonical_json = json.dumps(
    normalized_definition,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)

definition_id = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
```

Hashrelevant sind:

- `mode_key`,
- `rules_version`,
- `generator_version`,
- Rechenarten und Gewichte,
- Zahlen- und Faktorenbereiche,
- erlaubte Reihen,
- gesuchte Positionen,
- relevante Zeitlimits,
- relevante Aufgaben- oder Zielzahlen,
- Strafregeln,
- Combo-Regeln.

Nicht hashrelevant sind:

- Anzeigename,
- Farbe,
- Motiv,
- Ton,
- Vibration,
- reduzierte Animation,
- Favorit,
- Sortierung.

Nicht verwendete Felder müssen kanonisch normalisiert werden. Beispiel: Hat ein Modus keine Gesamtzeit, darf ein alter Wert in `total_time_seconds` den Hash nicht verändern.

---

## 4. Antwortstatus

Alle Modi verwenden ausschließlich diese Statuswerte:

```python
class AnswerStatus(Enum):
    CORRECT = "correct"
    WRONG_RESULT = "wrong_result"
    NO_INPUT = "no_input"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
```

Bedeutung:

- `CORRECT`: Die eingegebene Zahl entspricht exakt dem erwarteten Wert.
- `WRONG_RESULT`: Es wurde eine Zahl eingegeben, aber sie ist falsch.
- `NO_INPUT`: Es wurde ohne gültige Zahl bestätigt.
- `TIMEOUT`: Eine Aufgaben- oder Modusdeadline wurde überschritten.
- `CANCELLED`: Die Aufgabe oder Session wurde bewusst abgebrochen und zählt nicht als ausgewerteter Versuch.

Ein einmal ermittelter Status darf nicht später durch UI-Code überschrieben werden.

---

## 5. Zählregeln

Für jede abgeschlossene Runde gilt:

```text
attempt_count = correct_count + wrong_count + no_input_count + timeout_count
```

`CANCELLED` zählt nicht als ausgewertete Aufgabe. Abbrüche können im Session-Ergebnis dokumentiert werden, dürfen aber nicht heimlich als falsche Aufgabe in die Auswertung eingehen.

---

## 6. Legacy-kompatibler Generator Version 1

Der Generator ist noch nicht in Sitzung 1A implementiert, seine Zielregeln sind aber verbindlich dokumentiert.

### Addition

```text
num1 ∈ [factor_min, add_sub_max_result - factor_min]
num2 ∈ [factor_min, add_sub_max_result - num1]
result = num1 + num2
```

Gültigkeitsbedingung:

```text
add_sub_max_result >= 2 * factor_min
```

### Subtraktion

```text
num1 ∈ [factor_min, add_sub_max_result - 1]
num2 ∈ [factor_min, num1]
result = num1 - num2
```

Gültigkeitsbedingung:

```text
add_sub_max_result - 1 >= factor_min
```

### Multiplikation

```text
num1 ∈ allowed_tables
num2 ∈ [factor_min, factor_max]
result = num1 * num2
```

### Division

```text
quotient ∈ allowed_tables
divisor ∈ [factor_min, factor_max]
dividend = quotient * divisor
result = quotient
```

Division erzeugt in Version 1 ausschließlich ganzzahlige Aufgaben ohne Rest.

---

## 7. Gesuchte Position

Nach Aufgabenbildung wird eine erlaubte gesuchte Position aus `missing_positions` gewählt. Für Legacy-Kompatibilität sind die kanonischen Positionen:

| Wert | Gesucht |
|---|---|
| `1` | erster Operand |
| `2` | zweiter Operand |
| `3` | Ergebnis |

Diese Auswahl ist Teil des Generators und muss durch den gespeicherten Seed reproduzierbar sein.

---

## 8. Zeit- und Deadline-Regel

Alle Modi verwenden `Clock.monotonic()` als fachliche Zeitquelle. UI-Ticks dürfen nur anzeigen und keine fachliche Zeitentscheidung ersetzen.

Grenzregel:

```text
event_time <= deadline  → rechtzeitig
event_time > deadline   → Deadline überschritten
```

Diese Regel gilt unabhängig davon, ob UI-Callback oder Timer-Callback zuerst eintrifft.

---

## 9. Ziel-Spielmodi

### 9.1 `time_attack`

- feste Gesamtzeit,
- Ziel: möglichst viele richtige Aufgaben,
- primärer Rekordwert: `correct_count`,
- Tie-Breaker: weniger Fehler, danach geringere durchschnittliche Antwortzeit richtiger Antworten,
- optional zusätzlich `per_task_time_seconds`,
- offene Aufgabe bei Gesamtzeitablauf ohne Aufgabenlimit zählt nicht automatisch als falsch.

### 9.2 `task_sprint`

- feste `task_count`,
- jede ausgewertete Aufgabe zählt zum Fortschritt,
- Ziel: niedrigste Wertungszeit,
- `effective_time = elapsed_time + penalty_seconds`,
- Standardstrafe pro nicht richtiger Aufgabe: `2` Sekunden,
- reine Zeit und Strafzeit werden getrennt gespeichert.

### 9.3 `perfect_run`

- Ende beim ersten Status ungleich `CORRECT`,
- Hauptwertung: richtige Serie vor dem Fehler,
- optionales Gesamtzeitlimit,
- Zusatzpunkte dürfen die Serienwertung nicht verfälschen.

### 9.4 `target_hunt`

- feste `correct_target`,
- falsche Antworten erhöhen den Ziel-Fortschritt nicht,
- Ziel: niedrigste Wertungszeit,
- Standardstrafe pro nicht richtiger Aufgabe: `2` Sekunden,
- Spiel endet unmittelbar beim Erreichen des Ziels.

### 9.5 `per_task_timer`

- jede Aufgabe besitzt `per_task_time_seconds`,
- Standard: `task_count = 20`,
- mindestens `task_count` oder `total_time_seconds` muss gesetzt sein,
- Timeout erzeugt `TIMEOUT` und automatisch die nächste Aufgabe,
- primärer Rekordwert: `correct_count`,
- Tie-Breaker: weniger Fehler, danach geringere Summe der Antwortzeiten richtiger Aufgaben.

### 9.6 `combo`

Standardspiel:

```text
task_count = 30
base_points = 100
```

Multiplikator anhand der Serie nach der richtigen Antwort:

| Serie | Multiplikator |
|---:|---:|
| 1–4 | ×1 |
| 5–9 | ×2 |
| 10–14 | ×3 |
| ab 15 | ×4 |

Regeln:

- richtige Antwort: `base_points * multiplier`,
- nicht richtige Antwort: `0` Punkte und Serie auf `0`,
- keine Zufallsboni,
- primärer Rekordwert: Gesamtpunkte,
- Tie-Breaker: höhere richtige Anzahl, danach geringere Gesamtantwortzeit.

---

## 10. Ergebnisvertrag

Ein Spielmodus liefert genau einmal ein standardisiertes Ergebnis:

```python
GameSessionResult(
    session_id=session_id,
    game_definition_id=definition.id,
    mode_key=definition.mode_key,
    started_at_utc=started_at,
    finished_at_utc=finished_at,
    end_reason=end_reason,
    summary=summary,
    attempts=attempts,
    random_seed=random_seed,
    result_schema_version=1,
)
```

Die interne State-Machine eines Modus bleibt für den Core eine Blackbox.
