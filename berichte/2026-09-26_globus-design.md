# Globus im Design des alten Gerüsts, mit echten Nachtlichtdaten

Stand: 2026-09-26 · Ort: worktree `~/ALEPH-ui`, Branch `ui-geruest` · Geändert: `web/globus.html`, `web/globus.css`, `web/globus.js`, neu `web/vendor/fonts/` · Fotos: `berichte/2026-09-26_globus-design_bilder/`

## Kurzfassung

- `web/globus.html` hat jetzt den Aufbau und das Aussehen des alten Gerüsts. Daten und Beispielinhalte der Vorlage sind nicht übernommen.
- Die Datenlogik ist Zeichen für Zeichen unverändert: Laden, Selbsttest, Farbskala und Muster. Der Prüfer hat das mit `git show` verglichen.
- Die Stichproben stimmen wie vorher: Berlin 11, Paris 50, Kairo 41 (Nil und Delta hell), Sahara unter 0,1, Amerika „noch nicht geladen“, Polkappe „keine Daten“, Krim eigene Einheit (2,4).
- Die Legende ist immer sichtbar. Quelle, Datenstand und Evidenzstufe „beobachtet“ stehen fest in der Zeitleiste.
- Tests: ganze Suite 636 bestanden. Nach den letzten Korrekturen lief `test_export_globus.py` erneut mit 27 bestanden.
- Plausibilitäts-Prüfer: „plausibel mit Vorbehalt“. Alle 7 Punkte sind umgesetzt, darunter ein alter Fehler: Die Streifenrichtung in der Legende war vertauscht.
- Offen für eine spätere Sitzung: die Einheit „Sabah / North Borneo“ in der Einheitentabelle (in ~/ALEPH) umbenennen, siehe Empfehlung 1.

## Urteil

Das Ziel ist erreicht. Alle sechs Pflichtpunkte des Auftrags sind erfüllt, soweit ich sie hier prüfen konnte. Die Grenze liegt bei Punkt 5: Wie flüssig die Seite läuft, ist nur mit Software-Grafik gemessen (siehe Nicht geprüft).

**Was das Design der Vorlage ausmacht** (Fotos `v0_vorlage_geruest.jpg`, `v0b_vorlage_filter.jpg`, `v0c_vorlage_detail.jpg`):
- **Aufbau:**
  - Der Globus liegt mittig und füllt den ganzen Bildschirm, mit einem leichten dunklen Rand (Vignette).
  - Oben verläuft eine Kopfleiste ins Dunkle. Links sitzt ein Knopf „Filter“, in der Mitte die Marke „ALEPH“ mit goldenem Schild und darunter ein breites Suchfeld, rechts Knöpfe für die Ansicht.
  - Links fährt eine dunkle Leiste heraus.
  - Rechts schiebt sich ein helles, papierfarbenes „Dossier“ vor den Globus. Die Leitidee im Code heißt „Kartenblick gegen Aktenblick“.
  - Unten in der Mitte liegt eine Zeitleiste mit Regler und Datenverfügbarkeit.
