"""Machbarkeitsprüfung: liefert Google Earth Engine dieselben Nachtlichtwerte wie der VNP46A3-Würfel?

Bericht: berichte/2026-09-27_earth-engine-pruefung.md. Das ist KEIN Layer und
ändert nichts am Würfel oder am Download. Es wird nur gelesen (Würfel) und
verglichen; das Ergebnis aus Earth Engine liegt auf der SSD unter
`vergleich/earth_engine/` (Pfad über aleph/core/io.py, wie alle Daten).

Zwei Kandidaten, beide in Earth Engine auf genau das 0,25°-Raster des Würfels
zusammengefasst (Raster aus `aleph.layers.vnp46a3`, nicht neu festgelegt);
heruntergeladen wird nur das Ergebnis je Zelle:

A  `NASA/VIIRS/002/VNP46A2` (tägliche Black-Marble-Werte, Collection 2 wie
   der Würfel). Monatswert möglichst nahe am VNP46A3-Verfahren (User Guide
   Collection 2.0, Abschnitt 2.3, im Originaltext gelesen):
   - Tageswert `DNB_BRDF_Corrected_NTL` (nicht aufgefüllt), nur wenn
     `Mandatory_Quality_Flag` = 0 (NASA-Tabelle 9: „High-quality“),
     `Snow_Flag` = 0 (schneefrei, wie „Snow_Free“), Wolkenmaske Bits 6-7
     „sicher klar“ oder „wahrscheinlich klar“, Bit 0 „Nacht“;
   - je Pixel Ausreißer außerhalb Q1 − 1,5·IQR … Q3 + 1,5·IQR entfernt
     (Tukey, wie im User Guide), Mittelwert der übrigen Nächte;
   - Pixelwert unter 0,5 nW·cm⁻²·sr⁻¹ auf 0 gesetzt (wie im User Guide);
   - Pixel ohne eine einzige verbleibende Nacht: keine Daten.
   NICHT nachbaubar, nur angenähert (siehe Bericht): welche Qualitätswerte
   NASA wirklich zulässt (nur 0? auch 02 = hoher Sonnenzenitwinkel?), wie die
   Quartile gerechnet werden, und die Blickwinkelklassen (VNP46A2 in Earth
   Engine hat kein Winkelband; nur „AllAngle“ ist vergleichbar). Die
   historische Auffüllung (Quality 2) wird nicht nachgebaut; verglichen wird
   deshalb mit `allangle_mittel_beobachtet`.

B  `NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG` (Monatskomposit der Earth Observation
   Group, Colorado School of Mines): `avg_rad`, nur Pixel mit `cf_cvg` ≥ 1.
   Grundsätzlich anderes Verfahren (keine Mond-/BRDF-Korrektur, keine
   Trennung nach Schnee, keine Nullsetzung unter 0,5).

Zellwert = Mittel über die Pixel mit Daten (flächengewichtet, Earth-Engine
`reduceResolution`), dazu der Anteil der Pixel mit Daten („anteil“).

Die Vergleichskriterien K1-K6 (`KRITERIEN`) wurden am 2026-09-27, 16:24 UTC
festgelegt, bevor ein Earth-Engine-Wert berechnet wurde, und dürfen nicht
nachträglich angepasst werden.

Zeitraum: Monate ab 2023-01 werden verweigert (Validierungs-/Endtestzeitraum).

Aufrufe (im Projektordner):
    .venv/bin/python -m aleph.quellenvergleich.ee_nachtlicht laden --monat 2018-10 --kandidat A
    .venv/bin/python -m aleph.quellenvergleich.ee_nachtlicht vergleichen --monat 2018-10
    .venv/bin/python -m aleph.quellenvergleich.ee_nachtlicht karte --monat 2018-10 --ziel berichte/bilder/x.png
"""

from __future__ import annotations

import argparse
import concurrent.futures
import io as bytes_io
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from aleph.core import io
from aleph.layers import vnp46a3, vnp46a3_regionen

# --- Quellen --------------------------------------------------------------

A_ID = "NASA/VIIRS/002/VNP46A2"
A_NTL = "DNB_BRDF_Corrected_NTL"
B_ID = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG"
KANDIDATEN = {"A": A_ID, "B": B_ID}

RAUSCHSCHWELLE = 0.5  # User Guide Abschnitt 2.3: Kompositwerte darunter auf 0
TUKEY_FAKTOR = 1.5  # User Guide Abschnitt 2.3: Q1 - 1,5·IQR bis Q3 + 1,5·IQR
FEHLWERT = -9999.0  # „keine Daten“ in der Übertragung (Earth Engine liefert sonst 0)
REGION = vnp46a3_regionen.AFRIKA_EUROPA_ASIEN
# Höchstzahl Eingangspixel je Zelle für reduceResolution: 60 × 60 = 3600 bei A,
# bis 61 × 61 = 3721 bei B (um einen halben Pixel verschobenes Raster).
MAX_PIXEL_JE_ZELLE = 4096
# Zeitlimit je Earth-Engine-Anfrage. Nachgetragen 2026-09-27: Der erste Lauf für A
# hing mit drei Anfragen ohne Antwort über 40 Minuten (kein Byte in 60 s), weil
# die Bibliothek ohne Zeitlimit wartet. Ein A-Block brauchte sonst etwa 70 s.
ANFRAGE_ZEITLIMIT_SEKUNDEN = 600
# Wiederholung je Block (Netzwerkregel CLAUDE.md): 4 Versuche, Pausen 5, 10, 20 s.
# Die Bibliothek wiederholt HTTP 429/5xx schon selbst (earth_engine.BIBLIOTHEK_WIEDERHOLUNGEN);
# diese Schleife fängt zusätzlich Zeitüberschreitungen und Verbindungsabbrüche ab.
# Im schlimmsten Fall wartet ein Block 4 × 600 s + 35 s, danach fehlt er und der Lauf
# schreibt kein Ergebnis (siehe lade_region). Jede Wiederholung wird gemeldet.
BLOCK_VERSUCHE = 4
BLOCK_PAUSE_BASIS_SEKUNDEN = 5  # verdoppelt sich je Versuch

