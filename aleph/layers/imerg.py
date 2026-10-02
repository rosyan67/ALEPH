"""Layer Niederschlag: NASA GPM IMERG, monatlich (GPM_3IMERGM, Final Run V07B).

Steckbrief: docs/sources/imerg.md (maßgeblich, geprüfter Stand 2026-10-02).
Vorbild für Aufbau und Lademuster: aleph/layers/vnp46a3.py (gelesen, NICHT
verändert - der Nachtlicht-Hintergrund-Download läuft parallel und teilt sich
die Bandbreite, siehe GLEICHZEITIGE_DOWNLOADS unten). Grund für den Raster-
und Zeitachsen-Import aus vnp46a3 statt eigener Neudefinition: der Vertrag
verlangt "exakt das Gitter des Nachtlicht-Würfels"; nur ein einziger Ursprung
der Zahlen (720x1440, Zeile 0 = 89,875°N; 2013-01..2025-12) verhindert, dass
beide Layer unbemerkt auseinanderlaufen.

Unterschied zu VNP46A3: IMERG liefert EINE globale HDF5-Datei je Monat (kein
Kachelsystem mit hunderten Positionen). Katalogabfrage, Download und Prüfung
sind deshalb viel einfacher als bei VNP46A3; nur ein Zeitlimit und eine
Wiederholung mit wachsenden Pausen sind trotzdem Pflicht (CLAUDE.md,
Abschnitt "Netzwerk").

---------------------------------------------------------------------------
Warum exakte flächengewichtete (konservative) Regridding, 0,1° -> 0,25°
---------------------------------------------------------------------------
0,25° / 0,1° = 2,5: keine ganze Zahl. Jede 0,25°-Zielzelle überlappt deshalb
IMMER mit genau 3 Quellpixeln je Richtung (siehe Rechnung unten), nie mit 2
oder 4 - eine einfache "jeder 2.-3. Pixel"-Mittelung wäre falsch. Exaktes
Ergebnis: Da beide Gitter REGELMÄSSIGE Breiten-/Längengitter sind, ist die
Fläche eines Pixel-Zellzellen-Überlapps trennbar in einen Breitenanteil und
einen Längenanteil (Fläche = Δλ_überlapp · (sin φ_oben - sin φ_unten)); das
Gesamtgewicht eines Quellpixels (i,j) in einer Zielzelle (m,n) ist deshalb
W_lat(m,i) · W_lon(n,j), ein Produkt aus einer (720x1800)- und einer
(1440x3600)-Matrix. Damit lässt sich die flächengewichtete Mittelung über
Matrixmultiplikation rechnen: Zähler = W_lat @ (Wert·gültig) @ W_lonᵗ,
Nenner = W_lat @ gültig @ W_lonᵗ, Zellwert = Zähler/Nenner (Nenner=0 -> NaN).

Kanten werden in ganzzahligen "Ticks" von 0,05° gerechnet (= größter
gemeinsamer Teiler von 0,1° und 0,25°), NICHT in Grad als Fließkommazahl:
0,1° = 2 Ticks, 0,25° = 5 Ticks. So ist die Überlappungslänge jedes
Pixel-Zellen-Paars ein EXAKTES ganzzahliges Ergebnis ohne Rundungsfehler; nur
die Umrechnung in sin(φ) am Ende (für die Fläche in Breitenrichtung) nutzt
zwangsläufig Fließkommazahlen, wie jede Flächenrechnung auf einer Kugel.

Nachrechnung "3 Quellpixel je Richtung, 9 insgesamt" (Faktum aus dem
Auftrag, hier nachvollzogen): Kleinster gemeinsamer Zeitraum von 0,1°-Schritt
(2 Ticks) und 0,25°-Schritt (5 Ticks) ist 0,5° (10 Ticks) = 5 Quellpixel auf
2 Zielzellen. Zielzelle A (Ticks [0,5)) überlappt Quellpixel [0,2) (voll, 2
Ticks), [2,4) (voll, 2 Ticks), [4,6) (halb, 1 Tick) = 3 Pixel, 5 Ticks.
Zielzelle B (Ticks [5,10)) überlappt [4,6) (halb, 1 Tick), [6,8) (voll),
[8,10) (voll) = 3 Pixel, 5 Ticks. Das Muster wiederholt sich alle 0,5°; JEDE
Zielzelle trifft also in jeder Richtung genau 3 Quellpixel (voll, voll, halb
oder halb, voll, voll) - macht 3x3 = 9 Pixel bei voller Gültigkeit, wie im
Auftrag vorgegeben ("precipitation_gueltige_pixel" wird deshalb nie größer
als 9). Da die Erde in beiden Gittern ohne Lücke und ohne Überlapp an den
Rändern (-90°/90°, -180°/180°) abgedeckt ist, ist jede Zielzelle bei
vollständig gültigen Quelldaten voll abgedeckt (`precipitation_gueltig_anteil
== 1`).

Masken-Reihenfolge (Pflicht, CLAUDE.md): Jeder Fehlwert (-9999,9 laut Doku
ODER das `_FillValue`-Attribut der Datei, falls vorhanden) und jeder negative
oder nicht endliche Wert wird VOR jeder Mittelung zu NaN/ungültig; 0,0 bleibt
0,0 und fließt normal ein. Fehlende Pixel werden beim Nenner herausgerechnet,
nie als 0 mitgezählt (sonst würde eine Lücke den Zellwert künstlich senken).

Achsen werden NICHT aus der Dokumentation angenommen, sondern aus den
`lat`/`lon`-Arrays jeder Datei selbst bestimmt und gegen die erwarteten
Mittelpunkte (-89,95..89,95 bzw. -179,95..179,95, Schritt 0,1°) geprüft; passt
das nicht, bricht die Verarbeitung mit einer klaren Meldung ab
(`AchsenFehler`), statt eine falsche Ausrichtung zu raten.
"""

import argparse
import concurrent.futures
import hashlib
import os
import re
import shutil
import time
from calendar import monthrange
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import h5py
import numpy as np
import scipy.sparse as sp
import xarray as xr

import earthaccess
from earthaccess.exceptions import DownloadFailure, EulaNotAccepted, ServiceOutage

from aleph.core import io
from aleph.core.auth import abbruch_meldung, earthdata_login, login_mit_wiederholung

# Raster und Zeitachse: exakt wie der Nachtlicht-Würfel (ARCHITECTURE.md
# Abschnitt 4/5). Reiner Lese-Import, aleph/layers/vnp46a3.py wird NICHT
# verändert (der Nachtlicht-Download läuft parallel, Prozess vnp46a3_lauf.py).
from aleph.layers.vnp46a3 import (
    GITTER_BREITE,  # 720 Zeilen, Zeile 0 = 89,875°N
    GITTER_LAENGE,  # 1440 Spalten, Spalte 0 = -179,875°
    ZEITACHSE_ENDE,  # (2025, 12)
    ZEITACHSE_START,  # (2013, 1)
    _gitter_koordinaten,
    zeitachse,
)

META = {
    "name": "GPM IMERG V07 (GPM_3IMERGM, monatlich, Final Run)",
    "bereich": "Umwelt / Niederschlag",
    "quelle": (
        "The IMERG data were provided by the NASA/Goddard Space Flight Center's "
        "Mesoscale Atmospheric Processes Laboratory and PPS, which develop and "
        "compute IMERG as a contribution to GPM, and archived at the NASA GES "
        "DISC. DOI 10.5067/GPM/IMERG/3B-MONTH/07 (wörtlich aus dem NASA-Katalog, "
        "docs/sources/imerg.md Abschnitt 6)."
    ),
    "lizenz": (
        "'The data access policy is \"freely available\" with three common-sense "
        "caveats: 1. The data set source should be acknowledged ... 2. New users "
        "are urged to obtain their own current, clean copy from an official "
        "archive ... 3. Errors and difficulties ... should be reported to the "
        "dataset creators.' UseConstraints verweisen zusätzlich auf die EOSDIS "
        "Data Use and Citation Guidance (wörtlich aus dem NASA-Katalog, "
        "docs/sources/imerg.md Abschnitt 6)."
    ),
    "native_aufloesung": "0,1° x 0,1° (1800 x 3600 Punkte), monatlich, global",
    "ziel_aufloesung": (
        "0,25° (exakte flächengewichtete/konservative Aggregation, da 0,25°/0,1° "
        "= 2,5 keine ganze Zahl ist - Begründung im Modulkopf dieser Datei)"
    ),
    "einheit": (
        "mm/Monat (precipitation_mm_monat, random_error_mm_monat); Prozent "
        "(gauge_relative_weighting, probability_liquid); äquivalente "
        "Messstationen je 2,5°-Box (quality_index)"
    ),
    "herkunftseinheit": "mm/hr (mittlere Rate über den Kalendermonat), siehe docs/sources/imerg.md Abschnitt 2",
    "zeitraum": (
        "2013-01 bis 2025-09 (V07 Final Run endet mit September 2025 wegen der "
        "Umstellung auf V08; NASA-Mitteilung 'IMERG V08 Transition Schedule', "
        "https://gpm.nasa.gov/data/news/imerg-v08-transition-schedule, abgerufen "
        "2026-10-02). 2025-10 bis 2025-12 gibt es in V07 nicht und werden NIE als "
        "'keine Daten' geführt, sondern im Würfel ausdrücklich als 'beim Anbieter "
        "nicht vorhanden' (monat_fertig=5)."
    ),
    "bekannte_schwaechen": (
        "Schneefall unterschätzt, Gebirge weniger zuverlässig; verminderte Güte "
        "über gefrorenen Flächen und in hohen Breiten (Infrarot-Schätzungen nur "
        "60°N-S, siehe VERMINDERTE_GUETE_BREITENGRENZE - das ist eine eigene "
        "Annahme, keine Anbieterempfehlung); Regenmesser-Korrektur (Fuchs-"
        "Adjustierung) wirkt nur über Eurasien > 45°N; Kalibrierungswechsel "
        "TRMM->GPM nach Mai 2014 (möglicher Bruch 2013-2025); V07 wird durch V08 "
        "abgelöst und darf nie mit V08 gemischt werden."
    ),
    "anzeige": "Rohwerte mit Quellenangabe zulässig (siehe 'quelle' oben, 'freely available').",
    "details": "docs/sources/imerg.md",
}

