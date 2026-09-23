# ARCHITECTURE.md – Aufbau von ALEPH

Stand: 2026-09-21 · Status: bestätigt

Dieses Dokument beschreibt, wie ALEPH aufgebaut ist. Jede Claude-Code-Sitzung liest es vor Änderungen am Code. Die verbindlichen Arbeitsregeln stehen in `CLAUDE.md`.

---

## 1. Ziel in einem Satz

ALEPH erkennt außergewöhnliche Entwicklungen in globalen Daten aus vielen Bereichen, verknüpft sie mithilfe wissenschaftlicher Theorien, prüft diese Verknüpfungen an Daten und zeigt alles mit Evidenzstufe und Unsicherheit auf einer filterbaren Karte.

## 2. Grundprinzipien

1. **Ein gemeinsamer Takt.** Jede Datenquelle wird auf dasselbe räumliche Raster und dieselbe Zeitachse gebracht. Erst dann wird verglichen.
2. **Eine Ladelogik.** Alle Datenquellen nutzen denselben Lade- und Speicherweg (`aleph/core/`). Datenquellen-spezifischer Code steckt nur im jeweiligen Layer-Modul.
3. **Evidenzstufen sind Pflicht.** Jede Aussage trägt genau eine Stufe:
   - `beobachtet` – direkt in Daten gemessen
   - `statistische Assoziation` – Zusammenhang an unabhängigen Daten getestet
   - `Modellprojektion` – Ergebnis eines Modells mit dokumentierten Annahmen
   - `hypothetisches Szenario` – Was-wäre-wenn, ausdrücklich keine Vorhersage
4. **Keine Scheinpräzision.** Stärke wird in Bändern ausgedrückt (auffällig / stark / extrem), nicht als Punktzahl mit Nachkommastellen. Jede Meldung zeigt, wie gut die Datenlage ist.
5. **Einfache Infrastruktur.** Dateien statt Datenbankserver, klassische Statistik statt Deep Learning, statische Weboberfläche statt Backend.
6. **Prüfbarkeit.** Das System wird regelmäßig blind gegen bekannte Ereignisse getestet (Abschnitt 9).

## 3. Der Weg der Daten

```
Datenquelle
   │  (1) Laden          aleph/layers/<name>.py  + aleph/core/io.py
   ▼
Rohdaten (data/raw/)
   │  (2) Harmonisieren  aleph/core/grid.py
   ▼
Datenwürfel pro Layer (data/cube/<layer>.zarr)   Zeit × Breite × Länge
   │  (3) Erkennen       aleph/detect/     Abweichung vom Normalzustand finden
   │  (3b) Benennen      aleph/classify/   "Anomalie: Waldbrand" oder
   │                                       "Anomalie: unerklärte Veränderung in …"
   ▼
Benannte Anomalien (data/events/events.parquet)  Evidenzstufe: beobachtet
   │  (4) Verknüpfen     aleph/link/  + theories/
   ▼
Verknüpfte Ereignisse (data/events/links.parquet)
   │  (5) Prüfen         aleph/validate/
   ▼
Blindtest-Bericht (reports/)
   │  (6) Darstellen     web/
   ▼
Karte mit Filtern, Zeitreihen, Theorie-Status und Nachrichtenkontext
```

## 4. Gemeinsames Raster und Zeitachse

**Räumlich (Vorschlag):** globales Gitter mit 0,25° Kantenlänge (am Äquator ca. 28 km), 1440 × 720 Zellen.
- Feiner aufgelöste Quellen (z. B. Nachtlicht 500 m) werden pro Zelle zusammengefasst: Mittelwert und Anzahl gültiger Beobachtungen.
- Zweite räumliche Ebene: **Verwaltungseinheiten** (Länder, später Regionen). Wirtschaftsdaten wie BIP oder Handel gibt es nur auf dieser Ebene. Sie werden dort verknüpft und nie künstlich auf Gitterzellen verteilt.

