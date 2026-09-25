"""Physikalisches Kriterium: Darf eine VNP46A3-Kachel in einem Monat fehlen, weil es dort keine Nacht gibt?

Anlass (LOG.md 2026-09-25): Für 2022-07 fehlen im NASA-Katalog selbst 36
Kacheln (Reihe v01, 70-80° N). Die Grenze in `vnp46a3.pruefe_fehlende_beim_anbieter`
(höchstens 10 Positionen) hält den Monat deshalb an. Eine größere Zahlenschwelle
ist ausdrücklich nicht gewollt: Sie wäre willkürlich und würde echte Lücken
zudecken. Stattdessen rechnet dieses Modul aus Kachelposition und Monat, ob das
Fehlen physikalisch erklärbar ist.

Noch NICHT in den Download eingebunden (der Lauf 41131 lief während der
Entstehung; Einbindung erst nach dessen Ende, eigener Auftrag).

Kriterium (vorsichtige Richtung, "im Zweifel: Fehlen nicht erlaubt"):
Eine Kachel darf nur fehlen, wenn an KEINER Stelle der Kachel zu KEINEM
Zeitpunkt des Monats (plus `ZEITFENSTER_PUFFER_TAGE` an beiden Rändern) die
Sonne so tief steht, dass die Nachtgrenze der Black-Marble-Verarbeitung
erreicht wird (Sonnenzenitwinkel >= 102°), und das mit mehr als
`SICHERHEITSABSTAND_GRAD` Abstand.

Rechnung:
- Kachelgeometrie: einfaches Längen-Breiten-Gitter (Projektion GEO), nicht das
  sinusoidale MODIS-Raster. Zeile v reicht von 90 - 10·v (Nordrand) bis
  80 - 10·v (Südrand), v = 0..17 (LOG.md 2026-09-25, Raster-Ausrichtung).
- Am tiefsten steht die Sonne an einem Ort in der unteren Kulmination
  (Stundenwinkel 180°, "Mitternacht"): sin(Höhe) = sin φ sin δ − cos φ cos δ
  = −cos(φ + δ). Größter Sonnenzenitwinkel an diesem Tag: 180° − |φ + δ|
  (φ Breite, δ Deklination der Sonne, beide mit Vorzeichen; gilt für beide
  Halbkugeln).
- Über die ganze Kachel (φ zwischen Süd- und Nordrand) und den ganzen Monat
  (δ zwischen kleinster und größter Deklination) ist der größte erreichbare
  Zenitwinkel 180° − min|φ + δ|. Das Minimum liegt am äquatornahen Rand
  (Nordhalbkugel: Südrand) und am "dunkelsten Tag" (Nordsommer: kleinste
  Deklination im Monat).
- Das ist eine obere Schranke für das, was der Satellit sehen kann: Der
  Überflug liegt nicht genau in der unteren Kulmination. Die Schranke ist
  deshalb vorsichtig: Wenn nicht einmal um Mitternacht die Grenze erreicht
  wird, dann zu keiner Tageszeit.

Evidenzstufe: Die Deklination ist eine Modellrechnung (Formel unten, gegen
astropy geprüft, LOG.md 2026-09-25). Die Nachtgrenze 102° ist eine Angabe des
Anbieters (Wortlaut im Originaltext gelesen, Fundstelle unten). Dass NASA die
Kacheln aus genau diesem Grund nicht erzeugt, ist NICHT belegt; das Kriterium
sagt nur: das Fehlen ist physikalisch erklärbar. Es verlangt das Fehlen nicht.
"""

from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

# Nachtgrenze der Black-Marble-Verarbeitung: Sonnenzenitwinkel in Grad.
# Quelle: Wang, Z., Román, M. O., Shrestha, R., Yao, T., Kalb, V.: Black Marble
# User Guide (Collection 2.0), Oktober 2024, S. 13 (PDF-Seite 19), Fußnote 1 zu
# Tabelle 5 (VNP46A1): "Note that the need to use fill-values can arise from
# various scenarios such as bad quality data or if the solar zenith angle < 102
# degrees since that is the nighttime cut-off used in the code."
# Dazu S. 16, Tabelle 9 (VNP46A2, Mandatory_Quality_Flag): Wert 02 =
# "Poor-quality Main Algorithm (high solar zenith angle 102-108 degrees)".
# Gelesen im Originaltext (PDF von ladsweb.modaps.eosdis.nasa.gov und die
# wortgleiche Fassung von viirsland.gsfc.nasa.gov), am 2026-09-25.
# Warum 102 und nicht 108: Ob Beobachtungen mit Flag 02 (102-108°) in das
# Monatskomposit eingehen, sagt der User Guide nicht. 102 ist die kleinere und
# damit vorsichtigere Zahl: Mit ihr darf eine Kachel seltener fehlen.
NACHT_SONNENZENIT_GRENZE_GRAD = 102.0

