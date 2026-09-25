# Dunkle Nächte: Darf eine VNP46A3-Kachel fehlen? (Fall 2022-07)

Stand: 2026-09-25 · Code: `aleph/layers/vnp46a3_dunkle_naechte.py` (noch nicht in den Download eingebunden) · Tests: `tests/test_vnp46a3_dunkle_naechte.py`

## Kurzfassung

- Für 2022-07 meldet der NASA-Katalog 504 statt 540 Kacheln. Es fehlen genau die 36 Kacheln der Reihe v01 (70–80° N).
- Neues Kriterium: Eine Kachel darf nur fehlen, wenn dort im ganzen Monat (plus 1 Tag an jedem Rand) nirgends eine Nacht im Sinne von Black Marble vorkommt. Nacht heißt: Sonnenzenitwinkel ≥ 102°. Außerdem muss diese Grenze um mehr als 1° verfehlt werden.
- Die 102° stehen im User Guide Collection 2.0 (Okt. 2024), S. 13, Fußnote 1 zu Tabelle 5. Ich habe die Stelle im Originaltext gelesen.
- Ergebnis 2022-07: **alle 36 fehlenden Kacheln sind erklärbar.** Die Sonne steht dort höchstens 2,2° unter dem Horizont; die Grenze wird um 9,8° verfehlt.
- Gegenprobe: Juli erlaubt v00–v01 (hoher Norden), Dezember v15–v17 (hoher Süden), März keine Reihe. Das entspricht der Erwartung.
- An echten Kacheln geprüft (Juli 2023): 70–80° N und 60–70° N enthalten keinen einzigen gültigen Pixel. Bei 50–60° N reichen die Beobachtungen bis 58,9° N. Das passt zu 102°, nicht zu 108°.
- statistik-pruefer: „bestanden mit Auflagen“. Für die Einbindung übernommen sind: 1 Tag Puffer, 1° Sicherheitsabstand und eine feste Tabelle aller erlaubten Fälle.
- Tests: 68 neue, gesamt 495 von 495 grün. Der Download lief die ganze Zeit ungestört weiter.
- Offen: Einbindung in den Download (nach Laufende) und der Name des Zustands im Manifest.

## Urteil

2022-07 ist nach dem Kriterium **freizugeben**: Das Fehlen aller 36 Kacheln ist physikalisch erklärbar. Es gibt keine Ausnahme. Die Einbindung in den Download steht noch aus, deshalb bleibt der Monat vorerst zurückgestellt.

Evidenzstufen:
- Nachtgrenze 102°: Angabe des Anbieters.
- Sonnenstand: astronomische Rechnung, gegen astropy geprüft. Das ist keine Projektion im Sinne einer Vorhersage.
- Leere Sommerkacheln: beobachtet (zwei leere Kacheln, h19v01 und h19v02, dazu die Randkachel h19v03; alle aus einem Monat).
- Dass NASA die Kacheln *wegen* fehlender Nächte nicht erzeugt: **nicht belegt**. Das Kriterium sagt nur „erklärbar“. Es verlangt das Fehlen nicht.

## Belege

**Schwellenwert** (`NACHT_SONNENZENIT_GRENZE_GRAD = 102.0`)

Quelle: Wang, Román, Shrestha, Yao, Kalb: *Black Marble User Guide (Collection 2.0)*, Oktober 2024.

- S. 13 (PDF-Seite 19), Fußnote 1 zu Tabelle 5: „…if the solar zenith angle < 102 degrees since that is the nighttime cut-off used in the code.“
- S. 16, Tabelle 9: Flag 02 = „high solar zenith angle 102-108 degrees“ (Beobachtung schlechter Qualität).

Beide Fassungen (ladsweb und viirsland) sind wortgleich. Ich habe den Text selbst aus dem PDF extrahiert; es ist keine Zusammenfassung.

- Warum 102 und nicht 108: Ob Flag-02-Beobachtungen ins Monatskomposit eingehen, steht nicht im Guide. 102 ist die vorsichtigere Zahl.
- Die ATBD v1.1 (Juli 2020) nennt keine Sonnen-Nachtgrenze.

**Rechnung**

- Am tiefsten steht die Sonne um Mitternacht. Dann gilt: Zenitwinkel = 180° − |Breite + Deklination|.
- Gerechnet wird am äquatornahen Kachelrand und am dunkelsten Zeitpunkt des Fensters. Das Fenster reicht vom 1. 00:00 UTC bis zum 1. des Folgemonats und hat zusätzlich ±1 Tag Puffer.
- Das ist eine obere Schranke für jede Überflugzeit und gilt für beide Halbkugeln.
- Die Deklination weicht über 2013–2025 höchstens 0,0055° von astropy 8.0.1 ab. Direkter Zenitwinkel bei 60° N im Juli 2022: astropy 101,922°, eigene Rechnung 101,932°.

