# Nachtlicht × reales BIP, Querschnitt 2018 (Gegenprobe 2019)

Stand: 2026-09-28 (Rechnung 19:17 UTC) · Code: `aleph/link/nachtlicht_bip_querschnitt.py` (neu), Tests `tests/test_nachtlicht_bip_querschnitt.py` (neu) · Ergebnisdatei: `auswertungen/nachtlicht_bip_querschnitt/ergebnis.json` auf der SSD · Anzeige: Globus im worktree (`web/globus_auswertung.js`)

## Kurzfassung

- **Evidenzstufe: statistische Assoziation.** Querschnitt, ein Jahr, Afrika-Europa-Asien, kein Beleg für Ursache und Wirkung.
- **2018:** 125 Länder. 1 % mehr reales BIP geht im Mittel mit etwa 0,94 % mehr Nachtlicht einher (95-%-Bereich 0,85 bis 1,03), R² 0,81.
- **2019:** 123 Länder, Steigung 0,95 (0,86 bis 1,05), R² 0,80.
- Alle Gegenrechnungen (reine Zellen, Reinheit 30 % / 70 %, ohne Länder mit wenigen guten Monaten) liegen zwischen 0,93 und 0,98.
- Russland, Norwegen und Island fallen nach Regel 5 heraus (zu wenig Licht mit gültigem Jahreswert). Das weicht von der Erwartung im Auftrag ab („Russland drin lassen“); die Regel gilt.
- Nach dem ersten Lauf ein Umsetzungsfehler behoben: 12 Länder aus Amerika und Ozeanien waren drin. Keine Schwelle geändert.
- Größte Abweichungen: Irak rund 11-mal mehr Licht als die Linie; Isle of Man, Komoren, Kanalinseln rund 20-mal weniger.
- **Nicht geprüft vom statistik-pruefer** (Anweisung des Nutzers für diese Sitzung). Das muss vor einer Veröffentlichung nachgeholt werden.

## Urteil

Die Rechnung läuft nach den festgelegten Regeln, ist mit künstlichen Daten getestet (9 Tests) und in sich stimmig: 2018 und 2019 geben fast dieselbe Steigung, und keine Gegenrechnung verschiebt sie über den Unsicherheitsbereich hinaus. Für die Präsentation taugt die Aussage „In diesem Querschnitt haben Länder mit höherem realem BIP im Mittel mehr Nachtlicht, ungefähr im gleichen Verhältnis“. Sie taugt nicht für Aussagen über Ursache, über Veränderung in der Zeit oder über einzelne Länder.

Einschränkung: Die Methodenprüfung durch den `statistik-pruefer` fehlt. CLAUDE.md verlangt sie, bevor ein Ergebnis in Oberfläche oder Präsentation geht. Auf dem Globus steht das deshalb ausdrücklich unter „Wie gerechnet“.

## Belege

### Regeln und eigene Festlegungen

Die Regeln 1–7 stammen aus dem Auftrag. Wo der Auftrag eine Größe offen ließ, stehen im Kopf des Moduls eigene Festlegungen. Sie wurden vor dem ersten Lauf geschrieben:

| Punkt | Festlegung |
|---|---|
| guter Monat | gültig nach dem Verknüpfungsgerüst (mindestens 50 % beobachtet) und kein Schnee-Verdacht (bestehende Regel `aleph/detect/schnee.py`) |
| Jahreswert | Mittel der Lichtdichte über die guten Monate; erst ab 6 guten Monaten |
| „wenige gute Monate“ | 6 bis 8 gute Monate |
| „ganz zu einem Land“ | Anteil des Landes an der Landfläche der Zelle mindestens 99,9 % |
| Abdeckung nach Licht (Regel 5) | Licht mit Jahreswert geteilt durch (dasselbe plus geschätztes Licht der Zellen ohne Jahreswert). Schätzwert = Mittel über alle Monate mit irgendeinem Messwert, auch dünn beobachtete und Schnee-Monate. Er dient nur der Gewichtung. |
| Region | M49-Region (UN) der Einheiten eines Landes, nach Fläche überwiegend (Nachtrag, siehe unten) |
| Rechnung | y = ln(Jahres-Lichtsumme), x = ln(reales BIP); kleinste Quadrate; Bootstrap über Länder, 2000 Wiederholungen, fester Startwert 20260928, Perzentile 2,5 und 97,5 |
| Feld und Sicht | `allangle_mittel_beobachtet` (Standardfeld); Sicht „so wie die Weltbank zählt“ mit unklaren Gebieten; Verteilung „normiert“, s_min 0,05 (Standard des Gerüsts) |

