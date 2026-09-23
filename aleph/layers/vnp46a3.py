"""Layer Nachtlicht: NASA VNP46A3 (Black Marble, monatlich).

Steckbrief: docs/sources/vnp46a3.md. Nutzt dieselbe Ladelogik wie alle
anderen Layer (aleph/core/io.py, aleph/core/auth.py).

Zwei Datenfelder werden mitgeführt (Entscheidung 2026-09-22: beide
speichern, Vergleich in Etappe 2):
- NearNadir_Composite_Snow_Free  (Vorschlag Hauptfeld, wenig Winkelfehler)
- AllAngle_Composite_Snow_Free   (Vorschlag Vergleichsfeld, mehr Beobachtungen)

Pro Feld und Gitterzelle (0,25°, 60 x 60 Rohpixel) wird gespeichert:
- `<feld>_mittel`: Mittelwert der gültigen Pixel (nW·cm⁻²·sr⁻¹)
- `<feld>_gueltige_pixel`: Zahl der Pixel ohne Fehlwert (Datenlage, 0-3600)
- `<feld>_num`: Mittelwert von `_Num` der gültigen Pixel (Zahl der Nächte je
  Pixel, die ins Monatskomposit eingingen)
- `<feld>_aufgefuellt_pixel`: Zahl der Pixel mit Quality=2 ("gap filled NTL
  based on historical data", Steckbrief Abschnitt 8) unter den gültigen
  Pixeln. Diese Pixel sind keine direkte Messung des Monats, sondern aus
  historischen Daten ergänzt. Sie fließen weiterhin in `_mittel` ein (wie im
  Rohprodukt), werden aber separat gezählt, damit spätere Auswertungen
  zwischen „beobachtet" und „aus historischen Daten ergänzt" unterscheiden
  können (ARCHITECTURE.md Abschnitt 4, Evidenzstufen).

Fehlwerte: Komposit −999,9 (kein NaN in der Rohdatei), `_Num` 65535.
`_Quality` wird NICHT als vollständiges Feld mitgeführt (der Steckbrief,
Abschnitt 8, zeigt an zwei Probekacheln, dass die Zahlen-Schwelle in einer
Kachel exakt passte, in einer anderen nicht erklärbar abwich); `_Num` und
die Zahl gültiger Pixel bleiben das Datenlage-Maß, ergänzt um die separate
Zählung aufgefüllter Pixel oben.

Sicherheitsnetz vor dem großen Lauf (nach Prüfung durch statistik-pruefer,
2026-09-22):
- `pruefe_vollstaendigkeit` prüft, ob ein Monat vollständig geladen wurde
  (Soll-Ist-Vergleich gegen die NASA-Abfrage selbst, nicht gegen eine feste
  Zahl - die echte Kachelzahl schwankt von Monat zu Monat, gemessen an
  Januar 2024: 460 statt der im Steckbrief notierten 536-540 im Schnitt).
- `_pruefe_ausrichtung` liest `lat`/`lon` aus jeder Kachel und prüft die
  Annahme "Zeile 0 = Nordrand, Spalte 0 = Westrand" gegen die tatsächlichen
  Koordinaten, statt sie nur aus dem Dateinamen (h/v) anzunehmen.
- `schreibe_manifest` hält die Quelldateinamen (inkl. Erzeugungszeitstempel
  im Dateinamen) fest, bevor die Rohdaten gelöscht werden.

Download-Zuverlässigkeit (nach den Hängern vom 2026-09-22, behoben
2026-09-23):
`earthaccess.download()` lädt intern mit `requests` und OHNE jedes
Zeitlimit (`session.get(url, stream=True, ...)`, kein `timeout=`). Bleibt
eine Verbindung stecken (beobachtet: CLOSE_WAIT-Sockets zu einem
CloudFront-Server), wartet Python unbegrenzt, egal wie viele parallele
Threads earthaccess intern nutzt. Vermutete Ursache der Hänger: zu viele
gleichzeitige Verbindungen zum selben NASA/CloudFront-Server (übliche,
stille Drosselung ohne Fehlermeldung). Deshalb:
- Kacheln werden einzeln geladen (`_lade_kachel`), jede in einem eigenen,
  mit `concurrent.futures` überwachten Aufruf von `earthaccess.download`
  (weiterhin dieselbe NASA-Bibliothek, ARCHITECTURE.md Abschnitt 5 - hier
  wird nur die Nebenläufigkeit und das Zeitlimit von außen gesteuert,
  keine eigene HTTP-Logik geschrieben).
- `DATEI_TIMEOUT_SEKUNDEN` (10 Minuten) ist das Zeitlimit je Kachel -
  deutlich kürzer als `DOWNLOAD_TIMEOUT_SEKUNDEN` (4 Stunden) für den
  ganzen Monat, und großzügig über der beobachteten Normaldauer einer
  einzelnen Kachel (rund 11 Sekunden im Schnitt bei einem vollständigen
  Monat mit voller Parallelität).
- Hängt oder scheitert eine Kachel, wird sie bis zu `KACHEL_MAX_VERSUCHE`
  mal erneut versucht, mit wachsender Wartezeit dazwischen
  (`KACHEL_WARTEZEIT_BASIS_SEKUNDEN`, verdoppelt sich je Versuch).
- `GLEICHZEITIGE_DOWNLOADS_STANDARD` begrenzt, wie viele Kacheln gleichzeitig
  angefragt werden (Vorschlag 2-4, siehe LOG.md 2026-09-23). Einstellbar je
  Aufruf (`lade_monat`, `download`) und über `--gleichzeitig` beim
  Hintergrund-Lauf (`vnp46a3_lauf.py`).
"""

