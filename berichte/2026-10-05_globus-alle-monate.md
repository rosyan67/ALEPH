# Globus mit allen Nachtlicht-Monaten 2013–2022

Stand: 2026-10-05 nachmittags · **Zwischenstand** (Teil 2 wartet auf deine Freigabe) · worktree `~/ALEPH-ui` (Branch `ui-geruest`, Commit `cab931a`, gepusht) · Fotos: `berichte/2026-10-05_globus-alle-monate_bilder/`

## Kurzfassung

- **Teil 1 fertig:** Der Globus zeigt 119 Monate (2013-01 bis 2022-12). 2022-07 steht rot als „zurückgestellt“ in der Zeitleiste, mit Grund aus dem Download-Protokoll.
- Neue Zeitleiste über alle Jahre: Jahresmarken, ein Zustandsfeld je Monat (vollständig / nur Afrika-Europa-Asien / zurückgestellt), Abspielknopf mit Hinweis „keine Trendaussage“.
- **Startzeit:** vorher 3,1 s, nachher 2,8 s bis zum fertigen Globus (Median, Chrome ohne Grafikkarte). Monate laden schon immer erst beim Auswählen.
- **Teil 2 blockiert:** Die Länder-Zeitreihen müssen in ~/ALEPH neu gerechnet werden. Das Berechtigungssystem hat diesen Lauf abgelehnt. Ich habe es nicht umgangen. Die Länderansicht zeigt deshalb noch 2018-01 bis 2021-01.
- **Teil 3 entfällt:** IMERG ist nicht fertig (Bericht ohne Urteil, Download läuft). Nichts gebaut.
- Tests der Globus-Dateien: 58 bestanden. Gesamtlauf, Prüfer, PDF und Ablauf folgen nach Teil 2.

## Urteil

Teil 1 ist vorzeigbar. Jeder Monat 2013–2022 ist in der Zeitleiste mit seinem Zustand zu sehen, keiner fehlt still. 2023–2025 bleibt unsichtbar und nicht auswählbar.

Teil 2 ist nicht erledigt. Er hängt an einem einzigen Schritt (siehe Empfehlung).

## Belege

### Teil 1 – Alle Monate

- **Export** (`python -m aleph.export.globus`, 190 s):
  - Würfel: 35 Monate vollständig, 120 nur Afrika-Europa-Asien, 1 leer (2022-07).
  - Angezeigt werden 119 Monate vor 2023: 2013-01 bis 2017-12 und 2020-11 bis 2022-12 nur Afrika-Europa-Asien, 2018-01 bis 2020-10 vollständig.
  - 36 fertige Monate 2023–2025 erscheinen nur in der Konsole, in keiner Datei der Oberfläche (Test).
- **2022-07:** Im Würfel Zustand 0 („leer“). Das Download-Protokoll führt den Monat zuletzt am 2026-10-04 als „ZURÜCKGESTELLT“: „Im Katalog fehlen 36 Positionen der Referenzliste (z. B. h00v01 …)“.
  - Der Export liest das Protokoll nur. Die Zeitleiste zeigt den Monat rot, mit Grund im Tooltip und in der Legende.
  - Beim Ziehen, Klicken oder Abspielen wird er übersprungen. Ein Hinweis nennt ihn und den gezeigten Ersatzmonat (Foto 04).
- **Ladezeit** (`scripts/globus_startzeit.py`, neu; je 3 Durchgänge, Median):

  | Stand | Seite geladen | Globus fertig | Startdaten | JS-Speicher |
  |---|---|---|---|---|
  | vorher, 37 Monate | 1,1 s | 3,1 s | 8,8 MB | 109 MB |
  | 119 Monate, alte Seite | 1,2 s | 3,1 s | 14,0 MB | 131 MB |
  | 119 Monate, neue Seite | 1,2 s | 2,8 s | 14,0 MB | 131 MB |

  - Die Startdaten wachsen nur durch die Länderwerte (`laender.js` 2,5 → 7,6 MB). Monatsdateien lädt die Seite erst bei Auswahl.
  - Gemessen ohne Grafikkarte. Taugt zum Vergleich, nicht als Zeit auf dem Präsentationsrechner.
