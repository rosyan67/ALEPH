# Steckbrief: NASA VNP46A3 (Black Marble, monatliches Nachtlicht)

Stand der Recherche: 2026-09-21. Erstellt vom Agenten „datenquellen-scout".

Kennzeichnung in diesem Dokument:
- **[Anbieter]** = Angabe stammt von NASA/LAADS/Black-Marble-Team, mit Link.
- **[Dritt]** = Angabe stammt von einer Drittquelle (z. B. Weltbank-Paket), nicht vom Anbieter.
- **[Messung]** = eigene Messung des Auftraggebers, keine Herstellerangabe.
- **[Eigene Überlegung]** = Schlussfolgerung des Scouts, nicht vom Anbieter belegt.
- „nicht geprüft" = konnte nicht belegt werden.

> **Korrektur der Hauptsitzung (2026-09-21), nach dem Scout-Bericht:** Der Steckbrief liest `_Quality` als reine Anzahl-Schwelle (0 = mehr als 3 Nächte, 1 = höchstens 3). Das passt **nicht** zur Probekachel, und die Abschnitte 8, 16 und 17 (Sommer-Erklärung) stützen sich darauf.
> Die Messung im Einzelnen: 3 339 711 Fehlwert-Pixel hatten alle `_Num` = 0. Nur die 16 aufgefüllten Pixel (Quality 2) hatten ebenfalls `_Num` = 0. Das Maximum von `_Num` in der ganzen Kachel war 15. Es gibt also gültige Pixel mit bis zu 15 Nächten, und trotzdem hat **kein** Pixel Quality 0. Bei einer reinen Anzahl-Schwelle von 3 wäre das nicht möglich.
> Was Quality 1 in den Monatsprodukten wirklich bedeutet, ist damit **offen**. Die Definition stammt zudem nur aus einer automatischen Zusammenfassung des PDF-Textes. Die Verteilung von `_Num` unter den gültigen Pixeln wurde nicht ausgewertet, die Probedatei ist gelöscht. Bis dahin gilt: Quality nicht als Filter und nicht als Datenlage-Maß verwenden, sondern `_Num` (Zahl der Nächte) und die Zahl gültiger Pixel.
> Bestätigt (Hauptsitzung, direkt bei NASA gelesen): Die Auslieferung von Suomi-NPP-Produkten endet am 1. November 2026, 13:00 UTC, das Datum kann sich laut NASA ändern. Die Mitteilung nennt keine einzelnen Produkte und sagt nichts zum Archiv bereits erzeugter Daten (https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026).
> **Zweite Messung (Hauptsitzung, 2026-09-22), zweite Probekachel:** VNP46A3.A2019274.h17v08 (Oktober 2019, 10° W – 0°, 0–10° N, Golf-von-Guinea-Küste, Land-Wasser-Mix). Hier passt die Anbieter-Definition genau: NearNadir Quality 0 → `_Num` zwischen 4 und 7 (Mittel 4,10); Quality 1 → `_Num` zwischen 1 und 3 (Mittel 1,56); Quality 2 (aufgefüllt) → `_Num` = 0 bei allen 1 784 479 Pixeln; Quality 255 → keine gültigen Pixel. Bei AllAngle dasselbe Muster (Quality 0 → `_Num` 4–21, Quality 1 → `_Num` 1–12). Die Quality-Definition aus Abschnitt 8 (>3 Nächte = gut) **stimmt also in dieser Kachel exakt**. Die erste Probekachel (hohe Breite, Juni) bleibt eine echte, unerklärte Abweichung, ist aber damit vermutlich eine Besonderheit dieser Kachel/Jahreszeit (z. B. Polartag-Effekt, siehe Abschnitt 8) und **kein allgemeiner Bruch der Produktdefinition**. Fehlwerte (−999,9) traten in der zweiten Kachel ausschließlich bei `Land_Water_Mask = 255` auf (18 845 von 5 760 000 Pixeln, 0,3 %); alle Pixel mit Land- oder Wasser-Maskenwerten (0, 1, 2, 3, 5) waren zu 100 % gültig. Die „58 % Fehlwerte" der ersten Probekachel lassen sich damit **nicht** pauschal mit Land/Wasser erklären; sie sind eher mit fehlenden gültigen Nächten (Polartag/Wolken) verträglich. Die zweite Probedatei wurde nach der Auswertung gelöscht (wie die erste). Weiterhin gilt: `_Quality` nicht als Filter verwenden, sondern `_Num` und die Zahl gültiger Pixel als Datenlage – jetzt zusätzlich gestützt durch eine zweite, unabhängige Messung.

Hinweis zur Methode: Die PDF-Dokumente (Black Marble User Guide, ATBD, Fachartikel) sind als Binärdatei nicht direkt lesbar gewesen. Der Text des User Guides wurde über einen Text-Umwandlungsdienst (r.jina.ai) und anschließend eine automatische Zusammenfassung des WebFetch-Werkzeugs gelesen. Die Zitate mit Tabellen- und Seitenzahlen stammen daraus und sollten vor einer Veröffentlichung einmal im Original nachgeschlagen werden.

---

## 1. Name und Anbieter

