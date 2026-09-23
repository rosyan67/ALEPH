# Steckbrief: MODIS/Terra MOD13C2 (Vegetationsindizes, monatlich, global, CMG)

Stand der Recherche: 2026-09-23. Erstellt vom Agenten „datenquellen-scout".

Kennzeichnung in diesem Dokument (wie in `docs/sources/vnp46a3.md`):
- **[Anbieter]** = Angabe stammt von NASA/LP DAAC/LAADS, mit Link.
- **[Dritt]** = Angabe stammt von einer Drittquelle, nicht vom Anbieter.
- **[Messung]** = eigene Abfrage/Berechnung des Scouts (hier: CMR-Abfragen über das WebFetch-Werkzeug), keine Herstellerangabe.
- **[Eigene Überlegung]** = Schlussfolgerung des Scouts, nicht vom Anbieter belegt.
- „nicht geprüft" = konnte nicht belegt werden.

**Hinweis zur Methode (wichtig):** Anders als beim VNP46A3-Steckbrief hatte der Scout in dieser Sitzung **keinen Werkzeugzugriff auf Bash, keine Datei-Downloads und keinen h5py/GDAL-Zugriff**. Alle „[Messung]"-Angaben in diesem Dokument stammen aus **CMR-Suchabfragen über das WebFetch-Werkzeug**, dessen Antworten von einem Hilfsmodell zusammengefasst wurden, nicht aus einer selbst gezählten, vollständigen Liste. Wo das die Belastbarkeit einschränkt, steht das ausdrücklich dabei. Es wurden keine Rohdaten heruntergeladen (Auftrag).

---

## 1. Name und Anbieter

- **Name:** MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG, Version 6.1, Kurzname **MOD13C2**. CMG = Climate Modeling Grid. [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061]
- **Anbieter:** NASA Land Processes Distributed Active Archive Center (LP DAAC), Datenerzeugung durch das MODIS-Landteam; als verantwortlicher Wissenschaftler wird Kamel Didan genannt. [Anbieter: Zitat unten, https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061]
- **DOI Version 6.1:** 10.5067/MODIS/MOD13C2.061. Die Vorgängerversion 6 (DOI 10.5067/MODIS/MOD13C2.006) wurde am 31. Juli 2023 eingestellt. [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13C2 und https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-006]
- **Offizielle Seiten:**
  - Earthdata-Katalog (V061): https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061
  - LAADS-Produktseite: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13C2
  - LAADS-Dateispezifikation (Collection 6.1): https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD13C2
  - LP DAAC-Produktseite (leitet auf den Earthdata-Katalog um, geprüft am 2026-09-23): https://lpdaac.usgs.gov/products/mod13c2v061/
  - MODIS-VI-Nutzerhandbuch (Collection 6.1): https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf (Inhalt nicht im Volltext gelesen, nur per Suchergebnis-Auszug: nicht vollständig geprüft)
- Es gibt eine Schwesterquelle **MYD13C2** (baugleich, Sensor Aqua statt Terra), in diesem Steckbrief nicht behandelt. [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MYD13C2]

## 2. Inhalt

