# Globus mit allen Nachtlicht-Monaten 2013–2022, Länderansicht lang, Niederschlag

Stand: 2026-10-05 abends · **abgeschlossen** · worktree `~/ALEPH-ui` (Branch `ui-geruest`, gepusht) · Fotos: `berichte/2026-10-05_globus-alle-monate_bilder/` · Prüferbericht: `berichte/2026-10-05_plausibilitaet-globus-alle-monate.md`

## Kurzfassung

- **Teil 1:** Der Globus zeigt 119 Nachtlicht-Monate 2013-01 bis 2022-12, mit Zeitleiste über alle Jahre und Zustand je Monat. Dazu ein Abspielknopf. 2022-07 ist sichtbar als fehlend markiert (NASA-Satellit im Sicherheitsmodus, belegt), 2022-08 als Teilmonat. Die Startzeit ist nicht schlechter: 3,1 s vorher, 2,8 s nachher.
- **Teil 2:** Länderansicht 2013–2022, Weltbank 2013–2022. Saisonbereinigung jetzt für 125 von 236 Ländern bestimmbar (Regel unverändert). Die Stichproben Ägypten, Deutschland, Indien und Nigeria sind korrekt dargestellt.
- **Neuer Befund:** 2021 und 2022 liegt das Licht in der Mehrheit der Länder ungeklärt höher (Median aus 128 Ländern: +10 % und +16 %, vorher −3 bis +4 %). Er steht als Warnung in der Oberfläche: „Nicht als Wachstum deuten.“
- **Teil 3:** Niederschlag (NASA GPM IMERG) ist als umschaltbare Ebene gebaut. Eigene Grünskala, Einheit mm/Monat, Monate 2013–2022, keine Daten nie als 0 mm. Dazu gut sichtbar der Satz „Für großräumige Muster geeignet …“.
- **plausibilitaets-pruefer:** „plausibel mit Vorbehalt“; die Empfehlungen 1, 2, 4, 6 und 8 sind umgesetzt, die übrigen stehen unten. Ein statistik-pruefer war nicht nötig, weil keine Rechnung geändert wurde.
- **Tests:** worktree 865 bestanden (Gesamtlauf), danach 67 Globus-Tests nach der letzten Textänderung. Ablauf (7 Minuten) und Ersatzbilder-PDF (19 Seiten) sind neu.

## Urteil

Vorzeigbar, mit klaren Grenzen. Kein Monat fehlt still, und 2023–2025 bleibt unsichtbar. Jede Ebene nennt ihre Quelle und die Evidenzstufe „beobachtet“.

Zwei Dinge dürfen in der Präsentation nicht gedeutet werden:
- der Anstieg 2021–2022 beim Nachtlicht;
- einzelne Ortswerte beim Niederschlag.

Beides steht in der Oberfläche und im Ablauf.

## Belege

### Teil 1 – Alle Monate

- **Export:** 119 auswählbare Monate. Stand am Ende: 36 vollständig (2018-01 bis 2020-11), 83 nur Afrika-Europa-Asien. 2022-07 ist leer.
- **2022-07** erscheint in der Zeitleiste rot als „zurückgestellt“. Der Grund kommt aus zwei Quellen:
  - aus dem Download-Protokoll (nur gelesen): Im Katalog fehlen 36 Kacheln.
  - aus der NASA (Earthdata „Suomi NPP Recovers from Safe Mode“, selbst nachgelesen 2026-10-05): „Suomi NPP VIIRS data lost between July 26 and August 20, 2022, will not be recoverable.“
- **2022-08** ist als Teilmonat gekennzeichnet: rote Unterkante im Band, Hinweis beim Anwählen. Dass deshalb die Kacheln bei 70–80° N fehlen, ist eine Vermutung.
- **Startzeit** (`scripts/globus_startzeit.py`, Chrome ohne Grafikkarte, Median aus 3 Läufen):

  | Stand | bis Globus fertig | Startdaten |
  |---|---|---|
  | vorher, 37 Monate | 3,1 s | 8,8 MB |
  | 119 Monate, alte Seite | 3,1 s | 14,0 MB |
  | 119 Monate, neue Seite | 2,8 s | 14,0 MB |
  | mit Niederschlagsebene | 2,7 s | 14,0 MB |

  Monate lädt die Seite erst beim Auswählen. Beim Abspielen behält sie höchstens 8 Monate im Speicher: Im Test über 75 Monate blieb der Speicher zwischen 125 und 211 MB.
