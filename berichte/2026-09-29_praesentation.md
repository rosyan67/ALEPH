# Globus für die Präsentation am 30.09.2026

Stand: 2026-09-28 abends · worktree `~/ALEPH-ui` (Branch `ui-geruest`, zuletzt gepusht) · main `~/ALEPH` (Commit `1421b98` + LOG)

## Kurzfassung

- **Alle Teile 1–6 sind erledigt, committet und hochgeladen.**
  - Der Globus zeigt alle 24 Monate 2018–2019. Während der Sitzung ist 2020-01 fertig geworden, deshalb sind es jetzt 25.
  - 2024-01 steht im Würfel, ist aber weder auswählbar noch sichtbar, auch nicht als Name oder in der Zählung.
- Sechs Blickpunkte, Länderfeld (Nachtlicht und Weltbank nebeneinander), Punktwolke Nachtlicht × BIP, Vergleich 2019/2018, „Über ALEPH“.
- **Erste Auswertung** (statistische Assoziation, Querschnitt): 2018 125 Länder, Steigung 0,94 (95 %: 0,85–1,03), R² 0,81; 2019 fast gleich.
  - Nicht vom statistik-pruefer geprüft, auf deine Anweisung. Das steht auf dem Globus.
- Plausibilitäts-Prüfer: **„plausibel mit Vorbehalt“**. 7 von 8 Befunden sind umgesetzt; einer ist offen (alte Beispieldateien in `web/`).
- Der Globus startet **ohne Internet und ohne SSD**. Ersatzbilder als PDF und ein 5-Minuten-Ablauf liegen in `praesentation/`.
- **Tests:** worktree 756 bestanden, main 722 bestanden. Keiner übersprungen, keiner fehlgeschlagen.

## Urteil

Der Globus ist vorzeigbar. Jede Aussage darauf trägt ihre Evidenzstufe. Fehlende Daten sind nie dunkel. Die Sperre 2023–2025 ist doppelt abgesichert und getestet.

Die Auswertung Nachtlicht × BIP ist ehrlich beschriftet. Sie ist aber noch nicht methodisch abgenommen. In der Präsentation also nur als „erste, noch ungeprüfte Rechnung“ zeigen.

## Belege

### Teil 1 – Datenstand

- **Einheitentabelle** in ~/ALEPH neu gebaut, mit dem vorhandenen Bau-Schritt (`python -m aleph.layers.zell_einheiten`, 63 s). Kein Code in ~/ALEPH geändert.
  - Ergebnis: 326 Einheiten. `sabah_north_borneo` heißt jetzt „Ost-Sabah (von den Philippinen beansprucht)“.
  - Sicherung des alten Stands: `laender/zell_einheiten_stand_2026-09-26T1333Z`.
- **„Globus aktualisieren“:** den Export darin ausgeführt (`python -m aleph.export.globus`). Den Doppelklick mit dem Öffnen von Chrome habe ich nicht ausgeführt.
- **Gefundener Fehler:** Die linke Leiste zeigte bisher „fertig, aber gesperrt: 2024-01“.
  - Jetzt schreibt der Export Monate ab 2023 weder als Namen noch in die Zählung in eine Datei der Oberfläche.
  - Zusätzlich filtert die Seite selbst.
  - Tests: künstlich, und am echten Export (keine Datei enthält „2023-“, „2024-“ oder „2025-“).
- **Stichproben** (Zellwert nW·cm⁻²·sr⁻¹):

  | Ort | 2018-01 | 2018-06 | 2019-06 | 2019-12 |
  |---|---|---|---|---|
  | Berlin | 11,3 | 15,0 | 15,0 | 11,4 |
  | Paris | 50,1 | 67,8 | 67,5 | 60,4 |
  | Kairo | 40,8 | 52,2 | 52,3 | 44,7 |
  | Sahara | 0,0 | 0,0 | 0,0 | 0,0 |
  | Kolumbien (Amerika) | noch nicht geladen | noch nicht geladen | noch nicht geladen | noch nicht geladen |
  | Arktis 85° N | keine Daten | keine Daten | keine Daten | keine Daten |

### Teil 2 – Blickpunkte

- Die sechs Ansichten haben folgende Monate. Gewählt ist jeweils ein Monat mit gemessener Abdeckung im Ausschnitt, ohne Winter im Norden und ohne Monsun.

  | Blickpunkt | Monat | Abdeckung |
  |---|---|---|
  | Nil | 2018-10 | 100 % |
  | Korea | 2018-10 | 100 % |
  | Nigerdelta | 2018-11 | 100 % |
  | Irak | 2018-10 | 100 % |
  | Indien | 2018-03 | 96 % |
  | Europa | 2018-09 | 100 % |

- Jede Zahl im Text ist im Kopf von `web/globus_blickpunkte.js` belegt.
- Zu starke Formulierungen („durchgehend“, „fast flächig“) habe ich vor dem Commit durch gemessene Anteile ersetzt, zum Beispiel: Südkorea 65 % der Zellen über 1, Nordkorea 0 %.
- „Gasfackeln“ steht abgesetzt als „Vermutung, nicht geprüft“.

