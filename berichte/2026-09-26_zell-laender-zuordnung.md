# Zell-Länder-Zuordnung nach Flächenanteil, mit UN-Sicht und Sondereinheiten (Phase 3)

Stand: 2026-09-26 · Code: `aleph/layers/zell_einheiten.py`, `aleph/layers/un_m49.py`, `aleph/layers/sondereinheiten.yaml`, Erweiterung `aleph/layers/natural_earth.py` · Ergebnis: `laender/zell_einheiten/` auf der SSD · Status: abgeschlossen, geprüft

## Kurzfassung

- Jede 0,25°-Zelle des Nachtlicht-Gitters ist nach **Flächenanteil** auf 324 Einheiten verteilt (374 643 Zeilen Zelle → Einheit → Anteil). Das Gitter stammt aus dem Nachtlicht-Code und stimmt mit dem Würfel auf der SSD exakt überein.
- **Oberste Ebene ist die UN-Sicht (M49).** 87 Sondereinheiten (umstritten, besetzt/Konfliktzone, Sonderstatus) gehen nicht im Staat auf, u. a. Krim, Donezk, Luhansk, Taiwan, Tibet, Westjordanland, Gaza, Ostjerusalem, Golan, Westsahara, Nordzypern, Kosovo, Abchasien, Südossetien, Transnistrien, Bergkarabach, Somaliland, Kaschmir (6 Teile), Hongkong, Macau, Grönland. Jede nennt ihren M49-Eintrag mit Beleg oder „unklar“.
- **Krim:** eigene Einheit, UN-Eintrag Ukraine (Resolution 68/262); Simferopol-Zelle 100 % Krim. Weltbank-Sicht: kein Land (unklar).
- Flächen richtig auf dem Ellipsoid: keine Fläche verloren oder doppelt (je Zelle höchstens 1·10⁻¹⁴ Abweichung gegen die Landfläche). Für die fünf geprüften Länder weicht die Fläche höchstens 0,0007 % von einer unabhängigen Rechnung ab.
- Alle 217 Weltbank-Länder haben Zellfläche (mit Zellmitte: 26 ohne). 104 Einheiten sind kleiner als eine Zelle, sichtbar ausgewiesen, keine weggelassen; 2 davon (Sapodilla Cayes, Doumera) haben keine Fläche.
- Prüfer: `statistik-pruefer` „bestanden mit Auflagen“, Plausibilitäts-Prüfer „plausibel mit Vorbehalt“. Auflagen für Phase 3 umgesetzt; drei Festlegungen für Phase 5 stehen unter Empfehlung.
- Tests: 48 neue; Gesamtsuite **567 von 567 grün, keiner übersprungen** (echte Daten liefen mit). Zeitabhängigkeit und Karte nur als Plan.

## Urteil

Die Zuordnung ist gebaut, geprüft und gespeichert und trifft keine eigene Souveränitätsentscheidung. Größte Grenze: Alle Umrisse sind ein fester Stand (Natural Earth 5.1.1, Mai 2022). Für die Ukraine nach Februar 2022 fehlen die Umrisse; Bergkarabach entspricht laut Plausibilitätsprüfung eher der Lage nach Ende 2020 (nicht an einer Quelle geprüft). Für den Querschnitt 2018 (Phase 5) betrifft das Länder, die ohnehin als „unklar“ markiert sind.

## Belege

### Testlauf (2026-09-26, nach allen Änderungen)
- `.venv/bin/python -m pytest -q -rs` → „567 passed, 360 warnings in 274.41s“. Keine Zeile „SKIPPED“: Die Tests mit echten Daten (SSD) sind gelaufen, nicht übersprungen. Die Warnungen sind die bekannte DeprecationWarning aus `vnp46a3.py` Z. 1350.
- Neu: `tests/test_zell_einheiten.py` (39 Fälle) und `tests/test_un_m49.py` (9 Fälle); vorher 519.

### Raster
- Gitterdefinition aus `aleph/layers/vnp46a3.py` (720 × 1440, 0,25°, Zeile 0 = Nordrand 90°, Spalte 0 = Westrand −180°), nur importiert. Gegen die Koordinaten des Würfels `cube/vnp46a3.zarr` geprüft (nur lesend): gleich.

