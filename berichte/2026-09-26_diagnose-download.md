# Diagnose: Warum ist seit dem 25.09. kein VNP46A3-Monat fertig geworden?

Stand: 2026-09-26, 09:07–09:50 MESZ · Nur gelesen, nichts geändert · Download-Prozess 41131 unberührt

## Kurzfassung

- **Es gibt keinen Hänger.** Jeder Monat seit dem Neustart lief genau 4 Stunden und wurde dann zurückgestellt (2018-01 bis 2018-04). Die Kacheln kamen die ganze Zeit gleichmäßig an, die längste Pause war 2,9 Minuten.
- **Ursache:** Die „240 Minuten“ sind eine feste **Gesamtfrist je Monat** (`vnp46a3.py`, Z. 1031). Sie erkennen keinen Stillstand, und die Meldung „reagiert seit über 240 Minuten nicht mehr“ ist deshalb irreführend.
- **Warum die Frist jetzt reißt:** Der Download ist drei- bis viermal langsamer als am 23./24.09. (jetzt etwa 1,7–2 MB/s, damals etwa 6,8 MB/s). Außerdem hat ein Monat jetzt 540 statt 460 Kacheln (33,1 statt 28,7 GB, gemessen an 2024-01). Ein Monat braucht so etwa 4,6–5,4 Stunden.
- Wo der Engpass liegt (Leitung, WLAN oder NASA/CloudFront), ist **offen**. Die Messungen deuten eher auf die Leitung, beweisen es aber nicht, siehe Belege.
- **Neues Risiko:** Zurückgestellte Monate behalten ihre Rohdaten (etwa 22–26 GB je Monat), bis sie am Ende nachgeholt werden. Bei 835 GB frei ist die SSD nach rund 32 weiteren Monaten (etwa 5 Tage, also um den 1.10.) an der 50-GB-Grenze, und der Lauf bricht ab. Das ist eine Hochrechnung.
- **Hochrechnung:** So wie der Lauf jetzt eingestellt ist, wird er nicht fertig, auch nicht vor dem 1.11. Mit 1,7–2 MB/s und ohne die beiden Hindernisse bräuchte er etwa 25–35 Tage (Ende etwa 21.10. bis 1.11., also am oder knapp vor dem 1.11.), mit 6,8 MB/s etwa 8–9 Tage.
- **1.11.2026:** Laut NASA endet dann die Lieferung *neuer* Suomi-NPP-Daten. Ob das Archiv (VNP46A3 2013–2025) danach abrufbar bleibt, sagt die Seite nicht: **unbestätigt**.
- **Code:** Die ganze Reparatur vom 25.09. ist nicht committet; `vnp46a3_kachelpositionen.txt` kennt Git gar nicht. Der laufende Prozess nutzt diese uncommittete Fassung.

## Urteil

Von den vier Möglichkeiten trifft **d) etwas anderes** zu: Eine Gesamtfrist je Monat ist bei gesunkener Datenrate zu kurz.
- a) Der Download hängt nicht. Es gibt keine Netz-, Server- oder Anmeldefehler im Protokoll, und die Kacheln kommen stetig.
- b) Ist unwahrscheinlich, aber nicht ganz auszuschließen, weil MD5-Verwürfe nicht protokolliert werden.
- c) Kein Monat kommt überhaupt bis zum Schreiben in den Würfel.

Der Download ist nicht kaputt. Aber so wie er eingestellt ist, wird er nicht fertig. Eine Entscheidung liegt bei dir (Empfehlung).

## Belege

