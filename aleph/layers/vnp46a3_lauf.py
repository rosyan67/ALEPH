"""Hintergrund-Lauf: lädt VNP46A3 monatsweise, verkleinert sofort auf das
0,25°-Raster, schreibt in den Würfel auf der SSD und löscht die Originale.

Aufruf (normalerweise über scripts/vnp46a3_start.sh, nicht direkt):
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2013-01 --ende 2025-12

Eigenschaften:
- setzt nach einem Abbruch beim letzten fertigen Monat wieder an
  (aleph.layers.vnp46a3.vorhandene_monate prüft den Würfel auf der SSD),
- prüft vor jedem Monat den freien Platz auf der SSD (Speicherwächter,
  Stopp unter 50 GB frei) und bricht klar ab, wenn die SSD fehlt,
- prüft nach dem Laden, ob der Monat vollständig ist (Soll-Ist-Vergleich
  gegen die Zahl der bei NASA gemeldeten Kacheln, nicht gegen eine feste
  Zahl), bevor er verarbeitet wird,
- schreibt ein Protokoll und ein Manifest der Quelldateien auf die SSD
  (protokoll/vnp46a3.log, protokoll/manifeste/vnp46a3/<Monat>.txt),
- prüft nach dem Schreiben, dass der Monat tatsächlich im Würfel steht,
  bevor die Rohdaten gelöscht werden,
- bricht einen Download nach vnp46a3.DOWNLOAD_TIMEOUT_SEKUNDEN ohne Antwort
  ab (beobachtet 2026-09-22: eine hängengebliebene Netzwerkverbindung ließ
  den Prozess sonst unbegrenzt und ohne Fehlermeldung weiterlaufen) und
  beendet sich danach mit `os._exit`, damit hängende Hintergrund-Threads
  den Prozess nicht am wirklichen Beenden hindern.

Das Wachhalten des Macs (caffeinate) und das Weiterlaufen nach Schließen
des Terminals (nohup) übernimmt scripts/vnp46a3_start.sh, nicht dieses
Modul.
"""

import argparse
import os
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


def verarbeite_monat(jahr: int, monat: int, protokoll: Protokoll) -> None:
    raw_ordner = io.rohdaten_pfad("vnp46a3", f"{jahr:04d}-{monat:02d}")
    if raw_ordner.exists():
        protokoll.schreibe(
            f"{jahr:04d}-{monat:02d}: unvollständiger Rohdaten-Ordner von einem "
            "früheren Abbruch gefunden, wird gelöscht und neu geladen."
        )
        shutil.rmtree(raw_ordner)

    start_zeit = time.time()
    # lade_monat prüft selbst die Vollständigkeit (Soll-Ist-Vergleich gegen
    # die NASA-Abfrage) und bricht mit MonatUnvollstaendig ab, BEVOR etwas
    # geschrieben oder gelöscht wird - die Rohdaten bleiben dann zur Prüfung
    # liegen.
    dateien = vnp46a3.lade_monat(jahr, monat, raw_ordner)

    monatsdaten = vnp46a3.verkleinere_monat(dateien)
    vnp46a3.schreibe_in_wuerfel(monatsdaten)

    # Erst jetzt prüfen, ob der Monat wirklich lesbar im Würfel steht -
    # sonst könnte ein Absturz mitten im Zarr-Schreiben unbemerkt bleiben
    # und die Rohdaten wären schon weg.
    if (jahr, monat) not in vnp46a3.vorhandene_monate():
        raise RuntimeError(
            f"{jahr:04d}-{monat:02d}: nach dem Schreiben nicht im Würfel "
            "gefunden. Rohdaten bleiben erhalten, nichts wurde gelöscht."
        )

    manifest_pfad = vnp46a3.schreibe_manifest(jahr, monat, dateien)
    shutil.rmtree(raw_ordner)

    dauer_minuten = (time.time() - start_zeit) / 60
    protokoll.schreibe(
        f"{jahr:04d}-{monat:02d}: fertig, {len(dateien)} Kacheln, "
        f"{dauer_minuten:.1f} Minuten, Manifest {manifest_pfad.name}."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="erster Monat, Format JJJJ-MM")
    parser.add_argument("--ende", required=True, help="letzter Monat, Format JJJJ-MM (eingeschlossen)")
    args = parser.parse_args()

    protokoll_pfad = None
    try:
        protokoll_pfad = io.aleph_data_dir() / "protokoll" / "vnp46a3.log"
    except io.SSDNichtGefunden as fehler:
        print(f"ABBRUCH: {fehler}", file=sys.stderr)
        return 1
    protokoll = Protokoll(protokoll_pfad)

    alle_monate = _monatsliste(args.start, args.ende)
    fertige_monate = vnp46a3.vorhandene_monate()
    offene_monate = [m for m in alle_monate if m not in fertige_monate]

    protokoll.schreibe(
        f"Lauf gestartet: {args.start} bis {args.ende}, "
        f"{len(fertige_monate & set(alle_monate))} von {len(alle_monate)} Monaten bereits fertig, "
        f"{len(offene_monate)} offen."
    )

    for jahr, monat in offene_monate:
        try:
            io.pruefe_speicher()
        except (io.SSDNichtGefunden, io.SpeicherZuKnapp) as fehler:
            protokoll.schreibe(f"ABBRUCH vor {jahr:04d}-{monat:02d}: {fehler}")
            return 1

        try:
            verarbeite_monat(jahr, monat, protokoll)
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