# --- Kriterien (festgelegt 2026-09-27 16:24 UTC, vor dem Rechnen; nicht ändern) ---

KLASSE_DUNKEL_BIS = 0.5  # dunkel < 0,5
KLASSE_MITTEL_BIS = 5.0  # mittel 0,5 bis < 5; hell ≥ 5
LOG_ZUSATZ = 0.1  # log10(x + 0,1), Werte unter 0 vorher auf 0
KRITERIEN = {
    "K1_r_log_min": 0.95,
    "K2a_median_q": (0.90, 1.10),
    "K2b_median_abw_max": 0.15,
    "K3_anteil_faktor2_max": 0.05,
    "K4_dunkel_falsches_licht_ab": 1.0,
    "K4_anteil_max": 0.02,
    "K5_gleich_min": 0.95,
    "K5_fehlt_im_kandidat_max": 0.05,
    "K6_stadt_q": (0.67, 1.5),
    "K6_sahara_max": 0.5,
}
STICHPROBEN = {
    "Berlin": (52.52, 13.40),
    "Paris": (48.86, 2.35),
    "Kairo": (30.04, 31.24),
    "Lagos": (6.46, 3.39),
    "Delhi": (28.61, 77.21),
    "Sahara": (25.0, 25.0),
}
WUERFEL_WERT = "allangle_mittel_beobachtet"
WUERFEL_PIXEL = "allangle_beobachtete_pixel"
WUERFEL_WERT_MIT_AUFFUELLUNG = "allangle_mittel"


class ZeitraumGesperrt(ValueError):
    """Monate ab 2023 sind Validierungs-/Endtestzeitraum (CLAUDE.md)."""


def pruefe_zeitraum(jahr: int, monat: int) -> None:
    if (jahr, monat) >= (2023, 1):
        raise ZeitraumGesperrt(
            f"{jahr:04d}-{monat:02d} liegt im Validierungs-/Endtestzeitraum 2023–2025 und wird nicht verglichen."
        )


# --- Raster (aus dem Code des Nachtlicht-Layers) ---------------------------


def raster_transform() -> list[float]:
    """Affine Abbildung des Würfelrasters (EPSG:4326): [Breite x, 0, West, 0, -Höhe y, Nord].

    Aus den Konstanten in aleph.layers.vnp46a3 abgeleitet und gegen deren
    Zellmitten geprüft (Zeile 0 = Nordrand 90°, Spalte 0 = Westrand -180°).
    """
    z = vnp46a3.ZELLGROESSE
    breite, laenge = vnp46a3._gitter_koordinaten()
    nord = float(breite[0] + z / 2)
    west = float(laenge[0] - z / 2)
    if not (math.isclose(nord, 90.0) and math.isclose(west, -180.0)):
        raise ValueError(f"Würfelraster beginnt nicht bei 90°N/180°W (nord={nord}, west={west}).")
    if len(breite) != vnp46a3.GITTER_BREITE or len(laenge) != vnp46a3.GITTER_LAENGE:
        raise ValueError("Würfelraster hat nicht die erwartete Größe.")
    return [z, 0.0, west, 0.0, -z, nord]


def zelle_von(breite: float, laenge: float) -> tuple[int, int]:
    """Zeile und Spalte der Würfelzelle, in der ein Punkt liegt."""
    z = vnp46a3.ZELLGROESSE
    return int(math.floor((90.0 - breite) / z)), int(math.floor((laenge + 180.0) / z))


def region_maske() -> np.ndarray:
    return vnp46a3_regionen.zellmaske(
        vnp46a3_regionen.lies_region(REGION), vnp46a3.GITTER_BREITE, vnp46a3.GITTER_LAENGE
    )


# --- Earth Engine: Monatswert und Zusammenfassung auf das Raster ----------


def _monatsgrenzen(jahr: int, monat: int) -> tuple[str, str]:
    folge = (jahr + 1, 1) if monat == 12 else (jahr, monat + 1)
    return f"{jahr:04d}-{monat:02d}-01", f"{folge[0]:04d}-{folge[1]:02d}-01"


