# Steckbrief: GPM IMERG, monatlicher Niederschlag, global

Stand der Recherche: 2026-09-23. Erstellt vom Agenten „datenquellen-scout". Für diesen Steckbrief wurden **keine Daten heruntergeladen**; alle Angaben stammen aus Web-Recherche (Anbieterseiten, CMR-Metadatenabfrage, Suchergebnisse).

Kennzeichnung in diesem Dokument (wie in `docs/sources/vnp46a3.md`):
- **[Anbieter]** = Angabe stammt von NASA/GES DISC/GPM-Projekt, mit Link.
- **[Dritt]** = Angabe stammt von einer Drittquelle (z. B. AWS Open Data Registry, Google Earth Engine), nicht vom Anbieter selbst.
- **[Messung]** = eigene Stichprobe des Scouts (hier: CMR-Granule-Abfragen), keine Herstellerangabe.
- **[Eigene Überlegung]** = Schlussfolgerung/Hochrechnung des Scouts, nicht vom Anbieter belegt.
- „nicht geprüft" = konnte nicht belegt werden.

**Hinweis zur Methode:** Viele Angaben wurden über das WebFetch-Werkzeug gelesen, das Webseiten automatisch zusammenfasst (kleines Modell, keine wörtliche Wiedergabe). PDF-Dokumente (z. B. IMERG V07 Release Notes) konnten so **nicht** ausgewertet werden (Binärdaten, siehe Abschnitt 10). Vor einer Veröffentlichung in der Präsentation sollten die wichtigsten Zahlen (Lizenz, Datenmenge, Zeitraum) noch einmal im Original nachgeschlagen werden. Es wurden **keine** Probedateien heruntergeladen (anders als beim VNP46A3-Steckbrief); die Datenmenge in Abschnitt 11 ist eine Hochrechnung aus wenigen Stichproben, keine vollständige Katalogzählung.

---

## 1. Name und Anbieter

