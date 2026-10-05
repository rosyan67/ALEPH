# Steckbrief: GPM IMERG Final Run, monatlich (GPM_3IMERGM, Version 07B)

Stand der Recherche: 2026-10-02 (Hauptsitzung). Ersetzt `docs/sources/gpm_imerg.md` (Scout, 2026-09-23); jener Steckbrief bleibt zur Nachvollziehbarkeit liegen, seine Angaben gelten nur, soweit sie hier bestätigt sind.

Kennzeichnung (wie in `docs/sources/vnp46a3.md`):
- **[Anbieter]** = Angabe von NASA (CMR-Katalog, GES DISC, GPM-Projekt, PPS), mit Adresse und Abrufdatum.
- **[Messung]** = eigene Messung in dieser Sitzung (Katalogabfrage, Probedatei).
- **[Eigene Überlegung]** = Schlussfolgerung, nicht vom Anbieter belegt.
- „nicht geprüft" = konnte nicht belegt werden.

**Wie gelesen wurde (wichtig für die Belastbarkeit):**
- CMR-Katalog: Rohtext (JSON) direkt mit `curl` abgefragt, nicht über ein zusammenfassendes Werkzeug.
- GPM-Webseiten (Release Notes, Datennachrichten): HTML direkt abgerufen, Text selbst gelesen.
- IMERG Technical Documentation (PDF, 97 Seiten, Stand 13. Juli 2023) und README.GPM (PDF, 20 Seiten): heruntergeladen, Text maschinell aus dem PDF gezogen (`pypdf`) und die zitierten Stellen selbst gelesen. Seitenzahlen beziehen sich auf das PDF. Das ist der Originaltext, keine Zusammenfassung durch ein Hilfsmodell; Tabellen können beim Herausziehen verrutschen, die zitierten Stellen wurden deshalb im Zusammenhang gelesen.
- Abrufdatum aller Quellen in diesem Steckbrief: **2026-10-02**.

---

## 1. Name und Anbieter

- **Name:** „GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07 (GPM_3IMERGM)", Kurzname `GPM_3IMERGM`, Version `07`, Katalog-ID `C2723754851-GES_DISC`. [Anbieter: https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=GPM_3IMERGM]
- **Aktueller Stand innerhalb V07:** „Version 07B is the current version of the IMERG data sets." Dateinamen enden auf `.V07B.HDF5`. [Anbieter: CMR-Abstract, wie oben; Dateinamen: Messung, Abschnitt 14]
- **Final Run:** Das Monatsprodukt gibt es nur im Final Run: „The identifier 3IMERGM denotes the monthly output, only computed by the Final Run of IMERG." [Anbieter: IMERG Technical Documentation, S. 20, https://arthurhou.pps.eosdis.nasa.gov/Documents/IMERG_TechnicalDocumentation_final.pdf]
- **Archiv/Verteiler:** NASA GES DISC (Goddard Earth Sciences Data and Information Services Center). **Erzeuger:** NASA/GSFC (Mesoscale Atmospheric Processes Laboratory) und Precipitation Processing System (PPS).
- **Autoren laut Katalog-Zitat:** Huffman, G.J.; Stocker, E.F.; Bolvin, D.T.; Nelkin, E.J.; Tan, J. Veröffentlicht 2023-07-12, Greenbelt, MD. [Anbieter: CMR `CollectionCitations`]
- **DOI:** 10.5067/GPM/IMERG/3B-MONTH/07 [Anbieter: CMR; gleichlautend Technical Documentation S. 13]
- **Offizielle Seiten:**
  - GES DISC Produktseite: https://disc.gsfc.nasa.gov/datacollection/GPM_3IMERGM_07.html (Seite ist eine JavaScript-Anwendung, Inhalt nicht direkt lesbar)
  - Technical Documentation: https://arthurhou.pps.eosdis.nasa.gov/Documents/IMERG_TechnicalDocumentation_final.pdf
  - Release Notes V07: https://gpm.nasa.gov/resources/documents/imerg-v07-release-notes
  - V08-Umstellung: https://gpm.nasa.gov/data/news/imerg-v08-transition-schedule und https://gpm.nasa.gov/data/news/update-imerg-v08-transition-schedule-aug-2026