**Ausschlussliste Regel 3:** aus der Kurzfassung von `berichte/2026-09-26_weltbank-gebiete.md` (Georgien, Moldau, Tansania, Marokko, Zypern). Das Programm liest die Liste aus `sondereinheiten.yaml` und bricht ab, wenn sie nicht genau diesen fünf entspricht (Test vorhanden).

### Nachtrag nach dem ersten Lauf (offen dokumentiert)

- **Befund:** Im ersten Lauf waren 12 Länder außerhalb der Region in der Rechnung: ATG, CUW, DMA, GRD, KNA, LCA, PRI, SUR, TTO, VCT, VIR (Amerika) und PLW (Ozeanien).
- **Ursache:** Ihre Kacheln sind geladen, weil sie auch Land der französischen Antillen bzw. einer Region-Einheit enthalten. Deshalb galten sie nach Regel 7 als „vollständig geladen“.
- **Korrektur:** Das Land muss zusätzlich zur Region gehören. Das ist eine Korrektur der Umsetzung am festgelegten Rahmen „Afrika-Europa-Asien“. Keine Schwelle wurde geändert.
- **Vorher / nachher (Hauptrechnung):**

  | Jahr | vorher | nachher |
  |---|---|---|
  | 2018 | n = 137, Steigung 0,96 [0,89; 1,04], R² 0,84 | n = 125, Steigung 0,94 [0,85; 1,03], R² 0,81 |
  | 2019 | n = 135, 0,97 [0,89; 1,05], R² 0,83 | n = 123, 0,95 [0,86; 1,05], R² 0,80 |

- Kanalinseln (CHI) und Kosovo (XKX) haben keinen eigenen M49-Eintrag. Ihre Einheiten tragen aber M49-Einträge in Europa, deshalb bleiben sie drin.

### Ergebnis: alle Rechnungen nebeneinander

Steigung [95-%-Bereich], R², Zahl der Länder:

| Rechnung | 2018 | 2019 |
|---|---|---|
| Hauptrechnung (Regeln 1–7) | 0,94 [0,85; 1,03], R² 0,81, n 125 | 0,95 [0,86; 1,05], R² 0,80, n 123 |
| Regel 2: nur Zellen, die ganz zu einem Land gehören | 0,95 [0,87; 1,05], R² 0,81, n 125 | 0,96 [0,87; 1,06], R² 0,80, n 123 |
| Regel 4: Reinheit ≥ 30 % | 0,93 [0,84; 1,02], R² 0,80, n 131 | 0,95 [0,86; 1,04], R² 0,79, n 130 |
| Regel 4: Reinheit ≥ 70 % | 0,96 [0,88; 1,06], R² 0,82, n 112 | 0,98 [0,89; 1,09], R² 0,82, n 111 |
| Regel 6: ohne Länder mit > ⅓ Licht aus Zellen mit 6–8 guten Monaten | 0,94 [0,85; 1,03], R² 0,81, n 123 | 0,95 [0,86; 1,04], R² 0,80, n 122 |
| Zusatz (nicht im Auftrag): ohne Länder mit unklarem Weltbank-Gebiet | 0,93 [0,84; 1,02], R² 0,80, n 117 | 0,95 [0,85; 1,05], R² 0,80, n 116 |