- **Zeitleiste:** Regler über alle 120 Kalendermonate, Jahresmarken, Zustandsband mit Legende. Nicht auswählbare Monate werden übersprungen und mit Grund genannt.
- **Abspielknopf:** Solange er läuft, steht ein roter Hinweis da: „Monatswerte schwanken jahreszeitlich (Schnee, kurze Nächte); keine Trendaussage.“ Ergänzt sind Wolken, die wechselnde Abdeckung und der Sprung 2021–2022.

### Teil 2 – Länderansicht

- **Zeitreihen:** von dir in ~/ALEPH neu gerechnet. Die Ergebnisdatei habe ich geprüft: 119 Monate, 236 Länder, nichts ab 2023, Code-Stand `9d3d0f0`. Die alte Datei ist als `ergebnis_stand_2026-09-29.json` gesichert.
  - Sie wurde gerechnet, als 2020-11 noch „nur Afrika-Europa-Asien“ war. Für Amerika fehlt dieser Monat deshalb in der Länderansicht, auf dem Globus ist er da. Das gleicht der nächste Lauf aus.
- **Lücke 2022-07:** Die Rechnung zählt echte Kalendermonate. Der 12-Monats-Durchschnitt hat deshalb nach der Lücke keinen Wert, und der Jahreswert 2022 fehlt („Jahr im Würfel noch nicht vollständig“). Die Grafik nutzt eine echte Kalenderachse.
- **Saisonbereinigung** nach der unveränderten Regel (je Kalendermonat mindestens 3 voll gültige Werte): **125 von 236 Ländern** bestimmbar (vorher 88), keines herausgefallen.
  - Nicht bestimmbar sind 111 Länder: 61 weil Teile noch nicht geladen sind (vor allem Amerika und Ozeanien), 35 wegen Schnee, 13 wegen geringer Abdeckung, 2 sonst.
  - Die bestimmbaren Länder (Auszug A–R): Albanien, Algerien, Angola, Bahrain, Bangladesch, Belgien, Benin, Bosnien und Herzegowina, Botswana, Bulgarien, Burkina Faso, Burundi, Kambodscha, Kamerun, Tschad, Kongo (beide), Elfenbeinküste, Kroatien, Zypern, Tschechien, Dschibuti, Ägypten, Äthiopien, Frankreich, Gabun, Deutschland, Ghana, Griechenland, Guinea, Hongkong, Ungarn, Indien, Indonesien, Iran, Irak, Irland, Israel, Italien, Jordanien, Kenia, Südkorea, Kosovo, Kuwait, Laos, Libyen, Malaysia, Mali, Marokko, Mosambik, Namibia, Niederlande, Niger, Nigeria, Nordmazedonien, Oman, Philippinen, Polen, Portugal, Katar, Rumänien, Ruanda und weitere.
  - Dazu einige Inselgebiete in Amerika, deren Kacheln schon geladen sind: Antigua, Dominica, Puerto Rico, Curaçao.
  - Die vollständige Liste lässt sich aus `web/daten/laender_zeitreihen.js` erzeugen (`saison.summe.bestimmbar`).
- **Stichproben:**

  | Land | gültig | Schnee-Verdacht | geringe Abdeckung | Darstellung |
  |---|---|---|---|---|
  | Ägypten | 119 | – | – | volle Punkte, Lücke 2022-07 |
  | Deutschland | 111 | 2013-01, 2013-03, 2015-02, 2017-01, 2018-02, 2019-01 | 2013-02, 2021-01 | hohle bzw. blasse Punkte, Lücken im 12-Monats-Durchschnitt |
  | Indien | 116 | – | 2013-07, 2016-07, 2018-07 | blasse Punkte im Monsun-Juli |
  | Nigeria | 118 | – | 2019-10 | Lücke im 12-Monats-Durchschnitt 2019-10 bis 2020-09 |

- **Weltbank 2013–2022** stehen in den BIP-Grafiken und Tabellen, Ägypten zum Beispiel 307 bis 454 Mrd. US-$.
- **Befund Sprung 2021–2022.** Gerechnet nur als Prüfung für den Hinweistext, aus den Jahresmitteln der voll gültigen Monate. Zuerst über alle Länder, dann über einen festen Kreis von 128 Ländern mit Wert in allen Jahren, ohne 2022-07 und -08.
  - Median Jahr gegen Vorjahr: 2014 +3,6 %, 2015 −2,3 %, 2016 −1,6 %, 2017 +1,0 %, 2018 +3,1 %, 2019 +0,6 %, 2020 −2,6 %, **2021 +9,8 %, 2022 +15,6 %** (59 % der Länder über +10 %).
  - Der Prüfer fand keine NASA-Angabe zu einem Bruch.
  - Die Warnung steht in Länderansicht und Vergleich (absolut und Index), im Wortlaut nach seiner Empfehlung abgeschwächt.