**Zeitlich (Vorschlag):** monatlich.
- Tagesdaten werden zu Monatswerten zusammengefasst.
- Jahresdaten (z. B. BIP) bleiben jährlich und werden nur mit Jahresaggregaten verglichen.

**Speicher:** Datenwürfel als Zarr-Dateien (über `xarray`), Tabellen als Parquet-Dateien, Abfragen mit DuckDB. Kein Datenbankserver. Jeder Datenwürfel hat von Anfang an die feste Zeitachse des Untersuchungszeitraums (E3: 2013-01 bis 2025-12, 156 Monate), leer angelegt; jeder Monat wird an seine Position geschrieben, nie hinten angehängt, damit die Zeitachse unabhängig von der Lade-Reihenfolge sortiert bleibt. Eine Variable `monat_fertig` (0/1 je Monat) wird erst nach erfolgreichem Zurücklesen gesetzt; ein leerer, nicht geladener Monat ist so von einem Monat mit Daten und einem Monat ohne Messungen unterscheidbar. Alle Rohdaten und Würfel liegen auf einer externen SSD; der Pfad steht in `.env` unter `ALEPH_DATA_DIR` (Vorlage ohne Wert in `.env.example`). `aleph/core/io.py` liest diesen Pfad und bricht mit klarer Meldung ab, wenn die SSD nicht angeschlossen ist.

## 4a. Fokusgebiete: feinere Analyse für Kriegs- und Krisengebiete

Das globale Monatsraster ist für schnelle Veränderungen zu grob. Für ausgewählte Gebiete gibt es deshalb eine **zweite, feinere Analyseebene**.

**Auswahl der Fokusgebiete:** automatisch aus ACLED (Gebiete mit vielen Konfliktereignissen), ergänzend manuell (z. B. aktuelle Kriegs- und Katastrophengebiete). Gespeichert in `focus_areas.yaml` mit Grund und Zeitraum.

**Auflösung in Fokusgebieten:**

| | Global | Fokusgebiet |
|---|---|---|
| Raster | 0,25° (ca. 28 km) | native Auflösung der Quelle (500 m Nachtlicht, 375 m Brände, 10–20 m Radar) |
| Zeittakt | monatlich | täglich bzw. je Überflug, ausgewertet als Wochen- und Tagesreihen |

**Zusätzliche Datenquellen für Fokusgebiete:**

| Signal | Quelle | Was es zeigt |
|---|---|---|
| Nachtlicht täglich | VIIRS Black Marble VNP46A2 | Stromausfälle, Flucht und Rückkehr der Bevölkerung, Zerstörung von Infrastruktur |
| Brände täglich | FIRMS (VIIRS 375 m) | Brände durch Beschuss, Brandstiftung, getroffene Anlagen |
| Radar | Sentinel-1 (Copernicus), wolken- und nachtunabhängig | Gebäudeschäden über Kohärenzverlust zwischen zwei Aufnahmen |
| Optisch | Sentinel-2 (10 m) | Veränderungen an Flächen, Bauten, Feldern |
| Luftqualität | Sentinel-5P NO₂ | Stillstand oder Wiederanlauf von Industrie und Verkehr |
| Konfliktereignisse | ACLED | Kämpfe, Explosionen, Angriffe mit Ort und Datum |
| Nachrichten | GDELT | Berichterstattung zur Region |

**Methodische Besonderheiten:**
- Tägliche Daten sind verrauscht (Wolken, Mondlicht, Blickwinkel). Deshalb Qualitätsmasken der Anbieter nutzen und Tageswerte nur gemeinsam mit mehreren Tagen davor und danach bewerten.
- Die Basislinie ist die Zeit **vor** Beginn der Krise im selben Gebiet, nicht der globale Normalzustand.
- Gebäudeschäden aus Radar sind **abgeleitet**, nicht direkt gemessen. Anzeige als „vermutliche Schäden" mit Datenlage.
- Prüfung gegen unabhängige Schadenskartierungen, wo vorhanden (z. B. UNOSAT), und gegen ACLED-Ereignisse.