# --- NASA-Produkt -----------------------------------------------------------
KURZNAME = "GPM_3IMERGM"
KATALOG_VERSION = "07"
DATEI_VERSION_TEXT = "V07B"

# Monate, für die der Katalog laut NASA-Mitteilung (s. META["zeitraum"]) KEIN
# Granulat liefert. Herkunft: https://gpm.nasa.gov/data/news/imerg-v08-transition-schedule
# und .../update-imerg-v08-transition-schedule-aug-2026, abgerufen 2026-10-02
# (docs/sources/imerg.md Abschnitt 4). Taucht einer dieser Monate im Katalog
# DOCH auf, ist das ein Fehler (ReferenzlisteVeraltet) - V08 darf nicht still
# eingemischt werden; fehlt ein ANDERER Monat, ist das ebenfalls ein Fehler
# (MonatFehltUnerwartet) statt eines stillen Übergehens.
BEIM_ANBIETER_NICHT_VORHANDEN = {(2025, 10), (2025, 11), (2025, 12)}

# --- Quellgitter (0,1°) und Tick-Einheit für die exakte Flächengewichtung --
QUELL_BREITE = 1800
QUELL_LAENGE = 3600
QUELLZELLE_GRAD = 0.1
TICK_GRAD = 0.05  # größter gemeinsamer Teiler von 0,1° (Quelle) und 0,25° (Ziel)
QUELLE_SCHRITT_TICKS = 2  # 0,1° / 0,05°
ZIEL_SCHRITT_TICKS = 5  # 0,25° / 0,05°
A_LON_VOLL_TICKS = ZIEL_SCHRITT_TICKS  # volle Längsüberdeckung je Zielzelle (IMERG ist global lückenlos)

FEHLWERT_DOKU = -9999.9  # "All products in IMERG use the standard missing value '-9999.9'" (Doku S. 74)

H5_GRUPPE = "Grid"
FELD_EINHEITEN = {
    "precipitation": "mm/hr (mittlere Rate über den Kalendermonat)",
    "randomError": "mm/hr (Zufallsfehler; als Zellwert eine Obergrenze - siehe Attribut im Würfel)",
    "gaugeRelativeWeighting": "%",
    "probabilityLiquidPrecipitation": "%",
    "precipitationQualityIndex": "äquivalente Messstationen je 2,5°-Box",
}

# Dateiname laut Steckbrief Abschnitt 7/14: das zweite Feld vor '.V07BHDF5'
# ist (gemessen an der GPM-Namenskonvention) der Monat erneut, nicht ein
# fester Text - wird deshalb gegen den aus dem Datum erwarteten Monat geprüft.
_DATEINAME_MUSTER = re.compile(
    r"^3B-MO\.MS\.MRG\.3IMERG\.(\d{4})(\d{2})01-S000000-E235959\.(\d{2})\.V07B\.HDF5$"
)

VERMINDERTE_GUETE_BREITENGRENZE = 60.0
# Begründung (Eigene Überlegung, docs/sources/imerg.md Abschnitt 3/9, als
# "nicht geprüft" vermerkt): "IR only covers 60°N-S" (Technical Documentation
# S. 22); jenseits davon sinkt die Verlässlichkeit zusätzlich durch gefrorene
# Flächen. 60° ist eine ANNAHME aus der Infrarot-Grenze, keine
# Anbieterempfehlung - nur ein Kennzeichen, keine Löschung von Werten.

# --- Netzwerk: Zeitlimits und Wiederholungen (CLAUDE.md "Netzwerk") --------
# Katalogabfrage: ein einziges, leichtes CMR-Granulat je Monat. Ein normaler
# Aufruf dauert Sekunden; 60s lassen auch einer langsamen Leitung reichlich
# Luft, ohne einen echten Hänger lange zu verschleppen (vgl.
# auth.LOGIN_ZEITLIMIT_SEKUNDEN = 120s für den etwas schwereren Login-Aufruf).
KATALOG_ZEITLIMIT_SEKUNDEN = 60.0
# Wachsende Pausen bei Katalog-Fehlschlag (Netz, CMR-Wartung): kurze Störungen
# (Sekunden bis Minuten) sind die Regel, eine ausgefallene Metadaten-API ist
# selten lange gestört. Summe knapp 10 Minuten, dann gilt die Abfrage als
# gescheitert (kein endloses Warten, CLAUDE.md "Netzwerk").
KATALOG_PAUSEN_SEKUNDEN = (10.0, 30.0, 60.0, 180.0, 300.0)
# Toleranz bei der Trefferzahl-Prüfung: ein Monat hat genau 1 Granulat;
# `get()` wird trotzdem mit etwas Überhang aufgerufen (wie bei vnp46a3), damit
# eine unerwartet gewachsene Antwort auffällt statt stillschweigend
# abgeschnitten zu werden.
_KATALOG_UEBERHANG = 5

# Dateidownload: eine Monatsdatei ist 16,7-18,7 MB groß (Steckbrief Abschnitt
# 11). max(5 Minuten, Größe / Mindestrate): 5 Minuten sind für eine Datei
# dieser Größe schon bei sehr langsamer Leitung (> 60 kB/s) ausreichend; die
# größenabhängige Formel schützt zusätzlich vor künftig größeren Dateien
# (V08). 100 kB/s als Mindestrate: dieselbe konservative Annahme wie beim
# Nachtlicht-Layer (vnp46a3.KACHEL_MINDESTRATE_BYTES_JE_S), weil die
# Bandbreite mit dessen laufendem Download geteilt wird.
DATEI_ZEITLIMIT_MINDEST_SEKUNDEN = 5 * 60
DATEI_MINDESTRATE_BYTES_JE_S = 100_000
# Budget je Datei (Versuche und Pausen zusammen), wie im Auftrag vorgegeben:
# danach gilt die Datei als nicht geladen (der Monat bleibt offen, kein
# Blocker für den ganzen Lauf).
DATEI_RETRY_BUDGET_SEKUNDEN = 30 * 60
# Wartezeit vor dem nächsten Versuch, verdoppelt sich (wie vnp46a3): eine
# kurze Drosselung durch NASA/CloudFront ist nach wenigen zig Sekunden
# vorbei, eine längere Störung wird nicht mit Anfragen überflutet.
DATEI_WARTEZEIT_BASIS_SEKUNDEN = 20
DATEI_WARTEZEIT_MAX_SEKUNDEN = 5 * 60
# So oft wird eine Datei geladen, wenn sie nicht zur Katalog-Größe passt oder
# nicht als HDF5 lesbar ist (wie vnp46a3.PRUEFSUMMEN_VERSUCHE); danach gilt
# sie als nicht geladen.
PRUEFSUMMEN_VERSUCHE = 3
# Gleichzeitige Downloads: fest auf 2 (nicht konfigurierbar hochgesetzt),
# weil die Bandbreite mit dem laufenden Nachtlicht-Hintergrund-Download
# (Prozess vnp46a3_lauf.py) geteilt wird; IMERG selbst hat nur 153 kleine
# Dateien (zusammen ~2,7 GB) und ist nicht auf hohe Parallelität angewiesen.
GLEICHZEITIGE_DOWNLOADS = 2

_STATUS_IM_TEXT = re.compile(r"Status code:\s*(\d{3})")

ZUSTAND_GELADEN = "geladen"
ZUSTAND_NICHT_VORHANDEN = "beim Anbieter nicht vorhanden"
ZUSTAND_NICHT_GELADEN = "nicht geladen"

# monat_fertig je Monat (siehe Modulkopf-Vertrag): 0 leer, 1 fertig,
# 3 wird geschrieben (ein Absturz dabei hinterlässt keinen als fertig
# geltenden Monat), 5 beim Anbieter nicht vorhanden (zählt NICHT als
# vorhanden, aber auch nicht wie "keine Daten": die Zahl ist ausdrücklich
# reserviert und von 0 unterscheidbar).
MONAT_LEER = 0
MONAT_FERTIG = 1
MONAT_WIRD_GESCHRIEBEN = 3
MONAT_NICHT_VORHANDEN = 5

FERTIG_VARIABLE = "monat_fertig"
WUERFEL_DIMS = ("zeit", "breite", "laenge")
WUERFEL_CHUNKS = (1, 180, 720)  # wie vnp46a3.WUERFEL_CHUNKS: ein Monat je Chunk-Schicht


# --- Fehlerklassen -----------------------------------------------------------
class KatalogFehler(RuntimeError):
    """Katalogabfrage oder -antwort passt nicht zum erwarteten Muster."""


class MonatFehltUnerwartet(KatalogFehler):
    """Katalog meldet 0 Granulate für einen Monat, der NICHT in BEIM_ANBIETER_NICHT_VORHANDEN steht."""