### Flächenrechnung
- Flächentreue Zylinderprojektion EPSG:6933 auf dem WGS-84-Ellipsoid; jede Zelle ist darin ein Rechteck mit ihrer echten Fläche, zu den Polen kleiner (Äquatorzelle 769 km²). Summe aller Zellen = Oberfläche des Ellipsoids aus a und f (Test, < 10⁻⁹).
- Umrisse vorher in Grad auf ≤ 0,05° lange Kanten verdichtet; nach der Projektion auf Gültigkeit geprüft (keine Reparatur nötig).

| Land | Summe der Zellstücke (km²) | Umriss, gleiche Projektion | Umriss, geodätisch | Abw. Zellen/Umriss | Abw. Projektion/geodätisch | Grundeinheit ohne Sondereinheiten |
|---|---|---|---|---|---|---|
| Deutschland | 357 673,6 | 357 673,6 | 357 673,8 | 2·10⁻¹⁵ | −0,0001 % | 357 673,6 |
| Ägypten | 1 001 058,5 | 1 001 058,5 | 1 001 058,5 | 3·10⁻¹⁵ | 0,0000 % | 982 826,7 (ohne Halaib, Tiran/Sanafir) |
| Saudi-Arabien | 1 921 725,0 | 1 921 725,0 | 1 921 725,4 | 1·10⁻¹⁵ | 0,0000 % | 1 921 725,0 |
| Russland | 16 980 191,9 | 16 980 191,9 | 16 980 199,7 | 5·10⁻¹⁵ | 0,0000 % | 16 948 166,5 (ohne Krim, Kurilen) |
| Bahrain | 688,1 | 688,1 | 688,1 | 2·10⁻¹⁵ | +0,0007 % | 688,1 |

Die Flächen sind die der Grenzdatei, nicht amtliche Flächen. Laut Plausibilitätsprüfung weichen einige Umrisse deutlich von üblichen Angaben ab (Vergleichswerte teils aus dem Web, teils Allgemeinwissen des Prüfers): Transnistrien 3 052 statt etwa 4 160 km², Südossetien 4 465 statt etwa 3 900, Tibet 1 125 205 statt etwa 1 228 400, Gaza 339 statt 365, Saudi-Arabien 1,92 statt etwa 2,15 Mio. km², Singapur 510, Malediven 109. Ursache: die Umrisse von Natural Earth (Maßstab, Landgewinnung, umstrittene Ränder), nicht die Rechnung. Bei Transnistrien und Südossetien steht ein Hinweis in der Einheit (`umriss_hinweis`).

### Erhaltung und Summen
- Summe der Anteile je Zelle höchstens 1,0000000000002 (Rundung); Abbruch bei > 1 + 10⁻⁹.
- **Unabhängige Erhaltungsprüfung je Zelle** (Auflage statistik-pruefer): Summe der Anteile = Landanteil der Zelle aus der Vereinigung aller Länder der Grenzdatei; größte Abweichung 1,1·10⁻¹⁴ (Manifest). Es geht also nirgends Land verloren.
- 363 148 Zellen mit Land; 89 % sind zu mehr als 99,9 % Land; 11 067 Zellen teilen sich mehrere Einheiten.

### Datumsgrenze
- Alle Längen der Grenzdatei in [−180°, 180°]. Fidschi und Russland haben Zellen in Spalte 0 und 1439 (Tests).

### Stichproben (Plausibilitäts-Prüfer hat Zeile/Spalte nachgerechnet)
- Simferopol → krim 1,00 · Sewastopol → krim 0,92 (Rest Meer) · Donezk → donezk_2014 1,00 · Taiwan Inselmitte → taiwan 1,00 · Lhasa → tibet 1,00 · Nablus → westjordanland 1,00 · Grönland 72° N → groenland 1,00 · Berlin → land_DEU · Kairo → land_EGY · Atlantik 40° W / 30° N → keine Einheit.
- Gaza ist schmaler als eine Zelle (größter Anteil 0,348). Tests prüfen deshalb die ganzen Umrisse: Keine Grundeinheit (Israel, Ägypten; bei der Krim Russland und Ukraine; bei Tibet China, Indien, Nepal, Bhutan, Myanmar; bei Taiwan China; beim Westjordanland Israel, Jordanien; bei Grönland Dänemark, Kanada) überlappt die Sondereinheit um mehr als 0,001 km².

