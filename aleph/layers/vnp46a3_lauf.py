"""Hintergrund-Lauf: lädt VNP46A3 monatsweise, verkleinert sofort auf das
0,25°-Raster, schreibt in den Würfel auf der SSD und löscht die Originale.

Aufruf (normalerweise über scripts/vnp46a3_start.sh, nicht direkt):
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2013-01 --ende 2025-12
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2024-01 --ende 2024-01 --gleichzeitig 2
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2013-01 --ende 2025-12 --zuerst-ab 2018-01

Eigenschaften:
- setzt nach einem Abbruch beim letzten fertigen Monat wieder an
  (aleph.layers.vnp46a3.vorhandene_monate prüft den Würfel auf der SSD),
- arbeitet die Monate auf Wunsch nicht der Reihe nach ab: mit
  `--zuerst-ab 2018-01` kommen zuerst alle Monate ab 2018-01 (zeitlich
  aufsteigend), danach die früheren (ebenfalls aufsteigend). Sinn: bricht der
  Lauf ab oder greift die NASA-Frist (1.11.2026) früher, liegen bereits die
  jüngeren Jahre vollständig vor. Die Reihenfolge des Ladens hat keinen
  Einfluss auf die Ablage: jeder Monat wird an seine Position auf der festen
  Zeitachse des Würfels geschrieben,
- schreibt für jeden Monat echte Zeitstempel (Start, Ende) und die gemessene
  Dauer je Phase (Download, Verkleinern und Schreiben) ins Protokoll,
- prüft vor jedem Monat den freien Platz auf der SSD (Speicherwächter,
  Stopp unter 50 GB frei) und bricht klar ab, wenn die SSD fehlt,
- lädt Kacheln einzeln, höchstens `--gleichzeitig` auf einmal (Vorschlag
  2-4, Standard aleph.layers.vnp46a3.GLEICHZEITIGE_DOWNLOADS_STANDARD;
  vermutete Ursache früherer Hänger war zu viel Nebenläufigkeit zum
  selben NASA/CloudFront-Server - bei erneuten Hängern hier eine kleinere
  Zahl eintragen statt zu raten), mit eigenem Zeitlimit je Kachel
  (DATEI_TIMEOUT_SEKUNDEN) und automatischer Wiederholung mit wachsender
  Wartezeit (aleph.layers.vnp46a3._lade_kachel),
- prüft nach dem Laden, ob der Monat vollständig ist (Soll-Ist-Vergleich
  gegen die Zahl der bei NASA gemeldeten Kacheln, nicht gegen eine feste
  Zahl), bevor er verarbeitet wird,
- schreibt ein Protokoll und ein Manifest der Quelldateien auf die SSD
  (protokoll/vnp46a3.log, protokoll/manifeste/vnp46a3/<Monat>.txt),
- prüft nach dem Schreiben, dass der Monat tatsächlich im Würfel steht,
  bevor die Rohdaten gelöscht werden,
- bricht den GANZEN Monat nach vnp46a3.DOWNLOAD_TIMEOUT_SEKUNDEN ohne
  vollständige Antwort ab (Sicherheitsnetz über der Kachel-Wiederholung)
  und beendet sich danach mit `os._exit`, damit hängende Hintergrund-Threads
  den Prozess nicht am wirklichen Beenden hindern.

Das Wachhalten des Macs (caffeinate) und das Weiterlaufen nach Schließen
des Terminals (nohup) übernimmt scripts/vnp46a3_start.sh, nicht dieses
Modul.
"""

import argparse
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone

from aleph.core import io
from aleph.layers import vnp46a3


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


def _monat_argument(text: str) -> str:
    """Streng JJJJ-MM (argparse-Typ); alles andere ist ein klarer Fehler statt stiller Fehlfunktion."""
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", text):
        raise argparse.ArgumentTypeError(f"'{text}' ist kein Monat im Format JJJJ-MM.")
    return text


