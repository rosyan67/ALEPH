"""Zeigt den Stand des VNP46A3-Hintergrund-Laufs und ob etwas hängt.

Aufruf (normalerweise über scripts/vnp46a3_status.sh):
    .venv/bin/python -m aleph.layers.vnp46a3_status

Zeigt: läuft der Prozess noch, wie viele Monate (und Jahre) fertig sind, was
gerade läuft (Monat, Phase, Kacheln x von y), wann sich zuletzt etwas bewegt
hat, gemessene Dauer und eine grobe Restzeit. Am Ende steht eine Ampel:
OK / ACHTUNG / HÄNGT / GESTOPPT / FERTIG.
"""

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from aleph.core import io
from aleph.layers import vnp46a3

# Ab dieser Zeit ohne jede Bewegung im Rohordner wird gewarnt (der Download
# je Kachel hat ein Zeitlimit von 10 Minuten, danach kommt ein neuer Versuch).
WARNUNG_STILLSTAND_MINUTEN = 10
HAENGT_STILLSTAND_MINUTEN = 30
# Nach dem Download folgen Verkleinern und Schreiben (Rechenarbeit, keine neuen
# Dateien); ohne neue Protokollzeile so lange wird gewarnt.
WARNUNG_RECHNEN_MINUTEN = 45
# Mittlere Kachelzahl je Monat laut NASA-Katalog: 84 135 Kacheln / 156 Monate.
MITTLERE_KACHELN_JE_MONAT = 84135 / 156

_ZEIT = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC\s+(.*)$")
_MONAT_START = re.compile(r"^(\d{4})-(\d{2}): Start ")
_MONAT_GEMELDET = re.compile(r"^(\d{4})-(\d{2}): (\d+) Kacheln bei NASA gemeldet")
_MONAT_DOWNLOAD_FERTIG = re.compile(r"^(\d{4})-(\d{2}): Download fertig")
_MONAT_FERTIG = re.compile(
    r"^(\d{4})-(\d{2}): fertig, (\d+) Kacheln, .*Dauer gesamt ([\d.]+) Minuten "
    r"\(Download ([\d.]+), Verkleinern und Schreiben ([\d.]+)\)"
)


def _gesamt_monate() -> list[tuple[int, int]]:
    return [
        (z.astype(object).year, z.astype(object).month) for z in vnp46a3.zeitachse().astype("datetime64[M]")
    ]


def lies_protokoll(zeilen: list[str]) -> dict:
    """Wertet das Protokoll aus (reine Funktion, ohne Dateizugriff, testbar).

    Rückgabe:
    - `abgeschlossen`: Liste der in diesem Protokoll fertig gemeldeten Monate
      im neuen Format, je (jahr, monat, kacheln, gesamt_min, download_min, rechnen_min)
    - `lauf_beginn`: Zeitpunkt der letzten Zeile "Lauf gestartet" (oder None)
    - `lauf_fertig`: True, wenn nach dem letzten Start "Lauf fertig" steht
    - `fehler`: Fehler- und Abbruchzeilen seit dem letzten Start
    - `aktuell`: None oder dict(monat, gemeldet, download_fertig, start) für den
      Monat, der im letzten Lauf begonnen, aber nicht beendet wurde
    - `letzte_zeit`: Zeitpunkt der letzten Protokollzeile
    """
    ergebnis = {
        "abgeschlossen": [],
        "lauf_beginn": None,
        "lauf_fertig": False,
        "fehler": [],
        "aktuell": None,
        "letzte_zeit": None,
    }
    for zeile in zeilen:
        treffer = _ZEIT.match(zeile)
        if not treffer:
            continue  # Folgezeilen (z. B. Traceback) gehören zur Zeile davor
        zeitpunkt = datetime.strptime(treffer.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        text = treffer.group(2)
        ergebnis["letzte_zeit"] = zeitpunkt

        if text.startswith("Lauf gestartet"):
            ergebnis["lauf_beginn"] = zeitpunkt
            ergebnis["lauf_fertig"] = False
            ergebnis["fehler"] = []
            ergebnis["aktuell"] = None
        elif text.startswith("Lauf fertig"):
            ergebnis["lauf_fertig"] = True
        elif text.startswith("FEHLER") or text.startswith("ABBRUCH"):
            ergebnis["fehler"].append(zeile)

        if m := _MONAT_START.match(text):
            ergebnis["aktuell"] = {
                "monat": (int(m.group(1)), int(m.group(2))),
                "gemeldet": None,
                "download_fertig": False,
                "start": zeitpunkt,
            }
        elif (m := _MONAT_GEMELDET.match(text)) and ergebnis["aktuell"]:
            ergebnis["aktuell"]["gemeldet"] = int(m.group(3))
        elif _MONAT_DOWNLOAD_FERTIG.match(text) and ergebnis["aktuell"]:
            ergebnis["aktuell"]["download_fertig"] = True
        elif m := _MONAT_FERTIG.match(text):
            ergebnis["abgeschlossen"].append(
                (int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6)))
            )
            ergebnis["aktuell"] = None
    return ergebnis