### Einheiten (324)
- 237 Grundeinheiten, 27 Sondereinheiten aus der Liste, 60 automatisch aus der Natural-Earth-Datei „umstrittene Gebiete“ (Regel: Anspruchsvermerk in `NOTE_BRK` oder Typ „Indeterminate“; nicht „Overlay“, „Lease“). Bei Überschneidung hat die kleinere Sondereinheit Vorrang (so bleibt z. B. die Hans-Insel in Grönland sichtbar). Tibet (aus der Provinzdatei) liegt nach der Prüfung vollständig in China; läge ein Provinz-Umriss außerhalb seines Landes, bricht der Bau ab.
- UN-Zuordnung: 234 über gleichen ISO-Code, 19 ausdrücklich belegt, 5 abgeleitet (Somaliland, Westjordanland, Gaza, Ostjerusalem, Tibet; Schluss steht beim Beleg), 63 unklar, 3 nicht in M49 (Dhekelia, Akrotiri, Guantánamo).
- **Grenze der UN-Sicht** (Befund statistik-pruefer): Sie ist nur so fein wie die Einheiten der Grenzdatei. 11 M49-Einträge haben keine eigene Einheit, weil Natural Earth sie mit dem Mutterstaat zusammenfasst oder aufteilt: 638 Réunion, 312 Guadeloupe, 474 Martinique, 254 Französisch-Guayana (in Frankreich), 535 Bonaire/Sint Eustatius/Saba, 074 Bouvetinsel, 744 Svalbard und Jan Mayen, 162 Weihnachtsinsel, 166 Kokosinseln (in „Indian Ocean Territories“ → Australien), 772 Tokelau, 239 Südgeorgien und Südliche Sandwichinseln (zwei automatische Einheiten, beide „unklar“).
- 43 Einträge nicht aufgenommen, jeder mit Grund: 21 Grundeinheiten ganz in Sondereinheiten (z. B. Taiwan, Kosovo, Grönland, Palästina = Westjordanland + Gaza), 5 Doppel, 7 Überlagerungen/Pacht (5 „Overlay“, z. B. koreanische Demilitarisierte Zone; 2 „Lease“: Baikonur, Guantánamo), 10 ohne Anspruchsvermerk. **Wichtig:** Diese 10 gehen im Staat auf, darunter große: „North Borneo“ (Sabah, 38 570 km²), „Belize“ (7 957 km²), dazu Ceuta, Melilla, zwei Donauinseln. Die Aussage „kein umstrittenes Gebiet geht still im Staat auf“ gilt also nur für Gebiete **mit Anspruchsvermerk in Natural Earth** oder aus der Liste. (Kosovo B57 steht mit Grund „kein Anspruch“ in der Liste; sein Umriss ist trotzdem als Einheit `kosovo` vorhanden.)

### Tabelle der Sondereinheiten aus der Liste (gekürzt; vollständig mit wörtlichen Zitaten in `aleph/layers/sondereinheiten.yaml`)

