# Statistisches Grundgerüst und Verknüpfungsgerüst Nachtlicht × Weltbank

Stand: 2026-09-27 (Arbeit vom 26./27.09.) · Code: `aleph/detect/statistik.py`, `trend.py`, `schnee.py`, `anomalie.py`, `synthetische_pruefung.py`, `aleph/link/nachtlicht_einheiten.py` · Methoden: `docs/methoden.md`

## Kurzfassung

- **Teil A ist gebaut und nur an künstlichen Daten geprüft:**
  - Anomalie (robust und klassisch parallel), Trend mit Mann-Kendall und Sen-Steigung.
  - Zwei getrennte Korrekturen für Autokorrelation (Hamed-Rao, Yue).
  - Benjamini-Hochberg mit αFDR = 0,10, Flächengewichtung, Moran's I, Mindestlängen, Pflichtfelder.
- **Hauptbefund:** Keine der beiden Korrekturen hält bei zeitlich abhängigem Rauschen das Fehlerniveau.
  - Yue macht es sogar schlimmer als gar keine Korrektur.
  - Erst die Mindestgröße (4 zusammenhängende Zellen) bringt die Falschmeldungen am künstlichen Würfel auf 0–1,5 %. Das gilt nur für räumlich unabhängiges Rauschen.
- **Berichtigt:** Die Basislinie der Anomalieerkennung nutzte bisher auch aufgefüllte Pixel.
- **Schnee:** Der Würfel hat nur schneefreie Felder und kein Schnee-Kennzeichen. Moskau im Februar 2018 ist vermutlich nicht erkannter Schnee plus Auswahl-Effekt. Solche Zellmonate werden jetzt als „Schnee-Verdacht“ ausgeschlossen.
- **Teil B:** Nachtlicht je Einheit und Weltbank-Land läuft. Die Technikprobe 2018-01 liefert für 146 von 236 Ländern eine Summe; die anderen sind gekennzeichnet. **Technikprobe, keine Aussage.**
- **Tests:** ganze Suite grün, 644 bestanden, keiner übersprungen. Prüfer: statistik-pruefer „bestanden mit Auflagen“, Plausibilitäts-Prüfer „plausibel mit Vorbehalt“.

## Urteil

- **Das Gerüst steht und ist ehrlich gekennzeichnet.** Bereit für eine Trendkarte echter Daten ist es noch nicht.
  - Vorher muss im Kalibrierungszeitraum (2013–2019) gemessen werden, wie stark echte Nachtlichtreihen von Monat zu Monat zusammenhängen (Autokorrelation r1).
  - Außerdem muss geprüft werden, ob die Mindestgröße bei räumlich zusammenhängendem Rauschen noch schützt.
- **Die Anomalieerkennung ist verbessert:** klassischer z-Wert, Fehler in der Basislinie behoben, Schnee-Regel.
- **Die Verknüpfung liefert plausible Größenordnungen.** Für eine spätere BIP-Prüfung braucht sie noch:
  - eine lichtgewichtete Abdeckung,
  - Ausschlüsse (Tansania, Mischzellen-Länder),
  - Gegenproben.

## Belege

### Quellen der Verfahren (geprüft am 2026-09-26)

- **Crossref-Metadaten geprüft:**
  - Benjamini & Hochberg 1995 (JRSS B 57(1), 289–300)
  - Mann 1945 (Econometrica 13(3), 245)
  - Sen 1968 (JASA 63(324), 1379–1389)
  - Hamed & Rao 1998 (J. Hydrol. 204, 182–196)
  - Yue, Pilon, Phinney & Cavadias 2002 (Hydrol. Process. 16(9), 1807–1829)
  - Moran 1950 (Biometrika 37, 17–23)
  - Rousseeuw & Croux 1993 (JASA 88(424), 1273–1283)
  - Wilks 2016 (BAMS 97(12), 2263–2273, DOI 10.1175/BAMS-D-15-00267.1)
- **Wilks, Originaltext:** gelesen im Autorenmanuskript (AMS 96th Annual Meeting, Paper 9.3, ams.confex.com), nicht in der Zeitschriftenfassung; die Verlagsseite und die Free Online Library waren gesperrt und wurden nicht umgangen.
  - Wörtlich: „for data grids exhibiting moderate to strong spatial correlation, approximately correct global test levels can be produced using the FDR procedure by choosing αFDR = 2αglobal.“
  - Die Regel betrifft das **globale** Niveau, nicht die Fehlerrate je Zelle.