import concurrent.futures
import re
import time
import warnings
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np
import xarray as xr

import earthaccess

from aleph.core import io
from aleph.core.auth import earthdata_login

META = {
    "name": "VNP46A3",
    "bereich": "Umwelt / menschliche Aktivität",
    "quelle": "NASA VIIRS Black Marble, LAADS DAAC, DOI 10.5067/VIIRS/VNP46A3.002",
    "lizenz": "CC0 / ohne Einschränkung laut LAADS, Quellenangabe erbeten (nicht Pflicht)",
    "native_aufloesung": "15 Bogensekunden (~500 m), Kacheln 10° x 10°",
    "ziel_aufloesung": "0,25° (60 x 60 Rohpixel je Zelle), monatlich",
    "einheit": "nW·cm⁻²·sr⁻¹",
    "zeitraum": "2013-01 bis 2025-12 (Untersuchungszeitraum ALEPH, Entscheidung E3)",
    "bekannte_schwaechen": (
        "Starke Winkelabhängigkeit; Schnee verfälscht Nachtlicht; wenig "
        "gültige Nächte im Sommer in hohen Breiten; Suomi-NPP-Auslieferung "
        "endet 2026-11-01 (danach ggf. VJ146A3/NOAA-20 prüfen)."
    ),
    "details": "docs/sources/vnp46a3.md",
}

FELD_TRIPEL = {
    "near_nadir": (
        "NearNadir_Composite_Snow_Free",
        "NearNadir_Composite_Snow_Free_Num",
        "NearNadir_Composite_Snow_Free_Quality",
    ),
    "allangle": (
        "AllAngle_Composite_Snow_Free",
        "AllAngle_Composite_Snow_Free_Num",
        "AllAngle_Composite_Snow_Free_Quality",
    ),
}
HDF_GRUPPE = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields"
FEHLWERT_KOMPOSIT = -999.9
FEHLWERT_NUM = 65535
QUALITAET_AUFGEFUELLT = 2

PIXEL_PRO_KACHEL = 2400
ZELLEN_PRO_KACHEL = 40
PIXEL_PRO_ZELLE = 60
GITTER_BREITE = 720  # Zeilen, 0,25°, Zeile 0 = 90°N
GITTER_LAENGE = 1440  # Spalten, 0,25°, Spalte 0 = 180°W
ZELLGROESSE = 0.25

