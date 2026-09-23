"""Prüft die Verkleinerungs-Logik des Layers VNP46A3 mit synthetischen Kacheln.

Keine echten NASA-Daten, kein Netzzugriff. Die erwarteten Zahlen sind von
Hand nachgerechnet (siehe Kommentare), nicht nur gegen den Code selbst
geprüft.
"""

import time
from pathlib import Path

import h5py
import numpy as np
import pytest
import xarray as xr

from aleph.layers import vnp46a3

PIXEL = vnp46a3.PIXEL_PRO_KACHEL  # 2400


def _leere_kachel_arrays():
    near = np.full((PIXEL, PIXEL), vnp46a3.FEHLWERT_KOMPOSIT, dtype="float32")
    near_num = np.full((PIXEL, PIXEL), vnp46a3.FEHLWERT_NUM, dtype="uint16")
    near_q = np.full((PIXEL, PIXEL), 255, dtype="uint8")
    allangle = np.full((PIXEL, PIXEL), vnp46a3.FEHLWERT_KOMPOSIT, dtype="float32")
    allangle_num = np.full((PIXEL, PIXEL), vnp46a3.FEHLWERT_NUM, dtype="uint16")
    allangle_q = np.full((PIXEL, PIXEL), 255, dtype="uint8")
    return near, near_num, near_q, allangle, allangle_num, allangle_q


def _schreibe_kachel(pfad: Path, h: int, v: int, jahr: int, tag_im_jahr: int) -> Path:
    near, near_num, near_q, allangle, allangle_num, allangle_q = _leere_kachel_arrays()

    dateiname = f"VNP46A3.A{jahr:04d}{tag_im_jahr:03d}.h{h:02d}v{v:02d}.002.2025000000000.h5"
    ziel = pfad / dateiname
    lat_max = 90 - v * 10
    lon_min = -180 + h * 10
    lat = lat_max - (np.arange(PIXEL) + 0.5) * (10 / PIXEL)
    lon = lon_min + (np.arange(PIXEL) + 0.5) * (10 / PIXEL)
    with h5py.File(ziel, "w") as f:
        g = f.create_group(vnp46a3.HDF_GRUPPE)
        g.create_dataset("NearNadir_Composite_Snow_Free", data=near)
        g.create_dataset("NearNadir_Composite_Snow_Free_Num", data=near_num)
        g.create_dataset("NearNadir_Composite_Snow_Free_Quality", data=near_q)
        g.create_dataset("AllAngle_Composite_Snow_Free", data=allangle)
        g.create_dataset("AllAngle_Composite_Snow_Free_Num", data=allangle_num)
        g.create_dataset("AllAngle_Composite_Snow_Free_Quality", data=allangle_q)
        g.create_dataset("lat", data=lat.astype("float64"))
        g.create_dataset("lon", data=lon.astype("float64"))
    return ziel


def _kachel_h19v03(tmp_path, jahr=2020, tag=153) -> Path:
    """Kachel wie die erste Probekachel: 10-20°O, 50-60°N."""
    near, near_num, near_q, allangle, allangle_num, allangle_q = _leere_kachel_arrays()
    # Zelle (0,0): 3600 gültige Pixel, Wert 10, Num 5, Quality 1 (nicht aufgefüllt)
    near[0:60, 0:60] = 10.0
    near_num[0:60, 0:60] = 5
    near_q[0:60, 0:60] = 1
    allangle[0:60, 0:60] = 20.0
    allangle_num[0:60, 0:60] = 8
    allangle_q[0:60, 0:60] = 1
    # Zelle (0,1): nur halb gültig (erste 30 Zeilen), Wert 4, Num 2
    near[0:30, 60:120] = 4.0
    near_num[0:30, 60:120] = 2
    near_q[0:30, 60:120] = 1
    # Zelle (0,2): komplett aufgefüllt (Quality 2), Wert 1.5, Num 0
    near[0:60, 120:180] = 1.5
    near_num[0:60, 120:180] = 0
    near_q[0:60, 120:180] = 2

    dateiname = f"VNP46A3.A{jahr:04d}{tag:03d}.h19v03.002.2025133214434.h5"
    ziel = tmp_path / dateiname
    lat = 60 - (np.arange(PIXEL) + 0.5) * (10 / PIXEL)
    lon = 10 + (np.arange(PIXEL) + 0.5) * (10 / PIXEL)
    with h5py.File(ziel, "w") as f:
        g = f.create_group(vnp46a3.HDF_GRUPPE)
        g.create_dataset("NearNadir_Composite_Snow_Free", data=near)
        g.create_dataset("NearNadir_Composite_Snow_Free_Num", data=near_num)
        g.create_dataset("NearNadir_Composite_Snow_Free_Quality", data=near_q)
        g.create_dataset("AllAngle_Composite_Snow_Free", data=allangle)
        g.create_dataset("AllAngle_Composite_Snow_Free_Num", data=allangle_num)
        g.create_dataset("AllAngle_Composite_Snow_Free_Quality", data=allangle_q)
        g.create_dataset("lat", data=lat.astype("float64"))
        g.create_dataset("lon", data=lon.astype("float64"))
    return ziel


