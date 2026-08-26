# Android-Build und private Verteilung

## Festgelegte Buildbasis

Die Anwendung verwendet **Flet 0.28.3** exakt. Der sichtbare Name ist
**Mathe-Abenteuer**, die unveränderliche Android-Package-ID wird aus `org =
"de.familie"` und dem Projektnamen `matheabenteuer` gebildet und lautet
`de.familie.matheabenteuer`. Version `0.1.0` hat die numerische Android-
Buildnummer `1`. Bei jedem Update wird die Buildnummer erhöht; die lesbare
Version folgt Semantic Versioning.

## Werkzeuge und reproduzierbarer Debug-Build

Benötigt werden Python 3.13, Git, ein JDK 17, das Android SDK mit Platform Tools
(`adb`) und der durch Flet eingerichtete Flutter-Toolchain. Ein sauberer Checkout
wird wie folgt gebaut:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install 'flet[all]==0.28.3' pytest ruff pyright
python -m pytest
python tools/generate_android_assets.py
flet build apk --debug
```

Flet lädt beim ersten Lauf die passenden Android-/Flutter-Komponenten; dieser
erste Lauf benötigt deshalb Internetzugang. Die APK liegt anschließend unter
`build/apk/` (üblicherweise `build/apk/app-debug.apk`). Installation und Start:

```bash
adb devices
adb install -r build/apk/app-debug.apk
adb shell monkey -p de.familie.matheabenteuer 1
```

Die drei Bilddateien in `assets/` werden unmittelbar vor dem Build deterministisch
aus `tools/generate_android_assets.py` erzeugt. Binärdateien werden damit nicht in
Git gespeichert; trotzdem verwendet die APK das eigene normale Symbol, den
adaptiven Android-Vordergrund und den eigenen Startbildschirm statt der
Flet-Standardgrafiken.

## Daten, Signatur und Updates

SQLite und kopierte Profilbilder liegen in Flets privatem
`FLET_APP_STORAGE_DATA`. Die App fordert daher keine allgemeine
Dateisystemberechtigung an. Das Schema wird über `PRAGMA user_version` migriert;
ein Update darf die App-Daten nicht löschen.

Ein Release wird **erst nach** erfolgreichem Debug-Gerätetest gebaut. Einen
Keystore außerhalb dieses Repositories erzeugen und an zwei sicheren Orten
sichern. Keystore und Passwörter niemals committen. Zum Aktualisieren muss stets
derselbe Schlüssel verwendet und die Buildnummer erhöht werden. Vor der privaten
Weitergabe sind Installation der älteren signierten APK, Anlage eines Profils
und anschließend `adb install -r` mit der neuen APK zu prüfen.

## Geräte-Smoke-Test (noch auszuführen)

Die automatisierten Prüfungen ersetzen keinen echten Gerätetest. Vor Phase 7
sind Modell, Android-Version, Tastatur (AOSP/Gboard/Samsung), APK-Version und das
Ergebnis für Profilanlage, normale Runde, Fehlversuch, Spezialmodus, Rennen,
Rotation, Vorder-/Hintergrund, Neustart und Datenwiederherstellung hier zu
protokollieren. Ohne diesen Nachweis wird kein dauerhafter Signaturschlüssel und
keine Release-APK erzeugt.