# Sicherheitsabstand in Grad (eigene Festlegung, NICHT vom Anbieter): Eine
# Kachel darf nur fehlen, wenn der größte erreichbare Zenitwinkel um MEHR als
# diesen Wert unter der Nachtgrenze bleibt. Er wirkt nur in die vorsichtige
# Richtung: Größer heißt, weniger Kacheln dürfen fehlen.
# Warum 1°: Die bekannten Rechenfehler sind klein (Deklination gegen astropy
# höchstens 0,0055°, UT gegen TT, Pixelrand 15" = 0,004°). Nicht bekannt ist,
# wie genau der Anbieter den Zenitwinkel je Pixel rechnet. Entscheidend ist:
# Für 2013-2025 liegen alle Fälle entweder unter 0,5° Abstand (v01 im August,
# v02 im Juli; Urteil kippt von Jahr zu Jahr) oder über 3,5° (alle übrigen).
# Jeder Wert zwischen 0,5° und 3,5° ergibt dieselben erlaubten Fälle; 1° liegt
# darin und schließt die knappen Fälle aus (Test
# `test_ergebnis_haengt_nicht_am_genauen_sicherheitsabstand`, Auflage
# statistik-pruefer 2026-09-25, LOG.md).
SICHERHEITSABSTAND_GRAD = 1.0

# Puffer am Monatsrand in Tagen (eigene Festlegung, NICHT vom Anbieter): Belegt
# ist nur das Zeitfenster der Katalog-Metadaten (1. 00:00 UTC bis 1. des
# Folgemonats 00:00 UTC, vnp46a3._monatsspanne). Nicht belegt ist, welche
# Beobachtungen der Anbieter einem Monat zuordnet (UTC-Tag oder Ortstag; bei
# 180° W endet die Ortsnacht des Monatsletzten erst gegen Mittag UTC des
# Folgetags). Deshalb wird auf beiden Seiten ein Tag dazugenommen. Wirkt nur in
# die vorsichtige Richtung (längeres Fenster, mehr mögliche Nächte).
ZEITFENSTER_PUFFER_TAGE = 1

# Zeitschritt, in dem die Deklination über den Monat abgetastet wird. Die
# Deklination ändert sich um höchstens etwa 0,4° je Tag, in einer Stunde also
# um höchstens etwa 0,017°; Monatsanfang und -ende werden zusätzlich exakt
# berechnet.
_ABTASTUNG = timedelta(hours=1)

_POSITION = re.compile(r"h(\d{2})v(\d{2})")


