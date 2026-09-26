# Welche Gebiete stecken in den Weltbank-Zahlen? (Phase 2)

Stand: 2026-09-26 (Abrufe am 2026-09-25 zwischen 22:17 und 22:36 UTC) · Reihen: reales BIP `NY.GDP.MKTP.KD`, Bevölkerung `SP.POP.TOTL` (dazu `NY.GDP.PCAP.KD` als Prüfgröße)

## Kurzfassung

- Quelle: offizielles WDI-Gesamtpaket der Weltbank (Stand der Weltbank 15.07.2026) mit den Tabellen „Special Notes“ (je Land), „Country-Series“ (je Land und Reihe) und Jahres-Fußnoten. Alle Zitate unten sind wörtlich aus diesen Dateien kopiert, nicht zusammengefasst.
- **Klar belegt, Gebiet passt nicht zur Grenzdatei:** Georgien (ohne Abchasien/Südossetien), Moldau (ohne Transnistrien), Tansania (BIP nur Festland), Marokko (BIP deckt Westsahara ab), Zypern (BIP nur Gebiet unter Kontrolle der Regierung).
- **Klar belegt, passt:** Serbien ohne Kosovo / Kosovo getrennt; China ohne Hongkong, Macau, Taiwan; Sudan ohne Südsudan ab 9.7.2011.
- **Unklar (keine Angabe der Weltbank):** Russland/Ukraine (welche Gebiete ab 2014), Israel/Palästina (Ostjerusalem, Golan), Somalia/Somaliland, Aserbaidschan/Bergkarabach, Indien/Pakistan/China (Kaschmir), Syrien (Golan), Sudan (Abyei).
- **Russland/Ukraine, die frühere Auffälligkeit:** teilweise erklärt. Belegt ist: Das BIP 2014 und 2015 beruht laut Fußnote auf „official statistics of Ukraine and Russian Federation“. Nachgerechnet: Der Nenner der Pro-Kopf-Werte enthält bei Russland ab 2014 2,27–2,48 Mio. Menschen **mehr**, bei der Ukraine genau so viele **weniger** als die Bevölkerungsreihe. Dass es sich um Krim und Sewastopol handelt, sagt die Weltbank **nicht**; das bleibt eine Vermutung.
- Taiwan hat keine Weltbank-Zahl; Westsahara, Nordzypern, Somaliland, Abchasien, Südossetien, Transnistrien haben keine eigene.
- Evidenzstufe: beobachtet (Herstellerangaben) und eigene Rechnung an Weltbank-Zahlen.

## Urteil

Für die Nachtlicht-BIP-Auswertung dürfen die Länder nicht blind über `land_iso3` mit den Grenzen verknüpft werden. Für 5 Länder ist belegt, dass Weltbank-Zahl und Grenzfläche verschiedene Gebiete meinen (Tabelle, „passt: nein“). Für 9 weitere ist es unklar. Mit den neuen Sondereinheiten aus Phase 3 lassen sich die belegten Fälle sauber abbilden (Gebiet abziehen oder zuschlagen), die unklaren werden markiert und in einer Vergleichsrechnung ausgeschlossen.

## Belege

**Quellen** (alle abgerufen am 2026-09-25, UTC):

1. WDI-Gesamtpaket: `https://databank.worldbank.org/data/download/WDI_CSV.zip`, Abruf 22:17–22:28 UTC, HTTP 200, 282 845 220 Byte, Server-Datum „Last-Modified: Wed, 15 Jul 2026 02:19:16 GMT“, SHA-256 `2ab1d0d250ebe986ac8a9f7163f6e177fbe4cfb2750f822b18578d902aeb134f`. Gelesen: `WDICountry.csv` (Spalte „Special Notes“), `WDIcountry-series.csv` (Spalte „DESCRIPTION“), `WDIfootnote.csv`, `WDISeries.csv`. Die Dateien liegen nur im Zwischenordner der Sitzung (nicht im Projekt, nicht auf der SSD).
2. Weltbank-API, Länder-Metadaten: `https://api.worldbank.org/v2/sources/2/country/UKR/metadata?format=json` (und `/country/{UKR,RUS}/series/{NY.GDP.MKTP.KD,SP.POP.TOTL,NY.GDP.PCAP.KD}/metadata`), 22:17 UTC. Liefert für Ukraine und Russland nur Stammdaten (Währung, Zensusjahr usw.), **keine** Gebietshinweise.
3. Eigene Rechnung an der ALEPH-Weltbank-Tabelle (`laender/weltbank.parquet`, Abruf 2026-09-23 15:59 UTC, nur gelesen).