# Zeitlimit für den Download eines ganzen Monats. Großzügig über der
# beobachteten Normaldauer (92,8 Minuten für einen vollständigen Monat,
# gemessen 2026-09-22), damit legitime Langsamkeit nicht abgebrochen wird -
# aber begrenzt, weil eine hängengebliebene Netzwerkverbindung sonst
# unbegrenzt weiterlaufen würde (ebenfalls beobachtet, 2026-09-22). Dient
# seit 2026-09-23 als Sicherheitsnetz für den GANZEN Monat; das eigentliche
# Zeitlimit pro Kachel ist DATEI_TIMEOUT_SEKUNDEN (siehe unten).
DOWNLOAD_TIMEOUT_SEKUNDEN = 4 * 60 * 60  # 4 Stunden

# Zeitlimit je einzelner Kachel. earthaccess.download() setzt selbst kein
# Zeitlimit für die HTTP-Anfrage (session.get ohne timeout=), eine
# hängengebliebene Verbindung würde sonst unbegrenzt warten. 10 Minuten sind
# großzügig über der beobachteten Normaldauer einer Kachel (~11 Sekunden im
# Schnitt bei vollem Durchsatz), aber kurz genug, um einen echten Hänger
# rasch zu erkennen und neu zu versuchen.
DATEI_TIMEOUT_SEKUNDEN = 10 * 60  # 10 Minuten

# Wie oft eine einzelne Kachel neu versucht wird, bevor der Monat als
# gescheitert gilt.
KACHEL_MAX_VERSUCHE = 4

# Wartezeit vor dem ersten erneuten Versuch; verdoppelt sich je Versuch
# (20 s, 40 s, 80 s), damit eine kurzzeitige Drosselung Zeit hat, nachzulassen.
KACHEL_WARTEZEIT_BASIS_SEKUNDEN = 20

# Zahl gleichzeitiger Kachel-Downloads. Vermutete Ursache der Hänger vom
# 2026-09-22: zu viele gleichzeitige Verbindungen zum selben NASA/CloudFront-
# Server (stille Drosselung ohne Fehlermeldung). Vorschlag 2-4 (LOG.md
# 2026-09-23); bei erneuten Hängern hier eine kleinere Zahl eintragen statt
# zu raten.
GLEICHZEITIGE_DOWNLOADS_STANDARD = 3

_KACHEL_HV = re.compile(r"\.h(\d{2})v(\d{2})\.")
_KACHEL_DATUM = re.compile(r"\.A(\d{4})(\d{3})\.")


class KachelName(RuntimeError):
    """Der Dateiname passt nicht zum erwarteten VNP46A3-Muster."""


class KachelAusrichtung(RuntimeError):
    """Die lat/lon-Werte einer Kachel passen nicht zur angenommenen Ausrichtung."""


class MonatUnvollstaendig(RuntimeError):
    """Es wurden weniger Kacheln heruntergeladen, als NASA für den Monat meldet."""


class DownloadHaengt(RuntimeError):
    """Der Download hat länger als sein Zeitlimit nicht mehr reagiert."""


def _kachel_position(pfad: Path) -> tuple[int, int, int, int]:
    """Globale Zeilen-/Spalten-Startposition (0,25°-Gitter) einer Kachel, plus h, v.

    h/v aus dem Dateinamen, z. B. h19v03. Kachel h=0 beginnt bei 180°W,
    v=0 bei 90°N (geprüft an der Probekachel h19v03 = 10-20°O, 50-60°N,
    docs/sources/vnp46a3.md Abschnitt 14, und zusätzlich zur Laufzeit gegen
    lat/lon jeder Kachel geprüft, siehe `_pruefe_ausrichtung`).
    """
    treffer = _KACHEL_HV.search(pfad.name)
    if not treffer:
        raise KachelName(f"Kann h/v nicht aus Dateinamen lesen: {pfad.name}")
    h, v = int(treffer.group(1)), int(treffer.group(2))
    return v * ZELLEN_PRO_KACHEL, h * ZELLEN_PRO_KACHEL, h, v


