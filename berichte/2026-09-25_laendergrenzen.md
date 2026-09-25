# Bericht: Ländergrenzen (Natural Earth) – Steckbrief, Laden, Prüftest

Datum: 2026-09-25 · Auftrag: Ländergrenzen als Datenquelle, Regel „Berichte“ in CLAUDE.md

## Kurzfassung

- Ländergrenzen kommen jetzt aus Natural Earth 5.1.1, Admin 0 – Countries, 1:10m, Standarddatei. Der Download hat funktioniert, nichts ist nachgebaut.
- Die Datei liegt im Datenordner unter `raw/natural_earth/5.1.1/` mit Manifest (Prüfsumme). Geladen wird sie über `aleph/layers/natural_earth.py`, nach demselben Muster wie beim Weltbank-Layer.
- Die Datei hat 258 Einträge, genau so viele, wie die Quelle angibt. Alle fünf Punktproben stimmen: Kairo, Berlin, Paris, Riad und der Atlantik.
- Bestätigt: Frankreich und Norwegen haben im Feld ISO_A3 den Platzhalter „-99“. Gewählt ist deshalb ISO_A3_EH mit drei Korrekturen (Kosovo → XKX, Jersey/Guernsey → CHI). Damit haben alle 217 Weltbank-Länder eine Grenze.
- 34 Natural-Earth-Einträge haben kein Weltbank-Gegenstück, u. a. Taiwan, Somaliland, Westsahara, Nordzypern und Åland. Sie werden nicht still einem Nachbarn zugeschlagen.
- „De facto“ heißt bei Natural Earth: eine Regel des Anbieters, nicht die Kontrolle vor Ort. Die Krim liegt bei Russland, Donezk und Luhansk bei der Ukraine, und dieser Stand gilt für alle Jahre.
- Bei Zuordnung über die Zellmitte bekommen 26 kleine Weltbank-Länder keine 0,25°-Zelle. Das muss vor der Nachtlicht-BIP-Analyse entschieden werden.
- Tests: 519 von 519 grün (vorher 495, neu 24). Der Download 41131 lief ungestört weiter. Nichts committet.

## Urteil

Die Quelle ist brauchbar für die Zuordnung von Orten und Zellen zu Ländern und ist eingebaut. Der Plausibilitäts-Prüfer urteilte „plausibel mit Vorbehalt“. Sein Vorbehalt betraf eine falsche Begründung von mir, nämlich „de facto = Kontrolle vor Ort“. Die Begründung ist in Steckbrief, Code und ARCHITECTURE.md berichtigt. Offen ist eine inhaltliche Frage: Welche Gebiete umfassen die Weltbank-Zahlen je Land (Krim, Somaliland, Nordzypern)? Davon hängt ab, wie gut die gewählte Sicht zur Weltbank passt.

## Belege

Alle Zahlen stammen aus Messungen an den am 2026-09-25 geladenen Dateien und an der Weltbank-Länderliste vom Abruf 2026-09-23. Einzelheiten stehen in `docs/sources/natural_earth.md`, Abschnitt 13.

- **Download:** `https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip`, HTTP 200, 4 930 492 Byte, SHA-256 `ce1ac7036499a0edd641fbc093cd209a98f96a49d2eca8480aaacad35138a7f6`, beiliegende `VERSION.txt` = 5.1.1, Server-Datum 13. Mai 2022.
- **Anzahl:** 258 geladen. Die Quelle sagt „There are 258 countries in the world“ (beiliegende README). Der Satz steht aber auch bei 1:50m (242 Einträge) und 1:110m (177) und passt nur zu 1:10m.
- **Punktproben:** Kairo → Ägypten (EGY), Berlin → Deutschland (DEU), Paris → Frankreich (FRA), Riad → Saudi-Arabien (SAU), 40° W / 30° N → kein Land. Das nächste Land ist über 1000 km entfernt (Prüfer).
- **Code-Felder gegen 217 Weltbank-Codes (Treffer):** ISO_A3 213, ISO_A3_EH 215, ADM0_A3 213, WB_A3 206.
  - ISO_A3 = „-99“ bei 22 Einträgen, darunter Frankreich, Norwegen und Kosovo.
  - WB_A3 enthält alte Codes (ROM, ZAR, TMP, ADO, IMY, WBG, KSV). Bei Norwegen, Gibraltar, den Britischen Jungferninseln und Nauru steht dort „-99“.
  - Mit ISO_A3_EH und den Korrekturen passen alle 217.
- **Nicht passende Länder (vollständige Liste):**
  - Weltbank-Länder ohne passenden ISO_A3_EH: Kosovo (Natural Earth „-99“, Weltbank XKX) und Kanalinseln (Natural Earth Jersey JEY und Guernsey GGY, Weltbank nur CHI). Beide sind korrigiert.
  - Natural-Earth-Einträge ohne Weltbank-Gegenstück: 34, Liste im Steckbrief Abschnitt 13.
  - Mehrere Einträge je Weltbank-Code: AUS, BRA, CHI, FRA, KAZ.
