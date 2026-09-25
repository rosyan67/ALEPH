"""Gemeinsamer Lade- und Speicherweg für alle Layer.

Alle Rohdaten und Datenwürfel liegen auf der externen SSD, deren Pfad in
`.env` unter ALEPH_DATA_DIR steht (Vorlage ohne Wert in `.env.example`).
Dieses Modul bündelt:
- den Zugriff auf diesen Pfad (`aleph_data_dir`, `rohdaten_pfad`, `wuerfel_pfad`),
- den Speicherwächter (`pruefe_speicher`), den jeder Ladelauf vor jedem
  Monat aufruft und der stoppt, bevor die SSD voll läuft.

Ist die SSD nicht angeschlossen oder ALEPH_DATA_DIR nicht gesetzt, bricht
`aleph_data_dir()` mit einer klaren Meldung ab, statt irgendwo lokal zu
schreiben.
"""

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

ENV_DATEI = Path(__file__).resolve().parents[2] / ".env"

MIN_FREI_GB = 50  # Stopp, wenn weniger frei ist (1 GB = 1024³ Byte, wie im Finder/df)


class SpeicherZuKnapp(RuntimeError):
    """Zu wenig freier Speicherplatz: der Ladelauf wird gestoppt."""


class SSDNichtGefunden(RuntimeError):
    """ALEPH_DATA_DIR ist nicht gesetzt oder die SSD ist nicht angeschlossen."""


def aleph_data_dir() -> Path:
    """Pfad zu den ALEPH-Daten auf der externen SSD.

    Liest ALEPH_DATA_DIR aus `.env`. Bricht mit `SSDNichtGefunden` ab, wenn
    die Variable fehlt oder der Ordner gerade nicht erreichbar ist (SSD
    nicht angeschlossen oder nicht eingehängt).
    """
    load_dotenv(ENV_DATEI)
    wert = os.environ.get("ALEPH_DATA_DIR")
    if not wert:
        raise SSDNichtGefunden(
            "ALEPH_DATA_DIR ist nicht gesetzt. In .env den Pfad zur "
            "externen SSD eintragen (z. B. /Volumes/<Name>/ALEPH-data)."
        )
    pfad = Path(wert)
    if not pfad.is_dir():
        raise SSDNichtGefunden(
            f"SSD nicht gefunden: {pfad} ist nicht erreichbar. Ist die "
            "externe SSD angeschlossen und eingehängt?"
        )
    return pfad


def rohdaten_pfad(*teile: str) -> Path:
    """Pfad unterhalb von raw/ auf der SSD, z. B. rohdaten_pfad('vnp46a3')."""
    return aleph_data_dir().joinpath("raw", *teile)


def wuerfel_pfad(*teile: str) -> Path:
    """Pfad unterhalb von cube/ auf der SSD, z. B. wuerfel_pfad('vnp46a3.zarr')."""
    return aleph_data_dir().joinpath("cube", *teile)


def freier_speicher_gb(pfad) -> float:
    """Freier Speicherplatz auf dem Datenträger, auf dem `pfad` liegt, in GB."""
    return shutil.disk_usage(pfad).free / 1024**3


def pruefe_speicher(pfad=None, minimum_gb=MIN_FREI_GB) -> None:
    """Stoppt mit `SpeicherZuKnapp`, wenn weniger als `minimum_gb` frei sind.

    Ohne Angabe von `pfad` wird der Platz auf der ALEPH-SSD geprüft
    (`aleph_data_dir()`) - das bricht bereits vorher mit `SSDNichtGefunden`
    ab, wenn die SSD fehlt.
    """
    if pfad is None:
        pfad = aleph_data_dir()
    frei = freier_speicher_gb(pfad)
    if frei < minimum_gb:
        raise SpeicherZuKnapp(
            f"Nur noch {frei:.1f} GB frei auf {pfad}, Untergrenze ist "
            f"{minimum_gb} GB. Lauf gestoppt. Bereits fertig verarbeitete "
            "Monate bleiben erhalten."
        )