### Teil 1.1 – Zustand (26.09., 07:07 UTC)
- `scripts/vnp46a3_status.sh`: **AMPEL: OK**, „Prozess: läuft (Nr. 41131)“, „Fertige Monate: 0 von 156“, „Keine Fehler seit Lauf-Start“, „Aktuell: 2018-05, Download, 222 von 538 Kacheln im Rohordner, seit 98 Minuten“.
- Die Restzeit-Angabe „etwa 9 bis 12 Tage“ im Status beruht auf den alten, schnellen Monaten mit 460 Kacheln und ist überholt.
- `ps`: gestartet am Fr 25.09. um 15:28:14 MESZ, läuft seit 17 h 41 min, **2,2 % CPU**, 164 MB Arbeitsspeicher, 17 Threads. `caffeinate` (Prozess 41132) hält den Mac wach.
- `lsof`: 6 offene Verbindungen zu CloudFront (99.86.253.x:443), eine geschlossene. Es gibt keine aufgestauten Verbindungen; ein angefangener Download, der nicht mehr beendet wird, würde weitere offene Verbindungen hinterlassen.
- Netz, gemessen mit `nettop` in 20-s-Abschnitten: Der Prozess empfängt etwa **1,8–2,2 MB/s** (35,0 bzw. 43,7 MB je 20 s). Der ganze Mac empfängt etwa 2,3 MB/s (`netstat`, en0, 60 s). WLAN „Vodafone-8539“, Signal −64 dBm, Sende-Übertragungsrate 78 von höchstens 217 Mbit/s.
- Kein VPN im Weg: `route get 99.86.253.53` zeigt Schnittstelle en0, Gateway 192.168.0.1. Der Cisco-VPN-Dienst läuft zwar, aber der Weg zu NASA führt nicht darüber.
- Kein anderer Download-Prozess läuft.

### Teil 1.2 – Zeitleiste seit dem Neustart
Protokoll `protokoll/vnp46a3.log` auf der SSD, Lauf gestartet 25.09. 13:28:16 UTC (15:28 MESZ). Erste Zeile: „gleichzeitig=3 … Vorrang für 25 Monate (2018-01 bis 2024-01), 0 von 156 Monaten bereits fertig“. Die Kachelzahlen je Stunde stammen aus den Änderungszeiten der Dateien im Rohordner.

| Monat | Beginn (UTC) | Ende (UTC) | Zustand | Kacheln fertig (Protokoll) | Katalog | neu je Stunde (1./2./3./4. h) | größte Pause |
|---|---|---|---|---|---|---|---|
| 2018-01 | 25.09. 13:28 | 17:28 | zurückgestellt | 499 / 540 | 540 | 127 / 124 / 113 / 135 | 2,9 min |
| 2018-02 | 17:28 | 21:28 | zurückgestellt | 491 / 540 | 540 | 126 / 142 / 103 / 120 | 2,2 min |
| 2018-03 | 21:28 | 26.09. 01:28 | zurückgestellt | 404 / 540 | 540 | 116 / 88 / 93 / 107 | 2,4 min |
| 2018-04 | 01:28 | 05:28 | zurückgestellt | 430 / 540 | 540 | 105 / 102 / 98 / 125 | 2,3 min |
| 2018-05 | 05:28 | läuft | Download | 222 / 538 um 07:07 | 538 | 135 / 87 / … | 1,9 min |

- „Fertig“: kein Monat. „Beim Anbieter nicht vorhanden“: kein Fall; 2018-05 meldet 538 statt 540 Kacheln, der Monat ist aber nicht beendet.
- Im Rohordner liegen je Monat 3 Dateien mehr, als das Protokoll nennt (z. B. 502 statt 499). Nach der Frist laufen die 3 gerade aktiven Downloads noch zu Ende (`pool.shutdown(wait=False, cancel_futures=True)`, Z. 1066: wartende Kacheln werden gestrichen, nur die laufenden laden zu Ende).
- Zum Vergleich der Lauf vom 23./24.09. (Protokoll): 2018-01 „fertig, 460 Kacheln … Download 71.7“ Minuten; 2018-02 73,8; 2018-03 69,7; 2018-04 78,0; 2019-10 74,5 Minuten.