### Teil 3 – Niederschlag

- **Voraussetzung selbst geprüft:**
  - Der IMERG-Bericht hat ein Urteil („Layer nutzbar, mit ausgewiesener Unsicherheit“).
  - Der Würfel hat 153 Monate mit Zustand 1 und 3 mit Zustand 5.
  - Das Manifest führt 153 Monate als „geladen“. Für alle 120 Monate vor 2023 stimmen Größe und sha256 der Datei (selbst nachgerechnet).
  - Die Stichproben im Bericht sind bestanden.
- **Eingebaut:**
  - main in den worktree-Branch übernommen (ohne Konflikt).
  - Neu: `aleph/export/globus_niederschlag.py`. Es liest über `aleph/detect/wuerfel.lies_monate`, also dieselbe Ladelogik, und wendet die Gültigkeitsregel des Layers an (`imerg.nutzbar_maske`, mindestens 50 %).
  - Neu: `web/globus_niederschlag.js`.
- **Darstellung:**
  - Umschalter „Nachtlicht | Niederschlag“; es ist immer nur eine Ebene zu sehen.
  - Grünskala: hell heißt trocken (0 mm gemessen), dunkelgrün heißt mindestens 1 200 mm. Sie hat keine gemeinsame Farbe mit dem Nachtlicht (Test).
  - Fehlende Werte: „keine Daten“ und „zu wenig Messungen“ gestreift, nie 0 mm.
  - Beim Anklicken stehen Wert, Zufallsfehler, gültiger Flächenanteil und das Kennzeichen TRMM-Kalibrierung bis 2014-05.
  - Quellenzeile mit dem Pflichtsatz der NASA, Evidenzstufe „beobachtet“.
  - Der Satz „Für großräumige Muster geeignet, an einzelnen Orten deutliche Abweichungen zu Messstationen möglich.“ steht über der Zeitleiste, in der Legende und im Dossier.
- **Stichproben** (Test am Export):
  - Mumbai Juli 2018: 1 070 mm, ± 77 mm (IMERG-Bericht: 1 072).
  - Mumbai Januar 2018: höchstens 10 mm.
  - Sahara und Kairo Juli 2018: trocken.
  - Berlin Januar 2014: 45 mm, TRMM-kalibriert.
- **Grenze:** Der Monat folgt der Zeitleiste des Nachtlichts. Den Niederschlag 2022-07 gibt es, er ist aber nicht wählbar.

### Abschluss

- **Fotos** (alle ohne Fehleranzeige):
  - 01 Zeitleiste; 02 Monat 2014-10; 03 Monat 2021-10; 04 2022-07 übersprungen; 05 Abspielen;
  - 06 Ägypten lang, 07 Deutschland, 08 Indien, 09 Nigeria, 10 Ägypten Index, 11 Ägypten BIP, 12 Vergleich;
  - 13 Niederschlag Mumbai Juli 2018, 14 Niederschlag Erde Juli 2018, 15 Niederschlag Berlin 2014-01;
  - im Unterordner `pdf/` die Bilder für die PDF.
- **Ersatzbilder-PDF:** 19 Seiten, 10,4 MB, in der Reihenfolge des Ablaufs.
  - Sie entsteht jetzt reproduzierbar: `scripts/ersatzbilder_pdf.py` mit `praesentation/ersatzbilder_seiten.json`.
  - Seite 1 habe ich als Vorschaubild angesehen.
- **Ablauf:** 7 Minuten mit neuen Abschnitten (Zeitleiste, Niederschlag). Alle neun veralteten Stellen sind korrigiert, die sechs neuen „Nicht behaupten“-Punkte des Prüfers eingefügt.
- **plausibilitaets-pruefer** (einmal): „plausibel mit Vorbehalt“. Umgesetzt:
  - Safe Mode und Teilmonat;
  - Warntext abgeschwächt, mit festem Länderkreis;
  - Abspiel-Hinweis;
  - Ablauf;
  - Skalenbeschriftung.