def kandidat_a(ee, jahr: int, monat: int):
    """VNP46A2-Tageswerte → Monatswert je 500-m-Pixel. Rückgabe (Wert, gültig, native Projektion)."""
    start, ende = _monatsgrenzen(jahr, monat)
    tage = ee.ImageCollection(A_ID).filterDate(start, ende)
    nativ = tage.first().select(A_NTL).projection()

    def vorbereiten(bild):
        qualitaet = bild.select("Mandatory_Quality_Flag")
        schnee = bild.select("Snow_Flag")
        wolke = bild.select("QF_Cloud_Mask")
        klar = wolke.rightShift(6).bitwiseAnd(3).lte(1)
        nacht = wolke.bitwiseAnd(1).eq(0)
        ok = qualitaet.eq(0).And(schnee.eq(0)).And(klar).And(nacht)
        return bild.select([A_NTL], ["ntl"]).updateMask(ok)

    gut = tage.map(vorbereiten)
    quartile = gut.reduce(ee.Reducer.percentile([25, 75]))
    q1 = quartile.select("ntl_p25")
    q3 = quartile.select("ntl_p75")
    iqr = q3.subtract(q1)
    unten = q1.subtract(iqr.multiply(TUKEY_FAKTOR))
    oben = q3.add(iqr.multiply(TUKEY_FAKTOR))

    def ohne_ausreisser(bild):
        ntl = bild.select("ntl")
        return ntl.updateMask(ntl.gte(unten).And(ntl.lte(oben)))

    rest = gut.map(ohne_ausreisser)
    anzahl = rest.count().unmask(0)
    mittel = rest.mean()
    wert = mittel.where(mittel.lt(RAUSCHSCHWELLE), 0).updateMask(anzahl.gte(1))
    return wert, anzahl.gte(1), nativ


def kandidat_b(ee, jahr: int, monat: int):
    """VCMCFG-Monatskomposit. Rückgabe (Wert, gültig, native Projektion)."""
    start, ende = _monatsgrenzen(jahr, monat)
    bild = ee.ImageCollection(B_ID).filterDate(start, ende).first()
    nativ = bild.select("avg_rad").projection()
    gueltig = bild.select("cf_cvg").gte(1)
    return bild.select("avg_rad").updateMask(gueltig), gueltig, nativ


def auf_raster(ee, wert, gueltig, nativ):
    """Fasst Pixel flächengewichtet auf das Würfelraster zusammen: Bänder `wert` und `anteil`."""
    ziel = {"crs": "EPSG:4326", "crsTransform": raster_transform()}
    mittel = (
        wert.setDefaultProjection(nativ)
        .reduceResolution(ee.Reducer.mean(), maxPixels=MAX_PIXEL_JE_ZELLE)
        .reproject(**ziel)
        .unmask(FEHLWERT)
        .rename("wert")
    )
    anteil = (
        gueltig.unmask(0)
        .toFloat()
        .setDefaultProjection(nativ)
        .reduceResolution(ee.Reducer.mean(), maxPixels=MAX_PIXEL_JE_ZELLE)
        .reproject(**ziel)
        .unmask(0)
        .rename("anteil")
    )
    return ee.Image.cat([mittel, anteil]).toFloat()


def monatsbild(ee, kandidat: str, jahr: int, monat: int):
    pruefe_zeitraum(jahr, monat)
    if kandidat == "A":
        return auf_raster(ee, *kandidat_a(ee, jahr, monat))
    if kandidat == "B":
        return auf_raster(ee, *kandidat_b(ee, jahr, monat))
    raise ValueError(f"Unbekannter Kandidat {kandidat!r} (A oder B).")


@dataclass
class Messung:
    anfragen: int = 0
    wiederholungen: int = 0
    bytes: int = 0
    sekunden_summe: float = 0.0  # Summe der Anfragezeiten (Rechenzeit bei Google + Übertragung)
    sekunden_wand: float = 0.0  # tatsächlich verstrichene Zeit (mit Parallelität)
    wiederverwendet: int = 0  # Blöcke aus einem früheren, abgebrochenen Lauf
    fehler: list[str] = field(default_factory=list)


def _block_anfrage(ee, bild, zeile0: int, spalte0: int, hoehe: int, breite: int):
    z = vnp46a3.ZELLGROESSE
    return {
        "expression": bild,
        "fileFormat": "NPY",
        "grid": {
            "dimensions": {"width": breite, "height": hoehe},
            "affineTransform": {
                "scaleX": z, "shearX": 0, "translateX": -180.0 + spalte0 * z,
                "shearY": 0, "scaleY": -z, "translateY": 90.0 - zeile0 * z,
            },
            "crsCode": "EPSG:4326",
        },
    }


