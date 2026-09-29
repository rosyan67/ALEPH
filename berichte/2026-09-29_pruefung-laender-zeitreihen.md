# Methodenprüfung: Zeitreihen je Land (statistik-pruefer)

Stand: 2026-09-29 · geprüft: `aleph/link/laender_zeitreihen.py` (0.1.0), `tests/test_laender_zeitreihen.py`, im worktree `web/globus_zeitreihen.js` und `aleph/export/globus.py` (`laender_zeitreihen`) · Prüfer: `statistik-pruefer` (liest nur, führt nichts aus)

## Kurzfassung

- **Urteil: bestanden mit Auflagen.** Die Rechnung setzt die Regeln F1–F9 richtig um. Die Sperre 2023–2025 ist dicht.
- Kein Rechenfehler. Die Auflagen betreffen die Texte: Unsicherheit und Vergleichbarkeit der Jahreswerte.
- Mindestlänge der Saisonbereinigung (3 Werte je Kalendermonat, also 3 volle Jahre) ist vertretbar und bleibt.
- Die 7 Auflagen sind umgesetzt (Version 0.2.0, nur Texte, keine Zahl geändert). Die freiwillige Gegenrechnung 1c ist nicht gemacht.
- Die eigene Nachrechnung (Ägypten, Deutschland, Indien, Nigeria) stimmt bis auf Rundung.

## Urteil

bestanden mit Auflagen. Evidenzstufe „beobachtet“ passt, weil kein Zusammenhang gerechnet wird. Gleitender Durchschnitt (nachlaufend, nur mit 12 voll gültigen Monaten) und Kennzeichnung unsicherer Punkte sind in Ordnung. Ein Index-Unterschied von wenigen Punkten ist nicht deutbar; das muss dastehen.

## Belege

Nachrechnung (eigener Rechenweg direkt aus Würfel und Zuordnung, ohne die Funktionen des Gerüsts):

| Prüfung | Ergebnis |
|---|---|
| Monatssumme 2019-06, 2019-01 (EGY, DEU, IND, NGA) | gleich bis auf Rundung auf 3 Ziffern (z. B. DEU 2019-06: eigen 489 190, Datei 489 000) |
| Jahreswert 2019 eigen / Zeitreihe / Auswertung 2018-19 | EGY 787 204 / 787 000 / 787 204; DEU 417 918 / 418 000 / 417 918; IND 2 400 084 / 2 400 000 / 2 400 084; NGA 309 417 / 309 000 / 309 417 |
| alle 170 gültigen Jahreswerte 2018 und 2019 gegen die Auswertung | größte Abweichung 0,4 % (Rundung) |
| 12-Monats-Durchschnitt, Index, Licht pro Kopf | nachgerechnet, stimmt |
| Fläche monatlich gegen jährlich | gleich bis auf Rundung (DEU 358 000 / 357 265) |
| Einheit reales BIP | Weltbank-Tabelle: „konstante US-Dollar, Basisjahr 2015“ |

Auflagen und Umsetzung:

| Nr. | Auflage | Umgesetzt |
|---|---|---|
| 1 | Jahreswerte zwischen Jahren nur bedingt vergleichbar (wechselnde gute Monate): Anteil „Licht aus Zellen mit 6–8 guten Monaten“ zeigen, Satz im Index-Modus; freiwillig Gegenrechnung | Spalte in beiden Tabellen, Kennzeichen ab einem Drittel, Satz im Index-Modus; Gegenrechnung nicht gemacht |
| 2 | Aussage zur Unsicherheit fehlt | Satz im Rahmen: Schwankung ohne wirtschaftliche Änderung, Größe nicht bestimmt, wenige Indexpunkte nicht deutbar |
| 3 | „Landessumme“ sagt zu viel | jetzt „Summe über die gemessene Fläche (mind. 90 %)“; Hinweis zur wechselnden Abdeckung und zur Lücke der Schnee-Regel |
| 4 | Saisonbereinigung sieht aus wie Anomalie | Satz „Median aus denselben Jahren, Wert eingeschlossen, keine Anomalie-Bewertung“; Satz zu „genau 0“ nur bei ungerader Zahl |
| 5 | „vorläufig“ fehlt im Index-Modus | ergänzt (Punkt und Tabelle) |
| 6 | Stufe der Pro-Kopf-Monatswerte zum Jahreswechsel | Satz in der Regel „pro Kopf“ |
| 7 | Titel „nachlaufend“ | ergänzt |

## Umfang

Geprüft: Rechnung, Tests, Anzeige-Texte, Sperre im Export. Nur Jahre 2018–2021 (Weltbank) und Monate 2018-01 bis 2021-01; nichts aus 2023–2025 gelesen.

## Empfehlung

1. Nach der Präsentation die Gegenrechnung 1c (nur Kalendermonate, die in allen Jahren gut sind), ausdrücklich als nachträglich gekennzeichnet.
2. Die natürliche Schwankung der Jahreswerte im Kalibrierungszeitraum messen, bevor Index-Unterschiede gedeutet werden.

## Nicht geprüft

- Der Prüfer hat Code und Tests nicht ausgeführt und die Seite nicht angesehen.
- Ob die Weltbank-Sicht bei Georgien und Moldau die abgetrennten Gebiete wirklich ausschließt (Licht und Bevölkerung dasselbe Gebiet).
- Wie groß der Effekt der wechselnden guten Monate auf den Index ist (Mechanismus benannt, nicht gemessen).