def _reihenfolge(monate: list[tuple[int, int]], zuerst_ab: str | None) -> list[tuple[int, int]]:
    """Ordnet die Monate: erst alle ab `zuerst_ab` (aufsteigend), dann die früheren (aufsteigend).

    Ohne `zuerst_ab` bleibt es bei der zeitlichen Reihenfolge.
    """
    if zuerst_ab is None:
        return sorted(monate)
    grenze = tuple(int(t) for t in zuerst_ab.split("-"))
    return sorted(m for m in monate if m >= grenze) + sorted(m for m in monate if m < grenze)


class Protokoll:
    """Schreibt Zeilen mit Zeitstempel auf die SSD, sofort sichtbar (kein Puffer)."""

    def __init__(self, pfad):
        self.pfad = pfad
        self.pfad.parent.mkdir(parents=True, exist_ok=True)

    def schreibe(self, zeile: str) -> None:
        zeitstempel = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(self.pfad, "a", encoding="utf-8") as datei:
            datei.write(f"{zeitstempel}  {zeile}\n")
        print(zeile, flush=True)


def _stempel(zeitpunkt: datetime) -> str:
    return zeitpunkt.strftime("%Y-%m-%d %H:%M:%S UTC")


def verarbeite_monat(jahr: int, monat: int, protokoll: Protokoll, gleichzeitige_downloads: int) -> None:
    name = f"{jahr:04d}-{monat:02d}"
    raw_ordner = io.rohdaten_pfad("vnp46a3", name)
    if raw_ordner.exists():
        protokoll.schreibe(
            f"{name}: unvollständiger Rohdaten-Ordner von einem "
            "früheren Abbruch gefunden, wird gelöscht und neu geladen."
        )
        shutil.rmtree(raw_ordner)

    # Echte Uhrzeiten (Wanduhr, UTC) für Start und Ende; Dauern mit der
    # monotonen Uhr gemessen, damit eine Uhrumstellung sie nicht verfälscht.
    start_wand = datetime.now(timezone.utc)
    t0 = time.monotonic()
    protokoll.schreibe(f"{name}: Start {_stempel(start_wand)}.")

    # lade_monat prüft selbst die Vollständigkeit (Soll-Ist-Vergleich gegen
    # die NASA-Abfrage) und bricht mit MonatUnvollstaendig ab, BEVOR etwas
    # geschrieben oder gelöscht wird - die Rohdaten bleiben dann zur Prüfung
    # liegen.
    dateien = vnp46a3.lade_monat(
        jahr,
        monat,
        raw_ordner,
        gleichzeitige_downloads=gleichzeitige_downloads,
        melde=lambda text: protokoll.schreibe(f"{name}: {text}"),
    )
    t_download = time.monotonic()
    protokoll.schreibe(f"{name}: Download fertig nach {(t_download - t0) / 60:.1f} Minuten.")

    monatsdaten = vnp46a3.verkleinere_monat(dateien, erwarteter_monat=(jahr, monat))
    # schreibe_in_wuerfel legt den Monat an seine Position auf der festen
    # Zeitachse, liest ihn zurück, vergleicht und setzt erst dann die
    # Fertig-Markierung.
    vnp46a3.schreibe_in_wuerfel(monatsdaten)

    # Zusätzliche Kontrolle vor dem Löschen der Rohdaten: der Monat muss
    # als fertig markiert lesbar sein.
    if (jahr, monat) not in vnp46a3.vorhandene_monate():
        raise RuntimeError(
            f"{name}: nach dem Schreiben nicht als fertig im Würfel "
            "gefunden. Rohdaten bleiben erhalten, nichts wurde gelöscht."
        )
    t_wuerfel = time.monotonic()

    manifest_pfad = vnp46a3.schreibe_manifest(jahr, monat, dateien)
    shutil.rmtree(raw_ordner)

    ende_wand = datetime.now(timezone.utc)
    gesamt = (time.monotonic() - t0) / 60
    protokoll.schreibe(
        f"{name}: fertig, {len(dateien)} Kacheln, Start {_stempel(start_wand)}, "
        f"Ende {_stempel(ende_wand)}, Dauer gesamt {gesamt:.1f} Minuten "
        f"(Download {(t_download - t0) / 60:.1f}, Verkleinern und Schreiben "
        f"{(t_wuerfel - t_download) / 60:.1f}), Manifest {manifest_pfad.name}."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=_monat_argument, help="erster Monat, Format JJJJ-MM")
    parser.add_argument(
        "--ende", required=True, type=_monat_argument, help="letzter Monat, Format JJJJ-MM (eingeschlossen)"
    )
    parser.add_argument(
        "--zuerst-ab",
        default=None,
        type=_monat_argument,
        help=(
            "Monat JJJJ-MM: erst alle Monate ab hier (aufsteigend), dann die früheren "
            "(aufsteigend). Ohne Angabe: zeitliche Reihenfolge."
        ),
    )
    parser.add_argument(
        "--gleichzeitig",
        type=int,
        default=vnp46a3.GLEICHZEITIGE_DOWNLOADS_STANDARD,
        help=(
            "Zahl gleichzeitiger Kachel-Downloads (Vorschlag 2-4, Standard "
            f"{vnp46a3.GLEICHZEITIGE_DOWNLOADS_STANDARD}). Bei erneuten "
            "Hängern hier eine kleinere Zahl eintragen statt zu raten."
        ),
    )
    args = parser.parse_args()

    protokoll_pfad = None
    try:
        protokoll_pfad = io.aleph_data_dir() / "protokoll" / "vnp46a3.log"
    except io.SSDNichtGefunden as fehler:
        print(f"ABBRUCH: {fehler}", file=sys.stderr)
        return 1
    protokoll = Protokoll(protokoll_pfad)

    alle_monate = _monatsliste(args.start, args.ende)
    try:
        for jahr, monat in (alle_monate[0], alle_monate[-1]) if alle_monate else ():
            vnp46a3._monat_index(jahr, monat)  # bricht ab, wenn außerhalb der Zeitachse
    except vnp46a3.MonatAusserhalbZeitachse as fehler:
        protokoll.schreibe(f"ABBRUCH vor Start: {fehler} Kein Download gestartet.")
        return 1
    try:
        fertige_monate = vnp46a3.vorhandene_monate()
    except vnp46a3.WuerfelFormat as fehler:
        protokoll.schreibe(f"ABBRUCH vor Start: {fehler}")
        return 1
    offene_monate = _reihenfolge([m for m in alle_monate if m not in fertige_monate], args.zuerst_ab)

    reihenfolge_text = (
        f", Reihenfolge: zuerst ab {args.zuerst_ab}, dann davor" if args.zuerst_ab else ", zeitliche Reihenfolge"
    )
    protokoll.schreibe(
        f"Lauf gestartet: {args.start} bis {args.ende}, gleichzeitig={args.gleichzeitig}"
        f"{reihenfolge_text}, "
        f"{len(fertige_monate & set(alle_monate))} von {len(alle_monate)} Monaten bereits fertig, "
        f"{len(offene_monate)} offen"
        + (f", erster Monat {offene_monate[0][0]:04d}-{offene_monate[0][1]:02d}." if offene_monate else ".")
    )

    for jahr, monat in offene_monate:
        try:
            io.pruefe_speicher()
        except (io.SSDNichtGefunden, io.SpeicherZuKnapp) as fehler:
            protokoll.schreibe(f"ABBRUCH vor {jahr:04d}-{monat:02d}: {fehler}")
            return 1

        try:
            verarbeite_monat(jahr, monat, protokoll, args.gleichzeitig)
        except Exception as fehler:  # bewusst breit: jeder Fehler soll klar im Protokoll stehen
            protokoll.schreibe(
                f"FEHLER bei {jahr:04d}-{monat:02d}: {fehler}\n{traceback.format_exc()}"
            )
            return 1

    protokoll.schreibe("Lauf fertig: alle angefragten Monate stehen im Würfel.")
    return 0


if __name__ == "__main__":
    _rueckgabewert = main()
    sys.stdout.flush()
    sys.stderr.flush()
    # os._exit statt sys.exit: nach einem DownloadHaengt-Abbruch könnten
    # hängende Netzwerk-Threads (nicht Daemon-Threads) sonst den normalen
    # Interpreter-Shutdown unbegrenzt aufhalten.
    os._exit(_rueckgabewert)