### Teil 3a – Länderfeld

- **Nachtlicht:** kommt unverändert aus dem Verknüpfungsgerüst, in der Sicht „so wie die Weltbank zählt“. Unter 90 % Abdeckung gibt es keine Landessumme.
- **Gegenprobe 2018-01:** gleiche Werte wie die frühere Technikprobe. Deutschland 400 000, Ägypten 710 000, Russland ohne Summe (46 %).
- **Weltbank:** nur die Jahre der angezeigten Monate, nie ab 2023. „BIP pro Kopf“ wird nicht angezeigt, wo die Weltbank-Tabelle es als „nicht verwenden“ markiert hat (Russland, Ukraine, Zypern, Marokko, Tansania).
- **Markiert:** Länder mit abweichendem Gebiet (rot), unklarem Gebiet (gelb) oder geringer Abdeckung (rot).
- **Sondereinheiten:** Ohne eigene Weltbank-Zahl steht dort „keine eigene Weltbank-Zahl“ (z. B. Krim). Mit Zuordnung steht der Hinweis „gilt für das ganze Weltbank-Land“.

### Teil 3b – Auswertung

Einzelheiten stehen in `~/ALEPH/berichte/2026-09-29_nachtlicht-bip-2018.md`.

- **Ein Umsetzungsfehler nach dem ersten Lauf ist offen dokumentiert:**
  - Zuerst waren 12 Länder aus Amerika und Ozeanien in der Rechnung.
  - Vorher: n 137, Steigung 0,96. Nachher: n 125, Steigung 0,94.
  - Keine Schwelle wurde geändert.
- **Russland, Norwegen und Island** fallen nach Regel 5 heraus. Das weicht von deiner Erwartung („Russland drin lassen“) ab. Ich habe die Regel nicht angepasst.
- **Oberfläche:**
  - Die Punktwolke zeigt Kürzel, die Linie und den Umschalter 2018/2019. Ein Klick auf einen Punkt fliegt zum Land.
  - Darunter stehen Evidenzstufe, Rahmen, Zahl der Länder und ein Link zur Ausschlussliste.
  - Außerdem Gegenrechnungen, die 10 größten Abweichungen und „Wie gerechnet“.

### Teil 4 – Vergleich

- Die Differenz wird nur gezeigt, wenn eine Zelle in **beiden** Monaten einen gezeigten Wert hat. Sonst erscheint ein Karomuster „kein Vergleich möglich“.
- **Farben:** blau heißt dunkler, rot heißt heller, die Mitte ist grau.
- **Beschriftung:** „beobachtete Differenz, nicht auf Signifikanz geprüft“. Dazu der Hinweis, dass Unterschiede von etwa ±1 normale Schwankung sein können.
- Der Umschalter ist nur bei Monaten aus 2019 aktiv.

### Teil 5 – Über ALEPH

Das Feld ist aufklappbar. Es enthält:
- zwei Sätze, was ALEPH ist;
- die vier Evidenzstufen;
- den Datenstand (aus der Datei gelesen, nicht fest eingetragen);
- die nächsten Ebenen;
- die Regeln.

### Teil 6 – Absicherung

- **Ersatzbilder:** `praesentation/globus_ersatzbilder.pdf`, 8 Seiten, 1,7 MB. Die sechs Blickpunkte, dazu Punktwolke und Vergleich, jeweils mit Bildunterschrift.
- **Ohne Internet:** Chrome im Offline-Modus lädt die Seite ohne Fehler.
  - Alle vier Schriften sind lokal geladen. MapLibre liegt lokal.
  - Die Globus-Dateien enthalten keine Internetadresse (`grep`).
  - **Wichtig:** `web/daten/` ist nicht in Git, sondern liegt nur auf diesem Laptop. Die SSD braucht der Globus zum Zeigen nicht.
- **Ablauf:** `praesentation/ablauf.md`. Er enthält fünf Minuten mit „zeigen / sagen“, die Liste „was ich NICHT behaupten darf“ und drei Fragen mit ehrlicher Antwort.

### Plausibilitäts-Prüfer: „plausibel mit Vorbehalt“

Der Prüfer hat die Größenordnungen nachgerechnet (Licht je km², BIP pro Kopf) und die Rangfolgen als stimmig bestätigt. Er hat keinen Hinweis auf ein verdrehtes Raster und keine Lücke gefunden, die als 0 gezählt wird.