**Veröffentlichungsgrenze:** ALEPH zeigt Veränderungen mit Verzögerung und zusammengefasst (Schäden, Brände, Stromausfälle, Bevölkerungsbewegung). Es zeigt keine Positionen oder Bewegungen einzelner Einheiten, Fahrzeuge oder Personen in Echtzeit.

## 5. Layer: die Schnittstelle für jede Datenquelle

Jede Datenquelle ist ein Modul `aleph/layers/<name>.py` mit genau diesen Bestandteilen:

| Bestandteil | Inhalt |
|---|---|
| `META` | Name, Bereich (z. B. Umwelt, Mobilität, Wirtschaft), Quelle, Lizenz, native Auflösung, Einheit, Zeitraum, bekannte Schwächen |
| `download(start, ende)` | lädt Rohdaten nach `data/raw/<name>/`, nutzt `aleph/core/io.py` und Zugangsdaten (Tokens, Konten) ausschließlich aus `.env` |
| `to_cube()` | erzeugt den Datenwürfel auf dem gemeinsamen Raster: Messwert **und** Anzahl gültiger Beobachtungen pro Zelle und Monat |

Alle Layer sind in `layers.yaml` registriert. Ein neuer Layer ist fertig, wenn `to_cube()` einen Würfel liefert, der den automatischen Prüftest `tests/test_layer_contract.py` besteht.

Für NASA-Downloads wird die Bibliothek `earthaccess` genutzt, keine eigene Download-Logik.

**Kandidaten für die ersten Layer** (NASA-Daten zuerst, weil Space Apps sie verlangt):

| Layer | Quelle | Warum |
|---|---|---|
| Nachtlicht | VIIRS Black Marble VNP46A3 (monatlich) | menschliche Aktivität, Stromausfälle, Stadtwachstum |
| Vegetation | MODIS MOD13C2 NDVI (monatlich, global) | Dürre, Abholzung, Landwirtschaft |
| Brände | FIRMS Active Fire (MODIS + VIIRS) | Brände, Brandrodung |
| Luftqualität | OMI NO₂ (OMNO2d) | Industrie, Verkehr, Lockdowns |
| Niederschlag | GPM IMERG (monatlich) | Dürre, Überschwemmung |

Nicht als Erkennungs-Layer, sondern als **Kontext**:
- Nachrichten: GDELT (Ereignisse und Artikel-Links pro Region und Zeitraum)
- Wirtschaft: Weltbank-Indikatoren (jährlich, pro Land)

**Mobilität: Schiffs- und Flugverkehr** (nicht NASA, aber öffentlich und nicht-kommerziell nutzbar):

| Layer | Quelle | Zugang | Einschränkung |
|---|---|---|---|
| Schiffsverkehr | Global Fishing Watch, Datensatz „AIS Vessel Presence" (alle Schiffstypen, global) | kostenloses API-Token, nur nicht-kommerziell, Quellenangabe Pflicht | zeigt nur Schiffe, die AIS senden; ergänzend SAR-Radarerkennung für Schiffe ohne AIS |
| Flugverkehr | OpenSky Network | REST-API frei für nicht-kommerzielle Zwecke; vollständige Historie nur für Forschungseinrichtungen | für Privatpersonen nur veröffentlichte Datensätze und begrenzte API; Zugang über Universitätsanbindung prüfen |

Beide werden wie jeder andere Layer auf das gemeinsame Raster gebracht (z. B. Schiffe bzw. Flüge pro Zelle und Monat). Typische Fragen: neue Schifffahrtsrouten (z. B. Arktis), Ausfall von Handelswegen, Einbruch des Luftverkehrs in einer Region.

