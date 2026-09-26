"""Hintergrund-Lauf: lädt VNP46A3 monatsweise, verkleinert sofort auf das
0,25°-Raster, schreibt in den Würfel auf der SSD und löscht die Originale.

Aufruf (normalerweise über scripts/vnp46a3_start.sh, nicht direkt):
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2013-01 --ende 2025-12
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2024-01 --ende 2024-01 --gleichzeitig 2
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2013-01 --ende 2025-12 --zuerst-ab 2018-01
    .venv/bin/python -m aleph.layers.vnp46a3_lauf --start 2013-01 --ende 2025-12 --zuerst-ab 2018-01 \
        --vorrang 2018-01..2019-12,2024-01

Eigenschaften:
- setzt nach einem Abbruch beim letzten fertigen Monat wieder an
  (aleph.layers.vnp46a3.vorhandene_monate prüft den Würfel auf der SSD),
- arbeitet die Monate auf Wunsch nicht der Reihe nach ab: mit
  `--zuerst-ab 2018-01` kommen zuerst alle Monate ab 2018-01 (zeitlich
  aufsteigend), danach die früheren (ebenfalls aufsteigend). Sinn: bricht der
  Lauf ab oder greift die NASA-Frist (1.11.2026) früher, liegen bereits die
  jüngeren Jahre vollständig vor. Mit `--vorrang` kommen einzelne Monate oder
  Bereiche (z. B. `2018-01..2019-12,2024-01`) in der angegebenen Reihenfolge
  noch davor (Auftrag 2026-09-25: erst ein vollständiges Jahr 2018 für die
  erste Auswertung). Die Reihenfolge des Ladens hat keinen
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
- prüft nach dem Laden, ob der Monat vollständig ist (gegen die Trefferzahl
  des NASA-Katalogs über alle Seiten und gegen die Referenzliste der
  Kachelpositionen; jede Kachel zusätzlich gegen Größe und MD5 aus dem
  Katalog), bevor er verarbeitet wird,
- schreibt ein Protokoll und ein Manifest mit Zustand, Größe und MD5 je
  Kachelposition auf die SSD (protokoll/vnp46a3.log,
  protokoll/manifeste/vnp46a3/<Monat>.tsv),
- prüft nach dem Schreiben, dass der Monat tatsächlich im Würfel steht,
  bevor die Rohdaten gelöscht werden,
- stellt einen Monat zurück, wenn seit vnp46a3.STILLSTAND_SEKUNDEN (30 Minuten)
  keine neue, geprüfte Kachel mehr fertig geworden ist (Stillstand), oder -
  als Notbremse - wenn sein Download länger als
  vnp46a3.MONAT_NOTBREMSE_SEKUNDEN (12 Stunden) dauert (seit 2026-09-26; vorher
  eine feste Gesamtfrist von 4 Stunden, die auch langsame, aber stetige Monate
  zurückstellte), schreibt je Monat eine Zeile „Download-Statistik“ (MB/s,
  verworfene Kacheln, Wiederholungen) und beendet sich am Ende mit `os._exit`,
  damit hängende Hintergrund-Threads den Prozess nicht am wirklichen Beenden
  hindern.

Fehlerverhalten (Auftrag 2026-09-24, nach dem Abbruch bei 2019-02 wegen zweier
Kacheln mit HTTP 502):
- Der Lauf endet NUR noch bei echten Blockern: kein Speicherplatz, SSD nicht
  erreichbar, Anmeldung fehlgeschlagen (Meldung „ABBRUCH", Rückgabewert 1).
- Ein Monat, bei dem nach allen Wiederholungen Kacheln fehlen, wird
  ZURÜCKGESTELLT: nicht als fertig markiert, Rohdaten unangetastet, Vermerk im
  Protokoll („ZURÜCKGESTELLT (später erneut versuchen)"), weiter mit dem
  nächsten Monat. Dasselbe gilt für einen Verarbeitungsfehler in einem Monat
  (z. B. eine unlesbare Kachel); nur `MAX_VERARBEITUNGSFEHLER_HINTEREINANDER`
  davon in Folge beenden den Lauf (Verdacht auf Programm- oder
  Datenträgerfehler statt auf ein Einzelproblem).
- Am Ende werden die zurückgestellten Monate in einem Nachhol-Durchgang noch
  einmal versucht. Gültige Kacheln aus dem ersten Versuch werden
  wiederverwendet. Kam dabei mindestens ein Monat dazu und sind noch welche
  offen, folgt nach `NACHHOL_PAUSE_SEKUNDEN` (30 Minuten) ein weiterer Durchgang,
  insgesamt höchstens `NACHHOL_MAX_DURCHGAENGE` (3). Ein Durchgang ohne
  Fortschritt beendet das Nachholen (der Server ist dann vermutlich weiter
  gestört; jetzt zu warten brächte nichts). Bleiben Monate offen, endet der
  Lauf mit Rückgabewert 2 und der Meldung „Lauf beendet mit offenen Monaten";
  ein Neustart versucht sie erneut.
- Häufen sich HTTP-403-Antworten (mehr als 5 hintereinander oder alle Kacheln
  eines Monats), endet der Lauf als Blocker „Anmeldung prüfen"
  (aleph.layers.vnp46a3, `ZUGANG`); einzelne 403 sind ein Kachelfehler.
- Beim Start werden vorhandene Rohordner früherer Läufe NICHT mehr gelöscht,
  sondern wiederverwendet.

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
from aleph.layers import vnp46a3, vnp46a3_regionen

# Echte Blocker: nur sie beenden den Lauf.
BLOCKER = (io.SSDNichtGefunden, io.SpeicherZuKnapp, vnp46a3.AnmeldungFehlgeschlagen)

# So viele Monate in Folge mit einem Verarbeitungsfehler (nicht Download)
# beenden den Lauf: ein Einzelfall wird zurückgestellt, eine Serie deutet auf
# einen Programm- oder Datenträgerfehler, und jeder weitere Monat würde eine
# Stunde Download für nichts kosten.
MAX_VERARBEITUNGSFEHLER_HINTEREINANDER = 3

# Nachhol-Durchgänge am Ende des Laufs: solange im vorigen Durchgang mindestens
# ein Monat dazukam, mit Pause dazwischen; insgesamt höchstens so viele.
NACHHOL_MAX_DURCHGAENGE = 3
NACHHOL_PAUSE_SEKUNDEN = 30 * 60

FERTIG = "fertig"
ZURUECKGESTELLT = "zurückgestellt"
VERARBEITUNGSFEHLER = "verarbeitungsfehler"

# Stufen eines Monats (seit 2026-09-26, Vorrang nach Region, Option --region-zuerst):
# voll   = alle Kacheln, Ergebnis Zustand 1 (wie bisher)
# region = nur die Kacheln der Region, Ergebnis Zustand 4 (vnp46a3.MONAT_REGION_VOLLSTAENDIG)
# rest   = die übrigen Kacheln eines Monats mit Zustand 4, vereinigt mit dem
#          Region-Teil aus dem Würfel, Ergebnis Zustand 1
STUFE_VOLL, STUFE_REGION, STUFE_REST = "voll", "region", "rest"


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


def _reihenfolge(
    monate: list[tuple[int, int]],
    zuerst_ab: str | None,
    vorrang: list[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """Ordnet die Monate: erst die `vorrang`-Monate (in ihrer Reihenfolge, soweit
    offen), dann alle ab `zuerst_ab` (aufsteigend), dann die früheren (aufsteigend).

    Ohne `zuerst_ab` bleibt es für den Rest bei der zeitlichen Reihenfolge.
    """
    vorne = [m for m in (vorrang or []) if m in set(monate)]
    rest = [m for m in monate if m not in set(vorne)]
    if zuerst_ab is None:
        return vorne + sorted(rest)
    grenze = tuple(int(t) for t in zuerst_ab.split("-"))
    return vorne + sorted(m for m in rest if m >= grenze) + sorted(m for m in rest if m < grenze)


def _vorrang_argument(text: str) -> list[tuple[int, int]]:
    """'2018-01..2019-12,2024-01' -> Monatsliste in dieser Reihenfolge, ohne Doppelte (argparse-Typ)."""
    monate: list[tuple[int, int]] = []
    for teil in text.split(","):
        grenzen = teil.strip().split("..")
        if len(grenzen) not in (1, 2) or not all(re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", g) for g in grenzen):
            raise argparse.ArgumentTypeError(
                f"'{teil}' ist weder ein Monat JJJJ-MM noch ein Bereich JJJJ-MM..JJJJ-MM."
            )
        if len(grenzen) == 2 and grenzen[0] > grenzen[1]:
            raise argparse.ArgumentTypeError(f"Bereich '{teil}' läuft rückwärts.")
        for m in _monatsliste(grenzen[0], grenzen[-1]):
            if m not in monate:
                monate.append(m)
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


def _stempel(zeitpunkt: datetime) -> str:
    return zeitpunkt.strftime("%Y-%m-%d %H:%M:%S UTC")


def verarbeite_monat(
    jahr: int,
    monat: int,
    protokoll: Protokoll,
    gleichzeitige_downloads: int,
    stufe: str = STUFE_VOLL,
    region: str | None = None,
) -> None:
    """Lädt, prüft, verkleinert und schreibt einen Monat (Stufe siehe STUFE_*)."""
    name = f"{jahr:04d}-{monat:02d}"
    zusatz_kw: dict = {}
    zusatz = ""
    region_pos: set[str] = set()
    if stufe != STUFE_VOLL:
        region_pos = vnp46a3_regionen.lies_region(region)
        if stufe == STUFE_REGION:
            zusatz_kw["positionen"] = region_pos
            zusatz = f"_{region}"
        else:
            zusatz_kw["positionen"] = vnp46a3.lies_referenz_positionen() - region_pos
            zusatz = "_rest"
    region_text = vnp46a3_regionen.REGION_TEXT.get(region, region or "")
    if stufe == STUFE_REST:
        # Auflage B1: Der Region-Teil im Würfel muss mit genau dieser Kachelliste
        # entstanden und vollständig sein; sonst den ganzen Monat neu laden.
        ok, grund, nicht_beim_anbieter_stufe1 = vnp46a3.pruefe_stufe1_nachweis(jahr, monat, region)
        if not ok:
            protokoll.schreibe(f"{name}: Stufe-1-Nachweis passt nicht ({grund}); der ganze Monat wird neu geladen.")
            return verarbeite_monat(jahr, monat, protokoll, gleichzeitige_downloads)
    # Ein Rohordner aus einem früheren Versuch wird NICHT gelöscht: lade_monat
    # verwendet die gültigen Kacheln darin wieder und lädt nur die fehlenden.
    raw_ordner = io.rohdaten_pfad("vnp46a3", name)

    # Echte Uhrzeiten (Wanduhr, UTC) für Start und Ende; Dauern mit der
    # monotonen Uhr gemessen, damit eine Uhrumstellung sie nicht verfälscht.
    start_wand = datetime.now(timezone.utc)
    t0 = time.monotonic()
    stufen_text = {STUFE_VOLL: "", STUFE_REGION: f" (Stufe 1: nur {region_text})",
                   STUFE_REST: f" (Stufe 2: übrige Kacheln, {region_text} schon im Würfel)"}[stufe]
    protokoll.schreibe(f"{name}: Start {_stempel(start_wand)}{stufen_text}.")

    # lade_monat prüft selbst die Vollständigkeit (gegen Katalog und
    # Referenzliste) und bricht mit KachelnFehlen bzw. MonatUnvollstaendig
    # ab, BEVOR etwas geschrieben oder gelöscht wird - die Rohdaten bleiben
    # dann für den nächsten Versuch liegen.
    ladung = vnp46a3.lade_monat(
        jahr,
        monat,
        raw_ordner,
        gleichzeitige_downloads=gleichzeitige_downloads,
        melde=lambda text: protokoll.schreibe(f"{name}: {text}"),
        **zusatz_kw,
    )
    if stufe == STUFE_REST:
        # Auflage B2: Meldet der Katalog jetzt eine Region-Position, die in Stufe 1
        # „beim Anbieter nicht vorhanden“ war, fehlt sie im Region-Teil: ganz neu laden.
        neu_gemeldet = nicht_beim_anbieter_stufe1 & set(ladung.katalog_positionen)
        if neu_gemeldet:
            protokoll.schreibe(
                f"{name}: Der Katalog meldet jetzt Region-Kacheln, die in Stufe 1 beim Anbieter fehlten "
                f"({', '.join(sorted(neu_gemeldet))}); der ganze Monat wird neu geladen."
            )
            return verarbeite_monat(jahr, monat, protokoll, gleichzeitige_downloads)
    # Rest-Befund A1: direkt vor dem Lesen prüfen, ob die geprüften Dateien noch dieselben sind.
    vnp46a3.pruefe_ladung_unveraendert(ladung)
    dateien = ladung.dateien
    t_download = time.monotonic()
    protokoll.schreibe(f"{name}: Download fertig nach {(t_download - t0) / 60:.1f} Minuten.")

    # Manifest VOR dem Schreiben in den Würfel: Bricht es danach ab, gibt es
    # trotzdem einen Nachweis dieses Ladestands (Auflage statistik-pruefer
    # 2026-09-25). Die Kopfzeile nennt, was der Würfel bis dahin enthielt.
    stand = vnp46a3.MONATSSTATUS_TEXT.get(vnp46a3.monatsstatus(jahr, monat), "unbekannt")
    teil_hinweis = {STUFE_VOLL: "", STUFE_REGION: (
                        f" Nur Kacheln der Region {region_text} (Stufe 1). {vnp46a3.REGION_PRUEFSUMME_TEXT}: "
                        f"{vnp46a3_regionen.pruefsumme(region_pos)}."),
                    STUFE_REST: f" Nur die übrigen Kacheln (Stufe 2); Region-Teil siehe Manifest {name}_{region}.tsv."}[stufe]
    manifest_pfad = vnp46a3.schreibe_manifest(
        jahr, monat, ladung.zustaende,
        hinweis=f"Würfel-Stand dieses Monats vor dem Schreiben: {stand}; Manifest beschreibt den neuen Ladestand.{teil_hinweis}",
        **({"zusatz": zusatz} if zusatz else {}),
    )

    monatsdaten = vnp46a3.verkleinere_monat(dateien, erwarteter_monat=(jahr, monat))
    if stufe == STUFE_REST:
        # Region-Teil aus dem Würfel übernehmen; bricht ab, wenn der Monat nicht
        # Zustand 4 hat oder sich Region und Rest überschneiden.
        monatsdaten = vnp46a3.vereine_mit_region(monatsdaten, region_pos)
    # schreibe_in_wuerfel legt den Monat an seine Position auf der festen
    # Zeitachse, liest ihn zurück, vergleicht und setzt erst dann die
    # Fertig-Markierung (Zustand 1, in Stufe 1 Zustand 4).
    if stufe == STUFE_REGION:
        vnp46a3.schreibe_in_wuerfel(monatsdaten, zielzustand=vnp46a3.MONAT_REGION_VOLLSTAENDIG)
    else:
        vnp46a3.schreibe_in_wuerfel(monatsdaten)

    # Zusätzliche Kontrolle vor dem Löschen der Rohdaten: der Monat muss
    # mit dem erwarteten Zustand lesbar sein.
    if stufe == STUFE_REGION:
        if vnp46a3.monatsstatus(jahr, monat) != vnp46a3.MONAT_REGION_VOLLSTAENDIG:
            raise RuntimeError(
                f"{name}: nach dem Schreiben nicht als „vollständig für {region_text}“ im Würfel "
                "gefunden. Rohdaten bleiben erhalten, nichts wurde gelöscht."
            )
    elif (jahr, monat) not in vnp46a3.vorhandene_monate():
        raise RuntimeError(
            f"{name}: nach dem Schreiben nicht als fertig im Würfel "
            "gefunden. Rohdaten bleiben erhalten, nichts wurde gelöscht."
        )
    t_wuerfel = time.monotonic()

    if stufe == STUFE_REST:
        # Ein älteres Manifest ohne Stufen-Zusatz (z. B. „Ladeversuch GESCHEITERT“
        # aus einem Lauf ohne Region) widerspräche jetzt dem Würfel: umbenennen, nicht löschen.
        alt_manifest = vnp46a3.manifest_pfad(jahr, monat)
        if alt_manifest.exists():
            alt_manifest.rename(alt_manifest.with_name(alt_manifest.stem + "_ueberholt.tsv"))
    if stufe == STUFE_REGION:
        # Nur die geprüften und geschriebenen Region-Kacheln löschen; schon
        # geladene übrige Kacheln bleiben für Stufe 2 liegen.
        for pfad in dateien:
            pfad.unlink(missing_ok=True)
        ende_wand = datetime.now(timezone.utc)
        protokoll.schreibe(
            f"{name}: fertig für {region_text}, {len(dateien)} Kacheln, Start {_stempel(start_wand)}, "
            f"Ende {_stempel(ende_wand)}, Dauer gesamt {(time.monotonic() - t0) / 60:.1f} Minuten "
            f"(Download {(t_download - t0) / 60:.1f}, Verkleinern und Schreiben "
            f"{(t_wuerfel - t_download) / 60:.1f}), Manifest {manifest_pfad.name}. Zustand 4: übrige Zellen nicht geladen."
        )
        return

    shutil.rmtree(raw_ordner)

    ende_wand = datetime.now(timezone.utc)
    gesamt = (time.monotonic() - t0) / 60
    fertig_text = "fertig (Stufe 2, übrige Kacheln)" if stufe == STUFE_REST else "fertig"
    protokoll.schreibe(
        f"{name}: {fertig_text}, {len(dateien)} Kacheln, Start {_stempel(start_wand)}, "
        f"Ende {_stempel(ende_wand)}, Dauer gesamt {gesamt:.1f} Minuten "
        f"(Download {(t_download - t0) / 60:.1f}, Verkleinern und Schreiben "
        f"{(t_wuerfel - t_download) / 60:.1f}), Manifest {manifest_pfad.name}."
    )


def _bearbeite_monat(
    jahr: int, monat: int, protokoll: Protokoll, gleichzeitige_downloads: int,
    stufe: str = STUFE_VOLL, region: str | None = None,
) -> tuple[str, str]:
    """Ein Monat, mit Fehlerbehandlung nach dem Auftrag vom 2026-09-24.

    Rückgabe: (FERTIG | ZURUECKGESTELLT | VERARBEITUNGSFEHLER, Grund).
    Echte Blocker (`BLOCKER`) werden NICHT abgefangen, sondern weitergereicht.
    Bei jedem anderen Fehler bleiben Würfel und Rohdaten des Monats unberührt
    (verarbeite_monat löscht Rohdaten erst als letzten Schritt).
    """
    name = f"{jahr:04d}-{monat:02d}"
    try:
        if stufe == STUFE_VOLL:
            verarbeite_monat(jahr, monat, protokoll, gleichzeitige_downloads)
        else:
            verarbeite_monat(jahr, monat, protokoll, gleichzeitige_downloads, stufe=stufe, region=region)
        return FERTIG, ""
    except BLOCKER:
        raise
    except (vnp46a3.KachelnFehlen, vnp46a3.DownloadHaengt, vnp46a3.MonatUnvollstaendig) as fehler:
        grund = str(fehler)
        # Zustand je Kachelposition festhalten, auch wenn der Monat offen bleibt
        # (welche Positionen „nicht geladen" sind und warum).
        zustaende = getattr(fehler, "zustaende", None)
        if zustaende:
            stand = vnp46a3.MONATSSTATUS_TEXT.get(vnp46a3.monatsstatus(jahr, monat), "unbekannt")
            # Befund 3: gescheiterte Stufen schreiben in das Manifest ihrer Stufe
            # (ein späterer Erfolg derselben Stufe überschreibt es).
            zusatz = {STUFE_VOLL: "", STUFE_REGION: f"_{region}", STUFE_REST: "_rest"}[stufe]
            stufe_text = {STUFE_VOLL: "", STUFE_REGION: " (Stufe 1, nur Region)", STUFE_REST: " (Stufe 2, übrige Kacheln)"}[stufe]
            pfad = vnp46a3.schreibe_manifest(
                jahr, monat, zustaende,
                hinweis=f"Ladeversuch GESCHEITERT{stufe_text}; der Würfel enthält für diesen Monat: {stand}.",
                **({"zusatz": zusatz} if zusatz else {}),
            )
            grund += f" Manifest {pfad.name}."
        protokoll.schreibe(
            f"{name}: ZURÜCKGESTELLT (später erneut versuchen), nicht als fertig markiert, "
            f"Rohdaten bleiben erhalten. {grund}"
        )
        return ZURUECKGESTELLT, grund
    except Exception as fehler:  # bewusst breit: ein Einzelfall darf den Lauf nicht beenden
        # Ein Schreib- oder Verbindungsfehler kann ein Blocker sein (Platte voll, SSD weg).
        vnp46a3.pruefe_blocker(fehler, None)
        grund = f"{type(fehler).__name__}: {fehler}"
        # Nur „nicht als fertig markiert" schreiben, wenn der Würfel das bestätigt
        # (Auflage statistik-pruefer 2026-09-26: ein Fehler NACH dem Schreiben, z. B.
        # beim Löschen der Rohdaten, ließe sonst eine falsche Aussage im Protokoll).
        try:
            if stufe == STUFE_REGION:
                im_wuerfel_fertig = vnp46a3.monatsstatus(jahr, monat) == vnp46a3.MONAT_REGION_VOLLSTAENDIG
            else:
                im_wuerfel_fertig = (jahr, monat) in vnp46a3.vorhandene_monate()
        except Exception:  # noqa: BLE001 - nur für den Wortlaut der Meldung
            im_wuerfel_fertig = None
        if im_wuerfel_fertig:
            protokoll.schreibe(
                f"{name}: FEHLER NACH DEM SCHREIBEN - der Monat steht als fertig im Würfel, danach trat "
                f"ein Fehler auf (z. B. beim Löschen der Rohdaten). {grund}\n{traceback.format_exc()}"
            )
            return FERTIG, grund
        stand = "nicht als fertig markiert" if im_wuerfel_fertig is False else "Würfel-Stand nicht lesbar"
        protokoll.schreibe(
            f"{name}: ZURÜCKGESTELLT (später erneut versuchen), Verarbeitungsfehler, {stand}, "
            f"Rohdaten bleiben erhalten. {grund}\n{traceback.format_exc()}"
        )
        return VERARBEITUNGSFEHLER, grund


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
        "--vorrang",
        default=None,
        type=_vorrang_argument,
        help=(
            "Monate oder Bereiche, die vor allen anderen geladen werden, in dieser Reihenfolge, "
            "z. B. 2018-01..2019-12,2024-01."
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
    parser.add_argument(
        "--region-zuerst",
        default=None,
        choices=sorted(vnp46a3_regionen.REGIONEN),
        help=(
            "Zweistufig laden (seit 2026-09-26): erst nur die Kacheln dieser Region für alle offenen "
            "Monate (Zustand 4), danach die übrigen Kacheln (Zustand 1). Keine Region wird weggelassen."
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
    offene_monate = _reihenfolge(
        [m for m in alle_monate if m not in fertige_monate], args.zuerst_ab, args.vorrang
    )

    reihenfolge_text = (
        f", Reihenfolge: zuerst ab {args.zuerst_ab}, dann davor" if args.zuerst_ab else ", zeitliche Reihenfolge"
    )
    if args.vorrang:
        reihenfolge_text += (
            f", Vorrang für {len(args.vorrang)} Monate "
            f"({args.vorrang[0][0]:04d}-{args.vorrang[0][1]:02d} bis "
            f"{args.vorrang[-1][0]:04d}-{args.vorrang[-1][1]:02d})"
        )
    protokoll.schreibe(
        f"Lauf gestartet: {args.start} bis {args.ende}, gleichzeitig={args.gleichzeitig}"
        f"{reihenfolge_text}, "
        f"{len(fertige_monate & set(alle_monate))} von {len(alle_monate)} Monaten bereits fertig, "
        f"{len(offene_monate)} offen"
        + (f", erster Monat {offene_monate[0][0]:04d}-{offene_monate[0][1]:02d}." if offene_monate else ".")
    )

    alte_rohordner = sorted(p.name for p in io.rohdaten_pfad("vnp46a3").glob("*") if p.is_dir())
    if alte_rohordner:
        protokoll.schreibe(
            "Rohdaten aus früheren Versuchen vorhanden für: "
            f"{', '.join(alte_rohordner)} (gültige Kacheln werden wiederverwendet, nicht neu geladen)."
        )

    zustand = {"verarbeitungsfehler_in_folge": 0}

    def stufe_mit_nachholen(monate: list[tuple[int, int]], stufe_fuer, titel: str) -> tuple[int | None, dict]:
        """Bearbeitet `monate` (Stufe je Monat aus `stufe_fuer(monat)`), dann bis zu
        NACHHOL_MAX_DURCHGAENGE Nachhol-Durchgänge. Rückgabe: (Lauf-Ende oder None, zurückgestellt)."""
        zurueckgestellt: dict[tuple[int, int], str] = {}  # Monat -> Grund, in der Reihenfolge des Zurückstellens

        def durchgang(liste: list[tuple[int, int]]) -> int | None:
            for jahr, monat in liste:
                name = f"{jahr:04d}-{monat:02d}"
                try:
                    io.pruefe_speicher()
                    stufe = stufe_fuer((jahr, monat))
                    if stufe == STUFE_VOLL:
                        ergebnis, grund = _bearbeite_monat(jahr, monat, protokoll, args.gleichzeitig)
                    else:
                        ergebnis, grund = _bearbeite_monat(
                            jahr, monat, protokoll, args.gleichzeitig, stufe=stufe, region=args.region_zuerst
                        )
                except BLOCKER as fehler:
                    protokoll.schreibe(f"ABBRUCH bei {name}: {fehler}")
                    return 1
                if ergebnis == FERTIG:
                    zurueckgestellt.pop((jahr, monat), None)
                    zustand["verarbeitungsfehler_in_folge"] = 0
                    continue
                zurueckgestellt[(jahr, monat)] = grund
                zustand["verarbeitungsfehler_in_folge"] = (
                    zustand["verarbeitungsfehler_in_folge"] + 1 if ergebnis == VERARBEITUNGSFEHLER else 0
                )
                if zustand["verarbeitungsfehler_in_folge"] >= MAX_VERARBEITUNGSFEHLER_HINTEREINANDER:
                    protokoll.schreibe(
                        f"ABBRUCH bei {name}: {zustand['verarbeitungsfehler_in_folge']} Monate hintereinander mit "
                        "Verarbeitungsfehler (nicht Download). Das sieht nach einem Programm- oder "
                        "Datenträgerfehler aus, nicht nach einem Einzelfall; weitere Monate würden nur "
                        "Download-Zeit kosten. Letzter Grund siehe oben."
                    )
                    return 1
            return None

        ende_ = durchgang(monate)
        if ende_ is not None:
            return ende_, zurueckgestellt
        for durchgang_nr in range(1, NACHHOL_MAX_DURCHGAENGE + 1):
            if not zurueckgestellt:
                break
            nachholen = list(zurueckgestellt)
            protokoll.schreibe(
                f"Nachhol-Durchgang {durchgang_nr} von höchstens {NACHHOL_MAX_DURCHGAENGE}{titel}: "
                f"{len(nachholen)} zurückgestellte Monate werden noch einmal versucht: "
                f"{', '.join(f'{j:04d}-{m:02d}' for j, m in nachholen)}."
            )
            ende_ = durchgang(nachholen)
            if ende_ is not None:
                return ende_, zurueckgestellt
            nachgeholt = len(nachholen) - len(zurueckgestellt)
            if not zurueckgestellt:
                break
            if nachgeholt == 0:
                protokoll.schreibe(
                    f"Nachhol-Durchgang {durchgang_nr}{titel}: kein Monat dazugekommen, {len(zurueckgestellt)} weiterhin "
                    "offen. Kein weiterer Durchgang (die Ursache ist vermutlich nicht vorübergehend)."
                )
                break
            if durchgang_nr == NACHHOL_MAX_DURCHGAENGE:
                protokoll.schreibe(
                    f"Nachhol-Durchgang {durchgang_nr}{titel}: {nachgeholt} Monat(e) dazugekommen, "
                    f"{len(zurueckgestellt)} weiterhin offen. Höchstzahl an Durchgängen erreicht."
                )
                break
            protokoll.schreibe(
                f"Nachhol-Durchgang {durchgang_nr}{titel}: {nachgeholt} Monat(e) dazugekommen, "
                f"{len(zurueckgestellt)} weiterhin offen. Pause {NACHHOL_PAUSE_SEKUNDEN // 60} Minuten, "
                f"dann Durchgang {durchgang_nr + 1}."
            )
            time.sleep(NACHHOL_PAUSE_SEKUNDEN)
        return None, zurueckgestellt

    def stufe_nach_zustand(monat: tuple[int, int]) -> str:
        # Ein Monat mit Zustand 4 braucht nur noch den Rest; alle anderen den ganzen Monat.
        if args.region_zuerst and vnp46a3.monatsstatus(*monat) == vnp46a3.MONAT_REGION_VOLLSTAENDIG:
            return STUFE_REST
        return STUFE_VOLL

    region_offen: dict = {}
    if args.region_zuerst:
        region_text = vnp46a3_regionen.REGION_TEXT[args.region_zuerst]
        je_zustand = vnp46a3.monate_je_zustand()
        schon = je_zustand.get(vnp46a3.MONAT_FERTIG, set()) | je_zustand.get(vnp46a3.MONAT_REGION_VOLLSTAENDIG, set())
        stufe1 = [m for m in offene_monate if m not in schon]
        protokoll.schreibe(
            f"Stufe 1 ({region_text}, {len(vnp46a3_regionen.lies_region(args.region_zuerst))} Kacheln): "
            f"{len(stufe1)} Monate offen"
            + (f", erster Monat {stufe1[0][0]:04d}-{stufe1[0][1]:02d}." if stufe1 else ".")
        )
        ende, region_offen = stufe_mit_nachholen(stufe1, lambda m: STUFE_REGION, f" (Stufe 1, {region_text})")
        if ende is not None:
            return ende
        fertig_jetzt = vnp46a3.vorhandene_monate()
        offene_monate = [m for m in offene_monate if m not in fertig_jetzt]
        protokoll.schreibe(
            f"Stufe 1 ({region_text}) beendet: {len(region_offen)} Monate offen geblieben. "
            f"Stufe 2 (übrige Kacheln): {len(offene_monate)} Monate offen."
        )
    ende, zurueckgestellt = stufe_mit_nachholen(
        offene_monate, stufe_nach_zustand, " (Stufe 2, übrige Kacheln)" if args.region_zuerst else ""
    )
    if ende is not None:
        return ende

    if zurueckgestellt:
        protokoll.schreibe(
            f"Lauf beendet mit offenen Monaten: {len(zurueckgestellt)} Monate sind weiterhin nicht "
            "fertig und müssen nachgeholt werden (Rohdaten bleiben erhalten; Neustart mit "
            "scripts/vnp46a3_start.sh versucht sie erneut): "
            + "; ".join(f"{j:04d}-{m:02d}" for j, m in zurueckgestellt)
            + "."
        )
        return 2

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
