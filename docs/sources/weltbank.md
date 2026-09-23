# Steckbrief: Weltbank-Indikatoren (World Bank Open Data / World Development Indicators)

Stand der Recherche: 2026-09-23. Erstellt vom Agenten „datenquellen-scout".

Kennzeichnung in diesem Dokument:
- **[Anbieter]** = Angabe stammt direkt von der Weltbank (data.worldbank.org, datahelpdesk, datacatalog, API), mit Link.
- **[Dritt]** = Angabe stammt von einer Drittquelle (Fachartikel, Blog, Bibliotheks-Dokumentation), nicht von der Weltbank selbst.
- **[Eigene Überlegung]** = eigene Rechnung oder Schlussfolgerung des Scouts, keine Herstellerangabe.
- „nicht geprüft" = konnte nicht belegt werden.

Hinweis zur Methode: Alle Angaben wurden über die offiziellen Weltbank-Webseiten und die REST-API (nur Metadaten-Abfragen einzelner Indikatoren, keine Massendaten) recherchiert. Es wurden **keine Rohdaten heruntergeladen** und keine Downloads gestartet, wie vom Auftraggeber verlangt. Die genannten Mengen- und Größenangaben zum Zeitraum 2013–2025 sind eigene Überschlagsrechnungen auf Basis offizieller Eckwerte (Zahl der Volkswirtschaften, Zahl der Indikatoren), keine tatsächliche Downloadmessung.

---

## 1. Name und Anbieter