class ReferenzlisteVeraltet(KatalogFehler):
    """Katalog liefert ein Granulat für einen Monat, der als beim Anbieter nicht vorhanden geführt wird."""


class AchsenFehler(RuntimeError):
    """lat/lon oder Feldform in der HDF5-Datei passen nicht zum erwarteten IMERG-Gitter."""


class LeereRueckgabe(RuntimeError):
    """earthaccess.download gab eine leere Liste zurück: gilt als Fehlschlag, nicht als Erfolg.

    Hintergrund (Auftrag 2026-10-02): earthaccess.api.download() fängt
    AttributeError (z. B. ohne vorherigen Login) und gibt dann [] zurück,
    statt den Fehler durchzureichen (.venv/.../earthaccess/api.py). Eine
    leere Liste wird deshalb hier ausdrücklich wie ein Fehlschlag behandelt.
    """


class DownloadHaengt(RuntimeError):
    """Der Download einer Datei reagiert nicht innerhalb des Zeitlimits."""


class EarthdataZugangVerweigert(RuntimeError):
    """401 oder 403 mit EULA-Hinweis: echter Blocker, der Lauf endet."""


class MonatNichtGeladen(RuntimeError):
    """Eine Monatsdatei konnte nicht geladen werden (Budget verbraucht oder dauerhafter Fehler)."""

    def __init__(self, meldung: str, dauerhaft: bool):
        super().__init__(meldung)
        self.dauerhaft = dauerhaft


class AnmeldungFehlgeschlagen(RuntimeError):
    """Login bei NASA Earthdata fehlgeschlagen (nach Wiederholung, aleph/core/auth.py)."""


class WuerfelFormat(RuntimeError):
    """Der Würfel auf der SSD hat nicht den erwarteten Aufbau (feste Zeitachse, siehe vnp46a3)."""


class MonatAusserhalbZeitachse(ValueError):
    """Der Monat liegt nicht auf der Zeitachse des Würfels (2013-01 bis 2025-12)."""


class MonatSchonVorhanden(RuntimeError):
    """Der Monat ist im Würfel schon als fertig markiert und wird nicht überschrieben."""


class WuerfelSchreibFehler(RuntimeError):
    """Die Rückprüfung nach dem Schreiben fand Werte, die nicht den geschriebenen entsprechen."""


# Wartefunktionen für Katalog- und Datei-Wiederholung; Tests ersetzen sie,
# damit nicht wirklich gewartet wird (wie vnp46a3._schlafe_login).
_schlafe_katalog = time.sleep
_schlafe_datei = time.sleep


# --- Login -------------------------------------------------------------------
def anmelden(melde=None) -> None:
    """NASA-Login mit Wiederholung (aleph/core/auth.py, `login_mit_wiederholung`)."""
    ergebnis = login_mit_wiederholung(lambda: earthdata_login(), melde=melde, schlafe=time.sleep)
    if not ergebnis:
        raise AnmeldungFehlgeschlagen(abbruch_meldung(ergebnis))


# --- Katalog ------------------------------------------------------------------
def _monatsspanne(jahr: int, monat: int) -> tuple[str, str]:
    """Zeitfenster für die Katalogsuche eines Monats.

    Ein IMERG-Monatsgranulat spannt laut Katalog genau "1. 00:00:00 bis
    Monatsletzter 23:59:59.999" (Steckbrief Abschnitt 1). Die Suche beginnt
    trotzdem um 00:00:01 (wie bei vnp46a3._monatsspanne, dort begründet):
    CMR sucht nach Überlappung, und ab exakt 00:00:00 könnte ein
    Nachbargranulat, dessen Fenster an dieser Sekunde endet, mit auftauchen.
    """
    letzter_tag = monthrange(jahr, monat)[1]
    return (
        f"{jahr:04d}-{monat:02d}-01T00:00:01Z",
        f"{jahr:04d}-{monat:02d}-{letzter_tag:02d}T23:59:59Z",
    )


def _katalog_abfrage_einmal(jahr: int, monat: int) -> tuple[int, list]:
    """Ein einzelner (nicht wiederholter, nicht zeitlimitierter) Katalogaufruf."""
    start, ende = _monatsspanne(jahr, monat)
    auth = earthaccess.__auth__
    abfrage = earthaccess.DataGranules(auth if getattr(auth, "authenticated", False) else None).parameters(
        short_name=KURZNAME, version=KATALOG_VERSION, temporal=(start, ende)
    )
    gemeldet = abfrage.hits()
    granules = abfrage.get(gemeldet + _KATALOG_UEBERHANG) if gemeldet > 0 else []
    if len(granules) != gemeldet:
        raise KatalogFehler(
            f"{jahr:04d}-{monat:02d}: Katalog meldet {gemeldet} Treffer, geholt wurden {len(granules)}."
        )
    return gemeldet, granules


def _katalog_abfrage(jahr: int, monat: int, melde=None) -> tuple[int, list]:
    """Katalogabfrage mit Zeitlimit (`KATALOG_ZEITLIMIT_SEKUNDEN`) und wachsenden Pausen.

    Läuft in einem Hilfs-Thread, damit ein hängender Netzaufruf nicht
    unbegrenzt blockiert (CLAUDE.md "Netzwerk"); ein Zeitüberschreiten zählt
    wie jeder andere Fehlschlag und löst die nächste Pause aus. Jede
    Wiederholung geht über `melde` ins Protokoll.
    """
    letzter_fehler: BaseException | None = None
    pausen = (0.0, *KATALOG_PAUSEN_SEKUNDEN)
    for versuch, pause in enumerate(pausen, start=1):
        if pause:
            if melde is not None:
                melde(
                    f"{jahr:04d}-{monat:02d}: Katalogabfrage Versuch {versuch} nach "
                    f"{pause:.0f}s Pause (voriger Fehler: {type(letzter_fehler).__name__})."
                )
            _schlafe_katalog(pause)
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(_katalog_abfrage_einmal, jahr, monat)
        try:
            ergebnis = future.result(timeout=KATALOG_ZEITLIMIT_SEKUNDEN)
            pool.shutdown(wait=False)
            return ergebnis
        except concurrent.futures.TimeoutError:
            pool.shutdown(wait=False, cancel_futures=True)
            letzter_fehler = TimeoutError(
                f"Katalogabfrage reagiert seit über {KATALOG_ZEITLIMIT_SEKUNDEN:.0f}s nicht."
            )
        except Exception as fehler:  # bewusst breit: jeder Fehler löst eine Wiederholung aus
            pool.shutdown(wait=False)
            letzter_fehler = fehler
    raise KatalogFehler(
        f"{jahr:04d}-{monat:02d}: Katalogabfrage nach {len(pausen)} Versuchen gescheitert "
        f"({type(letzter_fehler).__name__}: {letzter_fehler})."
    ) from letzter_fehler


def _pruefe_dateiname(datei: str, jahr: int, monat: int) -> None:
    treffer = _DATEINAME_MUSTER.match(datei)
    if not treffer:
        raise KatalogFehler(f"{datei}: passt nicht zum erwarteten IMERG-V07B-Dateinamen.")
    dj, dm, dm2 = int(treffer.group(1)), int(treffer.group(2)), int(treffer.group(3))
    if (dj, dm) != (jahr, monat) or dm2 != monat:
        raise KatalogFehler(
            f"{datei}: Monat im Dateinamen ({dj:04d}-{dm:02d}, Feld {dm2:02d}) passt nicht zu "
            f"{jahr:04d}-{monat:02d}."
        )


@dataclass(frozen=True)
class MonatsSoll:
    """Was der Katalog über die Monatsdatei sagt: Name, Größe (Bytes), Erzeugungszeitpunkt."""

    datei: str
    groesse: int
    erzeugt: str | None


def _katalog_soll(jahr: int, monat: int, granule) -> MonatsSoll:
    """Dateiname, Größe (aus 'MB' in Bytes umgerechnet) und Erzeugungszeit laut Katalog.

    Der Katalog liefert KEINE Prüfsumme (Steckbrief Abschnitt 1); `Name` ist
    "Not provided", der Dateiname kommt deshalb aus dem Download-Link. Die
    Größe steht nur als `Size`/`SizeUnit` ("MB") in
    `ArchiveAndDistributionInformation`; Bytes = round(Size * 1024 * 1024)
    (Steckbrief Abschnitt 1: ergibt eine ganze Bytezahl, exakt).
    """
    dateien = [l.rsplit("/", 1)[-1] for l in granule.data_links() if l.upper().endswith(".HDF5")]
    if len(set(dateien)) != 1:
        raise KatalogFehler(f"{jahr:04d}-{monat:02d}: kein eindeutiger .HDF5-Link ({dateien}).")
    datei = dateien[0]
    _pruefe_dateiname(datei, jahr, monat)
    angaben = granule["umm"].get("DataGranule", {})
    verteilung = angaben.get("ArchiveAndDistributionInformation") or []
    passend = [a for a in verteilung if a.get("Size") is not None]
    if len(passend) != 1:
        raise KatalogFehler(f"{datei}: Katalog nennt {len(passend)} Größenangaben, erwartet genau eine.")
    einheit = passend[0].get("SizeUnit")
    if einheit != "MB":
        raise KatalogFehler(f"{datei}: unerwartete Größeneinheit {einheit!r} (erwartet 'MB').")
    groesse_bytes = round(float(passend[0]["Size"]) * 1024 * 1024)
    erzeugt = angaben.get("ProductionDateTime")
    return MonatsSoll(datei, groesse_bytes, erzeugt)