**Bevölkerung** (ohne Konto verfügbar, nötig für Stadtwachstum und Einwohnerzahlen):
- GHSL (EU-Kommission) oder WorldPop: Bevölkerungsraster, jährlich bzw. in Mehrjahresschritten. Dient auch als Kontrollvariable (Abschnitt 8).

**Quellen mit Konto oder Token** (Alexander richtet die Zugänge ein; Zugangsdaten nur in `.env`):

| Quelle | Inhalt | Rolle in ALEPH |
|---|---|---|
| NASA Earthdata | alle NASA-Satellitendaten oben | Grundlage |
| Copernicus Data Space | Sentinel-5P (NO₂ in höherer Auflösung), Sentinel-1 (Radar) | Ergänzung zu OMI, ab 2018 |
| Copernicus Climate Data Store | ERA5 Klimadaten (Temperatur, Bodenfeuchte u. a.) | Klima-Layer |
| ACLED | georeferenzierte Konflikt- und Gewaltereignisse, inkl. Explosionen | Kontext und Referenz, verlässlicher als GDELT |
| EM-DAT | Katastrophendatenbank | zweiter Referenzkatalog für den Blindtest |
| IDMC / UNHCR | Binnenvertreibung und Fluchtbewegungen | Wirkungsvariable für Migrationstheorien |
| UN Comtrade | Import/Export nach Land und Warengruppe | Wirtschaftskontext |
| Global Fishing Watch, OpenSky | siehe oben | Mobilität |

**Nutzungsbedingungen beachten:** Einige Anbieter erlauben die Analyse, aber nicht die öffentliche Weitergabe der Rohdaten (z. B. einzelne Datensätze auf einer öffentlichen Karte). Für jede Quelle wird in `META` festgehalten, was angezeigt werden darf: Rohdaten, nur zusammengefasste Werte oder nur Verweise. Die Oberfläche hält sich daran.

## 6. Anomalieerkennung

Pro Layer, pro Gitterzelle, pro Monat:

1. **Saisonale Basislinie.** Vergleich immer mit demselben Kalendermonat früherer Jahre (Juli mit Juli), damit normale Jahreszeiten keine Meldungen auslösen. Der untersuchte Monat ist nie Teil seiner eigenen Basislinie.
2. **Robuste Abweichung.** Abstand zum Median, geteilt durch die typische Streuung (MAD). Robust gegen einzelne Ausreißer in der Vergangenheit.
3. **Mindest-Datenlage.** Zellen mit zu wenigen gültigen Beobachtungen oder zu kurzer Basislinie werden nicht bewertet, sondern als „Datenlage unzureichend" markiert.
4. **Schutz vor Zufallstreffern.** Bei rund einer Million Zellen pro Monat entstehen allein durch Zufall tausende auffällige Werte. Deshalb:
   - Korrektur für multiples Testen (Benjamini-Hochberg, kontrolliert den erwarteten Anteil falscher Meldungen),
   - Mindestgröße: Ein Ereignis braucht mehrere benachbarte auffällige Zellen,
   - optional Dauer: auffällig in mehr als einem Monat.
5. **Ausgabe in Bändern.** auffällig / stark / extrem, dazu Richtung (Anstieg/Rückgang) und Datenlage (gut/mittel/dünn).
6. **Änderungen am Messsystem.** Viele Quellen verändern sich selbst: mehr AIS-Empfänger, mehr OpenSky-Sensoren, mehr Nachrichtenquellen in GDELT, Sensorwechsel (MODIS → VIIRS). Das erzeugt scheinbare Trends. Solche Brüche werden pro Layer in `META` dokumentiert und, wo möglich, herausgerechnet (z. B. Werte relativ zur Gesamtabdeckung im selben Monat). Wo das nicht geht, wird der Zeitraum getrennt bewertet.

## 7. Anomalien benennen

