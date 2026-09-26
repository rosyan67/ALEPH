# Globus mit echten Nachtlichtdaten, ein Globus statt zwei, Sabah und Süd-Belize

## Kurzfassung

- Der Globus zeigt jetzt die echten VNP46A3-Monate 2018-01 bis 2018-03, Zustand 4 („nur Afrika-Europa-Asien“). Evidenzstufe: beobachtet.
- Zellen außerhalb der Region sind blau gestreift und heißen „noch nicht geladen“. Sie sind nie dunkel und nie 0. Die Polkappen, für die NASA gar keine Kacheln liefert, heißen „keine Daten“.
- Die Stichproben stimmen: Berlin 11,3, Paris 50, Kairo 41 (Nil und Delta hell), Sahara 0, Amerika gestreift, die Krim als eigene Einheit.
- Es gibt jetzt nur noch einen Globus: `web/globus.html`. Das alte Gerüst mit erfundenen Beispieldaten heißt jetzt `web/geruest_beispieldaten.html` und ist rot als VERALTET markiert.
- Sabah (Anspruch der Philippinen) und Süd-Belize (Anspruch Guatemalas, IGH-Verfahren anhängig) sind eigene umstrittene Einheiten. Die Belege stammen von den Originalseiten, abgerufen am 26.09.2026.
- Tests: Worktree 635 bestanden, der Export-Test danach 27 bestanden; main 609 bestanden.
- Hochladen: main ja, ui-geruest nein. Grund: Im Verlauf von ui-geruest steckt der alte, zurückgezogene OpenRouter-Schlüssel. Die Entscheidung liegt beim Nutzer.

## Urteil

Das Ziel ist erreicht, mit den Einschränkungen unten. Die Karte zeigt nur gemessene Werte (beobachtet). Fehlende Daten erscheinen nie als dunkel. Es gibt drei eigene, gestreifte Klassen: „keine Daten“ (grau), „Datenlage unzureichend“ (braun) und „noch nicht geladen“ (blau).

Der Plausibilitätsprüfer hat einen Fehler gefunden, der behoben ist: Zellen in Kacheln, die NASA nie liefert (80–90° N, 70–90° S; 108 Positionen, 172 800 Zellen), standen als „noch nicht geladen … Download läuft“ da. Sie heißen jetzt „keine Daten“, wie in fertigen Monaten.

## Belege

### Phase A: Sabah und Süd-Belize (in ~/ALEPH, Commit 3991cf2)

| Einheit | Beleg für den Anspruch | Quelle, Abruf |
|---|---|---|
| Süd-Belize | IGH-Fall 177 „Guatemala's Territorial, Insular and Maritime Claim (Guatemala/Belize)“: Sondervereinbarung 8.12.2008, Protokoll 25.5.2015, Gerichtshof befasst seit 12.6.2019. Letzter Schritt ist der Beschluss vom 24.6.2022 (Fristen für Replik und Gegenreplik). **Ein Urteil gibt es nicht.** | icj-cij.org/case/177, 26.09.2026 13:27 UTC |
| Sabah / North Borneo | Republic Act 5446 (1968), Abschnitt 2: „the territory of Sabah, situated in North Borneo, over which the Republic of the Philippines has acquired dominion and sovereignty“. IGH-Fall 102: Die Philippinen beantragten am 13.3.2001 die Zulassung als Streithelfer; das wurde am 23.10.2001 abgelehnt. Über den Anspruch selbst hat der IGH nicht entschieden. | lawphil.net (RA 5446) und icj-cij.org/case/102, 26.09.2026 13:30 UTC |

- Der Prüfer hat alle Zitate an den Originalseiten gegengelesen, RA 5446 zusätzlich an der UN-Fassung.
- Die PDFs des IGH und das amtliche Gesetzblatt der Philippinen sind durch einen Cloudflare-Schutz gesperrt. Das wurde **nicht** umgangen; gelesen wurden die HTML-Fallseiten.
- Beide Einheiten gehören zur Kategorie „umstritten“ und folgen denselben Regeln wie die übrigen 87 Sondereinheiten. Die Einheitentabelle hat jetzt 326 Einheiten, davon 89 Sondereinheiten, und wurde neu gebaut. Eine Sicherung des alten Stands liegt unter `laender/zell_einheiten_stand_2026-09-25T2310Z`.
- **Abgrenzung:** Die Umrisse stammen aus Natural Earth 5.1.1 („umstrittene Gebiete“, B51 bzw. C04) und sind nicht selbst nachgezeichnet. Welchen Anspruch genau sie abbilden, sagt Natural Earth nicht. Das ist als offen vermerkt.
- **Einschränkung bei Sabah:** Der Umriss C04 deckt nur den Osten Sabahs ab (etwa 38 500 km²). Sandakan liegt darin, Kota Kinabalu nicht.

### Phase B: Globus

1. **Zwei Globusse.**
   - `web/index.html` war das Gerüst vom 23.09. mit erfundenen Beispieldaten. Es heißt jetzt `web/geruest_beispieldaten.html` und hat einen roten Hinweis „VERALTET“ im Titel und oben auf der Seite.
   - `web/globus.html` zeigt die echten Daten und wird behalten. „Globus öffnen.command“ öffnet diese Datei.
   - Ein neues `web/index.html` leitet auf `globus.html` weiter, damit alte Lesezeichen nicht auf die erfundenen Daten führen.