### Teil 1.3 – Warum kein Monat fertig wird
1. **Die Frist gilt je Monat, nicht je Stillstand.** `vnp46a3.py` Z. 1031: `frist = start_zeit + DOWNLOAD_TIMEOUT_SEKUNDEN` (Z. 202: `4 * 60 * 60`). Z. 1044 wartet mit `as_completed(..., timeout=max(frist - time.time(), 0))`. Z. 1057–1061 erzeugt bei Ablauf den Text „Download reagiert seit über 240 Minuten nicht mehr“. Ob Kacheln kommen, spielt dafür keine Rolle. Alle vier Zurückstellungen liegen auf etwa 2 Sekunden genau 4 Stunden nach „Download beginnt“: 13:28:20 → 17:28:22, 17:28:26 → 21:28:25, 21:28:33 → 01:28:32, 01:28:43 → 05:28:42.
2. **Die Kacheln kommen stetig** (Tabelle oben, größte Pause unter 3 Minuten). Das spricht gegen a) Hänger. Das Protokoll enthält seit dem Start keine Zeile mit Fehler, 403, 5xx oder ABBRUCH.
3. **Die Datenrate reicht nicht für 4 Stunden.**
   - Nach dem Manifest `2024-01.tsv` hat ein Monat mit 540 Kacheln 33,1 GB, die alten 460 Kacheln davon 28,7 GB. Die 80 früher fehlenden Kacheln sind 4,4 GB, vor allem h28–h35.
   - Die Kacheln sind im Median 57,8 MB groß (0,7 bis 158,5 MB). Im Rohordner 2018-01 liegen 502 Dateien mit 26,3 GB.
   - Früher: 28,7 GB in etwa 70 Minuten ≈ 6,8 MB/s. Jetzt: gemessen 1,8–2,2 MB/s, aus den Dateien errechnet etwa 115 Kacheln/h × 53 MB ≈ 1,7 MB/s.
   - 33 GB bei 2 MB/s ≈ 4,6 Stunden, bei 1,7 MB/s ≈ 5,4 Stunden, also mehr als die Frist von 4 Stunden.
4. **b) MD5- oder Größenprüfung:** Verworfene Kacheln und Wiederholungen je Kachel werden **nicht protokolliert** (`_lade_und_pruefe_kachel` Z. 819–846, `_lade_kachel` Z. 737–816). Ich kann sie also nicht zählen.
   - Der Durchsatz im Netz (etwa 2 MB/s) und die fertigen Dateien (etwa 1,7 MB/s) liegen nah beieinander. Viele doppelt geladene Kacheln sind damit unwahrscheinlich. Das ist eine Vermutung.
   - Die Vollständigkeitsprüfung kommt gar nicht erst zum Zug, weil der Monat vorher an der Frist endet.
5. **c) Übernahme in den Würfel:** Kommt nicht vor. Im ganzen Protokoll seit dem Neustart gibt es keine Zeile „Download fertig“ und kein „Verkleinern und Schreiben“.
6. **Warum der Download langsamer ist: Vermutung, nicht belegt.**
   - Kurzer Test am 26.09. gegen 09:30 MESZ, während der NASA-Download weiterlief: Einzelne Verbindungen zu fremden Servern bekamen nur 0,71 MB/s (proof.ovh.net) bzw. 0,12 MB/s (ash-speed.hetzner.com). Ein Test bei Cloudflare lieferte keine Daten.
   - Zusammen mit etwa 2,3 MB/s Gesamtempfang deutet das auf eine volle Leitung von grob 3 MB/s (etwa 25 Mbit/s) hin. Am 23./24.09. waren es mindestens 6,8 MB/s.
   - Die Tests sind schwache Belege: Sie liefen gleichzeitig mit dem Download, einzelne Verbindungen sind durch die Entfernung begrenzt (vor allem der US-Server), und „etwa 3 MB/s“ ist nur grob addiert. Die WLAN-Übertragungsrate von 78 Mbit/s (etwa 9,7 MB/s) spricht eher **gegen** das WLAN als Engpass.
   - Mögliche Ursachen: der Anschluss selbst, andere Geräte im Heimnetz, WLAN-Schwankungen oder eine Drosselung durch NASA/CloudFront. **Welche davon zutrifft, ist offen.**
   - Nicht geprüft: eine Messung ohne laufenden Download, eine Messung per Kabel.

