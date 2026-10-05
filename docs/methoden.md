# Methoden – statistisches Grundgerüst und Verknüpfung

Stand: 2026-09-26. Code: `aleph/detect/statistik.py`, `aleph/detect/trend.py`, `aleph/detect/anomalie.py`, `aleph/detect/schnee.py`, `aleph/link/nachtlicht_einheiten.py`.

Alles ist bisher **nur an künstlichen Daten** geprüft (`aleph/detect/synthetische_pruefung.py`). Auf echte Daten ist nichts davon inhaltlich angewandt worden. Die einzige Ausnahme ist die Technikprobe der Verknüpfung am Monat 2018-01.

„Geprüft“ bedeutet hier:
- **Metadaten:** Autoren, Jahr, Titel, Zeitschrift und Seiten sind bei Crossref gesehen.
- **Originaltext:** Die benutzte Aussage ist im Volltext gelesen.
- **nachgerechnet:** Das Ergebnis ist gegen eine unabhängige Umsetzung (scipy) oder von Hand geprüft.

## Übersicht

| Verfahren | Wozu | Quelle | geprüft |
|---|---|---|---|
| Robuste Abweichung (Median/MAD) | Anomalie je Zelle und Monat | Rousseeuw & Croux 1993 (Faktor 1,4826) | Metadaten; Faktor nachgerechnet |
| Klassischer z-Wert | Gegenprobe zur robusten Abweichung | Lehrbuch | nachgerechnet (Test) |
| Mann-Kendall | Gibt es einen Trend? | Mann 1945; Kendall (Buch) | Metadaten (Mann); gegen `scipy.stats.kendalltau` nachgerechnet |
| Sen-Steigung mit Band | Wie stark ist der Trend? | Sen 1968 | Metadaten; gegen `scipy.stats.theilslopes` nachgerechnet |
| Hamed-Rao | Autokorrelation (Varianzkorrektur) | Hamed & Rao 1998 | Metadaten; Einzelheiten nicht am Original |
| Prewhitening nach Yue | Autokorrelation (Reihe vorbehandeln) | Yue, Pilon, Phinney & Cavadias 2002 | Metadaten; Einzelheiten nicht am Original |
| Benjamini-Hochberg, αFDR = 2·αglobal | viele Tests zugleich | Benjamini & Hochberg 1995; Wilks 2016 | BH: Metadaten; Wilks: **Originaltext des Autorenmanuskripts** |
| Flächengewichtung | „X % der Fläche“ | Kugelformel | nachgerechnet (Summe = Kugeloberfläche) |
| Moran's I | räumliche Restabhängigkeit (Diagnose) | Moran 1950; Varianz nach Cliff & Ord (Buch) | Metadaten; gegen volle Matrix nachgerechnet |
| Schnee-Verdacht | Winter-Auswahleffekt kennzeichnen | eigene Festlegung | nur technisch an 2018-01..03 angesehen |
| Nachtlicht je Einheit | Verknüpfung mit Ländern | Vorschlag statistik-pruefer | Rechnung von Hand im Test |

Die vollständigen Quellenangaben mit DOI stehen im Kopf von `aleph/detect/statistik.py`.

## Anomalie: robust und klassisch parallel

- **Wozu:** Jeder Monatswert einer Zelle wird mit demselben Kalendermonat früherer Jahre verglichen (Januar mit Januar). Gezählt werden nur Werte mit mindestens 50 % beobachteten Pixeln.
- **Robuste Abweichung:**
  - z = (Wert − Median) / (Streuung · √(1 + π/(2n))).
  - Die Streuung ist das Größte aus 1,4826 · MAD, einer gemeinsamen Mindest-Streuung und 0,5 nW.
  - Gemeldet wird nach diesem Wert.
- **Klassischer z-Wert:**
  - z = (Wert − Mittel) / (Streuung · √(1 + 1/n)).
  - Die Streuung ist die Standardabweichung, mit derselben Mindest-Streuung.
  - **`z_uneinig`** heißt: Die beiden Werte widersprechen sich an der Zellschwelle |z| ≥ 5. Das ist eine Diagnose, zum Beispiel für einen Ausreißer in der Basislinie, keine Auswahl.