Zusammenhängende auffällige Zellen werden zu einer Anomalie zusammengefasst. Keine Anomalie bleibt ohne Namen: Jede bekommt entweder einen **bekannten Typ** oder wird ausdrücklich als **unerklärt** geführt.

**Bekannte Typen** (Beispiele, festgelegt in `anomaly_types.yaml`):

| Anzeige | Erkennungsregel (vereinfacht) |
|---|---|
| Anomalie: Waldbrand | viele Brand-Detektionen + Vegetationsrückgang, außerhalb von Siedlungen |
| Anomalie: Stromausfall | starker, plötzlicher Nachtlicht-Rückgang in besiedeltem Gebiet |
| Anomalie: Dürre | Niederschlagsdefizit + Vegetationsrückgang über mehrere Monate |
| Anomalie: Abholzung | dauerhafter Vegetationsverlust, oft nach Brand-Detektionen |
| Anomalie: Stadtwachstum | dauerhafter Nachtlicht-Anstieg am Siedlungsrand |
| Anomalie: neue Schifffahrtsroute | Schiffspräsenz in Zellen ohne frühere Präsenz |
| Anomalie: vermutliche Kriegsschäden | Radar-Kohärenzverlust + Brände und/oder ACLED-Ereignisse im Fokusgebiet |
| Anomalie: Stromausfall im Konfliktgebiet | Nachtlicht-Einbruch im Fokusgebiet, zeitnah zu ACLED-Ereignissen |
| Anomalie: Bevölkerungsbewegung | anhaltender Nachtlicht-Rückgang an einem Ort und Anstieg an anderen (z. B. Flucht), abgeglichen mit IDMC/UNHCR |

**Unerklärte Anomalien:** Passt keine Regel, lautet der Name *„Anomalie: unerklärte Veränderung in [betroffene Layer]"*, z. B. „Anomalie: unerklärte Veränderung in Nachtlicht und NO₂". Diese sind ausdrücklich gewollt: Sie sind die Kandidaten für echte Entdeckungen.

**Wie sicher ist der Name?** Die Benennung ist selbst eine Aussage und bekommt deshalb eine eigene Angabe:
- `direkt gemessen` – das Signal misst das Phänomen selbst (Brand-Detektionen → Waldbrand)
- `abgeleitet` – das Phänomen wird aus indirekten Signalen erschlossen (Nachtlicht-Rückgang → vermutlich Stromausfall). Anzeige dann mit „vermutlich" und Begründung.

**Jede Anomalie speichert:**
`id`, `name` (angezeigter Typ), `typ_sicherheit` (direkt gemessen / abgeleitet / unerklärt), `layer` (einer oder mehrere), `gebiet` (Umriss), `start`, `ende`, `richtung`, `stärke_band`, `datenlage`, `evidenzstufe` (hier immer `beobachtet`), `zeitreihe` (Verweis), `version` der Erkennungs- und Benennungslogik.

## 8. Verknüpfung und Theorie-Register

**Grundsatz:** ALEPH verknüpft Ereignisse nicht, weil sie zufällig zusammenfallen, sondern weil eine dokumentierte Theorie einen Zusammenhang erwartet. Diese Erwartung wird dann an Daten geprüft.

**Theorie-Eintrag** (`theories/<id>.yaml`):

```yaml
id: duerre-migration
titel: Dürre verstärkt Abwanderung aus ländlichen Regionen
disziplin: Umweltökonomie / Migrationsforschung
quellen:
  - "<Literaturangabe>"
ursache: {layer: niederschlag, richtung: rückgang}
wirkung: {layer: nachtlicht, richtung: rückgang, zusätzlich: abwanderung}
verzögerung_monate: [3, 24]
geltungsbereich: ländliche Regionen, landwirtschaftlich geprägt
mechanismus: >
  Ernteausfälle senken Einkommen, Haushalte wandern in Städte ab.
bedingungen: >
  Stärker bei geringer Bewässerung und schwachen sozialen Sicherungssystemen.
status: ungeprüft   # ungeprüft | bestätigt | nicht bestätigt | Daten unzureichend
prüfergebnisse: []
```

