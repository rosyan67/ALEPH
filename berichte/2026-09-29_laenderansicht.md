# Länderansicht mit Zeitreihen und Ländervergleich (Präsentation 30.09.2026)

Stand: 2026-09-29 abends · worktree `~/ALEPH-ui` (Branch `ui-geruest`, gepusht) · main `~/ALEPH` (neue Dateien, gepusht) · Fotos: `berichte/2026-09-29_laenderansicht_bilder/`

## Kurzfassung

- Teile 0–4 erledigt, jeder Teil committet und hochgeladen. Sicherung vorher: Git-Tag `praesentation-stabil`.
- Neu: Länderansicht (Nachtlicht monatlich, 12-Monats-Durchschnitt, saisonbereinigt, BIP; absolut/Index; Summe/pro Kopf/pro km²) und Ländervergleich für bis zu 4 Länder.
- Datenstand inzwischen **37 Monate (2018-01 bis 2021-01)**, also drei volle Jahre. Deshalb ist die Saisonbereinigung für Ägypten schon bestimmbar. Für Deutschland, Indien und Nigeria ist sie es noch nicht.
- Nachrechnung Ägypten, Deutschland, Indien, Nigeria: stimmt bis auf Rundung.
- statistik-pruefer: „bestanden mit Auflagen“. plausibilitaets-pruefer: „plausibel mit Vorbehalt“. Die Auflagen sind umgesetzt, bis auf zwei spätere Punkte.
- Ein Fehler von mir ist gefunden und behoben: Der Ländervergleich öffnete sich fälschlich beim alten Vorjahresvergleich.
- Die alten Ansichten funktionieren weiter; sie sind mit Fotos geprüft.
- Tests: worktree 761 bestanden, main 738 bestanden. Keiner übersprungen, keiner fehlgeschlagen.

## Urteil

Die Länderansicht und der Vergleich sind vorzeigbar. Beide sagen, was sie sind: beobachtete Werte nebeneinander, kein Zusammenhang. Unsichere Monate sind markiert und nicht weggelassen. Fehlende Werte bleiben Lücken. 2023–2025 ist dreifach gesperrt: in der Rechnung, im Export und auf der Seite.

Die Monatskurven zeigen aber deutliche Messeffekte: Juni-Spitzen in Europa, der Monsun in Indien, Schnee im Norden. Die dürfen in der Präsentation nicht gedeutet werden. Sie stehen im Ablauf unter „Was ich NICHT behaupten darf“.

## Belege

### Teil 0 – Sicherung und Aufräumen

- **Tag `praesentation-stabil`** auf Commit `f0c7663` (Stand vor dieser Sitzung), gepusht.
  - **Zurück im Notfall:** im Terminal `cd ~/ALEPH-ui && git checkout praesentation-stabil` eingeben. Danach zeigt der Globus den Stand von gestern Abend. Mit `git checkout ui-geruest` kommst du zum neuen Stand zurück.
- **Entfernt** (erfundene Beispieldaten, vom Globus nicht geladen):
  - `web/geruest_beispieldaten.html`
  - `web/app.js`
  - `web/style.css`
  - `web/beispieldaten/`: `beispiel_anomalien.js`, `beispiel_datenverfuegbarkeit.js`, `beispiel_projektionen.js`, `beispiel_theorien.js`, `orte.js`
- `web/index.html` verweist nicht mehr auf das Gerüst. Der Globus startete danach ohne Fehler (Foto).

### Teil 1 – Länderansicht