- **Maßstab (0,25°-Zellmitten):** 1:10m und 1:50m unterscheiden sich in 3 034 Zellen (0,9 % der Landzellen), bei 1:110m sind es 3,8 %. 1:50m verliert Bahrain, 1:110m verliert 48 Weltbank-Länder ganz.
- **Sichtweisen:**
  - Eine Weltbank- oder UN-Sicht gibt es nicht (HTTP 403, Spalte ADM0_A3_WB überall „-99“).
  - Die ISO-Sicht lässt umstrittene Flächen weg. Es entstehen Lücken, z. B. 278 Zellen, die sonst zu Indien gehören, und 206 bei Guyana.
  - Die deutsche Sicht weicht in 578 Zellen ab: Westsahara 259, Somaliland 226, Krim 53 und kleinere.
- **Geometrie:** Genau ein Umriss ist formal ungültig: Ägypten. Die Randlinie berührt sich selbst bei 35,621° O / 23,139° N. Die Reparatur ändert die Fläche nicht (< 1e-13 Grad²) und ist im Manifest vermerkt. Jede Reparatur mit Flächenänderung bricht ab.

## Umfang

- **Neu:**
  - `aleph/layers/natural_earth.py`: Download mit Zeitlimit und Wiederholung, Abbruch bei HTTP 4xx, Prüfung von Version, Anzahl, Koordinatensystem, Eindeutigkeit und Prüfsumme; `lade_laender`, `land_an_punkt`, `abgleich_weltbank`.
  - `tests/test_natural_earth.py`: 24 Tests, davon 6 mit echten Daten, die nur bei angeschlossener SSD laufen.
  - `docs/sources/natural_earth.md`: Recherche vom `datenquellen-scout`, Messungen und Entscheidungen von mir.
- **Geändert:**
  - `CLAUDE.md`: Regel „Berichte“ wörtlich eingetragen.
  - `ARCHITECTURE.md`: Abschnitt 4, Absatz „Ländergrenzen“.
  - `requirements.txt`: geopandas, shapely, pyogrio und requests nachgetragen. Sie waren schon installiert, standen aber nicht in der Liste.
  - `LOG.md`.
- **Nicht angefasst:** `aleph/layers/vnp46a3*.py`, die Kachelliste, `scripts/`, `.env`. Download-Prozess 41131 läuft (geprüft).
- **Übergabe `claude/uebergabe-2026-09-25.md`:** nicht vorhanden, nirgends im Projekt.
- **Agenten:**
  - `datenquellen-scout`: Steckbrief-Recherche.
  - Plausibilitäts-Prüfer: als allgemeiner Agent mit der Anleitung aus `.claude/agents/plausibilitaets-pruefer.md`, weil der Typ in der Sitzung nicht verfügbar war.
  - `statistik-pruefer`: nicht eingesetzt, weil kein Analyse-Code (Erkennung, Verknüpfung, Statistik) geändert wurde.
  - `layer-bauer`: nicht eingesetzt. Die Ländergrenzen sind kein Daten-Layer mit Würfel oder Tabelle, sondern ein Hilfsdatensatz für die Zuordnung. Diese Einordnung ist meine Entscheidung und kann anders gesehen werden.

## Empfehlung

1. Vor der Nachtlicht-BIP-Analyse die **Zuordnungsregel** festlegen: Zellmitte (26 kleine Länder ohne Zelle) oder Flächenanteil je Zelle und Land.
2. **Prüfen, welche Gebiete die Weltbank-Reihen umfassen.** Zuerst die Krim: Die Auffälligkeit bei Russland und der Ukraine im Weltbank-Steckbrief (ab 2014 je etwa 2,3 bis 2,5 Mio. Personen) könnte damit zusammenhängen. Das ist eine Vermutung und nicht geprüft. Danach Somaliland, Nordzypern und Westsahara.
3. Länder-Auswertungen für Russland, Ukraine, Marokko, Somalia, Zypern, Indien, Pakistan, China und Georgien mit und ohne die umstrittenen Zellen rechnen oder kennzeichnen.
4. Die Zitate des Scouts vor einer Präsentation am Original gegenlesen. Sie sind nur über ein Hilfsmodell gelesen.

## Nicht geprüft

- Welche Gebiete die Weltbank-Zahlen je Land einschließen (siehe Empfehlung 2).
- Die Genauigkeit der Grenzlinien selbst: kein Vergleich mit einer zweiten Quelle.
- Ob naciscdn.org die offizielle, dauerhafte Adresse ist. Am 2026-09-25 hat sie funktioniert.
- Die offizielle Bedeutung der Felder ISO_A3, WB_A3, SOV_A3 und GU_A3: Der Anbieter hat keine Feldbeschreibung.
- Die früheren Weltbank-Codes (ROM, ZAR usw.) sind nur aus Wissen des Prüfers als „alt“ beurteilt, nicht an einer Weltbank-Quelle belegt.
- Welche Fläche die 17 Sudan-Zellen sind, die in der deutschen Sicht keinem Land gehören.