- **Berichtigt am 2026-09-26:** Die Basislinie nutzte bisher das Mittel **mit** aufgefüllten Pixeln. Jetzt nutzt sie wie der untersuchte Monat nur beobachtete Pixel.
- **Mindestlänge:** 5 frühere Jahre, sonst „nicht bewertbar“.
- **Grenzen:**
  - Die p-Werte sind nominell; eine Falschmeldungsrate wird nicht garantiert (Modulkopf `anomalie.py`).
  - Rückgänge sind schwerer zu erkennen als Anstiege.
  - Die Stärke in z hängt von Helligkeit und Streuung der Zelle ab: Im Test ergab „×3“ z ≈ 10, „×2“ in einem anderen Block z ≈ 13.

## Trend: Mann-Kendall, Sen-Steigung, zwei Korrekturen

- **Wozu:** Hat eine Zelle über einen Zeitraum einen stetigen Anstieg oder Rückgang?
- **Ablauf:**
  1. Zuerst wird die Jahreszeit abgezogen: der Median desselben Kalendermonats **innerhalb des untersuchten Zeitraums**.
  2. Mann-Kendall liefert die Frage „ob“, die Sen-Steigung das „wie stark“, samt 95-%-Band.
  3. Die Autokorrelation wird auf zwei Wegen korrigiert. Die Ergebnisse stehen in **getrennten Feldern**.
     - **Hamed-Rao:** berücksichtigt nur die ersten 3 Lags und nur signifikante. Der Faktor wird auf mindestens 1 gesetzt; das ist eine eigene Festlegung, Begründung unten.
     - **Yue-Prewhitening:** Trend abziehen, Lag-1-Autokorrelation entfernen, Trend wieder addieren.
  4. Jede Karte wird mit Benjamini-Hochberg auf αFDR = 0,10 korrigiert.
  5. Als Trend gilt eine Zelle nur, wenn **beide** Korrekturen sie melden (`trend_beide`). Widersprechen sie sich, gilt das als Unsicherheit (`uneinig`).
- **Mindestlängen:**
  - 24 gültige Werte für Mann-Kendall.
  - 60 für die Korrekturen.
  - 3 Werte je Kalendermonat.
  - Darunter heißt es „nicht bestimmbar“ (NaN), nie 0.
- **Gemessen am künstlichen Würfel** (150 Monate, je 2 000 Zellen; Tabelle im Bericht):
  - **Ohne Trend und ohne Autokorrelation:** 9 von 100 Würfeln hatten mindestens eine Meldung. Erwartet ist bei unabhängigen Zellen höchstens etwa αFDR = 10 %; das passt.
  - **Autokorrelation 0,5:**

    | Variante | Fläche „signifikant“ |
    |---|---|
    | ohne Korrektur | 15,9 % |
    | Hamed-Rao | 0,33 % |
    | Yue | 22,8 % |

  - **Das Prewhitening nach Yue senkt die falschen Treffer nicht, es erhöht sie.** Deshalb darf es nie allein entscheiden.
  - **Hamed-Rao ohne Untergrenze** ließ bei reinem Rauschen 43,5 % der Würfel etwas melden, mit Untergrenze 6 %.
  - **Mehr als 3 Lags** waren bei Autokorrelation schlechter.
  - **Eingepflanzte Trends** von 1, 3, 5 und −3 % je Jahr wurden alle gefunden. Die geschätzte Stärke lag bei 0,94, 2,90, 4,88 und −3,02 % je Jahr.
- **Grenzen:**
  - Bei Autokorrelation 0,5 bleiben mit Korrektur noch etwa 0,3 % der Fläche falsch „signifikant“, bei 0,8 etwa 4 %. Die echte Autokorrelation des Nachtlichts ist **nicht gemessen**; das ist vor dem Einsatz zu klären (Kalibrierungszeitraum).
  - Ein Bruch im Messsystem erscheint als Trend.
- **Rechenzeit:** Gemessen wurden 20 000 Zellen × 150 Monate in 9,9 s. Hochgerechnet auf das volle Raster (1 036 800 Zellen) sind das etwa 8,5 Minuten.

