# Plausibilitätsprüfung: Globus alle Monate, Länderansicht lang, Niederschlag

Stand: 2026-10-05 · Prüfer: plausibilitaets-pruefer (ein Lauf) · abgelegt von der Hauptsitzung; Umsetzung siehe `2026-10-05_globus-alle-monate.md`

## Kurzfassung

- **Urteil: plausibel mit Vorbehalt.** Globus, Länderwerte und Niederschlag passen in Größenordnung, Rangfolge, Geografie und Jahreszeit; kein Hinweis auf verdrehtes Raster oder Lücken als 0.
- **2022-07:** Suomi NPP war vom 26.07. bis 20.08.2022 im Safe Mode; VIIRS-Daten laut Earthdata „not recoverable“. 2022-08 ist damit ein Teilmonat. (Von der Hauptsitzung an der Earthdata-Seite nachgelesen.)
- **Sprung 2021–2022:** keine NASA-Ursache gefunden (keine Bahnänderung, kein Versionswechsel; alle Monate aus derselben Collection-2-Neuprozessierung 2025). Warnung richtig, Wortlaut war zu stark („fast alle Länder“, „spricht eher für“).
- `praesentation/ablauf.md` war an mindestens 9 Stellen veraltet; 6 neue „Nicht behaupten“-Punkte.
- Kein Wert aus 2023–2025 in Fotos oder Oberflächentexten.

## Urteil

**plausibel mit Vorbehalt**

## Belege

**Gelesene Quellen:**
- Earthdata, „Suomi NPP Recovers from Safe Mode“ (https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-recovers-from-safe-mode): „Suomi NPP VIIRS data lost between July 26 and August 20, 2022, will not be recoverable.“
- MODAPS-Ausfallliste Suomi NPP (https://modaps.modaps.eosdis.nasa.gov/services/production/outages_suomi_npp.html): 26.–27. Juli L0 Outage, 27. Juli–11. August Lock-up 2022; 2021 nur kurze Ausfälle.
- LAADS-Produktseite VNP46A3: Version 2 wendet jährliche spektrale Antwortfunktionen gegen die Sensoralterung an; keine bekannten Probleme 2021/2022 genannt.
- Manifest-Dateinamen VNP46A3 (nur Erzeugungsstempel): 2015-06 → 2025099, 2020-06 → 2025133/134, 2021-06 → 2025148/149, 2022-06 → 2025155.
- Collection-2-Handbuch (PDF): Textextraktion fehlgeschlagen, nicht gelesen.

**Befunde:**
1. Nachtlicht-Globus (Fotos 01–05) plausibel; 2014-10 und 2021-10 zeigen das erwartete Bild. Hinweis zu 2022-07 nannte nur Katalogpositionen, nicht den Safe Mode; 2022-08 als normaler Monat angezeigt; Abspiel-Hinweis zu knapp (Wolken/Monsun, Abdeckungswechsel, Sprung fehlen).
2. Länderwerte stimmig (nachgerechnet: Deutschland 2014-01 je km² 1,06 → 1,1; Ägypten Index 2021 107; BIP-Index 2013 81). Deutschland 2021-02 nicht als Schnee markiert (Vermutung: nicht erkannter Schnee); Spitze 2013/14 ungeklärt. 125 von 236 Ländern mit Saisonbereinigung plausibel.
3. Sprung 2021–2022: als Warnung richtig, Begründung zu stark; Länderkreis wechselt zwischen den Jahren (Empfehlung: festen Länderkreis rechnen). Mögliche Ursache nur Vermutung (jährliche Sensorkorrektur Collection 2).
4. Niederschlag schlüssig, nicht mit Nachtlicht verwechselbar; Zellen liegen richtig; Größenordnungen nach Weltwissen passend. Kosmetik: überlappende Skalenbeschriftung.
5. Gesperrter Zeitraum sauber (nur Konstanten `GESPERRT_AB` und das Erscheinungsjahr der IMERG-Zitation).
6. ablauf.md: veraltete Stellen (Zeitraum, Amerika, Saisonbereinigung, Niederschlag „als Nächstes“, Datum, PDF-Seitenzahl); neue Punkte (a) 2021–2022 nicht als Wachstum, (b) nicht „bekannter NASA-Fehler“, (c) 2022-07/-08 Safe Mode, (d) Ägypten Licht flach/BIP +48 % nicht deuten, (e) Abspielen zeigt keinen Trend, (f) Niederschlag kein Stationswert, TRMM-Bruch, nicht mit Nachtlicht verknüpfen.

## Umfang

Alle 15 Fotos angesehen; Grep auf `web/` nach 2023–2025; Warntext, ablauf.md und Manifest-Dateinamen gelesen; Websuche Earthdata, MODAPS, LAADS; Stichproben nachgerechnet. Keine Dateien geändert, keine Werte aus 2023–2025 angesehen.

## Empfehlung

1. Hinweis 2022-07 mit Safe Mode ergänzen, 2022-08 als Teilmonat kennzeichnen.
2. Warntext abschwächen und präzisieren; „Nicht als Wachstum deuten“ fett lassen.
3. Median-Vergleich mit festem Länderkreis rechnen.
4. Abspiel-Hinweis ergänzen.
5. Deutschland 2021-02 und Spitze 2013/14 nicht ansprechen.
6. ablauf.md überarbeiten.
7. Optional: Collection-2-Handbuch im Volltext auf Brüche durchsuchen.
8. Skalenbeschriftung Niederschlag beheben.

## Nicht geprüft

Volltext Black-Marble-Handbuch Collection 2; ob die Sensorkorrektur den Sprung erklärt; Bahndrift 2021/2022; Weltbank-Werte gegen die Weltbank-Seite; Stationswerte Niederschlag; Ursache der fehlenden Kacheln 70–80° N in 2022-07 (Zusammenhang mit Safe Mode nur Vermutung).