**2022-07, die 36 fehlenden Kacheln**

Alle 36 Kacheln liegen in derselben Reihe und bekommen daher dasselbe Ergebnis.

| Kachel | Breitenbereich | erlaubt | Begründung |
|---|---|---|---|
| h00v01 … h35v01 (alle 36, einzeln geprüft) | 70° N bis 80° N | ja | Sonne höchstens 2,2° unter dem Horizont (Zenitwinkel 92,2°, bei 70° N, 2022-08-02 00:00 UTC). Die Grenze 102° wird im ganzen Monat (±1 Tag) um 9,8° verfehlt: keine Nacht im Sinne dieser Grenze, Fehlen erklärbar. |

Die Katalogabfrage (am 2026-09-25, über `vnp46a3._katalog_abfrage`) ergab:
- 504 Treffer gemeldet und 504 geholt;
- keine unbekannte Position;
- fehlend: h00v01 bis h35v01.

**Gegenprobe (2022): Reihen, in denen Fehlen erlaubt ist**

| Monat | erlaubt | Erwartung |
|---|---|---|
| Juli | v00, v01 | nur hoher Norden ✓ |
| Dezember | v15, v16, v17 | nur hoher Süden ✓ |
| März | keine | praktisch nichts ✓ |

**Erlaubt, aber vom Katalog trotzdem geliefert**

- 2022-07: Das Kriterium erlaubt v00 und v01. v00 steht gar nicht in der Referenzliste, v01 fehlt tatsächlich. In diesem Monat gibt es also keinen solchen Fall.
- In anderen Jahren liefert NASA v01 im Juli aber: 2019-07 35 von 36, 2021-07 und 2023-07 je 36 von 36.
- Geprüft an 2023-07: h19v01 und h19v02 sind je ~0,74 MB groß, Größe und MD5 stimmen mit dem Katalog. Alle sechs Komposite haben 0 gültige Pixel, `_Num` ist überall 0, Quality ist 255.
- Diese Kacheln werden also geliefert, sind aber leer. Das ist kein Widerspruch: Das Kriterium erlaubt das Fehlen, es verlangt es nicht.

**Die 102°-Grenze in den Daten sichtbar**

h19v03, Juli 2023, 50–60° N:
- Beobachtungen (AllAngle, `_Num > 0`) gibt es bis 58,887° N.
- Vorhersage bei einer 102°-Grenze: höchstens bis 59,87° N (Überflug um Mitternacht). Bei einem Überflug 1 bis 1,5 Stunden nach Mitternacht wären es 58,9 bis 57,6° N.
- Bei einer 108°-Grenze wäre bei 53,9° N Schluss.
- Belastbar ist nur die Unterscheidung 102° gegen 108°. Dass 58,887° N fast genau zu „eine Stunde nach Mitternacht“ passt, habe ich erst im Nachhinein gewählt; das ist keine Bestätigung. Es ist eine einzige Kachel.

**Frühere Katalog-Lücken**

- 2018-05: 2 Kacheln, 2018-06: 6, 2019-06: 4, 2019-07: 1.
- Alle 13 sind nach dem Kriterium erklärbar, mit mindestens 3,8° Abstand.
- Die alte Regel hat also nichts Unerklärbares durchgelassen.

**statistik-pruefer:** „bestanden mit Auflagen“. Umgesetzt wurden:
1. Das Zeitfenster hat ±1 Tag Puffer. Es ist nicht belegt, ob der Anbieter Beobachtungen nach UTC-Tag oder Ortstag zuordnet.
2. Der Sicherheitsabstand ist von 0,1° auf 1° erhöht.
3. Eine feste Tabelle aller erlaubten Fälle 2013–2025 ist als Test hinterlegt.
4. Die Formulierung lautet jetzt „keine Nacht im Sinne der Black-Marble-Grenze“.
5. Die früheren Lücken sind abgeglichen.

Ohne diese Änderungen gab es knappe Fälle, deren Urteil von Jahr zu Jahr kippte:
- v02 im Juli: Abstand 0,008–0,146°;
- v01 im August: 0,17–0,47°.

Jetzt haben alle erlaubten Fälle mehr als 3,5° Abstand. Jeder Sicherheitsabstand zwischen 0,5° und 3,5° liefert genau dieselben Fälle (Test).