- **Rechnung** in `~/ALEPH/aleph/link/laender_zeitreihen.py`, neue Datei. Die Regeln F1–F9 standen im Kopf der Datei, bevor die Rechnung zum ersten Mal lief.
  - **Monatswerte:** dasselbe Gerüst wie im Länderfeld. Ein Test prüft, dass die Werte zum Länderfeld passen.
  - **Punkte in der Grafik:**
    - voll: Summe über mindestens 90 % der Fläche;
    - hohl: Schnee-Verdacht auf mindestens 5 % der Fläche;
    - blass: unter 90 % der Fläche gemessen, nur Teilsumme;
    - kein Punkt: nicht geladen oder keine Messung.
  - **12-Monats-Durchschnitt:** nachlaufend. Er wird nur gerechnet, wenn alle 12 Monate im Fenster voll gültig sind; sonst bleibt eine Lücke. Grund: Sonst wäre der Durchschnitt jahreszeitlich verschoben.
  - **Saisonbereinigt:** Verfahren des Statistik-Gerüsts, also die Abweichung vom Median desselben Kalendermonats.
    - Mindestlänge: je Kalendermonat 3 volle Werte, also 3 Jahre (`Mindestlaengen.je_kalendermonat`).
    - Ist das nicht erfüllt, steht dort „noch nicht bestimmbar – benötigt mindestens 3 Jahre“.
  - **Jahreswert:** Regeln der Auswertung 2018 (gute Monate, Schnee, mindestens 90 % des Lichts). Index: 2018 = 100.
  - **Pro Kopf:** Licht geteilt durch die Bevölkerung. Nicht gerechnet für Zypern, Marokko, Russland, Tansania und die Ukraine; dort passt die Bevölkerungszahl nicht zum Gebiet.
- **Anzeige** in `web/globus_zeitreihen.js`, neue Datei.
  - Kleine Grafiken übereinander mit gemeinsamer Zeitachse, jede Grafik mit nur einer Achse.
  - Umschalter für die Darstellung und die Bezugsgröße.
  - Tabelle der Jahreswerte, dazu die Monatswerte zum Aufklappen.
  - Sichtbar sind außerdem der Hinweis, die Evidenzstufe, der Datenstand, die Quellen und die Kennzeichen.
  - Einstieg: Knopf „Zeitreihen ansehen“ im Länderfeld.
- **Export:** `aleph/export/globus.py` reicht die Ergebnisdatei nur durch und entfernt dabei alles ab 2023.

### Teil 2 – Rechnungen geprüft

Nachrechnung auf einem eigenen Weg, direkt aus Würfel und Zuordnung, ohne die Funktionen des Gerüsts:

| Prüfung | Ergebnis |
|---|---|
| Monatssumme 2019-06 | EGY 866 548 / Datei 867 000 · DEU 489 190 / 489 000 · IND 2 459 153 / 2 460 000 · NGA 304 808 / 305 000 |
| Jahreswert 2019 (eigen / Datei / Auswertung 2018-19) | EGY 787 204 / 787 000 / 787 204 · DEU 417 918 / 418 000 / 417 918 · IND 2 400 084 / 2 400 000 / 2 400 084 · NGA 309 417 / 309 000 / 309 417 |
| alle 170 gültigen Jahreswerte 2018 und 2019 | höchstens 0,4 % Abweichung von der Auswertung 2018 (Rundung) |
| Index Licht 2020 (Datei / nachgerechnet) | EGY 97 / 97,0 · DEU 95 / 95,1 · IND 94 / 93,8 · NGA 86 / 85,6 |
| Index reales BIP 2020 | EGY 109 · DEU 97 · IND 98 · NGA 96 (nachgerechnet 109,3 / 96,8 / 97,9 / 95,7) |
| Monate nicht voll gültig | DEU 2018-02, 2019-01 (Schnee), 2021-01 (gering) · IND 2018-07 · NGA 2019-10 · EGY keiner |

**statistik-pruefer: „bestanden mit Auflagen“.** Der Bericht liegt in `~/ALEPH/berichte/2026-09-29_pruefung-laender-zeitreihen.md`.

- **Mindestlänge 3 Jahre:** vertretbar. Der Prüfer rät ausdrücklich davon ab, sie nachträglich zu erhöhen.
- **Umgesetzt** (nur Texte, Version 0.2.0, keine Zahl geändert):
  - Satz zur Unsicherheit;
  - Anteil „Licht aus Zellen mit 6–8 guten Monaten“ je Jahr;
  - „Summe über die gemessene Fläche“ statt „Landessumme“;
  - Saison-Text „keine Anomalie-Bewertung“;
  - „vorläufig“ auch im Index;
  - Satz zur Stufe der Pro-Kopf-Werte zum Jahreswechsel;
  - Titel „nachlaufend“.
- **Nicht gemacht:** die freiwillige Gegenrechnung „nur Monate, die in allen Jahren gut sind“ (Auflage 1c).