### Teil 1.4 – Die „Hänger“ bei 2018-03 und 2018-04
Es gab keine. Die letzten Protokollzeilen davor sind jeweils nur Start und „Download beginnt“:
```
2026-09-25 21:28:25 UTC  2018-03: Start 2026-09-25 21:28:25 UTC.
2026-09-25 21:28:33 UTC  2018-03: 540 Kacheln bei NASA gemeldet (Katalog: 540 Treffer, alle geholt; Referenzliste 540 Positionen), Download beginnt.
2026-09-26 01:28:32 UTC  2018-03: ZURÜCKGESTELLT … Download reagiert seit über 240 Minuten nicht mehr (404 von 540 Kacheln fertig).
2026-09-26 01:28:43 UTC  2018-04: 540 Kacheln bei NASA gemeldet (…), Download beginnt.
2026-09-26 05:28:42 UTC  2018-04: ZURÜCKGESTELLT … (430 von 540 Kacheln fertig).
```
In den 4 Stunden kamen 404 bzw. 430 Dateien an, 88–125 pro Stunde (3 weitere je Monat erst nach Fristende). Die Statusabfrage vom 26.09. um 00:04 UTC im Globus-Bericht zeigte 2018-03 mit 258 Kacheln bei laufender Bewegung.

### Teil 1.5 – Speicher
- SSD: 835 GB frei von 1000 GB. Mac: 135 GB frei von 500 GB. Speicherwächter: `MIN_FREI_GB = 50` (`io.py` Z. 23), geprüft vor jedem Monat (`vnp46a3_lauf.py` Z. 381).
- Rohdaten jetzt: 156 GB. 2018-01 26,3 · 2018-02 26,2 · 2018-03 21,8 · 2018-04 23,0 · 2018-05 11,8 (läuft) · 2019-05 24,7 · 2019-11 21,9 GB.
- Zurückgestellte Monate werden erst nach dem Durchgang über alle offenen Monate nachgeholt (`vnp46a3_lauf.py` Z. 399–430). Bis dahin bleiben ihre Rohdaten liegen.
- Für heute spielt der Platz keine Rolle. **Hochrechnung:** Bei etwa 24 GB je zurückgestelltem Monat ist die Grenze nach (835 − 54) / 24 ≈ 32 Monaten erreicht, also nach etwa 5,3 Tagen bei 4 Stunden je Monat. Dann folgt „ABBRUCH … Speicher“ (`BLOCKER`, Z. 382–384). Voraussetzung ist, dass es beim jetzigen Tempo bleibt.
- Beim Nachholen werden gültige Kacheln wiederverwendet (`_sichte_rohordner`, Z. 1014–1023). Die 4 Stunden je Monat sind also nicht verloren.

### Teil 1.6 – Hochrechnung und 1.11.2026
- Datenmenge für alle 156 Monate: etwa 4,4–5,2 TB (28–33 GB je Monat; hochgerechnet aus 2024-01 und 2018-01).
- Bei 2 MB/s sind das etwa 25–30 Tage reine Ladezeit, beim aus den Dateien errechneten Wert von 1,7 MB/s etwa 30–35 Tage, bei 6,8 MB/s etwa 8–9 Tage. Dazu kommen je Monat etwa 6 Minuten Verkleinern und Schreiben (etwa 16 Stunden gesamt).
- Heute ist der 26.09., bis zum 1.11. sind es 36 Tage. Bei 1,7–2 MB/s endet der Lauf am oder knapp vor dem 1.11. Das gilt nur, wenn weder die Monatsfrist noch der Speicher bremsen. **So wie der Lauf jetzt eingestellt ist, reicht es nicht** (Speicher, siehe 1.5).
- **Offizielle Quelle:** NASA Earthdata, „Suomi NPP Data Product Delivery to Cease on November 1, 2026“ (https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026; veröffentlicht 7.8.2026 laut Abruf, im Seitentext „last Updated: Sept. 23, 2026“). Den Wortlaut habe ich selbst im abgerufenen Seitentext gelesen:
  - „Delivery of new science data from the Suomi National Polar-orbiting Partnership (Suomi NPP) satellite will cease at 13:00 Universal Time (UTC) on November 1, 2026 (2026/305), NOAA's National Environmental Satellite, Data, and Information Service (NESDIS) announced on August 3, 2026.“
  - „NASA archives and distributes data from Suomi NPP through Earthdata and multiple distributed data archive centers.“
  - Zu bereits archivierten Daten nach dem 1.11. sagt die Seite nichts. Also **unbestätigt**, weder belegt noch ausgeschlossen.
  - Die NOAA-Mitteilung (NESDIS) habe ich nur als Suchtreffer gesehen, nicht gelesen.