- **NDVI** (Normalized Difference Vegetation Index) und **EVI** (Enhanced Vegetation Index), je ein Wert pro Gitterzelle und Monat, gebildet aus atmosphärenkorrigierten, für Wasser, Wolken, starke Aerosole und Wolkenschatten maskierten bidirektionalen Oberflächenreflexionen. [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13C2]
- **Einheit:** dimensionslos (Index), gespeichert als ganzzahliger Wert (INT16) mit Skalierungsfaktor 10000 (d. h. gespeicherter Wert ÷ 10000 = eigentlicher Index). NDVI und EVI: gültiger Bereich −2000 bis 10000 (entspricht Index −0,2 bis 1,0), Fehlwert −3000. [Anbieter/[Dritt bestätigt]: LAADS-Dateispezifikation https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD13C2, sinngemäß bestätigt durch Google-Earth-Engine-Katalogeintrag für das verwandte 16-Tage-Produkt MOD13Q1 https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1]
- **Kompositbildung:** MOD13C2 fasst das feiner aufgelöste 16-tägige 1-km-Produkt MOD13A2 zu einem wolkenfreien Monatswert je 0,05°-Zelle zusammen (gewichteter zeitlicher Mittelwert über alle MOD13A2-Kacheln, die den Monat überlappen). [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13C2]
- **Weitere Datenfelder (Auszug, Collection 6.1):** VI-Qualität (Bitfeld), Rot-/Nahinfrarot-/Blau-/Mittelinfrarot-Reflexion, Blickwinkel-Geometrie, Zahl der genutzten 1-km-Pixel je Zelle, „Pixel Reliability" (Rang 0–4, 0 = ideal, 4 = aus historischer Reihe geschätzt). [Anbieter: LAADS-Dateispezifikation, s. o., wörtlich per WebFetch-Zusammenfassung ausgelesen, nicht Zeile für Zeile im Originaldokument gegengeprüft]

## 3. Räumliche Auflösung und Abdeckung

- **0,05° (ca. 5,6 km am Äquator)**, Climate Modeling Grid: 3 600 Zeilen × 7 200 Spalten, global, lückenlos (kein Kachelraster wie bei VNP46A3). [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061 und https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13C2]
- **Eine einzige Datei pro Monat für die ganze Erde** (keine Kachelung nach Sinusoidal- oder 10°-Raster). Bestätigt über eine CMR-Stichprobe: Für Januar 2013 liefert die Granular-Suche genau einen Treffer (`MOD13C2.A2013001.061.2021226150754`, 90,1 MB). [Messung: CMR-Abfrage per WebFetch, https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MOD13C2&version=061]
- **Vergleich mit dem ALEPH-Zielraster:** ALEPH nutzt 0,25° global, 1440 × 720 Zellen (ARCHITECTURE.md Abschnitt 4). Eine ALEPH-Zelle entspricht 5 × 5 = 25 MOD13C2-Zellen (0,25° ÷ 0,05° = 5). Aus je 25 nativen Pixeln muss eine ALEPH-Zelle gebildet werden (Mittelwert und Anzahl gültiger Pixel), analog zur bestehenden Vergröberung bei VNP46A3, aber mit einem viel kleineren Verhältnis (25 statt 3 600 Pixel je Zelle). [Eigene Überlegung, Rechnung: 0,25/0,05 = 5]

## 4. Zeitliche Auflösung und Zeitraum