**Definitionen der Reihen** (`WDISeries.csv`, wörtlich):
- `NY.GDP.MKTP.KD`: „Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period.“ Welches Gebiet „economic territory“ je Land ist, steht dort nicht.
- `SP.POP.TOTL`: „Total population is based on the de facto definition of population, which counts all residents regardless of legal status or citizenship. The values shown are midyear estimates.“

**Nachrechnung Pro-Kopf-Nenner** (BIP geteilt durch BIP pro Kopf, minus Bevölkerungsreihe, in Mio. Personen; Abruf 2026-09-23):

| Land | 2013 | 2014 | 2016 | 2018 | 2020 | 2022 |
|---|---|---|---|---|---|---|
| Russland | 0,000 | +2,271 | +2,366 | +2,421 | +2,462 | +2,477 |
| Ukraine | 0,000 | −2,271 | −2,366 | −2,421 | −2,462 | −2,477 |
| Zypern | −0,321 | −0,341 | −0,370 | −0,386 | −0,394 | −0,392 |
| Marokko | +0,457 | +0,473 | +0,500 | +0,526 | +0,549 | +0,569 |
| Tansania | −1,424 | −1,477 | −1,595 | −1,721 | −1,846 | −1,981 |

Lesart: Positiv heißt, der Pro-Kopf-Wert bezieht sich auf mehr Menschen als die Bevölkerungsreihe zählt.

**Hauptergebnis: Tabelle je Land**

„Grenzdatei“ = Natural Earth 5.1.1, Admin 0, 1:10m, Standardansicht (so wie in `aleph/layers/natural_earth.py`).