# --- Namen aus dem Dateinamen -----------------------------------------------


def test_kachel_position_h19v03(tmp_path):
    pfad = _kachel_h19v03(tmp_path)
    zeile0, spalte0, h, v = vnp46a3._kachel_position(pfad)
    assert (zeile0, spalte0, h, v) == (120, 760, 19, 3)


def test_kachel_jahr_monat(tmp_path):
    pfad = _kachel_h19v03(tmp_path, jahr=2020, tag=153)  # Tag 153 = 1. Juni 2020
    assert vnp46a3._kachel_jahr_monat(pfad) == (2020, 6)


def test_kachel_name_ohne_hv_bricht_ab(tmp_path):
    pfad = tmp_path / "keine_kachel.h5"
    pfad.touch()
    with pytest.raises(vnp46a3.KachelName):
        vnp46a3._kachel_position(pfad)


# --- Maskierung und Verkleinerung -------------------------------------------


def test_lies_kachel_maskiert_und_mittelt_korrekt(tmp_path):
    pfad = _kachel_h19v03(tmp_path)
    bloecke = vnp46a3._lies_kachel(pfad)

    assert bloecke["near_nadir_mittel"][0, 0] == pytest.approx(10.0)
    assert bloecke["near_nadir_gueltige_pixel"][0, 0] == 3600
    assert bloecke["near_nadir_num"][0, 0] == pytest.approx(5.0)
    assert bloecke["near_nadir_aufgefuellt_pixel"][0, 0] == 0

    # Zelle (0,1): nur 30*60=1800 der 3600 Pixel sind gültig, Mittel bleibt 4.0
    assert bloecke["near_nadir_mittel"][0, 1] == pytest.approx(4.0)
    assert bloecke["near_nadir_gueltige_pixel"][0, 1] == 1800

    # Zelle (0,2): komplett aufgefüllt, zählt trotzdem als gültig, aber markiert
    assert bloecke["near_nadir_gueltige_pixel"][0, 2] == 3600
    assert bloecke["near_nadir_aufgefuellt_pixel"][0, 2] == 3600
    assert bloecke["near_nadir_mittel"][0, 2] == pytest.approx(1.5)

    # Zelle ohne jeden gesetzten Wert: nichts gültig, Mittel ist NaN
    assert bloecke["near_nadir_gueltige_pixel"][1, 0] == 0
    assert np.isnan(bloecke["near_nadir_mittel"][1, 0])

    assert bloecke["allangle_mittel"][0, 0] == pytest.approx(20.0)


def test_verkleinere_monat_setzt_werte_an_globaler_position(tmp_path):
    pfad = _kachel_h19v03(tmp_path)
    ds = vnp46a3.verkleinere_monat([pfad])

    assert ds["zeit"].values[0] == np.datetime64("2020-06-01")
    assert float(ds["near_nadir_mittel"][0, 120, 760]) == pytest.approx(10.0)
    assert float(ds["near_nadir_mittel"][0, 120, 761]) == pytest.approx(4.0)
    # Weit entfernte Zelle bleibt unberührt (kein Übergriff auf andere Kacheln)
    assert np.isnan(float(ds["near_nadir_mittel"][0, 0, 0]))


def test_verkleinere_monat_ohne_dateien_bricht_ab():
    with pytest.raises(ValueError):
        vnp46a3.verkleinere_monat([])