def _prozess_nummern() -> list[str]:
    """Nummern der laufenden Lauf-Prozesse (leer, wenn keiner läuft).

    Das Muster ist am Anfang der Befehlszeile verankert (Python-Programm,
    dann `-m aleph.layers.vnp46a3_lauf`). Ohne Verankerung würde jede
    Shell, in deren Befehlstext der Name nur vorkommt (z. B. ein Test oder
    dieses Skript selbst), als laufender Lauf gezählt.
    """
    ergebnis = subprocess.run(
        ["pgrep", "-f", r"^[^ ]*python[^ ]* -m aleph[.]layers[.]vnp46a3_lauf"], capture_output=True, text=True
    )
    return ergebnis.stdout.split()


def _rohordner_zustand(monat: tuple[int, int]) -> tuple[int, datetime | None]:
    """Zahl der Dateien im Rohordner des Monats und Zeitpunkt der letzten Änderung daran."""
    ordner = io.rohdaten_pfad("vnp46a3", f"{monat[0]:04d}-{monat[1]:02d}")
    if not ordner.exists():
        return 0, None
    dateien = [p for p in ordner.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not dateien:
        return 0, None
    neueste = max(p.stat().st_mtime for p in dateien)
    return len(dateien), datetime.fromtimestamp(neueste, tz=timezone.utc)


def _minuten(von: datetime, bis: datetime) -> float:
    return (bis - von).total_seconds() / 60


def main() -> int:
    try:
        data_dir = io.aleph_data_dir()
    except io.SSDNichtGefunden as fehler:
        print(f"SSD nicht erreichbar: {fehler}")
        return 1

    jetzt = datetime.now(timezone.utc)
    alle = _gesamt_monate()
    try:
        fertig = vnp46a3.vorhandene_monate() & set(alle)
    except vnp46a3.WuerfelFormat as fehler:
        print(f"Würfel nicht lesbar: {fehler}")
        return 1

    prozesse = _prozess_nummern()
    protokoll_pfad: Path = data_dir / "protokoll" / "vnp46a3.log"
    if not protokoll_pfad.exists():
        print("Noch kein Protokoll vorhanden (Lauf wurde noch nicht gestartet).")
        return 0
    zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
    p = lies_protokoll(zeilen)

    print(f"Jetzt: {jetzt:%Y-%m-%d %H:%M:%S} UTC")
    print(f"Prozess: {'läuft (Nr. ' + ', '.join(prozesse) + ')' if prozesse else 'läuft NICHT'}")
    print(f"Fertige Monate: {len(fertig)} von {len(alle)}")
    jahre = sorted({j for j, _ in alle})
    je_jahr = "  ".join(f"{j}:{sum(1 for m in fertig if m[0] == j):>2}" for j in jahre)
    print(f"  je Jahr (von 12): {je_jahr}")

    ampel = "OK"
    grund = ""
    aktuell = p["aktuell"]
    if aktuell and prozesse:
        monat_text = f"{aktuell['monat'][0]:04d}-{aktuell['monat'][1]:02d}"
        seit = _minuten(aktuell["start"], jetzt)
        if not aktuell["download_fertig"]:
            dateien, letzte = _rohordner_zustand(aktuell["monat"])
            von = f" von {aktuell['gemeldet']}" if aktuell["gemeldet"] else ""
            print(f"Aktuell: {monat_text}, Download, {dateien}{von} Kacheln im Rohordner, seit {seit:.0f} Minuten.")
            referenz = letzte or aktuell["start"]
            still = _minuten(referenz, jetzt)
            print(f"  Letzte Bewegung im Rohordner vor {still:.1f} Minuten.")
            if still > HAENGT_STILLSTAND_MINUTEN:
                ampel, grund = "HÄNGT", f"seit über {HAENGT_STILLSTAND_MINUTEN} Minuten keine neue Datei"
            elif still > WARNUNG_STILLSTAND_MINUTEN:
                ampel, grund = "ACHTUNG", (
                    f"seit über {WARNUNG_STILLSTAND_MINUTEN} Minuten keine neue Datei "
                    "(Zeitlimit je Kachel ist 10 Minuten, danach kommt automatisch ein neuer Versuch)"
                )
        else:
            still = _minuten(p["letzte_zeit"], jetzt)
            print(f"Aktuell: {monat_text}, Verkleinern und Schreiben, letzte Protokollzeile vor {still:.1f} Minuten.")
            if still > WARNUNG_RECHNEN_MINUTEN:
                ampel, grund = "ACHTUNG", f"seit über {WARNUNG_RECHNEN_MINUTEN} Minuten keine neue Protokollzeile"
    elif p["lauf_fertig"] and not prozesse:
        ampel = "FERTIG"
    elif not prozesse:
        ampel, grund = "GESTOPPT", "der Prozess läuft nicht, der Lauf ist aber nicht als fertig protokolliert"

    if p["abgeschlossen"]:
        n = len(p["abgeschlossen"])
        gesamt_min = sum(a[3] for a in p["abgeschlossen"])
        kacheln = sum(a[2] for a in p["abgeschlossen"])
        print(f"Gemessen an {n} Monat(en) im neuen Protokollformat:")
        print(
            f"  Ø {gesamt_min / n:.1f} Minuten/Monat gesamt (Download Ø {sum(a[4] for a in p['abgeschlossen']) / n:.1f}, "
            f"Verkleinern und Schreiben Ø {sum(a[5] for a in p['abgeschlossen']) / n:.1f}), "
            f"{gesamt_min * 60 / kacheln:.1f} Sekunden je Kachel."
        )
        offen = len(alle) - len(fertig)
        raten = [a[3] * 60 / a[2] for a in p["abgeschlossen"]]  # Sekunden je Kachel, je Monat
        tage_je_rate = lambda r: offen * MITTLERE_KACHELN_JE_MONAT * r / 86400
        untere, obere = tage_je_rate(min(raten)), tage_je_rate(max(raten))
        print(
            f"  Restzeit grob: {offen} offene Monate (von {len(alle)}), etwa {round(untere)} bis {max(round(obere), round(untere))} Tage "
            f"(schnellster bis langsamster gemessener Monat, Grundlage: {n} Monat(e); "
            f"Kachelzahl je Monat mit Ø {MITTLERE_KACHELN_JE_MONAT:.0f} angenommen, echte Monate schwanken, z. B. hatte 2024-01 nur 460)."
        )
    else:
        print("Noch kein Monat im neuen Protokollformat abgeschlossen, keine Zeitmessung und keine Restzeit-Schätzung möglich.")

    if p["fehler"]:
        print(f"Fehler seit Lauf-Start:\n  {p['fehler'][-1]}")
        if ampel in ("OK", "GESTOPPT"):
            ampel, grund = "GESTOPPT", "der Lauf hat sich mit einem Fehler beendet"
    else:
        print("Keine Fehler seit Lauf-Start.")

    print(f"\nLetzte Protokollzeile:\n  {zeilen[-1] if zeilen else '(leer)'}")
    print(f"\nAMPEL: {ampel}{' - ' + grund if grund else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
