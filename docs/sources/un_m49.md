# Steckbrief: UN M49 (Standard country or area codes for statistical use)

Stand: 2026-09-26 · Status: eingebaut als oberste Ebene der Länderzuordnung (`aleph/layers/un_m49.py`)

## 1. Anbieter und Adresse

- United Nations Statistics Division (UNSD).
- Übersichtstabelle: https://unstats.un.org/unsd/methodology/m49/overview/
- Hauptseite mit „Questions & Answers“ und Fußnoten: https://unstats.un.org/unsd/methodology/m49/
- Abgerufen am 2026-09-25 22:44:31 UTC, gespeichert unverändert (HTML) unter `raw/un_m49/20260925T224431Z/` mit Manifest (SHA-256 je Seite).

## 2. Inhalt

- Liste der Länder und Gebiete mit dreistelligem Zahlencode (M49), ISO-alpha2/-alpha3 und Regionen. Englische Tabelle: 248 Einträge (eigene Zählung; die Seite nennt keine Zahl).
- **Keine Grenzlinien.** M49 sagt, welche Einträge es gibt, nicht, welche Fläche zu einem Eintrag gehört.
- Vorbehalt der Quelle (Hauptseite, wörtlich): „The designations employed and the presentation of material at this site do not imply the expression of any opinion whatsoever on the part of the Secretariat of the United Nations concerning the legal status of any country, territory, city or area or of its authorities, or concerning the delimitation of its frontiers or boundaries.“ Und: „The assignment of countries or areas to specific groupings is for statistical convenience and does not imply any assumption regarding political or other affiliation of countries or territories by the United Nations.“

## 3. Gebiete, die M49 nicht eigens führt (geprüft)

- **Kosovo** (Questions & Answers, wörtlich): „The status of Kosovo should be understood to be in the context of United Nations Security Council resolution 1244 (1999). As a result, within the "Standard country or area codes for statistical use (M49)", Kosovo is currently considered part of Serbia (numerical code 688). However, for strictly statistical purposes, the numerical code 412 can be used to represent this area.“
- **Taiwan** (Questions & Answers, wörtlich): „On the 25 th October 1971, the UN General Assembly adopted a resolution (2758) to recognize the representatives of the Government of the People's Republic of China as the only legitimate representatives of China to the United Nations. As a result, within the M49, Taiwan Province of China is considered part of China (numerical code 156). However, for strictly statistical purposes, the numerical code 158 can be used to represent this area.“
- Eigene Einträge hat M49 u. a. für Westsahara (732), Staat Palästina (275), Grönland (304), Hongkong (344), Macau (446), Falklandinseln (Malwinen) (238), Gibraltar (292), Mayotte (175).
- Nicht als eigener Eintrag und ohne Hinweis auf der Seite: Krim, Abchasien, Südossetien, Transnistrien, Bergkarabach, Nordzypern, Somaliland, Kaschmir, Tibet. Für diese stützt ALEPH die Zuordnung auf UN-Resolutionen (Belege in `aleph/layers/sondereinheiten.yaml`) oder führt sie als „unklar“.

## 4. Zugang, Lizenz

- Frei, ohne Konto. Der Abruf braucht eine Browser-Kennung (User-Agent). Nutzungsbedingungen der Seite: nicht geprüft.

## 5. Rolle in ALEPH

- Oberste Ebene: Jede Einheit der Zell-Zuordnung (`aleph/layers/zell_einheiten.py`) trägt ihren übergeordneten M49-Eintrag oder „unklar“, mit Art des Belegs (ausdrücklich, abgeleitet, gleicher ISO-Code, unklar).
- Zuordnung einer Grenzdatei-Einheit zu M49 über den ISO-alpha3-Code (Natural-Earth-Feld ISO_A3_EH); drei Einheiten haben keinen: Dhekelia, Akrotiri (britische Stützpunkte auf Zypern), US-Marinestützpunkt Guantánamo.

## 6. Nicht geprüft

- Wie oft und mit welcher Ankündigung UNSD die Liste ändert.
- Nutzungsbedingungen der Seite.
- Ob andere UN-Stellen (z. B. Kartographie-Abteilung) abweichende Zuordnungen verwenden.