def _kachel_jahr_monat(pfad: Path) -> tuple[int, int]:
    """Jahr und Monat einer Kachel aus dem Dateinamen (A{Jahr}{Tag-im-Jahr})."""
    treffer = _KACHEL_DATUM.search(pfad.name)
    if not treffer:
        raise KachelName(f"Kann Datum nicht aus Dateinamen lesen: {pfad.name}")
    jahr, tag = int(treffer.group(1)), int(treffer.group(2))
    datum = date(jahr, 1, 1) + timedelta(days=tag - 1)
    return datum.year, datum.month


def _pruefe_ausrichtung(gruppe, pfad: Path, h: int, v: int) -> None:
    """Prüft Zeile-0-ist-Nordrand / Spalte-0-ist-Westrand an den echten lat/lon-Werten.

    Nicht nur eine Annahme aus dem Dateinamen: `lat`/`lon` sind 1D-Felder je
    Kachel (gemessen, 2400 Werte). lat[0] muss der Nordrand sein und fallend
    verlaufen, lon[0] der Westrand und steigend, jeweils zur h/v-Position
    passend (Toleranz 0,01°, deutlich unter der Pixelgröße von 15 Bogensek.).
    """
    lat = gruppe["lat"][:]
    lon = gruppe["lon"][:]
    erwartet_lat0 = 90 - v * 10
    erwartet_lon0 = -180 + h * 10
    fehler = []
    if abs(float(lat[0]) - erwartet_lat0) > 0.01:
        fehler.append(f"lat[0]={lat[0]}, erwartet {erwartet_lat0}")
    if lat[0] <= lat[-1]:
        fehler.append("lat ist nicht fallend (Zeile 0 wäre dann nicht der Nordrand)")
    if abs(float(lon[0]) - erwartet_lon0) > 0.01:
        fehler.append(f"lon[0]={lon[0]}, erwartet {erwartet_lon0}")
    if lon[0] >= lon[-1]:
        fehler.append("lon ist nicht steigend (Spalte 0 wäre dann nicht der Westrand)")
    if fehler:
        raise KachelAusrichtung(f"{pfad.name}: unerwartete Ausrichtung: {'; '.join(fehler)}")


def _lies_kachel(pfad: Path) -> dict[str, np.ndarray]:
    """Liest eine Kachel und verkleinert sie auf 40 x 40 Gitterzellen.

    Fehlwerte werden vor jedem Mittelwert maskiert (−999,9 beim Komposit,
    65535 bei `_Num`). Rückgabe je Feldpaar: `<name>_mittel`,
    `<name>_gueltige_pixel`, `<name>_num`, `<name>_aufgefuellt_pixel`, je
    40 x 40.
    """
    ergebnis: dict[str, np.ndarray] = {}
    block_form = (ZELLEN_PRO_KACHEL, PIXEL_PRO_ZELLE, ZELLEN_PRO_KACHEL, PIXEL_PRO_ZELLE)
    with h5py.File(pfad, "r") as datei:
        gruppe = datei[HDF_GRUPPE]
        for name, (komposit_feld, num_feld, qualitaet_feld) in FELD_TRIPEL.items():
            komposit = gruppe[komposit_feld][:].astype("float32")
            num = gruppe[num_feld][:].astype("float32")
            qualitaet = gruppe[qualitaet_feld][:]
            if komposit.shape != (PIXEL_PRO_KACHEL, PIXEL_PRO_KACHEL):
                raise ValueError(
                    f"{pfad.name}: unerwartete Form {komposit.shape} bei {komposit_feld}"
                )
            # Vergleich mit dem exakten float32-Fehlwert der Datei (nicht mit
            # dem float64-Literal), damit Rundung beim Hoch-/Herunterrechnen
            # keine Fehlwert-Pixel übersehen lässt.
            fehlwert_f32 = np.float32(FEHLWERT_KOMPOSIT)
            gueltig = (komposit != fehlwert_f32) & (num != FEHLWERT_NUM)
            komposit_masked = np.where(gueltig, komposit, np.nan).reshape(block_form)
            num_masked = np.where(gueltig, num, np.nan).reshape(block_form)
            gueltig_bloecke = gueltig.reshape(block_form)
            aufgefuellt_bloecke = (
                (qualitaet == QUALITAET_AUFGEFUELLT) & gueltig
            ).reshape(block_form)

            with np.errstate(invalid="ignore"), warnings.catch_warnings():
                # Zellen ohne einen einzigen gültigen Pixel sind erwartbar
                # (z. B. am Kachelrand); "Mean of empty slice" ist dann kein Fehler.
                warnings.filterwarnings("ignore", message="Mean of empty slice")
                mittel = np.nanmean(komposit_masked, axis=(1, 3))
                num_mittel = np.nanmean(num_masked, axis=(1, 3))
            gueltige_pixel = gueltig_bloecke.sum(axis=(1, 3)).astype("int16")
            aufgefuellte_pixel = aufgefuellt_bloecke.sum(axis=(1, 3)).astype("int16")

            ergebnis[f"{name}_mittel"] = mittel.astype("float32")
            ergebnis[f"{name}_gueltige_pixel"] = gueltige_pixel
            ergebnis[f"{name}_num"] = num_mittel.astype("float32")
            ergebnis[f"{name}_aufgefuellt_pixel"] = aufgefuellte_pixel
    return ergebnis


