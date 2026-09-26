"""Zeigt den Stand des VNP46A3-Hintergrund-Laufs und ob etwas hängt.

Aufruf (normalerweise über scripts/vnp46a3_status.sh):
    .venv/bin/python -m aleph.layers.vnp46a3_status

Zeigt: läuft der Prozess noch, wie viele Monate (und Jahre) fertig sind, was
gerade läuft (Monat, Phase, Kacheln x von y), wann sich zuletzt etwas bewegt
hat, gemessene Dauer und eine grobe Restzeit. Außerdem: fertige Monate, offene
Monate und die Liste der Monate, die nachgeholt werden müssen (im Protokoll als
„ZURÜCKGESTELLT" vermerkt, siehe vnp46a3_lauf.py). Am Ende steht eine Ampel:
OK / ACHTUNG / HÄNGT / GESTOPPT / FERTIG / FERTIG MIT LÜCKEN.
"""

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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

# Datenmenge eines vollständigen Monats, als Spanne (für die Hochrechnung nach
# Datenmenge, seit 2026-09-26). Untere Grenze: Rohordner 2018-01 mit 502 von
# 540 Kacheln = 26,3 GB, auf 540 hochgerechnet etwa 28 GB. Obere Grenze:
# Manifest 2024-01, alle 540 Kacheln laut Katalog = 33,1 GB. Gemessen nur an
# diesen zwei Monaten; andere Monate können abweichen (Nicht geprüft).
GB_JE_MONAT_SPANNE = (28.0, 33.1)
# Anteil der Region Afrika-Europa-Asien (188 Kacheln) an der Datenmenge eines
# Monats: Manifest 2024-01, 14,9 von 33,1 GB (gemessen 2026-09-26, nur dieser Monat).
REGION_ANTEIL_DATEN = 14.9 / 33.1
# Verkleinern und Schreiben je Monat (gemessen 2026-09-23/24: 6,0-7,4 Minuten).
RECHNEN_MINUTEN_JE_MONAT = 6.5
# Zeitfenster für den aktuellen Durchsatz (Dateien im Rohordner des laufenden Monats).
DURCHSATZ_FENSTER_MINUTEN = 30

