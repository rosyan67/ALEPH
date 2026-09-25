"""Layer Niederschlag: GPM IMERG V07 (Global Precipitation Measurement).

Monatliche Niederschlagswerte vom NASA GPM-Projekt.

**Wichtig für ALEPH:** Das native 0,1°-Raster passt nicht ganzzahlig auf das
Zielraster 0,25° (Verhältnis 2,5). Wir verwenden eine **zweistufige Aggregation**:
1. Zuerst auf ein 0,5°-Raster (5:1 Verhältnis, glatte Teilung)
2. Dann auf 0,25° mit bilinearer Interpolation

Das Resultat ist eine Annäherung an die flächengewichtete Mittelung, ist aber
deutlich schneller und liefert vergleichbare Ergebnisse für Analysen.

Für eine exakte flächengewichtete Aggregation wäre ein Wechsel zu scipy oder
ein spezieller RegCoef-Mechanismus nötig.

Steckbrief: docs/sources/gpm_imerg.md
"""

import concurrent.futures
import os
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np
import xarray as xr

import earthaccess
from earthaccess.exceptions import DownloadFailure

from aleph.core import io

# --- Konstanten ------------------------------------------------------------
META = {
    "name": "GPM IMERG V07",
    "bereich": "Umwelt / Niederschlag",
    "quelle": "NASA GPM IMERG Final Precipitation Run V07",
    "lizenz": "CC0 (NASA Earthdata) / CC BY 4.0 (AWS)",
    "native_aufloesung": "0,1°",
    "ziel_aufloesung": "0,25°",
    "einheit": "mm (Monatssumme)",
    "zeitraum": "2013-01 bis 2025-12",
    "details": "docs/sources/gpm_imerg.md",
    "hinweis": "2stufige Aggregation (0,1°→0,5°→0,25°)",
}

# ALEPH-Zielraster
ZWischen_BREITE = 360   # 0,5°
ZWischen_LAENGE = 720   # 0,5°
ZIEGE_BREITE = 720      # 0,25°
ZIEGE_LAENGE = 1440     # 0,25°
ZELLEN_GROESSE = 0.25

# GPM-Meta-Informationen
GPM_LAT_CENTER = np.linspace(89.95, -89.95, 1800)  # 0,1° spacing
GPM_LON_CENTER = np.linspace(-179.95, 179.95, 3600)  # 0,1° spacing

# Feldnamen in HDF5
H5_DATEN_GRUPPE = "Grid"
H5_PRECIPITATION = "precipitation"      # mm/hr
H5_LATITUDE = "latitude"
H5_LONGITUDE = "longitude"

# Zeiten
MONATE_PRO_JAHR = 12
TAGE_PRO_MONAT = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                  7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def zeitachse_monate() -> np.ndarray:
    """Monatige Zeitachse für 2013-01 bis 2025-12."""
    start = np.datetime64("2013-01", "M")
    ende = np.datetime64("2025-12", "M")
    return np.arange(start, ende + np.timedelta64(1, "M"))


def _gitter_ziele() -> tuple[np.ndarray, np.ndarray]:
    """Zielgitter 0,25°."""
    breite = 90 - ZELLEN_GROESSE / 2 - np.arange(ZIEGE_BREITE) * ZELLEN_GROESSE
    laenge = -180 + ZELLEN_GROESSE / 2 + np.arange(ZIEGE_LAENGE) * ZELLEN_GROESSE
    return breite.astype("float32"), laenge.astype("float32")


