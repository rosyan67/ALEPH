"""Verbindung zu Google Earth Engine (Machbarkeitsprüfung 2026-09-27).

Earth Engine ist noch KEINE Datenquelle von ALEPH, sondern wird nur geprüft
(berichte/2026-09-27_earth-engine-pruefung.md). Dieses Modul bündelt die
Anmeldung, damit jede Prüfung denselben Weg nutzt:

- Die Zugangsdaten (OAuth-Token) legt `earthengine authenticate` außerhalb des
  Repos ab (`~/.config/earthengine/credentials`); dieses Modul liest sie nicht
  selbst, sondern überlässt das der Bibliothek.
- Das Google-Cloud-Projekt steht in `.env` unter `EE_PROJECT` und wird nur
  zur Laufzeit geladen (wie `ALEPH_DATA_DIR` in `aleph/core/io.py`). Der Wert
  wird nie ausgegeben, auch nicht in Fehlermeldungen: Nach außen gehen nur
  die Fehlerart (Klassenname) und ein eigener Hinweistext.

Aufruf zum Testen (im Projektordner):
    .venv/bin/python -m aleph.core.earth_engine
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_DATEI = Path(__file__).resolve().parents[2] / ".env"
PROJEKT_VARIABLE = "EE_PROJECT"


class EarthEngineNichtBereit(RuntimeError):
    """Earth Engine lässt sich nicht starten (Projekt fehlt, nicht angemeldet, abgelehnt)."""


def projekt() -> str:
    """Cloud-Projekt aus .env; bricht mit klarer Meldung ab, wenn es fehlt."""
    load_dotenv(ENV_DATEI)
    wert = os.environ.get(PROJEKT_VARIABLE, "").strip()
    if not wert:
        raise EarthEngineNichtBereit(
            f"{PROJEKT_VARIABLE} ist in .env nicht gesetzt. Die Projekt-ID des für Earth Engine "
            "registrierten Google-Cloud-Projekts dort eintragen."
        )
    return wert


def starte():
    """Startet Earth Engine mit dem Projekt aus .env und gibt das Modul `ee` zurück.

    Fehler der Bibliothek werden durch eine eigene Meldung ersetzt (nur die
    Fehlerart), damit weder Projekt-ID noch Token-Teile in Ausgaben landen.
    """
    import ee

    name = projekt()
    fehler_art = None
    try:
        ee.Initialize(project=name)
    except Exception as fehler:  # noqa: BLE001 - jede Art wird eingeordnet, Text verworfen
        fehler_art = type(fehler).__name__
    if fehler_art is not None:
        # Außerhalb des except ausgelöst, damit __context__ leer bleibt.
        raise EarthEngineNichtBereit(
            f"Earth Engine konnte nicht starten ({fehler_art}). Mögliche Gründe: nicht angemeldet "
            "(`earthengine authenticate`), Projekt nicht für Earth Engine registriert, "
            f"falsche Projekt-ID in {PROJEKT_VARIABLE}."
        )
    return ee


def main() -> int:
    ee = starte()
    # Mini-Test: eine Rechnung auf dem Server und ein Katalogzugriff.
    summe = ee.Number(1).add(1).getInfo()
    anzahl = (
        ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG")
        .filterDate("2018-10-01", "2018-11-01")
        .size()
        .getInfo()
    )
    print(f"Earth Engine verbunden. Test 1+1 = {summe}; VCMCFG-Bilder für 2018-10: {anzahl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