# --- Ausrichtungsprüfung (lat/lon gegen h/v) --------------------------------


def test_pruefe_ausrichtung_akzeptiert_passende_kachel(tmp_path):
    pfad = _schreibe_kachel(tmp_path, h=19, v=3, jahr=2020, tag_im_jahr=153)
    with h5py.File(pfad, "r") as f:
        vnp46a3._pruefe_ausrichtung(f[vnp46a3.HDF_GRUPPE], pfad, h=19, v=3)  # kein Fehler


def test_pruefe_ausrichtung_erkennt_vertauschte_hv(tmp_path):
    pfad = _schreibe_kachel(tmp_path, h=19, v=3, jahr=2020, tag_im_jahr=153)
    with h5py.File(pfad, "r") as f:
        with pytest.raises(vnp46a3.KachelAusrichtung):
            vnp46a3._pruefe_ausrichtung(f[vnp46a3.HDF_GRUPPE], pfad, h=3, v=19)


def test_pruefe_ausrichtung_erkennt_gedrehte_lat(tmp_path):
    pfad = _schreibe_kachel(tmp_path, h=0, v=0, jahr=2020, tag_im_jahr=1)
    with h5py.File(pfad, "r+") as f:
        lat = f[vnp46a3.HDF_GRUPPE]["lat"][:]
        f[vnp46a3.HDF_GRUPPE]["lat"][:] = lat[::-1]  # künstlich falsch herum
    with h5py.File(pfad, "r") as f:
        with pytest.raises(vnp46a3.KachelAusrichtung):
            vnp46a3._pruefe_ausrichtung(f[vnp46a3.HDF_GRUPPE], pfad, h=0, v=0)


# --- Vollständigkeitsprüfung -------------------------------------------------


def test_pruefe_vollstaendigkeit_akzeptiert_uebereinstimmende_zahl():
    dateien = [Path(f"kachel_{i}.h5") for i in range(460)]
    vnp46a3.pruefe_vollstaendigkeit(2024, 1, 460, dateien)  # kein Fehler


def test_pruefe_vollstaendigkeit_bricht_bei_abweichender_zahl_ab():
    dateien = [Path(f"kachel_{i}.h5") for i in range(459)]
    with pytest.raises(vnp46a3.MonatUnvollstaendig):
        vnp46a3.pruefe_vollstaendigkeit(2024, 1, 460, dateien)


# --- Würfel schreiben, Fortsetzung, Manifest (mit vorgetäuschter SSD) ------