### Teil 2.1 – Stand des Codes (`~/ALEPH`, Branch main, nichts gewechselt)
- Letzter Commit: `0070c88`. Letzte Commits der Download-Dateien:
  - `vnp46a3.py` 4d08637 (25.09. 11:01)
  - `vnp46a3_lauf.py` und `vnp46a3_status.py` 05681bc (24.09.)
  - `scripts/vnp46a3_start.sh` 434888a (23.09.)
- **Die Reparatur vom 25.09. ist nicht committet.** `git diff --stat`:
  - `vnp46a3.py`: +711 Zeilen (Katalogabfrage ohne `count=1000`, Größen- und MD5-Prüfung, Manifest mit drei Zuständen, Status 2/3)
  - `vnp46a3_lauf.py`: +99 (u. a. `--vorrang`)
  - `vnp46a3_status.py`: 2
  - `scripts/vnp46a3_start.sh`: 8
  - `tests/test_vnp46a3.py`: 132
  - `tests/test_vnp46a3_fehlerverhalten.py`: 15
- **Git gar nicht bekannt:**
  - `aleph/layers/vnp46a3_kachelpositionen.txt`
  - `tests/test_vnp46a3_katalog.py`, `tests/conftest.py`
  - aus Phase 3: `un_m49.py`, `zell_einheiten.py`, `sondereinheiten.yaml`, deren Tests und Steckbriefe, drei Berichte vom 26.09.
- Außerdem uncommittet: `.claude/settings.json` (Schlüssel entfernt), `ARCHITECTURE.md`, `LOG.md`, `natural_earth.py`, `docs/sources/natural_earth.md`, `berichte/2026-09-25_laendergrenzen.md`.
- Der laufende Prozess nutzt die uncommittete Fassung: `vnp46a3.py` und `vnp46a3_lauf.py` wurden zuletzt am 25.09. um 15:03 MESZ geändert, der Prozess startete um 15:28 MESZ.

### Teil 2.2 – Der „Tippfehler“-Fix
Die Aufgabe war in der Nachricht abgeschnitten („Zeige denr…“). Ich habe sie als „zeige den Unterschied“ verstanden. `git diff aleph/layers/vnp46a3.py`, Abschnitt in `_lies_kachel`:
```
@@ -433,7 +531,7 @@ def _lies_kachel(pfad: Path) -> dict[str, np.ndarray]:
                 mittel = np.nanmean(komposit_masked, axis=(1, 3))
                 mittel_beobachtet = np.nanmean(
-                    np.where(beobachtet_bloecke, komposit, np.nan), axis=(1, 3)
+                    np.where(beobachtet_bloecke, komposit_masked, np.nan), axis=(1, 3)
                 )
```
- `komposit` hat die Form 2400 × 2400, die Maske `beobachtet_bloecke` die Form 40 × 60 × 40 × 60. Die fehlerhafte Zeile bricht deshalb mit „operands could not be broadcast“ ab. Die korrigierte Zeile nutzt die schon in Blöcke umgeformte, maskierte Fassung.
- Eingeführt wurde der Fehler mit Commit **4d08637** („GPM IMERG …“; `git log -S`).
- Er hat am 25.09. um 09:20 UTC den Monat 2019-05 abstürzen lassen. Protokoll: „ValueError: operands could not be broadcast together with shapes (40,60,40,60)“.
- In der Arbeitskopie ist er behoben, und der laufende Prozess nutzt die behobene Fassung. Committet ist die Behebung nicht; deshalb scheitern im worktree `~/ALEPH-ui` 11 Tests.

## Umfang

- Nur gelesen: Status-Skript, Protokoll, Manifeste, Rohordner (nur Dateigrößen und Zeitstempel), Code, `git status/log/diff`, Prozess- und Netzwerkdaten.
- Zwei kurze Geschwindigkeitstests von je 15 s gegen öffentliche Testserver. Sie haben den Download für diese Zeit etwas gebremst.
- Eine Webseite von NASA abgerufen.
- Nicht angefasst: Prozess 41131, der Würfel, alle Projektdateien außer diesem Bericht und dem LOG-Eintrag; kein Branchwechsel, kein Commit, `.env` nicht geöffnet.
- Zeitraum 2023–2025: nicht berührt. Das Manifest 2024-01 habe ich nur technisch gelesen (Kachelgrößen); das ist eine technische Prüfung der Datenlieferung.
- Plausibilitäts-Prüfer: siehe Nachtrag unten.