2. **main in ui-geruest übernommen.** Das ging ohne Konflikte (Commit „main (3991cf2) in ui-geruest übernommen“). Die 11 alten Testfehler im Worktree sind damit weg.
3. **Anzeige der Zustände 1 und 4.** Monate vor 2023 mit Zustand 1 oder 4 werden angezeigt; im Moment sind das 2018-01 bis 2018-03. Die Zählung je Monat (2018-01; zusammen 1 036 800 Zellen) sieht so aus:

   | Klasse | Zellen |
   |---|---|
   | mit Wert | 236 567 |
   | keine Daten | 179 617 (davon 172 800 Polkappen ohne NASA-Kachel) |
   | unzureichend | 57 416 |
   | noch nicht geladen | 563 200 |

   Die Kontrollzahlen stimmen: Die Region hat 188 Kacheln zu je 1 600 Zellen, also 300 800 Zellen. Es gibt 540 Kachelpositionen, die NASA liefert. 540 − 188 = 352 davon sind noch nicht geladen, und 352 × 1 600 = 563 200.
4. **Monatsauswahl mit Zustand.** Ein Eintrag lautet zum Beispiel „2018-01 · nur Afrika-Europa-Asien“. Bei Monaten mit Zustand 4 erscheint zusätzlich ein gelber Hinweiskasten.
5. **„Globus aktualisieren.command“.**
   - Der Befehl liest den Würfel neu und nimmt jeden Monat auf, der den Zustand 1 oder 4 erreicht. Ein Monat mit Zustand 4 wird nur ausgegeben, wenn sein Stufe-1-Nachweis zur Kachelliste passt (die Prüfung kommt aus `aleph/layers/vnp46a3.py`).
   - Neu ist, dass der Export erst in einen Hilfsordner schreibt und ihn ganz am Ende austauscht. Bricht er ab, zeigt der Globus weiter den alten, stimmigen Stand; das ist getestet.
   - Den Export habe ich von Hand ausgeführt: Er gibt 3 Monate aus, jeweils „nur Afrika-Europa-Asien“. Den Befehl selbst per Doppelklick, mit dem Öffnen von Chrome, habe ich nicht ausgeführt.
6. **Datenstand und Quelle auf der Seite.**
   - Quelle: „NASA VIIRS Black Marble VNP46A3 (LAADS DAAC)“.
   - Evidenzstufe: „beobachtet“.
   - Dazu der Abschnitt „Datenstand und Quellen“ mit dem Zustand je Monat und der Zählung der Zellen.

### Fotos (`berichte/2026-09-26_globus-echtdaten_bilder/`, Monat 2018-01)

| Nr. | Inhalt |
|---|---|
| 01, 09 | Europa/Afrika; Berlin angeklickt: 11 (100 % beobachtet) |
| 02 | Paris: 50 |
| 03 | Kairo 41, Nil und Delta hell, Sinai und Wüste dunkel |
| 04 | Sahara: 0, gemessen dunkel |
| 05 | Amerika blau gestreift: „noch nicht geladen“, nicht dunkel. Die dunklen Rechtecke sind Kacheln, die zur Region gehören und deshalb schon geladen sind, zum Beispiel Französisch-Guayana, Guadeloupe und Martinique, Clipperton. |
| 06 | Krim: eigene Einheit (UN-Eintrag: Ukraine, 804), Wert 2,4 |
| 07 | Sabah: eigene umstrittene Einheit mit Belegen im Fenster. Im Januar ist Borneo zu 58 % „unzureichend“, vermutlich wegen Wolken. |
| 08 | Süd-Belize: eigene umstrittene Einheit mit Belegen; die Zellen dort sind „noch nicht geladen“ |
| 10 | Arktis: Polkappe grau als „keine Daten“ (nach der Korrektur), Region Afrika-Europa-Asien mit Werten, Rest blau |

### Tests

- Worktree `~/ALEPH-ui`: 635 bestanden (ganze Suite, vor der Polkappen-Korrektur). Danach lief `tests/test_export_globus.py`: 27 bestanden, darunter der neue Test für die Polkappen.
- `~/ALEPH` (main): 609 bestanden (ganze Suite, 26.09.2026, nach Commit 3991cf2).

### Plausibilitätsprüfung (Agent, 26.09.2026)

Ergebnis: **plausibel mit Vorbehalt**. Nachgerechnet aus den gepackten Monatsdateien wurden:

| Ort | Wert |
|---|---|
| Berlin | 11,3 |
| Kairo | 40,8 |
| Simferopol | 2,43 |
| Sahara | 0 |
| Atlantik | Code 254 |

Die Reihenfolge der Helligkeit ist plausibel: Kairo ist heller als Khartum, Seoul heller als Pjöngjang.