- **Nicht am Originaltext geprüft:** die Einzelheiten von Hamed-Rao und Yue (Lag-Auswahl), die Moran-Varianz (Cliff & Ord, Buch) und die Faustregel n ≥ 10 für Mann-Kendall.
  - Die Beschränkung von Hamed-Rao auf 3 Lags stützt sich auf die Doku von pymannkendall (Drittquelle).
- **Nachgerechnet:**
  - Mann-Kendall gegen `scipy.stats.kendalltau` (gleiche p-Werte, auch mit Bindungen und Lücken).
  - Sen-Steigung gegen `scipy.stats.theilslopes`.
  - Moran's I gegen die Rechnung mit voller Matrix.
  - Die Zellflächen ergeben zusammen die Kugeloberfläche.

### Prüfung am künstlichen Würfel

Wiederholbar mit `.venv/bin/python -m aleph.detect.synthetische_pruefung`. Aufbau:
- 150 Monate, Zellen in den Tropen, damit die Schnee-Regel nicht eingreift.
- Würfel mit je 2 000 Zellen; BH mit q = 0,10.
- Evidenzstufe: Simulation, keine Messung.

**Ohne jeden Trend:**

| Rauschen | Würfel | Würfel mit ≥ 1 Meldung: ohne Korrektur / Hamed-Rao / Yue / gemeldet (mit Mindestgröße) | falsch „signifikante“ Fläche: ohne / Hamed-Rao / Yue / gemeldet |
|---|---|---|---|
| unabhängig | 100 | 9 % / 9 % / 9 % / **0 %** | 0,007 % / 0,007 % / 0,007 % / 0 % |
| Autokorrelation 0,5 | 20 | 100 % / 90 % / 100 % / **0 %** | 15,9 % / 0,33 % / 22,8 % / 0 % |
| Autokorrelation 0,8 | 20 | 100 % / 100 % / 100 % / **10 %** | 50,2 % / 4,2 % / 67,0 % / 0,02 % |

- **Unabhängiges Rauschen:** Erwartet sind höchstens etwa 10 % der Würfel mit Meldung (αFDR, siehe Wilks). Gemessen sind 9 %; das passt.
- **Mit Autokorrelation:**
  - Ohne Korrektur werden viel zu viele Trends gefunden.
  - Hamed-Rao senkt das stark, aber nicht auf das Soll.
  - **Yue erhöht die Falschmeldungen.**
  - „Beide Korrekturen melden“ ergab in allen Läufen genau das Hamed-Rao-Ergebnis. Es ist also keine doppelte Absicherung.

**Eingepflanzte Trends** (Blöcke mit 10 × 10 Zellen):
- Alle Blöcke wurden vollständig gefunden (100 %), in allen Varianten.
- Die Sen-Steigung traf die eingepflanzte Stärke:

  | eingepflanzt (% je Jahr) | geschätzt (% je Jahr) |
  |---|---|
  | +1 | +0,94 |
  | +3 | +2,90 |
  | +5 | +4,88 |
  | −3 | −3,02 |

- Falsche Meldungen außerhalb der Blöcke (2 000 Zellen ohne Trend):
  - **Ohne Autokorrelation:** Hamed-Rao 38 falsche unter 438 Meldungen (8,7 %, im Rahmen von 10 %); mit Mindestgröße 0.
  - **Autokorrelation 0,5:** ohne Korrektur 449 (53 % der Meldungen), Hamed-Rao 98 (20 %), Yue 591 (60 %); mit Mindestgröße **6 (1,5 %)**.

**Ausreißer** (Anomalieerkennung, Blöcke mit 3 × 3 Zellen):

| eingepflanzt | gemeldet | z robust / klassisch |
|---|---|---|
| ×1,5 | 0 von 9 | 4,7 / 5,0 (unter der Schwelle 5) |
| ×2 | 9 von 9 | 13,3 / 13,7 |
| ×3 | 9 von 9 | 9,7 / 9,9 |
| ×0,3 (Rückgang) | 6 von 9 | −7,8 / −7,8 |
| ×2, dazu ×6 in einem Basisjahr | 5 von 9 | 5,3 / **0,3**: alle 5 gemeldeten Zellen „z_uneinig“ |