- **Farben:**
  - Nachtblau-Schwarz (#070a12, Leisten #0d1220).
  - Gold als einzige Akzentfarbe (#d9a441, #f0c876).
  - Papier für das Dossier (#e7e0cb, Schrift dunkelbraun #241f14).
- **Schrift:**
  - Fraunces, eine Serifenschrift, für die Marke und die Überschriften.
  - IBM Plex Sans für alles Übrige.
- **Bedienelemente:**
  - Knöpfe mit dünnem Rand und kleinen Rundungen.
  - Aktive Elemente haben einen goldenen Rand.
  - Goldene Häkchen und Reglerknöpfe.
  - Das Dossier ist in Felder aufgeteilt, jeweils kleines Etikett über dem Wert, getrennt durch feine Linien.

**Was davon übernommen ist:**
- **Kopfleiste:**
  - Links „Ebenen und Quellen“.
  - Mitte „ALEPH“ mit dem Schild „Nachtlicht · Evidenzstufe: beobachtet“ und darunter ein Suchfeld „Land oder Gebiet suchen“. Das Suchfeld durchsucht nur die 326 Einheiten der Einheitentabelle.
  - Rechts „Ganze Erde“.
- **Linke Leiste:** Ebenen an- und ausschalten, Liste der 89 Sondereinheiten, Datenstand und Quellen.
- **Dossier rechts beim Anklicken:**
  - Kennzeichen der Einheit.
  - Name und UN-Eintrag.
  - Kasten „Nachtlicht“ mit Wert oder Klasse.
  - Alle Felder der Einheitentabelle.
- **Zeitleiste unten:**
  - Monatsregler mit Pfeiltasten und dem Zustand je Monat.
  - Hinweis bei „nur Afrika-Europa-Asien“.
  - Die Zeile mit Quelle, Evidenzstufe und Datenstand.
- **Legende:** eine feste Karte unten links, die man nicht schließen kann.

**Nicht übernommen:**
- Die erfundenen Anomalien, Theorien und Orte.
- Die Filter nach Anomalie-Typ und Stärke; dafür gibt es noch keine echten Daten.
- Die fremde Hintergrundkarte.
- Die flache Karte.
- Die Balken „Datenverfügbarkeit“: Der Export liefert heute nur eine Zählung, keinen Zustand je Monat. Ich wollte den Export nicht ändern.

## Belege

**Die sechs Pflichtpunkte:**

| Nr. | Anforderung | Beleg |
|---|---|---|
| 1 | Echte Nachtlichtdaten, Monatsauswahl, Zustand je Monat | Regler 2018-01 bis 2018-03, daneben „nur Afrika-Europa-Asien“ (Fotos 01, 10, 11). Laden und Selbsttest (Kontrollzellen, SHA-256) laufen unverändert; `baueBild`, `farbeFuer` und `ladeMonat` sind unverändert (Prüfer, Vergleich mit `git show HEAD`). |
| 2 | Die drei Klassen sind unterscheidbar, nie dunkel, Legende immer sichtbar | grau „keine Daten“ (Foto 07), braun „zu wenig Messungen“ (Foto 13, Moskau Februar, 48 %), blau „noch nicht geladen“ (Foto 06). Die Legende ist auf jedem Foto zu sehen, auch bei offener linker Leiste (Foto 10) und im Sonderfall (Foto 14). |
| 3 | UN-Sicht, Sondereinheiten markiert, Anspruch, Verwaltung und Quelle beim Anklicken | Krim (Foto 08): „Sondereinheit“, „umstritten“, „besetzt/Konfliktzone“, UN-Eintrag Ukraine (M49 804), Belege aus der Tabelle. Sabah (Foto 09) mit Umriss-Hinweis aus der Tabelle. Fehlt ein Feld, steht dort „keine Angabe in der Einheitentabelle“. |
| 4 | Quelle, Datenstand, „beobachtet“ sichtbar | Fest unten: „Quelle: NASA VIIRS Black Marble VNP46A3 (LAADS DAAC) · Evidenzstufe beobachtet · Datenstand 2026-09-26 13:58:54 UTC · 2023–2025 gesperrt“. Dazu das Schild oben und je ein „beobachtet“ im Dossier. |
| 5 | Läuft auf MacBook Pro 2015, öffnen per Doppelklick | Die Seite ist nach rund 3 s bereit, wie vorher; der Monat braucht etwa 0,7 s von „Skript geladen“ bis „Bild fertig“ (Messpunkte der Seite, Software-Grafik). Kein Unschärfe-Effekt (`backdrop-filter`), keine Adresse im Internet (geprüft mit `grep http`: 0 Treffer). Die Schriften liegen lokal. „Globus öffnen.command“ ist unverändert und öffnet dieselbe Datei. |
| 6 | Die Tönung der Sondereinheiten sieht nicht aus wie schlechte Datenlage | Sondereinheiten haben nur gestrichelte Linien und keine Füllung (`fill-opacity: 0`). Gold kommt nur in der Oberfläche vor, nie auf der Karte. Der Hinweisbalken neben der Karte ist jetzt neutral grau statt gold (Prüferpunkt 2). |

**Stichproben** (Monat 2018-01, echte Klicks über das DevTools-Protokoll):

| Ort | Anzeige | Foto |
|---|---|---|
| Berlin | Germany, 11 nW·cm⁻²·sr⁻¹, 100 % beobachtet | 02 |
| Paris | France, 50, 100 % | 03 |
| Kairo | Egypt, 41, 100 %; Nil und Delta hell, Wüste dunkel | 04 |
| Sahara 23,1° N 12,1° O | Niger, „unter 0,1“, 100 % | 05 |
| Amerika 5° N 75° W | Colombia, „noch nicht geladen“, blau | 06 |
| Arktis 80,1° N 20° O | Norway, „keine Daten“, grau | 07 |
| Krim | eigene Einheit, UN-Eintrag Ukraine, 2,4 | 08 |
| Moskau, 2018-02 | „zu wenig Messungen“ (48 %), braun | 13 |

Die Werte sind dieselben wie im Bericht `2026-09-26_globus-echtdaten.md`. Im alten Vergleichsfoto zu Berlin hatte der Klick die westliche Nachbarzelle getroffen (4,4). Das Foto `00_vorher_nachher_berlin.jpg` vergleicht daher nur das Aussehen.

**Vorher/nachher nebeneinander:**
- `00_vorher_nachher_ueberblick.jpg`
- `00_vorher_nachher_berlin.jpg`
- `00_vorlage_nachher.jpg` (Vorlage links, neuer Globus rechts)

**Sonderfälle** (künstlich, nur in einer Kopie im Zwischenordner, Foto 14):
- **Kein Monat fertig:** Ein roter Hinweis in der Zeitleiste erscheint, der Globus ist überall grau schraffiert, und der Schalter „Nachtlicht“ ist gesperrt.
- **Einheitentabelle fehlerhaft:** Es werden keine Grenzen gezeigt. Den Grund nennen die Legende und die Leiste, und die Suche ist gesperrt.

**Kleine Bildschirme:** Auf 1280 × 800 (Foto 12) rückt die Zeitleiste nach rechts, damit sie die Legende nicht überdeckt. Ist das Dossier offen, rückt sie zwischen Legende und Dossier.

**Tests:**
- Ganze Suite im worktree: **636 bestanden**, 0 fehlgeschlagen (6:12 min).
- Nach den Korrekturen des Prüfers (nur CSS und JS): `tests/test_export_globus.py` **27 bestanden**.
- Für die Oberfläche selbst gibt es keine automatischen Tests. Sie ist über die Fotos und die ausgelesenen Dossier-Texte geprüft.

**Plausibilitäts-Prüfer** (allgemeiner Agent mit der Anleitung `.claude/agents/plausibilitaets-pruefer.md`): „plausibel mit Vorbehalt“.

Bestätigt hat der Prüfer:
- Alle Farben der Legende, nachgerechnet von Hex nach RGB: grau, braun, blau, die Farbe für 0 und die drei Linienfarben.
- Die Streifenanteile.
- Dieselbe Einteilung der Klassen in Kartenbild und Klick-Anzeige.
- Dass keine fehlende Zelle dunkel erscheinen kann.
- Dass die dunklen Kacheln in Amerika echte Messungen sind. Nachgeprüft an den Monatsdaten: Französische Antillen, Französisch-Guayana, Clipperton, Azoren.

Umgesetzt:
1. **Die Streifenrichtung in der Legende war gegenüber der Karte vertauscht.** Das gab es schon vor dieser Sitzung. Jetzt stimmt sie: grau „/“, braun „\“.
2. **Gold und „umstritten“ hatten fast denselben Farbton.** Die Hinweisbalken sind jetzt neutral grau.
3. **„beobachtet“ hatte zwei Farben.** Jetzt ist es überall gold.
4. **Die weiße Auswahl-Linie verdeckte die Farbe der Sondereinheit.** Sie liegt jetzt darunter (Foto 08: die Krim bleibt rosa gestrichelt).
5. **Die dunklen Kacheln mitten im blauen Amerika wirkten wie ein Fehler.** Der Hinweis erklärt sie jetzt: „Einzelne Kacheln außerhalb (z. B. Französisch-Guayana, Azoren) sind schon geladen …“.
6. **ARCHITECTURE.md Abschnitt 10 war veraltet.** Es gibt jetzt einen datierten Absatz.
7. **Im Sonderfall war ein Satz ungenau.** Jetzt steht dort: „Nachtlicht wird deshalb nicht angezeigt; der Globus trägt überall das Muster ‚keine Daten‘“.

## Umfang

- **Geändert** in `~/ALEPH-ui` auf `ui-geruest`:
  - `web/globus.html` und `web/globus.css` (komplett neu geschrieben).
  - `web/globus.js`: Der Datenteil ist unverändert. Bei den Klassen sind nur Anzeigetexte dazugekommen. Die Bedienung ist neu: Leisten, Suche, Monatsregler, Dossier.
  - `ARCHITECTURE.md` (ein Absatz).
- **Neu:** `web/vendor/fonts/`, 4 Schriftdateien, zusammen 108 KB, mit Lizenz OFL 1.1 und einer Datei `HERKUNFT.txt`. Abgerufen am 26.09.2026 über jsDelivr aus den Fontsource-Paketen 5.3.0.
- **Nicht angefasst:**
  - Export (`aleph/export/globus.py`), Würfel, Download, `.env`.
  - Das alte Gerüst und die Befehlsdateien.
  - In ~/ALEPH nur der LOG-Eintrag am Ende.
- **Nicht verwendet:** Das Plugin „frontend-design“ ist in dieser Sitzung nicht verfügbar.
- **Agenten:**
  - Plausibilitäts-Prüfer: eingesetzt.
  - `statistik-pruefer`: nicht eingesetzt, weil kein Analyse-Code geändert wurde.
  - `datenquellen-scout` und `layer-bauer`: nicht eingesetzt, weil kein neuer Layer entstanden ist.
- **Zeitraum 2023–2025:** Keine Daten angezeigt oder ausgewertet.

## Empfehlung

1. **Aufgabe für eine spätere Sitzung in ~/ALEPH, heute nicht erledigt:** Die Einheit `sabah_north_borneo` in `aleph/layers/sondereinheiten.yaml` umbenennen, zum Beispiel in „Ost-Sabah (beanspruchtes Gebiet)“.
   - Grund: Der heutige Name „Sabah / North Borneo (von den Philippinen beansprucht)“ klingt nach dem ganzen Bundesstaat. Der Umriss (Natural Earth C04) deckt aber nur den Osten ab: Sandakan liegt darin, Kota Kinabalu nicht.
   - Danach die Einheitentabelle neu bauen und `Globus aktualisieren.command` ausführen.
   - Die Oberfläche übernimmt den Namen dann von selbst. Hier habe ich bewusst nichts umbenannt.
2. **Dich selbst auf dem MacBook prüfen lassen:** „Globus öffnen.command“ doppelklicken und den Globus einige Sekunden drehen und zoomen. Ruckelt es, sag Bescheid. Der schnellste Hebel wäre, die dunkle Vignette abzuschalten (eine Zeile in `globus.css`).
3. **Später:** Die Balken „Datenverfügbarkeit“ aus der Vorlage lassen sich echt bauen, wenn der Export den Zustand je Monat mitliefert. Das ist eine kleine Änderung in `aleph/export/globus.py` und einen Test wert.

## Nicht geprüft

- Wie flüssig Drehen und Zoomen im sichtbaren Chrome mit der echten Grafikkarte laufen. Alle Fotos und Zeiten stammen aus Chrome ohne Fenster mit Software-Grafik (SwiftShader).
- Der Doppelklick auf „Globus öffnen.command“ selbst. Geprüft ist nur, dass die Datei unverändert auf `web/globus.html` zeigt.
- Die Bedienung mit der Tastatur habe ich nicht vollständig durchprobiert (Suche mit Pfeiltasten und Enter, Escape schließt).
- Ob Zeichen außerhalb der Schriftteilmenge „latin“ gut aussehen, etwa das hochgestellte Minus in nW·cm⁻²·sr⁻¹. Sie kommen aus einer Systemschrift.
- Die Inhalte der Einheitentabelle (UN-Zitate, Belege). Sie werden nur angezeigt; Prüfstand wie in den Berichten davor.