@pytest.fixture
def fake_ssd(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    return tmp_path


def test_wuerfel_schreiben_und_fortsetzung_erkennen(tmp_path, fake_ssd):
    pfad = _kachel_h19v03(tmp_path, jahr=2020, tag=153)  # Juni
    ds1 = vnp46a3.verkleinere_monat([pfad])
    assert vnp46a3.vorhandene_monate() == set()
    vnp46a3.schreibe_in_wuerfel(ds1)
    assert vnp46a3.vorhandene_monate() == {(2020, 6)}

    pfad2 = _kachel_h19v03(tmp_path, jahr=2020, tag=183)  # Juli
    ds2 = vnp46a3.verkleinere_monat([pfad2])
    vnp46a3.schreibe_in_wuerfel(ds2)
    assert vnp46a3.vorhandene_monate() == {(2020, 6), (2020, 7)}


def test_manifest_enthaelt_dateinamen(fake_ssd):
    dateien = [Path("VNP46A3.A2024001.h19v03.002.123.h5"), Path("VNP46A3.A2024001.h20v03.002.124.h5")]
    ziel = vnp46a3.schreibe_manifest(2024, 1, dateien)
    inhalt = ziel.read_text(encoding="utf-8").splitlines()
    assert sorted(inhalt) == sorted(p.name for p in dateien)
    assert ziel == fake_ssd / "protokoll" / "manifeste" / "vnp46a3" / "2024-01.txt"


# --- Kachel-Download: Zeitlimit und Wiederholung (2026-09-23) --------------
#
# Grund: earthaccess.download() setzt selbst kein Zeitlimit für die HTTP-
# Anfrage (session.get ohne timeout=), eine hängengebliebene Verbindung
# wartet sonst unbegrenzt. Diese Tests ersetzen earthaccess.download durch
# eine Attrappe - kein echter Netzzugriff, keine echten 10 Minuten Wartezeit.


def test_lade_kachel_erfolg_im_ersten_versuch(monkeypatch, tmp_path):
    aufrufe = []

    def fake_download(granules, local_path):
        aufrufe.append(granules)
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    pfad = vnp46a3._lade_kachel(
        "granule-1", tmp_path, datei_timeout_sekunden=1, max_versuche=3, wartezeit_basis_sekunden=0.01
    )
    assert pfad == tmp_path / "kachel.h5"
    assert len(aufrufe) == 1


def test_lade_kachel_bei_haenger_neuer_versuch(monkeypatch, tmp_path):
    """Simuliert eine hängengebliebene Verbindung: der erste Versuch reagiert
    nicht innerhalb des Zeitlimits, der zweite klappt."""
    versuche = {"n": 0}

    def fake_download(granules, local_path):
        versuche["n"] += 1
        if versuche["n"] == 1:
            time.sleep(0.5)  # länger als das Test-Zeitlimit unten (0,1 s)
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    pfad = vnp46a3._lade_kachel(
        "granule-1", tmp_path, datei_timeout_sekunden=0.1, max_versuche=3, wartezeit_basis_sekunden=0.01
    )
    assert pfad == tmp_path / "kachel.h5"
    assert versuche["n"] == 2


def test_lade_kachel_wartezeit_waechst(monkeypatch, tmp_path):
    """Prüft, dass die Wartezeit zwischen Versuchen wächst (verdoppelt sich)."""
    versuche = {"n": 0}
    wartezeiten = []

    def fake_download(granules, local_path):
        versuche["n"] += 1
        if versuche["n"] < 3:
            raise RuntimeError("simulierter Fehler")
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    monkeypatch.setattr(vnp46a3.time, "sleep", lambda s: wartezeiten.append(s))
    pfad = vnp46a3._lade_kachel(
        "granule-1", tmp_path, datei_timeout_sekunden=1, max_versuche=4, wartezeit_basis_sekunden=20
    )
    assert pfad == tmp_path / "kachel.h5"
    assert versuche["n"] == 3
    assert wartezeiten == [20, 40]


def test_lade_kachel_gibt_nach_max_versuchen_auf(monkeypatch, tmp_path):
    def fake_download(granules, local_path):
        raise RuntimeError("dauerhafter Fehler")

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    monkeypatch.setattr(vnp46a3.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="dauerhafter Fehler"):
        vnp46a3._lade_kachel(
            "granule-1", tmp_path, datei_timeout_sekunden=1, max_versuche=3, wartezeit_basis_sekunden=0.01
        )


# --- lade_monat: Nebenläufigkeit einstellbar, Fehler werden gesammelt ------


class _AttrappenGranule:
    """Ersetzt earthaccess.DataGranule in Tests: nur data_links() wird gebraucht."""

    def __init__(self, link: str):
        self._link = link

    def data_links(self):
        return [self._link]


def _attrappen_granules(anzahl: int, jahr: int = 2024, monat: int = 1) -> list[_AttrappenGranule]:
    tag = 1  # Tag 001 im Jahr = Januar
    return [
        _AttrappenGranule(f"https://example.org/VNP46A3.A{jahr:04d}{tag:03d}.h{i:02d}v03.002.20240101000000.h5")
        for i in range(anzahl)
    ]


def test_lade_monat_nutzt_gleichzeitige_downloads_und_sammelt_dateien(monkeypatch, tmp_path):
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    granules = _attrappen_granules(3)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **kwargs: granules)

    aufrufe = []

    def fake_lade_kachel(granule, ziel_ordner):
        aufrufe.append(granule)
        pfad = ziel_ordner / f"kachel_{len(aufrufe)}.h5"
        pfad.touch()
        return pfad

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    dateien = vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=2)
    assert len(dateien) == 3
    assert len(aufrufe) == 3


def test_lade_monat_meldet_kacheln_die_auch_nach_wiederholung_scheitern(monkeypatch, tmp_path):
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    granules = _attrappen_granules(2)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **kwargs: granules)

    def fake_lade_kachel(granule, ziel_ordner):
        raise vnp46a3.DownloadHaengt("simulierter dauerhafter Hänger")

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.DownloadHaengt, match="nicht geladen"):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=2)