**Beispiele für erste Theorie-Einträge** (Bereiche, nicht abschließend; jede Theorie ist in der Forschung umstritten und wird genau deshalb geprüft):

| Bereich | Theorie (vereinfacht) | Prüfbar mit |
|---|---|---|
| Klima und Konflikt | Niederschlags- und Hitzeschocks erhöhen das Konfliktrisiko (u. a. Miguel, Satyanath & Sergenti 2004; Hsiang, Burke & Miguel 2013) | Niederschlag, Temperatur, ACLED |
| Ressourcen und Konflikt | Rohstoffreichtum erhöht Konfliktrisiko („Ressourcenfluch", u. a. Collier & Hoeffler) | Weltbank-Rohstoffdaten, ACLED, Nachtlicht an Förderstätten |
| Nahrungspreise und Unruhen | steigende Nahrungsmittelpreise gehen Protesten voraus (u. a. Bellemare 2015) | Preisdaten (FAO), ACLED |
| Konflikt und Vertreibung | Gewalt führt zu Abwanderung, sichtbar an Nachtlicht und Vertreibungszahlen | ACLED, Nachtlicht, IDMC/UNHCR |
| Dürre und Migration | siehe Beispiel oben | Niederschlag, Vegetation, Nachtlicht, IDMC |

Literaturangaben werden beim Anlegen jedes Eintrags geprüft und vollständig zitiert.

**Prüfung einer Theorie:**
1. Theorie wird formuliert, **bevor** die Testdaten angesehen werden.
2. Aufteilung in Zeiträume: frühere Jahre zum Kalibrieren, spätere Jahre zum Testen.
3. Vergleich mit einem Zufallsmodell, das Jahreszeiten und räumliche Nachbarschaft erhält (Permutationstest). Nur wenn der gefundene Zusammenhang deutlich häufiger auftritt als im Zufallsmodell, gilt er als bestätigt.
4. Bekannte gemeinsame Treiber (z. B. Bevölkerungswachstum, Konjunktur) werden, wo möglich, als Kontrollvariablen berücksichtigt.
5. Das Ergebnis wird im Eintrag gespeichert und in der Oberfläche angezeigt, **auch wenn die Theorie nicht bestätigt wird.**

**Evidenzstufen der Verknüpfung:**
- Zwei Ereignisse fallen zusammen, passende Theorie noch ungeprüft → `beobachtet` (Koinzidenz), Theorie als Hypothese angezeigt
- Theorie an Testdaten bestätigt → `statistische Assoziation`
- Aus bestätigten Zusammenhängen abgeleitete Entwicklung → `Modellprojektion`
- Annahmen über die Zukunft → `hypothetisches Szenario`

## 9. Blindtest

Der Nachweis, dass ALEPH funktioniert.

1. Erkennung läuft über einen vergangenen Zeitraum (Vorschlag: 2019–2024), ohne Wissen über die tatsächlichen Ereignisse.
2. Vergleich mit einem unabhängigen Ereigniskatalog (Vorschlag: GDACS; ergänzend EM-DAT).
3. Zuordnungsregel festgelegt **vor** dem Test: Treffer, wenn Ort innerhalb von X km und Zeit innerhalb von ±1 Monat.
4. Kennzahlen pro Ereignistyp und Layer:
   - Trefferquote: Welcher Anteil der bekannten Ereignisse wurde gefunden?
   - Meldungen ohne Katalogeintrag: werden stichprobenartig von Hand geprüft (nicht jede ist falsch – ALEPH findet auch Dinge, die kein Katastrophenkatalog enthält, z. B. neue Industrieanlagen).
5. Ergebnis als Bericht in `reports/`, mit Datum und Version der Erkennungslogik.

## 9a. Wie das Modell besser wird

Die Erkennung in Abschnitt 6 ist eine bewusst einfache **Basislinie**. Sie wird nicht nach Gefühl verbessert, sondern nur, wenn der Blindtest eine Verbesserung zeigt.

**Drei getrennte Datenzeiträume** (sonst wird das System auf den Test „auswendig gelernt"):

| Zeitraum | Zweck | Darf angefasst werden? |
|---|---|---|
| Kalibrierung (z. B. 2013–2019) | Schwellenwerte, Regeln und Gewichte einstellen | beliebig oft |
| Validierung (z. B. 2020–2022) | Varianten vergleichen, beste auswählen | zum Vergleichen, nicht zum Einstellen |
| Endtest (z. B. 2023–2025) | ehrliche Leistungszahl für Bericht und Präsentation | nur einmal pro Hauptversion |

**Verbesserungsschleife:**
1. Blindtest zeigt, wo das System versagt (z. B. übersieht kleine Brände, meldet Wolken als Stromausfall).
2. Gezielte Änderung, z. B. bessere Wolkenmaske, zusätzlicher Layer, neue Benennungsregel.
3. Vergleich alte gegen neue Version auf dem Validierungszeitraum.
4. Übernahme nur bei messbarer Verbesserung; Ergebnis in `reports/` und `LOG.md`.

**Mögliche Ausbaustufen**, jeweils nur wenn die vorige Stufe ausgereizt ist:
- Stufe 1: saisonaler Vergleich (Abschnitt 6)
- Stufe 2: Trend und Saison getrennt modellieren (STL-Zerlegung), damit langsames Wachstum nicht als Anomalie gilt
- Stufe 3: mehrere Layer gemeinsam bewerten (Abweichung im Zusammenspiel, z. B. Nachtlicht sinkt, NO₂ bleibt gleich)
- Stufe 4: lernende Benennung (z. B. Entscheidungsbäume), trainiert auf den Katalogen aus Abschnitt 9 – nur mit getrenntem Endtest

## 10. Oberfläche

- Statische Webseite (`web/`), die fertige Dateien der Pipeline liest: Anomalien als GeoJSON, Kartenebenen als Kacheln.
- **Globus** als Hauptansicht: MapLibre GL JS mit Globus-Darstellung (frei, ohne Konto).
- **Suchleiste:** Orte (aus einem mitgelieferten Ortsverzeichnis, z. B. GeoNames/Natural Earth, ohne externe API), Anomalien, Theorien.
- **Filter:** Region, Bereich/Anomalie-Typ, Zeitraum (Zeitschieber), Evidenzstufe, Mindeststärke, nur Fokusgebiete.
- **Untersuchungsansicht pro Anomalie:** Zeitreihe mit Basislinie, Datenlage, verknüpfte Anomalien, betroffene Theorien mit Prüfstatus, Nachrichten (GDELT) und Konfliktereignisse (ACLED) für Region und Zeitraum.
- Die Oberfläche wird **ab Woche 2** gebaut, zuerst mit Beispieldaten, und wächst mit jedem fertigen Layer mit. So gibt es jederzeit einen vorzeigbaren Prototyp.
- Später: Veröffentlichung über GitHub Pages.

## 10a. Live-Kanal (zurückgestellt)

Live-Anzeige von Schiffen und Flügen ist bis nach dem Hackathon zurückgestellt: Sie bräuchte einen dauerhaft laufenden Server und bringt ohne historische Basislinie wenig wissenschaftlichen Wert. Mögliche Quellen für später: aisstream.io (Schiffe), ADSB.lol oder OpenSky (Flüge).

## 11. Ordnerstruktur

```
ALEPH/
├── CLAUDE.md              Arbeitsregeln
├── ARCHITECTURE.md        dieses Dokument
├── LOG.md                 Arbeitsprotokoll
├── README.md
├── layers.yaml            Register aller Layer
├── anomaly_types.yaml     bekannte Anomalie-Typen und ihre Regeln
├── focus_areas.yaml      Fokusgebiete mit feinerer Analyse
├── theories/              Theorie-Register (ein YAML pro Theorie)
├── docs/sources/          Steckbriefe der Datenquellen
├── aleph/
│   ├── core/              Raster, Laden, Speichern, Konfiguration
│   ├── layers/            ein Modul pro Datenquelle
│   ├── detect/            Abweichungen erkennen
│   ├── focus/             feinere Analyse für Fokusgebiete
│   ├── classify/          Anomalien benennen
│   ├── link/              Verknüpfung und Theorieprüfung
│   ├── validate/          Blindtest
│   └── export/            Ausgabe für die Oberfläche
├── web/                   Oberfläche
├── tests/                 automatische Tests
├── reports/               Blindtest- und Prüfberichte
├── scripts/               einfache Start-/Status-Befehle für Hintergrund-Läufe
├── logs/                  (nicht in Git) Absturz-Auffangprotokoll; Details stehen auf der SSD
└── data/                  (nicht in Git, liegt auf externer SSD, ALEPH_DATA_DIR) raw/, cube/, events/
```

## 12. Entscheidungen (bestätigt am 2026-09-21)

| Nr. | Frage | Entscheidung |
|---|---|---|
| E1 | Rasterweite | 0,25° global |
| E2 | Zeittakt | monatlich |
| E3 | Untersuchungszeitraum | 2013–2025 (ab Beginn der VIIRS-Nachtlichtdaten) |
| E4 | Erste Layer | Nachtlicht, Vegetation, Brände |
| E5 | Referenzkatalog für den Blindtest | GDACS |
| E6 | Erste Theorien | 3–5 Einträge, darunter Dürre → Abwanderung |
| E7 | Mobilitäts-Layer | Schiffsverkehr (Global Fishing Watch) in Woche 4; Flugverkehr, sobald der OpenSky-Zugang geklärt ist |
| E8 | Zugänge, die Alexander einrichtet | zuerst NASA Earthdata, Global Fishing Watch, Copernicus, ACLED; danach EM-DAT |
| E9 | Erstes Fokusgebiet | ein Gebiet mit guter Vergleichsdatenlage, z. B. Ukraine (seit 2022) |

## 13. Zeitplan bis zum Hackathon (14.–15. November 2026)

| Woche | Ziel |
|---|---|
| 1 | Kern: Raster, Laden, Speichern, Layer-Vertragstest; Layer Nachtlicht |
| 2 | Layer Vegetation und Brände; **Oberflächen-Gerüst: Globus, Suchleiste, Filter mit Beispieldaten** |
| 3 | Anomalieerkennung mit Korrektur für multiples Testen; Benennung; echte Anomalien auf dem Globus |
| 4 | Layer NO₂, Niederschlag und Schiffsverkehr |
| 5 | Fokusgebiete: tägliches Nachtlicht und Brände, ACLED; Theorie-Register mit ersten Theorien |
| 6 | Blindtest und Bericht; Untersuchungsansicht mit Zeitreihen und Kontext |
| 7 | Prototyp fertigstellen: Globus, Suchleiste, alle Filter, Fokusgebiet-Ansicht, Theorie-Status; Challenge-Bezug herstellen; stabilisieren, Präsentation vorbereiten. |

**Nach November** (Ideenspeicher, nicht Teil des Prototyps): Radar-Schadenserkennung (Sentinel-1), weitere Fokusgebiete, Live-Kanal, Szenarien, weitere Theorien. Neue Ideen landen zuerst hier, nicht direkt im Plan.

Am 28. Oktober erscheinen die vollständigen Challenge-Texte. Danach wird festgelegt, welcher Teil von ALEPH die gewählte Challenge direkt beantwortet.