def lade_block(ee, bild, zeile0: int, spalte0: int, hoehe: int, breite: int, versuche: int = BLOCK_VERSUCHE):
    """Lädt einen Block des Rasters. Rückgabe (wert, anteil, bytes, sekunden, wiederholungen)."""
    wiederholungen = 0
    for versuch in range(versuche):
        t0 = time.monotonic()
        try:
            roh = ee.data.computePixels(_block_anfrage(ee, bild, zeile0, spalte0, hoehe, breite))
        except Exception as fehler:  # noqa: BLE001 - Art zählt, Text kann Projektangaben enthalten
            art = type(fehler).__name__
            if versuch == versuche - 1:
                raise RuntimeError(f"Block Zeile {zeile0} Spalte {spalte0}: {art} nach {versuche} Versuchen") from None
            wiederholungen += 1
            pause = BLOCK_PAUSE_BASIS_SEKUNDEN * 2**versuch
            print(
                f"Earth Engine: Block Zeile {zeile0} Spalte {spalte0}, Versuch {versuch + 1}/{versuche} "
                f"gescheitert ({art}), neuer Versuch in {pause} s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(pause)
            continue
        sekunden = time.monotonic() - t0
        feld = np.load(bytes_io.BytesIO(roh))
        return (
            np.asarray(feld["wert"], dtype="float32"),
            np.asarray(feld["anteil"], dtype="float32"),
            len(roh),
            sekunden,
            wiederholungen,
        )
    raise AssertionError("unerreichbar")


def lade_region(
    ee, bild, kacheln: set[str], parallel: int = 6, melde=print, zwischen: Path | None = None
) -> tuple[np.ndarray, np.ndarray, Messung]:
    """Lädt je Regions-Kachel (10° = 40 × 40 Zellen) einen Block; außerhalb bleibt NaN.

    Mit `zwischen` (Ordner) wird jeder fertige Block sofort als Datei abgelegt und
    bei einem Neustart nicht erneut gerechnet (nachgetragen 2026-09-27, nachdem ein
    Lauf für A bei Block 160-188 von außen beendet wurde und alles verloren war).
    Wiederverwendete Blöcke zählen nicht in Zeit und Bytes (`messung.wiederverwendet`).
    """
    n = vnp46a3_regionen.ZELLEN_PRO_KACHEL
    wert = np.full((vnp46a3.GITTER_BREITE, vnp46a3.GITTER_LAENGE), np.nan, dtype="float32")
    anteil = np.full_like(wert, np.nan)
    messung = Messung()
    bloecke = sorted((int(p[4:6]) * n, int(p[1:3]) * n) for p in kacheln)
    offen = []
    for z0, s0 in bloecke:
        datei = zwischen / f"{z0:03d}_{s0:04d}.npz" if zwischen else None
        if datei is not None and datei.exists():
            with np.load(datei) as d:
                wert[z0 : z0 + n, s0 : s0 + n] = d["wert"]
                anteil[z0 : z0 + n, s0 : s0 + n] = d["anteil"]
            messung.wiederverwendet += 1
        else:
            offen.append((z0, s0))
    if messung.wiederverwendet:
        melde(f"  {messung.wiederverwendet} Blöcke aus einem früheren Lauf übernommen, {len(offen)} offen")
    if zwischen:
        zwischen.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
        auftraege = {pool.submit(lade_block, ee, bild, z0, s0, n, n): (z0, s0) for z0, s0 in offen}
        for i, fertig in enumerate(concurrent.futures.as_completed(auftraege), 1):
            z0, s0 = auftraege[fertig]
            try:
                w, a, nbytes, sek, wdh = fertig.result()
            except RuntimeError as fehler:
                messung.fehler.append(str(fehler))
                continue
            w = np.where(w == FEHLWERT, np.nan, w)
            if zwischen:
                np.savez(zwischen / f"{z0:03d}_{s0:04d}.npz", wert=w, anteil=a)
            wert[z0 : z0 + n, s0 : s0 + n] = w
            anteil[z0 : z0 + n, s0 : s0 + n] = a
            messung.anfragen += 1
            messung.wiederholungen += wdh
            messung.bytes += nbytes
            messung.sekunden_summe += sek
            if i % 20 == 0 or i == len(offen):
                melde(f"  {i}/{len(offen)} Blöcke, {time.monotonic() - t0:.0f} s")
    messung.sekunden_wand = time.monotonic() - t0
    return wert, anteil, messung


def ergebnis_pfad(jahr: int, monat: int, kandidat: str) -> Path:
    return io.aleph_data_dir() / "vergleich" / "earth_engine" / f"{jahr:04d}-{monat:02d}_{kandidat}.npz"


def lade_und_speichere(jahr: int, monat: int, kandidat: str, parallel: int = 6) -> Path:
    from aleph.core import earth_engine

    pruefe_zeitraum(jahr, monat)
    ee = earth_engine.starte()
    ee.data.setDeadline(ANFRAGE_ZEITLIMIT_SEKUNDEN * 1000)
    bild = monatsbild(ee, kandidat, jahr, monat)
    kacheln = vnp46a3_regionen.lies_region(REGION)
    print(f"{jahr:04d}-{monat:02d} Kandidat {kandidat} ({KANDIDATEN[kandidat]}): {len(kacheln)} Blöcke")
    ziel = ergebnis_pfad(jahr, monat, kandidat)
    wert, anteil, messung = lade_region(
        ee, bild, kacheln, parallel=parallel, zwischen=ziel.with_name(ziel.stem + "_bloecke")
    )
    if messung.fehler:
        # Kein Ergebnis schreiben: fehlende Blöcke sähen sonst aus wie „keine Daten“.
        raise RuntimeError(
            f"{len(messung.fehler)} Blöcke nicht geladen (fertige liegen im Zwischenordner, "
            f"ein Neustart rechnet nur den Rest): " + "; ".join(messung.fehler[:5])
        )
    ziel.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "kandidat": kandidat, "quelle": KANDIDATEN[kandidat], "monat": f"{jahr:04d}-{monat:02d}",
        "region": REGION, "bloecke": len(kacheln), "parallel": parallel,
        "anfragen": messung.anfragen, "wiederverwendet": messung.wiederverwendet, "wiederholungen": messung.wiederholungen, "bytes": messung.bytes,
        "sekunden_summe": round(messung.sekunden_summe, 1), "sekunden_wand": round(messung.sekunden_wand, 1),
        "fehler": messung.fehler, "erstellt_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    np.savez_compressed(ziel, wert=wert, anteil=anteil, info=json.dumps(info))
    print(json.dumps(info, ensure_ascii=False))
    return ziel


def lies_ergebnis(jahr: int, monat: int, kandidat: str) -> tuple[np.ndarray, np.ndarray, dict]:
    with np.load(ergebnis_pfad(jahr, monat, kandidat)) as d:
        return d["wert"], d["anteil"], json.loads(str(d["info"]))


# --- Würfel lesen (nur über die vorgesehene Lesefunktion) -----------------


def lies_wuerfel(jahr: int, monat: int) -> dict[str, np.ndarray]:
    pruefe_zeitraum(jahr, monat)
    ds = vnp46a3.lies_monate_mit_region(
        [(jahr, monat)], [WUERFEL_WERT, WUERFEL_PIXEL, WUERFEL_WERT_MIT_AUFFUELLUNG], REGION
    )
    nicht_geladen = ds["nicht_geladen"].values[0]
    # Immer zusätzlich die Regionsmaske: Ist der Monat später ganz fertig (Zustand 1),
    # ist `nicht_geladen` überall False; Earth-Engine-Werte gibt es aber nur für die
    # Region (Auflage statistik-pruefer 2026-09-27).
    return {
        "wert": ds[WUERFEL_WERT].values[0],
        "pixel": ds[WUERFEL_PIXEL].values[0],
        "wert_mit_auffuellung": ds[WUERFEL_WERT_MIT_AUFFUELLUNG].values[0],
        "maske": ~nicht_geladen & region_maske(),
    }


# --- Vergleich nach K1-K6 --------------------------------------------------


def _log(x: np.ndarray) -> np.ndarray:
    return np.log10(np.clip(x, 0, None) + LOG_ZUSATZ)


def _r(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    lx, ly = _log(x), _log(y)
    if np.std(lx) == 0 or np.std(ly) == 0:
        return float("nan")  # alle Werte gleich: Korrelation nicht bestimmbar
    return float(np.corrcoef(lx, ly)[0, 1])


def vergleiche(
    ref: np.ndarray, ref_hat: np.ndarray, kand: np.ndarray, kand_hat: np.ndarray, maske: np.ndarray
) -> dict:
    """Vergleicht Würfel (ref) und Kandidat Zelle für Zelle nach K1-K6.

    ref, kand: Zellwerte (NaN = kein Wert); ref_hat, kand_hat: bool „Zelle hat Daten“;
    maske: bool, Zellen der Region (nur diese zählen).
    """
    k = KRITERIEN
    beide = maske & ref_hat & kand_hat & np.isfinite(ref) & np.isfinite(kand)
    dunkel = beide & (ref < KLASSE_DUNKEL_BIS)
    mittel = beide & (ref >= KLASSE_DUNKEL_BIS) & (ref < KLASSE_MITTEL_BIS)
    hell = beide & (ref >= KLASSE_MITTEL_BIS)
    licht = mittel | hell

    klassen = {}
    for name, sel in (("dunkel", dunkel), ("mittel", mittel), ("hell", hell)):
        r, c = ref[sel], kand[sel]
        eintrag = {"zellen": int(sel.sum()), "r_log": _r(r, c), "mittlere_differenz": float(np.mean(c - r)) if len(r) else float("nan")}
        if name != "dunkel" and len(r):
            q = c / r
            eintrag.update(
                median_q=float(np.median(q)),
                median_abw=float(np.median(np.abs(q - 1))),
                anteil_faktor2=float(np.mean((q > 2) | (q < 0.5))),
            )
        if name == "dunkel" and len(r):
            eintrag["anteil_falsches_licht"] = float(np.mean(c >= k["K4_dunkel_falsches_licht_ab"]))
        klassen[name] = eintrag

    r_licht = _r(ref[licht], kand[licht])
    region_ref = ref_hat[maske]
    region_kand = kand_hat[maske]
    gleich = float(np.mean(region_ref == region_kand)) if region_ref.size else float("nan")
    fehlt = float(np.mean(~region_kand[region_ref])) if region_ref.any() else float("nan")
    nur_kand = float(np.mean(region_kand[~region_ref])) if (~region_ref).any() else float("nan")

    stichproben = {}
    for ort, (b, l) in STICHPROBEN.items():
        z, s = zelle_von(b, l)
        rw, kw = float(ref[z, s]), float(kand[z, s])
        if ort == "Sahara":
            ok = bool(rw < k["K6_sahara_max"] and kw < k["K6_sahara_max"])
            q = float("nan")
        else:
            q = kw / rw if rw > 0 else float("nan")
            ok = bool(np.isfinite(q) and k["K6_stadt_q"][0] <= q <= k["K6_stadt_q"][1])
        stichproben[ort] = {"zeile": z, "spalte": s, "wuerfel": rw, "kandidat": kw, "q": q, "erfuellt": ok}

    def zwischen(x, grenzen):
        return bool(np.isfinite(x) and grenzen[0] <= x <= grenzen[1])

    def hoechstens(x, grenze):
        return bool(np.isfinite(x) and x <= grenze)

    erfuellt = {
        "K1": bool(np.isfinite(r_licht) and r_licht >= k["K1_r_log_min"]),
        "K2": all(
            zwischen(klassen[c].get("median_q", np.nan), k["K2a_median_q"])
            and hoechstens(klassen[c].get("median_abw", np.nan), k["K2b_median_abw_max"])
            for c in ("hell", "mittel")
        ),
        "K3": all(hoechstens(klassen[c].get("anteil_faktor2", np.nan), k["K3_anteil_faktor2_max"]) for c in ("hell", "mittel")),
        "K4": hoechstens(klassen["dunkel"].get("anteil_falsches_licht", np.nan), k["K4_anteil_max"]),
        "K5": bool(np.isfinite(gleich) and gleich >= k["K5_gleich_min"] and hoechstens(fehlt, k["K5_fehlt_im_kandidat_max"])),
        "K6": all(s["erfuellt"] for s in stichproben.values()),
    }
    if all(erfuellt.values()):
        urteil = "erfüllt"
    elif erfuellt["K1"] and erfuellt["K6"]:
        urteil = "teilweise"
    else:
        urteil = "nicht erfüllt"
    return {
        "zellen_region": int(maske.sum()),
        "zellen_beide": int(beide.sum()),
        "r_log_mittel_und_hell": r_licht,
        "klassen": klassen,
        "luecken": {"gleicher_zustand": gleich, "wuerfel_ja_kandidat_nein": fehlt, "wuerfel_nein_kandidat_ja": nur_kand},
        "stichproben": stichproben,
        "erfuellt": erfuellt,
        "urteil": urteil,
    }


# --- Nachträgliche Zusatzprüfungen (NICHT Teil des Urteils; Kriterien bleiben) ---


def _gemeinsam(ref, ref_hat, kand, kand_hat, maske):
    return maske & ref_hat & kand_hat & np.isfinite(ref) & np.isfinite(kand)


def _klassenwerte(r: np.ndarray, c: np.ndarray) -> dict:
    q = c / r
    return {
        "zellen": int(len(r)),
        "median_q": float(np.median(q)) if len(r) else float("nan"),
        "median_abw": float(np.median(np.abs(q - 1))) if len(r) else float("nan"),
        "anteil_faktor2": float(np.mean((q > 2) | (q < 0.5))) if len(r) else float("nan"),
    }


def klassen_nach_beiden(ref, ref_hat, kand, kand_hat, maske) -> dict:
    """Median q je Klasse, eingeteilt nach dem geometrischen Mittel beider Quellen.

    Hintergrund (statistik-pruefer 2026-09-27): Wer nur nach dem Würfelwert einteilt,
    bekommt Regression zur Mitte - auch ohne jeden Versatz erscheinen helle Zellen
    beim Kandidaten dunkler und schwache heller. Das geometrische Mittel behandelt
    beide Quellen gleich. Nachträglich, nicht Teil des Urteils.
    """
    beide = _gemeinsam(ref, ref_hat, kand, kand_hat, maske)
    g = np.sqrt(np.clip(ref, 0, None) * np.clip(kand, 0, None))
    mittel = beide & (g >= KLASSE_DUNKEL_BIS) & (g < KLASSE_MITTEL_BIS)
    hell = beide & (g >= KLASSE_MITTEL_BIS)
    return {"mittel": _klassenwerte(ref[mittel], kand[mittel]), "hell": _klassenwerte(ref[hell], kand[hell])}


def block_bootstrap(ref, ref_hat, kand, kand_hat, maske, wiederholungen: int = 1000, seed: int = 0) -> dict:
    """95-%-Intervalle für r (K1) und Median q / Median |q-1| je Klasse (K2), räumlicher Block-Bootstrap.

    Blöcke = 10°-Kacheln (40 × 40 Zellen), damit räumlich abhängige Zellen gemeinsam
    gezogen werden. Klassen wie im Urteil nach dem Würfelwert. Nachträglich, nicht Teil
    des Urteils.
    """
    beide = _gemeinsam(ref, ref_hat, kand, kand_hat, maske) & (ref >= KLASSE_DUNKEL_BIS)
    z, s = np.nonzero(beide)
    r, c = ref[z, s], kand[z, s]
    n = vnp46a3_regionen.ZELLEN_PRO_KACHEL
    block = (z // n) * 1000 + (s // n)
    ids, inv = np.unique(block, return_inverse=True)
    glieder = [np.flatnonzero(inv == i) for i in range(len(ids))]
    rng = np.random.default_rng(seed)
    werte: dict[str, list[float]] = {k: [] for k in ("r_log", "hell_median_q", "mittel_median_q", "hell_median_abw", "mittel_median_abw")}
    for _ in range(wiederholungen):
        idx = np.concatenate([glieder[i] for i in rng.integers(0, len(glieder), len(glieder))])
        rr, cc = r[idx], c[idx]
        werte["r_log"].append(_r(rr, cc))
        for name, sel in (("hell", rr >= KLASSE_MITTEL_BIS), ("mittel", rr < KLASSE_MITTEL_BIS)):
            q = cc[sel] / rr[sel]
            werte[f"{name}_median_q"].append(float(np.median(q)) if len(q) else float("nan"))
            werte[f"{name}_median_abw"].append(float(np.median(np.abs(q - 1))) if len(q) else float("nan"))
    return {
        "bloecke": int(len(ids)),
        "wiederholungen": wiederholungen,
        **{k: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))] for k, v in werte.items()},
    }


