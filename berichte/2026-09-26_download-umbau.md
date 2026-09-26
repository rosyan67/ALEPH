# Download-Umbau VNP46A3: sichern, Stillstands-Erkennung, Messung, Neustart

Stand: 2026-09-26, 12:45 UTC · Lauf neu gestartet 12:13 UTC (Prozess 63920)

## Kurzfassung

- Die Reparatur vom 25.09. und die Ergebnisse vom 26.09. sind gesichert (3 Commits, nicht gepusht). Vorher liefen 567 von 567 Tests grün.
- Die starre 4-Stunden-Frist ist ersetzt: Ein Monat gilt erst nach **30 Minuten ohne neue, geprüfte Kachel** als hängend. Dazu gibt es eine Notbremse nach 12 Stunden und eine zutreffende Meldung.
- Messung: 1 Verbindung 1,69 MB/s, 3 Verbindungen 2,06 MB/s, 5 Verbindungen 2,31 MB/s. **Die Leitung bremst**, nicht die einzelne Verbindung. Eingestellt sind jetzt 5 gleichzeitige Downloads.
- Die neue Hochrechnung reicht bis zum 21. bis 26.10. (obere Grenze nach dem 25.10.). Deshalb habe ich den **Vorrang Afrika-Europa-Asien** gebaut: erst 188 Kacheln für alle Monate (Zustand 4), dann die übrigen Kacheln. Weggelassen wird nichts.
- Zwei Prüfungen durch den `statistik-pruefer`, jeweils „bestanden mit Auflagen“. Alle Auflagen sind umgesetzt und getestet.
- Neustart um 12:13 UTC mit **Ampel OK**. Der erste Monat (2018-01) war nach 19 Minuten für Afrika-Europa-Asien vollständig, mit 1,98 MB/s, 0 verworfenen Kacheln und 0 Wiederholungen.
- Hochrechnung: Afrika-Europa-Asien ist etwa **8. bis 10.10.** vollständig, alles etwa **21. bis 26.10.**, wenn der Durchsatz bleibt.
- Tests nach dem Umbau: 602 grün. Nach der letzten Status-Korrektur ist die Zahl im Abschnitt „Belege“ nachgetragen.

## Urteil

Der Download ist repariert und läuft wieder. Die Hauptursache der Zurückstellungen, die starre Gesamtfrist, ist beseitigt. Die Geschwindigkeit begrenzt die Internetleitung (etwa 2,3 MB/s, rund 18 Mbit/s); im Code lässt sich das nicht weiter verbessern. Afrika-Europa-Asien wird voraussichtlich deutlich vor dem 1.11. vollständig. Für den ganzen Datensatz ist der 1.11. erreichbar, aber knapp; jede Störung verschiebt das Ende.

## Belege

### Phase A – Sichern
- Testsuite vor den Commits (Arbeitskopie, der Download lief weiter): **567 passed**, 0 übersprungen, 276,7 s.
- `82802f2`: die Reparatur vom 25.09.
  - `vnp46a3.py` mit dem Fix `komposit_masked`
  - `vnp46a3_kachelpositionen.txt`
  - `vnp46a3_lauf.py`, `vnp46a3_status.py`
  - `scripts/vnp46a3_start.sh`
  - `tests/conftest.py`, `test_vnp46a3*.py`
  - aus `ARCHITECTURE.md` die Absätze „Vollständigkeit“, „Stand der Layer“ und der GPM-Block (unverändert übernommen). Aufgeteilt habe ich mit `git apply --cached` auf einen Teil-Patch.
- `f3b69bc`: die Ergebnisse vom 26.09.
  - Weltbank-Gebiete, Zell-Länder-Zuordnung (`un_m49.py`, `zell_einheiten.py`, `sondereinheiten.yaml`, `natural_earth.py`, Tests, Steckbriefe)
  - Diagnose-Bericht, Sitzungsübersicht, Nachtrag Ländergrenzen
  - `ARCHITECTURE.md`, Absatz „Länderzuordnung“
  - `LOG.md`
  - Keine Daten.
- `0ff8001`: Schlüssel aus `.claude/settings.json` entfernt. Die Historie ist nicht umgeschrieben; der Schlüssel steht weiter in `4d08637`.
- Vor jedem Commit habe ich nach Schlüsselmustern gesucht: keine Treffer.