- **Name:** GPM IMERG Final Precipitation L3 1 month 0.1° × 0.1° V07 (Kurzname `GPM_3IMERGM`), Teil der Produktfamilie „Integrated Multi-satellitE Retrievals for GPM" (IMERG). [Anbieter: https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergm-07]
- **Anbieter:** NASA Goddard Earth Sciences Data and Information Services Center (GES DISC), Datenprodukt der Global Precipitation Measurement (GPM) Mission, einer gemeinsamen Mission von NASA und JAXA. [Anbieter: https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergm-07 ; Mission: https://gpm.nasa.gov/missions/GPM]
- **Algorithmus-Autoren (Principal Investigators laut Katalog):** G.J. Huffman, E.F. Stocker, D.T. Bolvin, E.J. Nelkin, J. Tan. [Anbieter: Earthdata-Katalogseite, wie oben]
- **DOI:** 10.5067/GPM/IMERG/3B-MONTH/07 [Anbieter: wie oben]
- **Offizielle Seiten:**
  - Earthdata-Katalog: https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergm-07
  - GES DISC Produktseite: https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGM_07/summary
  - GPM-Projektseite zu IMERG: https://gpm.nasa.gov/data/imerg
  - IMERG-Zitierhinweis: https://gpm.nasa.gov/node/3174
  - IMERG V07 Release Notes (PDF, nicht auswertbar gelesen): https://gpm.nasa.gov/sites/default/files/2024-12/IMERG_V07_ReleaseNotes_241126.pdf
  - CMR-Metadaten (maschinenlesbar): https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=GPM_3IMERGM&version=07

## 2. Inhalt

- **Gemessene Größe:** Niederschlag (Regen und Schnee gemeinsam als „Niederschlag" geführt), zusammengeführt aus passiven Mikrowellen-Sensoren der GPM-Satellitenkonstellation, Infrarot-Schätzungen geostationärer Satelliten und, nur im „Final Run", monatlichen Regenmesser-Daten (GPCC). [Anbieter: https://gpm.nasa.gov/data/imerg]
- **Haupt-Datenfeld:** `precipitation`, **Einheit mm/h** (Niederschlagsrate, kein direkter Monatssummenwert). Für eine Monatssumme in mm muss mit der Zahl der Stunden im Monat multipliziert werden. [Dritt, Feldbeschreibung: https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_MONTHLY_V07 — die Einheit mm/h wird auch in NASA-Tutorials so verwendet, aber nicht wörtlich auf der Earthdata-Katalogseite bestätigt: **nicht geprüft im Originaltext des Anbieters**]
- **Berechnung des Monatswerts (Final Run):** Die halbstündlichen Multi-Satelliten-Schätzungen werden für den Monat aufsummiert und mit der monatlichen GPCC-Regenmesser-Analyse über eine inverse Fehler-Varianz-Gewichtung kombiniert; alle halbstündlichen Werte des Monats werden anschließend so skaliert, dass sie den Monatswert ergeben. [Anbieter: https://gpm.nasa.gov/data/imerg, sinngemäß über Suchergebnis-Auszug wiedergegeben — Originaltext nicht Wort für Wort gelesen]
- **Weitere Datenfelder** laut Google-Earth-Engine-Katalog (Drittquelle, Feldnamen aber vom IMERG-Produkt selbst): `gaugeRelativeWeighting` (%, wie stark Regenmesser in die Schätzung eingegangen sind), `precipitationQualityIndex` (Qualitätsmaß, Einheit „äquivalente Messstationen pro 2,5°-Box"), `probabilityLiquidPrecipitation` (%, Wahrscheinlichkeit flüssiger statt fester Niederschlag), `randomError` (mm/h, Zufallsfehler). [Dritt: https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_MONTHLY_V07]. Diese Feldnamen wurden nicht direkt in einer NASA-HDF5-Datei nachgeprüft: **nicht geprüft**.

## 3. Räumliche Auflösung und Abdeckung

- **0,1° × 0,1°** Gitter (ca. 10 × 10 km, laut Google Earth Engine Pixelkantenlänge 11 132 m am Äquator), global, −180° bis 180° Länge, −90° bis 90° Breite (volle Polabdeckung, kein Kachel-Ausschnitt wie bei VNP46A3). [Anbieter: CMR-Metadaten, https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=GPM_3IMERGM&version=07 ; Pixelmaß: Dritt, GEE-Katalog wie oben]
- **Damit feiner als das ALEPH-Zielraster von 0,25° (ARCHITECTURE.md Abschnitt 4).** Anders als bei VNP46A3 (60 × 60 native Pixel pro Zielzelle, glatte Zahl) ist 0,25° / 0,1° = **2,5** – **keine ganze Zahl**. Eine ALEPH-Zielzelle deckt also 2,5 × 2,5 native IMERG-Pixel ab; eine einfache Blockmittelung wie bei VNP46A3 reicht nicht, es braucht eine flächengewichtete Aggregation (Randpixel gehen mit halbem Gewicht ein) oder ein Neuraster-Verfahren in `aleph/core/grid.py`. [Eigene Überlegung, aus der Auflösungsangabe]
- Eine Datei deckt die **ganze Erde** in einem Stück ab (kein Kachelsystem). [Messung, siehe Abschnitt 11]

## 4. Zeitliche Auflösung und Zeitraum

- **Monatlich.** Basis sind halbstündliche Einzelwerte, für den Final Run zusätzlich mit monatlichen Regenmesser-Daten kombiniert (Abschnitt 2). [Anbieter: https://gpm.nasa.gov/data/imerg]
- **Verfügbarer Zeitraum laut CMR-Metadaten:** 1. Januar 1998 bis „fortlaufend" (Enddatum in der Abfrage 2025-09-30, entspricht dem Abfragezeitpunkt der Kollektionsmetadaten, nicht zwingend dem tatsächlichen letzten Monat). [Anbieter: https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=GPM_3IMERGM&version=07]
- **Wichtiger Bruch:** Der Zeitraum begann ursprünglich am 1. Juni 2000. Am 7. November 2024 wurde er **rückwirkend bis Januar 1998** erweitert (Beginn der TRMM-Ära). Für diese Erweiterung (1998–Mai 2000) wurde wegen fehlender hochwertiger Infrarot-Referenzdaten (CPC-IR) ersatzweise „GridSat-B1"-Infrarotdaten verwendet; laut Analyse ist deren Qualität geringer, NASA empfiehlt, diese frühen Monate nur zu nutzen, wenn nötig. [Anbieter/Fachbericht, über Suchergebnis-Auszug wiedergegeben, nicht im Original gelesen: https://gpm.nasa.gov/sites/default/files/2024-12/IMERG_V07_ReleaseNotes_241126.pdf]. **Für ALEPH ohne Bedeutung**, da der Untersuchungszeitraum 2013–2025 (Entscheidung E3) vollständig nach Juni 2000 liegt. [Eigene Überlegung]
- **GPM-Start und TRMM-Ende:** Der GPM-Kernsatellit startete am 27. Februar 2014; TRMM lieferte bis 2014/2015. [Anbieter: https://gpm.nasa.gov/missions/GPM/launch]. IMERG verknüpft die TRMM-Ära (bis 2014) und die GPM-Ära (ab 2014) zu einer durchgehenden Reihe, aber ein eigenes Anbieter-Dokument („Caveats for IMERG in the TRMM Era", George Huffman, 3. Mai 2019, für V06 geschrieben) nennt Einschränkungen: Die Kalibrierungsreferenz TRMM CORRA deckt nur 35° N–S ab, für GPM dagegen 65° N–S; außerhalb 35° N–S ist die Kalibrierung in der TRMM-Ära „nur näherungsweise". In den frühen TRMM-Jahren fehlten zudem Mikrowellenbeobachtungen um bestimmte Überflugzeiten, wodurch mehr Infrarot-Schätzung nötig war. [Anbieter, Dokument nicht im Volltext gelesen, nur über Suchergebnis-Zusammenfassung: https://docserver.gesdisc.eosdis.nasa.gov/public/project/GPM/IMERGV06_TRMMera-caveats.pdf]. Für ALEPHs Zeitraum 2013–2025 betrifft das nur **2013 bis Anfang 2014** (letzte TRMM-Monate), danach ist die volle GPM-Konstellation aktiv. Ob das Dokument für V07 unverändert gilt, ist **nicht geprüft** (Titel nennt „V06").
- **Verzögerung (Latenz):** Der Final Run – aus dem das Monatsprodukt stammt – hat laut Anbieter eine Latenz von **rund 3,5 Monaten**, weil er auf MERRA-2-Feuchtedaten und die monatliche GPCC-Regenmesser-Analyse wartet. [Anbieter: https://gpm.nasa.gov/data/faq]. Eine Drittquelle (AWS-Registrierungsseite) nennt „etwa 4 Monate": [Dritt: https://registry.opendata.aws/nasa-gpm3imergm/]. Für ALEPHs monatlichen Takt unkritisch, aber wichtig für die Aktualität der jeweils letzten verfügbaren Monate.

## 5. Zugang

- **Frei, mit kostenlosem NASA-Earthdata-Konto** (dieselbe Anmeldung wie für VNP46A3, siehe `docs/sources/vnp46a3.md` Abschnitt 5). Anmeldung: https://urs.earthdata.nasa.gov [Anbieter: https://urs.earthdata.nasa.gov/documentation/for_users/how_to_register]
- Laut NASA-Anleitung ist die Registrierung „quick and easy": Nutzername, Passwort, E-Mail eingeben, danach kommt eine Bestätigungs-E-Mail zur Aktivierung. Eine **genaue Wartezeit bis zur Freischaltung nennt die Anleitung nicht**; nach Bestätigung der E-Mail scheint das Konto sofort nutzbar zu sein. [Anbieter, sinngemäß über Suchergebnis-Auszug, Originaltext nicht vollständig gelesen: https://urs.earthdata.nasa.gov/documentation/for_users/how_to_register]. **Nicht geprüft:** ob für GES-DISC-spezifische Dienste (z. B. Datenzugriffsfreigabe „GES DISC" im Earthdata-Profil) ein zusätzlicher, separat zu bestätigender Schritt nötig ist — beim VNP46A3-Zugang wurde dieser Schritt laut LOG.md bereits einmal durchlaufen, hier nicht erneut geprüft.
- **Kein separates Konto bei der Precipitation Processing System (PPS)** nötig für den GES-DISC-Zugriffsweg; PPS-Registrierung betrifft einen anderen, hier nicht genutzten Zugriffsweg für Near-Real-Time-Daten. [Anbieter: https://gpm.nasa.gov/data/directory]
- **Variablennamen in `.env`** (nur Namen, keine Werte): `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD` — dieselben wie bei VNP46A3, kein zusätzlicher Token nötig. [Eigene Überlegung, aus der gemeinsamen NASA-Earthdata-Infrastruktur]
- **Zugriffswege laut Anbieter:** direkter Download über GES DISC, Teil-Abfrage (Subsetting) und OPeNDAP-Streaming, außerdem über die Visualisierungsplattform Giovanni. [Anbieter: https://gpm.nasa.gov/data/directory]. Für ALEPH vorgesehen: `earthaccess` (ARCHITECTURE.md Abschnitt 5), wie bei allen NASA-Layern.
- **Alternativer Zugang (nicht für ALEPH vorgesehen):** AWS Open Data Registry und Google Earth Engine spiegeln das Produkt. [Dritt: https://registry.opendata.aws/nasa-gpm3imergm/ , https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_MONTHLY_V07]. Laut AWS-Seite ist der S3-Bucket dort „Controlled Access" und verlangt eigene AWS-Zugangsdaten — ein **anderer** Zugangsweg als earthaccess, für ALEPH nicht relevant, da dieselbe Ladelogik für alle Quellen gilt (CLAUDE.md).

## 6. Lizenz und Nutzungsbedingungen

- **Earthdata-Katalog (offizielle NASA-Quelle):** „This dataset is openly shared, without restriction, in accordance with the EOSDIS Data Use and Citation Guidance." Zusätzlich `AccessConstraints: None`, `UseConstraints`: Verweis auf dieselbe EOSDIS-Richtlinie. [Anbieter: https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=GPM_3IMERGM&version=07 ; wortgleich auch: https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergm-07]. Das ist **derselbe Wortlaut**, der für VNP46A3 gefunden wurde (docs/sources/vnp46a3.md Abschnitt 6), dort mit dem allgemeinen NASA-Grundsatz „CC0, sofern nicht anders gekennzeichnet" verbunden. [Anbieter: https://earthdata.nasa.gov/learn/use-data/data-citations-acknowledgements]
- **Widerspruch bei einer Drittquelle:** Die AWS-Open-Data-Registrierungsseite für genau dieses Produkt nennt als Lizenz **„Creative Commons BY 4.0"** (Namensnennung erforderlich). [Dritt: https://registry.opendata.aws/nasa-gpm3imergm/]. Das ist **strenger** als CC0 (Namensnennungspflicht statt Bitte). Ob das eine eigenständige, verbindliche Lizenzangabe ist oder nur eine vereinfachte AWS-Standardkennzeichnung, konnte hier **nicht geklärt werden: nicht geprüft**. Für ALEPH ist der Unterschied praktisch klein, da ohnehin bei jeder Quelle zitiert wird (CLAUDE.md-Grundsatz „Nachprüfbarkeit"), aber die Angabe sollte vor der Präsentation an der Originalquelle (GES DISC, nicht AWS) noch einmal geprüft werden.
- **Nicht-kommerzielle Nutzung:** ausdrücklich erlaubt; die GPM-Projektseite formuliert allgemein (laut Google-Earth-Engine-Zusammenfassung): „All NASA-produced data from the GPM mission is made freely available for the public to use", Nutzung für Forschung, Bildung und gemeinnützige Zwecke kostenfrei. [Dritt-vermittelt, ursprünglich Anbieteraussage: https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_MONTHLY_V07 — Originalformulierung auf einer NASA-Seite nicht selbst gefunden: **nicht geprüft im NASA-Original**]
- **Quellenangabe:** Laut GPM-Zitierhinweis „soll" (nicht: muss) die Datenquelle genannt werden: „The data set source should be acknowledged when the data are used." Empfohlenes Zitierformat: Autor/Herausgeber, Erscheinungsdatum, Titel, Version, Archiv/Verteiler, Zugriffsdatum, DOI/URL, nach AMS-Richtlinien. Beispiel: „G.J. Huffman et al., 2023: Integrated Multi-satellitE Retrievals for GPM (IMERG), version 07. NASA's Precipitation Processing Center, accessed [Datum], [URL/DOI]." [Anbieter: https://gpm.nasa.gov/node/3174]
- **Folgerung für ALEPH** [Eigene Überlegung, wie beim VNP46A3-Steckbrief]: Nicht-kommerzielle Nutzung ist erlaubt. Anzeige von Rohwerten (z. B. Niederschlagskarte) ist nach der NASA-Formulierung „ohne Einschränkung" zulässig; wegen der abweichenden AWS-Angabe (CC BY 4.0) sollte ALEPH in jedem Fall eine sichtbare Quellenangabe mit DOI/Link zeigen, dann ist beides erfüllt. **Für `META`: Anzeige von Rohwerten zulässig, Quellenangabe verpflichtend gestalten (schadet nicht, deckt beide Lizenzlesarten ab).**

## 7. Dürfen Rohdaten auf der ALEPH-Karte gezeigt werden? (ARCHITECTURE.md Abschnitt 5)

- **Ja, nach den gefundenen Angaben.** Es gibt keine gefundene Einschränkung, die nur zusammengefasste Werte oder nur Verweise erlauben würde – anders als von ARCHITECTURE.md Abschnitt 5 als möglicher Fall beschrieben. Beide gefundenen Lizenzangaben (NASA: „ohne Einschränkung"; AWS: CC BY 4.0) erlauben öffentliche Weitergabe einschließlich Rohdaten-Darstellung, CC BY 4.0 zusätzlich mit Namensnennungspflicht. [Eigene Überlegung, aus Abschnitt 6 abgeleitet]
- **Einschränkung, die zu beachten ist:** Dies gilt für die **Rohwerte selbst** (Niederschlagsrate pro Zelle/Monat). Es wurde **nicht geprüft**, ob es zusätzliche Bedingungen für die Weiterverbreitung der eingeflossenen GPCC-Regenmesser-Daten gibt (GPCC ist ein Dienst des Deutschen Wetterdienstes, eine eigene, hier nicht recherchierte Institution). Da GPCC nur als **aggregierter Eingang** in das fertige IMERG-Produkt eingeht (keine einzelnen Stationsdaten), ist das Risiko nach Einschätzung des Scouts gering, aber **nicht geprüft**.

## 8. Python-Zugriff und Dateiformat

- **Format:** HDF5, **eine Datei pro Monat für die ganze Erde** (kein Kachelsystem wie bei VNP46A3). Dateiname-Muster laut Stichprobe: `3B-MO.MS.MRG.3IMERG.YYYYMM01-S000000-E235959.MM.V07B.HDF5`. [Messung, siehe Abschnitt 11; Format auch: Anbieter, CMR-Metadaten „DataFormat: HDF5 (Native)"]
- **Bibliothek:** `earthaccess` (ARCHITECTURE.md Abschnitt 5, dieselbe Ladelogik wie bei allen NASA-Layern). NASA selbst stellt ein offizielles Tutorial-Notebook „How_to_Read_IMERG_Data_Using_Python.ipynb" bereit, das `earthaccess` und `xarray` verwendet. [Anbieter/GitHub-NASA-Organisation: https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Read_IMERG_Data_Using_Python.ipynb — Inhalt des Notebooks selbst nicht geöffnet: **nicht geprüft im Detail**]
- Lesen der HDF5-Datei z. B. mit `h5py` oder `xarray` (mit `h5netcdf`/`netCDF4`-Engine); vom Scout nicht selbst getestet, keine Datei heruntergeladen (siehe Kopf des Dokuments): **nicht geprüft**.
- **Drittzugang, nur zur Kenntnis:** Auch über Google Earth Engine (`NASA_GPM_L3_IMERG_MONTHLY_V07`) und AWS Open Data verfügbar. Für ALEPH nicht vorgesehen (CLAUDE.md: „Alle Datenquellen nutzen dieselbe Ladelogik").

## 9. Bekannte Schwächen

- **Schneefall in Version 07 unterschätzt**, Niederschlag in Gebirgsregionen insgesamt weniger zuverlässig; für Schneedeckenabschätzung nicht geeignet. [Anbieter: https://gpm.nasa.gov/data/faq]
- **TRMM/GPM-Sensorwechsel:** Kalibrierungsreferenz deckt in der TRMM-Ära nur 35° N–S ab (GPM-Ära: 65° N–S), außerhalb davon ist die frühe Kalibrierung nur näherungsweise; betrifft bei ALEPH vor allem die Jahre 2013 bis Anfang 2014. [Anbieter, nur über Zusammenfassung gelesen, siehe Abschnitt 4]
- **Latenz von ca. 3,5–4 Monaten** beim Final Run (Abschnitt 4); die jeweils letzten Monate vor dem aktuellen Datum sind noch nicht als Final-Run-Monatswert verfügbar. [Anbieter/Dritt, siehe Abschnitt 4]
- **Version-7-Neuberechnung:** Der komplette TRMM-GPM-Zeitraum wurde 2023/2024 einheitlich auf V07 neu berechnet (zwei Durchläufe, zweiter abgeschlossen 8. Januar 2024, wegen fehlerhafter GPROF-Schätzungen in 238 Orbits). **Vorteil für ALEPH:** Der gesamte Zeitraum 2013–2025 liegt in derselben, einheitlich prozessierten Version — anders als bei VNP46A3 gibt es keinen Versionsbruch *innerhalb* des ALEPH-Zeitraums, sofern ausschließlich V07 geladen wird. [Dritt-vermittelt über Suchergebnis, ursprünglich NASA-Release-Notes, nicht im Original gelesen: https://gpm.nasa.gov/sites/default/files/2024-12/IMERG_V07_ReleaseNotes_241126.pdf]. Künftige Versionen (V08 o. ä.) würden einen neuen Bruch erzeugen; das Datum eines möglichen nächsten Versionswechsels ist **nicht geprüft**.
- **Regenmesser-Abdeckung uneben:** Der Final Run gewichtet mit monatlichen GPCC-Regenmesserdaten; über Ozeanen und dünn besiedelten Gebieten gibt es kaum oder keine Regenmesser, dort stützt sich der Wert stärker auf reine Satellitenschätzung. Das Feld `gaugeRelativeWeighting` (Abschnitt 2) zeigt das pro Zelle an. [Eigene Überlegung, gestützt auf die Feldbeschreibung, nicht wörtlich vom Anbieter als „Schwäche" benannt]
- **Auflösungs-Mismatch zum ALEPH-Raster** (0,1° vs. 0,25°, Faktor 2,5, siehe Abschnitt 3): technischer Mehraufwand bei der Aggregation, sonst keine inhaltliche Schwäche. [Eigene Überlegung]
- **Frühe TRMM-Ära (1998–Mai 2000) mit geringerer Qualität**, für ALEPHs Zeitraum ohne Bedeutung (Abschnitt 4).
- Genauigkeit „vor Ort" schwer prüfbar / stark von der lokalen Regenmesser-Dichte abhängig — analog zur bei VNP46A3 dokumentierten Aussage „in-situ-Messungen nicht flächendeckend verfügbar", hier aber **nicht wortgleich in einer NASA-Quelle gefunden: nicht geprüft**.

## 10. Rolle in ALEPH

Niederschlag ist laut ARCHITECTURE.md Abschnitt 5 ein Kandidat für einen **Erkennungs-Layer** („Dürre, Überschwemmung"), vorgesehen für Woche 4 des Zeitplans (Abschnitt 13). Er ist außerdem Bestandteil des Beispiel-Theorieeintrags „Dürre → Abwanderung" (Abschnitt 8 der Architektur: Niederschlagsrückgang als Ursache, Nachtlicht-Rückgang/Abwanderung als Wirkung) und wird im Muster „Anomalie: Dürre" (Abschnitt 7: „Niederschlagsdefizit + Vegetationsrückgang über mehrere Monate") mit dem Vegetations-Layer (MODIS NDVI) verknüpft. Zielraster: 0,25° global, monatlich, Untersuchungszeitraum 2013–2025 (Entscheidung E3).

## 11. Datenmenge

**Eigene Stichproben (CMR-Granule-Abfrage, keine vollständige Katalogzählung):**
- Januar–Mai 2013: Dateigrößen zwischen 16,76 MB und 18,19 MB. [Messung: CMR-Granule-Suche `short_name=GPM_3IMERGM&version=07`]
- Januar–Dezember 2024 (alle 12 Monate geprüft): Dateigrößen zwischen 17,33 MB und 18,43 MB, Summe der 12 Dateien ca. 218 MB. [Messung, wie oben]
- Format/Muster durchgehend: ein Granule pro Kalendermonat, weltweit, kein Kachelsystem. [Messung]

**Hochrechnung für 2013–2025** [Eigene Überlegung, **keine vollständige Zählung aller 156 Monate**, nur Interpolation aus den beiden Stichproben oben]:
- 13 Jahre × 12 Monate = **rund 156 Dateien** (sofern der komplette Jahrgang 2025 bis zum Download-Zeitpunkt bereits als Final-Run-Monatswert vorliegt; wegen der 3,5–4-monatigen Latenz, siehe Abschnitt 4, war das zum Zeitpunkt der Kollektions-Zeitstempel in den Metadaten, 30. September 2025, noch nicht vollständig der Fall, dürfte aber bis zum tatsächlichen ALEPH-Download nachgeliefert sein).
- Bei einer mittleren Dateigröße von ca. 17,5–18 MB ergibt das **grob 2,7–2,9 GB für den gesamten globalen Datensatz 2013–2025** — **rund 1 400-mal weniger** als die 4,01 TB, die für VNP46A3 im selben Zeitraum ermittelt wurden (docs/sources/vnp46a3.md Abschnitt 15). [Eigene Überlegung/Rechnung]
- Ein Fokusgebiet lässt sich hier **nicht** durch Auswahl einzelner Kacheln verkleinern (kein Kachelsystem); die volle globale Monatsdatei (≈ 18 MB) muss ohnehin geladen werden, ist aber wegen der geringen Größe unkritisch. Teil-Abfrage per OPeNDAP/Subsetting wäre möglich, aber angesichts der geringen Dateigröße für ALEPH nicht nötig. [Eigene Überlegung]
- **Fertiger Würfel** (analog zur Rechnung bei VNP46A3): 1440 × 720 Zellen × 156 Monate × 4 Byte (float32) ≈ 0,65 GB pro Feld, unkomprimiert — dieselbe Größenordnung wie bei jedem anderen Layer auf dem ALEPH-Zielraster, unabhängig von der nativen Auflösung der Quelle. [Eigene Überlegung/Rechnung]

## 12. Empfehlung

**Einbauen**, mit folgenden Bedingungen:

1. **Version fest auf V07 (aktuell Build V07B) setzen** und in `layers.yaml`/`META` dokumentieren; bei einer künftigen Version (V08 o. ä.) den ganzen Zeitraum neu laden, nicht mischen (CLAUDE.md: „Fehler explizit erklären statt Workarounds").
2. **Aggregation auf 0,25° sorgfältig umsetzen**: 0,1°-Raster passt nicht glatt in 0,25°-Zellen (Faktor 2,5), es braucht eine flächengewichtete Methode statt einer einfachen 1:1-Blockmittelung.
3. **Datenlage pro Zelle mitführen**: `gaugeRelativeWeighting` und `precipitationQualityIndex` zusätzlich zum Hauptwert speichern (analog zu `_Num`/`_Quality` bei VNP46A3), damit Zellen mit sehr wenig Regenmesser-Stützung erkennbar sind.
4. **2013–Anfang 2014 (letzte TRMM-Monate) als möglicherweise weniger verlässlich kennzeichnen**, besonders außerhalb 35° N–S, bis der Original-Text des Caveats-Dokuments geprüft wurde.
5. **Immer mit sichtbarer Quellenangabe (Name, DOI, Zugriffsdatum) anzeigen**, um sowohl die NASA-Formulierung („ohne Einschränkung") als auch die abweichende AWS-Angabe (CC BY 4.0) zu erfüllen.
6. **Vor Produktivbetrieb:** Lizenztext direkt bei GES DISC (nicht nur AWS) noch einmal im Original nachlesen und die PDF-Release-Notes einmal richtig auswerten (hier nur als Binärdatei gescheitert).

**Begründung:** Der Layer ist in ARCHITECTURE.md bereits als Kandidat vorgesehen, die Datenmenge ist mit rund 2,7–2,9 GB für 2013–2025 sehr klein (kein Speicher- oder Zeitrisiko), der Zugang läuft über dasselbe kostenlose Earthdata-Konto wie beim bereits eingerichteten VNP46A3-Layer, und der komplette ALEPH-Zeitraum liegt in einer einheitlich reprozessierten Version (V07) ohne internen Versionsbruch. Die Hauptrisiken sind technischer Art (Auflösungs-Mismatch) und rechtlich unscharf (CC0 vs. CC BY 4.0), beide sind mit den oben genannten Maßnahmen gut beherrschbar.

## 13. Zusammenfassung (einfache Sprache)

GPM IMERG ist ein kostenloses NASA/JAXA-Satellitenprodukt, das weltweiten Niederschlag pro Monat auf einem sehr feinen 0,1°-Raster liefert – feiner als das 0,25°-Raster, das ALEPH für alle Layer nutzt, sodass beim Einbau eine kleine Rechenaufgabe (Zusammenfassen der Zellen) ansteht. Der Zugang läuft über dasselbe kostenlose NASA-Konto, das für das Nachtlicht schon eingerichtet wurde. Die Datenmenge ist winzig: für den gesamten Zeitraum 2013–2025 und die ganze Erde geschätzt nur rund 2,7 bis 2,9 Gigabyte, also tausendfach weniger als beim Nachtlicht-Layer. Ob Rohwerte öffentlich gezeigt werden dürfen, ist nach den gefundenen Angaben ja, allerdings nennt eine NASA-Quelle „ohne Einschränkung" und eine andere (AWS) „Namensnennung erforderlich" – deshalb sollte ALEPH die Quelle immer sichtbar angeben, dann sind beide Angaben erfüllt. Empfehlung: einbauen, wie in der Architektur vorgesehen, mit sorgfältiger Behandlung der frühen TRMM-Jahre (2013/2014) und einer sauberen Flächengewichtung beim Umrechnen auf das gemeinsame Raster.

## 14. Nicht geprüft (Liste)

- Originaltext der IMERG-V07-Release-Notes (PDF ließ sich nicht auswerten).
- Ob „Caveats for IMERG in the TRMM Era" (Dokument von 2019, für V06 geschrieben) unverändert für V07 gilt.
- Genaue Wartezeit bis zur Freischaltung eines neuen Earthdata-Kontos.
- Ob ein zusätzlicher GES-DISC-spezifischer Freischaltungsschritt im Earthdata-Profil nötig ist.
- Wortlaut „mm/h" als Einheit direkt auf einer NASA-Seite (nur über Drittquelle/Tutorials bestätigt).
- Ob CC BY 4.0 (AWS) oder „ohne Einschränkung/CC0" (Earthdata-Katalog) die rechtlich maßgebliche Angabe ist.
- Auswirkungen einer möglichen eigenen GPCC-Lizenzbedingung auf das fertige, aggregierte IMERG-Produkt.
- Tatsächliche Feldstruktur einer heruntergeladenen HDF5-Datei (keine Probedatei geladen, im Unterschied zum VNP46A3-Steckbrief).
- Exakte Zahl der bislang veröffentlichten Monate für 2025 zum Zeitpunkt eines künftigen ALEPH-Downloads.
- Datum eines möglichen künftigen Versionswechsels (V08 o. ä.).