# Breitenbänder für die nachträgliche Auswertung nach Breite (2026-09-28). Die Grenzen
# 55/60/65/68/72/76° N wurden NACH Ansicht der Karte für A (2018-10) gewählt; sie sind
# beschreibend, keine geprüften Schwellen. Ohne Überlappung, Nord nach Süd.
BREITENBAENDER = (
    (76, 80), (72, 76), (68, 72), (65, 68), (60, 65), (55, 60), (40, 55),
    (20, 40), (0, 20), (-20, 0), (-40, -20), (-60, -40),
)


def nach_breite(ref, ref_hat, kand, kand_hat, maske, baender=BREITENBAENDER) -> list[dict]:
    """Kennzahlen je Breitenband (nachträglich, nicht Teil des Urteils).

    Einteilung wie im Urteil nach dem Würfelwert: „Zellen ≥ 0,5“ = Würfel ≥ KLASSE_DUNKEL_BIS.
    Je Band: Median q, Median |q-1|, Anteil Faktor 2 (Zellen ≥ 0,5), falsches Licht
    (Würfel < 0,5, Kandidat ≥ 1,0) und Zellen, in denen nur eine Quelle Daten hat.
    Untergrenze eingeschlossen, Obergrenze ausgeschlossen (Zellmitte).
    """
    breite, _ = vnp46a3._gitter_koordinaten()
    b = np.broadcast_to(np.asarray(breite, dtype=float)[:, None], ref.shape)
    beide = _gemeinsam(ref, ref_hat, kand, kand_hat, maske)
    ergebnis = []
    for unten, oben in baender:
        im_band = (b >= unten) & (b < oben)
        hell = beide & im_band & (ref >= KLASSE_DUNKEL_BIS)
        q = kand[hell] / ref[hell]
        dunkel = beide & im_band & (ref < KLASSE_DUNKEL_BIS)
        ergebnis.append({
            "band": [unten, oben],
            "zellen_ab_0_5": int(hell.sum()),
            "median_q": float(np.median(q)) if len(q) else float("nan"),
            "median_abw": float(np.median(np.abs(q - 1))) if len(q) else float("nan"),
            "anteil_faktor2": float(np.mean((q > 2) | (q < 0.5))) if len(q) else float("nan"),
            "falsches_licht": int((dunkel & (kand >= KRITERIEN["K4_dunkel_falsches_licht_ab"])).sum()),
            "nur_wuerfel": int((maske & im_band & ref_hat & ~kand_hat).sum()),
            "nur_kandidat": int((maske & im_band & kand_hat & ~ref_hat).sum()),
        })
    return ergebnis