### Ausgeschlossene Länder in der Region (2018; 2019 in Klammern, wo anders)

| Grund | Länder |
|---|---|
| Weltbank-Gebiet weicht ab (Regel 3) | Georgien, Moldau, Tansania, Marokko, Zypern (Zypern zusätzlich Reinheit 23 %) |
| Abdeckung nach Licht unter 90 % (Regel 5) | Russland 64 % (59 %), Norwegen 80 % (85 %), Island 77 % (89 %) |
| Reinheit unter 50 % (Regel 4) | Andorra, Monaco, San Marino, Singapur, Macau (je 0 %), Westjordanland und Gaza 7 %, Lesotho 19 % (15 %), Israel 33 % (32 %), Brunei 40 % (39 %), Kirgisistan 40 % (43 %), Slowenien 42 %, Luxemburg 48 %, Togo 48 % (47 %); 2019 zusätzlich Armenien 49 % |
| Lichtsumme 0 (ln nicht möglich) | Malediven |
| kein reales BIP der Weltbank | Nordkorea, Eritrea, Südsudan, Liechtenstein, Gibraltar, Vatikan und kleine Gebiete ohne Weltbank-Eintrag (ALA, ATF, IOT, SHN); 2019 zusätzlich Jemen |
| außerhalb der Region oder nicht vollständig geladen | 79 Länder und Gebiete (Amerika, Ozeanien) |

**Russland:** Der Schätzwert für Zellen ohne Jahreswert enthält auch Schnee-Monate. Schnee wirft Licht zurück, also ist der Schätzwert eher zu hoch und die Abdeckung eher zu niedrig angesetzt. So war es vor dem Lauf festgelegt; nichts wurde nachträglich geändert. Kasachstan bleibt drin: 32 % seines Lichts kommen aus Zellen mit wenigen guten Monaten, knapp unter einem Drittel, also nicht gekennzeichnet.

### Kennzeichen (drin, aber markiert)

- **Wenige gute Monate:**
  - Finnland: 2018 100 %, 2019 67 % des Lichts aus Zellen mit 6–8 guten Monaten.
  - Schweden: 2018 45 %.
- **Nördlich von 65° N:** Finnland 9 %, Schweden 8 % bzw. 7 % des Lichts.
- **Gebiet der Weltbank-Zahl unklar:** Armenien (2018), Aserbaidschan, Indien, Pakistan, Sudan, Somalia, Syrien, Ukraine.
- **Gasfackel-Hinweis:** Irak, Nigeria, Algerien. Das ist nur ein Hinweis aus der früheren Plausibilitätsprüfung und nicht an einer Fackel-Datenbank geprüft. Diese Länder sind benannt, nicht herausgerechnet.

### Die 10 größten Abweichungen von der Linie

| 2018 | 2019 |
|---|---|
| Isle of Man: 20-mal weniger Licht als die Linie | Isle of Man: 25-mal weniger |
| Komoren: 17-mal weniger | Komoren: 20-mal weniger |
| Kanalinseln: 17-mal weniger | Kanalinseln: 17-mal weniger |
| Irak: 11-mal mehr | Irak: 11-mal mehr |
| Schweiz: 10-mal weniger | Schweiz: 10-mal weniger |
| Libyen: 6,3-mal mehr | Libyen: 7,8-mal mehr |
| Hongkong: 6,3-mal weniger | Syrien: 6,1-mal mehr |
| Iran: 6,0-mal mehr | Hongkong: 5,9-mal weniger |
| Algerien: 5,6-mal mehr | Algerien: 5,8-mal mehr |
| Dänemark: 5,3-mal weniger | Iran: 5,6-mal mehr |

Das ist nur beobachtet. Über Gründe (Finanzplätze, Förderstätten, Stromversorgung, Messung an Küsten) sagt die Rechnung nichts. Nigeria liegt fast auf der Linie (Faktor 1,1 bzw. 1,0).

### Literaturvergleich