@dataclass(frozen=True)
class DunkelheitsBefund:
    """Ergebnis für eine Kachelzeile in einem Monat, mit Begründung."""

    v: int
    breite_sued: float
    breite_nord: float
    jahr: int
    monat: int
    fehlen_erlaubt: bool
    groesster_zenitwinkel_grad: float  # größter erreichbarer Sonnenzenitwinkel in Kachel und Monat
    groesste_sonnentiefe_grad: float  # = Zenitwinkel − 90: wie tief die Sonne höchstens unter dem Horizont steht
    breite_am_dunkelsten: float  # wo in der Kachel das erreicht wird
    zeitpunkt_am_dunkelsten: datetime  # UTC, Zeitpunkt der dafür maßgeblichen Deklination
    abstand_zur_grenze_grad: float  # Grenze − größter Zenitwinkel (positiv: Grenze nie erreicht)

    @property
    def breitenbereich(self) -> str:
        return f"{_breite_text(self.breite_sued)} bis {_breite_text(self.breite_nord)}"

    @property
    def begruendung(self) -> str:
        tiefe = self.groesste_sonnentiefe_grad
        lage = "unter" if tiefe >= 0 else "über"
        kern = (
            f"Sonne höchstens {_zahl(abs(tiefe), 1)}° {lage} dem Horizont "
            f"(Zenitwinkel {_zahl(self.groesster_zenitwinkel_grad, 1)}°, bei "
            f"{_breite_text(self.breite_am_dunkelsten)}, {self.zeitpunkt_am_dunkelsten:%Y-%m-%d %H:%M} UTC)"
        )
        grenze = f"Black-Marble-Nachtgrenze (Sonnenzenit ≥ {NACHT_SONNENZENIT_GRENZE_GRAD:.0f}°)"
        if self.fehlen_erlaubt:
            return (
                f"{kern}; die {grenze} wird im ganzen Monat (± {ZEITFENSTER_PUFFER_TAGE} Tag) "
                f"um {_zahl(self.abstand_zur_grenze_grad, 1)}° verfehlt: keine Nacht im Sinne dieser "
                "Grenze, Fehlen erklärbar."
            )
        if self.abstand_zur_grenze_grad > 0:
            return (
                f"{kern}; die {grenze} wird nur um {_zahl(self.abstand_zur_grenze_grad, 2)}° verfehlt, "
                f"nicht um mehr als den Sicherheitsabstand {_zahl(SICHERHEITSABSTAND_GRAD, 1)}°: "
                "im Zweifel Fehlen nicht erlaubt."
            )
        return (
            f"{kern}; die {grenze} wird erreicht: es gibt Nächte, Fehlen nicht erklärbar."
        )


def _zahl(wert: float, stellen: int) -> str:
    return f"{wert:.{stellen}f}".replace(".", ",")


def _breite_text(breite: float) -> str:
    if breite == 0:
        return "0°"
    return f"{abs(breite):g}° {'N' if breite > 0 else 'S'}"


def kachel_breiten(v: int) -> tuple[float, float]:
    """(Südrand, Nordrand) in Grad einer Kachelzeile v im GEO-Gitter von VNP46A3."""
    if not 0 <= v <= 17:
        raise ValueError(f"Kachelzeile v muss zwischen 0 und 17 liegen, nicht {v}")
    return 80.0 - 10.0 * v, 90.0 - 10.0 * v


def zeile_aus_position(position: str) -> int:
    """Kachelzeile v aus einer Position wie 'h21v05'."""
    treffer = _POSITION.fullmatch(position)
    if not treffer:
        raise ValueError(f"Keine Kachelposition der Form hXXvYY: {position!r}")
    return int(treffer.group(2))


def sonnendeklination_grad(zeitpunkte_utc: np.ndarray) -> np.ndarray:
    """Deklination der Sonne in Grad für UTC-Zeitpunkte (numpy datetime64).

    Kurzformel für die Sonnenposition (mittlere Länge L, mittlere Anomalie g,
    ekliptikale Länge λ, Schiefe der Ekliptik ε), so wie sie für Zwecke wie
    diesen verbreitet ist (Astronomical Almanac, "low precision formulas for
    the Sun"; Zitat aus dem Gedächtnis, nicht am Original geprüft). Belastbar
    ist sie hier nur, weil die Tests sie gegen astropy prüfen (LOG.md).
    Zeitskala: UTC statt TT (Unterschied gut eine Minute, für die
    Deklination unter 0,001°).
    """
    tage_seit_j2000 = (
        (zeitpunkte_utc - np.datetime64("2000-01-01T12:00:00")) / np.timedelta64(1, "s") / 86400.0
    )
    n = np.asarray(tage_seit_j2000, dtype=float)
    mittlere_laenge = np.radians((280.460 + 0.9856474 * n) % 360.0)
    mittlere_anomalie = np.radians((357.528 + 0.9856003 * n) % 360.0)
    ekliptik_laenge = (
        mittlere_laenge
        + np.radians(1.915) * np.sin(mittlere_anomalie)
        + np.radians(0.020) * np.sin(2 * mittlere_anomalie)
    )
    schiefe = np.radians(23.439 - 0.0000004 * n)
    return np.degrees(np.arcsin(np.sin(schiefe) * np.sin(ekliptik_laenge)))