## Viele Tests zugleich: Benjamini-Hochberg mit αFDR = 2·αglobal

- **Wozu:** Bei Hunderttausenden Zellen findet man allein durch Zufall Tausende „signifikante“.
- **Regel nach Wilks (2016):** αFDR = 2 · αglobal, also 0,10 bei 0,05. Im Autorenmanuskript steht wörtlich: „for data grids exhibiting moderate to strong spatial correlation, approximately correct global test levels can be produced using the FDR procedure by choosing αFDR = 2αglobal.“
- **Wichtig:** Das betrifft das **globale** Niveau, also die Wahrscheinlichkeit, dass irgendwo etwas gemeldet wird, obwohl nirgends etwas ist. Es ist keine Fehlerrate je Zelle. Bei fast unabhängigen Zellen liegt dieses Niveau nahe αFDR selbst, also bei 10 %; das zeigen auch unsere 9 %.
- **Grenze:** Gelesen wurde das Manuskript (AMS 2016, Paper 9.3), nicht die Zeitschriftenfassung (BAMS 97(12), 2263–2273), weil die Verlagsseite gesperrt war.

## Flächengewichtung

- Zellen werden zu den Polen kleiner: bei 60° halb so groß, bei 80° ein Sechstel.
- Jede Aussage „X % der Fläche“ nutzt `flaechenanteil()`, also Zellflächen auf der Kugel. Bezug sind nur die bewertbaren Zellen.
- Die Datumsgrenze macht keine doppelten Zellen: Das Gitter läuft von −180 bis 180. Für Nachbarschaften ist sie geschlossen.

## Moran's I (Diagnose)

- **Wozu:** Sind die Reste benachbarter Zellen abhängig? Dann gelten die Voraussetzungen von BH und die Wilks-Regel nur eingeschränkt.
- Dünn besetzte 8er-Nachbarschaftsmatrix (`scipy.sparse`), über die Datumsgrenze geschlossen.
- Gerechnet wird auf den Resten (Abweichung minus Sen-Gerade) an 12 Zeitpunkten und auf der z-Karte.
- Nur Diagnose, kein Test mit Garantie. Mindestens 30 Zellen.

## Schnee

- **Befund:** Der Würfel speichert nur die schneefreien Felder (`*_Composite_Snow_Free`). Ein Schnee-Kennzeichen gibt es dort nicht.
- **Moskau 2018-01/02/03:**

  | Monat | Wert | beobachtete Pixel |
  |---|---|---|
  | 2018-01 | 68 | 98 % |
  | 2018-02 | 192 | 49 % |
  | 2018-03 | 148 | 56 % |

- **Vermutung (berichtigt nach der Plausibilitätsprüfung):** Es ist nicht nur ein Auswahl-Effekt (nur wenige, helle Pixel zählen als beobachtet). Die beobachteten Pixel selbst sind im Februar um mindestens 35–40 % heller als die ganze Zelle im Januar. Naheliegend ist deshalb zusätzlich nicht erkannter Schnee, der das Licht zurückwirft.
- **Regel „Schnee-Verdacht“** (eigene Festlegung): |Breite| ≥ 23,5°, Winterhalbjahr der Halbkugel und unter 90 % beobachtete Pixel.
- **Umgang:**
  - **Anomalie und Trend gleich:** Zellmonate mit Verdacht werden nicht bewertet. Bei der Anomalie gilt das für den untersuchten Monat und für die Basislinie, beim Trend für die Reihe. Sie werden gezählt und als Karte ausgewiesen. Verglichen wird ohnehin nur mit demselben Kalendermonat.
- **Grenzen:**
  - Wolken erzeugen dasselbe Muster.
  - Verschneite Monate, die trotzdem fast ganz als „beobachtet“ zählen, werden nicht erfasst (zum Beispiel Helsinki 2019-01: 52 bei 98 % beobachtet).
  - Tropische Hochgebirge werden nicht erfasst.
  - Ein echtes Schnee-Kennzeichen braucht den Kern-Umbau nach dem Download (Empfehlung im Bericht).