| Einheit | Kategorie | UN-Eintrag (Art) | UN-Beleg | beansprucht / verwaltet (laut NE, Mai 2022) | Weltbank-Sicht |
|---|---|---|---|---|---|
| Krim inkl. Sewastopol | umstritten, besetzt/Konfliktzone | 804 Ukraine (ausdrücklich) | A/RES/68/262 Ziff. 1, 5, 6; A/RES/71/205 „temporarily occupied“ | Ukraine / Russland | kein Land (unklar) |
| Donezk, Luhansk (Linie NE, Stichtag unklar) | umstritten, besetzt/Konfliktzone | 804 Ukraine (ausdrücklich) | A/RES/ES-11/4 | Ukraine / „Self admin.“ | UKR (unklar) |
| Taiwan | umstritten | 156 China (ausdrücklich) | M49 Q&A | China / eigene Verwaltung | keine Weltbank-Zahl |
| Kosovo | umstritten | 688 Serbien (ausdrücklich) | M49 Q&A | unklar | XKX (belegt) |
| Nordzypern | umstritten | 196 Zypern (ausdrücklich) | S/RES/541 (1983) | Zypern / eigene Verwaltung | keine |
| Somaliland | umstritten | 706 Somalia (abgeleitet) | S/RES/2767 (2024) Präambel | Somalia / eigene Verwaltung | SOM (unklar) |
| Abchasien, Südossetien | umstritten | 268 Georgien (ausdrücklich) | A/RES/77/293 | Georgien / eigene Verwaltung | keine (Georgien ohne) |
| Transnistrien | umstritten | 498 Moldau (ausdrücklich) | A/RES/72/282 | Moldau / eigene Verwaltung | keine (Moldau ohne) |
| Bergkarabach | umstritten, besetzt/Konfliktzone | 031 Aserbaidschan (ausdrücklich) | A/RES/62/243 | Aserbaidschan / „Self admin.“ | AZE (unklar) |
| Golanhöhen | besetzt/Konfliktzone, umstritten | 760 Syrien (ausdrücklich) | S/RES/497 (1981) | Syrien / Israel | ISR (unklar) |
| Westjordanland | besetzt/Konfliktzone | 275 Palästina (abgeleitet) | M49 + S/RES/2334 (2016) | unklar | PSE (belegt) |
| Gazastreifen | besetzt/Konfliktzone | 275 Palästina (abgeleitet) | S/RES/1860 (2009) nennt einen künftigen Staat | unklar | PSE (belegt) |
| Ostjerusalem (Erweiterung) | besetzt/Konfliktzone, umstritten | 275 (abgeleitet) | S/RES/2334 nennt es ausdrücklich | Palästina / Israel | ISR (unklar) |
| Westsahara, 2 Teile | umstritten | 732 Westsahara (eigener M49-Eintrag) | M49 | gegenseitig Marokko/Westsahara | MAR (abgeleitet bzw. unklar) |
| Kaschmir, 6 Teile | umstritten | unklar | S/RES/47 (1948), Präambel: beide Staaten wünschen ein Plebiszit | je Teil Indien/Pakistan/China | unklar |
| Hongkong, Macau | Sonderstatus/autonom | 344, 446 (ausdrücklich) | M49-Einträge, Fußnoten 5, 6 | – | HKG, MAC (belegt) |
| Grönland | Sonderstatus/autonom | 304 (ausdrücklich) | M49-Eintrag | – | GRL (belegt) |
| Tibet | Sonderstatus/autonom | 156 China (abgeleitet) | M49 führt Tibet nicht; keine abweichende UN-Aussage gefunden | – | CHN (abgeleitet) |

Anerkennung (Zahl der Staaten) ist überall „unklar“. Wo eine UN-Resolution zur Nichtanerkennung aufruft (Krim, Donezk/Luhansk, Nordzypern), ist das zitiert. Die Zitate hat der Plausibilitäts-Prüfer gegen die Resolutionstexte gelesen: wörtlich oder nur durch Lesefehler des PDF-Textes verschieden (z. B. „Jam.mu“, „Sevastop ol“). Wertende Wörter stehen nur in Zitaten.

Erweiterungen über die vorgegebene Liste, mit Begründung: Ostjerusalem (S/RES/2334 nennt es ausdrücklich); Westsahara in zwei Teilen (Natural Earth trennt verwalteten und selbstverwalteten Teil); alle Einträge der Natural-Earth-Datei mit Anspruchsvermerk (z. B. Arunachal Pradesh, Essequibo-Gebiet, Abyei, Halaib-Dreieck, Kurilen, Falklandinseln, Mayotte, Hans-Insel) nach fester Regel. Deren UN-Angabe ist „unklar“, außer wo M49 das Gebiet eigens führt (Falkland 238, Gibraltar 292, Mayotte 175).

### Zu klein für 0,25° (Fläche kleiner als eine Zelle): 104 Einheiten
- 73 davon tragen einen Weltbank-Code. Zusammengefasst je Weltbank-Land sind **37 Weltbank-Länder** kleiner als eine Zelle (Summe der Anteile): GIB 0,006, TUV 0,030, SXM 0,032, MCO 0,034, NRU 0,037, MAC 0,042, MAF 0,093, BMU 0,096, SMR 0,108, MDV 0,142, VGB 0,198, MHL 0,216, ABW 0,226, ASM 0,242, LIE 0,260, KNA 0,359, CHI 0,381, CYM 0,426, GRD 0,461, VIR 0,484, VCT 0,491, MLT 0,520, SYC 0,570, BRB 0,593, ATG 0,614, CUW 0,616, TCA 0,622, PLW 0,644, SGP 0,664, GUM 0,754, MNP 0,784, AND 0,793, LCA 0,810, FSM 0,830, TON 0,834, DMA 0,984, BHR 0,993.
- Die übrigen sind Sondereinheiten (z. B. Gaza 0,515, Ostjerusalem 0,101) und Gebiete ohne Weltbank-Code (z. B. Vatikan, in 1:10m nur 0,012 km²). Sapodilla Cayes und Doumera haben 0 km² (Umriss außerhalb der Landfläche der Länderdatei).
- **Auflage statistik-pruefer:** „kleiner als eine Zelle“ misst Fläche, nicht Vermischung mit Nachbarn. Deshalb gibt es jetzt zusätzlich das **Reinheitsmaß** `reinheit()`: Anteil der Fläche eines Weltbank-Landes in Zellen, in denen es mindestens 90 % des Landes der Zelle stellt (ohne BIP berechenbar). Hauptsicht: 16 von 236 Codes haben Reinheit < 0,5, u. a. Andorra, Liechtenstein, San Marino, Monaco, Singapur, Macau (je 0), Gambia 0,31, Luxemburg 0,37, Brunei 0,37, Palästina 0,43.