def _monats_zeitpunkte(jahr: int, monat: int) -> np.ndarray:
    """Alle vollen Stunden des Monatsfensters, verlängert um `ZEITFENSTER_PUFFER_TAGE` auf beiden Seiten.

    Grundlage ist das Zeitfenster eines VNP46A3-Monatsgranulats in den
    Katalog-Metadaten (1. 00:00 UTC bis 1. des Folgemonats 00:00 UTC,
    vnp46a3._monatsspanne); beide Enden sind enthalten.
    """
    monatsanfang = np.datetime64(f"{jahr:04d}-{monat:02d}-01T00:00:00")
    tage = monthrange(jahr, monat)[1]
    puffer = np.timedelta64(ZEITFENSTER_PUFFER_TAGE, "D")
    anfang = monatsanfang - puffer
    ende = monatsanfang + np.timedelta64(tage, "D") + puffer
    schritt = np.timedelta64(int(_ABTASTUNG.total_seconds()), "s")
    return np.arange(anfang, ende + schritt, schritt)


def zeilen_befund(v: int, jahr: int, monat: int) -> DunkelheitsBefund:
    """Rechnet für Kachelzeile v und Monat, ob das Fehlen durch fehlende Nächte erklärbar ist."""
    if not 1 <= monat <= 12:
        raise ValueError(f"Monat muss zwischen 1 und 12 liegen, nicht {monat}")
    sued, nord = kachel_breiten(v)
    zeitpunkte = _monats_zeitpunkte(jahr, monat)
    deklination = sonnendeklination_grad(zeitpunkte)
    i_min, i_max = int(np.argmin(deklination)), int(np.argmax(deklination))
    d_min, d_max = float(deklination[i_min]), float(deklination[i_max])

    # |φ + δ| über das Rechteck φ in [sued, nord], δ in [d_min, d_max]:
    # φ + δ läuft über das Intervall [sued + d_min, nord + d_max].
    unten, oben = sued + d_min, nord + d_max
    if unten <= 0.0 <= oben:
        # Irgendwo in der Kachel steht die Sonne irgendwann im Nadir: tiefste Nacht.
        # Stelle und Zeitpunkt (nur zur Begründung): der erste Zeitpunkt, an dem
        # die Gegenbreite −δ in der Kachel liegt; sonst der nächstgelegene.
        gegenbreite = np.clip(-deklination, sued, nord)
        i_zeit = int(np.argmin(np.abs(gegenbreite + deklination)))
        kleinster_betrag, breite = 0.0, float(gegenbreite[i_zeit])
    elif unten > 0.0:
        # Nordhalbkugel-Fall: am Südrand, bei kleinster Deklination.
        kleinster_betrag, breite, i_zeit = unten, sued, i_min
    else:
        # Südhalbkugel-Fall: am Nordrand, bei größter Deklination.
        kleinster_betrag, breite, i_zeit = -oben, nord, i_max

    zenit = 180.0 - kleinster_betrag
    abstand = NACHT_SONNENZENIT_GRENZE_GRAD - zenit
    zeitpunkt = zeitpunkte[i_zeit].astype("datetime64[s]").astype(datetime).replace(tzinfo=timezone.utc)
    return DunkelheitsBefund(
        v=v,
        breite_sued=sued,
        breite_nord=nord,
        jahr=jahr,
        monat=monat,
        fehlen_erlaubt=abstand > SICHERHEITSABSTAND_GRAD,
        groesster_zenitwinkel_grad=zenit,
        groesste_sonnentiefe_grad=zenit - 90.0,
        breite_am_dunkelsten=breite,
        zeitpunkt_am_dunkelsten=zeitpunkt,
        abstand_zur_grenze_grad=abstand,
    )


def fehlen_erklaerbar(position: str, jahr: int, monat: int) -> DunkelheitsBefund:
    """Befund für eine Kachelposition wie 'h12v01'. Nur die Zeile v zählt (Breite), nicht h."""
    return zeilen_befund(zeile_aus_position(position), jahr, monat)


def erlaubte_zeilen(jahr: int, monat: int) -> list[int]:
    """Alle Kachelzeilen v (0..17), die in diesem Monat nach dem Kriterium fehlen dürfen."""
    return [v for v in range(18) if zeilen_befund(v, jahr, monat).fehlen_erlaubt]