def _monatsspanne(jahr: int, monat: int) -> tuple[str, str]:
    letzter_tag = monthrange(jahr, monat)[1]
    return f"{jahr:04d}-{monat:02d}-01", f"{jahr:04d}-{monat:02d}-{letzter_tag:02d}"


def _lade_kachel(
    granule,
    ziel_ordner: Path,
    datei_timeout_sekunden: float = DATEI_TIMEOUT_SEKUNDEN,
    max_versuche: int = KACHEL_MAX_VERSUCHE,
    wartezeit_basis_sekunden: float = KACHEL_WARTEZEIT_BASIS_SEKUNDEN,
) -> Path:
    """Lädt eine einzelne Kachel über `earthaccess.download`, mit eigenem
    Zeitlimit und Wiederholung bei Hänger oder Fehler.

    `earthaccess.download` selbst kennt kein Zeitlimit (siehe Moduldoku
    oben). Jeder Versuch läuft deshalb in einem eigenen Thread; reagiert er
    nicht innerhalb von `datei_timeout_sekunden`, wird dieser Thread
    aufgegeben (er kann nicht sauber beendet werden, sein Ergebnis wird nur
    ignoriert) und ein neuer Versuch gestartet, nach wachsender Wartezeit
    (`wartezeit_basis_sekunden`, verdoppelt sich je Versuch). Nach
    `max_versuche` erfolglosen Versuchen wird der letzte Fehler weitergereicht.
    """
    letzter_fehler: Exception | None = None
    for versuch in range(1, max_versuche + 1):
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(earthaccess.download, [granule], str(ziel_ordner))
        try:
            ergebnis = future.result(timeout=datei_timeout_sekunden)
            pool.shutdown(wait=False)
            return Path(ergebnis[0])
        except concurrent.futures.TimeoutError:
            pool.shutdown(wait=False, cancel_futures=True)
            letzter_fehler = DownloadHaengt(
                f"Kachel reagiert seit über {datei_timeout_sekunden / 60:.0f} "
                f"Minuten nicht mehr (Versuch {versuch}/{max_versuche})."
            )
        except Exception as fehler:  # bewusst breit: jeder Fehler löst einen neuen Versuch aus
            pool.shutdown(wait=False)
            letzter_fehler = fehler
        if versuch < max_versuche:
            wartezeit = wartezeit_basis_sekunden * (2 ** (versuch - 1))
            time.sleep(wartezeit)
    assert letzter_fehler is not None
    raise letzter_fehler