## Umfang

- **Neu:** `aleph/layers/vnp46a3_dunkle_naechte.py` und `tests/test_vnp46a3_dunkle_naechte.py` (68 Tests).
- **Ergänzt:** ein datierter Belegabsatz in `docs/sources/vnp46a3.md`, dazu `LOG.md`.
- **Nicht angefasst:** `vnp46a3.py`, `vnp46a3_lauf.py`, die Kachelliste und `scripts/`. Laut git sind sie zwar geändert, aber schon vor dieser Sitzung (Stand beim Sitzungsbeginn, Änderungszeit 14:59/15:03 Uhr). Download-Prozess 41131 lief durchgehend.
- **Gesamte Testsuite:** 495 von 495 grün (vorher 427, dazu die 68 neuen).
- **Probekacheln** (3 Stück, Juli 2023) liegen nur im Zwischenordner der Sitzung, nicht in den Projektdaten.
- **Erlaubte Fälle 2013–2025** (in jedem Jahr gleich), als Paare (Monat, Reihe):
  - hoher Norden: v00 April–August, v01 Mai–Juli, v02 Juni;
  - hoher Süden: v15 Dezember, v16 November–Januar, v17 Oktober–Februar.
- **Nachtrag 2026-09-26 (Zeitraum-Regel):** Für die Gegenprobe wurden Kacheln aus Juli 2023 und Lieferzahlen 2021/2023 verwendet. Das war eine technische Prüfung (leere Kacheln), keine inhaltliche Auswertung; die Regel war damals nicht im Repo.
- **Die Übergabe** `claude/uebergabe-2026-09-25.md` (Abschnitt 7) existiert nicht, weder dort noch sonst im Projekt. Gearbeitet habe ich mit LOG.md, ARCHITECTURE.md und dem Code.

## Empfehlung

Für die Einbindung nach Ende des Laufs (eigener Auftrag):

1. **Die neue Regel ersetzt die alte Zahlengrenze** (`NICHT_BEIM_ANBIETER_MAX/ZEILEN/MONATE`). Beide werden nicht mit „oder“ verknüpft. Die Prüfung „gemeldete Treffer = geholt = verschiedene Positionen“ bleibt davor Pflicht.
2. **Das Kriterium gilt je Kachel.** Es wird nicht verlangt, dass eine ganze Reihe fehlt (2019-07 zeigt 35 von 36).
3. **Eigener Zustand oder Grund im Manifest**, z. B. „im Katalog nicht gemeldet; Nacht ausgeschlossen (Sonnenzenit max. X°, Grenze 102°)“. Nicht einfach „beim Anbieter nicht vorhanden“: Ob die Kachel beim Anbieter fehlt oder nur in der Katalogantwort, zeigt das Kriterium nicht.
4. **Im Würfel und in der Erkennung:** Solche Kacheln werden wie leere gelieferte Kacheln behandelt, also als fehlender Wert mit „Datenlage unzureichend“, **nie als 0 Licht**. Dazu gehört ein Test. Wie weit Sommerzellen in hohen Breiten beobachtet werden, schwankt aus astronomischen Gründen; die Mindestzahl an Beobachtungen (`_Num`) muss solche Zellen ausschließen.
5. **Danach 2022-07 neu versuchen.**

## Nicht geprüft

- Welche Beobachtungszeiten der Anbieter einem Monat tatsächlich zuordnet (UTC- oder Ortstag). Der Tag Puffer fängt das nur ab; belegt ist es nicht.
- Ob Flag-02-Beobachtungen (102–108°) ins Monatskomposit eingehen. Für das Kriterium ist das egal, weil es die kleinere Zahl nimmt.
- Wie genau der Anbieter den Zenitwinkel je Pixel berechnet.
- Die 102°-Grenze in den Daten: nur an drei Kacheln eines Monats (Juli 2023, 10–20° O) gesehen, nicht in anderen Jahren, Längen oder auf der Südhalbkugel.
- Warum NASA v01 im Juli 2022 nicht erzeugt, in anderen Jahren aber leere Kacheln liefert.
- Die Kurzformel für den Sonnenstand ist aus dem Gedächtnis zitiert (Astronomical Almanac, nicht am Original geprüft). Tragend ist allein der Abgleich mit astropy.
- Der statistik-pruefer konnte selbst keinen Code ausführen. Seine Überschlagsrechnungen habe ich mit dem Modul nachgerechnet; die Tabelle oben stammt aus dem Modul.