### Phase B1 – Anhalten
- Einen eingebauten Stopp-Weg gibt es nicht. Ich habe deshalb am 26.09. um 07:43 UTC das normale Beenden-Signal (SIGTERM) an Prozess 41131 geschickt.
- Vorher notiert:
  - 2018-05 lud gerade: 285 fertige Kachel-Dateien, 3 angefangene.
  - Im Würfel war kein Monat auf Zustand 3 („wird geschrieben“), also wurde gerade nichts in den Würfel geschrieben.
  - Monatszustände: 134 × 0, 22 × 2.
- Danach: kein Lauf-Prozess mehr, Ampel „GESTOPPT“.

### Phase B2 – Messung
- **networkQuality** (macOS 12.7.6): zweimal Zeitüberschreitung beim Apple-Messserver. Gemessen wurden Download 0,32 bzw. 0,06 Mbit/s und Upload 13,2 bzw. 5,5 Mbit/s. Der Mac war dabei sonst still (4 kB/s).
- Gleichzeitig lieferten fremde Server je Verbindung 0,64 MB/s (proof.ovh.net) bzw. 1,09 MB/s (nbg1-speed.hetzner.com). Das Apple-Ergebnis ist deshalb nicht verwertbar; die Ursache ist nicht geklärt.
- **NASA-Durchsatz:** echte, noch fehlende Kacheln von 2018-05, normal abgelegt und gegen Größe und MD5 geprüft, je 5 Minuten. Gemessen am Empfang des Macs.
  - Der erste Versuch war ungültig: Der Mac schlief um 09:57:55 wegen Untätigkeit ein (`pmset -g log`: „Entering Sleep state due to 'Idle Sleep'“; Einstellung `sleep 1`). Mein Messprogramm lief ohne `caffeinate`. Der echte Download startet mit `caffeinate`.
  - Wiederholung mit `caffeinate`, 10:40–11:02 MESZ:

| gleichzeitig | Durchsatz | geprüfte Kacheln im Fenster | Fehler |
|---|---|---|---|
| 1 | 1,69 MB/s | 10 (479 MB) | 0 |
| 3 | 2,06 MB/s | 9 (523 MB) | 0 |
| 5 | 2,31 MB/s | 10 (512 MB) | 0 |

- **Urteil der Messung:** Eine Verbindung holt schon 73 % dessen, was mit fünf geht. Die Grenze setzt also die Leitung. Zum Vergleich: Am 23./24.09. kamen etwa 6,8 MB/s an. Die Leitung ist seitdem deutlich langsamer; warum, ist nicht geprüft.
- Eingestellt: 5 gleichzeitige Downloads (`scripts/vnp46a3_start.sh`, erstes Argument).

### Phase B3 – Umbau (Commit `8541064`)
- **a) Stillstand statt Gesamtfrist:**
  - `vnp46a3.py` `_sammle_kacheln`: `STILLSTAND_SEKUNDEN = 30 min` ohne neue, gegen Größe und MD5 geprüfte Kachel führt zu `DownloadHaengt`. Die Begründung steht an der Konstante.
  - `MONAT_NOTBREMSE_SEKUNDEN = 12 h` führt zu `DownloadZuLangsam` mit eigener Meldung.
  - Gemessen wird mit der monotonen Uhr, eine Uhrumstellung verfälscht also nichts.
- **b) Meldungen:** „Stillstand - seit 30 Minuten ist keine neue, geprüfte Kachel mehr fertig geworden (…)“ bzw. „Notbremse - … obwohl noch Kacheln ankommen (…)“. Die alte Meldung „reagiert seit über 240 Minuten nicht mehr“ gibt es nicht mehr.
- **c) Zurückgestellte Monate:**
  - Die Liste der Zurückgestellten lebte nur im laufenden Prozess. Beim Neustart bildet der Lauf die Reihenfolge neu aus dem Würfel, mit `--vorrang 2018-01..2019-12,2024-01`. 2018-01 bis 2018-04 kommen also zuerst.
  - Geprüfte Kacheln werden wiederverwendet. Beleg: „2018-01: 167 Kacheln aus einem früheren Versuch schon vorhanden und gültig (Größe und MD5 geprüft), 0 verworfen“.
  - Test: `test_zurueckgestellte_monate_2018_kommen_nach_neustart_zuerst`.
