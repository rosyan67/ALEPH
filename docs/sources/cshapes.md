# Steckbrief: CShapes 2.0 (historische Staatsgrenzen, ETH Zürich)

Stand 2026-09-26, Status: nur geprüft, nicht eingebaut

Recherche: Agent „datenquellen-scout“, Abrufdatum aller Seiten 2026-09-26. Es wurde nichts eingebaut und kein Datensatz heruntergeladen. Geladen wurden nur Dokumentation (zwei PDF-Dateien, 118 KB und 73 KB), der Fachartikel als PDF (1,9 MB) und kleine Metadaten-Abfragen.

**Kurz:** CShapes 2.0 gibt es. Es wird von ETH Zürich, International Conflict Research, herausgegeben und reicht **nur bis 31.12.2019**. Für ALEPH (2013–2025) fehlen damit 2020–2025, also auch die Ereignisse 2022 (Ostukraine) und 2023 (Bergkarabach). Die Lizenz ist **CC BY-NC-SA 4.0**. Die Codes sind **Gleditsch-Ward bzw. COW, nicht ISO3**. **Empfehlung: nicht als Ersatz für Natural Earth; allenfalls später als Prüfquelle für 2013–2019.**

Kennzeichnung:
- **[Volltext]** = im Original selbst gelesen. Das PDF wurde mit dem Read-Werkzeug direkt als Text und Seitenbild geöffnet, **ohne** Zusammenfassung durch ein Hilfsmodell. Zählt als `originaltext`.
- **[Hilfsmodell]** = über WebFetch gelesen, also in der Wiedergabe eines Hilfsmodells. Das zählt nach CLAUDE.md **nicht** als Volltext. Zitate sind die „wörtliche“ Wiedergabe des Hilfsmodells und nicht am Original gegengelesen.
- **[Dritt]** = Quelle ist nicht der Anbieter.
- **[Eigene Überlegung]** = Schlussfolgerung des Scouts.
- „nicht geprüft“ = nicht belegt.

---

## 1. Name, Anbieter, Veröffentlichung (Frage 1)

- **Name:** CShapes 2.0. Es gibt zwei Fassungen: auf Basis der Staatenliste von Gleditsch & Ward (GW) oder von Correlates of War (COW). Dazu kommt „CShapes-Europe“ (ab 1816).
- **Anbieter:** ETH Zürich, International Conflict Research (ICR). Datenseite: https://icr.ethz.ch/data/cshapes/ (abgerufen 2026-09-26) [Hilfsmodell]:
  - „CShapes 2.0 maps the borders and capitals of independent states and dependent territories from 1886 to 2019 and from 1816 for CShapes-Europe.“
  - „There are two versions of the dataset, which are based on the Gleditsch and Ward (1999) or the Correlates of War coding of independent states.“
- **Institution im Artikel** [Volltext, S. 1]: Affiliation 1 lautet „Center for Comparative and International Studies, ETH Zürich, Switzerland“. Weitere Autoren kommen von der Universität Konstanz, der University of Essex und PRIO. Korrespondenzautor ist Nils B. Weidmann (Konstanz).
- **Veröffentlichung**, geprüft über Crossref https://api.crossref.org/works/10.1177/00220027211013563 (abgerufen 2026-09-26) [Hilfsmodell-Wiedergabe des JSON]:
  - Titel: „Mapping the International System, 1886-2019: The CShapes 2.0 Dataset“
  - Autoren (Reihenfolge laut Crossref und Artikel-PDF): Guy Schvitz, Luc Girardin, Seraina Rüegger, Nils B. Weidmann, Lars-Erik Cederman, Kristian Skrede Gleditsch
  - Zeitschrift: Journal of Conflict Resolution, Band 66, Heft 1, S. 144–161; Druck 2022-01, online 2021-05-04; Verlag SAGE
  - DOI: 10.1177/00220027211013563; Lizenz des **Artikels** laut Crossref: https://creativecommons.org/licenses/by-nc/4.0/
