# Steckbrief: Natural Earth, Admin 0 – Countries (Ländergrenzen)

Stand der Recherche: 2026-09-25. Recherche vom Agenten „datenquellen-scout“, Messungen an den echten Dateien und Entscheidungen von der Hauptsitzung (Abschnitte 13 und 14, gekennzeichnet mit **[Messung]**).

**Kurz: Quelle** Natural Earth · **Version** 5.1.1 (Dateien vom Mai 2022) · **Maßstab** 1:10m · **Sichtweise** Standarddatei (de facto), keine POV · **Lizenz** gemeinfrei · **Download** https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip, geladen am 2026-09-25 (SHA-256 `ce1ac703…a7f6`) · **Schlüssel zur Weltbank** `land_iso3` = ISO_A3_EH plus Kosovo → XKX, Jersey/Guernsey → CHI · **Code** `aleph/layers/natural_earth.py`.

Kennzeichnung in diesem Dokument:
- **[Anbieter]** = Angabe stammt von Natural Earth selbst (naturalearthdata.com oder das offizielle GitHub-Repository `nvkelso/natural-earth-vector`, dort Changelog, Release-Seiten und Beiträge des Betreuers Nathaniel V. Kelso), mit Link.
- **[Dritt]** = Angabe stammt von einer Drittquelle, z. B. Meldungen fremder Nutzer im GitHub-Issue-Tracker des Anbieters oder Dokumentation fremder Bibliotheken. Solche Meldungen sind Beobachtungen Einzelner, keine Anbieteraussage.
- **[Eigene Überlegung]** = Schlussfolgerung des Scouts, nicht vom Anbieter belegt.
- **[Messung]** = von der Hauptsitzung an den geladenen Dateien gemessen (2026-09-25).
- „nicht geprüft" = konnte nicht belegt werden.

Hinweis zur Methode (Scout): Alle Seiten wurden mit dem Werkzeug WebFetch gelesen. Es liefert den Seitentext über ein Hilfsmodell; die Zitate unten sind dessen Wiedergabe, auf ausdrückliche Anfrage „wörtlich". Sie sind **nicht** manuell am Originaltext gegengelesen. Vor einer Verwendung in Präsentation oder Veröffentlichung einmal im Original nachschlagen (CLAUDE.md, Regel zu `verifiziert_umfang`). Es wurde **nichts heruntergeladen**; alle Angaben über den Dateiinhalt stammen von Anbieterseiten oder Issue-Meldungen, nicht aus eigener Messung.

---

## 1. Name und Anbieter