Vorbehalte:
1. **Polkappen falsch beschriftet.** Behoben, siehe Urteil; Test und Foto 10.
2. **Winterwerte schwanken stark.** Moskau: Januar 68, Februar „unzureichend“, März 148 bei 56 % beobachtet. Vor jeder Aussage über Veränderungen von Monat zu Monat im Winter muss das mit dem `statistik-pruefer` geklärt werden. Offen.
3. **Höchstwert im Januar: 234,9** an der Küste bei Phan Thiet (Vietnam). Vermutung: Fischereiboote mit starkem Licht. Nicht geprüft. Offen.
4. **Streifen beim Zoomen.** Sie wachsen mit, und in starker Vergrößerung kann eine einzelne blaue Zelle einfarbig wirken. Offen, das Risiko ist gering.
5. **Name „Sabah / North Borneo“.** Er klingt nach dem ganzen Bundesstaat, der Umriss ist aber nur der Osten. Außerdem ist der Anspruch nur für 1968 und 2001 belegt; eine mögliche neuere Quelle ist pna.gov.ph/articles/1269457 (nicht gelesen). Offen, siehe Empfehlung.
6. **Veralteter Text im Kopf von `aleph/export/globus.py`.** Behoben.

## Umfang

- **~/ALEPH (main):**
  - `aleph/layers/sondereinheiten.yaml`
  - `tests/test_zell_einheiten.py`
  - Nachtrag in `berichte/2026-09-26_zell-laender-zuordnung.md`
  - `LOG.md`
  - Die Einheitentabelle auf der SSD wurde neu gebaut.
- **~/ALEPH-ui (ui-geruest):**
  - `aleph/export/globus.py`
  - `web/globus.html`, `web/globus.js`, `web/globus.css`
  - `web/index.html` (neu, Weiterleitung) und `web/geruest_beispieldaten.html` (umbenannt, als veraltet markiert)
  - `tests/test_export_globus.py`
  - dieser Bericht und die Fotos
- **Nicht angefasst:**
  - der laufende Download (Prozess 63920)
  - `aleph/layers/vnp46a3*.py`, die Kachellisten und `scripts/`; der Würfel wurde nur gelesen
- **Keine Daten aus 2023–2025** angezeigt oder verwendet. Die Monatsauswahl endet hart vor 2023-01.

## Empfehlung

1. **Hochladen von ui-geruest selbst entscheiden.**
   - Der Commit 4d08637 mit dem alten OpenRouter-Schlüssel liegt schon in main auf GitHub. Der Schlüssel ist laut Nutzer zurückgezogen.
   - Ein Hochladen von ui-geruest würde also nichts Neues preisgeben, aber der Commit gehört zu seinem Verlauf, und die Regel sagt: nicht hochladen.
   - Die Wahl ist: entweder trotzdem hochladen, oder den Verlauf mit `git filter-repo` bereinigen. Letzteres schreibt die Geschichte um; alle Kopien müssen danach neu geholt werden.
2. **Sabah umbenennen**, zum Beispiel in „Ost-Sabah (Teil des philippinischen Anspruchs auf Sabah / North Borneo)“. Dafür muss die Einheitentabelle neu gebaut werden. Außerdem die PNA-Meldung lesen, um den heutigen Stand des Anspruchs zu belegen.
3. **Winterwerte im Norden** (Moskau, Stockholm) mit dem `statistik-pruefer` prüfen, bevor Monatsvergleiche gezeigt werden.

## Nicht geprüft

- „Globus aktualisieren.command“ per Doppelklick, mit dem Öffnen von Chrome. Der Export darin ist geprüft.
- Die PDFs des IGH und das amtliche Gesetzblatt der Philippinen, weil sie durch Cloudflare gesperrt sind.
- Ob die Umrisse von Natural Earth genau die Ansprüche abbilden.
- Die UN-Einstufung von Sabah und Belize.
- Die Ursache der festen „keine Daten“-Blöcke im Nordwestpazifik und Nordatlantik (etwa 1 230 Zellen). Vermutet wird eine Füllmaske des Produkts; das Handbuch ist nicht gelesen.
- Die Helligkeit der Krim und der Ukraine 2018 gegen eine Vergleichsquelle.
- Die Darstellung in einem echten Browser mit Grafikkarte; die Fotos entstanden mit Chrome ohne Fenster und Software-WebGL.

## So benutzt du es (drei Schritte)

1. Im Finder `~/ALEPH-ui` öffnen und **„Globus aktualisieren.command“** doppelklicken. Es liest die neuesten fertigen Monate ein und öffnet dann den Globus. Klappt das Einlesen nicht, zeigt der Globus den letzten Stand.
2. Links oben unter **„Monat“** einen Monat wählen. Der Zusatz sagt, wie vollständig er ist, zum Beispiel „nur Afrika-Europa-Asien“. Blau gestreift heißt noch nicht geladen, grau heißt keine Daten, braun heißt zu wenig Messungen. Keins davon bedeutet „dunkel“.
3. Auf ein Land oder eine gestrichelte Fläche **klicken**. Das Fenster zeigt den Nachtlichtwert der Zelle und die Einheit. Bei umstrittenen Gebieten stehen dort auch Anspruch, Verwaltung und Quelle.