## Nachtlicht je Einheit und Weltbank-Land (Technikprobe)

- **Wozu:** Die spätere Prüfung „Nachtlicht und Wirtschaft“ vorbereiten. Bisher gibt es **keine Regression und keine Aussage über das BIP**.
- **Rechnung:**
  - Lichtsumme einer Zelle = Mittel beobachteter Pixel × gültige Pixel/3600 × Zellfläche. Die Einheit ist nW·cm⁻²·sr⁻¹ · km².
  - Die Summe wird auf die Einheiten verteilt: nach Flächenanteil, geteilt durch den Landanteil der Zelle. Meerpixel sind im Würfel gültig und dunkel, deshalb gehört das Licht zum Land.
  - Danach wird je Weltbank-Land in der Sicht „so wie die Weltbank zählt“ summiert.
- **Einstellbar, mit Standard und Grund** (`VerknuepfungsEinstellungen`):
  - Verteilung „normiert“.
  - s_min = 0,05: Zellen mit weniger Land werden nicht verteilt.
  - Reinheitsgrenze 0,5 bei Schwelle 0,9: nur Kennzeichen.
  - Tansania „markieren“: BIP nur Festland.
  - Mindestabdeckung 0,9: darunter keine Landessumme.
- **Fehlende Daten** („nicht geladen“, „keine Daten“, „unzureichend“) gehen nie als 0 ein. Sie werden als Flächenanteile ausgewiesen.
- **Grenzen:**
  - Ohne BIP ist nichts über Wirtschaft gesagt.
  - Das Licht von Schiffen und Plattformen in Küstenzellen landet auf dem Land.
  - Gasfackeln zählen als Licht.
  - Die Umrisse haben den festen Stand Mai 2022.

## Bekannte Messeigenheiten Nachtlicht

Stand: 2026-10-06. Diese Regeln gelten für jede Auswertung, Grafik und Aussage mit dem Nachtlicht (NASA Black Marble VNP46A3). Herkunft je Punkt in Klammern; Hauptquelle ist `berichte/2026-10-05_anstieg-2021-2022.md` („Bericht Anstieg“).

- **2020 ist ein Tiefjahr.**
  - Befund (*beobachtet*): Jahreswert 2020 gegen 2019 etwa −3 % (alle beleuchteten Zellen, Afrika-Europa-Asien), Mai −8,4 %, Juni −10,6 %. In der Vergleichsquelle EOG ist die Delle nur im Mai und Juni sichtbar (−5,0 % / −5,9 %), im Jahreswert nicht (0,999) (Bericht Anstieg, Teil 1 „Pandemie 2020“, und Teil 4).
  - Regel: Vergleiche **gegen 2019**, nicht gegen 2020. Wo 2020 vorkommt, dazuschreiben: „2020 ist ein Tiefjahr“. Ein Vergleich Jahr gegen Vorjahr ab 2020 überzeichnet den Anstieg 2021.
  - Dass die Pandemie die Ursache ist, ist eine naheliegende Vermutung, **nicht geprüft**.
- **2022 liegt im Mittel 3–6 % über einer Vergleichsquelle desselben Sensors.**
  - Befund (*beobachtet*): gegen 2019 NASA +12,7 %, EOG VCMCFG +8,5 %; 95-%-Intervall des Unterschieds +2,7 bis +5,9 Prozentpunkte gegen 2019, nur räumliche Streuung erfasst; gemessen nur an Landzellen südlich 60° N in Afrika-Europa-Asien, Klassen mittel und hell (Bericht Anstieg, Teil 4). EOG ist nur **teilweise unabhängig** verarbeitet: gleicher Sensor (Suomi NPP VIIRS), eine eigene Kalibrierkette ist nicht belegt.
  - **Ursache offen.** Wer richtig liegt, ist nicht entschieden; EOG ist nicht „die Wahrheit“ (anderes Verfahren, ohne Mond- und Winkelkorrektur).
  - Regel: **Keine Korrektur**, nichts ausschließen. 2022 in Trend- und Ländervergleichen kennzeichnen, in der Oberfläche mit „NASA-Wert 2022 im Mittel 3–6 % höher als eine Vergleichsquelle desselben Sensors; Ursache offen“ (Bericht: „… als eine unabhängige Quelle …“; „desselben Sensors“ ergänzt, weil der Bericht „unabhängig“ ohne diesen Zusatz ausschließt). Änderungen unter etwa 6 % zwischen 2021 und 2022 nicht als Veränderung deuten. Dunkle und schwach beleuchtete Zellen 2022 mit „Grundwert 2022 erhöht“ versehen (Bericht Anstieg, Empfehlung 2–3).
  - 2021 wird normal verwendet: Der Anstieg 2021 erscheint auch bei EOG; kein Hinweis auf einen Verarbeitungsfehler (Bericht Anstieg, Urteil 1).