def lade_monat(
    jahr: int,
    monat: int,
    ziel_ordner: Path,
    gleichzeitige_downloads: int = GLEICHZEITIGE_DOWNLOADS_STANDARD,
) -> list[Path]:
    """Lädt alle VNP46A3-Kacheln eines Monats global nach `ziel_ordner`.

    Meldet sich vorher bei NASA Earthdata an (dieselbe Ladelogik wie alle
    Layer, aleph/core/auth.py). Bricht mit klarer Meldung ab, wenn der
    Login fehlschlägt.

    Jede Kachel wird einzeln geladen, mit eigenem Zeitlimit und
    Wiederholung bei Hänger (`_lade_kachel`), höchstens
    `gleichzeitige_downloads` Kacheln gleichzeitig (Vorschlag 2-4, siehe
    Moduldoku oben - vermutete Ursache der früheren Hänger war zu viel
    Nebenläufigkeit zum selben NASA/CloudFront-Server).

    Prüft danach die Vollständigkeit: die Zahl der heruntergeladenen
    Kacheln muss genau der Zahl entsprechen, die NASA für diesen Monat
    meldet (`pruefe_vollstaendigkeit`). Eine feste Zahl (z. B. "536-540")
    wäre hier eine Scheinpräzision: Die tatsächliche Kachelzahl schwankt
    real von Monat zu Monat (gemessen: Januar 2024 hat nur 460 Kacheln,
    nicht 536-540 wie der grobe Mehrjahres-Schnitt im Steckbrief). Der
    einzig robuste Vergleich ist gegen die Quelle selbst, nicht gegen einen
    angenommenen Erfahrungswert.

    Bricht außerdem mit `DownloadHaengt` ab, wenn der GANZE Monat länger
    als `DOWNLOAD_TIMEOUT_SEKUNDEN` (4 Stunden) braucht - ein Sicherheitsnetz
    über der Kachel-Wiederholung, falls z. B. sehr viele Kacheln gleichzeitig
    Probleme machen. Oder wenn einzelne Kacheln auch nach allen Versuchen
    nicht geladen werden konnten.
    """
    if not earthdata_login():
        raise RuntimeError("NASA-Earthdata-Login fehlgeschlagen. Zugangsdaten in .env prüfen.")
    start, ende = _monatsspanne(jahr, monat)
    treffer = earthaccess.search_data(
        short_name="VNP46A3",
        version="2",
        temporal=(start, ende),
        bounding_box=(-180, -90, 180, 90),
        count=1000,
    )
    # Die CMR-Zeitsuche kann Kacheln des Vor- und Folgemonats mitliefern,
    # deren Zeitfenster den Rand berührt. Nur der angefragte Monat bleibt.
    treffer = [
        g
        for g in treffer
        if any(_passt_zum_monat(link, jahr, monat) for link in g.data_links())
    ]
    ziel_ordner.mkdir(parents=True, exist_ok=True)

    start_zeit = time.time()
    frist = start_zeit + DOWNLOAD_TIMEOUT_SEKUNDEN
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, gleichzeitige_downloads))
    future_zu_granule = {pool.submit(_lade_kachel, g, ziel_ordner): g for g in treffer}

    dateien: list[Path] = []
    fehlgeschlagen: list[tuple[object, Exception]] = []
    try:
        for future in concurrent.futures.as_completed(future_zu_granule, timeout=max(frist - time.time(), 0)):
            granule = future_zu_granule[future]
            try:
                dateien.append(future.result())
            except Exception as fehler:
                fehlgeschlagen.append((granule, fehler))
    except concurrent.futures.TimeoutError:
        pool.shutdown(wait=False, cancel_futures=True)
        raise DownloadHaengt(
            f"{jahr:04d}-{monat:02d}: Download reagiert seit über "
            f"{DOWNLOAD_TIMEOUT_SEKUNDEN // 60} Minuten nicht mehr "
            f"({len(dateien)} von {len(treffer)} Kacheln fertig). "
            "scripts/vnp46a3_start.sh erneut ausführen - setzt beim letzten "
            "fertigen Monat fort. Hängt es wieder, eine kleinere Zahl bei "
            "--gleichzeitig probieren."
        ) from None
    pool.shutdown(wait=False)

    if fehlgeschlagen:
        beispiel_fehler = fehlgeschlagen[0][1]
        raise DownloadHaengt(
            f"{jahr:04d}-{monat:02d}: {len(fehlgeschlagen)} von {len(treffer)} "
            f"Kacheln auch nach je {KACHEL_MAX_VERSUCHE} Versuchen nicht geladen. "
            f"Beispiel: {beispiel_fehler}. Eine kleinere Zahl bei --gleichzeitig "
            "probieren, statt zu raten."
        )

    pruefe_vollstaendigkeit(jahr, monat, len(treffer), dateien)
    return dateien