- Falsch gemeldet: 0.
- Dass „×3“ einen kleineren z-Wert hat als „×2“, liegt an der unterschiedlichen Helligkeit und Streuung der Zellen. z misst „wie viele typische Schwankungen“, nicht Prozent.

**Rechenzeit:**
- Gemessen: 20 000 Zellen × 150 Monate, Trend 11,6 s.
- Hochgerechnet (× 51,84) auf das volle Raster mit 1 036 800 Zellen: etwa **10 Minuten**.
- Anomalie je Monat: etwa 2,7 s.

### Schnee (technische Prüfung an 2018, kein Endtest)

- **Code gelesen** (`aleph/layers/vnp46a3.py`, `FELD_TRIPEL`): Der Würfel speichert `AllAngle_Composite_Snow_Free` und `NearNadir_Composite_Snow_Free`, also nur schneefreie Beobachtungen. Ein Schnee-Kennzeichen ist nicht dabei.
- **Moskau** (allangle, Mittel über beobachtete Pixel):

  | Monat | Wert | beobachtete Pixel |
  |---|---|---|
  | 2018-01 | 68,0 | 97,9 % |
  | 2018-02 | 191,6 | 49,1 % |
  | 2018-03 | 148,1 | 56,4 % |

  Berlin (11–14) und Kairo (41) sind zu 100 % beobachtet und bleiben stabil.
- **Deutung, vom Plausibilitäts-Prüfer nachgerechnet und berichtigt:** Ein reiner Auswahl-Effekt reicht nicht. Die beobachteten Pixel tragen im Februar etwa 94 je Zellpixel bei, mehr als die ganze Zelle im Januar (etwa 67). Vermutlich kommt also nicht erkannter Schnee hinzu, der Licht zurückwirft. Laut Presseberichten gab es am 3./4.2.2018 Rekordschnee in Moskau; nicht am Original geprüft.
- **Festlegung „Schnee-Verdacht“:**
  - Bedingungen: |Breite| ≥ 23,5°, Winterhalbjahr der Halbkugel und unter 90 % beobachtete Pixel.
  - **Anomalie:** Diese Zellmonate werden weder im untersuchten Monat noch in der Basislinie bewertet. Verglichen wird ohnehin nur derselbe Kalendermonat.
  - **Trend:** Sie werden aus der Reihe genommen und gezählt.
  - **Lücke:** Verschneite, fast voll beobachtete Monate werden nicht erfasst (Helsinki 2019-01: 52 bei 98 %).
- **Empfehlung für den Kern-Umbau nach dem Download:** zusätzlich `AllAngle_Composite_Snow_Covered_Num` je Zelle speichern, also die Zahl der Schnee-Beobachtungen. Damit gäbe es ein echtes Kennzeichen. Den Würfel habe ich nicht geändert.

### Technikprobe 2018-01 (Teil B) – Technikprobe, keine Aussage

- 2018-01 hat Zustand 4: Nur Afrika, Europa und Asien sind geladen.
- Einheit: nW·cm⁻²·sr⁻¹ · km².
- Weltbank-Sicht mit unklaren Gebieten, Verteilung „normiert“.

| Land | Fläche km² | Abdeckung | Lichtsumme | je km² | Kennzeichen |
|---|---|---|---|---|---|
| Ägypten | 1 001 058 | 100 % | 713 000 | 0,71 | 1 % Sondergebiete mit unklarer Weltbank-Zuordnung |
| Deutschland | 357 674 | 100 % | 400 000 | 1,12 | – |
| Saudi-Arabien | 1 921 725 | 100 % | 1 983 000 | 1,03 | – |
| Nigeria | 907 499 | 100 % | 295 000 | 0,32 | – |
| Indien | 3 150 745 | 99,7 % | 2 295 000 | 0,73 | Gebiet der Weltbank-Zahl unklar; 5 % Sondergebiete (Kaschmir u. a.) |
| Russland | 16 953 097 | 46 % | — | (0,32) | 53 % Datenlage unzureichend; Schnee-Verdacht auf 24 %; keine Landessumme |
| USA | 9 464 218 | 1 % | — | – | überwiegend nicht geladen (97 %) |
| Tansania | 941 505 | 95 % | 33 000 | 0,04 | BIP nur Festland, Sansibar steckt im Umriss |