- **2022-07 fehlt, 2022-08 ist ein Teilmonat.**
  - Befund: Suomi NPP war vom 26.07. bis 20.08.2022 im Sicherheitsmodus; laut NASA sind die VIIRS-Daten dieser Zeit nicht wiederherstellbar (Earthdata, „Suomi NPP Recovers from Safe Mode“, gelesen am 2026-10-05; Zitat und Beleg in `aleph/export/globus.py` im worktree, Konstante `SAFE_MODE_2022`). Die MODAPS-Ausfallliste nennt für dieselbe Zeit „Lock-up 26.07.–11.08.“ (Bericht Anstieg, Teil 2.2).
  - 2022-07 ist in der Untersuchung ganz ausgeschlossen, 2022-08 ist dort als Teilmonat vermerkt (Bericht Anstieg, „Gemeinsame Grundlage“). Dass der Wert für 2022-08 nur auf den Tagen ab 21.08. beruht, folgt aus der Earthdata-Angabe (`MONATS_HINWEISE` in `aleph/export/globus.py`).
  - Regel: Beide Monate nicht deuten. **Keine Jahresmittel mit unterschiedlichen Monaten** vergleichen (2022 fehlen Juli und August); stattdessen gleiche Monate oder einen festen Zellkreis nehmen (Bericht Anstieg, Empfehlung 4).
- **Schnee.**
  - Befund: Der Würfel enthält nur die schneefreien Felder, ein Schnee-Kennzeichen fehlt. Verschneite Monate können heller erscheinen (Vermutung, Moskau 2018-02; Abschnitt „Schnee“ oben).
  - Regel: Zellmonate mit Schnee-Verdacht werden nicht bewertet; die Untersuchung zum Anstieg nutzt nur Zellmonate ohne Verdacht (Bericht Anstieg, „Gemeinsame Grundlage“). Die Verdachtsregel erfasst **nicht jeden** Schneemonat (z. B. Helsinki 2019-01).
- **Norden über 65° N ist unsicher.**
  - Befund: Nördlich von etwa 65° N weichen Würfel und der Earth-Engine-Nachbau A deutlich voneinander ab, auch in Städten (Norilsk ×1,7); welche Quelle falsch liegt, ist offen. Belastbar ist der Vergleich nur südlich 55° N; 55–65° N ist eine Übergangszone (A dort rund 4–5 % heller) (`berichte/2026-09-28_earth-engine-a.md`). Die Grenze 65° N selbst ist die Kennzeichnung aus `berichte/2026-09-29_nachtlicht-bip-2018.md`. Die Vergleichsquelle EOG ist im Norden lückenhaft; die Gegenprobe im Bericht Anstieg nutzt deshalb nur Zellen südlich 60° N (Teil 4).
  - Regel: Aussagen nördlich 65° N nicht verwenden; Länder mit nennenswertem Lichtanteil dort kennzeichnen (Kennzeichen „nördlich von 65° N“, `berichte/2026-09-29_nachtlicht-bip-2018.md`).
- **Methodenwarnung** (Bericht Anstieg, Empfehlung 5): Ein Vergleich mit dem Median desselben Kalendermonats über einen festen Basiszeitraum macht aus jedem stetigen Trend Stufen im Januar (Test `test_basislinie_macht_aus_stetigem_anstieg_eine_treppe`). Für Trend- oder Bruchfragen die Jahreszeit gemeinsam mit dem Trend schätzen.