| Nr. | Befund | Umgesetzt |
|---|---|---|
| 1 | Irak: Text „112“, Feld zeigt „110“ | ja, Text jetzt „bis rund 110“ |
| 2 | Deutung „Gasfackeln“ steht in einem Feld mit der Stufe „beobachtet“ | ja, eigene Zeile „Vermutung, nicht geprüft“ |
| 3 | „Gangesebene“ zu weit gefasst, Euphrat nicht belegt | ja, nachgerechnet: nur indische Zellen ohne Delhi 30 % gegen 10 %; Euphrat-Zellen Ramadi 14, Falludscha 12, Nasiriya 11 |
| 4 | Juni-Werte nördlich von 45° N vielleicht mit Dämmerlicht | als Regel in den Ablauf aufgenommen; am Handbuch nicht geprüft |
| 5 | `web/geruest_beispieldaten.html` und `web/beispieldaten/` enthalten erfundene Monate ab 2023 | **offen**, siehe Empfehlung |
| 6 | Auswertung ohne statistik-pruefer; Taiwan und Westsahara fehlen in der Ausschlussliste; Achse abgeschnitten | Hinweis auf Gebiete ohne Weltbank-Zahl ergänzt, Achse repariert; statistik-pruefer offen |
| 7 | Vergleich „+0,87 (44 → 45)“ verwirrt | ja, jetzt „+0,9 (44,4 → 45,2)“ |
| 8 | Kleine Unterschiede sind schon farbig | Hinweis „±1 kann normale Schwankung sein“ in der Legende |

### Tests

- **worktree:** `pytest` über alles, **756 bestanden**, 0 übersprungen, 0 fehlgeschlagen (6:49 min).
  - Zwei Läufe davor hatten je zwei Fehlschläge: 1. Die neue Datei `nachtlicht_bip.js` passte auf das Muster der Monatsdateien; sie heißt jetzt `auswertung_nachtlicht_bip.js`. 2. Die Tests hatten „genau 24 Monate“ fest eingetragen, aber der Download hatte inzwischen 2020-01 fertiggestellt.
  - Beides ist behoben.
- **main:** **722 bestanden**, 0 übersprungen, 0 fehlgeschlagen.
- Neue Tests: `tests/test_globus_oberflaeche.py` (10), 6 neue in `tests/test_export_globus.py`, `~/ALEPH/tests/test_nachtlicht_bip_querschnitt.py` (9).

## Umfang

- **~/ALEPH (main):**
  - neu: `aleph/link/nachtlicht_bip_querschnitt.py`, `tests/test_nachtlicht_bip_querschnitt.py` und der Bericht zur Auswertung
  - LOG-Eintrag
  - die Einheitentabelle auf der SSD neu gebaut
  - kein Branch gewechselt, keine bestehende Datei geändert
- **~/ALEPH-ui (ui-geruest):**
  - main übernommen (Merge `d255019`, Konflikt in `.gitignore`, beide Teile behalten)
  - neu: `aleph/export/globus_laender.py`, `web/globus_blickpunkte.js`, `globus_laender.js`, `globus_auswertung.js`, `globus_ueber.js`, `praesentation/`, `tests/test_globus_oberflaeche.py`, dieser Bericht
  - geändert: `aleph/export/globus.py`, `web/globus.js`, `globus.html`, `globus.css`, `tests/test_export_globus.py`
  - `git config http.postBuffer` nur für dieses Repository vergrößert, weil der Push der PDF sonst mit HTTP 400 scheiterte
- **Nicht angefasst:**
  - der Download (Prozess 82367)
  - `.env`
  - `vnp46a3*.py`
  - die Kachellisten
  - der Würfel wurde nur gelesen
- **Keine inhaltliche Auswertung von 2023–2025.** Die Auswertung rechnet nur 2018 und 2019.
- **Kein statistik-pruefer** (deine Anweisung). Der plausibilitaets-pruefer lief genau einmal.

## Empfehlung

1. **Vor dem 30.09.:** `web/geruest_beispieldaten.html` und `web/beispieldaten/` aus dem Ordner nehmen oder zumindest nicht öffnen. Sie enthalten erfundene Daten, auch mit „2024“. Ich habe sie nicht gelöscht, weil sie bewusst als „VERALTET“ behalten wurden. Die Entscheidung liegt bei dir.
2. **Am Präsentationslaptop:** einmal „Globus öffnen.command“ doppelklicken und die sechs Blickpunkte durchklicken. Die Fotos entstanden mit Software-Grafik ohne Fenster.
3. **Nach der Präsentation:**
   - `statistik-pruefer` über die Auswertung laufen lassen.
   - Den Gasfackel-Hinweis an einer geprüften Quelle belegen.
   - Die Dämmerungsgrenze im Black-Marble-Handbuch (Volltext) nachlesen.
4. Neue Monate (z. B. 2020-01) kommen mit „Globus aktualisieren“ automatisch dazu. Die Auswertung und der Vergleich bleiben bei 2018/2019.

## Nicht geprüft

- Der Doppelklick auf „Globus aktualisieren.command“ und „Globus öffnen.command“ mit einem echten Chrome-Fenster und Grafikkarte.
- Das Aussehen auf einem kleineren Bildschirm als 1440 × 900 (die Knopfreihe rechts ist länger geworden).
- Die Gasfackel-Deutung, die Dämmerungsgrenze im Juni, die Weltbank-Werte gegen die Originalquelle (nur nachgerechnet).
- Die PDF als Bild angesehen: Auf diesem Rechner fehlt ein PDF-Betrachter für die Kommandozeile. Geprüft sind Aufbau, 8 Seiten und volle Auflösung; die Einzelbilder habe ich vorher angesehen.