- **Monatlich.** Zeitraum laut Earthdata-Katalog: **1. Februar 2000 bis laufend** („Present, ongoing"). [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061]
- Version 6.1 wird seit 16. Februar 2021 ausgeliefert (Veröffentlichungsdatum der Version laut Katalogseite); ältere Monate wurden rückwirkend in Version 6.1 neu erzeugt. [Anbieter, WebFetch-Zusammenfassung der Katalogseite, Datum nicht im Original-HTML gegengeprüft: teilweise nicht geprüft]
- Der ALEPH-Untersuchungszeitraum 2013–2025 (Entscheidung E3) liegt vollständig innerhalb der Produktlaufzeit; zusätzlich stünden 2000–2012 als Vorlauf zur Verfügung, sofern gebraucht. [Eigene Überlegung, aus der Zeitangabe oben]
- **Verzögerung bis zur Veröffentlichung:** nicht geprüft (keine Anbieterangabe gefunden, die eine feste Latenz in Tagen/Wochen nennt).

## 5. Zugang

- **Frei, mit kostenlosem NASA-Earthdata-Konto** – derselbe Zugangsweg wie bei VNP46A3: Anmeldung über https://urs.earthdata.nasa.gov, Datenhaltung bei LP DAAC (statt LAADS DAAC bei VNP46A3, aber gleiches Earthdata-Ökosystem). [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061, Data Center „LP DAAC"]
- **Zugriffsbeschränkung:** In der CMR-Zusammenfassung als „None" ausgewiesen (frei zugänglich, keine gesonderte Freigabe nötig). [Anbieter, per WebFetch aus CMR-Metadaten zusammengefasst: nicht am Originaldokument gegengeprüft]
- **Werkzeuge:** Earthdata Search, LP DAAC-Datenarchiv, earthaccess/CMR-Suche (Kurzname `MOD13C2`, Version `061`). [Anbieter: https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13C2, eigene CMR-Abfrage bestätigt den Kurznamen]
- **Variablennamen in `.env`** (nur Namen, keine Werte, identisch zu VNP46A3, da gleiches Earthdata-Konto genutzt wird): `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`. Kein separates Token für dieses Produkt nötig, sofern `earthaccess` bereits eingerichtet ist. [Eigene Überlegung, gestützt auf ARCHITECTURE.md Abschnitt 5 „Für NASA-Downloads wird die Bibliothek earthaccess genutzt" und den bereits bestehenden VNP46A3-Zugang]
- Ein eigenes Antragsverfahren (über die reine Kontoerstellung hinaus) wurde nicht gefunden: nicht geprüft, aber es gibt keinen Hinweis darauf, dass eines nötig wäre (Zugriffsbeschränkung „None").

## 6. Lizenz und Nutzungsbedingungen

- Earthdata-Katalogseite: „openly shared, without restriction" gemäß EOSDIS Data Use and Citation Guidance. [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061]
- LP DAAC-Datenrichtlinie: „All LP DAAC current data and products acquired through the LP DAAC have no restrictions on reuse, sale, or redistribution." Zitierung wird erbeten, nicht vorgeschrieben. [Anbieter: https://lpdaac.usgs.gov/data/data-citation-and-policies/, per WebSearch-Auszug zusammengefasst – Originaltext nicht selbst geöffnet und Zeile für Zeile gelesen: **teilweise nicht geprüft**, sollte vor einer Veröffentlichung am Original nachgeschlagen werden]
- Wie bei VNP46A3 gilt der NASA-Grundsatz: Daten NASA-geführter Missionen ohne eigene Lizenzkennzeichnung gelten als CC0. [Anbieter: https://earthdata.nasa.gov/learn/use-data/data-citations-acknowledgements, bereits im VNP46A3-Steckbrief geprüft, hier sinngemäß übertragen – **nicht erneut einzeln für MOD13C2 bestätigt**]
- **Folgerung für ALEPH [Eigene Überlegung]:** Nicht-kommerzielle Nutzung ist erlaubt. Ein Verbot der öffentlichen Anzeige von Rohwerten wurde nirgends gefunden; „no restrictions on reuse, sale, or redistribution" spricht eher dafür, dass auch die Kartenanzeige von Rohwerten zulässig ist. Für `META`: **Anzeige von Rohwerten (NDVI-Karte) zulässig**, wie bei VNP46A3 – aber diese Aussage stützt sich auf eine per Suchmaschine zusammengefasste Passage der LP-DAAC-Seite, nicht auf den selbst gelesenen Originaltext. **Vor der endgültigen Freigabe für die öffentliche Karte sollte https://lpdaac.usgs.gov/data/data-citation-and-policies/ einmal im Original geöffnet werden.**
- **Quellenangabe:** erbeten, nicht Pflicht (wie bei VNP46A3). Zitierform laut Earthdata-Katalog:
  Didan, K. (2021). *MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG* [Dataset]. NASA Land Processes Distributed Active Archive Center. https://doi.org/10.5067/MODIS/MOD13C2.061
  [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061]. Zugriffsdatum sollte mit angegeben werden.

## 7. Python-Zugriff und Dateiformat

- **Format: HDF-EOS2**, also auf **HDF4** basierend – **anders als VNP46A3**, das HDF5 (HDF-EOS5) nutzt. [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13c2-061, per WebFetch ausgelesen; zusätzlich unabhängig bestätigt durch eine Beispieldatei-Auswertung eines Drittanbieters, [Dritt: https://hdfeos.org/zoo/LPDAAC/MOD13C2.A2007001.006.2015161222701.hdf.py]]
- **Bibliothek:** `earthaccess` für Suche/Download (ARCHITECTURE.md Abschnitt 5, gleiche Ladelogik wie bei VNP46A3). Zum **Lesen** der HDF4-Datei wird jedoch ein anderes Werkzeug als bei VNP46A3 gebraucht: `h5py` funktioniert nicht (kein HDF5). Genutzt werden üblicherweise GDAL, `rioxarray` oder `pyhdf`, die auf GDAL aufbauen. [Dritt: https://earthdatascience.org/courses/use-data-open-source-python/hierarchical-data-formats-hdf/open-MODIS-hdf4-files-python/, Aussage per WebSearch-Auszug übernommen, nicht selbst getestet: nicht geprüft]
- **Konsequenz für ALEPH [Eigene Überlegung]:** Die gemeinsame Ladelogik (`aleph/core/io.py`) kann für Download und Ablage gleich bleiben (earthaccess), aber das layer-spezifische Einlesen (`aleph/layers/mod13c2.py`) braucht einen anderen Dateileser als der Nachtlicht-Layer. Das ist nach ARCHITECTURE.md Abschnitt 5 zulässig („Datenquellen-spezifischer Code steckt nur im jeweiligen Layer-Modul"), sollte aber im Code-Kommentar begründet werden.
- Ob `earthaccess` HDF4-Dateien genauso unterstützt wie HDF5 (z. B. `earthaccess.open()` mit `xarray`), wurde nicht selbst getestet: nicht geprüft.

## 8. Bekannte Schwächen

- **Sensorwechsel/Nachfolgeprodukt bestätigt:** Es gibt ein VIIRS-Nachfolgeprodukt, **VNP13C2** (VIIRS/NPP Vegetation Indices Monthly, 0,05° CMG), „designed after the MODIS Terra and Aqua Vegetation Indices product suite to promote continuity". Verfügbar seit 1. Januar 2012, DOI 10.5067/VIIRS/VNP13C2.002, ebenfalls bei LP DAAC. Es gibt außerdem Fortsetzungsprodukte für NOAA-20 (`VJ113C2`) und NOAA-21 (`VJ213C2`). [Anbieter: https://www.earthdata.nasa.gov/data/catalog/lpcloud-vnp13c2-002, https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj113c2-002, https://www.earthdata.nasa.gov/data/catalog/lpcloud-vj213c2-002]
- **Wichtig für den Zeitplan:** Dieselbe NASA-Mitteilung wie bei VNP46A3 gilt auch hier: Die Auslieferung von Suomi-NPP-Produkten (also auch VNP13C2, falls später als Ergänzung genutzt) **endet am 1. November 2026**. [Anbieter, laut WebFetch-Auszug der VNP13C2-Katalogseite, dieselbe Mitteilung wie im VNP46A3-Steckbrief bereits direkt gelesen: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026]. MOD13C2 selbst (Terra-Sensor) ist davon **nicht** betroffen, da Terra nicht Suomi NPP ist.
- **Terra-Missionsende (wichtig für Aktualität, nicht für den historischen Zeitraum 2013–2025):** Terra treibt seit einer letzten Bahnkorrektur (27. Februar 2020) langsam aus seiner Sonnensynchron-Bahn; laut NASA-Fachartikel verließ Terra im Herbst 2022 die A-Train-Konstellation und wurde auf eine niedrigere Bahn gebracht. [Anbieter (per WebSearch-Auszug zusammengefasst): https://www.earthdata.nasa.gov/news/feature-articles/viirs-instruments-become-more-essential-terra-aqua-drift-traditional-orbits]. Ein neuerer Bericht nennt als aktuell geplantes Ende der wissenschaftlichen Terra-Mission **Februar 2027** wegen Treibstoff- und Energieknappheit; eine mögliche Stilllegung der EOS-Flaggschiffe (Terra, Aqua, Aura) bereits Ende 2026 wird ebenfalls genannt. [Anbieter/Presse, per WebSearch-Auszug: https://science.nasa.gov/science-research/earth-science/terra-the-end-of-an-era, Originaltext nicht selbst geöffnet: **nicht im Volltext geprüft**]. Für den Untersuchungszeitraum 2013–2025 ist das ohne Belang (Daten bereits vorhanden); für laufende Aktualisierungen nach 2026 ist Vorsicht geboten, ähnlich wie beim VNP46A3-Termin.
- **Bahndrift-Effekt auf die Datenqualität:** Eine frühere Überflugzeit bedeutet niedrigeren Sonnenstand und mehr Schattenwurf; die Fachquelle nennt außerdem mögliche Lücken in der räumlichen Abtastung durch die abgesenkte Bahnhöhe, aber „little to no impact on instrument data collection or quality" insgesamt. [Anbieter, per WebSearch-Auszug: dieselbe Quelle wie oben]. Wie stark das NDVI/EVI in MOD13C2 konkret betrifft: nicht geprüft.
- **Bekannter Datenfehler, dokumentiert und korrigiert:** Eine fehlerhafte Darstellung der Aerosolmengen in den Collection-6-Oberflächenreflexionsprodukten (MOD09) hat laut Suchergebnis-Auszug die MOD13-Vegetationsindex-Produkte beeinflusst, besonders über hellen ariden Flächen; die Korrektur erfolgte in der Collection-6.1-Neuprozessierung (also in der hier verwendeten Version). [Anbieter (LDOPE Known-Issue-Seite, nur per WebSearch-Auszug gelesen, nicht selbst geöffnet): https://landweb.modaps.eosdis.nasa.gov/knownissue?sensor=MODIS&sat=TerraAqua&as=62 – **nicht im Original geprüft**]
- **Wolken- und Aerosolmaskierung:** NDVI/EVI werden aus wolken- und aerosolmaskierten Reflexionen gebildet; bewölkte Zellen ohne verwertbare 16-Tage-Beobachtung im Monat können daher als Fehlwert oder mit „Pixel Reliability" 3/4 (aus historischer Reihe geschätzt bzw. unbrauchbar) markiert sein. [Anbieter: LAADS-Dateispezifikation, Feld „Pixel Reliability", s. Abschnitt 2; genaue Bedeutung der Rangstufen 1–4 nicht im Volltext des User Guide gegengeprüft: teilweise nicht geprüft]
- **Räumliche Vergröberung ist bereits eine Zusammenfassung:** MOD13C2 ist selbst schon aus dem 1-km-Produkt MOD13A2 aggregiert (gewichteter Mittelwert); feinräumige Vorgänge (z. B. einzelne Rodungsflächen) sind auf 0,05° und erst recht auf ALEPHs 0,25° nicht mehr einzeln erkennbar, nur als flächenhafter Rückgang. [Eigene Überlegung, aus der Kompositbeschreibung Abschnitt 2]

## 9. Rolle in ALEPH

Zweiter geplanter **Erkennungs-Layer** „Vegetation" gemäß ARCHITECTURE.md Abschnitt 5 (Tabelle „Kandidaten für die ersten Layer") und Abschnitt 13 (Woche 2: „Layer Vegetation und Brände"). Gedachte Anwendung laut Architektur: Dürre, Abholzung, Landwirtschaft – u. a. als Baustein der Anomalie-Regeln „Anomalie: Dürre" (Niederschlagsdefizit + Vegetationsrückgang über mehrere Monate) und „Anomalie: Abholzung" (dauerhafter Vegetationsverlust, oft nach Brand-Detektionen), siehe ARCHITECTURE.md Abschnitt 7. Zielraster 0,25° global (1440 × 720), monatlich, Untersuchungszeitraum 2013–2025 (Entscheidung E3). [Eigene Überlegung, unmittelbar aus ARCHITECTURE.md abgeleitet]

## 10. Datenmenge (Frage 1 des Auftrags)

**Rasterprüfung:** Die Herstellerangabe „0,05° CMG" ist bestätigt (Abschnitt 3). Das ist **fünfmal feiner** als ALEPHs Zielraster von 0,25° (nicht 60-mal wie bei VNP46A3s 15-Bogensekunden-Raster). [Eigene Überlegung/Messung, Rechnung s. Abschnitt 3]

**Downloadmenge 2013–2025, global – Schätzung:**
- Bestätigtes Muster: **eine Datei pro Monat**, global, keine Kachelung. [Messung: CMR-Stichprobe Januar 2013, ein Treffer]
- Beobachtete Dateigrößen in einer Stichprobe von Granulen aus 2013/2014: zwischen ca. 86,7 MB und 102,6 MB, die meisten um 90–101 MB. [Messung: CMR-Abfrage per WebFetch über einen Zeitausschnitt Jan 2013–Apr 2014; die WebFetch-Zusammenfassung nannte nur 20 von angefragten 200 Einträgen – **die Stichprobe istklein und nicht selbst vollständig ausgezählt**, daher als Anhaltspunkt, nicht als exakte Messung zu verstehen]
- Für 2013–2025 (13 Jahre × 12 Monate) ergäben sich bei durchgehender Monatsabdeckung **156 Dateien**. Mit einer mittleren Dateigröße von rund 90–95 MB ergibt das eine **geschätzte Gesamtgröße von rund 14–15 GB** für den gesamten globalen Datensatz über den ALEPH-Untersuchungszeitraum. [Eigene Überlegung/Rechnung: 156 × 90 MB ≈ 14,0 GB, 156 × 95 MB ≈ 14,8 GB]
- **Das ist rund 270- bis 290-mal kleiner** als die für VNP46A3 gemessene Menge von 4 108 GB im selben Zeitraum (dort: 84 135 gekachelte Dateien à ca. 40 MB). Grund: MOD13C2 liegt nicht gekachelt vor und hat eine gröbere native Auflösung (0,05° statt 15 Bogensekunden ≈ 0,0042°). [Eigene Überlegung, Vergleich mit `docs/sources/vnp46a3.md` Abschnitt 15]
- **Einschränkung dieser Schätzung:** Die tatsächliche Dateizahl (Lücken? Zwei Dateien in einzelnen Monaten durch Neuprozessierung?) wurde **nicht durch eine vollständige, selbst ausgezählte Liste aller 156 Monate bestätigt**, sondern aus dem beobachteten Muster (1 Datei/Monat) hochgerechnet. Vor einem echten Download sollte die CMR-Trefferzahl für den vollen Zeitraum einmal exakt gezählt werden (z. B. über `earthaccess.search_data(short_name="MOD13C2", version="061", temporal=("2013-01-01","2025-12-31"))`, `len(...)`), was in dieser Sitzung nicht ausgeführt wurde (kein Download/Bash erlaubt).
- **Fertiger ALEPH-Würfel (Vergleichsrechnung):** 1440 × 720 Zellen × 156 Monate × 4 Byte (float32) ≈ 0,65 GB pro Feld, unkomprimiert – exakt wie beim Nachtlicht-Layer, da die Würfelgröße unabhängig von der Rohdatenmenge ist. [Eigene Überlegung, gleiche Rechnung wie in `docs/sources/vnp46a3.md` Abschnitt 15]
- **Für ein Fokusgebiet:** Da MOD13C2 nicht gekachelt ist, muss für jedes Fokusgebiet trotzdem die volle globale Monatsdatei geladen werden (90–100 MB), auch wenn nur ein Ausschnitt gebraucht wird – anders als bei VNP46A3, wo pro Fokusgebiet nur einzelne Kacheln nötig sind. Das ist bei der ohnehin geringen Gesamtgröße unkritisch. [Eigene Überlegung]

## 11. Zugangsbedingungen – Zusammenfassung (Frage 2 des Auftrags)

Ja, der Zugang läuft **wie bei VNP46A3 über NASA Earthdata**: kostenloses Konto unter urs.earthdata.nasa.gov, Zugriff über `earthaccess`/CMR, keine weitere Freischaltung oder gesondertes Antragsverfahren gefunden (Zugriffsbeschränkung „None"). Es wird kein zusätzliches, produktspezifisches Token benötigt; dieselben `.env`-Variablennamen (`EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`) genügen. [Zusammenfassung aus Abschnitt 5]

## 12. Lizenz – Zusammenfassung (Frage 3 des Auftrags)

Nicht-kommerzielle **und** kommerzielle Nutzung sind laut LP-DAAC-Aussage ohne Einschränkung erlaubt („no restrictions on reuse, sale, or redistribution"); Zitierung ist **erbeten**, nicht **verpflichtend**. Diese Aussage stammt in dieser Sitzung nur aus einer Suchergebnis-Zusammenfassung der LP-DAAC-Richtlinienseite, nicht aus dem selbst gelesenen Original – Empfehlung: vor Veröffentlichung einmal gegenlesen. [Zusammenfassung aus Abschnitt 6]

## 13. Öffentliche Anzeige der Rohdaten (Frage 4 des Auftrags, zentral für ARCHITECTURE.md Abschnitt 5)

Nach den gefundenen Belegen (CC0-Grundsatz für NASA-Missionen, „no restrictions on reuse, sale, or redistribution" bei LP DAAC, „openly shared, without restriction" im Earthdata-Katalog) spricht nichts gegen die Anzeige von **Rohwerten** (NDVI/EVI je Zelle) auf der ALEPH-Karte, genau wie bei VNP46A3. Eine ausdrückliche Anbieteraussage speziell zur *öffentlichen Kartenanzeige* (im Unterschied zu Weiterverbreitung/Verkauf allgemein) wurde nicht gefunden. **Empfehlung für `META`:** „Rohwerte anzeigen zulässig", mit demselben Vorbehalt wie bei VNP46A3 (keine anbieterseitige Einschränkungskennzeichnung einzelner Dateien geprüft) und dem zusätzlichen Vorbehalt, dass die LP-DAAC-Richtlinienseite hier nur per Suchauszug, nicht im Original gelesen wurde. [Eigene Überlegung, Abschnitt 6 und 12]

## 14. Sensorwechsel und Nachfolgeprodukt (Frage 5 des Auftrags)

Ja, es gibt ein VIIRS-Nachfolgeprodukt, analog zur Nachtlicht-Situation: **VNP13C2** (Suomi NPP, seit 2012), **VJ113C2** (NOAA-20) und **VJ213C2** (NOAA-21), alle als CMG-Vegetationsindizes „designed after" die MODIS-Produktfamilie. MOD13C2 selbst (Terra) ist von der Suomi-NPP-Abschaltung am 1. November 2026 nicht betroffen, aber Terra selbst nähert sich absehbar dem Missionsende (frühestens Ende 2026, spätestens Februar 2027 laut aktuellen Presse-/NASA-Berichten). Für ALEPHs historischen Zeitraum 2013–2025 ändert das nichts; für künftige Aktualisierungen (nach dem Hackathon) ist ein Wechsel auf VNP13C2/VJ113C2/VJ213C2 als Anschluss-Layer bereits heute als Option festzuhalten, inklusive der zu erwartenden Sensor-Bruchstelle im Zeitreihenvergleich (ARCHITECTURE.md Abschnitt 6, Punkt 6: „Sensorwechsel (MODIS → VIIRS)" wird dort bereits ausdrücklich als Beispiel genannt). [Zusammenfassung aus Abschnitt 8]

## 15. Empfehlung

**Einbauen** (zweiter Layer nach Nachtlicht), mit folgenden Bedingungen:
1. Vor dem ersten echten Download die CMR-Trefferzahl für 2013–2025 exakt zählen (z. B. mit `earthaccess.search_data(...)`), um die hier nur hochgerechnete Downloadmenge (Abschnitt 10) zu bestätigen oder zu korrigieren.
2. Leser für HDF4/HDF-EOS2 im Layer-Modul einbauen (GDAL/`rioxarray`/`pyhdf`), **nicht** `h5py` wie bei VNP46A3; das gemeinsame Herunterladen über `earthaccess` bleibt gleich.
3. Hauptfeld **NDVI** (Skalierungsfaktor 10000, Fehlwert −3000) für die Erkennung, EVI als Vergleichsfeld, „Pixel Reliability" und „Number of 1km Pixels Used" als Datenlage-Angabe je Zelle mitführen (analog `_Num`/`_Quality` bei VNP46A3).
4. Vor der öffentlichen Freigabe der NDVI-Rohwerte auf der Karte die LP-DAAC-Richtlinienseite (https://lpdaac.usgs.gov/data/data-citation-and-policies/) im Original nachlesen, da diese Sitzung sie nur per Suchauszug kannte.
5. In `META`: Bruchstelle „MOD13C2 → VNP13C2/VJ113C2/VJ213C2" als bekannten künftigen Sensorwechsel dokumentieren, auch wenn er den Zeitraum 2013–2025 nicht betrifft.

**Begründung:** Die Downloadmenge ist mit geschätzt 14–15 GB für den gesamten globalen Zeitraum sehr gering (verglichen mit 4,1 TB bei VNP46A3) und stellt kein Speicherproblem dar; Zugang und Lizenz folgen denselben, bereits für VNP46A3 geprüften NASA-Grundsätzen; das Produkt ist genau der in ARCHITECTURE.md vorgesehene Vegetations-Layer. Einzige Auflage: ein anderer Dateileser (HDF4 statt HDF5) und eine Bestätigung der Downloadmenge vor dem eigentlichen Download, da die Zählung in dieser Sitzung nicht vollständig, sondern nur stichprobenhaft erfolgen konnte.

## 16. Angaben, die nur aus einer (per WebFetch/WebSearch zusammengefassten) Quelle bestätigt sind

- Genaue Bedeutung der „Pixel Reliability"-Rangstufen und der VI-Qualitäts-Bitfelder: nur aus der LAADS-Dateispezifikation, per WebFetch-Zusammenfassung gelesen, nicht im HTML-Original gegengeprüft.
- LP-DAAC-Lizenztext („no restrictions on reuse, sale, or redistribution"): nur aus WebSearch-Auszug, Originalseite nicht selbst geöffnet.
- Terra-Missionsende (Februar 2027 bzw. mögliche Stilllegung Ende 2026): nur aus WebSearch-Auszügen von science.nasa.gov und einem Fachartikel-Portal (SatNews/Washington Technology), keine direkt gelesene NASA-Pressemitteilung mit Datum.
- Bekannter Aerosolfehler in MOD13 (Collection 6, korrigiert in 6.1): nur aus WebSearch-Auszug der LDOPE-Known-Issue-Seite.
- Downloadmenge 2013–2025 (156 Dateien, ~14–15 GB): aus einem bestätigten Muster (1 Datei/Monat) und einer kleinen Stichprobe von Dateigrößen hochgerechnet, **nicht** durch vollständiges Auszählen aller Monate bestätigt.

## 17. Nicht geprüft (Liste)

- Vollständiger Text des MODIS-VI-Nutzerhandbuchs (Collection 6.1 PDF).
- Exakte CMR-Trefferzahl für 2013–2025 (nur Stichproben, kein vollständiger Zähllauf).
- Ob `earthaccess` HDF4-Dateien ebenso reibungslos unterstützt wie HDF5 (kein eigener Test).
- Genaue Verzögerung zwischen Monatsende und Veröffentlichung der Datei.
- Genaue Definition und Grenzwerte aller VI-Qualitäts-Bitfelder im Detail.
- Vollständiger Text der LP-DAAC-Daten-Zitier- und Nutzungsrichtlinie (nur Suchauszug gelesen).
- Exaktes Datum der Terra-Missionsstilllegung (widersprüchliche Angaben in Presse-/NASA-Quellen: Herbst 2022 A-Train-Austritt, Ende 2026 mögliche Stilllegung, Februar 2027 Wissenschaftsende – alle drei beziehen sich vermutlich auf unterschiedliche Phasen, nicht im Detail auseinandergehalten).
- Ob es in einzelnen Monaten mehr als eine Granule gibt (z. B. durch Neuprozessierung mit zwei Versionsständen gleichzeitig im Archiv).