- **d) Protokoll:** Je Monat eine Zeile „Download-Statistik (vollständig geladen | abgebrochen)“ mit Kachelzahl, GB, Minuten, MB/s geprüfte Nutzdaten, nach Größen- oder MD5-Prüfung verworfenen Kacheln und Wiederholungen. Beispiel 2018-01: 21 Kacheln, 1,3 GB, 10,6 Minuten, 1,98 MB/s, 0 verworfen, 0 Wiederholungen.
- **e) Status-Skript** (`vnp46a3_status.py`):
  - zeigt den Durchsatz (laufender Monat ab Download-Beginn sowie die zuletzt vollständig geladenen Monate),
  - rechnet je Stufe hoch, als Spanne und mit ausgeschriebenen Annahmen,
  - zeigt beide Fortschritte getrennt.
  - **Nach dem Neustart berichtigt:** Das Durchsatz-Fenster zählte die Prüfzeit am Monatsanfang mit (0,5 statt 1,76 MB/s). Die Ampel zeigte fälschlich „HÄNGT“, weil sie an alten Dateien im Rohordner maß; dieser Fehler bestand schon vor dem Umbau. Beides ist mit Tests behoben.
- **f) Speicher:**
  - Rohdaten eines Monats werden weiterhin erst gelöscht, wenn er geprüft im Würfel steht (Zustand 1: ganzer Rohordner). In Stufe 1 werden nur die geschriebenen Region-Kacheln gelöscht; die übrigen, schon vorhandenen Kacheln bleiben für Stufe 2 liegen.
  - Beim Neustart: SSD 829 GB frei, Rohdaten 161 GB, davon 100 GB außerhalb der Region.
  - Zusätzlich bleiben nur die Region-Rohdaten zurückgestellter Monate liegen (etwa 15 GB je Monat).
  - Der Speicherwächter (50 GiB) hat damit reichlich Platz. Gelöscht habe ich nichts.
- **g)** 5 gleichzeitige Downloads (siehe B2).
- **Auflagen der ersten Prüfung (A1–A5):**
  - A1: Fingerabdruck (Inode, Größe, Änderungszeit) jeder geprüften Datei. Er wird vor der Vollständigkeitsprüfung und noch einmal direkt vor dem Verkleinern verglichen; wurde eine Datei verändert, wird Größe und MD5 neu geprüft.
  - A2: Das Zeitlimit je Kachel wächst mit der Größe, mindestens 0,1 MB/s je Verbindung, also 26 Minuten für die größte Kachel.
  - A3: Eine Abbruch-Runde trägt erst alle fertigen Kacheln ein.
  - A4/A5: genauere Wörter in Statistik und Hochrechnung; „nicht als fertig markiert“ steht nur noch, wenn der Würfel das bestätigt.

### Phase C3/C4 – Hochrechnung und Vorrang nach Region
- **Hochrechnung vor dem Umbau:**
  - Rest 4,2–5,0 TB (156 Monate × 28–33 GB, abzüglich 0,16 TB Rohdaten).
  - Bei 1,9–2,3 MB/s sind das 22–31 Tage, Ende etwa 18. bis 27.10.
  - Die obere Grenze liegt nach dem 25.10., also habe ich den Vorrang gebaut.
- **a) Kachelliste:** `aleph/layers/vnp46a3_kacheln_afrika_europa_asien.txt`, **188 Kacheln**, abgeleitet mit `aleph/layers/vnp46a3_regionen.py`.
  - Regel: eine Kachel der Referenzliste mit mindestens einer 0,25°-Zelle, deren Flächenanteil > 0 einer Einheit gehört, deren UN-M49-Region Africa, Europe oder Asia ist.
  - Quellen: `laender/zell_einheiten` (erstellt 2026-09-25T23:10:39Z) und M49-Abruf 20260925T224431Z. Beide stehen mit Prüfsumme im Dateikopf.
  - Besonderheiten (ebenfalls im Kopf):
    - 9 Kacheln nördlich 80° N liefert NASA nicht (h19v00–h27v00).
    - 12 gemischte Kacheln, meist Überseegebiete, die Natural Earth dem Mutterstaat zuordnet, z. B. Französisch-Guayana. Sie sind mit drin; das verlängert Stufe 1 etwas, verliert aber nichts.
    - Einheiten ohne M49-Region außerhalb der Liste liegen alle in Amerika, Ozeanien oder der Antarktis.
  - Datenanteil der Region: 14,9 von 33,1 GB (45 %). Grundlage ist das Manifest 2024-01, nur die Dateigrößen. Das ist eine technische Prüfung der Datenlieferung, keine inhaltliche Auswertung von 2023–2025.