| Land | Was die Weltbank-Zahl abdeckt (wörtlicher Beleg) | Was die Grenzdatei abdeckt | passt | Vorschlag |
|---|---|---|---|---|
| **Ukraine (UKR)** | BIP, Fußnote 2014 und 2015: „Based on data from official statistics of Ukraine and Russian Federation; by relying on these data, the World Bank does not intend to make any judgment on the legal or other status of the territories concerned or to prejudice the final determination of the parties' claims.“ Pro Kopf, Country-Series: gleicher Wortlaut („Based on national accounts data from official statistics of Ukraine and Russian Federation; …“). Bevölkerung: „Data source: United Nations World Population Prospects“. Welche Gebiete: **nicht genannt**. Rechnung: Pro-Kopf-Nenner ab 2014 um 2,27–2,48 Mio. kleiner als die Bevölkerungsreihe. | ohne Krim (Krim im Umriss Russlands), mit Donezk und Luhansk | unklar | Ukraine und Russland in der Hauptrechnung ausschließen, in einer Vergleichsrechnung aufnehmen. Krim ist in Phase 3 eine eigene Einheit. |
| **Russland (RUS)** | BIP: gleiche Fußnote 2014, 2015. Bevölkerung: „Data source: Russian Federation Federal State Statistics Service, 1979 Census, 1989 Census“. Rechnung: Pro-Kopf-Nenner ab 2014 um 2,27–2,48 Mio. größer. | mit Krim, mit Kurilen | unklar | wie Ukraine |
| **Zypern (CYP)** | Pro Kopf: „Data are for areas under the effective control of the Government of the Republic of Cyprus.“ Bevölkerung: UN WPP. Rechnung: Pro-Kopf-Nenner 0,32–0,39 Mio. kleiner als die Bevölkerungsreihe. Da BIP = Pro-Kopf-Wert × Nenner, gilt das BIP für dasselbe Gebiet (Schluss aus der Rechnung, nicht wörtlich belegt). | ohne Nordzypern (eigene Einheit), ohne UN-Pufferzone | BIP ja (abgeleitet), Bevölkerung nein | BIP verwenden; Bevölkerungsreihe für Zypern nicht als Nenner verwenden |
| **Serbien (SRB) / Kosovo (XKX)** | Special Notes Serbien: „data from 1999 onward for Serbia for most indicators exclude data for Kosovo, 1999 being the year when Kosovo became a territory under international administration pursuant to UN Security Council Resolution 1244 (1999); any exceptions are noted. Kosovo became a World Bank member on June 29, 2009; available data are shown separately for Kosovo.“ Bevölkerung Serbien: „Note: Excluding Kosovo.“ | getrennte Einheiten | ja | verknüpfen wie bisher |
| **Marokko (MAR) / Westsahara** | Pro Kopf: „Data cover Western Sahara.“ Bevölkerung: UN WPP. Rechnung: Pro-Kopf-Nenner 0,46–0,57 Mio. größer als die Bevölkerungsreihe, also enthält das BIP die Westsahara, die Bevölkerungsreihe nicht (Schluss aus der Rechnung). Ob die ganze Westsahara oder nur der von Marokko verwaltete Teil: nicht genannt. | von Marokko verwalteter Teil im Umriss Marokkos, östlicher Rest eigene Einheit (SAH) | nein | BIP Marokkos gegen Marokko + Westsahara (von Marokko verwalteter Teil) rechnen; markieren, weil der Umfang unklar ist |
| **Georgien (GEO)** | Special Notes: „Includes self-governed areas only, which mostly exclude Abkhazia and South Ossetia, but small areas in Abkhazia and South Ossetia are included before 2008 or 2009 because of the changes in self-governed areas.“ Pro Kopf: „Excludes Abkhazia and South Ossetia.“ | mit Abchasien und Südossetien | nein | Abchasien und Südossetien abziehen (in Phase 3 eigene Einheiten) |
| **Moldau (MDA)** | Special Notes: „Excluding Transnistria. For 1950-94, World Bank estimates using UN World Population Prospects' growth rates of whole Moldova.“ Pro Kopf: „Excludes Transnistria.“ | mit Transnistrien | nein | Transnistrien abziehen (eigene Einheit) |
| **Sudan (SDN) / Südsudan (SSD)** | BIP, Fußnote 2011: „Excludes South Sudan after July 9, 2011.“ Bevölkerung: „Estimates are for Sudan excluding South Sudan.“ | getrennt; Abyei liegt im Umriss Sudans | ja (Abyei unklar) | verknüpfen; Abyei eigene Einheit, Sudan markieren |
| **China (CHN), Hongkong (HKG), Macau (MAC), Taiwan** | Special Notes China: „Unless otherwise noted, data for China do not include data for Hong Kong SAR, China; Macao SAR, China; or Taiwan, China.“ Taiwan steht nicht in der Weltbank-Länderliste. | Hongkong, Macau, Taiwan getrennt; Aksai Chin und Shaksgam im Umriss Chinas | ja (Aksai Chin, Shaksgam unklar) | verknüpfen; Taiwan fällt nur aus der Weltbank-Auswertung heraus |
| **Israel (ISR) / Westjordanland und Gaza (PSE)** | Weltbank-Name des Eintrags PSE: „West Bank and Gaza“. Bevölkerung PSE: „World Bank estimates based on data from Palestinian Central Bureau of Statistics, excluding E. Jerusalem.“ Israel: keine Gebietsangabe. | Palästina (Westjordanland + Gaza) eigene Einheit; Ostjerusalem und Golan im Umriss Israels | unklar | Israel, Palästina (und Syrien wegen Golan) markieren, in der Vergleichsrechnung ausschließen |
| **Somalia (SOM) / Somaliland** | keine Gebietsangabe gefunden | Somaliland eigene Einheit, nicht bei Somalia | unklar | Somalia markieren |
| **Aserbaidschan (AZE) / Bergkarabach** | BIP und Gesamtbevölkerung: keine Gebietsangabe. Nur Reihen aus UN WPP (z. B. Geburten, Sterblichkeit) tragen „Including Nagorno-Karabakh.“ | Bergkarabach im Umriss Aserbaidschans | unklar | Aserbaidschan (und Armenien) markieren |
| **Indien (IND), Pakistan (PAK) / Kaschmir** | keine Gebietsangabe gefunden | nach Verwaltung aufgeteilt (Standardansicht) | unklar | markieren |
| **Tansania (TZA)** | Pro Kopf: „Data cover mainland Tanzania only.“ Rechnung: Pro-Kopf-Nenner 1,4–2,0 Mio. kleiner als die Bevölkerungsreihe, also BIP nur Festland (Schluss aus der Rechnung); Reihen aus UN WPP tragen „Including Zanzibar.“ | mit Sansibar | nein | Sansibar abziehen (Geometrie aus der NE-Provinzdatei) oder markieren; in dieser Sitzung: markieren |
| **Frankreich (FRA)** | Bevölkerung: „Including the French overseas departments of French Guiana, Guadeloupe, Martinique, Mayotte, and Réunion.“ BIP: keine Angabe. | mit diesen Übersee-Departements | Bevölkerung ja, BIP unklar | verknüpfen, BIP-Gebiet offen lassen |
| **Dänemark (DNK) / Grönland (GRL)** | Grönland ist eigener Weltbank-Eintrag. Ob die Zahlen Dänemarks Grönland/Färöer ausschließen: keine Angabe. | getrennte Einheiten | vermutlich ja, nicht belegt | verknüpfen |
| **Syrien (SYR)** | keine Gebietsangabe | ohne Golan (im Umriss Israels) | unklar | markieren |