### Teil 3 – Ländervergleich

- **Neue Datei** `web/globus_vergleich.js`.
  - Bis zu 4 Länder: über die Suche, über „Zum Vergleich hinzufügen“ im Länderfeld und über einen Schalter in der Punktwolke („Klick fügt zum Vergleich hinzu“).
  - Kleine Grafiken nebeneinander mit gleicher Zeitachse und gleichem Wertebereich. Umschalter absolut/Index und Bezugsgröße, Vergleichstabelle.
- **Farben:** grün (Kreis), violett (Quadrat), gelbgrün (Dreieck), rostrot (Raute).
  - Mit dem Farbprüfer gemessen: bei Rot-Grün-Schwäche ΔE ≥ 9,9, bei normalem Sehen ΔE ≥ 17,8.
  - Sie sind verschieden von den Farben für Datenlage, Sondereinheiten und rote Kennzeichen (Test).
  - Jedes Land hat zusätzlich seine Form und sein Kürzel. In der Punktwolke wird es mit derselben Farbe und Form umrandet.
- **Mein Fehler, gefunden beim Durchklicken:**
  - Ich hatte den Adressschlüssel `#vergleich=` benutzt. Den nutzt schon der Vorjahresvergleich, deshalb ging dort ein leeres Vergleichsfeld auf.
  - Jetzt heißt der Schlüssel `#laendervergleich=`. Ein Test sichert das ab.

### Teil 4 – Durchklicken, Ersatzbilder, Ablauf, Prüfer

- **Fotos:** 17 Stück, alle ohne Fehleranzeige.
  - 01–04: die alten Ansichten Blickpunkt Nil, Länderfeld, Vorjahresvergleich und „Über ALEPH“, alle unverändert.
  - 05: Klickweg Länderfeld → „Zeitreihen ansehen“.
  - 06–11, 17: Ägypten, Deutschland, Indien, Nigeria, pro Kopf, pro km², Index.
  - 12–16: Vergleich absolut und Index, Punktwolke markiert, Klick in der Punktwolke und der vollständige Präsentationsweg.
  - Aufgenommen mit Chrome ohne Fenster (Software-Grafik). Das Skript ist `scripts/globus_fotos.py`, neu.
- **Ersatzbilder-PDF:** 15 Seiten statt 8, 3,7 MB.
  - Die Seiten 1–8 sind unverändert; sie sind neu aus dem Stand `praesentation-stabil` übernommen.
  - Die Seiten 9–15 zeigen Ägypten, Deutschland, Indien, Deutschland im Index, den Vergleich absolut und im Index sowie die Punktwolke, jeweils mit Bildunterschrift.
- **Ablauf:** jetzt 6 Minuten, mit dem neuen Abschnitt 4:30–5:30.
  - Der Vergleich wird in einem vorbereiteten zweiten Tab gezeigt, damit man in der Präsentation nichts tippen muss.
  - Neue Punkte unter „Was ich NICHT behaupten darf“:
    - kein Ursache-Wirkungs-Verhältnis;
    - wenige Indexpunkte sind nicht deutbar;
    - die Saisonbereinigung ist meist noch nicht möglich;
    - kein „Corona-Effekt“;
    - pro km² ist keine Wirtschaftskennzahl;
    - Juni-Spitzen, Monsun in Indien, der Ausschlag 2020 in Ägypten, Nigeria mit Gasfackeln und neuer BIP-Berechnung, Nordländer mit Schnee.
- **plausibilitaets-pruefer: „plausibel mit Vorbehalt“.**
  - Kein Rechen-, Einheiten- oder Rasterfehler. Die Länderfeld-Werte passen zur neuen Datei. Die alten Ansichten sind unbeschädigt.
  - Umgesetzt:
    - Gasfackel-Hinweis (Irak, Nigeria, Algerien) jetzt auch in der Länderansicht und im Vergleich;
    - Satz zur Dämmerung im Juni und Juli nördlich von 45° N;
    - Schnee-Anteil im Tooltip bei Teilsummen;
    - alle sechs fehlenden Punkte im Ablauf;
    - Präsentationsweg gekürzt.
  - Nicht umgesetzt: siehe Empfehlung 2.