- **b) Reihenfolge:** `--region-zuerst afrika_europa_asien`.
  - Stufe 1 lädt für alle offenen Monate nur die Region (Reihenfolge wie bisher: Vorrang 2018 bis 2019 und 2024-01, dann ab 2018, dann davor).
  - Stufe 2 lädt die übrigen Kacheln. Bei Zustand 4 wird mit dem Region-Teil aus dem Würfel vereinigt, sonst der ganze Monat geladen.
  - Jede Stufe hat ihr eigenes Nachholen.
- **c) Zustand 4** „vollständig nur für Afrika-Europa-Asien“:
  - Die Vollständigkeit gilt je Stufe gegen Katalog und Referenzliste, beide auf die Positionen beschnitten.
  - Die Grenze „beim Anbieter nicht vorhanden“ (höchstens 10) wird immer für den **ganzen** Monat geprüft (Auflage B2).
  - Stufe 1 schreibt eine Prüfsumme der Kachelliste ins Manifest. Stufe 2 vereinigt nur, wenn Liste und Stufe-1-Nachweis passen und der Katalog keine in Stufe 1 fehlende Region-Kachel neu meldet; sonst lädt sie den ganzen Monat neu (Auflage B1).
- **d) Lesen:**
  - `vorhandene_monate` und alle bisherigen Lesefunktionen in `aleph/detect/wuerfel.py` liefern weiter nur Zustand 1. Ein Monat mit Zustand 4 kann dort also nie als 0 oder dunkel erscheinen.
  - Neu: `lies_monate_mit_region`. Sie setzt außerhalb der Region jede Variable, auch die Zähler, auf NaN und liefert eine Maske `nicht_geladen`. Die Layer-Fassung bildet die Maske selbst aus der geprüften Liste.
  - Test: `test_zustand_4_zaehlt_nicht_als_vorhanden_und_wird_nie_als_0_gelesen`.
- **e) Status:** „Vollständig für Afrika-Europa-Asien (Zustand 4 oder fertig): x von 156“ neben „Fertige Monate“, dazu die Hochrechnung für Stufe 1 und für alles.
- **f) statistik-pruefer**, zweite Prüfung: „bestanden mit Auflagen“.
  - A1–A5 sind erfüllt.
  - Stufe 1 öffnet keine stille Lücke; kein Leser sieht Zellen außerhalb der Region als 0.
  - Auflagen vor Stufe 2: B1 (Kachelliste an Zustand 4 binden), B2 (Grenze je Monat). Dazu: Manifest je Stufe, Hochrechnung korrigiert, fehlende Tests.
  - Alles ist umgesetzt, mit Tests: Liste geändert führt zum Neuladen des ganzen Monats; Stufe 1 gescheitert führt dazu, dass Stufe 2 den ganzen Monat lädt; die Grenze über den ganzen Monat.
- **g) Hochrechnung** (Status-Skript um 12:45 UTC, 2,0 MB/s aus 2018-01):
  - Stufe 1: 2,0–2,3 TB, **12–14 Tage, etwa 08.10. bis 10.10.2026**. Das ist eher zu hoch, weil vorhandene Rohdaten nicht abgezogen sind.
  - Alles: 4,2–5,0 TB, **25–30 Tage, etwa 21.10. bis 26.10.2026**.
  - Annahme: Der Durchsatz bleibt so; Zurückstellungen und Wiederholungen sind nicht eingerechnet.

### Phase C – Neustart
- `scripts/vnp46a3_start.sh` um 12:13:03 UTC: „Gestartet (Prozess-Nummer 63920), gleichzeitige Downloads: 5.“
- Erste Protokollzeilen: „Lauf gestartet: … gleichzeitig=5 …“, „Stufe 1 (Afrika-Europa-Asien, 188 Kacheln): 156 Monate offen, erster Monat 2018-01.“
- Prüfung nach 15 Minuten (12:28 UTC): **AMPEL: OK**, „Keine Fehler seit Lauf-Start“, Kacheln kommen an. Der Durchsatz lag, nachgerechnet seit Download-Beginn, bei 1,76 MB/s.
- Um 12:32 UTC: „2018-01: fertig für Afrika-Europa-Asien, 188 Kacheln, … Dauer gesamt 19.1 Minuten“; 2018-02 begonnen.
- Danach habe ich nicht weiter beobachtet (nur die Ampel nach der Status-Korrektur einmal geprüft: OK).