## Umfang

- **Neu:** `aleph/layers/un_m49.py`, `aleph/layers/zell_einheiten.py`, `aleph/layers/sondereinheiten.yaml`, `tests/test_zell_einheiten.py`, `tests/test_un_m49.py`, `docs/sources/un_m49.md`, `docs/sources/cshapes.md` (vom `datenquellen-scout`).
- **Geändert:** `aleph/layers/natural_earth.py` (Zusatzdateien; bestehende Funktionen unverändert), `docs/sources/natural_earth.md` (Abschnitt 16, datierte Korrektur), `berichte/2026-09-25_laendergrenzen.md` (Nachtrag), `ARCHITECTURE.md` (Absatz Länderzuordnung).
- **Auf der SSD neu:** `raw/natural_earth/5.1.1_umstritten/`, `raw/natural_earth/5.1.1_provinzen/`, `raw/un_m49/20260925T224431Z/`, `raw/un_dokumente/20260925T2235Z/` (18 UN-Resolutionen als PDF mit Prüfsummen), `laender/zell_einheiten/` (Einheiten mit Umrissen, Zuordnung, Nicht-Aufgenommenes, Manifest mit Prüfsummen der Quellen und des Ergebnisses, Version der Grenzdatei, Git-Stand).
- **Nicht angefasst:** Download 41131, `vnp46a3*.py`, Kachelliste, `scripts/`, `.env`. Würfel nur gelesen (Koordinaten).
- **Prüfer:**
  - `statistik-pruefer`: „bestanden mit Auflagen“. Für Phase 3 umgesetzt: Tests der Bau-Regeln mit Beispielflächen (Vorrang, Wegfall, Doppel, Overlay/Lease, M49 über Namen, geteilter ISO-Code), Erhaltungsprüfung je Zelle gegen die Landfläche, Abbruch bei Provinz-Umriss außerhalb des Mutterlandes, Gültigkeitsprüfung nach der Projektion, Reparaturen der Zusatzdateien ins Manifest, schärfere Toleranz (10⁻⁴) gegen die geodätische Fläche, Randstreifen-Tests über ganze Umrisse, unbenutzter Code entfernt, Reinheitsmaß und Weltbank-Sicht als Funktionen, Aussagen im Bericht eingeschränkt. Offen für Phase 5 siehe Empfehlung.
  - Plausibilitäts-Prüfer (allgemeiner Agent mit der Anleitung aus `.claude/agents/plausibilitaets-pruefer.md`, weil der Typ in der Sitzung nicht verfügbar war): „plausibel mit Vorbehalt“. Umgesetzt: Gaza „abgeleitet“ statt „ausdrücklich“; Kaschmir-Zitat mit Satzanfang („Noting with satisfaction that both India and Pakistan desire …“); Krim ohne Weltbank-Kandidat (sonst zählte die Krim bei Zusammenfassung nach Code still zu Russland); Hinweise zu Bergkarabach (Zeitstand), Transnistrien, Südossetien; Aussage zu umstrittenen Gebieten eingeschränkt; Einheiten ohne Fläche genannt. Nicht umgesetzt: Zitat aus S/RES/2334 mit großem „T“ – geprüft: Die zitierte Ziffer 1 schreibt „territory“ klein, die Präambel groß; das Zitat ist wörtlich.
- Evidenzstufe: keine Messung. Die Zuordnung ist eine Festlegung aus Umrissen (Natural Earth) und UN-Dokumenten.

## Empfehlung