def _passt_zum_monat(link: str, jahr: int, monat: int) -> bool:
    treffer = _KACHEL_DATUM.search(link)
    if not treffer:
        return False
    datum = date(int(treffer.group(1)), 1, 1) + timedelta(days=int(treffer.group(2)) - 1)
    return datum.year == jahr and datum.month == monat


def pruefe_vollstaendigkeit(jahr: int, monat: int, erwartete_anzahl: int, kachel_dateien: list[Path]) -> None:
    """Bricht mit `MonatUnvollstaendig` ab, wenn nicht alle gemeldeten Kacheln da sind.

    `erwartete_anzahl` ist die Zahl der Kacheln, die NASA (CMR-Suche) für
    diesen Monat tatsächlich meldet - kein angenommener Erfahrungswert.
    Ohne diese Prüfung würde ein Netzwerkfehler, der nur einen Teil der
    Kacheln liefert, wie eine echte Datenlücke (Polarnacht, Wolken) aussehen
    - und wäre nach dem Löschen der Rohdaten nicht mehr zu unterscheiden.
    """
    if len(kachel_dateien) != erwartete_anzahl:
        raise MonatUnvollstaendig(
            f"{jahr:04d}-{monat:02d}: {len(kachel_dateien)} von {erwartete_anzahl} "
            "bei NASA gemeldeten Kacheln wurden heruntergeladen. Rohdaten "
            "bleiben zur Prüfung erhalten, nichts wurde in den Würfel "
            "geschrieben."
        )


def schreibe_manifest(jahr: int, monat: int, kachel_dateien: list[Path]) -> Path:
    """Hält die verarbeiteten Quelldateinamen fest, bevor die Rohdaten gelöscht werden.

    Die Erzeugungszeitstempel von NASA stehen im Dateinamen selbst
    (docs/sources/vnp46a3.md Abschnitt 10: eine spätere Neuerzeugung kann
    denselben Monat ändern, deshalb ist die genaue Version wichtig).
    """
    ziel = io.aleph_data_dir() / "protokoll" / "manifeste" / "vnp46a3" / f"{jahr:04d}-{monat:02d}.txt"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    namen = sorted(p.name for p in kachel_dateien)
    ziel.write_text("\n".join(namen) + "\n", encoding="utf-8")
    return ziel


def verkleinere_monat(kachel_dateien: list[Path]) -> xr.Dataset:
    """Baut aus den Kacheln eines Monats ein globales 0,25°-Gitter (ein Zeitschritt)."""
    if not kachel_dateien:
        raise ValueError("Keine Kacheln übergeben.")
    jahr, monat = _kachel_jahr_monat(kachel_dateien[0])

    variablen: dict[str, np.ndarray] = {}
    for name in FELD_TRIPEL:
        variablen[f"{name}_mittel"] = np.full((GITTER_BREITE, GITTER_LAENGE), np.nan, dtype="float32")
        variablen[f"{name}_gueltige_pixel"] = np.zeros((GITTER_BREITE, GITTER_LAENGE), dtype="int16")
        variablen[f"{name}_num"] = np.full((GITTER_BREITE, GITTER_LAENGE), np.nan, dtype="float32")
        variablen[f"{name}_aufgefuellt_pixel"] = np.zeros((GITTER_BREITE, GITTER_LAENGE), dtype="int16")

    for pfad in kachel_dateien:
        zeile0, spalte0, h, v = _kachel_position(pfad)
        with h5py.File(pfad, "r") as datei:
            _pruefe_ausrichtung(datei[HDF_GRUPPE], pfad, h, v)
        bloecke = _lies_kachel(pfad)
        for schluessel, block in bloecke.items():
            variablen[schluessel][zeile0 : zeile0 + ZELLEN_PRO_KACHEL, spalte0 : spalte0 + ZELLEN_PRO_KACHEL] = block

    breite = 90 - ZELLGROESSE / 2 - np.arange(GITTER_BREITE) * ZELLGROESSE
    laenge = -180 + ZELLGROESSE / 2 + np.arange(GITTER_LAENGE) * ZELLGROESSE
    zeit = [np.datetime64(f"{jahr:04d}-{monat:02d}-01")]

    daten_vars = {
        schluessel: (("zeit", "breite", "laenge"), werte[np.newaxis, :, :])
        for schluessel, werte in variablen.items()
    }
    return xr.Dataset(
        data_vars=daten_vars,
        coords={"zeit": zeit, "breite": breite, "laenge": laenge},
        attrs={"quelle": META["quelle"], "einheit_mittel": META["einheit"]},
    )