Entfällt. Die Quellen im Theorie-Eintrag `theories/nachtlicht-wirtschaft.yaml` (u. a. Henderson, Storeygard, Weil 2012) sind nur mit `verifiziert_umfang: metadaten` geprüft. Außerdem meinen sie eine andere Größe: BIP auf Licht, Panel mit Länder- und Jahres-Effekten. Diese Auswertung **prüft den Theorie-Eintrag nicht**. Der Eintrag legt auch ein anderes Feld fest (NearNadir); hier wurde das Standardfeld AllAngle des Verknüpfungsgerüsts benutzt.

### Tests

- `tests/test_nachtlicht_bip_querschnitt.py`: **9 bestanden**. Die Tests prüfen:
  - die 6-Monats-Regel;
  - den Schnee-Ausschluss;
  - die Verteilung, die Reinheit und die Abdeckung nach Licht;
  - die Kennzeichen „wenige Monate“ und „nördlich von 65° N“;
  - alle Ausschlussgründe, auch den Regionsausschluss;
  - dass die Regression die Steigung findet und der Bootstrap wiederholbar ist;
  - dass Jahre ab 2023 gesperrt sind;
  - dass die Liste aus Bericht und YAML übereinstimmt.
- Die ganze Suite in ~/ALEPH lief am Ende der Sitzung (Zahl im Sitzungsbericht des worktree).

## Umfang

- **In ~/ALEPH neu:**
  - `aleph/link/nachtlicht_bip_querschnitt.py`
  - `tests/test_nachtlicht_bip_querschnitt.py`
  - dieser Bericht
- **Geändert:** keine bestehende Datei, außer einem Eintrag in `LOG.md`.
- **Nur gelesen:**
  - der Würfel (24 Monate 2018–2019, Zustand 4, über `lies_monate_mit_region`)
  - die Zell-Zuordnung
  - die Weltbank-Tabelle (Abruf 2026-09-23)
  - die M49-Tabelle und `sondereinheiten.yaml`
- **Zeiträume:** nur 2018 und 2019. Jahre ab 2023 verweigert das Programm (Test).
- Die Oberfläche im worktree liest nur `ergebnis.json` (über `aleph/export/globus.py`, Funktion `auswertung_nachtlicht_bip`).

## Empfehlung

1. Vor jeder Veröffentlichung: `statistik-pruefer` über Regeln, Rechnung und Beschriftung.
   - Besonders prüfen: Bootstrap mit Perzentilen bei n ≈ 125 und ein paar sehr kleinen Inseln am Rand (Isle of Man, Kanalinseln, Komoren) mit großem Hebel.
2. In der Präsentation nur sagen: „im Querschnitt dieser 125 Länder etwa proportional“. Keine Zahl zur Elastizität aus der Literatur daneben stellen.
3. Die Regel-5-Schätzung ohne Schnee-Monate als **weitere** Gegenrechnung rechnen. Sie wird ausdrücklich als nachträglich gekennzeichnet, damit Russland nicht nur an einer vorsichtigen Festlegung scheitert.
4. Den Gasfackel-Hinweis an einer geprüften Quelle belegen (z. B. VIIRS Nightfire / Weltbank-Fackeldaten, nach Scout-Steckbrief) oder weglassen.

## Nicht geprüft

- Methodenprüfung durch den `statistik-pruefer` (bewusst ausgelassen, Nutzeranweisung).
- Ob die Weltbank-Jahreswerte einzelner Länder vom Kalenderjahr abweichen (Fiskaljahre).
- Ob Kleinstaaten an Küsten durch die Verteilung „normiert“ verzerrt sind.
- Gasfackeln, Gewächshäuser, Schiffe: nicht an Vergleichsdaten geprüft.
- Die Ergebnisse mit NearNadir statt AllAngle.
- Eine Plausibilitätsprüfung erfolgt am Ende der Sitzung gemeinsam für die Teile 1–4 (Ergebnis im Sitzungsbericht `~/ALEPH-ui/berichte/2026-09-29_praesentation.md`).