**Vor Phase 5 festzulegen (Auflagen statistik-pruefer), ohne das BIP anzusehen:**
1. **Verteilung des Lichts in Küsten- und Grenzzellen.** Vorschlag des Prüfers: Lichtsumme einer Zelle L = Mittelwert × Zahl gültiger Pixel × Pixelfläche; Anteil eines Landes = L × a / S (S = Summe der Landanteile der Zelle); Zellen mit S < s_min (z. B. 0,05) nicht verteilen, getrennt ausweisen; Gegenproben mit s_min 0,01 und 0,2 und ohne Normierung. Vorher klären, ob Meerpixel im Würfel gültig (dunkel) oder Fehlwerte sind.
2. **Ausschluss nach Reinheit** statt nach „kleiner als eine Zelle“; Schwelle (z. B. R < 0,5) vorher festlegen.
3. **Weltbank-Sicht:** Hauptsicht `weltbank_sicht(mit_unklar=True)` (sonst verlöre z. B. Guyana 74 % seiner Fläche, Marokko 30 %), Gegenprobe ohne „unklar“; Länder mit hohem Anteil unklarer Fläche getrennt ausweisen. Tansania (BIP nur Festland) aus der Hauptrechnung nehmen oder Sansibar abziehen.

**Zeitabhängigkeit (Plan, nicht gebaut):**
1. Jede Sondereinheit bekommt Gültigkeitszeiträume (von/bis, Monat) für Status und Umriss; frühere Zustände bleiben als eigene Zeilen, nichts wird überschrieben.
2. Zuordnung je Zeitraum getrennt rechnen, Gültigkeit im Manifest.
3. Quellen: CShapes 2.0 (ETH Zürich, Schvitz et al. 2022, Journal of Conflict Resolution) reicht nur bis 31.12.2019, ordnet nicht anerkannte Gebiete dem Mutterstaat und umstrittene nach tatsächlicher Kontrolle zu, Lizenz CC BY-NC-SA, keine ISO3-Codes; brauchbar nur als Gegenprobe 2013–2019 (Steckbrief `docs/sources/cshapes.md`, Scout; Krim 2014 dort nur in einer Drittkopie gesehen). Für die Ukraine ab 2014/2022 und Bergkarabach vor 2020 und ab 2023 fehlt eine geprüfte Quelle mit Umrissen je Zeitpunkt; erst suchen und prüfen, nichts selbst nachzeichnen.
4. Bis dahin: Ergebnisse, die diese Gebiete berühren, mit „Umriss Stand Mai 2022“ kennzeichnen.

**Kartendarstellung (Plan, nicht gebaut):** Sondereinheiten mit Schraffur und Farbe je Kategorie; beim Antippen die Angaben aus der YAML (UN-Eintrag mit Art und Beleg, Anspruch, Verwaltung, Status, Anerkennung, Gültigkeit, Weltbank-Sicht, Umriss-Hinweis). Bei „unklar“ steht „unklar“; die Karte behauptet keine Zugehörigkeit, die nicht belegt ist. Umrisse liegen schon im Ergebnis (`umriss_wkb`, EPSG:6933).

**Weitere Entscheidungen für dich:** ob „North Borneo“ (Sabah) und „Belize“ trotz fehlendem Anspruchsvermerk eigene Einheiten werden sollen; ob die 11 M49-Einträge ohne eigene Einheit (z. B. Réunion, Französisch-Guayana) aus einer feineren Quelle getrennt werden sollen.

## Nicht geprüft

- Genauigkeit der Umrisse (kein Vergleich mit einer zweiten Kartenquelle); Stichtag der Linien für Donezk, Luhansk und Bergkarabach.
- Status der Westsahara auf der UN-Liste der Hoheitsgebiete ohne Selbstregierung (Seite zum Abruf gesperrt).
- Zahl der anerkennenden Staaten; UN-Aussagen zu Tibet, Somaliland (ausdrücklich), Kaschmir außer S/RES/47 und zu den automatisch aufgenommenen Gebieten.
- Die Resolutionstexte wurden mit pypdf aus den PDFs gewonnen und die Stellen darin gelesen (keine Zusammenfassung durch ein Hilfsmodell); bei S/RES/541 und S/RES/47 sind die PDFs Sammelseiten. Die Seiten wurden nicht als Bild geprüft.
- Vergleichsflächen des Plausibilitäts-Prüfers stammen teils aus seinem Allgemeinwissen (im Prüfbericht gekennzeichnet).
- Beide Prüfer konnten keinen Code ausführen; alle Zahlen stammen aus meinen Läufen.