def vergleiche_monat(jahr: int, monat: int, kandidat: str, mit_auffuellung: bool = False) -> dict:
    w = lies_wuerfel(jahr, monat)
    kand, anteil, info = lies_ergebnis(jahr, monat, kandidat)
    ref = w["wert_mit_auffuellung"] if mit_auffuellung else w["wert"]
    ergebnis = vergleiche(ref, w["pixel"] > 0, kand, anteil > 0, w["maske"])
    ergebnis["ladung"] = info
    ergebnis["vergleichsgroesse"] = WUERFEL_WERT_MIT_AUFFUELLUNG if mit_auffuellung else WUERFEL_WERT
    return ergebnis


def karte(jahr: int, monat: int, ziel: Path, kandidaten=("A", "B")) -> Path:
    """Abweichungskarte: Kandidat/Würfel je Zelle, dazu Lücken und falsches Licht.

    Farben (Diverging-Paar blau ↔ rot mit grauer Mitte, dataviz-Referenzpalette):
    blau = Kandidat niedriger, rot = Kandidat höher, gekappt bei Faktor 4; die graue
    Mitte ist dunkler als der Untergrund, damit „gleich hell“ nicht wie „dunkel“ aussieht.
    Eigene Farben: gelb = Würfel dunkel, Kandidat ≥ 1; schwarz = nur der Würfel hat
    Daten; violett = nur der Kandidat hat Daten; mittelgrau = keine der beiden Quellen.
    Schraffiert: außerhalb der Region, nicht verglichen. Ausschnitt 80° N bis 60° S,
    20° W bis 180° O (die ganze Region Afrika-Europa-Asien).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap
    from matplotlib.patches import Patch

    matplotlib.rcParams["hatch.color"] = "#d6d5d0"
    matplotlib.rcParams["hatch.linewidth"] = 0.6
    w = lies_wuerfel(jahr, monat)
    ref, ref_hat, maske = w["wert"], w["pixel"] > 0, w["maske"]
    divergierend = LinearSegmentedColormap.from_list(
        "blau_rot", ["#104281", "#3987e5", "#c9c7c0", "#e34948", "#8f1f1e"]
    )
    # 0 dunkel passend, 1 falsches Licht, 2 nur Würfel, 3 nur Kandidat, 4 keine Daten, 5 außerhalb
    zusatz_farben = ListedColormap(["#fcfcfb", "#fab219", "#1a1a19", "#8e44ad", "#9a9892", "#fcfcfb"])
    ausschnitt = (slice(40, 600), slice(640, 1440))
    ausdehnung = (-20, 180, -60, 80)

    fig, achsen = plt.subplots(len(kandidaten), 1, figsize=(11, 6.2 * len(kandidaten)), constrained_layout=True)
    achsen = np.atleast_1d(achsen)
    for ax, k in zip(achsen, kandidaten):
        kand, anteil, _ = lies_ergebnis(jahr, monat, k)
        kand_hat = anteil > 0
        beide = maske & ref_hat & kand_hat & np.isfinite(ref) & np.isfinite(kand)
        licht = beide & (ref >= KLASSE_DUNKEL_BIS)
        with np.errstate(divide="ignore", invalid="ignore"):
            abw = np.where(licht, np.log2(np.clip(kand, 1e-3, None) / ref), np.nan)
        zusatz = np.full(ref.shape, np.nan)
        dunkel = beide & (ref < KLASSE_DUNKEL_BIS)
        zusatz[dunkel] = 0
        zusatz[dunkel & (kand >= KRITERIEN["K4_dunkel_falsches_licht_ab"])] = 1
        zusatz[maske & ref_hat & ~kand_hat] = 2
        zusatz[maske & ~ref_hat & kand_hat] = 3
        zusatz[maske & ~ref_hat & ~kand_hat] = 4
        zusatz[~maske] = 5
        ax.imshow(zusatz[ausschnitt], cmap=zusatz_farben, vmin=-0.5, vmax=5.5, extent=ausdehnung, interpolation="nearest")
        ausserhalb = (~maske)[ausschnitt].astype(float)
        ax.contourf(
            np.linspace(ausdehnung[0], ausdehnung[1], ausserhalb.shape[1]),
            np.linspace(ausdehnung[3], ausdehnung[2], ausserhalb.shape[0]),
            ausserhalb, levels=[0.5, 1.5], colors="none", hatches=["////"],
        )
        bild = ax.imshow(abw[ausschnitt], cmap=divergierend, vmin=-2, vmax=2, extent=ausdehnung, interpolation="nearest")
        ax.set_title(f"Kandidat {k} ({KANDIDATEN[k]}) gegen VNP46A3-Würfel, {jahr:04d}-{monat:02d}", loc="left", fontsize=11)
        ax.set_xlabel("Länge (°)", color="#555")
        ax.set_ylabel("Breite (°)", color="#555")
        ax.tick_params(colors="#555", labelsize=8)
        for seite in ax.spines.values():
            seite.set_color("#bbb")
        leiste = fig.colorbar(bild, ax=ax, shrink=0.8, ticks=[-2, -1, 0, 1, 2])
        leiste.ax.set_yticklabels(["¼ (niedriger)", "½", "gleich", "×2", "×4 (höher)"], fontsize=8)
        leiste.set_label("Kandidat / Würfel (Zellen mit Würfel ≥ 0,5 nW·cm⁻²·sr⁻¹)", fontsize=8)
    fig.legend(
        handles=[
            Patch(facecolor="#fcfcfb", edgecolor="#999", label="Würfel < 0,5 und Kandidat < 1"),
            Patch(facecolor="#fab219", label="Würfel < 0,5, Kandidat ≥ 1 (K4)"),
            Patch(facecolor="#1a1a19", label="nur Würfel hat Daten (K5)"),
            Patch(facecolor="#8e44ad", label="nur Kandidat hat Daten (K5)"),
            Patch(facecolor="#9a9892", label="keine Quelle hat Daten"),
            Patch(facecolor="#fcfcfb", edgecolor="#999", hatch="////", label="außerhalb Afrika-Europa-Asien"),
        ],
        loc="lower center", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.08),
    )
    ziel.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ziel, dpi=110, facecolor="#fcfcfb", bbox_inches="tight")
    plt.close(fig)
    return ziel


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("aktion", choices=["laden", "vergleichen", "karte"])
    p.add_argument("--ziel", help="PNG-Datei für die Karte")
    p.add_argument("--monat", required=True, help="JJJJ-MM, vor 2023")
    p.add_argument("--kandidat", choices=["A", "B"], action="append")
    p.add_argument("--parallel", type=int, default=6)
    a = p.parse_args(argv)
    jahr, monat = (int(t) for t in a.monat.split("-"))
    pruefe_zeitraum(jahr, monat)
    kandidaten = a.kandidat or ["A", "B"]
    if a.aktion == "karte":
        print(karte(jahr, monat, Path(a.ziel), tuple(kandidaten)))
        return 0
    for k in kandidaten:
        if a.aktion == "laden":
            lade_und_speichere(jahr, monat, k, parallel=a.parallel)
        else:
            for auff in (False, True):
                e = vergleiche_monat(jahr, monat, k, mit_auffuellung=auff)
                print(json.dumps({"kandidat": k, **e}, ensure_ascii=False, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