- **Tests:**
  - Gesamtlauf worktree: 865 bestanden, 0 übersprungen, 0 fehlgeschlagen.
  - Danach nur Texte geändert (Satz zum Niederschlag); die 67 Globus-Tests bestehen.
  - Zwei alte Tests hatten den Ladestand vom September fest eingetragen (Kolumbien bzw. USA 2018 „nicht geladen“). Sie prüfen jetzt je nach Zustand des Monats: `tests/test_export_globus.py`, `tests/test_link_nachtlicht_einheiten.py`. Der zweite stammt aus main und schlägt dort mit demselben Grund fehl, sobald man ihn mit dem heutigen Würfel laufen lässt.

## Umfang

- **~/ALEPH-ui (ui-geruest), Commits:**
  - `cab931a` Teil 1, `ae6f035` Teil 2, `3c3036a` Merge main, `d99d356` Teil 3;
  - dazu der Abschluss-Commit mit Prüfer-Auflagen, Ablauf, PDF und Berichten.
- **Neu:**
  - `aleph/export/globus_niederschlag.py`, `web/globus_niederschlag.js`;
  - `scripts/globus_startzeit.py`, `scripts/ersatzbilder_pdf.py`;
  - `praesentation/ersatzbilder_seiten.json`;
  - `tests/test_globus_niederschlag.py`;
  - zwei Berichte und die Fotos.
- **Geändert:** `aleph/export/globus.py`, `web/globus.js`, `globus.html`, `globus.css`, `globus_ueber.js`, `globus_zeitreihen.js`, `globus_vergleich.js`, drei Testdateien, `ARCHITECTURE.md` (zwei Absätze), `praesentation/ablauf.md`, `praesentation/globus_ersatzbilder.pdf`.
- **~/ALEPH:** nur `LOG.md` (ein Eintrag, ein Commit, auf deine Anweisung). Die Zeitreihen hast du selbst gerechnet.
- **SSD:**
  - gelesen: Nachtlicht- und IMERG-Würfel, Einheiten, Download-Protokoll, IMERG-Manifest und Rohdateien (nur Prüfsummen vor 2023);
  - geschrieben: nur die Sicherung `ergebnis_stand_2026-09-29.json`.
- **`web/daten/`** ist 321 MB groß, davon etwa 270 MB Niederschlag. Der Ordner ist nicht in Git.
- **Nicht angefasst:** der Nachtlicht-Download und `.env`. Keine Rechnung geändert, also kein statistik-pruefer.
- **Zeiträume:** Nichts aus 2023–2025 angezeigt oder inhaltlich ausgewertet. Der Prüfer hat nur Erzeugungsstempel in Manifest-Dateinamen gesehen.

## Empfehlung

1. **Vor der Präsentation:** den Ablauf einmal am echten Laptop durchklicken, vor allem den Umschalter zum Niederschlag und den zweiten Tab.
2. **Sprung 2021–2022 klären,** bevor 2021/2022 in eine Auswertung eingeht:
   - im Collection-2-Handbuch (Volltext) nach Brüchen suchen;
   - den Effekt in festen, stabilen Gebieten messen;
   - danach den statistik-pruefer einsetzen.
3. **Schnee-Verdacht:** Deutschland 2021-02 wurde nicht erkannt. Die Regel prüfen; ändern nur im Kalibrierungszeitraum und mit dem statistik-pruefer.
4. **Nach weiteren Download-Fortschritten** in dieser Reihenfolge ausführen:
   - erst `python -m aleph.link.laender_zeitreihen` in ~/ALEPH;
   - dann „Globus aktualisieren.command“ (dauert jetzt etwa 6 Minuten, wegen des Niederschlags).
5. **Den Test `test_technikprobe_2018_01_echte_daten` auf main** so anpassen wie im worktree, oder main den worktree-Stand übernehmen lassen.
6. **Optional:** Niederschlag 2022-07 wählbar machen (eigene Zeitleiste je Ebene).

## Nicht geprüft

- Globus in einem echten Chrome-Fenster mit Grafikkarte, und die Startzeit dort.
- Darstellung unter 1 440 px Breite (das Zustandsband ist dort sehr schmal).
- Die Ursache des Sprungs 2021–2022 und ob die fehlenden 2022-07-Kacheln mit dem Safe Mode zusammenhängen.
- Weltbank-Werte gegen die Weltbank-Seite; Niederschlag gegen Stationen.
- Die PDF ab Seite 2 als Bild (Aufbau mit 19 Seiten geprüft; die Einzelbilder habe ich vorher angesehen).
