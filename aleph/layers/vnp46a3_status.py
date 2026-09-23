"""Zeigt den Stand des VNP46A3-Hintergrund-Laufs.

Aufruf (normalerweise über scripts/vnp46a3_status.sh):
    .venv/bin/python -m aleph.layers.vnp46a3_status
"""

import re
import sys

from aleph.core import io
from aleph.layers import vnp46a3

GESAMT_START = (2013, 1)
GESAMT_ENDE = (2025, 12)

_DAUER_ZEILE = re.compile(r"fertig, \d+ Kacheln, ([\d.]+) Minuten")


def _gesamtzahl_monate() -> int:
    jahr, monat = GESAMT_START
    end_jahr, end_monat = GESAMT_ENDE
    n = 0
    while (jahr, monat) <= (end_jahr, end_monat):
        n += 1
        monat += 1
        if monat > 12:
            monat, jahr = 1, jahr + 1
    return n


def main() -> int:
    try:
        data_dir = io.aleph_data_dir()
    except io.SSDNichtGefunden as fehler:
        print(f"SSD nicht erreichbar: {fehler}")
        return 1

    gesamt = _gesamtzahl_monate()
    fertig = vnp46a3.vorhandene_monate()
    fertig_im_zeitraum = {m for m in fertig if GESAMT_START <= m <= GESAMT_ENDE}
    print(f"Fertige Monate: {len(fertig_im_zeitraum)} von {gesamt}")

    protokoll_pfad = data_dir / "protokoll" / "vnp46a3.log"
    if not protokoll_pfad.exists():
        print("Noch kein Protokoll vorhanden (Lauf wurde noch nicht gestartet).")
        return 0

    zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
    dauern = [float(m.group(1)) for zeile in zeilen if (m := _DAUER_ZEILE.search(zeile))]
    if dauern:
        mittel_minuten = sum(dauern) / len(dauern)
        offen = gesamt - len(fertig_im_zeitraum)
        rest_minuten = mittel_minuten * offen
        print(
            f"Durchschnitt: {mittel_minuten:.1f} Minuten/Monat, "
            f"Restzeit-Schätzung für {offen} offene Monate: "
            f"{rest_minuten / 60:.1f} Stunden (grobe Schätzung, hängt vom Netz ab)."
        )
    else:
        print("Noch kein Monat abgeschlossen, keine Restzeit-Schätzung möglich.")

    fehler_zeilen = [z for z in zeilen if "FEHLER" in z or "ABBRUCH" in z]
    if fehler_zeilen:
        print(f"Letzter Fehler:\n  {fehler_zeilen[-1]}")
    else:
        print("Keine Fehler im Protokoll.")

    print(f"\nLetzte Protokollzeile:\n  {zeilen[-1] if zeilen else '(leer)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