def _wuerfel_pfad() -> Path:
    return io.wuerfel_pfad("vnp46a3.zarr")


def vorhandene_monate() -> set[tuple[int, int]]:
    """Monate, die bereits im Würfel auf der SSD stehen (für den Neustart)."""
    pfad = _wuerfel_pfad()
    if not pfad.exists():
        return set()
    ds = xr.open_zarr(pfad)
    try:
        zeiten = ds["zeit"].values
    finally:
        ds.close()
    return {(np.datetime64(z, "M").astype(object).year, np.datetime64(z, "M").astype(object).month) for z in zeiten}


def schreibe_in_wuerfel(monatsdaten: xr.Dataset) -> None:
    """Hängt einen Monat an den Datenwürfel auf der SSD an (oder legt ihn neu an)."""
    pfad = _wuerfel_pfad()
    if pfad.exists():
        monatsdaten.to_zarr(pfad, mode="a", append_dim="zeit")
    else:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        monatsdaten.to_zarr(pfad, mode="w")


# --- Architektur-Vertrag (ARCHITECTURE.md Abschnitt 5) ----------------------
# download() und to_cube() sind die vorgeschriebenen Einstiegspunkte für
# einzelne, kleinere Läufe. Der Hintergrund-Lauf (viele Monate, mit
# Speicherwächter, Vollständigkeitsprüfung, Fortsetzung, Manifest und
# Protokoll) nutzt die Bausteine oben direkt, siehe
# aleph/layers/vnp46a3_lauf.py.


def download(
    start: str,
    ende: str,
    gleichzeitige_downloads: int = GLEICHZEITIGE_DOWNLOADS_STANDARD,
) -> list[Path]:
    """Lädt Rohdaten für den Zeitraum [start, ende] (Format 'JJJJ-MM') nach der SSD."""
    dateien: list[Path] = []
    jahr, monat = (int(t) for t in start.split("-"))
    end_jahr, end_monat = (int(t) for t in ende.split("-"))
    while (jahr, monat) <= (end_jahr, end_monat):
        ziel = io.rohdaten_pfad("vnp46a3", f"{jahr:04d}-{monat:02d}")
        dateien += lade_monat(jahr, monat, ziel, gleichzeitige_downloads=gleichzeitige_downloads)
        monat += 1
        if monat > 12:
            monat, jahr = 1, jahr + 1
    return dateien


def to_cube() -> xr.Dataset:
    """Baut den Würfel aus allen momentan unter raw/vnp46a3/ vorhandenen Monaten."""
    basis = io.rohdaten_pfad("vnp46a3")
    monats_ordner = sorted(p for p in basis.iterdir() if p.is_dir()) if basis.exists() else []
    monats_datasets = [verkleinere_monat(sorted(p.glob("*.h5"))) for p in monats_ordner]
    return xr.concat(monats_datasets, dim="zeit") if monats_datasets else xr.Dataset()