- **Name:** World Development Indicators (WDI), ausgeliefert über „World Bank Open Data" und die World Bank Indicators API (Version 2).
- **Anbieter:** The World Bank Group (Development Data Group). [Anbieter: https://data.worldbank.org/]
- **Offizielle Seiten:**
  - Portal: https://data.worldbank.org/
  - Datensatz-Katalogeintrag WDI: https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators
  - API-Dokumentation (Einstieg): https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
  - API Basic Call Structure: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures
  - Lizenz-/Zugangsübersicht (Data Catalog): https://datacatalog.worldbank.org/public-licenses
  - Terms of Use for Datasets: https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets
  - Länder-/Regionsklassifikation: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups
  - WDI Quartals-Release-Notes (aktuellster geprüfter Stand): https://datatopics.worldbank.org/world-development-indicators/release-note/jan-2026.html

## 2. Inhalt

Was gemessen wird, hängt vom gewählten Indikator ab (WDI umfasst laut Anbieter über 1.500 Indikatoren [Anbieter: Data-Catalog-Eintrag oben]). Für ALEPH relevant sind mindestens die folgenden, mit ihrem offiziellen Indikator-Code, Namen und Einheit, jeweils gegen die Live-API geprüft:

| Indikator-Code | Name (Anbieter) | Einheit | Beleg |
|---|---|---|---|
| `NY.GDP.MKTP.CD` | GDP (current US$) | laufende US-Dollar | [Anbieter: https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD?format=json] |
| `NY.GDP.MKTP.KD.ZG` | GDP growth (annual %) | Prozent, auf Basis konstanter Preise von 2015 | [Anbieter: https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.KD.ZG?format=json] |
| `NE.TRD.GNFS.ZS` | Trade (% of GDP) | Prozent des BIP, Summe aus Warenexporten und -importen sowie Dienstleistungen | [Anbieter: https://api.worldbank.org/v2/indicator/NE.TRD.GNFS.ZS?format=json] |
| `SP.POP.TOTL` | Population, total | Personen (de-facto-Bevölkerung, Jahresmitte) | [Anbieter: https://api.worldbank.org/v2/indicator/SP.POP.TOTL?format=json] |
| `SP.POP.GROW` | Population growth (annual %) | Prozent, exponentielle Jahreswachstumsrate | [Anbieter: https://api.worldbank.org/v2/indicator/SP.POP.GROW?format=json] |

Die ersten drei Codes (BIP, BIP-Wachstum, Handel) decken die vom Auftraggeber geforderten Mindestbereiche „BIP" und „Außenhandel" ab; `SP.POP.TOTL`/`SP.POP.GROW` decken „Bevölkerung" ab. `NY.GDP.MKTP.KD.ZG` und `SP.POP.GROW` sind zusätzlich als Kontrollvariablen für Theorieprüfung relevant (ARCHITECTURE.md Abschnitt 8 nennt ausdrücklich „Bevölkerungswachstum" und „Konjunktur" als mögliche Kontrollvariablen). Für die in Abschnitt 8 genannte Ressourcenfluch-Theorie wären zusätzlich rohstoffspezifische Indikatoren nötig (z. B. Erz-/Brennstoffexportanteile); diese wurden hier nicht recherchiert, da nicht ausdrücklich angefragt – **nicht geprüft, Nachtrag bei Bedarf**. [Eigene Überlegung]

Datenherkunft: laut Anbieter aus den Statistiksystemen der Mitgliedsländer und amtlich anerkannten internationalen Quellen zusammengestellt (z. B. UN Population Division für Bevölkerung, ILO für Arbeitsmarkt), nicht von der Weltbank selbst erhoben. [Anbieter: WDI-Suchergebnis-Zusammenfassung des Data Catalog]

## 3. Räumliche Auflösung und Abdeckung

- **Keine Rasterauflösung.** Die Daten existieren ausschließlich auf **Länderebene** (Volkswirtschaften), nicht als Gitterzellen. Das ist bei Wirtschaftsdaten inhärent so: Es gibt keine Rohmessung „BIP pro 0,25°-Zelle", sondern nur nationale (und teils subnationale, hier nicht behandelte) Statistikaggregate.
- **Verbindlich laut ARCHITECTURE.md Abschnitt 4:** „Zweite räumliche Ebene: Verwaltungseinheiten (Länder, später Regionen). Wirtschaftsdaten wie BIP oder Handel gibt es nur auf dieser Ebene. Sie werden dort verknüpft und **nie künstlich auf Gitterzellen verteilt**." Dieser Steckbrief hält sich strikt daran: Die Weltbank-Indikatoren werden in ALEPH mit Länderpolygonen verknüpft, nicht auf das 0,25°-Raster interpoliert oder aufgeteilt.
- **Abdeckung:** Die Weltbank klassifiziert **217 Volkswirtschaften** (Länder und Gebiete), aufgeteilt in sieben Weltregionen; Aggregate wie „World" oder Einkommensgruppen zählen laut der Klassifikationsseite nicht zusätzlich zu diesen 217. [Anbieter: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups] Der Data-Catalog-Eintrag zur WDI spricht davon, dass „mehr als 200 Länder und Territorien" abgedeckt werden – vereinbar mit der 217er-Angabe. [Anbieter: https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators] Nicht alle 217 Einträge sind souveräne UN-Mitgliedstaaten (einige sind Gebiete/Territorien); wie viele ALEPH-Länderpolygone (Natural Earth, ARCHITECTURE.md Abschnitt 10) sich 1:1 zuordnen lassen, ist **nicht geprüft**.

## 4. Zeitliche Auflösung und verfügbarer Zeitraum

- **Jährlich.** Die meisten WDI-Indikatoren sind Jahreswerte; einzelne Wirtschafts-/Finanzindikatoren werden laut Anbieter quartalsweise aktualisiert (Aktualisierungsrhythmus der Datenbank, nicht zwingend die Frequenz jedes einzelnen Indikators). [Anbieter/Websuche-Zusammenfassung: WDI-Datenbank wird quartalsweise, manche Reihen häufiger aktualisiert]
- **Verfügbarer Gesamtzeitraum laut Data Catalog:** 1960 bis 2025. [Anbieter: https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators]
- **Für ALEPH (2013–2025, Entscheidung E3):** vollständig im verfügbaren Bereich, mit Einschränkung: Die aktuellsten ein bis zwei Jahre sind für viele Indikatoren und Länder noch vorläufig oder fehlen (siehe Abschnitt 8, „Bekannte Schwächen").
- **Verbindlich laut ARCHITECTURE.md Abschnitt 4:** „Jahresdaten (z. B. BIP) bleiben jährlich und werden nur mit Jahresaggregaten verglichen." Die Weltbank-Indikatoren werden in ALEPH **nicht** auf Monate verteilt oder interpoliert; sie bleiben Jahreswerte und werden nur gegen andere Jahresaggregate (z. B. Jahresmittel von Nachtlicht) gestellt.

## 5. Zugang

- **Frei, ohne Konto, ohne Token.** Die offizielle API-Dokumentation stellt ausdrücklich fest: „API keys and other authentication methods are no longer necessary to access the API." [Anbieter: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation]
- **Beispiel-Endpunkt:** `https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json` (Struktur laut Anbieter-Dokumentation). [Anbieter: ebd.]
- **Rate-Limits:** Von der Weltbank selbst **nicht dokumentiert**; die offizielle Dokumentation äußert sich dazu nicht. [Anbieter: ebd., keine Angabe gefunden] Ein Drittartikel (kein Weltbank-Dokument) berichtet aus praktischer Erfahrung von Fehlern ab etwa 1.000 Anfragen pro Minute von derselben IP-Adresse und empfiehlt eine kleine Pause zwischen Anfragen. [Dritt: https://themineworks.com/blog/world-bank-api-python-2025/] Für ALEPH (wenige Indikatoren, jährliche Aktualisierung, keine Massenabfrage in Echtzeit) ist das nach eigener Einschätzung unkritisch. [Eigene Überlegung]
- **Variablen in `.env`:** **Keine.** Da kein Konto und kein Token nötig sind, entfällt ein Eintrag in `.env` für diese Quelle. Sollte sich das künftig ändern (z. B. Umstieg auf ein Kontingent-Verfahren), wäre `WORLDBANK_API_KEY` ein naheliegender Variablenname – aktuell aber nicht erforderlich. [Eigene Überlegung]
- **SDMX-Alternative:** Die Weltbank bietet zusätzlich einen SDMX-API-Zugang an. [Anbieter: https://datahelpdesk.worldbank.org/knowledgebase/articles/1886701-sdmx-api-queries] Für ALEPH nicht näher geprüft, da die JSON/REST-API ausreicht — nicht geprüft im Detail.

## 6. Lizenz und Nutzungsbedingungen

- **Lizenz: CC BY 4.0 (Creative Commons Attribution 4.0 International)**, als Standardlizenz für von der Weltbank selbst erzeugte, offen verfügbare Datensätze: „CC-BY 4.0, with the additional terms below, is the default license for all Datasets produced by the World Bank itself and distributed as open data." [Anbieter: https://datacatalog.worldbank.org/public-licenses] Lizenztext: https://creativecommons.org/licenses/by/4.0
- **Kommerzielle Nutzung ist erlaubt:** Die Lizenz gestattet ausdrücklich „copy, modify and distribute data in any format for any purpose, including commercial use". [Anbieter: https://datacatalog.worldbank.org/public-licenses] ALEPH ist nicht-kommerziell, das ist damit erst recht gedeckt.
- **Zitierpflicht: ja.** CC BY 4.0 verlangt Namensnennung und Kennzeichnung von Änderungen. Die Weltbank gibt eine konkrete Zitierform vor: „The World Bank: [Dataset name]: [Data source (if known)]." [Anbieter: https://datacatalog.worldbank.org/public-licenses bzw. https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets]
- **Zusatzbedingungen:** Neben CC BY 4.0 gelten laut Data Catalog verbindliche Zusatzklauseln, u. a. eine Streitschlichtungsklausel (nicht-bindende Mediation, danach Schiedsverfahren nach UNCITRAL-Regeln in englischer Sprache). [Anbieter: https://datacatalog.worldbank.org/public-licenses] Für ALEPH als nicht-kommerziellen Hackathon-Prototyp ohne erwartbare Streitfälle praktisch nicht relevant, aber der Vollständigkeit halber notiert.
- **Achtung – Begriffsverwirrung zwischen zwei Weltbank-Seiten:** Die allgemeine Seite „Terms of Use for Datasets" (https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets) verweist an einer Stelle unspezifisch auf generelle Weltbank-Nutzungsbedingungen, die für *andere* Materialien (z. B. Publikationen, Fotos) eine nicht-kommerzielle Beschränkung vorsehen. Diese generelle Beschränkung gilt laut der spezifischeren, direkt einschlägigen Data-Catalog-Lizenzseite **nicht** für die als Open Data gekennzeichneten Datensätze wie WDI – dort gilt CC BY 4.0 mit ausdrücklicher Erlaubnis kommerzieller Nutzung. [Anbieter: https://datacatalog.worldbank.org/public-licenses, spezifischer als die allgemeine Terms-of-Use-Seite] Für einen vollständig zweifelsfreien Beleg wäre ein direkter, unveränderter Blick auf den Volltext beider Seiten sinnvoll; die hier zitierten Auszüge stammen aus automatisierten Seitenzusammenfassungen (WebFetch), nicht aus manuell gegengelesenem Originaltext: **Einschränkung der Belegqualität, nicht abschließend geprüft.**
- **Öffentliche Anzeige der Rohdaten auf der ALEPH-Karte: ja, zulässig.** CC BY 4.0 erlaubt laut Definition ausdrücklich Vervielfältigung und Verbreitung in jedem Format („copy, modify and distribute data in any format for any purpose"). [Anbieter: https://datacatalog.worldbank.org/public-licenses] Es wurde keine Einschränkung gefunden, die eine öffentliche Kartendarstellung von WDI-Rohwerten (z. B. BIP-Zahl pro Land und Jahr) untersagt. Bedingung ist die Namensnennung „The World Bank" plus Datensatzname, wie oben zitiert. Für `META`: **Anzeige von Rohwerten (nicht nur Zusammenfassungen) zulässig, mit Quellenangabe.**

## 7. Python-Zugriff und Dateiformat

- **Direkter REST/JSON-Zugriff:** Die API liefert Ergebnisse als JSON (Standard) oder XML; keine Bibliothek nötig, ein einfacher HTTP-GET reicht. [Anbieter: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation]
- **`wbgapi`** – von der Weltbank selbst vorgestelltes/angekündigtes Python-Paket („Introducing WBGAPI: A new python package for accessing World Bank data", Weltbank-Datenblog). [Anbieter-nah/Dritt: https://blogs.worldbank.org/en/opendata/introducing-wbgapi-new-python-package-accessing-world-bank-data, Quellcode https://github.com/tgherzog/wbgapi] Fragt standardmäßig die WDI-Datenbank ab, unterstützt pandas-Ausgabe, Mehrfachauswahl von Ländern/Indikatoren/Jahren. Installation: `pip install wbgapi`.
- **`wbdata`** – weiteres, von der Weltbank unabhängiges Drittpaket für denselben API-Zugriff. [Dritt: https://pypi.org/project/wbdata/]
- **Dateiformat bei Bulk-Download über das Webportal:** CSV oder Excel (ganze WDI-Datenbank als Download: 269,7 MB CSV bzw. 77,9 MB Excel, für alle 1.500+ Indikatoren und alle Jahre seit 1960). [Anbieter: https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators] Für ALEPH sinnvoller ist der gezielte API-Abruf einzelner Indikatoren statt des Komplett-Downloads (siehe Abschnitt 9, Datenmenge).
- Gemäß ARCHITECTURE.md Abschnitt 5 nutzt jeder Layer dieselbe Ladelogik (`aleph/core/io.py`); für diese Quelle bedeutet das einen schlanken HTTP-Abrufer statt `earthaccess` (das ist nur für NASA-Erdbeobachtungsdaten vorgesehen, Abschnitt 5).

## 8. Bekannte Schwächen

- **Veröffentlichungsverzug:** Laut dem aktuellsten geprüften WDI-Quartalsupdate (Januar 2026) sind viele Indikatoren nur bis 2023 vollständig, manche bis 2024 „für einige Länder"; die Dokumentation warnt ausdrücklich, dass Schätzwerte für Länder mit schwacher nationaler Datenlage einen hohen Unsicherheitsgrad tragen und nicht als direkte Beobachtungen zu interpretieren sind. [Anbieter: https://datatopics.worldbank.org/world-development-indicators/release-note/jan-2026.html] **Folgerung für ALEPH:** Die Jahre 2024 und erst recht 2025 sind zum Stand dieser Recherche (September 2026) für viele Länder noch nicht final; ALEPH sollte die neuesten ein bis zwei Jahre als „vorläufig/unsicher" kennzeichnen und nicht wie abgeschlossene Beobachtungsjahre behandeln. [Eigene Überlegung]
- **Datenlücken bei einzelnen Ländern, besonders Konflikt- und fragile Staaten:** Eine wissenschaftliche Arbeit dokumentiert, dass für Länder wie Afghanistan, Irak, Myanmar, Syrien und Jemen BIP-Daten über teils Jahrzehnte fehlen oder unzuverlässig sind, weil die amtliche Statistik durch Konflikt gestört ist. [Dritt: arXiv-Preprint „From Revolution to Ruin: An Empirical Analysis Yemen's State Collapse", https://arxiv.org/pdf/2507.08512, sowie allgemeiner Befund aus der Recherche] Das betrifft genau die Länder, die für ALEPHs Fokusgebiete und Konflikt-Theorien (ARCHITECTURE.md Abschnitt 4a, 8) am interessantesten wären – dort ist der Wirtschaftskontext also am dünnsten.
- **Imputation bei Aggregaten:** Für Gruppen- und Weltsummen füllt die Weltbank fehlende Länderwerte modellbasiert auf, führt aber laut eigener Methodikseite keine Schätzung durch, wenn mehr als ein Drittel der Werte im Bezugsjahr fehlt. [Anbieter: WDI Sources and Methods, https://datatopics.worldbank.org/world-development-indicators/sources-and-methods.html — Seite selbst nicht im Volltext gelesen, nur über Suchergebnis-Zusammenfassung erschlossen: **nicht abschließend geprüft**] Für einzelne Länderwerte (nicht Aggregate) ist unklar, ob und wie oft Imputation stattfindet – **nicht geprüft**.
- **Revisionen:** Die Weltbank aktualisiert und revidiert die WDI-Datenbank quartalsweise; bereits veröffentlichte Jahre können sich rückwirkend ändern (z. B. nach Rebasierung von Preisindizes oder Methodikwechseln). [Anbieter: Release-Note-Seiten, allgemeiner Hinweis aus Websuche] Für ALEPHs Reproduzierbarkeit folgt daraus: Der Abrufzeitpunkt sollte mit den Rohdaten gespeichert werden, damit spätere Revisionen nachvollziehbar bleiben. [Eigene Überlegung, analog zur Empfehlung im VNP46A3-Steckbrief]
- **Kein Raster, keine Subnationaldaten in diesem Datensatz:** Innerstaatliche Unterschiede (z. B. Wirtschaftskraft einer Region innerhalb eines großen Landes) sind mit WDI nicht abbildbar; das ist eine strukturelle Grenze, keine behebbare Lücke.
- **Sensorwechsel-Äquivalent:** entfällt (keine Satellitenmessung); stattdessen können sich Erhebungsmethoden einzelner nationaler Statistikämter über die Zeit ändern (z. B. Volkszählungsjahre vs. Fortschreibungen bei Bevölkerungsdaten) – **nicht länderweise geprüft**.

## 9. Rolle in ALEPH

**Ausdrücklich kein Erkennungs-Layer.** ARCHITECTURE.md Abschnitt 5 listet „Wirtschaft: Weltbank-Indikatoren (jährlich, pro Land)" explizit unter „Nicht als Erkennungs-Layer, sondern als **Kontext**". Diese Quelle löst also selbst keine Anomalie-Meldungen aus und wird nicht auf das 0,25°-Raster gebracht (Abschnitt 3 oben).

Konkrete Rolle laut ARCHITECTURE.md Abschnitt 8 (Verknüpfung und Theorie-Register):
- **Kontrollvariable bei Theorieprüfungen:** „Bekannte gemeinsame Treiber (z. B. Bevölkerungswachstum, Konjunktur) werden, wo möglich, als Kontrollvariablen berücksichtigt." Dafür eignen sich direkt `SP.POP.GROW` (Bevölkerungswachstum) und `NY.GDP.MKTP.KD.ZG` (Konjunktur/BIP-Wachstum).
- **Wirtschaftskontext für die Ressourcenfluch-Theorie** (Abschnitt 8, Tabelle: „Rohstoffreichtum erhöht Konfliktrisiko"), dort als „Weltbank-Rohstoffdaten" genannt – für rohstoffspezifische Indikatoren (z. B. Erz- oder Brennstoffexportanteile) wäre eine gezielte Nachrecherche mit eigenen Indikator-Codes nötig, hier nicht Teil des Auftrags. [Eigene Überlegung]
- **Anzeige in der Untersuchungsansicht** einer Anomalie (Abschnitt 10: „…Nachrichten (GDELT) und Konfliktereignisse (ACLED) für Region und Zeitraum") als zusätzlicher Länderkontext (BIP, Handel, Bevölkerung im betroffenen Land und Jahr), nicht als eigenständige Anomaliequelle.

## 10. Datenmenge

**Tatsächliche Downloadmenge für 2013–2025, wie vom Auftraggeber angefragt (eigene Überschlagsrechnung, keine tatsächliche Downloadmessung):**

- Zeitraum 2013–2025 = 13 Jahre.
- Länder/Volkswirtschaften: 217 [Anbieter, siehe Abschnitt 3].
- Mindest-Indikatorenset (BIP, Handel, Bevölkerung): 3 Codes (`NY.GDP.MKTP.CD`, `NE.TRD.GNFS.ZS`, `SP.POP.TOTL`).
  → **3 × 217 × 13 = 8.463 mögliche Datenpunkte** (Obergrenze; tatsächlich weniger, weil bei vielen Ländern einzelne Jahre fehlen, siehe Abschnitt 8). [Eigene Überlegung, eigene Rechnung]
- Erweitertes Set inkl. der zwei Kontrollvariablen (BIP-Wachstum, Bevölkerungswachstum): 5 Codes
  → **5 × 217 × 13 = 14.105 mögliche Datenpunkte.** [Eigene Überlegung, eigene Rechnung]
- **Geschätzte Dateigröße:** Ein Datenpunkt als CSV-Zeile (Ländercode, Indikatorcode, Jahr, Wert) benötigt überschlägig 40–80 Byte. Bei 8.463 bis 14.105 Zeilen ergibt das rund **0,3 bis 1,1 MB unkomprimiert**, deutlich unter 1 MB in den meisten Formatierungen; als JSON mit Feldnamen-Overhead entsprechend mehr, aber immer noch im ein- bis niedrigen zweistelligen MB-Bereich. [Eigene Überlegung, eigene Rechnung, keine tatsächliche Messung]
- **Einordnung:** Selbst die *komplette* WDI-Datenbank (über 1.500 Indikatoren, alle Länder, alle Jahre seit 1960) ist als CSV nur 269,7 MB groß [Anbieter: https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators]. Das ist etwa **15.000-mal kleiner** als die 4.108 GB (4,01 TB) des einzelnen Satelliten-Layers VNP46A3 für denselben Zeitraum 2013–2025 (siehe `docs/sources/vnp46a3.md`, Abschnitt 15). Die Weltbank-Indikatoren sind damit im ALEPH-Datenhaushalt eine **vernachlässigbare Nebengröße**, keine Belastung für Speicher oder Ladezeit.
- Für ein einzelnes Fokusgebiet (z. B. Ukraine, Entscheidung E9) reduziert sich die Menge auf 1 Land × 3–5 Indikatoren × 13 Jahre = 39–65 Datenpunkte – praktisch nicht der Rede wert.

## 11. Empfehlung

**Einbauen**, als Kontext-/Kontrollvariablen-Layer, kein Erkennungs-Layer. Begründung:
1. Zugang ist frei, ohne Konto, ohne Token, keine `.env`-Einträge nötig – geringster Aufwand aller bisher recherchierten Quellen.
2. Lizenz (CC BY 4.0) erlaubt öffentliche Kartenanzeige der Rohwerte mit einfacher Quellenangabe, auch kommerziell – für ALEPH als nicht-kommerziellen Prototyp unproblematisch.
3. Datenmenge ist verschwindend klein (siehe Abschnitt 10) – kein Infrastrukturaufwand, passt zu CLAUDE.md („keine unnötig komplexe Infrastruktur").
4. Direkt nützlich für die in ARCHITECTURE.md Abschnitt 8 vorgesehenen Kontrollvariablen (Bevölkerungswachstum, Konjunktur) und den Länderkontext in der Untersuchungsansicht.

**Bedingungen für den Einbau:**
1. Strikt auf Länderebene verknüpfen, niemals auf das 0,25°-Raster verteilen (ARCHITECTURE.md Abschnitt 4, siehe Abschnitt 3 dieses Steckbriefs).
2. Jahreswerte bleiben Jahreswerte, kein Verteilen auf Monate (ARCHITECTURE.md Abschnitt 4, siehe Abschnitt 4 dieses Steckbriefs).
3. Die jeweils letzten ein bis zwei Jahre (aktuell 2024/2025) als „vorläufig/unsicher" kennzeichnen, nicht als abgeschlossene Beobachtung (Abschnitt 8).
4. Abrufdatum mit den Rohdaten speichern, wegen möglicher rückwirkender Revisionen (Abschnitt 8).
5. Für Länder mit bekannten Datenlücken (Konflikt-/fragile Staaten, Abschnitt 8) den fehlenden Wert explizit als „keine Daten" zeigen, nicht stillschweigend überspringen oder interpolieren – passt zu CLAUDE.md „Unsicherheit immer ausweisen".
6. In `META`: Lizenz CC BY 4.0, Zitierform „The World Bank: [Dataset name]: [Data source]", Rohwert-Anzeige zulässig, Evidenzstufe der reinen Zahlenwerte `beobachtet` (amtliche Statistik, keine Modellprojektion) – mit dem Zusatz, dass einzelne Länderwerte selbst bereits Schätzungen nationaler Statistikämter sein können.

## 12. Nicht geprüft (Liste)

- Vollständiger Wortlaut der WDI „Sources and Methods"-Seite zur Imputation (nur über Suchergebnis-Zusammenfassung erschlossen).
- Exakte Deckungsgleichheit der 217 Weltbank-Volkswirtschaften mit den in ALEPH genutzten Länderpolygonen (Natural Earth, ARCHITECTURE.md Abschnitt 10).
- Offiziell dokumentiertes Rate-Limit der API (Weltbank selbst nennt keines; nur Dritt-Erfahrungswert).
- Rohstoffspezifische Indikator-Codes für die Ressourcenfluch-Theorie (Abschnitt 8) – bewusst nicht recherchiert, da außerhalb des engeren Auftrags („BIP, Handel, Bevölkerung").
- Genaue Formulierung des Volltexts der allgemeinen „Terms of Use for Datasets"-Seite im Widerspruch/Verhältnis zur spezifischeren Data-Catalog-Lizenzseite (nur automatisierte Zusammenfassungen gelesen, siehe Warnhinweis in Abschnitt 6).
- SDMX-API im Detail.
- Ob und wie oft einzelne Länderwerte (nicht nur Aggregate) durch die Weltbank imputiert/geschätzt statt roh gemeldet werden.