- **Summen:** 146 von 236 Weltbank-Ländern haben eine Landessumme.
  - 58 sind „überwiegend nicht geladen“ (Amerika, Ozeanien).
  - Die übrigen haben unter 90 % Abdeckung: Winter im Norden, Wolken, Kleinstaaten in Küstenzellen.
  - Kein Land ohne Summe steht ohne Kennzeichen da.
- **Plausibilitäts-Prüfer:**
  - Hat die Summen direkt aus dem Würfel nachgerechnet: höchstens 0,7 % Abweichung.
  - Die Muster passen:
    - Ägypten: Das Licht steckt im Niltal, 25 % im Raum Kairo.
    - Deutschland: Das Licht ist breit verteilt.
    - Nordkorea 0,04 gegen Südkorea 4,99 je km², Sudan 0,03 gegen Ägypten 0,71.
  - Gasfackeln prägen Irak (59 % aus dem Raum Basra), Nigeria (75 % Nigerdelta) und Algerien.
  - Für die Verhältnisse zwischen Ländern gibt es keine geprüfte Vergleichsquelle.

### Prüfer

- **statistik-pruefer: „bestanden mit Auflagen“.** Die Formeln (MK-Varianz, Sen-Band, HR-Faktor, TFPW, Moran-Varianz, Flächen) sind richtig. Ein Datenleck in den Endtest wurde nicht gefunden. Umgesetzt:
  - ehrliche Texte zum nicht eingehaltenen Niveau;
  - „trend_beide“ ist nicht als doppelte Absicherung dargestellt;
  - Sen-Band zusätzlich mit Hamed-Rao-Varianz (`sen_unten_hr`, `sen_oben_hr`);
  - Mindestgröße für Trendmeldungen;
  - Jahreszeit-Beschreibung berichtigt;
  - Schnee bei Anomalie und Trend gleich (auch in der Basislinie);
  - veralteter Text zum Zellmittel berichtigt;
  - Zahlen in der Doku geklärt (43,5 % galt für alle Lags; 0,18 % für reine AR-Reihen, 0,33 % für den Würfel);
  - gleiche Bezugsmenge für Zellzahl und Flächenanteil;
  - ganze Prozente, Reinheit mit einer Nachkommastelle.
  - Offene Auflagen siehe Empfehlung.
- **Plausibilitäts-Prüfer: „plausibel mit Vorbehalt“.** Umgesetzt:
  - Technikprobe mit dem endgültigen Code neu gerechnet; die CSV-Dateien waren vorher älter als der Code.
  - Schnee-Deutung berichtigt.
  - Rundung „90 % unter 90 %“ behoben: Es wird jetzt abgerundet.
  - Grenzen (Untergrenze, Gasfackeln, Gewächshäuser Närpes, kleine Küstenländer) im Modulkopf.
  - Offen: Die Liste „je km²“ braucht eine Mindestfläche (hier 1 000 km²), sonst stehen Macau und Bahrain vorn. FRA, XKX, HKG, MAC und SSD haben in der YAML keinen Eintrag unter `weltbank_laender` und erscheinen deshalb als „keine Angabe gefunden“; der Weltbank-Bericht nennt sie „passt“ bzw. „BIP unklar“.

### Tests

- `.venv/bin/python -m pytest -q -rs` nach allen Änderungen (2026-09-27): **644 passed**, keine Zeile „SKIPPED“. Die Tests mit echten Daten (SSD) liefen mit.
- Neu:
  - `tests/test_detect_trend.py`
  - `tests/test_link_nachtlicht_einheiten.py`
  - 15 Tests in `test_detect_statistik.py`
  - 4 in `test_detect_anomalie.py`
- In zwei älteren Anomalie-Tests ist die Schnee-Regel ausdrücklich abgeschaltet. Sie prüfen Rauschen und Mindestdauer bei 60° N, nicht Schnee.

## Umfang