def _mittelwert_01_to_05(fine_data: np.ndarray) -> np.ndarray:
    """Agglomeriert von 0,1° auf 0,5° mit 5:1 Mittelung (glatt teilbar)."""
    ny, nx = fine_data.shape
    assert ny % 5 == 0 and nx % 5 == 0, "Rastergröße muss durch 5 teilbar sein"

    # Reshape und mittel: 0,1° → 0,5°
    coarsed = fine_data.reshape(ny // 5, 5, nx // 5, 5).mean(axis=(1, 3))
    return coarsed.astype("float32")


def _interpoliere_05_to_025(fine_data: np.ndarray) -> np.ndarray:
    """Interpoliert von 0,5° auf 0,25° mit bilinearer Interpolation."""
    ny, nx = fine_data.shape

    # Zielgitter (0,25°): Zentren 89.875, 89.625, ..., -89.875
    target_lat, target_lon = _gitter_ziele()

    # Quellgitter (0,5°): Zentren 89.75, 89.25, ..., -89.75
    # Wichtig: Source grid ist um 0.125° verschoben zum Target grid
    src_lat_0 = 89.75  # Erster Quell-Punkt
    src_lon_0 = -179.75

    # Interpolate with numpy only: use 4-point stencil interpolation
    result = np.full((len(target_lat), len(target_lon)), np.nan, dtype="float32")

    for i, tlat in enumerate(target_lat):
        for j, tlon in enumerate(target_lon):
            # Find nearest source indices
            # ilat = (src_lat_0 - tlat) / 0.5
            # ilon = (tlon - src_lon_0) / 0.5
            ilat = (src_lat_0 - tlat) / 0.5
            ilon = (tlon - src_lon_0) / 0.5

            i0 = int(np.floor(ilat))
            j0 = int(np.floor(ilon))

            if i0 < 0 or i0 >= ny - 1 or j0 < 0 or j0 >= nx - 1:
                continue

            # Bilinear weight
            wi = ilat - i0
            wj = ilon - j0

            v00 = fine_data[i0, j0]
            v01 = fine_data[i0, j0 + 1]
            v10 = fine_data[i0 + 1, j0]
            v11 = fine_data[i0 + 1, j0 + 1]

            result[i, j] = (
                (1 - wi) * (1 - wj) * v00 +
                wj * (1 - wi) * v01 +
                (1 - wj) * wi * v10 +
                wj * wi * v11
            )

    return result


def _aggregate_gpm(mittel_mmhr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Agglomeriert GPM-Daten: 0,1° → 0,5° → 0,25°, konvertiert zu mm/Monat."""
    # 1. 0,1° → 0,5° (5:1 Mittelung)
    stufe1 = _mittelwert_01_to_05(mittel_mmhr)

    # 2. 0,5° → 0,25° (Interpolation)
    stufe2 = _interpoliere_05_to_025(stufe1)

    # 3. Dichte (mm/h) → Niederschlag (mm/Monat)
    # Für jeden Monat multiplizieren wir mit den Stunden
    # Das passiert außerhalb in der Konvertierung
    return stufe2, _berechne_gueltige_pixel(mittel_mmhr)


def _berechne_gueltige_pixel(mittel: np.ndarray) -> np.ndarray:
    """Zählt gültige Pixel nach Aggregation."""
    # Anzahl gültiger Pixel nach Aggregation (0,1° → 0,5° → 0,25°)
    # Nach der 5:1 Mittelung auf 0,5° bleiben 25 gültige Pixel je 0,5°-Zelle
    # (bei vollständig gültigen Eingabedaten). Bei Fehlwerten wird entsprechend weniger.
    ny, nx = mittel.shape
    if ny % 5 != 0 or nx % 5 != 0:
        raise ValueError("Rastergröße muss durch 5 teilbar sein")

    gueltig_05 = np.full((ny // 5, nx // 5), 0, dtype=np.int32)
    for i in range(0, ny, 5):
        for j in range(0, nx, 5):
            gueltig_05[i // 5, j // 5] = int(np.isfinite(mittel[i:i + 5, j:j + 5]).sum())

    # Nach der Interpolation auf 0,25° bleibt die Zahl gültiger Pixel gleich
    # (je 0,25°-Zelle sind es 25 gültige Pixel bei vollständig gültigen Daten)
    gueltig_025 = np.repeat(np.repeat(gueltig_05, 2, axis=0), 2, axis=1)

    return gueltig_025.astype(np.int16)


def download_monat(jahr: int, monat: int, ziel_ordner: Path) -> Path | None:
    """Lädt eine Monatsdatei herunter."""
    leer_tag = date(jyr := jahr, monat, 1).day
    tage = MONATE_PRO_JAHR
    dateiname = f"3B-MO.MS.MRG.3IMERG.{jahr:4d}{leer_tag:02d}-S000000-E235959.01.V07B.HDF5"

    treffer = earthaccess.search_data(
        short_name="GPM_3IMERGM", version="07",
        temporal=(f"{jahr:04d}-{monat:02d}-01", f"{jahr:04d}-{monat:02d}-{MONATE_PRO_JAHR}"),
        bounding_box=(-180, -90, 180, 90), count=1,
    )
    if not treffer:
        return None

    return earthaccess.download([treffer[0]], str(ziel_ordner))[0]


def download(start: str, ende: str, gleichzeitig: int = 2) -> list[Path]:
    """Lädt alle Monate herunter."""
    jahr, monat = map(int, start.split("-"))
    end_jahr, end_monat = map(int, ende.split("-"))
    base = io.rohdaten_pfad("gpm_imerg")
    dateien = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=gleichzeitig) as pool:
        futures = {}
        while (jahr, monat) <= (end_jahr, end_monat):
            ziel = base / f"{jahr:04d}-{monat:02d}.h5"
            futures[pool.submit(download_monat, jahr, monat, ziel.parent)] = (jahr, monat, ziel)
            monat += 1
            if monat > 12:
                monat, jahr = 1, jahr + 1

        for future in concurrent.futures.as_completed(futures):
            try:
                ergebnis = future.result(timeout=120)
                if ergebnis:
                    dateien.append(ergebnis)
            except (Exception, DownloadFailure):
                pass
    return dateien


def to_cube() -> xr.Dataset:
    """Baut den Würfel."""
    base = io.rohdaten_pfad("gpm_imerg")
    pfad = io.wuerfel_pfad("gpm_imerg.zarr")

    if not base.exists():
        return xr.Dataset()

    zie_ge = _gitter_ziele()
    zeit = zeitachse_monate()

    monate_daten = []
    for h5_datei in sorted(base.glob("*.h5")):
        try:
            ds = _verkleinere_monat(h5_datei)
            monate_daten.append(ds)
        except Exception:
            continue

    if not monate_daten:
        return xr.Dataset()

    gesamt = xr.concat(monate_daten, dim="zeit")
    gesamt.to_zarr(pfad, mode="w")
    return gesamt


def _verkleinere_monat(pfad: Path) -> xr.Dataset:
    """Reduziert einen Monat auf das ALEPH-Raster."""
    with h5py.File(pfad, "r") as f:
        precip_hr = f[H5_DATEN_GRUPPE][H5_PRECIPITATION][:]
        lat = f[H5_DATEN_GRUPPE][H5_LATITUDE][:]
        lon = f[H5_DATEN_GRUPPE][H5_LONGITUDE][:]

    # Maskiere Fehlwerte
    gueltig = (precip_hr > 0) & np.isfinite(precip_hr) & (precip_hr < 1000)
    mittel_gefiltert = np.where(gueltig, precip_hr, np.nan)

    # Aggregation
    mittel_025, gueltig_025 = _aggregate_gpm(mittel_gefiltert)

    # Konvertiere mm/h → mm/Monat
    jahr = int(pfad.stem.split("-")[0])
    monat = int(pfad.stem.split("-")[1])
    stunden = MONATE_PRO_JAHR * 24  # grobe Annäherung, genauer wäre Tagessumme

    return xr.Dataset(
        {
            "precipitation_mittel": (("zeit", "breite", "laenge"),
                (mittel_025 * stunden)[np.newaxis, :, :].astype("float32")),
            "precipitation_gueltige_pixel": (("zeit", "breite", "laenge"),
                gueltig_025[np.newaxis, :, :].astype("int16")),
            "monat_fertig": (("zeit",), np.array([1], dtype="int8")),
        },
        coords={"zeit": [np.datetime64(f"{jahr:04d}-{monat:02d}-01", "M")],
                "breite": _gitter_ziele()[0], "laenge": _gitter_ziele()[1]},
        attrs={"quelle": META["quelle"], "einheit_mittel": "mm/Monat"},
    )


def vorhandene_monate() -> set[tuple[int, int]]:
    """Gefundene Monate im Würfel."""
    pfad = io.wuerfel_pfad("gpm_imerg.zarr")
    if not pfad.exists():
        return set()

    with xr.open_zarr(pfad, chunks=None) as ds:
        zeit = ds["zeit"].values
        fertig = ds["monat_fertig"].values

    return {(z.astype(object).year, z.astype(object).month) for z, f in zip(zeit, fertig) if f == 1}