- **Name:** Natural Earth, Thema „Admin 0 – Countries" (Dateiname `ne_<maßstab>_admin_0_countries`), in drei Maßstäben 1:10m, 1:50m, 1:110m.
- **Anbieter:** Natural Earth, ein gemeinfreier Kartendatensatz, betreut von Nathaniel V. Kelso und Tom Patterson, unterstützt von NACIS (North American Cartographic Information Society). [Anbieter: https://github.com/nvkelso/natural-earth-vector] Die Rolle von NACIS stammt nur aus einer Suchergebnis-Zusammenfassung (https://nacis.org/initiatives/natural-earth/, Seite selbst nicht geöffnet): nicht geprüft.
- **Offizielle Seiten:**
  - Produktseite 1:10m: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/
  - Produktseite 1:50m: https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries-2/
  - Produktseite 1:110m: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/
  - Nutzungsbedingungen: https://www.naturalearthdata.com/about/terms-of-use/
  - Umgang mit umstrittenen Grenzen: https://www.naturalearthdata.com/about/disputed-boundaries-policy/
  - Quell-Repository mit Changelog und Issues: https://github.com/nvkelso/natural-earth-vector

## 2. Inhalt

- **Was es ist:** Länderpolygone mit Attributen (Namen, Codes), keine Messung. Anbieter: „There are 258 countries in the world. Greenland as separate from Denmark. Most users will want this file instead of sovereign states, though some users will want map units instead when needing to distinguish overseas regions of France." [Anbieter: Produktseiten, s. o.]
  - Achtung: Der Satz mit „258 countries" steht **wortgleich auf allen drei Maßstabsseiten** (auch in der jeder Zip-Datei beiliegenden `.README.html`, dort gelesen). Gezählt: 1:10m 258, 1:50m 242, 1:110m 177 Einträge. Die Angabe passt also nur zu 1:10m. [Messung]
- **Metropole vs. abhängige Gebiete:** „Countries distinguish between metropolitan (homeland) and independent and semi-independent portions of sovereign states. If you want to see the dependent overseas regions broken out (like in ISO codes, see France for example), use map units instead." [Anbieter: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/]
- **Weitere Attribute:** „Each country is coded with a world region that roughly follows the United Nations setup. Includes some thematic data from the United Nations, U.S. Central Intelligence Agency, and elsewhere." [Anbieter: ebd.] Laut einem alten Forumsbeitrag des Betreuers stammen Bevölkerungs- und BIP-Felder (`pop_est`, `gdp_md` o. ä.) „mostly from 2009" [Anbieter: https://www.naturalearthdata.com/forums/topic/thematic-codes/, Beitrag von 2010]. Ob das für Version 5.1.1 noch gilt: nicht geprüft. **Für ALEPH diese Thema-Felder nicht verwenden**, dafür gibt es die Weltbank-Daten. [Eigene Überlegung]
- **Einheit:** entfällt (Geometrie in Längen-/Breitengrad). Koordinatensystem: EPSG:4326 (WGS 84) in allen drei Maßstäben. [Messung]
- **Variante „_lakes":** Zu jedem Maßstab gibt es `ne_<m>_admin_0_countries_lakes` („without boundary lakes"), bei der große Grenzseen aus den Länderflächen ausgeschnitten sind. [Anbieter: Produktseiten 10m/50m, Download-Beschriftung „without boundary lakes"] Für die Zuordnung von Nachtlicht-Zellen ist die Standarddatei ohne `_lakes` passender, da Seezellen dann einem Land zugeordnet bleiben. [Eigene Überlegung]

### Countries, Sovereignty, Map Units, Subunits (Frage 2)

Laut Seite „Admin 0 – Details" [Anbieter: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-details/]:
- **Sovereignty:** „There are 209 sovereign states in the world, though only 199 issue passports." – „Sovereign States do not distinguish between the metropolitan and semi-independent portions of a state or it's constituent countries. Passports are issued by sovereign states, not countries."
- **Countries:** siehe oben (Metropole getrennt von unabhängigen und halbunabhängigen Teilen; Grönland getrennt von Dänemark).
- **Map units:** „Not usually useful but some FIPS and ISO codes refer to groups of individual admin-0 territories by these designations." Beispiele laut Seite: US-Pazifikinseln, Französisch-Guayana.
- **Map subunits:** „Countries subdivided by non-contiguous units" (z. B. Korsika getrennt vom französischen Festland). „These rarely correspond to actual administrative divisions but rather highlight geographical regions that are not continuous but are part of the same country."
- Die Seite nennt außerdem 298 Map Units und 360 Subunits (nur in der Hilfsmodell-Zusammenfassung gesehen, nicht wörtlich zitiert: nicht geprüft).
- Die Features-Seite fasst zusammen: „dependencies (French Polynesia), map units (U.S. Pacific Island Territories) and sub-national map subunits (Corsica versus mainland Metropolitan France)". [Anbieter: https://www.naturalearthdata.com/features/]

Folgerung für ALEPH [Eigene Überlegung]: Die Weltbank führt manche abhängigen Gebiete als eigene Volkswirtschaft (z. B. vermutlich Französisch-Polynesien, Neukaledonien; nicht geprüft). Ob „countries" diese Gebiete als eigene Polygone enthält oder ob dafür „map units" nötig sind, entscheidet die Messung (Abschnitt 13). „Countries" ist der empfohlene Ausgangspunkt, weil der Anbieter ihn für die meisten Nutzer empfiehlt.

## 3. Räumliche Auflösung und Abdeckung (Maßstäbe, Frage 2)

Anbieterbeschreibung der drei Maßstäbe [Anbieter: https://www.naturalearthdata.com/downloads/]:
- **1:10m** („Large scale data"): „The most detailed. Suitable for making zoomed-in maps of countries and regions. Show the world on a large wall poster."
- **1:50m** („Medium scale data"): „Suitable for making zoomed-out maps of countries and regions. Show the world on a tabloid size page."
- **1:110m** („Small scale data"): „Suitable for schematic maps of the world on a postcard or as a small locator globe."

Kleine Länder im groben Maßstab:
- Eine ausdrückliche Liste, welche kleinen Länder oder Inseln in 1:110m als Polygon fehlen, wurde auf den Anbieterseiten **nicht gefunden**: nicht geprüft.
- Indirekter Hinweis: Für 1:110m und 1:50m gibt es eigens die Punktdatei `admin_0_tiny_countries`: „Some countries don't read well on thematic choropleth data maps. Color code the dots with the same information as the larger country polygons to communicate data that would otherwise be lost." [Anbieter: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-details/] Die Hilfsmodell-Zusammenfassung nennt für 110m den Filter `ScaleRank <= 2` (nicht wörtlich gesehen: nicht geprüft).
- Abdeckung: global. [Anbieter: Maßstabsbeschreibungen]

Bezug zum ALEPH-Raster [Eigene Überlegung]: Eine 0,25°-Zelle ist ca. 28 km breit (ARCHITECTURE.md Abschnitt 4). Dafür reicht grundsätzlich 1:50m; 1:10m ist aber so klein (Abschnitt 11), dass es keinen Grund gibt, auf Genauigkeit zu verzichten. 1:110m ist für eine Zuordnung ungeeignet, weil der Anbieter es selbst als „schematisch" beschreibt und kleine Länder dort in eine eigene Punktdatei ausgelagert sind.

## 4. Zeitliche Auflösung, Version und Aktualität (Frage 1)

- **Keine Zeitreihe.** Natural Earth liefert einen einzigen Stand der Grenzen je Version, keine Grenzen je Jahr. [Eigene Überlegung aus den Produktseiten; eine Zeitdimension wird nirgends erwähnt]
- **Version der Dateien: 5.1.1.** Alle drei Produktseiten nennen „version 5.1.1". [Anbieter: Produktseiten] Die Versionsdateien im Repository enthalten ebenfalls „5.1.1": https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/10m_cultural/ne_10m_admin_0_countries.VERSION.txt und …/110m_cultural/ne_110m_admin_0_countries.VERSION.txt [Anbieter].
- **Neueste Release auf GitHub: v5.1.2.** Tag-Liste: v5.1.2 und v5.1.1 am 13. Mai 2022, v5.1.0 am 5. Mai 2022, v5.0.1 am 18. März 2022, v5.0.0 am 8. Dezember 2021, v4.1.0 am 23. Mai 2018, v4.0.0 am 27. Oktober 2017. [Anbieter: https://github.com/nvkelso/natural-earth-vector/tags] Eine Abfrage der Seite `releases/latest` nannte für v5.1.2 „May 13, 2023"; Tag-Liste und Changelog sagen 2022. Vermutlich ein Lesefehler des Hilfsmodells [Eigene Überlegung]; Jahr im Original prüfen.
- **Changelog nennt zusätzlich „2022-06-02: Version 5.2.0"**, aber die Datei `VERSION` im Repository enthält „5.2.0-pre", und es gibt keinen Tag v5.2.0. [Anbieter: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/CHANGELOG, https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/VERSION] 5.2.0 betrifft laut Changelog Meeres-Beschriftungsflächen („marine polygon geographic label areas"), nicht Admin 0. Für ALEPH maßgeblich ist damit **5.1.1** (Dateistand) bzw. v5.1.2 (letzte Release, laut Changelog nur ein Nachtrag zu `ne_50m_admin_0_boundary_lines_disputed_areas` und eine Schreibweise).
- **Changelog-Einträge zu Admin 0** [Anbieter: CHANGELOG, Link oben; Zitate aus der Hilfsmodell-Wiedergabe]:
  - 5.1.2 (2022-05-13): „Add missing TLC point-of-view to `ne_50m_admin_0_boundary_lines_disputed_areas` theme."
  - 5.1.1 (2022-05-12): „Ensure 'empty' text fields have minimum length of 1 char for PostGIS compatibility." (kein Grenzinhalt)
  - 5.1.0 (2022-05-04): „Add top-level-country (TLC) point-of-view (POV) with shapefile, cleanup the existing ISO POV, add shapefile export for ISO point-of-view"; außerdem „Mark Kosovo as recognized by fewer countries and by TLC (but not ISO)", „Mark Taiwan as recognized by itself and TLC", „Add Sir Creek dispute between Pakistan and India", „Add FRA to Metropolitan France at country level as iso_a3_eh".
  - 5.0.1 (2022-03-17): „Ukraine's boundary POV updated for current events, leaving only Morocco and Sweden showing two ambiguous boundaries"; „Kosovo is not recognized by India POV"; „Adds Siachen Glacier between India and Pakistan as disputed for most POVs". Das Hilfsmodell gab zusätzlich wieder: „Donbass split in two, recognized as countries by Russia" (nicht gesondert bestätigt).
  - 5.0.0 (2021-12-07): „Adds support for alternate points of view in admin-0 related themes"; „Provides easy alternate download of `ne_10m_admin_0_countries` themes preassembled for the 31 different viewpoints"; „Rename Macedonia to North Macedonia" (und Swasiland zu Eswatini).
  - 4.1.0 (2018-05-21): „Restored missing polygons for Bosnia & Herzegovina's Republic Srpska".
  - 4.0.0 (2017-10-15): „New geometry between Ukraine and Russia for Crimea, other disputed areas"; „Serbia and Kosovo are no longer disputed adm0"; „Rename Czechia".
  - Datumsangaben im Changelog (4.0.0: 2017-10-15; 4.1.0: 2018-05-21; 5.0.1: 2022-03-17) weichen um Tage von den Tag-Daten ab. Unkritisch, aber bei Zitaten die Quelle nennen.
- **Aktualität:** Die letzte inhaltliche Änderung an Admin 0 liegt im Mai 2022; seitdem gab es keine neue Release (Stand der Tag-Liste). [Anbieter: Tag-Liste] Grenzänderungen danach sind also nicht enthalten. [Eigene Überlegung]
- **Folge für den Untersuchungszeitraum 2013–2025** [Eigene Überlegung]: ALEPH legt einen Grenzstand von 2022 über alle 13 Jahre. Wo sich die tatsächliche Kontrolle geändert hat (z. B. Krim ab 2014, Gebiete in der Ostukraine ab 2014 und 2022, Bergkarabach 2020/2023), ordnet die Datei Zellen für manche Jahre anders zu, als die Kontrolle damals war. Das muss in `META` als bekannte Schwäche stehen und bei Länder-Zeitreihen dieser Länder ausgewiesen werden.

## 5. Zugang (Frage 4)

- **Frei, ohne Konto, ohne Token.** „No permission is needed to use Natural Earth." [Anbieter: https://www.naturalearthdata.com/about/terms-of-use/]
- **Variablen in `.env`:** keine.
- **Download-Adressen:**
  - Die Produktseiten verlinken z. B. `https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip` (entsprechend `50m`, `110m`). [Anbieter: Produktseiten]
  - Diese Links scheitern laut einem Nutzer beim Abruf per Programm mit „HTTP Error 406: Not Acceptable"; funktionierend sei die CDN-Adresse `https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_1_states_provinces.zip` (nach Muster also `https://naciscdn.org/naturalearth/<m>/cultural/ne_<m>_admin_0_countries.zip`). Das Issue ist offen, eine Antwort des Betreuers wurde nicht gesehen. [Dritt: https://github.com/nvkelso/natural-earth-vector/issues/903, 3. April 2024] Dass naciscdn.org die offizielle Verteiladresse ist, steht auf keiner gelesenen Anbieterseite: nicht geprüft. Die Hauptsitzung prüft beim Laden, welche Adresse funktioniert.
  - GitHub (Quelle der Dateien): Shapefiles unter `10m_cultural/`, `50m_cultural/`, `110m_cultural/`, GeoJSON unter `geojson/` im Repository https://github.com/nvkelso/natural-earth-vector. [Anbieter]
- **Dateinamen „countries" in allen drei Maßstäben** [Anbieter: Produktseiten und Repository-Verzeichnisse]:
  - `ne_10m_admin_0_countries.zip` (4,7 MB), `ne_10m_admin_0_countries_lakes.zip` (4,87 MB)
  - `ne_50m_admin_0_countries.zip` (781,78 KB), `ne_50m_admin_0_countries_lakes.zip` (799,31 KB)
  - `ne_110m_admin_0_countries.zip` (210,08 KB), `ne_110m_admin_0_countries_lakes.zip`
  - Im Repository je Shapefile die Bestandteile `.shp .shx .dbf .prj .cpg` sowie `.README.html` und `.VERSION.txt`. [Anbieter: https://github.com/nvkelso/natural-earth-vector/tree/master/110m_cultural]

## 6. Lizenz und Nutzungsbedingungen (Frage 3)

- **Gemeinfrei (Public Domain):** „All versions of Natural Earth raster + vector map data found on this website are in the public domain." [Anbieter: https://www.naturalearthdata.com/about/terms-of-use/]
- **Quellenangabe nicht verpflichtend:** „No permission is needed to use Natural Earth. Crediting the authors is unnecessary." [Anbieter: ebd.]
- **Empfohlene Zitierform:** „Made with Natural Earth" oder ausführlich „Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com." [Anbieter: ebd.]
- **Haftungsausschluss:** „The authors provide Natural Earth as a public service and are not responsible for any problems relating to accuracy, content, design, and how it is used." [Anbieter: ebd.] Die Seite nennt außerdem lizenzierte Beiträge u. a. der Washington Post, der Europäischen Kommission, XNR Productions und International Mapping Associates zur Erstellung der Grundkarte (nur als Zusammenfassung gelesen; ob das die Gemeinfreiheit der ausgelieferten Daten einschränkt, sagt die Seite laut Zusammenfassung nicht: nicht geprüft).
- **Nicht-kommerzielle Nutzung:** erlaubt (gemeinfrei, jede Nutzung). **Öffentliche Anzeige von Rohdaten:** zulässig. Für `META`: Rohdaten anzeigen zulässig; Quellenangabe freiwillig, ALEPH nennt sie trotzdem („Made with Natural Earth"), weil ALEPH jede Quelle ausweist. [Eigene Überlegung, gestützt auf die Zitate]

## 7. Sichtweisen (Point of View, POV) und umstrittene Gebiete (Frage 5)

**Standarddatei (ohne POV) = de facto:**
- „Natural Earth draws boundaries of sovereign states according to de facto ("in fact") status rather than de jure ("by law")." [Anbieter: https://www.naturalearthdata.com/about/disputed-boundaries-policy/, „Last updated 2022-02-27"]
- Produktseite: „Natural Earth Vector draws boundaries of countries according to defacto status. We show who actually controls the situation on the ground." Nutzer könnten das Thema „disputed areas" darüberlegen („mashup"), um die eigene politische Sicht abzubilden. [Anbieter: Produktseiten]
- Maßstab des Anbieters für „de facto souverän": „We consider a de facto sovereign state (aka country or nation) to have a government that sustains administrative power over their own physical territory, including some combination of making and enforcing laws for its people, minting money, collecting taxes, raising armies, with longevity, self determination, and being desirous of recognition by other sovereign states." [Anbieter: Disputed-Boundaries-Seite]

**POV-Varianten:**
- Seit Version 5 (Changelog: 5.0.0 vom 2021-12-07): „Starting in version 5, we introduced optional 'point-of-view' (POV) or 'worldview' for administrative geographies." [Anbieter: Disputed-Boundaries-Seite, Changelog]
- Bedeutung: „Optional point-of-view (POV) variants show the worldview for several dozen countries according to de jure boundaries (as prescribed by the home country's law and/or local conventions) and their global alliances." [Anbieter: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/]
- Liste der Sichtweisen laut Anbieter (Kürzel der Felder): „Argentina (ar), Bangladesh (bd), Brazil (br), China (cn), Egypt (eg), France (fr), Germany (de), Greece (gr), India (in), Indonesia (id), Israel (il), Italy (it), Japan (jp), Morocco (ma), Nepal (np), Netherlands (nl), Pakistan (pk), Palestine (ps), Poland (pl), Portugal (pt), Russia (ru), Saudi Arabia (sa), South Korea (ko), Spain (es), Sweden (se), Taiwan (tw), Turkey (tr), United Kingdom (gb), United States (us), Vietnam (vn), ISO (iso)". [Anbieter: Disputed-Boundaries-Seite] Seit 5.1.0 zusätzlich „TLC" (top-level-country). [Anbieter: Changelog]
- **Dateinamen** (Muster laut Anbieter „like ne_10m_admin_0_countries_arg for Argentina"): auf der 10m-Downloadseite `ne_10m_admin_0_countries_<code>.zip` mit den Codes arg, bdg, bra, chn, deu, egy, esp, fra, gbr, grc, idn, ind, iso, isr, ita, jpn, kor, mar, nep, nld, pak, pol, prt, pse, rus, sau, swe, tlc, tur, twn, ukr, usa, vnm. [Anbieter: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/] Dieselben 33 Namen als GeoJSON unter `geojson/` im Repository. [Anbieter: https://github.com/nvkelso/natural-earth-vector/tree/master/geojson]
  - Unstimmigkeit beim Anbieter: Die Feldliste enthält Ägypten, aber keine Ukraine; die Dateiliste enthält eine Ukraine-Datei (`ukr`). Auf der Seite wurden 33 Dateien gezählt (31 Länder + ISO + TLC). Nicht weiter geklärt.
- **Maßstäbe:** POV-Dateien für `countries` wurden **nur für 1:10m** gefunden. Die Seiten für 1:50m und 1:110m sowie die Repository-Verzeichnisse `50m_cultural/` und `110m_cultural/` zeigen keine `countries_<code>`-Dateien. [Anbieter: https://www.naturalearthdata.com/downloads/50m-cultural-vectors/, Produktseite 110m, Repository-Verzeichnisse] Einschränkung: GitHub zeigt große Verzeichnisse evtl. gekürzt, und eine ausdrückliche Anbieteraussage „nur 10m" gibt es nicht. Der Changelog nennt nur „preassembled" Downloads für `ne_10m_admin_0_countries`.
- Technisch: Die Sichtweisen werden über Felder `fclass_*` (z. B. `fclass_iso`, `fclass_tlc`) gesteuert. [Anbieter: Changelog 5.0.0/5.1.0, Seite „Breakaway, Disputed Areas"]

**Einzelne umstrittene Gebiete in der Standarddatei:**

| Gebiet | Was der Anbieter sagt | Wie es in der Standarddatei `countries` erscheint |
|---|---|---|
| Somaliland | „A notable edge case is Somaliland which is treated as a sovereign state in Natural Earth because it meets the rubric above." [Anbieter: Disputed-Boundaries-Seite] | eigener Eintrag SOL, ISO_A3 und ISO_A3_EH „-99“; Hargeisa → Somaliland. Kein Weltbank-Gegenstück. [Messung] |
| Kosovo | „There are other states without any representation at the UN, including Taiwan, Western Sahara, Northern Cyprus, and Kosovo" [Anbieter: ebd.]; 4.0.0: „Serbia and Kosovo are no longer disputed adm0"; 5.1.0: „recognized by fewer countries and by TLC (but not ISO)" [Anbieter: Changelog] | eigener Eintrag KOS, ISO_A3 und ISO_A3_EH „-99“, WB_A3 „KSV“ (die Weltbank-API nutzt XKX); Pristina → Kosovo. [Messung] |
| Taiwan | gleiches Zitat wie Kosovo; 5.1.0: „Mark Taiwan as recognized by itself and TLC" [Anbieter] | eigener Eintrag TWN (ISO_A3 TWN); Taipeh → Taiwan. Die Weltbank führt Taiwan nicht. [Messung] |
| Westsahara | gleiches Zitat wie Kosovo; als Beispiel auf der Seite „Breakaway, Disputed Areas" genannt [Anbieter: https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-breakaway-disputed-areas/] | geteilt: Laayoune → Marokko, Tifariti → eigener Eintrag „Western Sahara“ (ESH). In der Sicht DEU gehören 259 Zellen mehr zur Westsahara. [Messung] |
| Nordzypern | gleiches Zitat wie Kosovo; Beispiel auf der Disputed-Areas-Seite [Anbieter] | eigener Eintrag CYN, Codes „-99“; Nord-Nikosia → Northern Cyprus. [Messung] |
| Krim | 4.0.0: „New geometry between Ukraine and Russia for Crimea, other disputed areas" [Anbieter: Changelog]; in der TLC-Sicht Beispiel für „Admin-0 claim area (eg Crimea between Ukraine and Russia)" [Anbieter: Changelog 5.1.0] | **Russland** (Simferopol → Russia). Donezk, Luhansk, Mariupol, Melitopol dagegen → Ukraine, obwohl sie im Mai 2022 nicht von der Ukraine kontrolliert wurden. Grund ist die Anbieterregel: „de facto“ bezieht sich auf de-facto-souveräne Staaten; Abspaltungsgebiete bleiben beim Staat, zu dem sie völkerrechtlich gehören, die Krim ist als Annexion Russland zugeschlagen (Hinweis des Plausibilitäts-Prüfers, 2026-09-25). 53 Zellen gehören in der Sicht DEU zur Ukraine statt zu Russland. [Messung] |
| Kaschmir | Beispiel auf der Disputed-Areas-Seite („From Kashmir to the Elemi Triangle…"); Siachen-Gletscher als umstritten (5.0.1) [Anbieter] | Siachen-Gletscher eigener Eintrag KAS („-99“); Srinagar → Indien, Muzaffarabad → Pakistan. [Messung] |
| Palästina | „There are also non-member 'observers' to the UN like the Holy See and Palestine." [Anbieter: Disputed-Boundaries-Seite]; Palästina ist eigene POV-Sicht | Eintrag „Palestine“ mit ISO_A3 PSE; Ramallah und Gaza → Palestine. Passt zur Weltbank („West Bank and Gaza“, PSE). [Messung] |
| Abspaltungsgebiete (u. a. Südossetien, Abchasien, Donezk, Luhansk, Arzach laut Zusammenfassung) | „…several of the geographically small and politically isolated polities (often with proxy military involvement by another sovereign state instead of self determination) are instead represented as breakaway polygons and lines in auxiliary downloads." [Anbieter: Disputed-Boundaries-Seite] | also **nicht** als eigene Länder in `countries`, sondern in Zusatzdateien (`admin_0_breakaway_disputed_areas`). Punktproben: Stepanakert → Aserbaidschan, Tskhinvali und Suchumi → Georgien, Tiraspol → Moldau. [Messung] |

Folgerung für ALEPH [Eigene Überlegung]: Die Standarddatei (de facto) passt am besten zu Nachtlicht, weil Licht dort gemessen wird, wo tatsächlich verwaltet und versorgt wird. Sie passt aber **nicht** zwingend zur Zuordnung der Weltbank, die ihre Zahlen nach eigenen Regeln einem Land zuschreibt (Beispiel: der Befund in weltbank.md Abschnitt 14, dass BIP-pro-Kopf- und Bevölkerungsreihe für Russland/Ukraine ab 2014 um ca. 2,3 Mio. Menschen auseinanderlaufen). Eine POV-Datei „iso" könnte näher an der Weltbank-Sicht liegen; das ist eine Vermutung und nicht geprüft. **[Messung]:** Die ISO-Datei ist für die Zuordnung ungeeignet, weil sie umstrittene Flächen weglässt (Lücken, Abschnitt 13). Wo de-facto-Polygon und Weltbank-Zuordnung auseinanderfallen, muss die Länder-Zeitreihe diesen Unterschied ausweisen, statt ihn stillschweigend zu übergehen.

## 8. Code-Felder (Frage 6)

**Offizielle Felddokumentation:** Eine Tabelle mit der Bedeutung aller Felder wurde beim Anbieter **nicht gefunden**. Ein Nutzer fragte 2015 genau danach („There are no table/field description?", auch nach der Bedeutung von „-99"); das Issue ist weiterhin offen, eine Antwort wurde nicht gesehen. [Dritt/Anbieter-Tracker: https://github.com/nvkelso/natural-earth-vector/issues/153] Jede Datei hat eine `.README.html` im Repository; deren Inhalt wurde nicht gelesen: nicht geprüft.

Was belegt ist:
- **SOV_A3, ADM0_A3, GU_A3, SU_A3:** „The following 4 columns are unique to the Natural Earth administrative-0 coding system, but somewhat follow the ISO 3 digit alpha codes: sov_a3, adm_a3, gu_a3, su_a3" [Anbieter: Forumsbeitrag des Betreuers, 9. März 2010, https://www.naturalearthdata.com/forums/topic/thematic-codes/]. Die Namenszuordnung zu den Ebenen (SOV = sovereignty, ADM0 = country, GU = geo/map unit, SU = subunit) ergibt sich aus den Namen und Abschnitt 2, ist aber vom Anbieter nicht ausdrücklich definiert: [Eigene Überlegung], nicht geprüft.
- **Wichtig:** Diese vier Codes sind **keine** ISO-Codes. Beispiel laut Nutzermeldung: Palästina `SU_A3 = PSX`, ISO `PSE`. [Dritt: Issue #112]
- **ISO_A3:** Name deutet auf ISO 3166-1 alpha-3. Eine Anbieterdefinition wurde nicht gefunden: nicht geprüft.
- **ISO_A3_EH:** Vom Betreuer selbst erklärt: „The `iso_a3_eh` column was added as a way to bridge this difference and be easier, though incorrect, for most downstream users". Gemeint ist der Unterschied zwischen ISO-Zuschnitt und Natural-Earth-Einheiten; „eh" sei „American English / California slang for kinda right, kinda wrong, but moving on". [Anbieter: Issue #237, eröffnet von nvkelso am 13. November 2017, https://github.com/nvkelso/natural-earth-vector/issues/237] Changelog 5.0.0 und 5.1.0: „Add FRA to Metropolitan France at country level as iso_a3_eh". [Anbieter: CHANGELOG]
- **WB_A3:** Eine Anbieteraussage zu Bedeutung oder Herkunft (z. B. „World Bank code") wurde **nicht gefunden**. **[Messung]:** WB_A3 enthält teils veraltete Codes (ROM statt ROU, ZAR statt COD, TMP statt TLS, ADO statt AND, IMY statt IMN, WBG statt PSE, KSV statt XKX) und „-99“ bei Norwegen, Gibraltar, den Britischen Jungferninseln und Nauru, obwohl die Weltbank alle vier führt; nur 206 der 217 Weltbank-Codes kommen vor. Ungeeignet. Dass WB_A3 der Weltbank-Code sei, ist naheliegend, aber nicht geprüft. Ebenso nicht geprüft, ob die Werte dem heutigen Weltbank-Stand entsprechen (z. B. Kosovo `XKX`). Eine Websuche verwies auf ein fremdes Projekt mit einer Umschreibung „Kosovo KSV → XKX" beim Verknüpfen; das ist eine Drittquelle ohne Anbieterbezug und ein Hinweis, dass WB_A3 für Kosovo nicht `XKX` sein könnte – nicht geprüft, Messung.
- **Weltbank-Zuordnung allgemein:** Eine Aussage des Anbieters zur Zuordnung zu Weltbank-Ländern wurde nicht gefunden.

**Fälle von „-99" in ISO_A3** (Frage 6; alles Nutzermeldungen im Issue-Tracker des Anbieters, keine Anbieteraussage):
- **Frankreich:** „France is returning ISO_A2 and ISO_A3 of "-99" when it should instead be "FR" and "FRA"" in `geojson/ne_10m_admin_0_countries.geojson`. Offen, keine Antwort gesehen. [Dritt: https://github.com/nvkelso/natural-earth-vector/issues/695, 9. März 2022]
- **Norwegen:** In `ne_50m_admin_0_countries.geojson`: `ISO_A2` „-99", `ISO_A2_EH` „NO", `ISO_A3` „-99", `ISO_A3_EH` „NOR", `ISO_N3` „-99", `ISO_N3_EH` „578". Der Melder schreibt, PR #446 habe das für Frankreich behoben, Norwegen sei übersehen worden. Offen. [Dritt: https://github.com/nvkelso/natural-earth-vector/issues/947, 7. März 2025] (Ob PR #446 in einer Release steckt: nicht geprüft; die Frankreich-Meldung #695 ist trotzdem offen.)
- **Liste für 1:10m:** Ein Nutzer meldete für die 10m-Datei `ISO_A2`/`ISO_A3` = -99 bei: „Dhekalia, France, Somaliland, Norway, USNB Guantanamo Bay, Brazilian I., N. Cyprus, Cyprus U.N. Buffer Zone, Siachen Glacier, Baikonur, Akrotiri, Southern Patagonian Ice Field, Bir Tawil, Indian Ocean Ter., Coral Sea Is., Spratly Is., Clipperton I., Ashmore and Cartier Is., Bajo Nuevo Bank, Serranilla Bank, Scarborough Reef". Geschlossen, Begründung nicht gesehen. [Dritt: https://github.com/nvkelso/natural-earth-vector/issues/675, 19. Januar 2022, also vor 5.1.x]
- Ältere Meldungen: Frankreich, Kosovo, Norwegen ohne ISO-Codes in 10m (2015, geschlossen, Meilenstein v4.0.0) [Dritt: Issue #131]; Norwegen `ISO_A3_EH` = -99 (2018, geschlossen, Meilenstein v5.0.0) [Dritt: Issue #252].
- Eine Begründung des Betreuers, **warum** Frankreich und Norwegen -99 tragen, wurde in keiner gelesenen Seite im Wortlaut gefunden. Der Zusammenhang mit dem Zuschnitt (Frankreich-Metropole ohne Überseegebiete, Norwegen ohne Svalbard) ist eine naheliegende Vermutung [Eigene Überlegung], nicht geprüft.

Folgerung [Eigene Überlegung]: **`ISO_A3` nicht als Verknüpfungsschlüssel verwenden.** Kandidat ist `ISO_A3_EH` (vom Betreuer ausdrücklich für einfache Weiterverarbeitung gedacht), ergänzt um `ADM0_A3` und eine kleine, handgepflegte Ausnahmeliste (mit Herkunft und Datum, wie die Kachel-Referenzliste in ARCHITECTURE.md Abschnitt 5). Welches Feld am besten zu den 217 Weltbank-Codes passt, entscheidet allein die Messung (Abschnitt 13).

## 9. Python-Zugriff und Dateiformat

- **Formate:** Shapefile (ZIP) auf naturalearthdata.com; im Repository zusätzlich GeoJSON (`geojson/`). Der Changelog nennt für Releases außerdem SQLite und GeoPackage als Paketformate. [Anbieter: Produktseiten, Repository, CHANGELOG 5.2.0]
- **Laden:** einfacher HTTP-Download einer ZIP-Datei über die gemeinsame Ladelogik (`aleph/core/io.py`), kein `earthaccess` (das ist nur für NASA-Daten, ARCHITECTURE.md Abschnitt 5). Lesen z. B. mit `geopandas` (Shapefile oder GeoJSON). [Eigene Überlegung; geopandas-Doku nicht gelesen: nicht geprüft]
- **Drittpaket, nur zur Kenntnis:** `cartopy.io.shapereader.natural_earth(resolution, category, name)` lädt Natural-Earth-Shapefiles, z. B. `name='admin_0_countries'`. [Dritt: https://scitools.org.uk/cartopy/docs/v0.22/reference/generated/cartopy.io.shapereader.natural_earth.html, nur Suchergebnis-Zusammenfassung] Für ALEPH nicht nötig.
- **Zuordnung Zelle → Land** [Eigene Überlegung, Vorschlag, nicht getestet]: Zellmittelpunkt im Polygon ist die einfachste Regel, verliert aber Küstenzellen, deren Mittelpunkt im Meer liegt, und Kleinstaaten, die keinen Zellmittelpunkt enthalten. Robuster ist ein Flächenanteil je Zelle und Land (Zelle kann mehreren Ländern anteilig gehören). Die Wahl gehört in `META`, und die Zahl der Länder ohne einzige Zelle sollte gemessen und ausgewiesen werden.

## 10. Bekannte Schwächen (Frage 7)

- **Codes nicht durchgängig ISO:** -99 in `ISO_A3` u. a. bei Frankreich und Norwegen gemeldet, teils seit Jahren offen (Abschnitt 8). [Dritt, Issue-Tracker]
- **Keine offizielle Feldbeschreibung** (Issue #153 offen). [Dritt]
- **Stand 2022, keine Zeitreihe:** letzte Release Mai 2022; keine Grenzstände je Jahr (Abschnitt 4). [Anbieter: Tag-Liste; Folgerung eigene Überlegung]
- **De-facto-Sicht:** Grenzen nach tatsächlicher Kontrolle zum Stand der Version; das kann von der Zuordnung der Weltbank abweichen (Abschnitt 7). [Anbieter: Policy; Folgerung eigene Überlegung]
- **Download-Links der Webseite** scheitern laut Nutzer beim Programm-Abruf (HTTP 406); CDN-Adresse als Ausweg (Abschnitt 5). [Dritt: Issue #903]
- **Viele offene Issues:** Die Repository-Seite zeigte 439 offene Issues (Stand des Abrufs 2026-09-25). [Anbieter: https://github.com/nvkelso/natural-earth-vector] Einzelne davon zu Admin-0-Geometrien wurden nicht durchgesehen: nicht geprüft.
- **Grobe Maßstäbe schematisch:** 1:110m laut Anbieter nur für „schematic maps"; Kleinstaaten dort in eigener Punktdatei (Abschnitt 3).
- **Produktseiten nennen „Known Problems: None."** [Anbieter] – steht im Gegensatz zu den offenen Issues. [Eigene Überlegung]
- **Ein ungültiger Umriss** (Ägypten, 1:10m), siehe Abschnitt 13. [Messung]

## 11. Rolle in ALEPH

**Hilfsdatensatz (Geometrie-Referenz)**, weder Erkennungs-Layer noch Kontext-Layer mit eigenen Werten. Zweck: Jede 0,25°-Zelle einem Land (bzw. anteilig mehreren) zuordnen, damit Nachtlicht je Land und Jahr zusammengefasst und mit der Weltbank-Tabelle (`laender/weltbank.parquet`, ISO3-Codes) verknüpft werden kann (ARCHITECTURE.md Abschnitt 4: zweite räumliche Ebene „Verwaltungseinheiten"). Keine hochaufgelöste Kartendarstellung. [Eigene Überlegung, nach Auftrag]

## 12. Datenmenge

- 1:10m: 4,7 MB (ZIP), 1:50m: 781,78 KB, 1:110m: 210,08 KB, jeweils Version 5.1.1. [Anbieter: Produktseiten]
- Eine Zuordnungstabelle Zelle → Land für 1440 × 720 Zellen ist klein (höchstens rund eine Million Zeilen, nur Landzellen nötig). [Eigene Überlegung, nicht gemessen]
- Für ein Fokusgebiet: dieselbe Datei, kein Mehraufwand.

## 13. Messung (Hauptsitzung, 2026-09-25)

Alle Angaben hier: **[Messung]** an den am 2026-09-25 von naciscdn.org geladenen Dateien (Version 5.1.1 laut beiliegender `VERSION.txt`, Server-Datum 13. Mai 2022). Weltbank-Vergleich gegen die Länderliste des Abrufs 2026-09-23 (217 Volkswirtschaften ohne Aggregate).

**Download:** Die CDN-Adresse funktioniert (HTTP 200) für 10m, 50m, 110m und die 10m-POV-Dateien. `ne_50m_admin_0_countries_deu.zip` sowie `ne_10m_admin_0_countries_wb.zip` und `…_un.zip` gibt es nicht (HTTP 403). Die Spalte `ADM0_A3_WB` ist in allen Einheiten „-99“: Eine Weltbank-Sicht gibt es in 5.1.1 nicht.

**Anzahl je Maßstab:** 1:10m 258, 1:50m 242, 1:110m 177 Einträge. `ADM0_A3` ist in allen Dateien eindeutig und nie „-99“.

**Code-Felder gegen die 217 Weltbank-Codes** (1:10m; Treffer / Weltbank-Länder ohne Eintrag / „-99“):

| Feld | Treffer | Weltbank ohne Eintrag | „-99“ |
|---|---|---|---|
| ISO_A3 | 213 | 4 (CHI, FRA, NOR, XKX) | 22 |
| ISO_A3_EH | 215 | 2 (CHI, XKX) | 14 |
| ADM0_A3 | 213 | 4 | 0 |
| WB_A3 | 206 | 11 | 44 |

- **Frankreich und Norwegen:** ISO_A3 = „-99“ bestätigt (in 10m, 50m und 110m). ISO_A3_EH trägt FRA bzw. NOR. WB_A3 hat bei Norwegen ebenfalls „-99“.
- **Gewählt: ISO_A3_EH plus drei Korrekturen** (Kosovo KOS → XKX; Jersey JEY und Guernsey GGY → CHI, weil die Weltbank nur „Channel Islands“ führt). Ergebnis in Spalte `land_iso3`: **alle 217 Weltbank-Länder haben mindestens einen Eintrag.**
- **Mehrere Einträge für einen Weltbank-Code** (werden zusammengefasst): AUS (Australien, Indian Ocean Territories, Coral Sea Islands, Ashmore and Cartier Islands), BRA (Brasilien, Brazilian Island), CHI (Jersey, Guernsey), FRA (Frankreich, Clipperton), KAZ (Kasachstan, Baikonur).
- **34 Einträge ohne Weltbank-Gegenstück.** Mit nennenswerter Bevölkerung (Feld POP_EST der Datei): Taiwan, Somaliland, Westsahara, Nordzypern, Åland; dazu Vatikan, Antarktis, britische/französische/australische/neuseeländische Außengebiete (u. a. Falklandinseln, St. Helena, Cookinseln, Niue, Wallis und Futuna), Militärbasen (Guantánamo, Akrotiri, Dhekelia) und unbewohnte umstrittene Flächen (Siachen, Bir Tawil, Spratly-Inseln, Scarborough-Riff, Bajo Nuevo, Serranilla, Südpatagonisches Eisfeld, Zypern-Pufferzone). Diese Einträge bekommen keine Weltbank-Daten; sie werden nicht still einem Nachbarland zugeschlagen. Ob die Weltbank-Zahlen für Somalia, Zypern, Finnland oder Marokko diese Gebiete einschließen: nicht geprüft.

**Punktproben** (Standarddatei): Kairo → Ägypten, Berlin → Deutschland, Paris → Frankreich, Riad → Saudi-Arabien, 30° N / 40° W (Atlantik) → kein Land. Umstrittene Orte siehe Tabelle in Abschnitt 7; außerdem Cayenne (Französisch-Guayana) → Frankreich, Longyearbyen (Spitzbergen) → Norwegen, Mariehamn → Åland.

**Maßstab auf dem 0,25°-Raster** (Zuordnung über die Zellmitte, 1440 × 720 Zellen):

| | 1:10m | 1:50m | 1:110m |
|---|---|---|---|
| Einträge mit mindestens einer Zelle | 207 von 258 | 200 von 242 | 177 von 177 |
| Weltbank-Länder mit mindestens einer Zelle (Code ISO_A3_EH) | 190 | 188 | 169 |
| Zellen anders als 1:10m | – | 3 034 (0,9 % der Landzellen; 2 723 Land/Meer, 311 anderes Land) | 13 152 (3,8 %; 1 879 anderes Land) |

Bahrain bekommt bei 1:50m keine Zelle, bei 1:10m schon. Bei 1:110m fehlen 48 Weltbank-Länder ganz (auch mit ISO_A3_EH).

**Mit der gewählten Datei und `land_iso3`** bekommen 191 der 217 Weltbank-Länder mindestens eine Zellmitte, 26 keine: Aruba, Andorra, Amerikanisch-Samoa, Antigua und Barbuda, Bermuda, Kanalinseln, Kaimaninseln, Gibraltar, St. Kitts und Nevis, St. Lucia, Liechtenstein, Macau, St. Martin, Monaco, Malediven, Marshallinseln, Nauru, San Marino, Sint Maarten, Seychellen, Turks- und Caicosinseln, Tonga, Tuvalu, St. Vincent und die Grenadinen, Britische und Amerikanische Jungferninseln. Das betrifft die spätere Wahl der Zuordnungsregel (Zellmitte oder Flächenanteil), nicht die Wahl der Quelle.

**Sichtweisen auf dem 0,25°-Raster** (1:10m, Zellmitte):
- Standard gegen **ISO**: 1 128 Zellen anders. Die ISO-Datei lässt 19 Einheiten weg (u. a. Kosovo, Somaliland, Nordzypern, Kaschmir-Flächen), ihre Flächen werden zu Lücken: z. B. 278 Zellen, die in der Standarddatei zu Indien gehören, 206 zu Guyana, 125 zu Pakistan, liegen dann in keinem Land. Für die Zuordnung ungeeignet (Land würde wie Meer aussehen).
- Standard gegen **Deutschland (deu)**: 578 Zellen (0,17 % der Landzellen) anders: Marokko → Westsahara 259, Somaliland → Somalia 226, Russland → Ukraine (Krim) 53, Sudan → keins 17, Baikonur → Kasachstan 14, Nordzypern → Zypern 4, Südpatagonisches Eisfeld → keins 3, Siachen → Indien 2.

**Zellmitten an Flüssen und Küsten:** Ein Punkt in der Stadt Cherson (32,62° O / 46,64° N) liegt in keinem Land, 0,001° neben der Ukraine, vermutlich im Umriss des Dnipro-Ufers (Plausibilitäts-Prüfer). Bei Zuordnung über Zellmitten können also auch in bewohnten Gebieten einzelne Zellen ohne Land bleiben.

**Geometrie:** Im 1:10m-Datensatz ist genau ein Umriss formal ungültig: Ägypten, Randlinie berührt sich selbst bei 35,621° O / 23,139° N (Grenzgebiet zum Sudan). In 1:50m und 1:110m ist nichts ungültig. `make_valid` repariert es ohne Flächenänderung (Unterschied < 1e-13 Grad²). Das Modul repariert nur, wenn die Fläche gleich bleibt (relativ höchstens 1e-9), und schreibt jede Reparatur ins Manifest (`umriss_repariert: ["EGY"]`); sonst bricht es ab.

## 14. Entscheidungen und Empfehlung

**Einbauen**, als Hilfsdatensatz für die Länderzuordnung (Hauptsitzung, 2026-09-25):

1. **Maßstab 1:10m.** Begründung: Für 0,25°-Zellen reicht grundsätzlich auch 1:50m; die Grenzen unterscheiden sich nur in 0,9 % der Landzellen. Aber 1:50m verliert Bahrain ganz und hat keine POV-Dateien, 1:110m verliert 48 Weltbank-Länder. 1:10m kostet nur 4,9 MB (4 930 492 Byte; die Anbieterangabe „4,7 MB“ meint vermutlich MiB), und die Rechnung auf dem 0,25°-Raster dauert Sekunden. Hohe Kartengenauigkeit ist nicht der Grund.
2. **Standarddatei (de facto), keine POV.** Begründung: (a) Es ist die dokumentierte Voreinstellung des Anbieters mit einer offengelegten Regel, keine Sicht eines einzelnen Staates. **Wichtig:** „de facto“ ist die Anbieterregel für de-facto-souveräne Staaten, **nicht** die tatsächliche Kontrolle vor Ort. Abspaltungsgebiete (Ostukraine, Transnistrien, Abchasien, Südossetien, Bergkarabach) liegen beim Mutterstaat, die Krim bei Russland. Das Argument „Nachtlicht misst, wo tatsächlich versorgt wird“ trägt deshalb nur für die Einheiten, die Natural Earth als de-facto-Staaten führt (z. B. Somaliland, Nordzypern, Taiwan, Kosovo), nicht für diese Gebiete. (b) Die ISO-Sicht macht umstrittene Flächen zu Lücken. (c) Eine Weltbank-Sicht gibt es nicht. (d) Keine andere Sicht passt nachweislich besser zur Weltbank, denn deren Gebietszuschnitt ist nicht geprüft. Die Wahl betrifft 578 Zellen im Vergleich zur deutschen Sicht (Abschnitt 13). Einschränkung: Welche Gebiete die Weltbank-Zahlen je Land umfassen (z. B. die Krim, Somaliland, Nordzypern), ist **nicht geprüft**. Die Standarddatei ist zudem ein fester Stand von 2022, der für alle Jahre 2013–2025 gilt: Die Krim liegt auch 2013 bei Russland. Deshalb sollen spätere Länder-Auswertungen für Russland, Ukraine, Marokko, Somalia, Zypern, Indien, Pakistan und China mit und ohne die betroffenen Zellen gerechnet oder gekennzeichnet werden.
3. **Schlüssel `land_iso3`** = ISO_A3_EH plus Korrekturen (Abschnitt 13). ISO_A3 und WB_A3 werden nicht verwendet. Der Betreuer nennt ISO_A3_EH selbst „easier, though incorrect“ (Abschnitt 8); für die Weltbank-Verknüpfung ist es gemessen das Feld mit den meisten Treffern, und jeder Unterschied ist oben aufgeführt.
4. **Nicht verwenden:** die Thema-Felder der Datei (POP_EST, GDP_MD usw.); dafür gibt es die Weltbank-Daten.
5. In `META`: Lizenz gemeinfrei, Quellenangabe freiwillig, ALEPH nennt sie trotzdem („Made with Natural Earth“).

## 15. Nicht geprüft (Liste)

- Welche Gebiete die Weltbank-Reihen je Land umfassen (Krim, Somaliland, Nordzypern, Westsahara, Åland, Überseegebiete Frankreichs). Das entscheidet, ob die Standardsicht zur Weltbank passt.
- Offizielle Bedeutung von `ISO_A3`, `WB_A3`, `SOV_A3`, `GU_A3` (nur der gemeinsame Forumssatz zu sov/adm/gu/su gefunden).
- Begründung des Betreuers für „-99“ bei Frankreich und Norwegen.
- Ob naciscdn.org offiziell ist und dauerhaft funktioniert (am 2026-09-25 funktionierte es).
- Einschränkungen durch lizenzierte Beiträge Dritter (Washington Post u. a.) zur Grundkarte.
- Alle wörtlichen Zitate des Scouts: nur über die Hilfsmodell-Wiedergabe von WebFetch gelesen, nicht manuell am Original gegengelesen. Ausnahme: Die Sätze „There are 258 countries…“, „Natural Earth shows de facto boundaries by default…“ und „Known Problems: None.“ stehen in der `.README.html` der geladenen Dateien (von der Hauptsitzung gelesen).
- Genauigkeit der Grenzlinien selbst (nicht mit einer anderen Quelle verglichen).