## Empfehlung

Alle Punkte ändern den Download und sind deshalb **deine Entscheidung**. Umgesetzt habe ich nichts.
1. **Die Monatsfrist ersetzen oder anheben.** Statt „4 Stunden gesamt“ auf echten Stillstand prüfen, etwa „seit X Minuten keine neue Kachel“. Die Meldung sollte sagen, was wirklich passiert ist. Kurzfristig würde es schon helfen, die Frist z. B. auf 8 Stunden anzuheben. Das geht nur mit einem Neustart; gültige Kacheln werden dabei wiederverwendet.
2. **Speicherfalle entschärfen.** Einen zurückgestellten Monat sofort erneut versuchen, wenn nur die Frist abgelaufen ist. Oder die Zahl zurückgestellter Monate mit liegenden Rohdaten begrenzen. Sonst stoppt der Lauf in etwa 5 Tagen am Speicherwächter.
3. **Netz prüfen.** Eine Geschwindigkeitsmessung ohne laufenden Download, am besten per Kabel, zeigt, ob die Leitung selbst langsamer geworden ist.
4. **Protokollieren.** Wiederholungen je Kachel und MD5-Verwürfe ins Protokoll schreiben, damit b) künftig messbar ist.
5. **Committen.** Die Reparatur vom 25.09. einschließlich `vnp46a3_kachelpositionen.txt` und des `komposit_masked`-Fixes. Das empfiehlt der Übersichtsbericht schon; danach im worktree `ui-geruest` main erneut übernehmen.
6. **Wegen des 1.11. vorsorglich:** Bei NASA/LAADS nachfragen oder nachlesen, ob archivierte VNP46A3-Daten nach dem 1.11. abrufbar bleiben. Falls nicht, 2018–2022 zuerst fertig laden.

## Nicht geprüft

- Ob einzelne Kacheln still wiederholt oder nach einer MD5-Abweichung neu geladen wurden (nicht protokolliert).
- Die Leitungsgeschwindigkeit ohne laufenden Download, und warum sie gegenüber dem 23./24.09. gesunken ist.
- Ob NASA/CloudFront einzelne Verbindungen drosselt.
- Die Größe aller 156 Monate; hochgerechnet wurde nur aus 2024-01 und 2018-01.
- Die NOAA-Mitteilung im Wortlaut; ob das NASA-Archiv nach dem 1.11. erreichbar bleibt.
- Der Teil von Teil 2.2 nach „Zeige den…“, weil die Nachricht dort abgeschnitten war.

## Nachtrag: Plausibilitäts-Prüfer

Eingesetzt wurde ein allgemeiner Agent mit der Anleitung aus `.claude/agents/plausibilitaets-pruefer.md`. Urteil: „plausibel mit Vorbehalt“.
- **Bestätigt:**
  - Die 4 Stunden sind eine Gesamtfrist je Monat und keine Stillstandserkennung.
  - Alle Rechnungen stimmen.
  - Nachholen erst am Ende, Rohdaten bleiben liegen, gültige Kacheln werden wiederverwendet, MD5-Verwürfe werden nicht protokolliert.
  - Das „unbestätigt“ zum NASA-Archiv ist richtig.
- **Berichtigt:**
  - Zeilennummern (1044, 1057–1061, 1066), selbst nachgesehen.
  - 404/430 statt 407/433 Dateien in 4 Stunden.
  - Engpass „offen“ statt „weniger wahrscheinlich NASA“.
  - Hochrechnung mit der Spanne 1,7–2 MB/s (25–35 Tage, ein Monat 4,6–5,4 Stunden).
  - „auf etwa 2 Sekunden“ statt „auf die Sekunde“.
- Der Prüfer nannte als Aktualisierungsdatum der NASA-Seite den 25.09.2026. Im Seitentext habe ich selbst „last Updated: Sept. 23, 2026“ gelesen und diesen Wert übernommen.
- Der Prüfer hatte keinen Zugriff auf Protokoll, SSD und Prozessdaten. Diese Werte hat er nur auf innere Stimmigkeit geprüft. Teil 2 hat er nicht geprüft.