def _einordnen_katalog(jahr: int, monat: int, gemeldet: int, granules: list) -> tuple[str, MonatsSoll | None, str]:
    """Ordnet einen Monat gegen den Katalog UND gegen BEIM_ANBIETER_NICHT_VORHANDEN ein.

    Rückgabe: (Zustand, Soll-Angaben oder None, Grund/Hinweis). Siehe
    Modulkopf-Vertrag: ein fehlender ANDERER Monat ist ein Fehler, kein
    stilles Übergehen; taucht einer der drei erwarteten Lückenmonate DOCH im
    Katalog auf, ist auch das ein Fehler (Referenzliste veraltet / V08
    versehentlich eingemischt).
    """
    name = f"{jahr:04d}-{monat:02d}"
    referenziert_fehlend = (jahr, monat) in BEIM_ANBIETER_NICHT_VORHANDEN
    if gemeldet == 0:
        if referenziert_fehlend:
            return (
                ZUSTAND_NICHT_VORHANDEN,
                None,
                "Katalog meldet 0 Granulate; passt zur bekannten Lücke (V07 Final endet 2025-09, "
                "NASA-Mitteilung IMERG V08 Transition Schedule, abgerufen 2026-10-02).",
            )
        raise MonatFehltUnerwartet(
            f"{name}: Katalog meldet 0 Granulate, dieser Monat steht aber NICHT in "
            "BEIM_ANBIETER_NICHT_VORHANDEN. Kein stilles Übergehen: Katalog oder Version prüfen."
        )
    if gemeldet != 1:
        raise KatalogFehler(f"{name}: Katalog meldet {gemeldet} Granulate, erwartet genau 1.")
    if referenziert_fehlend:
        raise ReferenzlisteVeraltet(
            f"{name}: Katalog liefert jetzt ein Granulat, obwohl dieser Monat in "
            "BEIM_ANBIETER_NICHT_VORHANDEN als fehlend geführt wird. Referenzliste veraltet oder "
            "Version prüfen - V08 darf nicht still eingemischt werden."
        )
    soll = _katalog_soll(jahr, monat, granules[0])
    return ZUSTAND_GELADEN, soll, ""


# --- Dateidownload -------------------------------------------------------------
def _datei_zeitlimit(groesse_bytes: int | None) -> float:
    if not groesse_bytes:
        return DATEI_ZEITLIMIT_MINDEST_SEKUNDEN
    return max(DATEI_ZEITLIMIT_MINDEST_SEKUNDEN, groesse_bytes / DATEI_MINDESTRATE_BYTES_JE_S)


def _statuscode(fehler: BaseException) -> int | None:
    treffer = _STATUS_IM_TEXT.search(str(fehler))
    return int(treffer.group(1)) if treffer else None


def _ist_zugangsblocker(fehler: BaseException, status: int | None) -> bool:
    """401 oder 403 mit EULA-Hinweis: Blocker (Auftrag, HTTP-403-EULA-Fall)."""
    if isinstance(fehler, EulaNotAccepted) or status == 401:
        return True
    return "eula" in str(fehler).lower()


def _ist_vorlaeufig(fehler: BaseException, status: int | None) -> bool:
    """True, wenn Warten und Wiederholen sinnvoll ist (5xx, Zeitüberschreitung, Verbindung, 408/429)."""
    if isinstance(fehler, (DownloadHaengt, ServiceOutage, OSError, LeereRueckgabe)):
        return True
    if isinstance(fehler, DownloadFailure):
        return status is None or status >= 500 or status in (408, 429)
    return False


_ZUGANG_MELDUNG = (
    "Anwendung NASA GESDISC DATA ARCHIVE im Earthdata-Profil freigeben: "
    "https://urs.earthdata.nasa.gov/approve_app?client_id=e2WVk8Pw6weeLUKZYOxvTQ"
)


def _lade_monatsdatei(granule, soll: MonatsSoll, ziel_ordner: Path, melde=None) -> Path:
    """Lädt eine einzelne Monatsdatei über `earthaccess.download`, mit eigenem Zeitlimit
    und hartnäckiger Wiederholung bei vorübergehenden Fehlern (siehe Modulkopf/Konstanten).

    Eine leere Rückgabeliste von earthaccess.download gilt als Fehlschlag
    (`LeereRueckgabe`), nicht als Erfolg (siehe Klassendoku). 401/EULA-403
    beenden sofort mit `EarthdataZugangVerweigert` (Blocker).
    """
    verbraucht = 0.0
    versuch = 0
    while True:
        versuch += 1
        zeitlimit = _datei_zeitlimit(soll.groesse)
        beginn = time.monotonic()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(earthaccess.download, [granule], str(ziel_ordner))
        try:
            ergebnis = future.result(timeout=zeitlimit)
            pool.shutdown(wait=False)
            if not ergebnis:
                raise LeereRueckgabe(
                    f"{soll.datei}: earthaccess.download gab eine leere Liste zurück."
                )
            return Path(ergebnis[0])
        except concurrent.futures.TimeoutError:
            pool.shutdown(wait=False, cancel_futures=True)
            fehler: BaseException = DownloadHaengt(
                f"{soll.datei}: reagiert seit über {zeitlimit / 60:.1f} Minuten nicht (Versuch {versuch})."
            )
        except Exception as gefangen:  # bewusst breit: unten wird nach Art des Fehlers entschieden
            pool.shutdown(wait=False)
            fehler = gefangen
        verbraucht += time.monotonic() - beginn

        status = _statuscode(fehler)
        if _ist_zugangsblocker(fehler, status):
            raise EarthdataZugangVerweigert(
                f"Anmeldung prüfen: {soll.datei}: {type(fehler).__name__} (Status {status}). "
                f"{_ZUGANG_MELDUNG}"
            ) from fehler
        if not _ist_vorlaeufig(fehler, status):
            raise MonatNichtGeladen(
                f"{soll.datei}: dauerhafter Fehler ({fehler}), kein weiterer Versuch.", dauerhaft=True
            ) from fehler

        wartezeit = min(DATEI_WARTEZEIT_BASIS_SEKUNDEN * (2 ** (versuch - 1)), DATEI_WARTEZEIT_MAX_SEKUNDEN)
        if verbraucht + wartezeit > DATEI_RETRY_BUDGET_SEKUNDEN:
            raise MonatNichtGeladen(
                f"{soll.datei}: nach {versuch} Versuchen in {verbraucht / 60:.0f} Minuten aufgegeben "
                f"({fehler}).",
                dauerhaft=False,
            ) from fehler
        if melde is not None:
            melde(
                f"{soll.datei}: Wiederholung {versuch} nach Fehler ({type(fehler).__name__}: {fehler}); "
                f"warte {wartezeit:.0f}s."
            )
        _schlafe_datei(wartezeit)
        verbraucht += wartezeit


def _ist_lesbare_hdf5(pfad: Path) -> bool:
    try:
        with h5py.File(pfad, "r"):
            return True
    except OSError:
        return False


def _pruefe_rohdatei(pfad: Path, soll: MonatsSoll, jahr: int, monat: int) -> str | None:
    """None, wenn Name, Größe, Lesbarkeit und Monat passen; sonst der Grund."""
    if pfad.name != soll.datei:
        return f"Dateiname {pfad.name} statt {soll.datei}"
    groesse = pfad.stat().st_size
    if groesse != soll.groesse:
        return f"{pfad.name}: Größe {groesse} Bytes statt {soll.groesse} laut Katalog"
    if not _ist_lesbare_hdf5(pfad):
        return f"{pfad.name}: nicht als HDF5 lesbar"
    try:
        _pruefe_dateiname(pfad.name, jahr, monat)
    except KatalogFehler as fehler:
        return str(fehler)
    return None


def hole_monatsdatei(jahr: int, monat: int, soll: MonatsSoll, granule, ziel_ordner: Path, melde=None) -> Path:
    """Liefert die geprüfte Rohdatei eines Monats: vorhandene Datei wiederverwenden, sonst laden.

    Bis zu `PRUEFSUMMEN_VERSUCHE` Ladeversuche, wenn Größe/Lesbarkeit/Monat
    nicht passen (wie vnp46a3._lade_und_pruefe_kachel); danach gilt die Datei
    als nicht geladen.
    """
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    vorhanden = ziel_ordner / soll.datei
    if vorhanden.exists():
        grund = _pruefe_rohdatei(vorhanden, soll, jahr, monat)
        if grund is None:
            if melde is not None:
                melde(f"{jahr:04d}-{monat:02d}: vorhandene Rohdatei wiederverwendet ({vorhanden.name}).")
            return vorhanden
        vorhanden.unlink()
        if melde is not None:
            melde(f"{jahr:04d}-{monat:02d}: vorhandene Rohdatei verworfen ({grund}); wird neu geladen.")
    letzter_grund = ""
    for versuch in range(1, PRUEFSUMMEN_VERSUCHE + 1):
        pfad = _lade_monatsdatei(granule, soll, ziel_ordner, melde=melde)
        grund = _pruefe_rohdatei(pfad, soll, jahr, monat)
        if grund is None:
            return pfad
        pfad.unlink(missing_ok=True)
        letzter_grund = grund
        if melde is not None:
            melde(f"{jahr:04d}-{monat:02d}: Versuch {versuch} verworfen ({grund}).")
    raise MonatNichtGeladen(
        f"{jahr:04d}-{monat:02d}: passt nach {PRUEFSUMMEN_VERSUCHE} Versuchen nicht zum Katalog "
        f"({letzter_grund}).",
        dauerhaft=False,
    )