- **Unstimmigkeiten beim Anbieter:**
  - Die ETH-Seiten zitieren den Titel als „Mapping The International System, **1886-2017**: The CShapes 2.0 Dataset“ und nennen die Autoren in anderer Reihenfolge (Schvitz, Rüegger, Girardin, Cederman, Weidmann, Gleditsch) [Hilfsmodell: https://icr.ethz.ch/data/cshapes/, https://icr.ethz.ch/publications/cshapes-2/]. Crossref und das Artikel-PDF sagen „1886-2019“. Maßgeblich für Zitate sind Crossref und das PDF.
  - Die Tabelle 1 im Artikel nennt als Zeitraum „1886-2018“ [Volltext, S. 3], der Abstract „1886 through 2019“.
- **Gelesener Volltext:** https://repository.essex.ac.uk/31791/1/00220027211013563.pdf (Repositorium der University of Essex, abgerufen 2026-09-26). Es ist die SAGE-Satzfassung mit Seitenzählung 1–18 (Online-First), nicht die Heftfassung S. 144–161. Deshalb sind die Seitenangaben unten die der PDF-Fassung.

## 2. Inhalt

- Polygone von unabhängigen Staaten und abhängigen Gebieten mit Gültigkeitszeitraum, dazu Hauptstadt (Name, Koordinaten). Keine Messung, keine Einheit außer Fläche (km²).
- Zitat [Volltext, S. 4]: „Each polygon is linked to a row in an attribute table that contains further information, such as the time period during which the polygon is active, the territory's political status and the name and location of its capital.“
- Keine Verwaltungsgrenzen unterhalb der Staatsebene [Volltext, S. 3]: „CShapes is limited to international boundaries and does not map sub-national administrative boundaries.“
- Umfang [Volltext, S. 9]: „The final dataset covers 249 political units that are represented by 476 polygons over time. […] In total, our dataset covers 357 territorial changes.“

## 3. Zeitraum (Frage 2)

- **Ende: 31. Dezember 2019.** Changelog, Eintrag „2020-06-07 (2.0)“: „Updated CShapes until December 31, 2019.“ und „Backdated CShapes to January 1, 1886.“ [Hilfsmodell: https://icr.ethz.ch/data/cshapes/ChangeLog.txt; das Modell weigerte sich, den ganzen Changelog wörtlich wiederzugeben, und lieferte nur diese Einträge]
- Artikel, Abstract [Volltext, S. 1]: „a GIS dataset that maps the borders of states and dependent territories from 1886 through 2019.“
- **Zeitliche Auflösung: tagesgenau.** [Volltext, S. 3]: „CShapes records the exact date of each territorial change and therefore effectively accounts for changes on a daily basis.“ Einschränkung aus der Kodieranleitung [Volltext, Codebook S. 3]: „In some cases, our dataset does not yet list the correct date, as our source datasets often did not provide exact dates. In these cases, we used the first of January, or the first of the month as a default.“
- **Keine neuere Version gefunden.** Das R-Paket auf CRAN hat Version 2.0 vom 2021-06-05 [Volltext: https://cran.r-project.org/web/packages/cshapes/cshapes.pdf, S. 1]. Dessen Beschreibung „country borders (1886-today)“ widerspricht dem Changelog. Ob das Paket Daten nach 2019 enthält: nicht geprüft. Eine Websuche nach Aktualisierungen 2023–2025 fand nur CShapes-Europe (Buch Cederman et al. 2025) und keine Fortschreibung nach 2019. Dass es keine gibt, ist damit **nicht bewiesen**, nur nicht gefunden.

**Abdeckung der gefragten Ereignisse:**

| Ereignis | Abgedeckt? | Beleg |
|---|---|---|
| Krim 2014 | vermutlich ja: Krim ab 18.03.2014 bei Russland | nur [Dritt]: öffentliche ArcGIS-Kopie „CShapes-2.0“ (Eigentümer unbekannt), Abfrage 2026-09-26: https://services1.arcgis.com/DIcffHalFljSYvfk/arcgis/rest/services/Map_uten_landegrenser_WFL1/FeatureServer/18. Ukraine (gwcode 369): Zeile 1991-12-26 bis 2014-03-17, Fläche 597 502,75 km², danach 2014-03-18 bis 2019-12-31, 571 666,6 km². Russland (365): 1991-12-21 bis 2014-03-17, 16 882 562 km², dann ab 2014-03-18 16 908 398 km². Differenz je rund 25 836 km². Am Originaldatensatz der ETH **nicht geprüft**. |
| Ostukraine 2014 (Donezk/Luhansk) | bleibt bei der Ukraine | [Dritt, dieselbe Abfrage]: Die Ukraine hat nach 2014-03-18 keine weitere Änderung bis 2019. Passt zur Regel für De-facto-Staaten (Abschnitt 4). |
| Ostukraine 2022 | **nein** | Datensatz endet 2019-12-31 |
| Bergkarabach 2020/2023 | **nein** | Datensatz endet 2019-12-31. Nach der Regel für De-facto-Staaten wäre Bergkarabach ohnehin bei Aserbaidschan: [Dritt] Aserbaidschan (373) hat eine einzige Zeile 1991-12-26 bis 2019-12-31. |

## 4. Zuordnungsregel und umstrittene Gebiete (Frage 3)

Alle Zitate in diesem Abschnitt sind **[Volltext]** aus dem Artikel (Essex-PDF) bzw. aus dem „Codebook“.

- **Staatenlisten:** GW und COW, zwei getrennte Fassungen [S. 4–5]: „we decided to ensure full compatibility with both the GW and COW list […] we provide two separate versions CShapes 2.0 that are based either on the COW or GW coding of independent states.“ Fußnote 4 [S. 16]: „The COW-based version of CShapes 2.0 was derived automatically from the GW-based version.“
- **Grundregel: international anerkannte Grenzen** [S. 5]: „we code a state's territory primarily based on its internationally recognized boundaries. In most cases, this means that we code borders as they were defined in bilateral and multilateral agreements and shown on contemporaneous maps.“
- **Umstrittene Gebiete: de facto Kontrolle, keine eigenen Einheiten** [S. 6]: „Instead of coding disputed territories separately, however, we assign them to a given state based on its de facto control over the region. In the case of the Golan Heights, this means that we assign the disputed territory to Israel, although its control over the region is not internationally recognized. In the case of Kashmir, we code the Line of Control as the existing border“. Begründung in Fußnote 8 [S. 16]: „One potential solution would be to code disputed territories as separate units that do not belong to any state. However, we view territorial disputes as an important subject in their own right, which are best dealt with as part of a separate data collection effort.“
- **Nicht anerkannte De-facto-Staaten: beim Mutterstaat** [S. 6]: „Another related issue arises with de facto states, such as Abkhazia and South Ossetia, both of which declared independence from Georgia in the early 1990s, but have not received international recognition. […] Because these entities do not count as independent states according to our definition, we do not code them as separate units and instead assign their claimed territory to the host state they are located in.“
- **Kriegsbedingte Änderungen** [S. 8]: „we also excluded wartime territorial changes, unless they were made permanent in treaties signed after the war.“
- **Mindestgröße** [S. 7]: „we have restricted our coding efforts to transfers of territory larger than 100 × 100 km, as done in the previous version of CShapes.“ Die Kodieranleitung sagt „Territorial changes below 10'000 sqkm“ [Codebook S. 4].
- **Kodieranleitung (Codebook)**, https://icr.ethz.ch/data/cshapes/CShapes-2.0_Codebook.pdf, datiert „December 21, 2018“ [Volltext, S. 3]: „Note that we only code *de jure* changes in territory and sovereignty. Therefore, we code the day on which for example a treaty was signed as the day a territorial change occurred.“ Außerdem ausgeschlossen [S. 4]: „Cases in which a de-facto secession occurred that lacked international support and recognition (e.g. Biafra).“
  - **Achtung:** Die Datei heißt „Codebook“, ist aber eine interne Arbeitsanweisung an Kodierer („Your task will be to provide background information…“). Sie nennt noch den Zeitraum „from 1886 to 2017“, und die Quellen der Codes sind als „?“ stehengeblieben („gwcode: Country identifier based on ? for independent states and ? for dependencies.“). Ein eigentliches Codebuch mit der Beschreibung der ausgelieferten Spalten wurde nicht gefunden.
- **Zusammengefasst [Eigene Überlegung]:** Grundsätzlich de jure. Umstrittene Grenzstücke werden nach de facto Kontrolle einem Staat zugeordnet. Nicht anerkannte Abspaltungen gehören zum Mutterstaat. Eigene Einheiten sind nur Staaten der GW- bzw. COW-Liste. Wie die Krim 2014 unter diese Regeln fällt, sagt der Text nicht ausdrücklich. Die Drittkopie zeigt eine Zuordnung zu Russland ab 18.03.2014 (Abschnitt 3).

**Einzelne Gebiete** (Belegart jeweils angegeben):

| Gebiet | Eigene Einheit? | Beleg |
|---|---|---|
| Abchasien, Südossetien | nein, gehören zu Georgien | [Volltext, S. 6], Zitat oben |
| Taiwan | ja, gwcode 713, Zeilen 1895–1945 und 1949-12-08 bis 2019-12-31 | [Dritt, ArcGIS-Abfrage]; im Artikel nicht erwähnt |
| Kosovo | ja, gwcode 347, ab 2008-02-20 | [Dritt, ArcGIS-Abfrage]. Der Changelog einer älteren Version erwähnt „Removed ISO codes for Kosovo since no official code has been assigned.“ [Hilfsmodell, ChangeLog.txt] |
| Somaliland | keine eigene Einheit; Somalia (520) eine Zeile 1960-07-01 bis 2019-12-31 | [Dritt]; folgt aus der Regel für nicht anerkannte Staaten [Eigene Überlegung] |
| Nordzypern | keine eigene Einheit; Zypern (352) 9 128 km² von 1960 bis 2019 unverändert, also vermutlich die ganze Insel | [Dritt]; Flächenschluss [Eigene Überlegung] |
| Westsahara | keine eigene Einheit gefunden; Marokko (600) ab 1979-08-05 mit 672 200 km², vermutlich einschließlich Westsahara | [Dritt]; Flächenschluss [Eigene Überlegung], nicht geprüft |

Die Drittkopie ist die GW-Fassung (Spalten `gwcode`, `gwsdate` …). Ob sie unverändert der ETH-Datei entspricht: **nicht geprüft**.

## 5. Räumliche Genauigkeit, Format, Zugang, Lizenz (Frage 4)

- **Genauigkeit / Maßstab:** Eine Angabe zu Maßstab, Punktdichte oder Lagegenauigkeit der Linien wurde **nicht gefunden**: nicht geprüft. Belegt ist nur die Herkunft:
  - Die ursprüngliche Geometrie stammt aus dem ESRI-Länder-Shapefile. [Volltext, Fußnote 1, S. 15–16]: „The ESRI countries shapefile served as the basis for the original CShapes dataset (Weidmann, Kuse, and Gleditsch 2010).“
  - Ältere Grenzen wurden von georeferenzierten historischen Karten gezeichnet [S. 8]: „We geo-referenced these maps using GIS software and used them to draw and modify country borders.“
  - Das R-Paket vereinfacht Polygone **nur** für Distanzberechnungen (Douglas-Peucker, „keep“ Standard 0.1) [Volltext, CRAN-Handbuch S. 2–3]. Ob die ausgelieferten Polygone selbst vereinfacht sind: nicht geprüft.
  - Flächen aus der Drittkopie: Malediven 33,6 km², Bahrain 628,8 km², Barbados 442 km² [Dritt]. Die Malediven haben laut Allgemeinwissen rund 300 km² Landfläche; das deutet auf eine grobe oder vereinfachte Küstenlinie hin. [Eigene Überlegung, nicht geprüft]
- **Formate** [Hilfsmodell, https://icr.ethz.ch/data/cshapes/]: CSV (UTF-8), Tab-getrennt, GeoJSON, Shapefile, SQL, R-Paket. Verlinkte Dateinamen: `CShapes-2.0.csv`, `CShapes-2.0.txt`, `CShapes-2.0.geojson`, `CShapes-2.0.zip` (Shapefile), `CShapes-2.0.sql`, `cshapes_2.0.tar.gz`, `CShapes-Europe.geojson`, `CShapes-2.0_Codebook.pdf`, `ChangeLog.txt`.
- **Erreichbarkeit** (2026-09-26):
  - `https://icr.ethz.ch/data/cshapes/CShapes-2.0_Codebook.pdf` wurde geladen (117,5 KB) und `…/ChangeLog.txt` gelesen.
  - Die Verzeichnisse `…/Dyadic_distance_data/` und `…/Shapefiles/` sind als Verzeichnislisten abrufbar.
  - Die eigentlichen Datendateien (`CShapes-2.0.zip`, `.geojson`, `.csv`) wurden **nicht** abgerufen, um nichts Großes zu laden. Ob sie funktionieren und wie groß sie sind: nicht geprüft. Die Adressen wurden aus den relativen Links der Datenseite zusammengesetzt, also `https://icr.ethz.ch/data/cshapes/CShapes-2.0.zip` usw. [Eigene Überlegung].
- **Zugang:** frei, ohne Konto oder Token. Das wurde auf keiner Seite ausdrücklich gesagt, ist aber aus den direkten Links abgeleitet [Eigene Überlegung]. **Variablen in `.env`:** keine.
- **Lizenz der Daten: CC BY-NC-SA 4.0.** [Hilfsmodell, https://icr.ethz.ch/data/cshapes/]: „CShapes by Schvitz, Rüegger, Girardin, Cederman, Weidmann, Gleditsch is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.“ Dazu der Artikel [Volltext, S. 4]: „CShapes 2.0 is freely available for academic and other non-commercial purposes.“
  - Was das bedeutet [Eigene Überlegung, Lizenztext von Creative Commons nicht gelesen: nicht geprüft]: Nicht-kommerzielle Nutzung ist erlaubt. Die Quellenangabe ist Pflicht. Abgeleitete Daten, etwa eine Zuordnungstabelle Zelle → Land, müssen bei Weitergabe unter derselben Lizenz stehen (ShareAlike). Rohdaten und Ableitungen dürfen öffentlich gezeigt werden, wenn Quelle und Lizenz genannt sind.
  - **Nicht verwechseln:** Der Fachartikel steht unter CC BY-NC 4.0 (Crossref), das R-Paket unter „GPL (>= 2)“ [Volltext, CRAN-Handbuch S. 1]. Welche Lizenz für die im R-Paket mitgelieferten Daten gilt: nicht geprüft.

## 6. Python-Zugriff

- Es gibt kein offizielles Python-Paket (keines gefunden). Das offizielle Werkzeug ist das R-Paket `cshapes` mit `cshp(date = NA, useGW = TRUE, dependencies = FALSE)` [Volltext, CRAN-Handbuch S. 2].
- In Python reicht GeoJSON oder Shapefile mit `geopandas`, geladen über die gemeinsame Ladelogik `aleph/core/io.py` [Eigene Überlegung].
- **Spalten der 2.0-Datei:** Beim Anbieter ist keine Spaltenbeschreibung der ausgelieferten Datei belegt. Die Kodieranleitung nennt `gwcode, statename, startdate, enddate, status, ruledby, capname, caplong, caplat, area_sqkm, b_def, fid, geom_id` [Volltext, Codebook S. 2]. Die Drittkopie hat dagegen `cntry_name, area, capname, caplong, caplat, gwcode, gwsdate, gwsyear, gwsmonth, gwsday, gwedate, gweyear, gwemonth, gweday` [Dritt]. Welche Spalten in der ETH-Datei wirklich stehen: nicht geprüft.

## 7. Passung zu ALEPH (Frage 5)

- **Zeitraum:** Nur 2013–2019 abgedeckt (7 von 13 Jahren, 84 von 156 Monaten). 2020–2025 fehlen ganz. [Belegt durch Abschnitt 3; Rechnung eigene]
- **Takt:** Tagesgenaue Gültigkeit lässt sich leicht auf Monate oder Jahre abbilden (Stand z. B. am Monatsersten oder zur Jahresmitte). Das wäre ein Vorteil gegenüber dem festen Natural-Earth-Stand von 2022. [Eigene Überlegung]
- **Zuordnung von 0,25°-Zellen:**
  - Das ist grundsätzlich möglich, aber nicht erprobt.
  - Kleinstaaten: Die GW-Liste setzt eine Bevölkerung über 250 000 voraus [Volltext, S. 4]. Die GW-Fassung führt daher viele Weltbank-Kleinstaaten nicht als eigene Einheit; in der Drittkopie fehlen z. B. Andorra, Liechtenstein, Monaco und San Marino. Eine Ausnahme für 22 Mikrostaaten gibt es nur in der COW-Fassung [Volltext, Fußnote 7, S. 16].
  - Abhängige Gebiete sind nur mit über 250 000 Einwohnern enthalten [Volltext, S. 5].
  - In welches Polygon Kleinstaaten und kleinere Gebiete fallen (Nachbarland oder keines): nicht geprüft.
- **Abgleich mit Weltbank-ISO3:**
  - CShapes 2.0 führt `gwcode` bzw. COW-Codes, **keine ISO3-Codes**. Keine Spalte mit ISO-Code ist belegt: Die Datenseite erwähnt ISO laut Hilfsmodell nicht, und die Spaltenlisten oben enthalten keinen. Ältere Versionen 0.x hatten ISO-Codes (Changelog, Kosovo- und Südsudan-Einträge) [Hilfsmodell].
  - Eine Abbildung GW → ISO3 wäre mit einer fremden Umschlüsselung möglich, z. B. dem Python-Paket `country_converter`, das „GWcode - Gledisch & Ward numerical codes“ als Klassifikation nennt [Dritt, Hilfsmodell: https://github.com/IndEcol/country_converter]. Wie vollständig und richtig diese Tabelle für alle 217 Weltbank-Länder ist: nicht geprüft.
  - Bekannte Eigenheiten der GW-Liste, z. B. „German Federal Republic“ (260) ab 1990 und „Yemen (Arab Republic of Yemen)“ (678) [Dritt], müssten von Hand geprüft werden.
- **Verhältnis zu Natural Earth [Eigene Überlegung]:** Beide ordnen Abspaltungsgebiete (Abchasien, Donbass, Bergkarabach) dem Mutterstaat zu. Unterschiede gibt es bei Somaliland, Nordzypern und Westsahara: Natural Earth führt sie als eigene Einheiten, CShapes nach Drittkopie nicht. Der Vorteil von CShapes wäre die richtige Krim-Zuordnung vor und nach März 2014. Genau das ist aber nur an der Drittkopie gesehen.

## 8. Bekannte Schwächen

- Das Ende 2019 ist für ALEPH das wichtigste Ausschlusskriterium. [Volltext/Hilfsmodell, Abschnitt 3]
- Änderungen unter 100 × 100 km werden nicht erfasst [Volltext, S. 7]. Kriegsbedingte Änderungen ohne Vertrag werden ignoriert [Volltext, S. 8].
- Standarddaten sind teils Platzhalter (1. Januar oder Monatserster) [Volltext, Codebook S. 3].
- Die Angaben zum Zeitraum sind uneinheitlich (2017 / 2018 / 2019 je nach Dokument, Abschnitt 1). Ein richtiges Spalten-Codebuch fehlt, und die Kodieranleitung enthält „?“-Platzhalter.
- Die Genauigkeit der Linien ist undokumentiert (Abschnitt 5).
- Kleinstaaten fehlen in der GW-Fassung (Abschnitt 7).

## 9. Rolle in ALEPH

Hilfsdatensatz (Geometrie-Referenz), wie Natural Earth. Denkbar nur als **Prüfquelle** für 2013–2019: Wie viele Zellen würden sich in Russland/Ukraine ändern, wenn die Krim bis März 2014 zur Ukraine gezählt wird? Nicht als Hauptquelle der Ländergrenzen. [Eigene Überlegung]

## 10. Datenmenge

- Datendateien 2.0: Größe nicht geprüft.
- Zum Vergleich [Anbieter-Verzeichnisliste, Hilfsmodell]: älteres Shapefile `cshapes_0.6.zip` 6,3 MB; Distanztabellen `cshapes_2.0_dist_GW.csv` 105 MB und `…_COW.csv` 115 MB (für ALEPH nicht nötig).
- Für ALEPH genügt eine Datei für die ganze Welt, das Fokusgebiet verursacht keinen Mehraufwand. [Eigene Überlegung]

## 11. Empfehlung

**Nicht als Ersatz für Natural Earth einbauen; „später“ höchstens als Prüfquelle für 2013–2019.** Begründung:
1. Endet 2019-12-31; 2020–2025 (6 von 13 Jahren) fehlen, darunter 2022 und 2023.
2. Keine ISO3-Codes; die Verknüpfung mit der Weltbank bräuchte eine fremde Umschlüsselung, die selbst geprüft werden müsste.
3. Kleinstaaten fehlen in der GW-Fassung.
4. Die Lizenz CC BY-NC-SA 4.0 erlaubt die nicht-kommerzielle Hackathon-Nutzung, verlangt aber Quellenangabe und die Weitergabe von Ableitungen unter derselben Lizenz. Das ist strenger als bei Natural Earth (gemeinfrei).
5. Der einzige klare Mehrwert, die zeitlich richtige Krim-Zuordnung 2014, ist nur an einer Drittkopie gesehen.

Falls später gewünscht: GeoJSON der GW-Fassung direkt von der ETH laden (Größe vorher prüfen) und die Zeilen für Russland und Ukraine sowie die Spaltennamen am Original bestätigen.

## 12. Nicht geprüft (Liste)

- Ob die Datendateien `CShapes-2.0.zip/.geojson/.csv` erreichbar sind und wie groß sie sind.
- Welche Spalten die ausgelieferte 2.0-Datei hat; ob irgendein ISO-Code enthalten ist.
- Krim-Zuordnung ab 2014-03-18, die Flächen, Taiwan, Kosovo, Somaliland, Nordzypern und Westsahara **am Originaldatensatz der ETH**. Alles das stammt aus einer ArcGIS-Kopie mit unbekanntem Eigentümer.
- Maßstab, Lagegenauigkeit und Vereinfachung der Grenzlinien.
- Ob es eine Fortschreibung nach 2019 gibt (nur nicht gefunden).
- Ob das R-Paket Daten nach 2019 enthält („1886-today“ in der Paketbeschreibung).
- Vollständigkeit und Richtigkeit einer Umschlüsselung GW → ISO3 (`country_converter`) für die 217 Weltbank-Länder.
- Der Wortlaut des CC-BY-NC-SA-4.0-Lizenztextes (Folgerungen oben sind eigene Deutung).
- **Nur über Hilfsmodell gelesen (kein Volltext im Sinne von CLAUDE.md):** Datenseite https://icr.ethz.ch/data/cshapes/ (Zeitraum-Satz, Formate, Lizenzsatz, Zitierform), Publikationsseite https://icr.ethz.ch/publications/cshapes-2/, ChangeLog.txt, Crossref-JSON, CRAN-Übersichtsseite, Essex-Repositoriumsseite, die Verzeichnislisten, die ArcGIS-Abfragen, country_converter-README.
- **Im Original selbst gelesen (Volltext):** Artikel-PDF (Essex-Repositorium), „Codebook“-PDF der ETH, CRAN-Referenzhandbuch `cshapes.pdf`.