- **Name:** VIIRS/NPP Lunar BRDF-Adjusted Nighttime Lights Monthly L3 Global 15 arc second Linear Lat Lon Grid, Version 2 (Collection 2.0), Kurzname VNP46A3, Produktfamilie „Black Marble".
- **Anbieter:** NASA VIIRS Land Science Investigator-led Processing System (Land SIPS), verteilt vom LAADS DAAC. Principal Investigator des Black-Marble-Teams laut Earthdata: Zhuosen Wang (University of Maryland / NASA Goddard). [Anbieter: https://www.earthdata.nasa.gov/data/projects/black-marble]
- **DOI:** 10.5067/VIIRS/VNP46A3.002 [Anbieter: https://www.earthdata.nasa.gov/data/catalog/laads-vnp46a3-2]
- **Offizielle Seiten:**
  - LAADS-Produktseite: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A3
  - Earthdata-Katalog: https://www.earthdata.nasa.gov/data/catalog/laads-vnp46a3-2
  - Black-Marble-Projektseite: https://www.earthdata.nasa.gov/data/projects/black-marble
  - User Guide v2.0 (Oktober 2024): https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/archives/Document%20Archive/Science%20Data%20Product%20Documentation/Black-Marble_v2.0_UG_2024.pdf
  - User Guide Collection 2.0 (zweite Fassung auf der Black-Marble-Seite): https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf
  - ATBD v1.1 (Juli 2020): https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/archives/Document%20Archive/Science%20Data%20Product%20Documentation/Product%20Generation%20Algorithms/VIIRS_Black_Marble_ATBD_v1.1_July_2020.pdf (Inhalt nicht gelesen, siehe „nicht geprüft")

## 2. Inhalt

- Monatlich zusammengesetzte (komposite), um Mondlicht und Atmosphäre korrigierte Strahldichte des nächtlichen Lichts, gemessen vom Day/Night Band (DNB) des VIIRS-Sensors auf Suomi NPP. [Anbieter: https://www.earthdata.nasa.gov/data/catalog/laads-vnp46a3-2]
- **Einheit:** nW·cm⁻²·sr⁻¹ (nWatts/(cm² sr)), Fehlwert −999,9, Skalierung 1,0. [Anbieter: User Guide Tabelle 11, S. 18, für AllAngle_Composite_Snow_Covered; für die übrigen Felder analog angenommen, siehe auch [Messung] unten]
- **28 Datenfelder (SDS):** Strahldichte-Komposit, Anzahl Beobachtungen, Qualität und Standardabweichung, je für drei Blickwinkelklassen und zwei Schneezustände, dazu Plattform, Land-Wasser-Maske, Länge/Breite. [Anbieter: https://www.earthdata.nasa.gov/data/catalog/laads-vnp46a3-2]
  - Blickwinkel: **Near-nadir** (Sensor-Zenitwinkel 0–20°), **Off-nadir** (40–60°), **All angles** (alle qualitativ guten Beobachtungen). [Anbieter: User Guide Tabelle 11, S. 18–22]
  - Schneezustand: **Snow-free** (Beobachtungen ohne Schnee/Eis) und **Snow-covered** (Beobachtungen mit erkanntem Schnee/Eis). [Anbieter: User Guide Tabelle 11, S. 18]
- **Kompositbildung:** Aus täglichen, atmosphären- und mond-BRDF-korrigierten Werten (VNP46A2). Ausreißer werden mit der Boxplot-Regel (Tukey; außerhalb Q1 − 1,5·IQR bis Q3 + 1,5·IQR) entfernt, dann wird der **Mittelwert** der übrigen Beobachtungen gebildet. [Anbieter: User Guide Abschnitt 2.3, S. 5]
- **Rauschschwelle (wichtig für ALEPH):** „To remove any residual background noise, the NTL composite values with radiances less than 0.5 nW·cm⁻²·sr⁻¹ are set to zero." Komposit-Werte unter 0,5 werden also auf exakt 0 gesetzt. [Anbieter: User Guide Abschnitt 2.3, S. 6]
- **Keine Vegetationskorrektur** in Collection 1 und 2. [Anbieter: User Guide Abschnitt 4, S. 10]

## 3. Räumliche Auflösung und Abdeckung

- 15 Bogensekunden (ca. 500 m am Äquator), lineares Breiten-/Längengitter, global. [Anbieter: LAADS-Produktseite]
- Version 2 deckt **Land und Wasser** ab (Version 1 nur Land). [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A3]
- Kacheln zu 10° × 10° (2400 × 2400 Pixel). [Messung, siehe Abschnitt 14]

## 4. Zeitliche Auflösung und Zeitraum

- Monatlich. Sammlung beginnt laut CMR-Metadaten am 2012-01-01, „EndsAtPresentFlag: true". [Anbieter: https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=VNP46A3&version=2]
- Die täglichen Suomi-NPP-Produkte laufen ab 19. Januar 2012. [Anbieter: https://www.earthdata.nasa.gov/data/projects/black-marble]
- Der Untersuchungszeitraum von ALEPH (2013–2025, Entscheidung E3) ist damit vollständig abgedeckt; 2012 stünde als zusätzliches Basisjahr zur Verfügung. [Eigene Überlegung, aus den beiden Zeitangaben]
- Verzögerung: Die Black-Marble-Produkte werden laut Projektseite in Fast-Echtzeit (innerhalb von 3 Stunden) erzeugt (gilt für die Suite, für das Monatsprodukt nicht einzeln geprüft).

## 5. Zugang

- **Frei, mit kostenlosem NASA-Earthdata-Konto.** Anmeldung: https://urs.earthdata.nasa.gov (Kontoanlage selbst nicht geprüft; Einrichtung durch Alexander laut ARCHITECTURE.md, Entscheidung E8).
- **Werkzeuge:** Earthdata Search, LAADS-Archiv, S3-Bucket `s3://prod-lads/VNP46A3`. [Anbieter: CMR-Metadaten, Link oben]
- **Variablennamen in `.env`** (nur Namen, keine Werte): `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`.
- Der Zugriff über `earthaccess` und die CMR-Suche wurde vom Auftraggeber bereits benutzt (siehe [Messung]). Die earthaccess-Dokumentation selbst wurde vom Scout nicht gelesen: nicht geprüft.

## 6. Lizenz und Nutzungsbedingungen

- LAADS: Die Daten werden „openly shared, without restriction, in accordance with the EOSDIS Data Use and Citation Guidance". [Anbieter: https://www.earthdata.nasa.gov/data/catalog/laads-vnp46a3-2]
- CMR-Metadaten: `AccessConstraints: None`, `FreeAndOpenData: true`, keine Gebühr. [Anbieter: CMR-Link oben]
- NASA-Grundsatz: „Unless the content is marked with a use restriction or license, data provided from a NASA-led mission are licensed as Creative Commons Zero (CC0)." [Anbieter: https://earthdata.nasa.gov/learn/use-data/data-citations-acknowledgements]
- **Folgerung für ALEPH:** Nicht-kommerzielle Nutzung erlaubt. Ein Verbot der öffentlichen Anzeige von Rohwerten wurde nirgends gefunden; laut den oben genannten Aussagen (ohne Einschränkung, CC0) ist auch die Anzeige von Rohwerten und Ableitungen zulässig. [Eigene Überlegung, gestützt auf die Zitate]. Nicht geprüft: ob einzelne Dateien eine eigene Einschränkungskennzeichnung tragen (in den Metadaten der Sammlung wurde keine gefunden). Für `META` daher: Anzeige von Rohwerten zulässig.
- **Quellenangabe:** von NASA *erbeten*, nicht verpflichtend: „we request that you cite the datasets". [Anbieter: Earthdata-Zitierhinweis, Link oben]. Der User Guide verweist auf die LAADS-Zitierrichtlinie (https://modaps.modaps.eosdis.nasa.gov/services/faq/LAADS_Data-Use_Citation_Policies.pdf, Inhalt nicht gelesen: nicht geprüft).
- **Zitierform (APA, von der Earthdata-Katalogseite):**
  NASA VIIRS Land Science Investigator-led Processing System. (2025). *VIIRS/NPP Lunar BRDF-Adjusted Nighttime Lights Monthly L3 Global 15 arc second Linear Lat Lon Grid* [Dataset]. NASA Level 1 and Atmosphere Archive and Distribution System Distributed Active Archive Center. https://doi.org/10.5067/VIIRS/VNP46A3.002
  [Anbieter: https://www.earthdata.nasa.gov/data/catalog/laads-vnp46a3-2]. Das CMR nennt als Veröffentlichungsdatum der Version 2 den 23. Oktober 2025. Zusätzlich wird im User Guide zitiert: Román, M. O., et al. (2018). NASA's Black Marble nighttime lights product suite. *Remote Sensing of Environment*, 210, 113–143. https://doi.org/10.1016/j.rse.2018.03.017. Für die Komposite gehört ergänzend Wang, Z., Shrestha, R. M., Román, M. O., Kalb, V. L. (2022), *IEEE Geoscience and Remote Sensing Letters*, 19, doi 10.1109/LGRS.2022.3176616 (https://ieeexplore.ieee.org/document/9779217/) in die Literaturangabe, denn der User Guide nennt sie als Beschreibung der Komposite (Abschnitt 2.3). Das Zugriffsdatum sollte angegeben werden.

## 7. Python-Zugriff und Dateiformat

- **Format:** HDF-EOS5 (HDF5), eine Datei pro 10°-Kachel und Monat. [Anbieter: LAADS-Produktseite]
- **Bibliothek:** `earthaccess` (ARCHITECTURE.md Abschnitt 5). Lesen der HDF5-Dateien z. B. mit `h5py` (nicht vom Scout getestet; die Feldstruktur stammt aus [Messung]).
- **Drittpaket, nur zur Kenntnis:** `blackmarblepy` bzw. `blackmarbler` der Weltbank. Diese Pakete nutzen als Standardvariable für VNP46A3 `NearNadir_Composite_Snow_Free`. [Dritt: https://worldbank.github.io/blackmarbler/, https://worldbank.github.io/blackmarblepy/api/blackmarble.html]. Für ALEPH nicht nötig (gleiche Ladelogik für alle Quellen).

## 8. Qualitätsfelder: Bedeutung (Frage 1)

Tabelle 12, Abschnitt 5.3, S. 23 des User Guides (Felder `*_Quality` der Monats- und Jahresprodukte): [Anbieter: User Guide Collection 2.0, https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf; wörtlich gleiche Definitionen im Weltbank-Paket, [Dritt] https://worldbank.github.io/blackmarbler/]

| Wert | Bedeutung laut Anbieter |
|---|---|
| 0 | „Good-quality: The number of observations used for the composite is larger than 3" |
| 1 | „Poor-quality: The number of observations used for the composite is less than or equal to 3" |
| 2 | „Gap filled NTL based on historical data" |
| 255 | Fehlwert („Fill value", keine Berechnung) |

**Kernaussage:** Quality bei den Monatskompositen ist eine reine **Anzahl-Schwelle**: Gut heißt mehr als 3 gültige Nächte im Monat, schlecht heißt 3 oder weniger. Es ist **keine** Aussage über Wolken, Schnee oder Kalibrierung eines einzelnen Pixels.

**Warum kann ein ganzer Sommermonat in hohen Breiten fast nur „schlecht" sein?**
- Bestätigt (Anbieter): Nur hochwertige, wolkenfreie, korrigierte Nachtbeobachtungen gehen ins Komposit. Nachts wird über den Sonnen-Zenitwinkel definiert; bei täglichen Werten sind Zenitwinkel zwischen 102° und 108° mit „Poor-quality (high solar zenith angle 102–108 degrees)" markiert (User Guide Tabelle 9, S. 17). Die Fachseite nennt die Ausweitung des nutzbaren Zenitwinkels von >108° auf >102° als Neuerung in Version 2. [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A3] Der Text des User Guides enthält nach dem verfügbaren Auszug keine eigene Aussage zu Polartag oder hohen Breiten im Sommer („The document does not discuss polar region … limitations" laut Auszug): nicht im Wortlaut belegt.
- [Eigene Überlegung, nicht vom Anbieter belegt]: Die Sonne steht zur Sonnenwende um Mitternacht bei Breite φ rechnerisch φ + 23,44° − 90° über dem Horizont. Bei 55° N sind das −11,6° (Zenitwinkel etwa 101,6°), bei 50° N etwa −16,6° (Zenitwinkel etwa 106,6°). Im Juni gibt es also in der Kachel 50–60° N nahe der Sonnenwende praktisch keine Nächte mit Zenitwinkel über 102°, oder nur sehr wenige (der Überflug liegt zudem etwa um 01:30 Ortszeit, nicht genau um Mitternacht; [Dritt: https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/s-npp-nasa-viirs-overview/, nur als Suchergebnis-Zusammenfassung gelesen, Seite selbst nicht geöffnet]). Zusammen mit Wolken bleiben dann höchstens wenige gültige Beobachtungen, also Quality 1. Das passt zur Beobachtung in der Probekachel, ist aber **nicht bewiesen**. Ob Beobachtungen mit Zenitwinkel 102–108° in das Komposit eingehen oder nicht, ist im gelesenen Material nicht eindeutig: nicht geprüft.
- Quality 2 („gap filled") ist laut Anbieter für Lücken gedacht, die durch Wolken, Schnee und andere kurzlebige Störungen entstehen: „persistent data gaps caused by nighttime clouds, snow, and other ephemeral artifacts" [Anbieter, User Guide, sinngemäß im Auszug]. Dass in der Probekachel nur 16 Pixel Quality 2 haben, ist eine Messung und nicht verallgemeinerbar.

**Empfohlene Nutzung durch den Anbieter:** Eine ausdrückliche Empfehlung, welche Qualitätswerte auszuschließen sind, wurde in den Anbieterdokumenten **nicht gefunden**: nicht geprüft. Das Weltbank-Paket rät für Monats-/Jahresdaten, die Werte 1 und 2 zu entfernen, wenn man nur gute Pixel will [Dritt: https://worldbank.github.io/blackmarbler/articles/assess-quality.html]. Für ALEPH ist ein bloßes Ausschließen von Quality 1 riskant: In Ihrer Probekachel bliebe kein einziger Pixel übrig. Sinnvoller [Eigene Überlegung]: Quality nicht als Filter, sondern zusammen mit `_Num` als Datenlage-Angabe je Zelle und Monat mitführen (siehe Abschnitt 11).

## 9. Welches Datenfeld für die Anomalieerkennung? (Frage 2)

**Belegt:**
- Der Anbieter warnt: „Users should be aware that artificial lights derived from VIIRS DNB data show a strong angular effect … impacting retrievals, particularly across dense urban centers where NTL radiance at nadir can be significantly higher than off-nadir observations." [Anbieter: User Guide Abschnitt 2.3, S. 6]. Deshalb gibt es getrennte Komposite je Blickwinkelklasse.
- Das Black-Marble-Team hat gezeigt, dass Winkel- und Atmosphäreneffekte die Unsicherheit der Messung dominieren, und empfiehlt, winkelkonsistente Beobachtungen zu verwenden (Wang et al. 2021, RSE 263, 112557). [Anbieter/Fachartikel: https://ntrs.nasa.gov/citations/20210017813, nur Zusammenfassung gelesen]
- Schnee erhöht laut User Guide die Streuung des Lichts durch höhere Bodenreflexion: „The presence of nighttime snow also enhances the scattering of reflected NTL due to the increased surface reflectance." [Anbieter: User Guide Abschnitt 2.3, S. 6]. Schnee-Beobachtungen und schneefreie Beobachtungen sind daher nicht direkt vergleichbar.
- Das Weltbank-Paket nimmt als Standard `NearNadir_Composite_Snow_Free`. [Dritt]. Das ist eine Paketvorgabe und keine Empfehlung von NASA.

**Vorschlag [Eigene Überlegung, keine ausdrückliche Anbieter-Empfehlung gefunden: nicht geprüft]:**
- **Hauptfeld: `NearNadir_Composite_Snow_Free`.** Grund: gleichbleibende Blickgeometrie über die Jahre, wenig Winkelartefakte (die bei Änderungen des Überflugmusters Scheinschwankungen erzeugen könnten); Schnee als Störgröße ausgeschlossen. Nachteil: weniger Beobachtungen pro Monat als AllAngle (nur Zenitwinkel bis 20°), also häufiger Quality 1 und geringeres `_Num`. Das ist plausibel, aber nicht gemessen.
- **Zweitfeld: `AllAngle_Composite_Snow_Free`** als Vergleich und zur Datenlage-Bewertung. Es hat die meisten Beobachtungen, mischt aber Winkel.
- `OffNadir_*`: für die Erkennung nicht sinnvoll (stärkste Winkelabhängigkeit, Randverzerrung).
- `*_Snow_Covered`: nicht mit Snow_Free mischen. Wo im Monat kein schneefreier Wert existiert, sollte die Zelle als „Datenlage unzureichend" gelten und nicht auf Snow_Covered ausweichen. Wie das Produkt Pixel ohne schneefreie Beobachtung füllt, ist im User Guide nicht ausdrücklich beschrieben: nicht geprüft.
- **Empfohlener Prüfschritt vor der Festlegung:** In der Probekachel (und einer Winterkachel) `AllAngle` und `NearNadir` nebeneinander auf Fehlwertanteil, Quality-Verteilung und `_Num` vergleichen.

**Wie werden Störungen behandelt (belegt, sofern nicht anders vermerkt)?**
- **Wolken:** Standard-VIIRS-Wolkenmaske (VCM); nur hochwertige, wolkenfreie Beobachtungen gehen in die Korrektur. [Anbieter: User Guide Abschnitt 2.2, S. 3]. Der User Guide räumt selbst ein, dass nächtliche Wolkenmaskierung schwierig ist (Abb. 4, S. 24 im Auszug).
- **Mondlicht:** Mondstrahlung, Aerosol und Bodenalbedo werden per Inversion eines Lunar-BRDF-Modells geschätzt und korrigiert; bei mondlosen Nächten wird die Beleuchtungsgeometrie auf Nadir gesetzt. [Anbieter: User Guide Abschnitt 2.3, S. 4–5]
- **Streulicht:** Ist Teil der Korrektur; Genauigkeitsziel im User Guide 0,45 nW·cm⁻²·sr⁻¹ (Tabelle 14, S. 26). [Anbieter, im Auszug]
- **Schnee:** eigenes Schneestatus-Flag (0 = kein Schnee/Eis, 1 = Schnee/Eis) auf Tagesebene, Schneealbedo-Verfahren bei aktivem Flag; Monatskomposite getrennt nach Schneezustand. [Anbieter: User Guide Tabelle 10 S. 17, Abschnitt 2.2 S. 3]
- **Polarlicht (Aurora), Sonnenglitzern (Glint), Mondfinsternis:** in Version 2 eigene Qualitätswerte auf Tagesebene (3 = Mondfinsternis, 4 = Aurora, 5 = Glint); polarlichtbelastete Pixel werden mit Fülldaten gefüllt (User Guide Abschnitt 2.3, S. 6, im Auszug). [Anbieter: https://www.earthdata.nasa.gov/data/catalog/laads-vnp46a3-2]. Die Fachpublikation Wang et al. 2021 nennt Polarlicht in mittleren bis hohen Breiten als Quelle kurzlebiger Artefakte. [Anbieter/Fachartikel, Zusammenfassung]
- **Polarnacht / Polartag:** siehe Abschnitt 8. Polarnacht (dauerhafte Dunkelheit) liefert im Winter viele Nachtbeobachtungen, dann kommt aber oft Schnee ins Spiel; Polartag (Sommer) liefert kaum brauchbare Nächte. Beide Effekte sind im gelesenen Anbietermaterial nicht ausdrücklich beschrieben: nicht geprüft.
- **Rauschschwelle:** Komposit-Werte unter 0,5 nW·cm⁻²·sr⁻¹ werden auf 0 gesetzt (Abschnitt 2). Folge für ALEPH [Eigene Überlegung]: Dunkle Zellen haben viele exakte Nullen; die MAD (Abschnitt 6 der Architektur) kann 0 werden, dann darf nicht durch 0 geteilt werden. Zwischen „Null wegen Schwelle" und „Fehlwert" (−999,9) muss unterschieden werden.

## 10. Brüche und Änderungen über die Zeit (Frage 3)

Belegt:
- **Version 2 / Collection 2:** Neu gegenüber Version 1: Strahldichte als Fließkommazahl statt Ganzzahl (kein Sättigen bei 6553,5), Land **und** Wasser, neue Qualitätswerte (Mondfinsternis, Polarlicht, Glint), nutzbarer Zenitwinkel >102° statt >108°, jährliche spektrale Antwortfunktionen. [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A3]
- **Kalibrierung / Alterung des Suomi-NPP-Sensors:** Die Fachseite nennt, dass in Version 2 jährliche spektrale Antwortfunktionen angewendet werden, um die Verschlechterung („degradation") des SNPP-DNB nach dem Start zu berücksichtigen. [Anbieter: LAADS-Produktseite, Link oben]. Ob nach dieser Korrektur noch ein Restdrift bleibt, ist nicht geprüft. Der Satz „NOAA-20 und NOAA-21 sind stabil" stammt nur aus einer Suchergebnis-Zusammenfassung, nicht aus einer gelesenen Anbieterseite: nicht geprüft.
- **Neuerzeugung 2025:** NASA weist aus, dass seit 25. August 2025 alle VNP-/VJ1-Produkte Collection 2 sind und die Verarbeitung von Collection 1 beendet ist. [Anbieter: https://www.earthdata.nasa.gov/data/projects/black-marble]. Der Zeitstempel im Dateinamen der Probedatei (…2025133214434) zeigt Erzeugung im Jahr 2025 [Messung]. Für die Nachvollziehbarkeit sollten Dateinamen (inkl. Zeitstempel) im Rohdaten-Verzeichnis festgehalten werden, weil eine spätere Neuerzeugung dieselben Monate ändern kann [Eigene Überlegung].
- **Sensorwechsel:** Innerhalb von VNP46A3 gibt es nur Suomi NPP. NOAA-20 hat ein eigenes Produkt (VJ146A3), verfügbar ab 1. Januar 2018 [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ146A3]. Das Feld `DNB_Platform` kennt die Werte 0 = Suomi-NPP, 1 = NOAA-20, 2 = NOAA-21, 3 = NOAA-20 und NOAA-21 kombiniert [Anbieter: User Guide Tabelle 13, S. 23]. Ob in VNP46A3 immer nur 0 vorkommt: nicht geprüft.
- **Ende der Suomi-NPP-Lieferung:** NASA teilt mit, dass die Auslieferung von Suomi-NPP-Datenprodukten am **1. November 2026 um 13:00 UTC endet**; Nutzer sollen auf NOAA-20/NOAA-21 wechseln. Was mit dem **Archiv** bereits erzeugter Daten geschieht, steht in der Mitteilung nicht. [Anbieter: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026]. Zusätzlich gab es vom 2. bis 10. August 2026 eine Störung; Daten von 2026-08-03 02:00 UTC bis 2026-08-06 16:24 UTC wurden von der Verarbeitung ausgeschlossen. [Anbieter: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-viirs-data-outage-anomaly-august-2-2026]. Beides betrifft 2026, nicht den Untersuchungszeitraum 2013–2025. Wichtig ist es für Aktualisierungen und für den Zeitplan (Hackathon 14.–15. November 2026): **Alle benötigten Kacheln sollten vor dem 1. November 2026 heruntergeladen werden** [Eigene Überlegung, Vorsichtsmaßnahme].
- **Weitere Brüche** (Bahnlage/Überflugzeit von Suomi NPP über die Jahre, Umstellung der Straßenbeleuchtung auf LED und ihr Effekt auf das DNB-Signal, Änderung der Schneeflag-Eingangsdaten): **nicht geprüft**.

## 11. Num und Std (Frage 5)

- **`*_Num`:** „Number of Observations of Temporal Radiance Composite" je Blickwinkel-/Schneeklasse, also die Zahl der Nächte, die in den Pixelwert des Monats eingegangen sind. [Anbieter: User Guide Tabelle 11, S. 18–22]. Datentyp uint16, Fehlwert 65535 [Messung].
- **`*_Std`:** „Standard Deviation of Temporal Radiance Composite", also die Streuung der Nachtwerte im Monat. [Anbieter: User Guide Tabelle 11]. Wie Std bei Num = 1 oder 2 aussieht (z. B. 0 oder Fehlwert): nicht geprüft.
- **Eignung für „Datenlage":**
  - `_Num` eignet sich gut, denn der Anbieter selbst trennt bei 3 Beobachtungen in gut und schlecht (Quality 0 / 1). ALEPH kann eigene Schwellen setzen und muss sie in `META` festhalten. [Eigene Überlegung]
  - `_Std` beschreibt die zeitliche Streuung im Monat, nicht die Verlässlichkeit. Bei sehr wenigen Beobachtungen ist sie selbst unsicher. Eignet sich als Zusatzinformation, nicht als Ersatz für `_Num`. [Eigene Überlegung]
  - Bei der Aggregation auf 0,25° (60 × 60 Pixel je Zelle) sollten pro Zelle mindestens gespeichert werden: Anzahl der Pixel mit gültigem Wert, Mittelwert der gültigen Pixel, Mittelwert bzw. Minimum von `_Num`, Anteil Quality 0/1/2. Fehlwerte −999,9 und 65535 müssen vorher maskiert werden. [Eigene Überlegung, zu ARCHITECTURE.md Abschnitt 4 und 6]

## 12. Bekannte Schwächen (Zusammenfassung)

- Starke Winkelabhängigkeit der Messung, besonders in dichten Städten (Anbieter, User Guide Abschnitt 2.3).
- Schnee verfälscht Nachtlicht (Anbieter, User Guide Abschnitt 2.3); Schnee-Eingangsdaten sind grob (Wang et al. 2021, Zusammenfassung).
- Fehler in der nächtlichen Wolkenmaske (Wang et al. 2021, Zusammenfassung).
- Polarlicht in mittleren/hohen Breiten (Wang et al. 2021, Zusammenfassung).
- Wenig Nächte im Sommer in hohen Breiten [Eigene Überlegung, plausibel, nicht belegt]; im Winter Schnee.
- Werte unter 0,5 nW werden auf 0 gesetzt (Anbieter).
- Tatsächliche Genauigkeit vor Ort schwer prüfbar: „quality-assessed in situ NTL measurements are not widely available" (Anbieter, User Guide Abschnitt 6, S. 27).
- Suomi NPP endet für Nutzer am 1. November 2026 (Anbieter, siehe Abschnitt 10).
- Unterschied zwischen Herstellerangabe und Messung: LAADS nennt ca. 58 MB pro Datei [Anbieter], die Katalogabfrage des Auftraggebers ergab im Mittel etwa 40 MB [Messung]. Grund: nicht geprüft.

## 13. Rolle in ALEPH

Erster **Erkennungs-Layer** (Nachtlicht: menschliche Aktivität, Stromausfälle, Stadtwachstum) gemäß ARCHITECTURE.md Abschnitt 5, Untersuchungszeitraum 2013–2025, Zielraster 0,25° global (1440 × 720), monatlich. Aus 60 × 60 Pixeln entsteht genau eine Zelle, eine Kachel ergibt 40 × 40 Zellen [Messung].

## 14. Eigene Messungen (2026-09-21)

Dies sind Messungen des Auftraggebers, **keine Herstellerangaben**. Sie wurden vom Scout nicht überprüft, sondern wörtlich übernommen.

- Katalogabfrage über earthaccess/CMR, Sammlung VNP46A3 Version 2: Beginn 2012-01-01. Für 2013–2025 gibt es 156 Monate, 84 135 Dateien (Kacheln), zusammen 4 108 GB (4,01 TB). Pro Monat rund 536–540 Kacheln, Kachelnamen von h00v01 bis h35v15. Dateigröße pro Kachel zwischen 0,7 und etwa 110 MB, Mittel etwa 40 MB. Pro Jahr rund 294–362 GB.
- Eine Probedatei (VNP46A3.A2020153.h19v03.002.2025133214434.h5, Juni 2020, Kachel 10–20° O, 50–60° N) hat 27 518 677 Byte und stimmt mit der Katalogangabe (26,2 MB) überein.
- Dateiformat HDF5, Gitter 2400 x 2400 Pixel je 10°-Kachel, Pixelabstand 15 Bogensekunden (0,004167°). 60 x 60 Pixel ergeben genau eine 0,25°-Zelle, eine Kachel ergibt 40 x 40 Zellen.
- Datenfelder in der Datei (Gruppe HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields): je für AllAngle, NearNadir, OffNadir und je für Snow_Free und Snow_Covered die Felder Composite, _Num, _Quality, _Std; dazu DNB_Platform, Land_Water_Mask, lat, lon.
- Feld AllAngle_Composite_Snow_Free: float32, Einheit nWatts/(cm^2 sr), Fehlwert −999,9 (kein NaN!), gültiger Bereich >= 0. Feld _Num: uint16, Fehlwert 65535. Feld _Quality: 0 = gut, 1 = schlecht, 2 = aufgefüllt, 255 = Fehlwert.
- In dieser einen Probekachel (Juni 2020, 50–60° N): 58,0 % der Pixel sind Fehlwerte (vermutlich Meer, nicht geprüft), 871 von 1600 Zellen haben keinen gültigen Pixel. Von den gültigen Pixeln haben 2 420 273 Quality = 1 („schlecht") und nur 16 Quality = 2; kein einziger Pixel hat Quality = 0. Das ist EINE Kachel in EINEM Monat und darf nicht verallgemeinert werden.

**Abgleich mit Herstellerangaben (Scout):**
- Die Fehlwerte (−999,9 für Strahldichte, 255 für Quality) und die Qualitätsbedeutungen 0/1/2/255 stimmen mit dem User Guide überein.
- Zum Fehlwertanteil von 58 %: Version 2 deckt laut Anbieter **auch Wasser** ab (siehe Abschnitt 3). „Meer" allein ist daher nicht ohne Weiteres die Erklärung. Alternativ oder zusätzlich kommen fehlende gültige Sommernächte in Frage (siehe Abschnitt 8, [Eigene Überlegung]). Empfohlener Prüfschritt: Fehlwertanteil getrennt nach `Land_Water_Mask` auswerten.
- ~~Dass kein Pixel Quality 0 hat, ist mit der Anzahl-Definition (nur ≤ 3 Nächte) in dieser Kachel und diesem Monat vereinbar, aber nicht bewiesen.~~ **Korrigiert, siehe Kasten oben:** Die Messung widerspricht der Anzahl-Definition.

## 15. Datenmenge

- Gesamt 2013–2025 global: **4 108 GB (4,01 TB)** in 84 135 Kacheln, laut Katalogabfrage [Messung]. Pro Jahr 294–362 GB [Messung].
- Für ein Fokusgebiet (z. B. Ukraine, E9) genügen wenige Kacheln pro Monat; Zahl der benötigten Kacheln und Gesamtgröße: nicht geprüft.
- Hinweis: Auch wenn ALEPH nur wenige Felder braucht, ist die Kachel-Datei ein Ganzes; die Download-Größe ist durch die Kachelgröße bestimmt (ob Teil-Lesen per S3 möglich ist: nicht geprüft). Der fertige Würfel ist dagegen klein: 1440 × 720 × 156 Monate × 4 Byte (float32) ergibt rund 0,65 GB pro Feld, unkomprimiert (eigene Rechnung).

## 16. Empfehlung

**Einbauen** (erster Layer), mit folgenden Bedingungen:
1. Alle benötigten Kacheln **vor dem 1. November 2026** laden und Dateinamen festhalten (Ende der Suomi-NPP-Auslieferung; ob das Archiv bleibt, ist nicht belegt).
2. Hauptfeld vorläufig `NearNadir_Composite_Snow_Free`, Vergleichsfeld `AllAngle_Composite_Snow_Free`; Entscheidung nach dem Vergleichstest (Abschnitt 9). Zusätzlich `_Num` und `_Quality` je Zelle mitführen.
3. Kein hartes Ausschließen von Quality 1; stattdessen Datenlage-Stufen aus `_Num`/Quality/Anzahl gültiger Pixel. Zellen mit zu wenigen Daten werden als „Datenlage unzureichend" markiert (ARCHITECTURE.md Abschnitt 6, Punkt 3).
4. Hohe Breiten (Sommer: kaum Nächte; Winter: Schnee) getrennt bewerten oder zurückhaltend melden.
5. Nullwerte (Schwelle 0,5 nW) und Fehlwerte (−999,9) strikt trennen; Division durch MAD = 0 abfangen.
6. In `META`: „Rohwerte anzeigen zulässig" (CC0 / ohne Einschränkung, laut LAADS), Quellenangabe wie oben, Bruchliste aus Abschnitt 10.

## 17. Zusammenfassung (einfache Sprache)

VNP46A3 ist ein frei nutzbares NASA-Nachtlicht-Produkt mit monatlichen Werten für die ganze Erde; die Rohwerte dürfen laut NASA ohne Einschränkung öffentlich gezeigt werden, eine Quellenangabe wird erbeten. Der Qualitätswert im Monatsprodukt zählt nur die Nächte: „gut" heißt mehr als 3 gültige Nächte, „schlecht" heißt höchstens 3; deshalb ist ein heller Sommer in hohen Breiten fast automatisch „schlecht". Diese Begründung für den Sommer ist eine plausible eigene Überlegung, keine NASA-Aussage. Für die Anomalieerkennung schlage ich das Feld NearNadir mit Snow_Free vor (gleichmäßiger Blickwinkel, kein Schnee), das aber erst gegen AllAngle getestet werden sollte; alle Werte unter 0,5 sind bereits auf 0 gesetzt. Offen sind vor allem: ob es Restbrüche durch die Alterung des Suomi-NPP-Sensors gibt, wie Schnee-freie Lücken im Winter gefüllt werden, warum 58 % der Probekachel Fehlwerte hat, und was nach dem 1. November 2026 mit dem Suomi-NPP-Archiv passiert.

## 18. Angaben, die nur aus einer Quelle bestätigt sind

- Quality-Bedeutungen 0/1/2/255: User Guide (Tabelle 12), inhaltlich gleichlautend im Weltbank-Paket. Das Weltbank-Paket übernimmt vermutlich denselben Text, ist also **keine unabhängige** Bestätigung.
- Rauschschwelle 0,5 nW und Boxplot-Regel (Mittelwert nach Entfernen von Ausreißern): nur User Guide (Abschnitt 2.3).
- Winkelwarnung und Schnee-Effekt: nur User Guide (die Winkelwirkung zusätzlich Wang et al. 2021, nur Zusammenfassung).
- Zenitwinkel-Schwellen (102°, 102–108° = schlecht): User Guide und LAADS-Produktseite (zwei Anbieterquellen, aber gleiche Herkunft).
- Ende der Suomi-NPP-Lieferung (1. November 2026) und die Störung im August 2026: Earthdata-Mitteilungen; das Datum steht zusätzlich in Suchergebnissen von NESDIS/NOAA (nicht direkt gelesen).
- Lizenz („ohne Einschränkung", CC0): LAADS-Seite, CMR und Earthdata-Zitierhinweis (drei Stellen, alle NASA).
- Alterungskorrektur des SNPP-Sensors: nur LAADS-Produktseite.
- SNPP-Auslieferung, Zitierform, Version-2-Änderungen: NASA-Seiten; die Version-2-Änderungen wurden an drei NASA-Seiten (LAADS, Earthdata-Katalog, VJ146A3-Seite) übereinstimmend gelesen.
- Alle Angaben aus dem User Guide stammen aus einer automatischen Zusammenfassung des PDF-Textes; Seiten- und Tabellennummern nicht im Original gegengeprüft.

## 19. Nicht geprüft (Liste)

- Vollständiger Text des ATBD und des Fachartikels Román et al. 2018 (PDF nicht lesbar).
- Ob Beobachtungen mit Zenitwinkel 102–108° in die Monatskomposite eingehen.
- Ausdrückliche Anbieterempfehlung, welche Qualitätswerte auszuschließen sind und welches Feld für Zeitreihen zu nutzen ist.
- Behandlung von Pixeln ohne schneefreie Beobachtung im Snow_Free-Komposit.
- Std-Wert bei sehr wenigen Beobachtungen.
- Restdrift des SNPP-DNB nach der Kalibrierkorrektur; Bahn-/Überflugzeitdrift; LED-Effekt.
- Ob VNP46A3 immer `DNB_Platform` = 0 enthält.
- Schicksal des Suomi-NPP-Archivs nach dem 1. November 2026.
- LAADS-Zitier- und Nutzungsrichtlinie (PDF); earthaccess-Dokumentation; Kontoanlage bei Earthdata.
- Grund für den Unterschied 58 MB (LAADS) vs. ca. 40 MB (Messung) je Datei.