- **Speicher beim Abspielen:** neu höchstens 8 entpackte Monate. Abspieltest über 75 Monate (2013-01 bis 2019-04): immer 8 behalten, Speicher zwischen 125 und 211 MB, keine Fehleranzeige. Etwa 1,7 s je Monat.
- **Zeitleiste:** Regler über alle 120 Kalendermonate, damit gleiche Abstände gleiche Zeit sind. Jahresmarken 2013–2022. Ein Klick auf das Zustandsband wählt den Monat.
- **Abspielknopf ▶:** läuft Monat für Monat. Solange er läuft, steht rot hinterlegt: „Monatswerte schwanken jahreszeitlich (Schnee, kurze Nächte); keine Trendaussage.“ (Foto 05)
- **„Über ALEPH“** nennt jetzt 119 Monate, die nicht auswählbaren Monate und die Zahl der Monate nur Afrika-Europa-Asien.
- **Stichproben** am echten Export (Test): Berlin, Paris, Kairo, Sahara in 2014-06, 2018-06, 2019-06, 2021-06 im erwarteten Bereich. Kolumbien und USA in Monaten nur Afrika-Europa-Asien „noch nicht geladen“, in vollständigen Monaten gemessen.
- **Ein alter Test schlug fehl:** Er erwartete Kolumbien 2018-06 als „noch nicht geladen“. Seit dem Ladestand Oktober ist 2018-06 vollständig, Kolumbien hat 99 % beobachtete Pixel. Der Test prüft jetzt je nach Zustand des Monats.

### Teil 2 – Länderansicht (nicht erledigt)

- Die Länderansicht liest `auswertungen/laender_zeitreihen/ergebnis.json` von der SSD. Die Datei wird in ~/ALEPH gerechnet (`python -m aleph.link.laender_zeitreihen`) und steht noch auf dem Stand vom 29.09. (37 Monate, Weltbank 2018–2021).
- **Abgelehnt:** Meinen Aufruf in ~/ALEPH hat das Berechtigungssystem als Eingriff in eine gemeinsam genutzte Stelle abgelehnt. Ich habe ihn nicht auf anderem Weg nachgeholt.
- Gesichert habe ich vorher den alten Stand: `ergebnis_stand_2026-09-29.json` neben der Datei.
- **Schon da** (aus dem Globus-Export): Das Länderfeld im Dossier hat Weltbank-Werte 2013–2022.

### Teil 3 – Niederschlag

- `~/ALEPH/berichte/2026-10-02_imerg.md`: Kurzfassung, Urteil und Empfehlung „folgt am Ende“. Der IMERG-Download läuft (Prozess für 2018).
- Also **nicht fertig**. Nichts gebaut, auch kein Platzhalter.

## Umfang

- **~/ALEPH-ui (ui-geruest):**
  - geändert: `aleph/export/globus.py`, `web/globus.js`, `web/globus.html`, `web/globus.css`, `web/globus_ueber.js`, `tests/test_export_globus.py` (+6 Tests, 1 angepasst), `tests/test_globus_oberflaeche.py` (+2), `ARCHITECTURE.md` (ein Absatz)
  - neu: `scripts/globus_startzeit.py`, 5 Fotos, dieser Bericht
  - `web/daten/` neu erzeugt (nicht in Git)
- **SSD:** gelesen: Würfel, Einheitentabelle, Download-Protokoll. Geschrieben: nur die Sicherung `ergebnis_stand_2026-09-29.json`.
- **Nicht angefasst:** Download (Prozess 82367), IMERG-Lauf, `.env`, Code in ~/ALEPH.
- **Zeiträume:** nur Monate vor 2023. Keine inhaltliche Auswertung von 2023–2025.
- **Prüfer:** noch keiner. statistik-pruefer ist nicht nötig, weil keine Rechnung geändert wurde. plausibilitaets-pruefer folgt einmal am Ende.

## Empfehlung

1. **Teil 2 freigeben.** Zwei Möglichkeiten:
   - Du führst selbst im Terminal aus: `cd ~/ALEPH && .venv/bin/python -m aleph.link.laender_zeitreihen` (Dauer geschätzt 10–20 Minuten). Danach sagst du mir Bescheid.
   - Oder du erlaubst mir diesen einen Aufruf ausdrücklich.
   - Die Rechnung ändert keine Datei in ~/ALEPH. Sie schreibt nur ihr Ergebnis auf die SSD und stört den IMERG-Lauf nicht.
2. Danach mache ich weiter: Teil 2, Fotos, plausibilitaets-pruefer, Gesamttests, PDF, Ablauf, Abschluss dieses Berichts.

## Nicht geprüft

- Globus in einem echten Chrome-Fenster mit Grafikkarte, auch die Startzeit dort.
- Das Zustandsband auf Bildschirmen schmaler als 1440 px (die Felder sind dort etwa 5 px breit).
- Der Gesamtlauf aller Tests (nur die Globus-Testdateien).
- Inhaltliche Plausibilität der Monate 2013–2017 (plausibilitaets-pruefer folgt am Ende).