def _sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as datei:
        for block in iter(lambda: datei.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


# --- HDF5 lesen: Achsen erkennen, Fehlwerte maskieren --------------------------
#: Toleranz für die Achsenprüfung in Grad. IMERG speichert lat/lon laut
#: Steckbrief/Probe als float32; float32 hat bei Beträgen um 90-180 nur eine
#: Auflösung von rund 1e-5 (90 * 2⁻²³). 1e-4° ist großzügig darüber, aber
#: immer noch weit unter der Pixelgröße (0,1°) - ein echter Achsenfehler
#: (z. B. vertauschte Reihenfolge oder falscher Rand) weicht um Zehntelgrad
#: oder mehr ab und wird zuverlässig erkannt.
ACHSEN_TOLERANZ_GRAD = 1e-4


def _pruefe_achse(werte: np.ndarray, erwartete_anzahl: int, zellgroesse: float, rand: float, name: str) -> None:
    """Bricht ab, wenn `werte` nicht genau `erwartete_anzahl` gleichmäßige Mittelpunkte
    im Abstand `zellgroesse`° hat, beginnend am erwarteten Rand (Toleranz ACHSEN_TOLERANZ_GRAD)."""
    werte = np.asarray(werte, dtype="float64")
    if werte.shape != (erwartete_anzahl,):
        raise AchsenFehler(f"{name}: Form {werte.shape}, erwartet ({erwartete_anzahl},).")
    diffs = np.diff(werte)
    schritt = float(diffs[0])
    if abs(abs(schritt) - zellgroesse) > ACHSEN_TOLERANZ_GRAD or not np.allclose(
        diffs, schritt, atol=ACHSEN_TOLERANZ_GRAD
    ):
        raise AchsenFehler(f"{name}: nicht gleichmäßig in Schritten von {zellgroesse}° verteilt.")
    erster_erwartet = rand + zellgroesse / 2 if schritt > 0 else -rand - zellgroesse / 2
    if abs(float(werte[0]) - erster_erwartet) > ACHSEN_TOLERANZ_GRAD:
        raise AchsenFehler(f"{name}: erster Mittelpunkt {werte[0]}, erwartet {erster_erwartet}.")


def _feld_2d(dataset, lat_len: int, lon_len: int) -> np.ndarray:
    """Liest ein Feld und bringt es auf die Form (lat_len, lon_len), ohne eine feste
    Achsenreihenfolge anzunehmen (siehe Modulkopf: Doku nennt 1800x3600, die Datei hat
    aber wahrscheinlich die Form time=1 x lon=3600 x lat=1800). Bestimmt wird das an
    der tatsächlichen Länge jeder Achse; passt keine Kombination, bricht es ab.
    """
    arr = dataset[:]
    form = arr.shape
    if arr.ndim == 3:
        zeit_achsen = [i for i, g in enumerate(form) if g not in (lat_len, lon_len)]
        if len(zeit_achsen) != 1 or form[zeit_achsen[0]] != 1:
            raise AchsenFehler(f"{dataset.name}: unerwartete Form {form} (lat={lat_len}, lon={lon_len}).")
        arr = np.take(arr, 0, axis=zeit_achsen[0])
        form = arr.shape
    if arr.ndim != 2 or lat_len not in form or lon_len not in form:
        raise AchsenFehler(f"{dataset.name}: unerwartete Form {form} (erwartet lat={lat_len}, lon={lon_len}).")
    if form == (lat_len, lon_len):
        return arr
    if form == (lon_len, lat_len):
        return arr.T
    raise AchsenFehler(f"{dataset.name}: unerwartete Form {form} (erwartet lat={lat_len}, lon={lon_len}).")


def _ausrichten(arr: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Bringt ein (lat,lon)-Feld in aufsteigende Reihenfolge (Süd->Nord, West->Ost),
    unabhängig davon, wie die Datei es tatsächlich speichert."""
    if lat[0] > lat[-1]:
        arr = arr[::-1, :]
    if lon[0] > lon[-1]:
        arr = arr[:, ::-1]
    return arr


def _gueltig_maske(arr: np.ndarray, fuellwert_attribut) -> np.ndarray:
    """Jeder Fehlwert, jeder negative oder nicht endliche Wert wird ungültig (VOR jeder Mittelung).

    Niederschlag/Zählwerte sind laut Doku nie negativ; da FEHLWERT_DOKU
    (-9999,9) selbst negativ ist, deckt `arr >= 0` den Normalfall schon ab -
    die expliziten Vergleiche bleiben trotzdem stehen, damit ein anderer
    Fehlwert (z. B. ein _FillValue-Attribut) nicht übersehen wird.
    """
    # Toleranz 1e-2: die Werte sind float32 (Datei) bzw. wurden dorthin
    # gerundet; float32 hat bei |-9999,9| nur rund 1e-3 Auflösung. 1e-2 ist
    # großzügig darüber, aber noch viele Größenordnungen unter jedem
    # plausiblen echten Messwert in der Nähe von 0.
    maske = np.isfinite(arr) & (arr >= 0)
    if fuellwert_attribut is not None:
        maske &= ~np.isclose(arr, float(fuellwert_attribut), rtol=0, atol=1e-2)
    maske &= ~np.isclose(arr, FEHLWERT_DOKU, rtol=0, atol=1e-2)
    return maske


def _lies_monatsdatei(pfad: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Liest alle Felder einer Monatsdatei, geprüft und ausgerichtet (Süd->Nord, West->Ost).

    Rückgabe je Feld: (Werte float32, gültig bool), beide Form (1800,3600).
    """
    ergebnis: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with h5py.File(pfad, "r") as datei:
        if H5_GRUPPE not in datei:
            raise AchsenFehler(f"{pfad.name}: Gruppe '{H5_GRUPPE}' fehlt.")
        gruppe = datei[H5_GRUPPE]
        if "lat" not in gruppe or "lon" not in gruppe:
            raise AchsenFehler(f"{pfad.name}: 'lat'/'lon' fehlen in der Gruppe '{H5_GRUPPE}'.")
        lat = gruppe["lat"][:]
        lon = gruppe["lon"][:]
        _pruefe_achse(lat, QUELL_BREITE, QUELLZELLE_GRAD, -90.0, f"{pfad.name}: lat")
        _pruefe_achse(lon, QUELL_LAENGE, QUELLZELLE_GRAD, -180.0, f"{pfad.name}: lon")
        for feld in FELD_EINHEITEN:
            if feld not in gruppe:
                raise AchsenFehler(f"{pfad.name}: Feld '{feld}' fehlt in der Gruppe '{H5_GRUPPE}'.")
            dataset = gruppe[feld]
            fuellwert = dataset.attrs.get("_FillValue")
            arr = _feld_2d(dataset, len(lat), len(lon)).astype("float64")
            arr = _ausrichten(arr, lat, lon)
            gueltig = _gueltig_maske(arr, fuellwert)
            ergebnis[feld] = (arr.astype("float32"), gueltig)
    return ergebnis


# --- Exakte flächengewichtete Aggregation (siehe Modulkopf) --------------------
def _eindimensionale_ueberlappung(
    n_ziel: int, ziel_schritt_ticks: int, n_quelle: int, quelle_schritt_ticks: int
) -> list[list[tuple[int, int, int]]]:
    """Für jede Zielzelle m: Liste von (Quellindex i, Tick-Start, Tick-Ende) der Überlappung.

    Beide Gitter beginnen am selben Rand (Tick 0 = Südrand bzw. Westrand);
    alle Werte sind ganze Ticks (0,05°), keine Fließkommazahlen - siehe
    Modulkopf. `n_ziel * ziel_schritt_ticks` muss `n_quelle *
    quelle_schritt_ticks` ergeben (beide decken denselben Bereich lückenlos).
    """
    ergebnis: list[list[tuple[int, int, int]]] = []
    for m in range(n_ziel):
        a = m * ziel_schritt_ticks
        b = a + ziel_schritt_ticks
        segmente = []
        i = a // quelle_schritt_ticks
        while i * quelle_schritt_ticks < b:
            c = i * quelle_schritt_ticks
            d = c + quelle_schritt_ticks
            t0, t1 = max(a, c), min(b, d)
            if t1 > t0:
                segmente.append((i, t0, t1))
            i += 1
        ergebnis.append(segmente)
    return ergebnis


def _baue_gewichte():
    """Baut die (dünnbesetzten) Gewichtsmatrizen W_lat, B_lat, W_lon, B_lon (siehe Modulkopf).

    W_* = flächengewichtet (sin-Differenz für Breite, Tick-Länge für Länge),
    B_* = reine 0/1-Überlappungsanzeige (für die Pixelzählung, ungewichtet).
    """
    lat_segmente = _eindimensionale_ueberlappung(GITTER_BREITE, ZIEL_SCHRITT_TICKS, QUELL_BREITE, QUELLE_SCHRITT_TICKS)
    lon_segmente = _eindimensionale_ueberlappung(GITTER_LAENGE, ZIEL_SCHRITT_TICKS, QUELL_LAENGE, QUELLE_SCHRITT_TICKS)

    lat_rows, lat_cols, lat_vals = [], [], []
    for m, segmente in enumerate(lat_segmente):
        for i, t0, t1 in segmente:
            grad_unten = -90.0 + t0 * TICK_GRAD
            grad_oben = -90.0 + t1 * TICK_GRAD
            gewicht = np.sin(np.radians(grad_oben)) - np.sin(np.radians(grad_unten))
            lat_rows.append(m)
            lat_cols.append(i)
            lat_vals.append(gewicht)
    w_lat = sp.csr_matrix((lat_vals, (lat_rows, lat_cols)), shape=(GITTER_BREITE, QUELL_BREITE))
    b_lat = sp.csr_matrix(
        (np.ones(len(lat_rows)), (lat_rows, lat_cols)), shape=(GITTER_BREITE, QUELL_BREITE)
    )

    lon_rows, lon_cols, lon_vals = [], [], []
    for n, segmente in enumerate(lon_segmente):
        for j, t0, t1 in segmente:
            lon_rows.append(n)
            lon_cols.append(j)
            lon_vals.append(t1 - t0)
    w_lon = sp.csr_matrix(
        (lon_vals, (lon_rows, lon_cols)), shape=(GITTER_LAENGE, QUELL_LAENGE), dtype="float64"
    )
    b_lon = sp.csr_matrix(
        (np.ones(len(lon_rows)), (lon_rows, lon_cols)), shape=(GITTER_LAENGE, QUELL_LAENGE)
    )
    return w_lat, b_lat, w_lon, b_lon


@lru_cache(maxsize=1)
def _gewichte():
    w_lat, b_lat, w_lon, b_lon = _baue_gewichte()
    a_lat_voll = np.asarray(w_lat.sum(axis=1)).reshape(-1)
    return w_lat, b_lat, w_lon, b_lon, a_lat_voll


def _regrid_feld(
    werte: np.ndarray, gueltig: np.ndarray, w_lat, b_lat, w_lon, b_lon, a_lat_voll: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exakte flächengewichtete Mittelung eines (1800,3600)-Feldes auf (720,1440).

    Rückgabe: (Zellwert, gültiger Flächenanteil 0..1, Zahl gültiger
    überlappender Quellpixel 0..9), alle in Süd->Nord-, West->Ost-Reihenfolge
    (Ausrichtung auf die ALEPH-Konvention passiert danach, s. `_flip_sn`).
    """
    v = gueltig.astype("float64")
    x = np.where(gueltig, werte, 0.0).astype("float64")

    zaehler = w_lon.dot(w_lat.dot(x * v).T).T
    nenner = w_lon.dot(w_lat.dot(v).T).T
    pixel = b_lon.dot(b_lat.dot(v).T).T

    with np.errstate(invalid="ignore", divide="ignore"):
        zellwert = np.where(nenner > 0, zaehler / nenner, np.nan)
    anteil = np.clip(nenner / (a_lat_voll[:, None] * A_LON_VOLL_TICKS), 0.0, 1.0)
    return zellwert.astype("float32"), anteil.astype("float32"), np.round(pixel).astype("int16")


def _flip_sn(arr: np.ndarray) -> np.ndarray:
    """Dreht ein Süd->Nord-Feld auf die ALEPH-Konvention (Zeile 0 = 89,875°N)."""
    return np.flip(arr, axis=0)


def verminderte_guete_maske() -> np.ndarray:
    """True, wo |Breite| > VERMINDERTE_GUETE_BREITENGRENZE: Kennzeichen, keine Löschung
    (Begründung siehe Modulkopf-Konstante)."""
    breite, _ = _gitter_koordinaten()
    return np.abs(breite) > VERMINDERTE_GUETE_BREITENGRENZE


# --- Verarbeitung eines Monats -------------------------------------------------
def _verarbeite_monat(pfad: Path, jahr: int, monat: int) -> xr.Dataset:
    felder = _lies_monatsdatei(pfad)
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = _gewichte()
    tage = monthrange(jahr, monat)[1]

    niederschlag, anteil, pixel = _regrid_feld(*felder["precipitation"], w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    niederschlag = niederschlag * (24 * tage)  # mm/h -> mm/Monat (Doku: mittlere Rate über den Kalendermonat)

    fehler, _, _ = _regrid_feld(*felder["randomError"], w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    fehler = fehler * (24 * tage)

    gewichtung, _, _ = _regrid_feld(*felder["gaugeRelativeWeighting"], w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    guete, _, _ = _regrid_feld(*felder["precipitationQualityIndex"], w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    fluessig, _, _ = _regrid_feld(
        *felder["probabilityLiquidPrecipitation"], w_lat, b_lat, w_lon, b_lon, a_lat_voll
    )

    breite, laenge = _gitter_koordinaten()
    zeit = [np.datetime64(f"{jahr:04d}-{monat:02d}-01")]
    daten = {
        "precipitation_mm_monat": _flip_sn(niederschlag).astype("float32"),
        "precipitation_gueltig_anteil": _flip_sn(anteil).astype("float32"),
        "precipitation_gueltige_pixel": _flip_sn(pixel).astype("int16"),
        "random_error_mm_monat": _flip_sn(fehler).astype("float32"),
        "gauge_relative_weighting": _flip_sn(gewichtung).astype("float32"),
        "quality_index": _flip_sn(guete).astype("float32"),
        "probability_liquid": _flip_sn(fluessig).astype("float32"),
    }
    data_vars = {k: (WUERFEL_DIMS, w[np.newaxis, :, :]) for k, w in daten.items()}
    return xr.Dataset(
        data_vars,
        coords={"zeit": zeit, "breite": breite, "laenge": laenge},
        attrs={
            "quelle": META["quelle"],
            "einheit_precipitation_mm_monat": "mm/Monat (umgerechnet aus mm/h x 24 x Tage des Kalendermonats)",
            "einheit_random_error_mm_monat": (
                "mm/Monat; flächengewichteter Mittelwert der Pixelfehler = Obergrenze bei voll "
                "korrelierten Fehlern, KEIN exakter Zellfehler (docs/sources/imerg.md Abschnitt 8)"
            ),
            "herkunftseinheit_precipitation": FELD_EINHEITEN["precipitation"],
            "herkunftseinheit_random_error": FELD_EINHEITEN["randomError"],
            "herkunftseinheit_gauge_relative_weighting": FELD_EINHEITEN["gaugeRelativeWeighting"],
            "herkunftseinheit_quality_index": FELD_EINHEITEN["precipitationQualityIndex"],
            "herkunftseinheit_probability_liquid": FELD_EINHEITEN["probabilityLiquidPrecipitation"],
            "aggregation": (
                "exakte flächengewichtete (konservative) Mittelung 0,1°->0,25° "
                "(Verhältnis 2,5, keine ganze Zahl; Begründung im Modulkopf von aleph/layers/imerg.py)"
            ),
        },
    )


# --- Würfel --------------------------------------------------------------------
def _wuerfel_pfad() -> Path:
    return io.wuerfel_pfad("imerg.zarr")


def _wuerfel_variablen() -> dict[str, str]:
    return {
        "precipitation_mm_monat": "float32",
        "precipitation_gueltig_anteil": "float32",
        "precipitation_gueltige_pixel": "int16",
        "random_error_mm_monat": "float32",
        "gauge_relative_weighting": "float32",
        "quality_index": "float32",
        "probability_liquid": "float32",
    }


def _monat_index(jahr: int, monat: int) -> int:
    ziel = np.datetime64(f"{jahr:04d}-{monat:02d}-01", "ns")
    treffer = np.flatnonzero(zeitachse() == ziel)
    if len(treffer) != 1:
        raise MonatAusserhalbZeitachse(
            f"{jahr:04d}-{monat:02d} liegt nicht auf der Zeitachse des Würfels "
            f"({ZEITACHSE_START[0]:04d}-{ZEITACHSE_START[1]:02d} bis "
            f"{ZEITACHSE_ENDE[0]:04d}-{ZEITACHSE_ENDE[1]:02d})."
        )
    return int(treffer[0])


def _lege_wuerfel_an(pfad: Path) -> None:
    """Legt den leeren Würfel mit fester Zeitachse an (Werte NaN, Zähler 0, nichts fertig).

    Wie vnp46a3._lege_wuerfel_an: zuerst an einem Hilfspfad gebaut, erst am
    Ende umbenannt, damit ein Abbruch keinen halbfertigen Würfel hinterlässt.
    """
    achse = zeitachse()
    breite, laenge = _gitter_koordinaten()
    hilfspfad = pfad.with_name(pfad.name + ".neu")
    if hilfspfad.exists():
        shutil.rmtree(hilfspfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    xr.Dataset(
        coords={"zeit": achse, "breite": breite, "laenge": laenge},
        attrs={"quelle": META["quelle"]},
    ).to_zarr(hilfspfad, mode="w")
    form = (len(achse), GITTER_BREITE, GITTER_LAENGE)
    for name, dtyp in _wuerfel_variablen().items():
        leerwert = np.float32(np.nan) if dtyp == "float32" else np.int16(0)
        xr.Dataset({name: (WUERFEL_DIMS, np.broadcast_to(leerwert, form))}).to_zarr(
            hilfspfad, mode="a", encoding={name: {"chunks": WUERFEL_CHUNKS}}
        )
    xr.Dataset({FERTIG_VARIABLE: (("zeit",), np.zeros(len(achse), dtype="int8"))}).to_zarr(hilfspfad, mode="a")
    os.replace(hilfspfad, pfad)


def _pruefe_wuerfel_format(pfad: Path) -> None:
    with xr.open_zarr(pfad, chunks=None) as ds:
        fehlend = [v for v in [*_wuerfel_variablen(), FERTIG_VARIABLE] if v not in ds]
        achse_ok = ds.sizes.get("zeit") == len(zeitachse()) and np.array_equal(ds["zeit"].values, zeitachse())
    if fehlend or not achse_ok:
        raise WuerfelFormat(
            f"Der Würfel {pfad} hat nicht den erwarteten Aufbau "
            f"{'; fehlende Variablen: ' + ', '.join(fehlend) if fehlend else ''}"
            f"{'; Zeitachse stimmt nicht' if not achse_ok else ''}. Nichts geschrieben."
        )


def _setze_monatsstatus(pfad: Path, index: int, wert: int) -> None:
    region = {"zeit": slice(index, index + 1)}
    xr.Dataset({FERTIG_VARIABLE: (("zeit",), np.array([wert], dtype="int8"))}).to_zarr(
        pfad, mode="r+", region=region
    )


def monatsstatus(jahr: int, monat: int) -> int:
    """Wert von `monat_fertig` für einen Monat (0, wenn es noch keinen Würfel gibt)."""
    pfad = _wuerfel_pfad()
    if not pfad.exists():
        return MONAT_LEER
    _pruefe_wuerfel_format(pfad)
    with xr.open_zarr(pfad, chunks=None) as ds:
        return int(ds[FERTIG_VARIABLE].values[_monat_index(jahr, monat)])


def vorhandene_monate() -> set[tuple[int, int]]:
    """Monate mit `monat_fertig == MONAT_FERTIG` (1); weder leere (0) noch
    'beim Anbieter nicht vorhanden' (5) zählen als vorhanden."""
    pfad = _wuerfel_pfad()
    if not pfad.exists():
        return set()
    _pruefe_wuerfel_format(pfad)
    with xr.open_zarr(pfad, chunks=None) as ds:
        zeiten = ds["zeit"].values
        fertig = ds[FERTIG_VARIABLE].values
    monate = set()
    for z, f in zip(zeiten, fertig):
        if f == MONAT_FERTIG:
            datum = np.datetime64(z, "M").astype(object)
            monate.add((datum.year, datum.month))
    return monate


def schreibe_in_wuerfel(monatsdaten: xr.Dataset) -> None:
    """Schreibt einen Monat an seine Position; legt den Würfel beim ersten Mal an.

    Schritte wie vnp46a3.schreibe_in_wuerfel: Zustand erst auf "wird
    geschrieben" (3), dann Werte schreiben, zurücklesen und vergleichen, erst
    danach auf "fertig" (1) setzen. Ein schon fertiger Monat wird NIE
    überschrieben.
    """
    if monatsdaten.sizes.get("zeit") != 1:
        raise ValueError("Es muss genau ein Monat (ein Zeitschritt) übergeben werden.")
    datum = np.datetime64(monatsdaten["zeit"].values[0], "M").astype(object)
    index = _monat_index(datum.year, datum.month)

    pfad = _wuerfel_pfad()
    if not pfad.exists():
        _lege_wuerfel_an(pfad)
    _pruefe_wuerfel_format(pfad)

    breite, laenge = _gitter_koordinaten()
    if not (
        np.allclose(monatsdaten["breite"].values, breite) and np.allclose(monatsdaten["laenge"].values, laenge)
    ):
        raise WuerfelFormat("Die Gitterkoordinaten des Monats passen nicht zum Würfel. Nichts geschrieben.")

    with xr.open_zarr(pfad, chunks=None) as ds:
        bisher = int(ds[FERTIG_VARIABLE].values[index])
    if bisher == MONAT_FERTIG:
        raise MonatSchonVorhanden(f"{datum.year:04d}-{datum.month:02d} ist im Würfel schon fertig.")

    variablen = list(_wuerfel_variablen())
    region = {"zeit": slice(index, index + 1)}
    _setze_monatsstatus(pfad, index, MONAT_WIRD_GESCHRIEBEN)
    monatsdaten[variablen].drop_vars(["zeit", "breite", "laenge"]).to_zarr(pfad, mode="r+", region=region)

    with xr.open_zarr(pfad, chunks=None) as ds:
        for name in variablen:
            gelesen = ds[name].isel(zeit=index).values
            geschrieben = monatsdaten[name].values[0]
            if not np.array_equal(gelesen, geschrieben, equal_nan=True):
                raise WuerfelSchreibFehler(
                    f"{datum.year:04d}-{datum.month:02d}: {name} stimmt nach dem Schreiben nicht."
                )
    _setze_monatsstatus(pfad, index, MONAT_FERTIG)


def setze_nicht_vorhanden(jahr: int, monat: int) -> None:
    """Markiert einen Monat als 'beim Anbieter nicht vorhanden' (5), ohne Werte zu schreiben.

    Nur für Monate in BEIM_ANBIETER_NICHT_VORHANDEN, nur solange der Monat im
    Würfel noch leer ist: ein schon gefüllter Monat (1) widerspräche der
    Referenz und wird NICHT überschrieben (Programmfehler, kein stilles
    Weiterlaufen).
    """
    if (jahr, monat) not in BEIM_ANBIETER_NICHT_VORHANDEN:
        raise ValueError(f"{jahr:04d}-{monat:02d} steht nicht in BEIM_ANBIETER_NICHT_VORHANDEN.")
    pfad = _wuerfel_pfad()
    if not pfad.exists():
        _lege_wuerfel_an(pfad)
    _pruefe_wuerfel_format(pfad)
    index = _monat_index(jahr, monat)
    with xr.open_zarr(pfad, chunks=None) as ds:
        bisher = int(ds[FERTIG_VARIABLE].values[index])
    if bisher == MONAT_FERTIG:
        raise MonatSchonVorhanden(
            f"{jahr:04d}-{monat:02d} hat im Würfel schon Daten (Zustand 1), widerspricht aber "
            "BEIM_ANBIETER_NICHT_VORHANDEN. Nicht überschrieben - Referenzliste oder Würfel prüfen."
        )
    if bisher == MONAT_NICHT_VORHANDEN:
        return
    _setze_monatsstatus(pfad, index, MONAT_WIRD_GESCHRIEBEN)
    _setze_monatsstatus(pfad, index, MONAT_NICHT_VORHANDEN)


# --- Manifest (Spalten siehe Auftrag Punkt 8) -----------------------------------
MANIFEST_SPALTEN = (
    "monat",
    "zustand",
    "datei",
    "groesse_bytes",
    "groesse_bytes_gemessen",
    "sha256",
    "abrufdatum_utc",
    "katalog_erzeugt",
    "herkunftseinheit",
    "grund",
)


@dataclass
class ManifestZeile:
    monat: str
    zustand: str
    datei: str = "-"
    groesse_bytes: str = "-"
    groesse_bytes_gemessen: str = "-"
    sha256: str = "-"
    abrufdatum_utc: str = "-"
    katalog_erzeugt: str = "-"
    herkunftseinheit: str = "-"
    grund: str = "-"


def manifest_pfad() -> Path:
    return io.aleph_data_dir() / "protokoll" / "manifeste" / "imerg" / "manifest_V07B.tsv"


def lies_manifest() -> dict[tuple[int, int], ManifestZeile]:
    pfad = manifest_pfad()
    ergebnis: dict[tuple[int, int], ManifestZeile] = {}
    if not pfad.exists():
        return ergebnis
    spaltennamen = [f.name for f in fields(ManifestZeile)]
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if zeile.startswith("#") or not zeile.strip() or zeile.startswith("monat\t"):
            continue
        teile = zeile.split("\t")
        if len(teile) != len(spaltennamen):
            continue
        eintrag = ManifestZeile(*teile)
        jahr, monat = (int(t) for t in eintrag.monat.split("-"))
        ergebnis[(jahr, monat)] = eintrag
    return ergebnis


def schreibe_manifest(zeilen: dict[tuple[int, int], ManifestZeile]) -> Path:
    """Schreibt das VOLLSTÄNDIGE Manifest (alle 156 Monate 2013-01..2025-12) atomar.

    Monate, die `zeilen` nicht enthält, werden als "nicht geladen" (Grund:
    "noch nicht verarbeitet") ergänzt - ein nicht geladener Zeitraum darf nie
    wie "keine Daten" aussehen UND nie einfach fehlen (CLAUDE.md). Atomar:
    zuerst eine .tmp-Datei, dann `os.replace` (Hilfsdatei + Umbenennen), damit
    ein Absturz mitten im Schreiben kein kaputtes Manifest hinterlässt.
    """
    pfad = manifest_pfad()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    vollstaendig = dict(zeilen)
    start_text = f"{ZEITACHSE_START[0]:04d}-{ZEITACHSE_START[1]:02d}"
    ende_text = f"{ZEITACHSE_ENDE[0]:04d}-{ZEITACHSE_ENDE[1]:02d}"
    for jahr, monat in _monatsliste(start_text, ende_text):
        vollstaendig.setdefault(
            (jahr, monat),
            ManifestZeile(f"{jahr:04d}-{monat:02d}", ZUSTAND_NICHT_GELADEN, grund="noch nicht verarbeitet"),
        )
    zaehler = {z: 0 for z in (ZUSTAND_GELADEN, ZUSTAND_NICHT_VORHANDEN, ZUSTAND_NICHT_GELADEN)}
    for eintrag in vollstaendig.values():
        zaehler[eintrag.zustand] = zaehler.get(eintrag.zustand, 0) + 1
    kopf = [
        f"# {KURZNAME} Version {DATEI_VERSION_TEXT}, DOI 10.5067/GPM/IMERG/3B-MONTH/07, "
        f"Katalog-Trefferzahl insgesamt erwartet: 153 (2013-01..2025-09) + 3 bekannte Lücken "
        f"(2025-10..12); " + ", ".join(f"{z}: {n}" for z, n in zaehler.items()),
        "# Katalog liefert keine Prüfsumme; sha256 ist selbst berechnet (docs/sources/imerg.md Abschnitt 1).",
    ]
    zeilen_text = ["\t".join(MANIFEST_SPALTEN)]
    for (jahr, monat), eintrag in sorted(vollstaendig.items()):
        zeilen_text.append("\t".join(str(getattr(eintrag, s)) for s in MANIFEST_SPALTEN))
    hilfspfad = pfad.with_suffix(".tsv.tmp")
    hilfspfad.write_text("\n".join(kopf + zeilen_text) + "\n", encoding="utf-8")
    os.replace(hilfspfad, pfad)
    return pfad


# --- Protokoll -------------------------------------------------------------------
def _protokoll_pfad() -> Path:
    return io.aleph_data_dir() / "protokoll" / "imerg_lauf.log"


def _protokoll_melder():
    def melde(text: str) -> None:
        pfad = _protokoll_pfad()
        pfad.parent.mkdir(parents=True, exist_ok=True)
        zeile = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} {text}\n"
        with open(pfad, "a", encoding="utf-8") as datei:
            datei.write(zeile)

    return melde


# --- Architektur-Vertrag (ARCHITECTURE.md Abschnitt 5) --------------------------
def _monatsliste(start: str, ende: str) -> list[tuple[int, int]]:
    jahr, monat = (int(t) for t in start.split("-"))
    end_jahr, end_monat = (int(t) for t in ende.split("-"))
    monate = []
    while (jahr, monat) <= (end_jahr, end_monat):
        monate.append((jahr, monat))
        monat += 1
        if monat > 12:
            monat, jahr = 1, jahr + 1
    return monate


def download(start: str, ende: str, gleichzeitige_downloads: int = GLEICHZEITIGE_DOWNLOADS) -> list[Path]:
    """Lädt Rohdateien für [start, ende] ('JJJJ-MM') nach raw/imerg/V07B/<Jahr>/.

    Fragt für jeden Monat zuerst den Katalog ab (Zeitlimit + Wiederholung,
    `_katalog_abfrage`); Monate in BEIM_ANBIETER_NICHT_VORHANDEN werden ohne
    Downloadversuch im Manifest vermerkt. Lädt danach die übrigen Monate mit
    höchstens `gleichzeitige_downloads` gleichzeitigen Downloads (Standard
    GLEICHZEITIGE_DOWNLOADS = 2, Begründung bei der Konstante).
    """
    melde = _protokoll_melder()
    anmelden(melde)
    manifest = lies_manifest()
    jetzt = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
    zu_laden: list[tuple[int, int, object, MonatsSoll]] = []
    for jahr, monat in _monatsliste(start, ende):
        monatstext = f"{jahr:04d}-{monat:02d}"
        gemeldet, granules = _katalog_abfrage(jahr, monat, melde=melde)
        zustand, soll, grund = _einordnen_katalog(jahr, monat, gemeldet, granules)
        if zustand == ZUSTAND_NICHT_VORHANDEN:
            manifest[(jahr, monat)] = ManifestZeile(
                monatstext, ZUSTAND_NICHT_VORHANDEN, abrufdatum_utc=jetzt, grund=grund
            )
        else:
            zu_laden.append((jahr, monat, granules[0], soll))

    pfade: list[Path] = []
    io.pruefe_speicher()
    with concurrent.futures.ThreadPoolExecutor(max_workers=gleichzeitige_downloads) as pool:
        futures = {
            pool.submit(
                hole_monatsdatei,
                jahr,
                monat,
                soll,
                granule,
                io.rohdaten_pfad("imerg", DATEI_VERSION_TEXT, f"{jahr:04d}"),
                melde,
            ): (jahr, monat, soll)
            for jahr, monat, granule, soll in zu_laden
        }
        for future in concurrent.futures.as_completed(futures):
            jahr, monat, soll = futures[future]
            monatstext = f"{jahr:04d}-{monat:02d}"
            try:
                pfad = future.result()
            except (io.SSDNichtGefunden, io.SpeicherZuKnapp, AnmeldungFehlgeschlagen, EarthdataZugangVerweigert):
                raise
            except Exception as fehler:
                melde(f"{monatstext}: nicht geladen ({type(fehler).__name__}: {fehler})")
                manifest[(jahr, monat)] = ManifestZeile(
                    monatstext,
                    ZUSTAND_NICHT_GELADEN,
                    datei=soll.datei,
                    groesse_bytes=str(soll.groesse),
                    abrufdatum_utc=jetzt,
                    katalog_erzeugt=soll.erzeugt or "-",
                    grund=str(fehler)[:300],
                )
                continue
            pfade.append(pfad)
            manifest[(jahr, monat)] = ManifestZeile(
                monatstext,
                ZUSTAND_GELADEN,
                datei=pfad.name,
                groesse_bytes=str(soll.groesse),
                groesse_bytes_gemessen=str(pfad.stat().st_size),
                sha256=_sha256(pfad),
                abrufdatum_utc=jetzt,
                katalog_erzeugt=soll.erzeugt or "-",
                herkunftseinheit=FELD_EINHEITEN["precipitation"],
                grund="",
            )
    schreibe_manifest(manifest)
    return pfade


def to_cube() -> list[tuple[int, int]]:
    """Verarbeitet alle vorhandenen, geprüften Rohdateien unter raw/imerg/V07B/ in den Würfel.

    Setzt außerdem monat_fertig=5 für die Monate in
    BEIM_ANBIETER_NICHT_VORHANDEN, sofern sie im Würfel noch leer sind. Ein
    schon fertiger Monat (Zustand 1) wird nicht neu verarbeitet.
    """
    melde = _protokoll_melder()
    basis = io.rohdaten_pfad("imerg", DATEI_VERSION_TEXT)
    verarbeitet: list[tuple[int, int]] = []
    manifest = lies_manifest()
    jetzt = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
    if basis.exists():
        for jahrordner in sorted(p for p in basis.iterdir() if p.is_dir()):
            for datei in sorted(jahrordner.glob("3B-MO.*.HDF5")):
                treffer = _DATEINAME_MUSTER.match(datei.name)
                if not treffer:
                    continue
                jahr, monat = int(treffer.group(1)), int(treffer.group(2))
                if monatsstatus(jahr, monat) == MONAT_FERTIG:
                    continue
                try:
                    datensatz = _verarbeite_monat(datei, jahr, monat)
                    schreibe_in_wuerfel(datensatz)
                except Exception as fehler:
                    melde(f"{jahr:04d}-{monat:02d}: Verarbeitung fehlgeschlagen ({type(fehler).__name__}: {fehler})")
                    raise
                verarbeitet.append((jahr, monat))
    for jahr, monat in sorted(BEIM_ANBIETER_NICHT_VORHANDEN):
        if monatsstatus(jahr, monat) == MONAT_LEER:
            setze_nicht_vorhanden(jahr, monat)
            manifest.setdefault(
                (jahr, monat),
                ManifestZeile(
                    f"{jahr:04d}-{monat:02d}",
                    ZUSTAND_NICHT_VORHANDEN,
                    abrufdatum_utc=jetzt,
                    grund="V07 Final endet 2025-09 (NASA-Mitteilung IMERG V08 Transition Schedule).",
                ),
            )
    schreibe_manifest(manifest)
    return verarbeitet


# --- Kommandozeile ---------------------------------------------------------------
def _pruefe_katalog_nur(start: str, ende: str, melde) -> int:
    fehlerzahl = 0
    for jahr, monat in _monatsliste(start, ende):
        monatstext = f"{jahr:04d}-{monat:02d}"
        try:
            gemeldet, granules = _katalog_abfrage(jahr, monat, melde=melde)
            zustand, soll, grund = _einordnen_katalog(jahr, monat, gemeldet, granules)
            if soll is not None:
                print(f"{monatstext}: im Katalog vorhanden ({soll.datei}, {soll.groesse} Bytes)")
            else:
                print(f"{monatstext}: {zustand} ({grund})")
        except Exception as fehler:
            fehlerzahl += 1
            print(f"{monatstext}: FEHLER {type(fehler).__name__}: {fehler}")
            melde(f"{monatstext}: Katalogprüfung fehlgeschlagen: {type(fehler).__name__}: {fehler}")
    print(f"Geprüft: {len(_monatsliste(start, ende))} Monate, {fehlerzahl} Fehler.")
    return 1 if fehlerzahl else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Lädt und verarbeitet GPM IMERG V07B (monatlich).")
    parser.add_argument("--start", help="JJJJ-MM")
    parser.add_argument("--ende", help="JJJJ-MM")
    parser.add_argument(
        "--nur-katalog", action="store_true", help="Prüft nur den Katalog gegen die Referenz, kein Download."
    )
    args = parser.parse_args(argv)
    melde = _protokoll_melder()

    start = args.start or f"{ZEITACHSE_START[0]:04d}-{ZEITACHSE_START[1]:02d}"
    ende = args.ende or f"{ZEITACHSE_ENDE[0]:04d}-{ZEITACHSE_ENDE[1]:02d}"

    if args.nur_katalog:
        return _pruefe_katalog_nur(start, ende, melde)

    if not args.start or not args.ende:
        parser.error("--start und --ende sind erforderlich (außer bei --nur-katalog).")
    download(args.start, args.ende)
    to_cube()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