- **Neu:**
  - `aleph/detect/trend.py`, `aleph/detect/schnee.py`, `aleph/detect/synthetische_pruefung.py`
  - `aleph/link/__init__.py`, `aleph/link/nachtlicht_einheiten.py`
  - `docs/methoden.md`
  - die zwei neuen Testdateien
- **Geändert:**
  - `aleph/detect/statistik.py` (erweitert, Bestehendes unverändert)
  - `aleph/detect/anomalie.py` (Version 0.2.0)
  - `aleph/detect/synthetisch.py` (Option `ar1`; mit 0 gleiche Zufallszahlen wie bisher)
  - `ARCHITECTURE.md` (Abschnitt 6, Nachtrag)
  - `requirements.txt`: `scipy==1.18.1` nachgetragen; war schon installiert, die Umgebung ist unverändert
  - Tests
- **Nicht angefasst:** Download (Prozess 63920), `aleph/layers/vnp46a3*.py`, Kachellisten, `scripts/`, `.env`. Würfel und Zell-Zuordnung wurden nur gelesen.
- **Zeiträume:**
  - Keine Daten aus 2023–2025 angesehen oder verwendet. Trend und Anomalie verweigern 2023+ ohne Freigabe; die Technikprobe verweigert 2023+.
  - Der Prüfer hat für Moskau und Helsinki 2018/2019 angesehen; das ist eine technische Prüfung.

## Empfehlung

1. **Vor jeder Trendkarte echter Daten:**
   - Im Kalibrierungszeitraum (2013–2019, sobald geladen) die Verteilung von r1 der bereinigten Nachtlichtreihen messen.
   - Am künstlichen Würfel räumlich zusammenhängendes Rauschen simulieren und prüfen, ob die Mindestgröße dann noch schützt.
   - Bessere Wege prüfen, jeweils erst nach Prüfung der Quelle am Originaltext:
     - ein Zufallsmodell mit Block-Permutation oder Block-Bootstrap, das Jahreszeit und Abhängigkeit erhält (ARCHITECTURE 8.3 verlangt das ohnehin);
     - ein saisonaler Kendall-Test.
2. **Weitere Prüfungen am künstlichen Würfel:** Jahreszeit-Schwankung, die mit dem Niveau wächst (Rest bei Lag 12), und Schnee-Lücken in einzelnen Jahren.
3. **Kern-Umbau nach dem Download:** die Zahl der Schnee-Beobachtungen (`*_Snow_Covered_Num`) in den Würfel aufnehmen. Klären, woher aufgefüllte Pixel stammen: nur frühere oder auch spätere Daten? Davon hängt ab, ob es ein Datenleck gibt.
4. **Vor der ersten Regression Nachtlicht × BIP:**
   - lichtgewichtete Abdeckung ergänzen;
   - Tansania und Länder mit Reinheit < 0,5 ausschließen;
   - Gegenproben rechnen (s_min 0,01 und 0,2, „flaechenanteil“, ohne „unklar“);
   - Gasfackeln kennzeichnen;
   - für die Westsahara klären, ob nur der verwaltete Teil zu Marokko zählt.
5. **Präsentation:**
   - Nicht „globales Niveau 5 %“ sagen. Belegt ist bei unabhängigen Zellen etwa 10 %; bei räumlicher Abhängigkeit ist nichts gezeigt.
   - Trends nur mit dem Hamed-Rao-Band zeigen.

## Nicht geprüft

- Hamed-Rao, Yue, Cliff & Ord und Kendall im Originaltext; BAMS-Fassung von Wilks.
- Räumlich abhängiges Rauschen (in allen Szenarien war Moran's I der Reste etwa 0).
- Jahreszeit-Schwankung, die mit dem Niveau wächst; Schnee-Lücken in einzelnen Jahren; die Wirkung auf die Steigung.
- Ob der Schnee-Verdacht Schnee tatsächlich erfasst (ohne Pixeldaten oder Schneekarte nicht zu klären).
- Externe Vergleichswerte für Nachtlicht-Summen je Land.
- Ob VNP46A3 Gasfackeln oder Polarlicht filtert (User Guide dazu nicht gelesen).
- Die Anwendung auf echte Daten über mehrere Jahre: Im Würfel sind erst 2018-01 bis -03 im Zustand 4.
