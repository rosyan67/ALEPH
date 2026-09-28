"""Schnee-Verdacht je Zelle und Monat (Ersatz, weil der Würfel kein Schnee-Kennzeichen hat).

Befund 2026-09-26 (Code gelesen, Würfel nur gelesen):
- Der Würfel speichert nur die SCHNEEFREIEN Komposite `AllAngle_Composite_Snow_Free` und
  `NearNadir_Composite_Snow_Free` (aleph/layers/vnp46a3.py, FELD_TRIPEL). Beobachtungen, die NASA als
  Schnee/Eis erkannt hat, stecken dort nicht drin. Ein Schnee-Kennzeichen oder die Zahl der
  Schnee-Beobachtungen (`*_Snow_Covered_Num`) ist NICHT im Würfel.
- Moskau (Zelle 55,75° N / 37,62° O), Feld allangle, technische Prüfung an 2018 (kein Endtest):
  2018-01 Mittel über beobachtete Pixel 68,0 bei 97,9 % beobachteten Pixeln; 2018-02 191,6 bei 49,1 %;
  2018-03 148,1 bei 56,4 %. Das Mittel über ALLE gültigen Pixel (mit aufgefüllten) ist im Februar 149,8.
  Berlin und Kairo (100 % beobachtet) schwanken nur um 11-14 bzw. 41.
- Folgerung (Vermutung, nicht bewiesen; BERICHTIGT nach der Plausibilitätsprüfung 2026-09-26): Ein reiner
  AUSWAHL-Effekt (nur die helle Innenstadt bleibt beobachtet) reicht NICHT. Die beobachteten Pixel allein
  tragen im Februar 191,6 × 0,49 ≈ 94 je Zellpixel bei, mehr als die ganze Zelle im Januar (≈ 67) oder April
  (≈ 69); sie sind also selbst um mindestens etwa 35–40 % heller geworden. Naheliegend ist NICHT ERKANNTER
  Schnee, der das Licht zurückwirft (User Guide Abschnitt 2.3; laut Presseberichten Rekordschneefall in Moskau
  am 3./4.2.2018 – nicht am Original geprüft), zusammen mit der Auswahl weniger beobachteter Pixel
  (Quality 2 „gap filled“ laut Anbieter u. a. wegen Schnee).
- Bekannte Lücke der Regel unten: Ein verschneiter Monat, der trotzdem fast ganz als „beobachtet“ zählt, wird
  nicht erfasst (Prüfer-Beispiel: Helsinki 2019-01, Wert 52 bei 98 % beobachtet, sonst 15–22). Die Regel
  erfasst eher die Auswahl als Schnee selbst. Ein echtes Kennzeichen braucht die Zahl der Schnee-Beobachtungen
  (`*_Snow_Covered_Num`) – Empfehlung für den Kern-Umbau nach dem Download.

Regel (eigene Festlegung, einstellbar, an 2018-01..03 nur technisch angesehen, nicht kalibriert):
Eine Zelle hat in einem Monat SCHNEE-VERDACHT, wenn alle drei Bedingungen gelten:
1. außerhalb der Tropen: |Breite| >= 23,5° (Schnee in Tieflagen der Tropen ist selten; Hochgebirge in den
   Tropen, z. B. Anden, werden damit NICHT erfasst – bekannte Lücke),
2. Winterhalbjahr der Halbkugel: Nord November bis April, Süd Mai bis Oktober,
3. weniger als 90 % beobachtete Pixel (der Rest ist aufgefüllt oder ungültig; genau dann kann die
   Auswahl der beobachteten Pixel das Zellmittel verschieben).
Das ist ein Verdacht, kein Nachweis: Wolken erzeugen dasselbe Muster. Deshalb heißt das Feld „Verdacht“.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SchneeRegel:
    min_breite_grad: float = 23.5
    winter_nord: tuple[int, ...] = (11, 12, 1, 2, 3, 4)
    winter_sued: tuple[int, ...] = (5, 6, 7, 8, 9, 10)
    beobachtet_unter: float = 0.9


def schnee_verdacht(breite: np.ndarray, monat: int, beobachtet_anteil: np.ndarray, regel: SchneeRegel | None = None) -> np.ndarray:
    """Bool-Karte (Breite × Länge): Schnee-Verdacht nach der Regel im Modulkopf.

    `breite`: Zellmitten (Länge = Zeilen von `beobachtet_anteil`), `monat`: Kalendermonat 1-12.
    Zellen ohne gültigen Anteil (NaN, nicht geladen) bekommen False: Sie sind ohnehin nicht bewertbar.
    """
    r = regel or SchneeRegel()
    lat = np.asarray(breite, dtype="float64")[:, None]
    anteil = np.asarray(beobachtet_anteil, dtype="float64")
    winter = np.where(lat >= 0, monat in r.winter_nord, monat in r.winter_sued)
    return (np.abs(lat) >= r.min_breite_grad) & winter & np.isfinite(anteil) & (anteil < r.beobachtet_unter)