## Umfang

- **~/ALEPH (main):**
  - neu: `aleph/link/laender_zeitreihen.py`, `tests/test_laender_zeitreihen.py` (16 Tests), `berichte/2026-09-29_pruefung-laender-zeitreihen.md`
  - ein Eintrag in `LOG.md`
  - keine bestehende Datei geändert, kein Branch gewechselt
- **Auf der SSD geschrieben:** `auswertungen/laender_zeitreihen/ergebnis.json`. Außerdem habe ich den Globus-Export einmal ausgeführt. Er liest nur und schreibt nach `web/daten/`, das nicht in Git ist.
- **~/ALEPH-ui (ui-geruest):**
  - neu: `web/globus_zeitreihen.js`, `web/globus_vergleich.js`, `scripts/globus_fotos.py`, die Fotos und dieser Bericht
  - geändert: `web/globus.html`, `web/globus.css`, `web/index.html`, `aleph/export/globus.py`, `tests/test_globus_oberflaeche.py`, `ARCHITECTURE.md` (ein Nachtragssatz), `praesentation/ablauf.md`, `praesentation/globus_ersatzbilder.pdf`
  - entfernt: die alten Beispieldateien (siehe Teil 0)
  - unverändert: `globus.js`, `globus_laender.js`, `globus_auswertung.js`, `globus_blickpunkte.js`, `globus_ueber.js`
- **Nicht angefasst:** der Download (er läuft weiter), `.env`, `vnp46a3*.py`, die Kachellisten. Der Würfel wurde nur gelesen.
- **Zeiträume:**
  - Gelesen: Monate 2018-01 bis 2021-01 und Weltbank-Werte 2018–2021.
  - Nichts aus 2023–2025. Das gilt auch technisch: Ein Test prüft, dass die exportierte Datei weder „2023“, „2024“ noch „2025“ enthält.

## Empfehlung

1. **Vor der Präsentation:**
   - „Globus öffnen.command“ doppelklicken.
   - Den zweiten Tab vorbereiten, wie im Ablauf beschrieben.
   - Einmal Ägypten → „Zeitreihen ansehen“ durchklicken.
   - Finnland und Schweden nicht öffnen.
2. **Nach der Präsentation:**
   - Ein Kennzeichen „Juni/Juli nördlich von 45° N“ wie beim Schnee-Verdacht einführen.
   - Die gemeinsame Achse im Vergleich nur aus vollen Punkten bestimmen. Heute können blasse Teilsummen, zum Beispiel von Russland, die Achse aufblähen.
   - Die natürliche Schwankung der Jahreswerte messen, bevor Indexunterschiede gedeutet werden.
   - Die Gegenrechnung 1c des statistik-pruefer.
3. **Neue Monate:** Sie kommen nicht von selbst in die Zeitreihen. Nötig sind zwei Schritte:
   - erst in ~/ALEPH `python -m aleph.link.laender_zeitreihen` (einige Minuten);
   - dann „Globus aktualisieren.command“.

## Nicht geprüft

- Der Globus in einem echten Chrome-Fenster mit Grafikkarte und auf einem Bildschirm unter 1440 × 900. Die Fotos entstanden ohne Fenster.
- Die Weltbank-Werte gegen die Weltbank-Seite. Die Einheit „konstante US-Dollar, Basisjahr 2015“ steht so in der ALEPH-Weltbank-Tabelle.
- Die Vermutungen des Plausibilitäts-Prüfers sind nicht an Quellen oder Daten geprüft:
  - Dämmerung im Juni;
  - Monsun;
  - Ramadan;
  - Gasfackel-Anteil;
  - Nigerias BIP-Neuberechnung 2025 (nur Sekundärquellen);
  - Schnee im Winter 2019/20.
- Wie stark die wechselnden guten Monate den Index verschieben: Der Mechanismus ist benannt, gemessen ist er nicht.
- Ob die Weltbank-Sicht bei Georgien und Moldau die abgetrennten Gebiete wirklich ausschließt.
- Die PDF als Bild. Geprüft sind 15 Seiten im Seitenbaum und eine neue Seite als Vorschau.