_ZEIT = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC\s+(.*)$")
_MONAT_START = re.compile(r"^(\d{4})-(\d{2}): Start ")
_MONAT_GEMELDET = re.compile(r"^(\d{4})-(\d{2}): (\d+) Kacheln bei NASA gemeldet")
_MONAT_DOWNLOAD_FERTIG = re.compile(r"^(\d{4})-(\d{2}): Download fertig")
_MONAT_WIEDERAUFGENOMMEN = re.compile(r"^(\d{4})-(\d{2}): \d+ Kacheln aus einem früheren Versuch schon vorhanden")
_MONAT_ZURUECKGESTELLT = re.compile(r"^(\d{4})-(\d{2}): ZURÜCKGESTELLT")
_MONAT_STATISTIK = re.compile(
    r"^(\d{4})-(\d{2}): Download-Statistik \(([^)]+)\): (\d+) Kacheln neu geladen \(([\d.]+) GB\) in ([\d.]+) Minuten, "
    r"([\d.]+) MB/s geprüfte Nutzdaten.*?; (\d+) nach Größen-/MD5-Prüfung verworfen \(davon (\d+) nicht mehr neu "
    r"geladen\); (\d+) Wiederholungen"
)
# So viele der letzten vollständig geladenen Monate bilden die Durchsatz-Spanne.
DURCHSATZ_MONATE = 5
# Abschlusszeilen der Stufen (seit 2026-09-26): nehmen den Monat aus „nachzuholen“,
# zählen aber NICHT als ganzer Monat für die alte Kachelzeit-Schätzung.
_MONAT_STUFE_FERTIG = re.compile(r"^(\d{4})-(\d{2}): fertig (für |\(Stufe 2)")
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
    - `zurueckgestellt`: dict Monat -> kurzer Grund, für Monate, bei denen zuletzt
      „ZURÜCKGESTELLT" stand (nicht „fertig"). Gilt über Läufe hinweg, nicht nur
      seit dem letzten Start: ein Monat bleibt nachzuholen, bis er fertig ist
    - `lauf_beendet_offen`: True, wenn der letzte Lauf mit „Lauf beendet mit
      offenen Monaten" endete
    - `wiederaufgenommen`: Monate, bei denen Kacheln aus einem früheren Versuch
      übernommen wurden (nur der Rest wurde geladen). Ihre Dauer ist keine
      Messung eines ganzen Monats und bleibt aus der Restzeit-Schätzung heraus
    - `nachhol`: letzte Protokollzeile „Nachhol-Durchgang ..." (oder None)
    - `statistik`: Liste der Zeilen „Download-Statistik" (seit 2026-09-26), je
      dict(monat, zustand, kacheln, gb, minuten, mb_s, verworfen, verworfen_endgueltig, wiederholungen);
      `zustand` ist „vollständig geladen" oder „abgebrochen" (Stillstand, Notbremse,
      gescheiterte Kacheln)
    """
    ergebnis = {
        "abgeschlossen": [],
        "lauf_beginn": None,
        "lauf_fertig": False,
        "fehler": [],
        "aktuell": None,
        "letzte_zeit": None,
        "zurueckgestellt": {},
        "lauf_beendet_offen": False,
        "wiederaufgenommen": set(),
        "nachhol": None,
        "statistik": [],
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
            ergebnis["lauf_beendet_offen"] = False
            ergebnis["nachhol"] = None
        elif text.startswith("Nachhol-Durchgang"):
            ergebnis["nachhol"] = text
        elif text.startswith("Lauf fertig"):
            ergebnis["lauf_fertig"] = True
        elif text.startswith("Lauf beendet mit offenen Monaten"):
            ergebnis["lauf_beendet_offen"] = True
        elif text.startswith("FEHLER") or text.startswith("ABBRUCH"):
            ergebnis["fehler"].append(zeile)

        if m := _MONAT_START.match(text):
            ergebnis["aktuell"] = {
                "monat": (int(m.group(1)), int(m.group(2))),
                "gemeldet": None,
                "download_fertig": False,
                "start": zeitpunkt,
                "download_seit": None,
                "teil": False,
            }
        elif (m := _MONAT_GEMELDET.match(text)) and ergebnis["aktuell"]:
            ergebnis["aktuell"]["gemeldet"] = int(m.group(3))
            ergebnis["aktuell"]["download_seit"] = zeitpunkt
            ergebnis["aktuell"]["teil"] = "ausgewählte Positionen" in text
        elif _MONAT_DOWNLOAD_FERTIG.match(text) and ergebnis["aktuell"]:
            ergebnis["aktuell"]["download_fertig"] = True
        elif m := _MONAT_STATISTIK.match(text):
            ergebnis["statistik"].append({
                "monat": (int(m.group(1)), int(m.group(2))),
                "zustand": m.group(3),
                "kacheln": int(m.group(4)),
                "gb": float(m.group(5)),
                "minuten": float(m.group(6)),
                "mb_s": float(m.group(7)),
                "verworfen": int(m.group(8)),
                "verworfen_endgueltig": int(m.group(9)),
                "wiederholungen": int(m.group(10)),
            })
        elif m := _MONAT_WIEDERAUFGENOMMEN.match(text):
            ergebnis["wiederaufgenommen"].add((int(m.group(1)), int(m.group(2))))
            if ergebnis["aktuell"]:
                ergebnis["aktuell"]["download_seit"] = zeitpunkt  # Prüfung der vorhandenen Kacheln ist vorbei
        elif m := _MONAT_ZURUECKGESTELLT.match(text):
            monat = (int(m.group(1)), int(m.group(2)))
            # Grund: der Teil nach dem Standardsatz, gekürzt (die volle Meldung steht im Protokoll)
            grund = text.split("Rohdaten bleiben erhalten.", 1)[-1].strip()
            ergebnis["zurueckgestellt"][monat] = grund[:220]
            ergebnis["aktuell"] = None
        elif m := _MONAT_STUFE_FERTIG.match(text):
            ergebnis["zurueckgestellt"].pop((int(m.group(1)), int(m.group(2))), None)
            ergebnis["aktuell"] = None
        elif m := _MONAT_FERTIG.match(text):
            ergebnis["abgeschlossen"].append(
                (int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6)))
            )
            ergebnis["zurueckgestellt"].pop((int(m.group(1)), int(m.group(2))), None)
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


def durchsatz_im_ordner(
    ordner: Path, jetzt: datetime, fenster_minuten: float = DURCHSATZ_FENSTER_MINUTEN,
    download_seit: datetime | None = None,
) -> float | None:
    """MB/s aus den fertigen Kacheln (.h5, ohne `partial_`) im Ordner, die im Zeitfenster fertig wurden.

    Das Fenster beginnt frühestens bei `download_seit` (Beginn des eigentlichen
    Ladens laut Protokoll); sonst würde die Prüfzeit wiederverwendeter Kacheln am
    Monatsanfang mitgezählt und der Durchsatz viel zu niedrig angezeigt.
    None, wenn im Fenster keine Kachel fertig wurde, das Fenster kürzer als
    2 Minuten ist oder der Ordner fehlt. Unterschätzt leicht (die gerade
    übertragenen Kacheln zählen noch nicht).
    """
    if not ordner.exists():
        return None
    grenze = jetzt.timestamp() - fenster_minuten * 60
    if download_seit is not None:
        grenze = max(grenze, download_seit.timestamp())
    sekunden = jetzt.timestamp() - grenze
    if sekunden < 120:
        return None
    summe = 0
    for p in ordner.iterdir():
        if p.suffix == ".h5" and not p.name.startswith("partial"):
            st = p.stat()
            if st.st_mtime >= grenze:
                summe += st.st_size
    return summe / 1e6 / sekunden if summe else None


def rohdaten_bytes(basis: Path) -> int:
    """Summe der fertigen Kacheln in allen Rohordnern (werden beim Weiterladen wiederverwendet)."""
    if not basis.exists():
        return 0
    return sum(
        p.stat().st_size for d in basis.iterdir() if d.is_dir()
        for p in d.iterdir() if p.suffix == ".h5" and not p.name.startswith("partial")
    )


def hochrechnung(
    offene_monate: int, roh_bytes: int, mb_s_min: float, mb_s_max: float | None = None, anteil: float = 1.0,
    monate_nur_rest: int = 0,
) -> dict:
    """Restmenge und Restdauer als Spanne (reine Funktion, testbar).

    Restmenge = offene Monate × GB_JE_MONAT_SPANNE minus die schon geladenen
    Rohdaten; Dauer = Restmenge / Durchsatz + RECHNEN_MINUTEN_JE_MONAT je Monat.
    Kürzeste Dauer: kleine Datenmenge bei höchstem Durchsatz; längste: große
    Datenmenge bei kleinstem Durchsatz. ANNAHME: der Durchsatz bleibt in der
    gemessenen Spanne; Zurückstellungen, Wiederholungen und doppelte Datenströme
    sind nicht eingerechnet. `anteil`: Anteil der Datenmenge je Monat, der noch
    zu laden ist (z. B. REGION_ANTEIL_DATEN für Stufe 1). `monate_nur_rest`: davon
    so viele Monate mit Zustand 4, bei denen nur noch (1 - REGION_ANTEIL_DATEN) fehlt.
    """
    mb_s_max = mb_s_min if mb_s_max is None else mb_s_max
    monate_gewichtet = (offene_monate - monate_nur_rest) * anteil + monate_nur_rest * (1 - REGION_ANTEIL_DATEN)
    tb = [max(monate_gewichtet * gb * 1e9 - roh_bytes, 0) / 1e12 for gb in GB_JE_MONAT_SPANNE]
    rechnen_tage = offene_monate * RECHNEN_MINUTEN_JE_MONAT / 1440
    tage = [
        tb[0] * 1e12 / (mb_s_max * 1e6) / 86400 + rechnen_tage,
        tb[1] * 1e12 / (mb_s_min * 1e6) / 86400 + rechnen_tage,
    ]
    return {"tb": tb, "tage": tage}


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
    print(f"Offene Monate: {len(alle) - len(fertig)} von {len(alle)}")
    je_zustand = vnp46a3.monate_je_zustand()
    region_voll = (je_zustand.get(vnp46a3.MONAT_REGION_VOLLSTAENDIG, set()) | fertig) & set(alle)
    print(
        f"Vollständig für Afrika-Europa-Asien (Zustand 4 oder fertig): {len(region_voll)} von {len(alle)}; "
        f"davon nur Region, übrige Zellen noch nicht geladen: {len(region_voll - fertig)}"
    )
    # Ein Monat gilt nur dann als nachzuholen, wenn er im Würfel wirklich noch
    # nicht fertig ist (das Protokoll allein könnte veraltet sein).
    nachzuholen = {m: g for m, g in p["zurueckgestellt"].items() if m not in fertig}
    if nachzuholen:
        print(f"Nachzuholen (zurückgestellt, später erneut versuchen): {len(nachzuholen)} Monat(e)")
        for (j, mo), grund in sorted(nachzuholen.items()):
            print(f"  {j:04d}-{mo:02d}: {grund}")
    else:
        print("Nachzuholen (zurückgestellt): keine")
    if p["nachhol"] and prozesse and not p["lauf_fertig"]:
        print(f"Nachholen: {p['nachhol']}")

    ampel = "OK"
    grund = ""
    aktuell = p["aktuell"]
    if aktuell and prozesse:
        monat_text = f"{aktuell['monat'][0]:04d}-{aktuell['monat'][1]:02d}"
        seit = _minuten(aktuell["start"], jetzt)
        if not aktuell["download_fertig"]:
            dateien, letzte = _rohordner_zustand(aktuell["monat"])
            if aktuell.get("teil"):
                print(
                    f"Aktuell: {monat_text}, Download (nur eine Stufe: {aktuell['gemeldet']} Kacheln), "
                    f"{dateien} Dateien im Rohordner (auch Kacheln der anderen Stufe), seit {seit:.0f} Minuten."
                )
            else:
                von = f" von {aktuell['gemeldet']}" if aktuell["gemeldet"] else ""
                print(f"Aktuell: {monat_text}, Download, {dateien}{von} Kacheln im Rohordner, seit {seit:.0f} Minuten.")
            # Späterer Zeitpunkt aus neuester Datei und Monats- bzw. Download-Beginn: Ein
            # Rohordner mit Kacheln aus einem früheren Versuch hat alte Dateien; die
            # sagen nichts darüber, ob der laufende Versuch steht (Befund 2026-09-26).
            referenz = max(t for t in (letzte, aktuell["start"], aktuell.get("download_seit")) if t is not None)
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
    elif p["lauf_beendet_offen"] and not prozesse:
        ampel, grund = "FERTIG MIT LÜCKEN", (
            f"der Lauf ist zu Ende, aber {len(nachzuholen)} Monate müssen nachgeholt werden "
            "(scripts/vnp46a3_start.sh startet einen neuen Versuch)"
        )
    elif not prozesse:
        ampel, grund = "GESTOPPT", "der Prozess läuft nicht, der Lauf ist aber nicht als fertig protokolliert"

    # Wiederaufgenommene Monate (nur der Rest geladen, z. B. 2019-02 mit 7,5 Minuten)
    # sind keine Messung eines ganzen Monats und würden die Schätzung zu
    # optimistisch machen.
    messbar = [a for a in p["abgeschlossen"] if (a[0], a[1]) not in p["wiederaufgenommen"]]
    ausgenommen = sorted((a[0], a[1]) for a in p["abgeschlossen"] if (a[0], a[1]) in p["wiederaufgenommen"])
    if messbar:
        n = len(messbar)
        gesamt_min = sum(a[3] for a in messbar)
        kacheln = sum(a[2] for a in messbar)
        print(f"Gemessen an {n} vollständig geladenen Monat(en) im neuen Protokollformat:")
        if ausgenommen:
            print(
                "  Nicht eingerechnet (Sonderfall: aus früherem Versuch fortgesetzt, nur der Rest wurde geladen): "
                + ", ".join(f"{j:04d}-{m:02d}" for j, m in ausgenommen) + "."
            )
        print(
            f"  Ø {gesamt_min / n:.1f} Minuten/Monat gesamt (Download Ø {sum(a[4] for a in messbar) / n:.1f}, "
            f"Verkleinern und Schreiben Ø {sum(a[5] for a in messbar) / n:.1f}), "
            f"{gesamt_min * 60 / kacheln:.1f} Sekunden je Kachel."
        )
        offen = len(alle) - len(fertig)
        raten = [a[3] * 60 / a[2] for a in messbar]  # Sekunden je Kachel, je Monat
        tage_je_rate = lambda r: offen * MITTLERE_KACHELN_JE_MONAT * r / 86400
        untere, obere = tage_je_rate(min(raten)), tage_je_rate(max(raten))
        print(
            f"  Restzeit grob (alte Schätzung aus Kachelzeiten, überholt seit den Monaten mit 540 Kacheln): {offen} offene Monate (von {len(alle)}), etwa {round(untere)} bis {max(round(obere), round(untere))} Tage "
            f"(schnellster bis langsamster gemessener Monat, Grundlage: {n} Monat(e); "
            f"Kachelzahl je Monat mit Ø {MITTLERE_KACHELN_JE_MONAT:.0f} angenommen, gemessen 534 bis 540 je Monat)."
        )
    else:
        print(
            "Noch kein vollständig geladener Monat im neuen Protokollformat abgeschlossen, keine Zeitmessung "
            "und keine Restzeit-Schätzung möglich."
        )

    # Durchsatz und Hochrechnung nach Datenmenge (seit 2026-09-26)
    raten: list[float] = []
    quellen: list[str] = []
    if aktuell and prozesse and not aktuell["download_fertig"]:
        r = durchsatz_im_ordner(
            io.rohdaten_pfad("vnp46a3", f"{aktuell['monat'][0]:04d}-{aktuell['monat'][1]:02d}"), jetzt,
            download_seit=aktuell.get("download_seit"),
        )
        if r:
            raten.append(r)
            quellen.append(f"laufender Monat, höchstens die letzten {DURCHSATZ_FENSTER_MINUTEN} Minuten seit Download-Beginn")
    if p["statistik"]:
        st = p["statistik"][-1]
        print(
            f"Letzte Download-Statistik ({st['monat'][0]:04d}-{st['monat'][1]:02d}, {st['zustand']}): "
            f"{st['kacheln']} Kacheln, {st['gb']:.1f} GB in {st['minuten']:.0f} Minuten = {st['mb_s']:.2f} MB/s "
            f"geprüfte Nutzdaten; {st['verworfen']} nach Größen-/MD5-Prüfung verworfen, "
            f"{st['wiederholungen']} Wiederholungen."
        )
        # Für den Durchsatz nur vollständig geladene Monate: eine abgebrochene
        # Zeile enthält Stillstand und würde die Rate verfälschen.
        voll = [x["mb_s"] for x in p["statistik"] if x["zustand"] == "vollständig geladen" and x["mb_s"] > 0]
        if voll:
            raten += voll[-DURCHSATZ_MONATE:]
            quellen.append(f"{len(voll[-DURCHSATZ_MONATE:])} zuletzt vollständig geladene Monate")
    offen = len(alle) - len(fertig)
    if raten:
        lo, hi = min(raten), max(raten)
        roh = rohdaten_bytes(io.rohdaten_pfad("vnp46a3"))
        offen_region = len(alle) - len(region_voll)
        if offen_region:
            # Stufe 1 (nur Region): Rohdaten nicht abgezogen (nicht nach Region getrennt gezählt) - vorsichtig.
            h1 = hochrechnung(offen_region, 0, lo, hi, anteil=REGION_ANTEIL_DATEN)
            e1 = [jetzt + timedelta(days=t) for t in h1["tage"]]
            print(
                f"Hochrechnung Stufe 1 (nur Afrika-Europa-Asien, {offen_region} Monate × "
                f"{REGION_ANTEIL_DATEN:.0%} der Monatsmenge): noch etwa {h1['tb'][0]:.1f} bis {h1['tb'][1]:.1f} TB, "
                f"{h1['tage'][0]:.0f} bis {h1['tage'][1]:.0f} Tage, also etwa {e1[0]:%d.%m.%Y} bis {e1[1]:%d.%m.%Y}. "
                "Anteil gemessen an einem Monat (2024-01); vorhandene Rohdaten nicht abgezogen, daher eher zu hoch."
            )
        nur_rest = len(region_voll - fertig)
        h = hochrechnung(offen, roh, lo, hi, monate_nur_rest=nur_rest)
        ende = [jetzt + timedelta(days=t) for t in h["tage"]]
        spanne = f"{lo:.1f} MB/s" if round(lo, 1) == round(hi, 1) else f"{lo:.1f} bis {hi:.1f} MB/s"
        print(f"Durchsatz: {spanne} ({'; '.join(quellen)}).")
        print(
            f"Hochrechnung bis ganz fertig (alle Stufen): noch etwa {h['tb'][0]:.1f} bis {h['tb'][1]:.1f} TB "
            f"({offen} offene Monate × {GB_JE_MONAT_SPANNE[0]:.0f}-{GB_JE_MONAT_SPANNE[1]:.0f} GB, davon {nur_rest} "
            f"mit Zustand 4 nur mit dem Rest-Anteil {1 - REGION_ANTEIL_DATEN:.0%}, "
            f"abzüglich {roh / 1e9:.0f} GB schon im Rohordner); bei {spanne} etwa "
            f"{h['tage'][0]:.0f} bis {h['tage'][1]:.0f} Tage, also etwa {ende[0]:%d.%m.%Y} bis {ende[1]:%d.%m.%Y}. "
            f"Annahme: der Durchsatz bleibt in dieser Spanne; je Monat {RECHNEN_MINUTEN_JE_MONAT:.1f} Minuten "
            "Rechenzeit eingerechnet, Zurückstellungen und Wiederholungen nicht."
        )
    elif offen:
        print("Durchsatz: noch kein Messwert (keine fertige Kachel im Zeitfenster, keine Download-Statistik).")

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