### Tests
- Nach dem Umbau: **602 passed**, 0 übersprungen (517,9 s).
- Neu: `tests/test_vnp46a3_stillstand.py` und `tests/test_vnp46a3_region.py`.
- Geändert: `test_lade_monat_meldet_kachelzahl`, der jetzt auch die Statistik-Zeile prüft.
- Nach der Status-Korrektur: siehe Nachtrag am Ende.

## Umfang

- **Geändert:**
  - `aleph/layers/vnp46a3.py`, `vnp46a3_lauf.py`, `vnp46a3_status.py`
  - `scripts/vnp46a3_start.sh`
  - `aleph/detect/wuerfel.py` (nur eine neue Funktion; die bisherigen sind unverändert)
  - `ARCHITECTURE.md` Abschnitt 5
  - Tests
- **Neu:** `aleph/layers/vnp46a3_regionen.py`, die Kachelliste, zwei Testdateien, dieser Bericht.
- **Nicht angefasst:**
  - der worktree `~/ALEPH-ui`. Dort filtert der Globus-Export auf Zustand 1, zeigt Zustand-4-Monate also nicht; nur die Beschriftung von Zustand 4 fehlt dort.
  - `.env`
  - Branches: kein Wechsel, nichts gepusht.
- **Rohdaten:** Nur die Messung hat Kacheln von 2018-05 dazugeladen (geprüft, im normalen Ordner). Gelöscht wurde nichts außer dem, was der Lauf nach Design löscht.
- **Zeitraum 2023–2025:** nicht ausgewertet. Nur die Dateigrößen im Manifest 2024-01 habe ich technisch gelesen.
- **Agenten:** `statistik-pruefer` zweimal (siehe oben). Der `plausibilitaets-pruefer` wurde nicht eingesetzt: Es gibt kein neues inhaltliches Ergebnis, nur Technik und Hochrechnung.

## Empfehlung

1. **Schneller geht es nur über die Leitung.**
   - Den Mac per Kabel ans Netz hängen oder näher an den Router stellen (WLAN-Signal −64 dBm).
   - Andere große Übertragungen im Heimnetz vermeiden.
   - Beim Anbieter prüfen, ob der Anschluss derzeit weniger liefert als am 23./24.09. (damals mindestens 6,8 MB/s, heute etwa 2,3).
   - Mehr als 5 gleichzeitige Downloads bringen laut Messung kaum etwas.
2. **Mac-Einstellung:** Ruhezustand nach 1 Minute ist für den Download unkritisch, weil er `caffeinate` nutzt. Für andere lange Arbeiten sollte man das wissen.
3. Den Globus-Export im worktree bei Gelegenheit um die Beschriftung von Zustand 4 ergänzen. Anzeigen soll er solche Monate erst, wenn die Oberfläche „nicht geladen“ darstellen kann (`lies_monate_mit_region`).
4. Ob das NASA-Archiv nach dem 1.11. abrufbar bleibt, ist weiter unbestätigt. Mit dem Vorrang ist Afrika-Europa-Asien voraussichtlich Anfang Oktober sicher.

## Nicht geprüft

- Warum die Leitung langsamer ist als am 23./24.09.; ob WLAN, Anschluss oder Anbieter.
- Das Ergebnis von `networkQuality`: Der Apple-Server war nicht erreichbar.
- Ob doppelte Datenströme bei sehr langsamer Leitung (unter 0,1 MB/s je Verbindung) auftreten; bekannter Rest, bewusst nicht in earthaccess eingegriffen.
- Der Region-Anteil von 45 % ist nur an einem Monat gemessen (2024-01).
- Der Verlauf nach 12:45 UTC; wie beauftragt nicht weiter beobachtet.

## Nachtrag Tests (nach der Status-Korrektur)

- `.venv/bin/python -m pytest -q` → **605 passed**, 0 übersprungen (367,6 s). Neu dazugekommen sind 3 Tests zur Status-Anzeige (Durchsatz ab Download-Beginn, Teilstufe, kein falsches „HÄNGT“).