## 2. Inhalt und Einheit

- **Hauptfeld `precipitation`:** „Merged satellite-gauge precipitation estimate (recommended for general use)", Einheit **mm/hr**. [Anbieter: Technical Documentation, Tabelle 2, S. 24]
- **Was die Zahl bedeutet:** „The precipitation value is an average rate over the calendar month." (S. 22) und „The monthly values are average rates over the month" (S. 61). Es ist also eine **mittlere Rate**, keine Monatssumme. [Anbieter: Technical Documentation]
- **Umrechnung in mm pro Monat** [Eigene Überlegung, folgt direkt aus der Definition]: Monatssumme (mm) = Rate (mm/h) × 24 × Zahl der Tage des Kalendermonats (28, 29, 30 oder 31; Schaltjahre beachten). Der alte Code rechnete mit 12 × 24 Stunden; das ist falsch.
- **Weitere Felder im Monatsprodukt** (Tabelle 2, S. 24–25):
  - `randomError` (mm/hr): Zufallsfehler des Hauptfelds. „computed for both the half-hourly (3IMERGHH) and monthly (3IMERGM) datasets. The units are mm/hr." (S. 44, Abschnitt „random error field")
  - `gaugeRelativeWeighting` (Prozent): Gewicht der Regenmesser gegenüber der Satellitenschätzung.
  - `probabilityLiquidPrecipitation` (Prozent): niederschlagsgewichtete Wahrscheinlichkeit flüssiger Phase.
  - `precipitationQualityIndex` („Equivalent gauges per 2.5° box"): Qualitätsmaß, siehe Abschnitt 8.
  - Die Feldnamen im PDF sind beim Umbruch zerteilt (z. B. „gaugeRelativeWeight / percent"); die genauen Namen werden an der Probedatei abgelesen (Abschnitt 14).
- **Rundung:** „V07 precipitation rates are rounded to … 0.001 mm / h for the monthly datasets." Größte zulässige Rate 200 mm/h. [Anbieter: S. 19]
- **Berechnung des Monatswerts:** Monatliche Satelliten-Regenmesser-Kombination (SG combination) aus der monatlichen Summe der halbstündlichen Satellitenschätzungen und der GPCC-Regenmesseranalyse (S. 52, „SG combination"). [Anbieter]

## 3. Räumliche Auflösung, Gitter und Abdeckung

- **Gitter:** 0,1° × 0,1°, 1800 × 3600 Punkte, WGS84. „It is size 1800×3600, with X (latitude) incrementing most rapidly South to North from the southern edge, and then Y (longitude) incrementing West to East from the Dateline … First point center (89.95°S,179.95°W) … Last point center (89.95°N,179.95°E)." [Anbieter: Technical Documentation, S. 22]
  - **Folge für ALEPH:** Die Breite läuft von **Süd nach Nord**, im ALEPH-Würfel aber von Nord nach Süd (Zeile 0 = 90° N). Die Achsenreihenfolge in der Datei wird an der Probedatei gemessen und im Code an den Koordinaten geprüft, nicht angenommen. [Eigene Überlegung]
- **Abdeckung:** „The spatial coverage of Version 07 IMERG precipitation estimates is the latitude band 90°N-S." Seit V07 werden Mikrowellen-Schätzungen auch über gefrorenen Flächen verwendet, „except for a handful of grid boxes (mostly at the poles), IMERG has complete global coverage". [Anbieter: S. 23]
- **Bis zu welchem Breitengrad gültig?** Es gibt **keine harte Grenze** in V07, aber eine abgestufte Verlässlichkeit:
  - Infrarot nur 60° N–S: „IR only covers 60°N-S" (S. 22).
  - Über gefrorenen Flächen, besonders in hohen Breiten, verminderte Güte: „users should be aware of the diminished performance of these estimates … applications that use and evaluate these estimates over frozen surfaces, especially at high latitudes, should indicate this caveat of reduced skill" (S. 23).
  - Oberhalb 89° N sollten alle Werte fehlen: „all gridbox values above 89°N should be ‚missing' for the precipitationUncal and Precipitation variables. This issue is corrected in V07 IMERG" (S. 67, Punkt 9).
  - **Gemessen in ALEPH (2026-10-05, alle 153 Monate, technische Prüfung):** Im 0,25°-Würfel fehlen Werte nur in den Zeilen jenseits ±89,5° (Zellmitten 89,625/89,875 N und S), je Monat 0,34–0,57 % der Zellen. Die Zeilen 89,125 und 89,375 N haben Werte. Das Zitat oben beschreibt also einen in V07 behobenen Fehler, keine Lücke ab 89° N. Dass auch am Südpol Werte fehlen, steht nicht im gelesenen Text. [Messung]
  - Folgerung für ALEPH [Eigene Überlegung]: Werte nördlich/südlich von 60° als „verminderte Güte" kennzeichnen (Datenlage-Merkmal), nicht löschen; ob 60° die richtige Linie ist, ist eine Annahme aus der IR-Grenze, keine Anbieterempfehlung.
- **Fehlwert:** „All products in IMERG use the standard missing value ‚-9999.9' or ‚-9999' for 4-byte floats or 2-byte integers, respectively. These values are carried in the metadata." [Anbieter: S. 74]

## 4. Zeitliche Auflösung und Zeitraum

- **Monatlich**, je Datei ein Kalendermonat (UTC). [Anbieter: S. 21–22]
- **Zeitraum laut Katalog: 1998-01-01 bis 2025-09-30**, `EndsAtPresentFlag: False`, `CollectionProgress: COMPLETE`. [Anbieter: CMR, abgerufen 2026-10-02]
- **Wichtig: V07 Final endet mit September 2025.** Wortlaut NASA (28. April 2026): „For the Final Run, the V07 record ends in September 2025 because the parent products feeding into the IMERG algorithm (CORRA and GPROF) are being upgraded to V08. … The IMERG V08 Final Run is planned for release in the summer of 2026 … it will be a retrospective processing of the full record, starting from January 1998". Aktualisierung (6. August 2026): „it seems more likely that IMERG V08 Final Run will be released in the fall of 2026". [Anbieter: https://gpm.nasa.gov/data/news/imerg-v08-transition-schedule ; https://gpm.nasa.gov/data/news/update-imerg-v08-transition-schedule-aug-2026]
  - **Folge für ALEPH:** Oktober–Dezember 2025 gibt es als V07-Final-Monatswert **nicht** und wird es nicht geben. Diese drei Monate werden im Manifest als „beim Anbieter nicht vorhanden" geführt. Sie liegen im Endtest-Zeitraum.
  - Die Early/Late Runs laufen weiter, aber im „hybrid"-Modus mit V08-Eingängen und möglichen Brüchen (gleiche Mitteilung). Sie sind ein anderes Produkt ohne monatliche Regenmesser-Anpassung und werden **nicht** eingemischt. [Eigene Überlegung]
- **Beginn und TRMM-Ära:** „The period of record for TRMM-based IMERG is June 2000 <January 1998> through May 2014. Thereafter IMERG has GPM-based calibration." (S. 22). V07 nutzt TRMM-Kalibrierung bis Mai 2014 (S. 19). Der CMR-Text nennt „June 2000 to the present" als Zeitraum, der Katalog aber 1998-01 als Beginn; die Erweiterung auf 1998 hat geringere Qualität (alter Steckbrief, Anbieter-Caveat-Dokument nicht im Volltext gelesen).
- **Latenz:** „about 3.5 months" (S. 22) bzw. „~4 months after the observation month" (CMR-Abstract). Gemessen: Der Monat 2025-09 wurde am 2026-02-01 erzeugt (ProductionDateTime). [Anbieter / Messung]
- **Version 07 einheitlich:** Der ganze Zeitraum wurde als V07B neu gerechnet, abgeschlossen am 8. Januar 2024 (Release Notes). Innerhalb 2013-01 bis 2025-09 also eine Version. Bruch innerhalb ALEPH: Kalibrierungswechsel TRMM → GPM nach Mai 2014. [Anbieter: https://gpm.nasa.gov/resources/documents/imerg-v07-release-notes]

## 5. Zugang

- **Konto:** NASA Earthdata Login (dasselbe wie für das Nachtlicht). Zugangsdaten nur in `.env` (`EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`), gelesen über `aleph/core/auth.py`.
- **Einmalige Freigabe nötig (gemessen 2026-10-02):** Anmeldung gelingt, der Abruf einer Datei liefert aber HTTP 403 mit `"error_description":"EULA Acceptance Failure"` und `"resolution_url":"https://urs.earthdata.nasa.gov/approve_app?client_id=e2WVk8Pw6weeLUKZYOxvTQ"`. [Messung]
  - Dieselbe Adresse nennt GES DISC selbst: „Once registered, you can click here to authorize 'NASA GESDISC DATA ARCHIVE' application." [Anbieter: Verzeichnisseite https://discnrt1.gesdisc.eosdis.nasa.gov/data/]
  - **Was der Nutzer tut:** Adresse oben im Browser öffnen, bei Earthdata anmelden, die Anwendung „NASA GESDISC DATA ARCHIVE" freigeben („Authorize"/„Approve").
  - **Erledigt 2026-10-05:** Freigabe erteilt, danach liefen alle 153 Abrufe ohne 403. [Messung]
- **Zugriffsweg:** HTTPS-Download über `earthaccess` (ARCHITECTURE.md Abschnitt 5); Downloadadresse aus dem Katalog, Muster `https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGM.07/<Jahr>/<Datei>`. [Anbieter: CMR-Granulat, `RelatedUrls`]
- **Hinweis Serverumzug:** Die alte GES-DISC-Verzeichnisseite meldet: „Access to this server (and all other GES DISC data servers) will end no earlier than September 30th 2026. Users will need to transition to Earthdata". Die Katalog-Adressen zeigen bereits auf `data.gesdisc.earthdata.nasa.gov`. Ob das der neue Weg ist, ist nicht geprüft; ALEPH nimmt immer die Adresse aus dem Katalog, nie eine fest eingetragene. [Anbieter / Eigene Überlegung]

## 6. Lizenz und Zitierweise

- **Katalog:** `AccessConstraints: None`; `UseConstraints`: Verweis auf die EOSDIS Data Use and Citation Guidance (https://earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance) und die GES-DISC-Richtlinien (https://disc.gsfc.nasa.gov/data-guidelines). [Anbieter: CMR]
- **Datenpolitik des Erzeugers** (Katalogfeld `Quality`, wörtlich): „The data access policy is ‚freely available' with three common-sense caveats: 1. The data set source should be acknowledged when the data are used, in the form: ‚The IMERG data were provided by the NASA/Goddard Space Flight Center's Mesoscale Atmospheric Processes Laboratory and PPS, which develop and compute IMERG as a contribution to GPM, and archived at the NASA GES DISC.' 2. New users are urged to obtain their own current, clean copy from an official archive … 3. Errors and difficulties … should be reported to the dataset creators." [Anbieter: CMR]
- **Zitierform für ALEPH** (aus den Katalogangaben zusammengesetzt): Huffman, G.J., E.F. Stocker, D.T. Bolvin, E.J. Nelkin, J. Tan (2023): GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07, Greenbelt, MD, Goddard Earth Sciences Data and Information Services Center (GES DISC), abgerufen am [Datum], doi:10.5067/GPM/IMERG/3B-MONTH/07.
- **Für `META`:** Rohwerte dürfen gezeigt werden („freely available"); Quellenangabe mit dem Satz oben ist Pflicht in ALEPH. Die CC-BY-Angabe der AWS-Seite aus dem alten Steckbrief stammt von einem Dritten und ist nicht maßgeblich.

## 7. Dateiformat

- HDF5, eine Datei je Monat für die ganze Erde (kein Kachelsystem). Dateiname: `3B-MO.MS.MRG.3IMERG.YYYYMM01-S000000-E235959.MM.V07B.HDF5`. [Anbieter: S. 21; Messung: Katalog]
- Felder in der Gruppe `Grid` (Release Notes/Technical Documentation; Feldnamen „not changed in V07" für die Monatsdatei, S. 18). Genaue Struktur: Abschnitt 14.

## 8. Qualitäts- und Unsicherheitsfelder

- **`precipitationQualityIndex` (QIm):** „equivalent number of gauges" je 2,5°×2,5°-Fläche, abgeleitet aus dem Zufallsfehler; „this formulation only addresses random error, not bias." Ampel laut Anbieter: 0–2 „red", 2–10 „yellow", 10+ „green". Über gefrorenen Flächen nicht angepasst, weil die Fehlerkoeffizienten auf Regen abgestimmt sind. [Anbieter: S. 56]
- **`randomError`** (mm/h): Zufallsfehler des Monatswerts nach Huffman (1997). [Anbieter: S. 44]
- **`gaugeRelativeWeighting`** (%): Anteil der Regenmesser am Ergebnis; über Meer und regenmesserarmen Gebieten klein. [Anbieter: Tabelle 2; Deutung: Eigene Überlegung]
- **Für ALEPH** (nach Auflagen statistik-pruefer, 2026-10-02):
  - `random_error_mm_monat`: Flächenmittel der Pixelfehler, in mm/Monat; exakt bei voll korrelierten Pixelfehlern, sonst eine Obergrenze.
  - `quality_index_min`: **Minimum** der überlappenden 0,1°-Pixel (kein Flächenmittel, weil der Index auf der 2,5°-Skala definiert und nicht linear ist); Ampel des Anbieters gilt weiter.
  - `probability_liquid`: **niederschlagsgewichtet** gemittelt (Gewicht = Fläche × Niederschlag), wie im Anbieterprodukt; in einer trockenen Zelle NaN (nicht definiert).
  - `gauge_relative_weighting`: Flächenmittel.
  - Mindestschwelle für die Nutzung eines Zellwerts: gültige Fläche ≥ 50 % (`MINDEST_GUELTIG_ANTEIL`, festgelegt vor dem Ansehen echter Daten); der Würfel behält auch Teilmittel.
  - Kalibrierungsbruch TRMM → GPM (bis 2014-05 TRMM) als Variable `kalibrierung_trmm`.

## 9. Bekannte Schwächen

- Schneefall in V07 unterschätzt, Gebirge weniger zuverlässig (GPM-FAQ, alter Steckbrief; nicht erneut im Original gelesen).
- Verminderte Güte über gefrorenen Flächen und in hohen Breiten (S. 23, wörtlich oben).
- Regenmesser-Korrektur: „The Legates-Wilmott scheme for undercatch in the GPCC gauges is too large at high latitudes, so a climatological Fuchs adjustment was implemented in V07 over Eurasia north of 45°N" (S. 18). Bedeutet: In hohen Breiten hängt der Wert spürbar vom gewählten Korrekturverfahren ab.
- Kalibrierungswechsel TRMM → GPM nach Mai 2014 (S. 19, S. 22): möglicher Bruch innerhalb 2013–2025.
- Liste bekannter Fehler und Anomalien: Technical Documentation Abschnitt „known errors and anomalies" (S. 67 ff.), nicht vollständig ausgewertet.
- Datensatz endet mit 2025-09 (Abschnitt 4). Ein künftiger V08-Datensatz ersetzt den ganzen Zeitraum; V07 und V08 dürfen nicht gemischt werden.

## 10. Rolle in ALEPH

Erkennungs-Layer „Niederschlag" (ARCHITECTURE.md Abschnitt 5: Dürre, Überschwemmung), Ursache-Layer in den Theorien zu Dürre (theories/duerreindizes-spi-spei.yaml) und Klima–Konflikt.

## 11. Datenmenge

- **153 Dateien** für 2013-01 bis 2025-09 im Katalog, keine Lücke, keine doppelten Monate; fehlend 2025-10, 2025-11, 2025-12. [Messung: CMR-Granulatsuche, 2026-10-02, Trefferzahl `CMR-Hits: 153`]
- **Zusammen 2 734 MB (≈ 2,7 GB)**, je Datei 16,70–18,67 MB. Der Katalog gibt die Größe nur in MB an (Feld `Size`, Einheit `MB`), ohne Prüfsumme; die MB-Werte ergeben mal 1 048 576 eine ganze Bytezahl (z. B. 2025-09: 19 172 907 Byte), sind also exakt. [Messung]
- Der Katalog nennt als Durchschnitt 30 MB je Datei (`AverageFileSize`), die Technical Documentation 20 MB (S. 60). Beides sind Richtwerte; maßgeblich ist die Granulatangabe. [Anbieter]
- **Fertiger Würfel:** 1440 × 720 × 156 × 4 Byte ≈ 0,65 GB je float32-Feld unkomprimiert. [Eigene Überlegung]

## 12. Empfehlung

**Einbauen**, mit diesen Bedingungen:
1. Nur V07B Final Run laden; Version als Konstante im Code. Kommt V08 heraus, den **ganzen** Zeitraum neu laden, nie mischen.
2. 2025-10 bis 2025-12 als „beim Anbieter nicht vorhanden" führen, nicht als „nicht geladen" und nie als 0.
3. Flächengewichtete Umrechnung 0,1° → 0,25° (Faktor 2,5, keine ganze Zahl).
4. Einheit mm/h × Stunden des Kalendermonats → mm/Monat.
5. Fehlwert −9999,9 vor jeder Mittelung entfernen; Niederschlag 0 bleibt 0, fehlend bleibt NaN.
6. Qualitätsfelder (`precipitationQualityIndex`, `randomError`, `gaugeRelativeWeighting`) mitspeichern; hohe Breiten (> 60°) als verminderte Güte kennzeichnen.
7. Vor der Präsentation: GES-DISC-Freigabe ist einmalig nötig (Abschnitt 5).

## 13. Zusammenfassung (einfache Sprache)

IMERG ist ein kostenloses NASA-Produkt mit dem Niederschlag jedes Monats für die ganze Erde, auf einem 10-km-Raster. Die Zahl in der Datei ist ein Durchschnitt in Millimetern pro Stunde; für Millimeter im Monat muss man mit den Stunden des Monats malnehmen. Die geprüfte Version (V07) endet mit September 2025, weil NASA gerade auf Version 08 umstellt; die letzten drei Monate von 2025 gibt es deshalb nicht. Für 2013 bis September 2025 sind es 153 Dateien mit zusammen etwa 2,7 GB. Damit das Konto die Dateien laden darf, muss einmal die Anwendung „NASA GESDISC DATA ARCHIVE" im Earthdata-Profil freigegeben werden.

## 14. Eigene Messungen an der Probedatei

(wird nach dem Laden der Probedatei ergänzt)

## 15. Nicht geprüft (Liste)

- Inhalt der IMERG-V07-Release-Notes als PDF und des Dokuments „Caveats for IMERG extension into TRMM era" (Volltext nicht gelesen).
- Ob V08 vor dem Hackathon (14.–15.11.2026) erscheint und wie stark es von V07 abweicht.
- Ob `data.gesdisc.earthdata.nasa.gov` der Weg nach der angekündigten Abschaltung der alten GES-DISC-Server ist.
- Ob GPCC-Regenmesserdaten eigene Weitergabebedingungen haben (fließen nur zusammengefasst ein).
- Ob 60° die sinnvolle Grenze für „verminderte Güte" ist (Annahme aus der IR-Grenze).
- Schnee-Unterschätzung: nicht erneut im Originaltext gelesen.