Gesucht wurde in allen 7 939 Country-Series-Hinweisen und allen Jahres-Fußnoten zu BIP und Bevölkerung nach: Crimea, Sevastopol, Abkhaz, Ossetia, Transnistria, Kosovo, Karabakh, Somaliland, Northern Cyprus, occupied, Western Sahara, Kashmir, Golan, Zanzibar, Taiwan, Donbas, Donetsk, Luhansk. Treffer nur wie in der Tabelle zitiert. „Crimea“, „Sevastopol“, „Donetsk“, „Luhansk“, „Kashmir“, „Golan“, „Somaliland“: **kein** Treffer.

**Die bisherige Auffälligkeit bei Russland und der Ukraine**

- Belegt: Ab 2014 stützt die Weltbank das BIP beider Länder auf die amtlichen Statistiken beider Länder und will damit ausdrücklich keine Aussage über den Status „der betroffenen Gebiete“ treffen (Fußnote oben).
- Belegt durch Rechnung: Der Unterschied beginnt genau 2014, ist in beiden Ländern gleich groß und spiegelbildlich. Die Pro-Kopf-Werte Russlands beziehen sich auf 2,27–2,48 Mio. Menschen mehr, die der Ukraine auf ebenso viele weniger, als die jeweilige Bevölkerungsreihe zählt. Die Pro-Kopf-Reihen und die Bevölkerungsreihe verwenden also ab 2014 eine unterschiedliche Abgrenzung.
- **Nicht belegt:** dass diese Menschen die Bewohner der Krim und Sewastopols sind, und welche Gebiete das BIP Russlands bzw. der Ukraine ab 2014 genau enthält (Krim? Teile von Donezk und Luhansk?). Zeitpunkt und Wortlaut „territories concerned“ passen zur Krim; das bleibt eine Vermutung.
- Folge: Die Auffälligkeit ist in ihrem Mechanismus erklärt, im Gebiet nicht. Für eine Länderauswertung gelten Russland und Ukraine ab 2014 als „Gebiet unklar“.

## Umfang

- Nur gelesen: Weltbank-Paket und -API, die ALEPH-Weltbank-Tabelle auf der SSD. Nichts im Projekt geändert außer diesem Bericht.
- Die Evidenzstufe der Tabelle ist „beobachtet“ (Angaben der Weltbank) bzw. eigene Rechnung an den Weltbank-Zahlen. Schlüsse der Art „BIP = Pro-Kopf × Nenner, also gleiches Gebiet“ sind als „abgeleitet“ gekennzeichnet.
- Das Weltbank-Paket (Stand 15.07.2026) ist neuer als der ALEPH-Abruf (2026-09-23 über die API). Die Nachrechnung nutzt den ALEPH-Abruf; die Hinweise das Paket.

## Empfehlung

1. In der Auswertung eine ausdrücklich benannte **Sicht „so wie die Weltbank zählt“** verwenden: Georgien ohne Abchasien und Südossetien, Moldau ohne Transnistrien, Zypern ohne Nordzypern, Marokko mit dem von Marokko verwalteten Teil der Westsahara, Serbien ohne Kosovo, China ohne Hongkong, Macau, Taiwan (umgesetzt in Phase 3 als Spalte `weltbank_code` je Einheit).
2. Länder mit „unklar“ in der Hauptrechnung markieren und in einer Vergleichsrechnung ausschließen: Russland, Ukraine, Israel, Palästina, Syrien, Somalia, Aserbaidschan, Armenien, Indien, Pakistan, Sudan, Tansania, Marokko (Umfang).
3. Für Russland/Ukraine bei den Statistikämtern (Rosstat, Ukrstat) nachlesen, welche Gebiete sie ab 2014 einschließen. Das ist eine Frage an die Originalquelle, nicht an die Weltbank.
4. Bevölkerung von Zypern, Marokko und Tansania nicht als Nenner des BIP verwenden (anderes Gebiet).

## Nicht geprüft

- Welche Gebiete die amtlichen Statistiken Russlands und der Ukraine ab 2014 umfassen.
- Ob „Data cover Western Sahara“ die ganze Westsahara meint.
- Welches Gebiet das BIP Israels umfasst (Ostjerusalem, Golan, Siedlungen), welches das BIP Somalias (Somaliland), Aserbaidschans (Bergkarabach), Indiens und Pakistans (Kaschmir).
- Die Weltbank-Datenkataloge außerhalb des WDI-Pakets (z. B. Länderseiten auf data.worldbank.org) wurden nicht gelesen.
- Einwohnerzahl der Krim: nicht an einer Quelle geprüft, deshalb auch kein Größenvergleich mit den 2,27–2,48 Mio.
