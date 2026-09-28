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
- Netzwerkregel (CLAUDE.md, 2026-09-28): Der Start hat ein Zeitlimit und wird
  bei Netzproblemen mit wachsenden Pausen wiederholt; danach hat jede Anfrage
  ein Standard-Zeitlimit (die Bibliothek wartet sonst unbegrenzt,
  `deadline_ms = 0`). Jede Wiederholung wird auf stderr gemeldet.

Aufruf zum Testen (im Projektordner):
    .venv/bin/python -m aleph.core.earth_engine
"""

import concurrent.futures
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ENV_DATEI = Path(__file__).resolve().parents[2] / ".env"
PROJEKT_VARIABLE = "EE_PROJECT"

# Zeitlimit für den Start (`ee.Initialize`). Der Start holt die Liste der
# Serverfunktionen, gemessen am 27.09. etwa 5 s. Die Bibliothek setzt dafür
# kein Zeitlimit. 120 s lassen einer langsamen, mit dem NASA-Download geteilten
# Leitung reichlich Luft (gleicher Wert wie das Login-Zeitlimit in auth.py).
# Ein hängender Versuch wird aufgegeben; sein Hilfsfaden läuft im Hintergrund aus.
START_ZEITLIMIT_SEKUNDEN = 120

# Pausen zwischen Startversuchen bei Netzproblemen (Zeitüberschreitung,
# Verbindung): 10, 30, 60 s, also 4 Versuche in höchstens etwa 10 Minuten.
# Eine kurze Störung ist damit überbrückt; eine längere soll klar abbrechen,
# denn Earth Engine ist hier nur ein Prüfwerkzeug, kein Dauerlauf.
START_PAUSEN_SEKUNDEN = (10, 30, 60)

# Standard-Zeitlimit je Anfrage nach dem Start (z. B. `getInfo`). Kleine
# Anfragen brauchen Sekunden. Wer mehr braucht, setzt selbst ein größeres
# Limit (ee_nachtlicht: ANFRAGE_ZEITLIMIT_SEKUNDEN = 600 für große Blöcke).
ANFRAGE_ZEITLIMIT_STANDARD_SEKUNDEN = 300

# Die Bibliothek wiederholt Anfragen mit HTTP 429 und 5xx selbst, mit
# zufälligen, sich verdoppelnden Pausen (googleapiclient: bis 2^n s). Standard
# der Bibliothek ist 5; hier ausdrücklich gesetzt, damit der Wert sichtbar ist.
BIBLIOTHEK_WIEDERHOLUNGEN = 5

# Fehlerarten, bei denen ein neuer Versuch sinnvoll ist (Netz, Zeitlimit).
# Alles andere (nicht angemeldet, Projekt falsch, Rechte fehlen) wird durch
# Wiederholen nicht besser und bricht sofort ab.
_VORUEBERGEHEND = {
    "TimeoutError",
    "ConnectionError",
    "ConnectTimeout",
    "ReadTimeout",
    "Timeout",
    "TransportError",  # google-auth: Netzfehler beim Erneuern des Tokens
}


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


def _starte_einmal(ee, name: str, zeitlimit_sekunden: float) -> str | None:
    """Ein Startversuch mit Zeitlimit. Rückgabe: None bei Erfolg, sonst die Fehlerart."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(ee.Initialize, project=name)
        try:
            future.result(timeout=zeitlimit_sekunden)
        except concurrent.futures.TimeoutError:
            return "TimeoutError"
        except Exception as fehler:  # noqa: BLE001 - jede Art wird eingeordnet, Text verworfen
            return type(fehler).__name__
        return None
    finally:
        pool.shutdown(wait=False)


def starte(
    zeitlimit_sekunden: float = START_ZEITLIMIT_SEKUNDEN,
    pausen_sekunden=START_PAUSEN_SEKUNDEN,
    schlafe=time.sleep,
):
    """Startet Earth Engine mit dem Projekt aus .env und gibt das Modul `ee` zurück.

    Fehler der Bibliothek werden durch eine eigene Meldung ersetzt (nur die
    Fehlerart), damit weder Projekt-ID noch Token-Teile in Ausgaben landen.
    """
    import ee

    name = projekt()
    versuche = len(pausen_sekunden) + 1
    fehler_art = None
    for versuch in range(1, versuche + 1):
        fehler_art = _starte_einmal(ee, name, zeitlimit_sekunden)
        if fehler_art is None or fehler_art not in _VORUEBERGEHEND or versuch == versuche:
            break
        pause = pausen_sekunden[versuch - 1]
        print(
            f"Earth Engine: Startversuch {versuch}/{versuche} gescheitert ({fehler_art}), "
            f"neuer Versuch in {pause} s",
            file=sys.stderr,
            flush=True,
        )
        schlafe(pause)
    if fehler_art is not None:
        raise EarthEngineNichtBereit(
            f"Earth Engine konnte nicht starten ({fehler_art}). Mögliche Gründe: Netz oder Server "
            "nicht erreichbar, nicht angemeldet (`earthengine authenticate`), Projekt nicht für "
            f"Earth Engine registriert, falsche Projekt-ID in {PROJEKT_VARIABLE}."
        )
    ee.data.setMaxRetries(BIBLIOTHEK_WIEDERHOLUNGEN)
    ee.data.setDeadline(ANFRAGE_ZEITLIMIT_STANDARD_SEKUNDEN * 1000)
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
