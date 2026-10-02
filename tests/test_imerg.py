"""Tests für den Niederschlags-Layer GPM IMERG (aleph/layers/imerg.py).

Nur Kunstdaten und gemockte Netzaufrufe (schnell, kein echter Netzzugriff,
kein echtes Warten: time.sleep wird in den Wiederholungs-Tests ersetzt).
Eine echte Katalogabfrage gibt es NICHT in diesem Modul (nur im manuellen
Lauf `python -m aleph.layers.imerg --nur-katalog`, siehe LOG.md).

Abdeckung (Auftrag 2026-10-02):
- Regridding-Eigenschaften (konstant, globales Mittel, Fehlwert lokal,
  Null-Feld, Alles-Fehlwert-Feld).
- Achsen-Erkennung/Umdrehen an einer echten HDF5-Datei im erwarteten Layout
  (time=1, lon=3600, lat=1800), ein Pixel bei Mumbai.
- Tage je Kalendermonat (Schaltjahre).
- Fehlwert != 0.
- Katalog-Vollständigkeit (fehlender Monat, Anbieter-Lücke, veraltete Lücke).
- Zeitlimit und Wiederholung mit wachsenden Pausen (Datei und Katalog).
- 403/EULA und 401 -> Blocker; leere Download-Rückgabe -> Fehlschlag.
- Größe falsch -> verworfen und neu geladen / endgültig nicht geladen.
- Würfel schreiben/zurücklesen/Status; Manifest; Gitter identisch mit vnp46a3.

Auflagen statistik-pruefer (2026-10-02, "bestanden mit Auflagen"):
- Attribute im Würfel (Dataset UND je Variable), zurückgelesen aus der Zarr-Datei.
- `probability_liquid` niederschlagsgewichtet (Hand-Rechnung), trockene Zelle -> NaN.
- `quality_index_min` als Minimum (nicht Flächenmittel) über die gültigen Pixel.
- `MINDEST_GUELTIG_ANTEIL`/`nutzbar_maske()`.
- `kalibrierung_trmm`.
- `to_cube()` nur mit manifestgeprüften Rohdateien (inkl. Ablehnung bei falschem sha256).
- Gewichte unabhängig geprüft (Summen, Randpixel-Hälften), nicht konstantes Feld mit
  einem (halben) Fehlwert-Randpixel gegen eine von Hand gerechnete Zelle.
- Absteigende Achsen, Form ohne Zeitachse; ganzzahliges Feld mit Fehlwert -9999.
- Zustände 0/3/5 über `aleph.detect.wuerfel.lies_monate`.
"""

import math
from pathlib import Path

import h5py
import numpy as np
import pytest
import xarray as xr
from earthaccess.exceptions import EulaNotAccepted

from aleph.core import io
from aleph.detect import wuerfel as lesen
from aleph.layers import imerg, vnp46a3


@pytest.fixture
def fake_ssd(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    return tmp_path


# --- Gewichte / Regridding-Eigenschaften ---------------------------------------


def test_gewichte_haben_hoechstens_3_quellpixel_je_zeile_und_volle_laengsueberdeckung():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    assert np.diff(w_lat.indptr).max() <= 3
    assert np.diff(w_lon.indptr).max() <= 3
    # volle Längsüberdeckung: jede Zielzeile deckt genau 5 Ticks (0,25°) ab.
    assert np.allclose(np.asarray(w_lon.sum(axis=1)).reshape(-1), imerg.A_LON_VOLL_TICKS)


def test_konstantes_feld_bleibt_konstant():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    werte = np.full((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), 3.0, dtype="float32")
    gueltig = np.ones_like(werte, dtype=bool)
    zellwert, anteil, pixel = imerg._regrid_feld(werte, gueltig, w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    assert np.allclose(zellwert, 3.0)
    assert np.allclose(anteil, 1.0)
    assert (pixel == 9).all()  # volle Gültigkeit: 3x3 Quellpixel je Zielzelle (Modulkopf)


def test_flaechengewichtetes_globales_mittel_bleibt_bis_auf_rundung_gleich():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    rng = np.random.default_rng(0)
    werte = rng.random((imerg.QUELL_BREITE, imerg.QUELL_LAENGE)).astype("float32")
    gueltig = np.ones_like(werte, dtype=bool)
    zellwert, _, _ = imerg._regrid_feld(werte, gueltig, w_lat, b_lat, w_lon, b_lon, a_lat_voll)

    quell_lat = np.asarray(w_lat.sum(axis=0)).reshape(-1)
    quell_lon = np.asarray(w_lon.sum(axis=0)).reshape(-1)
    quell_mittel = (quell_lat[:, None] * quell_lon[None, :] * werte).sum() / (
        quell_lat[:, None] * quell_lon[None, :]
    ).sum()

    ziel_lon = np.asarray(w_lon.sum(axis=1)).reshape(-1)
    ziel_mittel = (a_lat_voll[:, None] * ziel_lon[None, :] * zellwert).sum() / (
        a_lat_voll[:, None] * ziel_lon[None, :]
    ).sum()
    assert abs(quell_mittel - ziel_mittel) < 1e-6


def test_ein_fehlwert_pixel_senkt_nur_betroffene_zellen_den_anteil():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    gueltig = np.ones((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), dtype=bool)
    gueltig[1090, 2528] = False
    werte = np.full((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), 5.0, dtype="float32")
    zellwert, anteil, pixel = imerg._regrid_feld(werte, gueltig, w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    betroffen = anteil < 1.0
    assert 0 < betroffen.sum() <= 9  # ein Pixel berührt höchstens 2x2=4, hier 1 Zielzelle
    # überall sonst unverändert konstant 5,0 (gültig), bei den betroffenen Zellen
    # bleibt der Zellwert gleich (nur die gültige Fläche sinkt, nicht der Mittelwert).
    assert np.allclose(zellwert[betroffen], 5.0)
    assert np.allclose(zellwert[~betroffen], 5.0)


def test_feld_nur_aus_null_ergibt_null_nicht_nan():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    werte = np.zeros((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), dtype="float32")
    gueltig = np.ones_like(werte, dtype=bool)
    zellwert, anteil, _ = imerg._regrid_feld(werte, gueltig, w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    assert not np.isnan(zellwert).any()
    assert np.allclose(zellwert, 0.0)
    assert np.allclose(anteil, 1.0)


def test_feld_nur_aus_fehlwerten_ergibt_nan():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    gueltig = np.zeros((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), dtype=bool)
    werte = np.full((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), imerg.FEHLWERT_DOKU, dtype="float32")
    zellwert, anteil, pixel = imerg._regrid_feld(werte, gueltig, w_lat, b_lat, w_lon, b_lon, a_lat_voll)
    assert np.isnan(zellwert).all()
    assert np.allclose(anteil, 0.0)
    assert (pixel == 0).all()


# --- Achsen: Erkennung, Umdrehen, Fehlwertmaske --------------------------------


def test_ausrichten_dreht_nur_bei_absteigenden_achsen():
    arr = np.array([[1, 2], [3, 4]])
    lat_auf, lon_auf = np.array([-1.0, 1.0]), np.array([-1.0, 1.0])
    assert np.array_equal(imerg._ausrichten(arr, lat_auf, lon_auf), arr)
    lat_ab = np.array([1.0, -1.0])
    assert np.array_equal(imerg._ausrichten(arr, lat_ab, lon_auf), arr[::-1, :])
    lon_ab = np.array([1.0, -1.0])
    assert np.array_equal(imerg._ausrichten(arr, lat_auf, lon_ab), arr[:, ::-1])


def test_gueltig_maske_unterscheidet_null_von_fehlwert():
    arr = np.array([0.0, imerg.FEHLWERT_DOKU, -1.0, np.nan, 2.5], dtype="float32")
    maske = imerg._gueltig_maske(arr, None)
    assert maske.tolist() == [True, False, False, False, True]


def _baue_imerg_testdatei(
    pfad: Path,
    precip_wert: float,
    mumbai_lat_idx: int,
    mumbai_lon_idx: int,
    random_error_wert: float = 0.0,
) -> None:
    """Baut eine HDF5-Datei im (vermutlich) echten IMERG-Layout: time=1, lon=3600, lat=1800.

    `precipitation` UND `randomError` sind Fehlwert, außer einem einzigen
    Pixel bei (mumbai_lat_idx, mumbai_lon_idx) - so bleibt die flächengewichtete
    Zelle exakt gleich dem eingesetzten Wert (nur ein gültiges Pixel in der
    Zelle). Die übrigen Felder sind überall 0 (gültig).
    """
    lat = (-89.95 + 0.1 * np.arange(imerg.QUELL_BREITE)).astype("float32")
    lon = (-179.95 + 0.1 * np.arange(imerg.QUELL_LAENGE)).astype("float32")
    precip = np.full((1, imerg.QUELL_LAENGE, imerg.QUELL_BREITE), imerg.FEHLWERT_DOKU, dtype="float32")
    precip[0, mumbai_lon_idx, mumbai_lat_idx] = precip_wert
    random_error = np.full((1, imerg.QUELL_LAENGE, imerg.QUELL_BREITE), imerg.FEHLWERT_DOKU, dtype="float32")
    random_error[0, mumbai_lon_idx, mumbai_lat_idx] = random_error_wert
    null = np.zeros((1, imerg.QUELL_LAENGE, imerg.QUELL_BREITE), dtype="float32")
    with h5py.File(pfad, "w") as datei:
        gruppe = datei.create_group("Grid")
        gruppe.create_dataset("lat", data=lat)
        gruppe.create_dataset("lon", data=lon)
        gruppe.create_dataset("time", data=np.array([0.0]))
        feld = gruppe.create_dataset("precipitation", data=precip)
        feld.attrs["_FillValue"] = np.float32(imerg.FEHLWERT_DOKU)
        feld2 = gruppe.create_dataset("randomError", data=random_error)
        feld2.attrs["_FillValue"] = np.float32(imerg.FEHLWERT_DOKU)
        for name in ("gaugeRelativeWeighting", "probabilityLiquidPrecipitation", "precipitationQualityIndex"):
            gruppe.create_dataset(name, data=null)


def test_achsen_erkennung_und_umdrehen_mumbai_pixel_landet_in_richtiger_zelle(tmp_path):
    """Ein Pixel bei 19,05°N/72,85°O (nahe Mumbai) landet in der dazu passenden
    ALEPH-Würfelzelle, nach Achsen-Erkennung (time/lon/lat-Reihenfolge) und
    Umdrehen auf die ALEPH-Konvention (Zeile 0 = Norden)."""
    pfad = tmp_path / "3B-MO.MS.MRG.3IMERG.20180701-S000000-E235959.07.V07B.HDF5"
    # i=1090 -> lat -89,95+0,1*1090 = 19,05; j=2528 -> lon -179,95+0,1*2528 = 72,85
    _baue_imerg_testdatei(pfad, precip_wert=2.5, mumbai_lat_idx=1090, mumbai_lon_idx=2528)

    datensatz = imerg._verarbeite_monat(pfad, 2018, 7)  # Juli: 31 Tage
    werte = datensatz["precipitation_mm_monat"].values[0]
    anteil = datensatz["precipitation_gueltig_anteil"].values[0]

    gueltige_zellen = np.argwhere(~np.isnan(werte))
    assert gueltige_zellen.shape == (1, 2)  # genau eine Zelle betroffen
    zeile, spalte = gueltige_zellen[0]
    assert (zeile, spalte) == (283, 1011)
    assert werte[zeile, spalte] == pytest.approx(2.5 * 24 * 31)  # mm/h -> mm/Monat, Juli = 31 Tage
    assert 0 < anteil[zeile, spalte] <= 1.0

    breite, laenge = imerg._gitter_koordinaten()
    # Die betroffene Zelle muss tatsächlich 19,05°N/72,85°O umschließen.
    assert breite[zeile] - 0.125 <= 19.05 <= breite[zeile] + 0.125
    assert laenge[spalte] - 0.125 <= 72.85 <= laenge[spalte] + 0.125


def test_feld_fehlt_in_der_datei_bricht_mit_achsenfehler_ab(tmp_path):
    pfad = tmp_path / "kaputt.HDF5"
    lat = (-89.95 + 0.1 * np.arange(imerg.QUELL_BREITE)).astype("float32")
    lon = (-179.95 + 0.1 * np.arange(imerg.QUELL_LAENGE)).astype("float32")
    with h5py.File(pfad, "w") as datei:
        gruppe = datei.create_group("Grid")
        gruppe.create_dataset("lat", data=lat)
        gruppe.create_dataset("lon", data=lon)
        # 'precipitation' fehlt absichtlich.
    with pytest.raises(imerg.AchsenFehler, match="precipitation"):
        imerg._lies_monatsdatei(pfad)


def test_achsenpruefung_lehnt_falsche_laenge_ab():
    with pytest.raises(imerg.AchsenFehler):
        imerg._pruefe_achse(np.arange(100, dtype="float64"), 1800, 0.1, -90.0, "lat")


# --- Tage je Kalendermonat (Schaltjahre) ----------------------------------------


def test_umrechnung_nutzt_tage_des_kalendermonats_nicht_die_stdlib_direkt(tmp_path):
    """Ersetzt den früheren rein-stdlib-Test (nur `calendar.monthrange` selbst geprüft):
    dieser Test prüft, dass `_verarbeite_monat` das Ergebnis tatsächlich NUTZT - für
    precipitation UND random_error (dieselbe Umrechnung mm/h -> mm/Monat), an einem
    Schaltjahr (Februar 2016, 29 Tage) gegen ein Nicht-Schaltjahr (Februar 2018, 28 Tage)."""
    pfad_feb_2016 = tmp_path / "feb2016.HDF5"
    pfad_feb_2018 = tmp_path / "feb2018.HDF5"
    _baue_imerg_testdatei(pfad_feb_2016, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800)
    _baue_imerg_testdatei(pfad_feb_2018, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800)

    ds_2016 = imerg._verarbeite_monat(pfad_feb_2016, 2016, 2)
    ds_2018 = imerg._verarbeite_monat(pfad_feb_2018, 2018, 2)
    assert np.nanmax(ds_2016["precipitation_mm_monat"].values) == pytest.approx(1.0 * 24 * 29)
    assert np.nanmax(ds_2018["precipitation_mm_monat"].values) == pytest.approx(1.0 * 24 * 28)
    # random_error wird mit demselben Faktor umgerechnet (randomError=0.0 in der
    # Testdatei, aber die Multiplikation mit 24*Tage darf nicht übersprungen werden -
    # geprüft über eine Datei mit einem randomError ungleich 0 an derselben Stelle).
    pfad_mit_fehler = tmp_path / "feb2016_fehler.HDF5"
    _baue_imerg_testdatei(
        pfad_mit_fehler, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800, random_error_wert=0.5
    )
    ds_fehler = imerg._verarbeite_monat(pfad_mit_fehler, 2016, 2)
    assert np.nanmax(ds_fehler["random_error_mm_monat"].values) == pytest.approx(0.5 * 24 * 29)


# --- Verminderte Güte -----------------------------------------------------------


def test_verminderte_guete_maske_nur_jenseits_60_grad():
    maske = imerg.verminderte_guete_maske()
    breite, _ = imerg._gitter_koordinaten()
    assert maske[np.abs(breite) > 60.0].all()
    assert not maske[np.abs(breite) <= 60.0].any()


# --- Katalog-Vollständigkeit -----------------------------------------------------


class _Granule(dict):
    """Attrappe für ein earthaccess-DataGranule (nur das, was imerg.py nutzt)."""

    def __init__(self, datei: str, groesse_mb: float, erzeugt: str = "2024-01-08T00:00:00.000Z"):
        super().__init__(
            umm={
                "DataGranule": {
                    "ArchiveAndDistributionInformation": [{"Size": groesse_mb, "SizeUnit": "MB"}],
                    "ProductionDateTime": erzeugt,
                }
            }
        )
        self.datei = datei

    def data_links(self):
        return [f"https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGM.07/x/{self.datei}"]


def _dateiname(jahr: int, monat: int) -> str:
    return f"3B-MO.MS.MRG.3IMERG.{jahr:04d}{monat:02d}01-S000000-E235959.{monat:02d}.V07B.HDF5"


def test_katalog_soll_rechnet_mb_in_bytes_um():
    granule = _Granule(_dateiname(2018, 7), 18.288082122802734)
    soll = imerg._katalog_soll(2018, 7, granule)
    assert soll.groesse == round(18.288082122802734 * 1024 * 1024)
    assert soll.datei == _dateiname(2018, 7)
    assert soll.erzeugt == "2024-01-08T00:00:00.000Z"


def test_einordnen_katalog_normaler_monat():
    granule = _Granule(_dateiname(2018, 7), 18.0)
    zustand, soll, grund = imerg._einordnen_katalog(2018, 7, 1, [granule])
    assert zustand == imerg.ZUSTAND_GELADEN
    assert soll is not None and soll.datei == _dateiname(2018, 7)


def test_fehlender_monat_ausserhalb_der_referenz_ist_ein_fehler():
    with pytest.raises(imerg.MonatFehltUnerwartet):
        imerg._einordnen_katalog(2019, 3, 0, [])


def test_bekannte_anbieter_luecke_bekommt_zustand_nicht_vorhanden():
    jahr, monat = sorted(imerg.BEIM_ANBIETER_NICHT_VORHANDEN)[0]
    zustand, soll, grund = imerg._einordnen_katalog(jahr, monat, 0, [])
    assert zustand == imerg.ZUSTAND_NICHT_VORHANDEN
    assert soll is None
    assert grund  # ein Grund wird genannt


def test_wieder_auftauchende_luecke_ist_ein_fehler_referenzliste_veraltet():
    jahr, monat = sorted(imerg.BEIM_ANBIETER_NICHT_VORHANDEN)[0]
    granule = _Granule(_dateiname(jahr, monat), 18.0)
    with pytest.raises(imerg.ReferenzlisteVeraltet):
        imerg._einordnen_katalog(jahr, monat, 1, [granule])


def test_katalog_meldet_mehr_als_ein_granulat_ist_ein_fehler():
    g1 = _Granule(_dateiname(2018, 7), 18.0)
    g2 = _Granule(_dateiname(2018, 7), 18.0)
    with pytest.raises(imerg.KatalogFehler):
        imerg._einordnen_katalog(2018, 7, 2, [g1, g2])


def test_dateiname_monat_muss_zum_angefragten_monat_passen():
    with pytest.raises(imerg.KatalogFehler, match="passt nicht"):
        imerg._pruefe_dateiname(_dateiname(2018, 8), 2018, 7)


# --- Katalogabfrage: Zeitlimit und Wiederholung mit wachsenden Pausen ----------


def test_katalogabfrage_zeitlimit_greift_bei_haengendem_aufruf(monkeypatch):
    monkeypatch.setattr(imerg, "KATALOG_ZEITLIMIT_SEKUNDEN", 0.05)
    monkeypatch.setattr(imerg, "KATALOG_PAUSEN_SEKUNDEN", (0.0, 0.0))  # keine echte Wartezeit nötig
    pausen = []
    monkeypatch.setattr(imerg, "_schlafe_katalog", pausen.append)

    def haengt(jahr, monat):
        import time

        time.sleep(1.0)  # weit über dem (verkürzten) Zeitlimit
        return 1, []

    monkeypatch.setattr(imerg, "_katalog_abfrage_einmal", haengt)
    with pytest.raises(imerg.KatalogFehler, match="Katalogabfrage"):
        imerg._katalog_abfrage(2018, 7)


def test_katalogabfrage_wiederholt_mit_wachsenden_pausen(monkeypatch):
    pausen = []
    monkeypatch.setattr(imerg, "_schlafe_katalog", pausen.append)
    monkeypatch.setattr(imerg, "KATALOG_PAUSEN_SEKUNDEN", (1.0, 2.0, 4.0))

    def scheitert_immer(jahr, monat):
        raise RuntimeError("CMR nicht erreichbar")

    monkeypatch.setattr(imerg, "_katalog_abfrage_einmal", scheitert_immer)
    with pytest.raises(imerg.KatalogFehler):
        imerg._katalog_abfrage(2018, 7)
    assert pausen == [1.0, 2.0, 4.0]  # wachsend, wie konfiguriert; kein echtes Warten


def test_katalogabfrage_meldet_jede_wiederholung(monkeypatch):
    monkeypatch.setattr(imerg, "_schlafe_katalog", lambda s: None)
    monkeypatch.setattr(imerg, "KATALOG_PAUSEN_SEKUNDEN", (1.0,))
    aufrufe = {"n": 0}

    def einmal_scheitern_dann_klappen(jahr, monat):
        aufrufe["n"] += 1
        if aufrufe["n"] == 1:
            raise RuntimeError("kurzer Hänger")
        return 1, [_Granule(_dateiname(jahr, monat), 18.0)]

    monkeypatch.setattr(imerg, "_katalog_abfrage_einmal", einmal_scheitern_dann_klappen)
    meldungen = []
    gemeldet, granules = imerg._katalog_abfrage(2018, 7, melde=meldungen.append)
    assert gemeldet == 1 and len(granules) == 1
    assert any("Versuch 2" in m for m in meldungen)


# --- Dateidownload: Zeitlimit, Wiederholung, Blocker, leere Liste --------------


def _soll(jahr=2018, monat=7, groesse=18_000_000):
    return imerg.MonatsSoll(_dateiname(jahr, monat), groesse, "2024-01-08T00:00:00.000Z")


def test_datei_zeitlimit_greift_bei_haengendem_download(monkeypatch):
    monkeypatch.setattr(imerg, "DATEI_ZEITLIMIT_MINDEST_SEKUNDEN", 0.05)
    monkeypatch.setattr(imerg, "DATEI_RETRY_BUDGET_SEKUNDEN", 0.2)
    monkeypatch.setattr(imerg, "_schlafe_datei", lambda s: None)

    def haengt(granules, ordner):
        import time

        time.sleep(1.0)
        return [str(Path(ordner) / granules[0].datei)]

    monkeypatch.setattr(imerg.earthaccess, "download", haengt)
    with pytest.raises(imerg.MonatNichtGeladen):
        imerg._lade_monatsdatei(_Granule(_dateiname(2018, 7), 18.0), _soll(groesse=None), Path("/tmp"))


def test_datei_wiederholung_mit_wachsenden_pausen_bis_budget_erschoepft(monkeypatch, tmp_path):
    pausen = []
    monkeypatch.setattr(imerg, "_schlafe_datei", pausen.append)

    def scheitert_mit_serverfehler(granules, ordner):
        raise imerg.DownloadFailure("Download failed for x. Status code: 502")

    monkeypatch.setattr(imerg.earthaccess, "download", scheitert_mit_serverfehler)
    with pytest.raises(imerg.MonatNichtGeladen):
        imerg._lade_monatsdatei(_Granule(_dateiname(2018, 7), 18.0), _soll(), tmp_path)
    assert len(pausen) >= 3
    assert pausen[0] == imerg.DATEI_WARTEZEIT_BASIS_SEKUNDEN
    assert pausen[1] == imerg.DATEI_WARTEZEIT_BASIS_SEKUNDEN * 2
    assert pausen == sorted(pausen)  # wachsend
    assert max(pausen) <= imerg.DATEI_WARTEZEIT_MAX_SEKUNDEN


def test_404_gibt_sofort_auf_ohne_wartezeit(monkeypatch, tmp_path):
    pausen = []
    monkeypatch.setattr(imerg, "_schlafe_datei", pausen.append)

    def nicht_gefunden(granules, ordner):
        raise imerg.DownloadFailure("Download failed for x. Status code: 404")

    monkeypatch.setattr(imerg.earthaccess, "download", nicht_gefunden)
    with pytest.raises(imerg.MonatNichtGeladen) as info:
        imerg._lade_monatsdatei(_Granule(_dateiname(2018, 7), 18.0), _soll(), tmp_path)
    assert info.value.dauerhaft is True
    assert pausen == []  # kein einziger Wiederholungsversuch


def test_401_ist_ein_blocker(monkeypatch, tmp_path):
    def abgelehnt(granules, ordner):
        raise imerg.DownloadFailure("Download failed for x. Status code: 401")

    monkeypatch.setattr(imerg.earthaccess, "download", abgelehnt)
    with pytest.raises(imerg.EarthdataZugangVerweigert, match="approve_app"):
        imerg._lade_monatsdatei(_Granule(_dateiname(2018, 7), 18.0), _soll(), tmp_path)


def test_403_mit_eula_ist_ein_blocker(monkeypatch, tmp_path):
    def eula_fehler(granules, ordner):
        raise EulaNotAccepted("Eula Acceptance Failure for https://...")

    monkeypatch.setattr(imerg.earthaccess, "download", eula_fehler)
    with pytest.raises(imerg.EarthdataZugangVerweigert, match="approve_app"):
        imerg._lade_monatsdatei(_Granule(_dateiname(2018, 7), 18.0), _soll(), tmp_path)


def test_leere_rueckgabeliste_gilt_als_fehlschlag_nicht_als_erfolg(monkeypatch, tmp_path):
    monkeypatch.setattr(imerg, "DATEI_RETRY_BUDGET_SEKUNDEN", 0.0)
    monkeypatch.setattr(imerg, "_schlafe_datei", lambda s: None)

    def leere_liste(granules, ordner):
        return []

    monkeypatch.setattr(imerg.earthaccess, "download", leere_liste)
    with pytest.raises(imerg.MonatNichtGeladen):
        imerg._lade_monatsdatei(_Granule(_dateiname(2018, 7), 18.0), _soll(), tmp_path)


# --- Rohdatei-Prüfung: falsche Größe wird verworfen -----------------------------


def test_vorhandene_datei_mit_falscher_groesse_wird_verworfen_und_neu_geladen(monkeypatch, tmp_path):
    # Die HDF5-Lesbarkeitsprüfung wird hier ausgeklammert (eigener Test oben:
    # test_nach_drei_falschen_downloads_gilt_die_datei_als_nicht_geladen prüft
    # den unveränderten, echten Pfad inklusive HDF5-Prüfung); dieser Test
    # prüft gezielt nur die Größenprüfung und das Verwerfen/Neuladen.
    monkeypatch.setattr(imerg, "_ist_lesbare_hdf5", lambda pfad: True)
    soll = _soll(groesse=10)
    vorhanden = tmp_path / soll.datei
    vorhanden.write_bytes(b"x" * 999)  # falsche Größe

    def schreibe_richtige_datei(granules, ordner):
        ziel = Path(ordner) / granules[0].datei
        ziel.write_bytes(b"x" * soll.groesse)
        return [str(ziel)]

    monkeypatch.setattr(imerg.earthaccess, "download", schreibe_richtige_datei)
    granule = _Granule(soll.datei, 18.0)
    pfad = imerg.hole_monatsdatei(2018, 7, soll, granule, tmp_path)
    assert pfad.read_bytes() == b"x" * soll.groesse


def test_nach_drei_falschen_downloads_gilt_die_datei_als_nicht_geladen(monkeypatch, tmp_path):
    soll = _soll(groesse=10)

    def immer_falsche_groesse(granules, ordner):
        ziel = Path(ordner) / granules[0].datei
        ziel.write_bytes(b"x" * 3)
        return [str(ziel)]

    monkeypatch.setattr(imerg.earthaccess, "download", immer_falsche_groesse)
    granule = _Granule(soll.datei, 18.0)
    with pytest.raises(imerg.MonatNichtGeladen, match="3 Versuchen"):
        imerg.hole_monatsdatei(2018, 7, soll, granule, tmp_path)
    assert not (tmp_path / soll.datei).exists()


# --- Würfel: schreiben, zurücklesen, Status -------------------------------------


def _monatsdaten(jahr: int, monat: int, wert: float) -> xr.Dataset:
    breite, laenge = imerg._gitter_koordinaten()
    variablen = {}
    for name, dtyp in imerg._wuerfel_variablen().items():
        variablen[name] = (
            imerg.WUERFEL_DIMS,
            np.full((1, len(breite), len(laenge)), wert, dtype=dtyp),
        )
    return xr.Dataset(
        variablen,
        coords={"zeit": [np.datetime64(f"{jahr:04d}-{monat:02d}-01")], "breite": breite, "laenge": laenge},
    )


def test_schreiben_zurücklesen_status(fake_ssd):
    assert imerg.monatsstatus(2018, 7) == imerg.MONAT_LEER
    imerg.schreibe_in_wuerfel(_monatsdaten(2018, 7, 42.0))
    assert imerg.monatsstatus(2018, 7) == imerg.MONAT_FERTIG
    assert imerg.vorhandene_monate() == {(2018, 7)}
    with xr.open_zarr(imerg._wuerfel_pfad(), chunks=None) as ds:
        assert float(ds["precipitation_mm_monat"].isel(zeit=imerg._monat_index(2018, 7)).values.max()) == 42.0


def test_fertiger_monat_wird_nicht_ueberschrieben(fake_ssd):
    imerg.schreibe_in_wuerfel(_monatsdaten(2018, 7, 1.0))
    with pytest.raises(imerg.MonatSchonVorhanden):
        imerg.schreibe_in_wuerfel(_monatsdaten(2018, 7, 2.0))


def test_monat_ausserhalb_der_zeitachse_bricht_ab(fake_ssd):
    with pytest.raises(imerg.MonatAusserhalbZeitachse):
        imerg._monat_index(2026, 1)


def test_setze_nicht_vorhanden_nur_fuer_referenzierte_monate(fake_ssd):
    jahr, monat = sorted(imerg.BEIM_ANBIETER_NICHT_VORHANDEN)[0]
    imerg.setze_nicht_vorhanden(jahr, monat)
    assert imerg.monatsstatus(jahr, monat) == imerg.MONAT_NICHT_VORHANDEN
    assert imerg.vorhandene_monate() == set()  # zählt nicht als vorhanden
    with pytest.raises(ValueError):
        imerg.setze_nicht_vorhanden(2018, 7)  # nicht in der Referenzliste


def test_setze_nicht_vorhanden_widerspricht_vorhandenen_daten(fake_ssd):
    jahr, monat = sorted(imerg.BEIM_ANBIETER_NICHT_VORHANDEN)[0]
    imerg.schreibe_in_wuerfel(_monatsdaten(jahr, monat, 1.0))
    with pytest.raises(imerg.MonatSchonVorhanden):
        imerg.setze_nicht_vorhanden(jahr, monat)


# --- Manifest --------------------------------------------------------------------


def test_manifest_schreiben_und_lesen_hat_alle_156_monate(fake_ssd):
    zeilen = {
        (2018, 7): imerg.ManifestZeile("2018-07", imerg.ZUSTAND_GELADEN, datei="x.HDF5"),
        (2025, 10): imerg.ManifestZeile("2025-10", imerg.ZUSTAND_NICHT_VORHANDEN, grund="Lücke"),
    }
    pfad = imerg.schreibe_manifest(zeilen)
    assert pfad.exists()
    assert not pfad.with_suffix(".tsv.tmp").exists()  # Hilfsdatei wurde umbenannt, nicht liegen gelassen
    gelesen = imerg.lies_manifest()
    assert len(gelesen) == 156
    assert gelesen[(2018, 7)].zustand == imerg.ZUSTAND_GELADEN
    assert gelesen[(2025, 10)].zustand == imerg.ZUSTAND_NICHT_VORHANDEN
    # alle nicht genannten Monate: "nicht geladen", nie "keine Daten".
    assert gelesen[(2013, 1)].zustand == imerg.ZUSTAND_NICHT_GELADEN
    assert gelesen[(2013, 1)].grund == "noch nicht verarbeitet"


# --- Gitter identisch mit vnp46a3 ------------------------------------------------


def test_gitter_identisch_mit_vnp46a3():
    breite, laenge = imerg._gitter_koordinaten()
    b2, l2 = vnp46a3._gitter_koordinaten()
    assert np.array_equal(breite, b2)
    assert np.array_equal(laenge, l2)
    assert imerg.GITTER_BREITE == 720 and imerg.GITTER_LAENGE == 1440


def test_gitter_identisch_mit_echtem_vnp46a3_wuerfel_auf_ssd():
    try:
        pfad = io.wuerfel_pfad("vnp46a3.zarr")
    except io.SSDNichtGefunden:
        pytest.skip("SSD nicht angeschlossen; echter Würfel-Vergleich übersprungen.")
    if not pfad.exists():
        pytest.skip("Kein echter Nachtlicht-Würfel auf der SSD gefunden.")
    with xr.open_zarr(pfad, chunks=None) as ds:
        breite_echt = ds["breite"].values
        laenge_echt = ds["laenge"].values
    breite, laenge = imerg._gitter_koordinaten()
    assert np.allclose(breite, breite_echt)
    assert np.allclose(laenge, laenge_echt)


# --- Zeitachse / Monatsliste -----------------------------------------------------


def test_monatsliste_umfang():
    monate = imerg._monatsliste("2013-01", "2025-12")
    assert len(monate) == 156
    assert monate[0] == (2013, 1) and monate[-1] == (2025, 12)


# --- Auflagen statistik-pruefer 2026-10-02 --------------------------------------


# --- Punkt 1: Attribute im Würfel ------------------------------------------------


def test_wuerfel_hat_dataset_und_variablen_attribute(fake_ssd):
    breite, laenge = imerg._gitter_koordinaten()
    variablen = {}
    for name, dtyp in imerg._wuerfel_variablen().items():
        variablen[name] = (imerg.WUERFEL_DIMS, np.full((1, len(breite), len(laenge)), 1.0, dtype=dtyp))
    ds = xr.Dataset(
        variablen, coords={"zeit": [np.datetime64("2018-07-01")], "breite": breite, "laenge": laenge}
    )
    imerg.schreibe_in_wuerfel(ds)

    with xr.open_zarr(imerg._wuerfel_pfad(), chunks=None) as cube:
        # Dataset-Attribute (Quelle, DOI, Version, Zitierweise).
        assert cube.attrs["doi"] == "10.5067/GPM/IMERG/3B-MONTH/07"
        assert cube.attrs["version"] == "V07B"
        assert "Huffman" in cube.attrs["zitierweise"]
        assert "GES DISC" in cube.attrs["quelle"]

        # Je-Variable-Attribute.
        precip_attrs = cube["precipitation_mm_monat"].attrs
        assert precip_attrs["einheit"] == "mm/Monat"
        assert "beobachtet" in precip_attrs["evidenzstufe"]
        assert str(imerg.MINDEST_GUELTIG_ANTEIL) in precip_attrs["mindest_gueltig_anteil_hinweis"]

        fehler_attrs = cube["random_error_mm_monat"].attrs
        assert "exakt bei voll korrelierten Pixelfehlern" in fehler_attrs["genauigkeit"]
        assert "Obergrenze" in fehler_attrs["genauigkeit"]

        qualitaet_attrs = cube["quality_index_min"].attrs
        assert "Minimum" in qualitaet_attrs["beschreibung"]
        assert "rot" in qualitaet_attrs["beschreibung"] and "grün" in qualitaet_attrs["beschreibung"]

        fluessig_attrs = cube["probability_liquid"].attrs
        assert "niederschlagsgewichtet" in fluessig_attrs["aggregation"]

        kalib_attrs = cube["kalibrierung_trmm"].attrs
        assert "2014-06" in kalib_attrs["beschreibung"]


def test_region_write_behaelt_die_variablen_attribute_trotzdem(fake_ssd):
    """Die eigentliche Auflage: `schreibe_in_wuerfel` (Region-Write) darf die beim
    Anlegen gesetzten Attribute nicht verlieren (sie werden nicht dort, sondern in
    `_lege_wuerfel_an` gesetzt - ein zweiter Monat beweist, dass sie erhalten bleiben)."""
    breite, laenge = imerg._gitter_koordinaten()
    variablen = {}
    for name, dtyp in imerg._wuerfel_variablen().items():
        variablen[name] = (imerg.WUERFEL_DIMS, np.full((1, len(breite), len(laenge)), 2.0, dtype=dtyp))
    ds1 = xr.Dataset(
        variablen, coords={"zeit": [np.datetime64("2018-07-01")], "breite": breite, "laenge": laenge}
    )
    imerg.schreibe_in_wuerfel(ds1)
    ds2 = xr.Dataset(
        variablen, coords={"zeit": [np.datetime64("2018-08-01")], "breite": breite, "laenge": laenge}
    )
    imerg.schreibe_in_wuerfel(ds2)  # zweiter Region-Write
    with xr.open_zarr(imerg._wuerfel_pfad(), chunks=None) as cube:
        assert cube.attrs["doi"] == "10.5067/GPM/IMERG/3B-MONTH/07"
        assert cube["precipitation_mm_monat"].attrs["einheit"] == "mm/Monat"


# --- Punkt 2: probability_liquid niederschlagsgewichtet --------------------------


def _lat_gewicht(t0: int, t1: int) -> float:
    return math.sin(math.radians(-90.0 + t1 * 0.05)) - math.sin(math.radians(-90.0 + t0 * 0.05))


def test_probability_liquid_niederschlagsgewichtet_von_hand_nachgerechnet():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    n_lat, n_lon = imerg.QUELL_BREITE, imerg.QUELL_LAENGE
    probliquid = np.zeros((n_lat, n_lon))
    pl_gueltig = np.zeros((n_lat, n_lon), dtype=bool)
    niederschlag = np.zeros((n_lat, n_lon))
    ns_gueltig = np.zeros((n_lat, n_lon), dtype=bool)

    block_probliquid = {(0, 0): 10.0, (0, 1): 20.0, (0, 2): 30.0, (1, 0): 40.0, (1, 1): 50.0,
                         (1, 2): 60.0, (2, 0): 70.0, (2, 1): 80.0, (2, 2): 90.0}
    block_precip = {(0, 0): 1.0, (0, 1): 0.0, (0, 2): 2.0, (1, 0): 0.0, (1, 1): 3.0,
                     (1, 2): 0.0, (2, 0): 4.0, (2, 1): 0.0, (2, 2): 5.0}
    for k, v in block_probliquid.items():
        probliquid[k] = v
        pl_gueltig[k] = True
    for k, v in block_precip.items():
        niederschlag[k] = v
        ns_gueltig[k] = True

    zellwert = imerg._regrid_niederschlagsgewichtet(
        probliquid, pl_gueltig, niederschlag, ns_gueltig, w_lat, w_lon
    )

    wl = {0: _lat_gewicht(0, 2), 1: _lat_gewicht(2, 4), 2: _lat_gewicht(4, 5)}
    wlon = {0: 2.0, 1: 2.0, 2: 1.0}
    gewicht = {k: wl[k[0]] * wlon[k[1]] for k in block_probliquid}
    zaehler = sum(gewicht[k] * block_probliquid[k] * block_precip[k] for k in block_probliquid)
    nenner = sum(gewicht[k] * block_precip[k] for k in block_probliquid)
    assert zellwert[0, 0] == pytest.approx(zaehler / nenner, rel=1e-6)


def test_probability_liquid_trockene_zelle_ist_nan_nicht_0():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    n_lat, n_lon = imerg.QUELL_BREITE, imerg.QUELL_LAENGE
    probliquid = np.full((n_lat, n_lon), 42.0)
    pl_gueltig = np.ones((n_lat, n_lon), dtype=bool)
    niederschlag = np.zeros((n_lat, n_lon))  # überall trocken
    ns_gueltig = np.ones((n_lat, n_lon), dtype=bool)
    zellwert = imerg._regrid_niederschlagsgewichtet(
        probliquid, pl_gueltig, niederschlag, ns_gueltig, w_lat, w_lon
    )
    assert np.isnan(zellwert).all()


# --- Punkt 3: quality_index_min als Minimum --------------------------------------


def test_quality_index_minimum_statt_flaechenmittel():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    n_lat, n_lon = imerg.QUELL_BREITE, imerg.QUELL_LAENGE
    werte = np.full((n_lat, n_lon), 99.0)
    gueltig = np.ones((n_lat, n_lon), dtype=bool)
    werte[1, 1] = 3.0  # eine schwache Stelle in der 3x3-Zelle (0,0)
    ergebnis = imerg._regrid_minimum(werte, gueltig)
    assert ergebnis[0, 0] == pytest.approx(3.0)  # Minimum, nicht das (hohe) Flächenmittel


def test_quality_index_minimum_ohne_gueltigen_pixel_ist_nan():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    n_lat, n_lon = imerg.QUELL_BREITE, imerg.QUELL_LAENGE
    werte = np.zeros((n_lat, n_lon))
    gueltig = np.zeros((n_lat, n_lon), dtype=bool)
    ergebnis = imerg._regrid_minimum(werte, gueltig)
    assert np.isnan(ergebnis).all()


# --- Punkt 4: MINDEST_GUELTIG_ANTEIL / nutzbar_maske ------------------------------


def test_nutzbar_maske_wendet_die_schwelle_an():
    ds = xr.Dataset({"precipitation_gueltig_anteil": (("zeit",), np.array([0.3, 0.5, 0.9]))})
    maske = imerg.nutzbar_maske(ds)
    assert maske.values.tolist() == [False, True, True]  # 0,5 ist >= Schwelle (0,5)


def test_mindest_gueltig_anteil_ist_ueber_0_5():
    assert imerg.MINDEST_GUELTIG_ANTEIL == 0.5


# --- Punkt 7: Kalibrierung TRMM -> GPM -------------------------------------------


def test_kalibrierung_trmm_variable_im_wuerfel(fake_ssd):
    breite, laenge = imerg._gitter_koordinaten()
    variablen = {}
    for name, dtyp in imerg._wuerfel_variablen().items():
        variablen[name] = (imerg.WUERFEL_DIMS, np.full((1, len(breite), len(laenge)), 1.0, dtype=dtyp))
    ds = xr.Dataset(
        variablen, coords={"zeit": [np.datetime64("2018-07-01")], "breite": breite, "laenge": laenge}
    )
    imerg.schreibe_in_wuerfel(ds)
    with xr.open_zarr(imerg._wuerfel_pfad(), chunks=None) as cube:
        kalib = cube["kalibrierung_trmm"].values
        zeit = cube["zeit"].values
    for z, k in zip(zeit, kalib):
        datum = np.datetime64(z, "M").astype(object)
        erwartet = 1 if (datum.year, datum.month) < imerg.KALIBRIERUNG_GPM_AB else 0
        assert int(k) == erwartet


# --- Punkt 6: to_cube nur mit manifestgeprüften Rohdateien -----------------------


def test_to_cube_verarbeitet_nur_mit_passendem_manifest(fake_ssd):
    jahr, monat = 2018, 7
    datei_name = _dateiname(jahr, monat)
    ordner = io.rohdaten_pfad("imerg", imerg.DATEI_VERSION_TEXT, f"{jahr:04d}")
    ordner.mkdir(parents=True)
    pfad = ordner / datei_name
    _baue_imerg_testdatei(pfad, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800)
    groesse = pfad.stat().st_size
    sha = imerg._sha256(pfad)
    manifest = {
        (jahr, monat): imerg.ManifestZeile(
            f"{jahr:04d}-{monat:02d}", imerg.ZUSTAND_GELADEN, datei=datei_name,
            groesse_bytes_gemessen=str(groesse), sha256=sha,
        )
    }
    imerg.schreibe_manifest(manifest)
    verarbeitet = imerg.to_cube()
    assert verarbeitet == [(jahr, monat)]
    assert imerg.monatsstatus(jahr, monat) == imerg.MONAT_FERTIG


def test_to_cube_lehnt_datei_mit_falschem_sha256_ab(fake_ssd):
    jahr, monat = 2018, 8
    datei_name = _dateiname(jahr, monat)
    ordner = io.rohdaten_pfad("imerg", imerg.DATEI_VERSION_TEXT, f"{jahr:04d}")
    ordner.mkdir(parents=True)
    pfad = ordner / datei_name
    _baue_imerg_testdatei(pfad, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800)
    groesse = pfad.stat().st_size
    manifest = {
        (jahr, monat): imerg.ManifestZeile(
            f"{jahr:04d}-{monat:02d}", imerg.ZUSTAND_GELADEN, datei=datei_name,
            groesse_bytes_gemessen=str(groesse), sha256="0" * 64,
        )
    }
    imerg.schreibe_manifest(manifest)
    verarbeitet = imerg.to_cube()
    assert verarbeitet == []
    assert imerg.monatsstatus(jahr, monat) == imerg.MONAT_LEER


def test_to_cube_ueberspringt_datei_ohne_manifesteintrag(fake_ssd):
    jahr, monat = 2018, 9
    ordner = io.rohdaten_pfad("imerg", imerg.DATEI_VERSION_TEXT, f"{jahr:04d}")
    ordner.mkdir(parents=True)
    pfad = ordner / _dateiname(jahr, monat)
    _baue_imerg_testdatei(pfad, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800)
    # kein Manifesteintrag geschrieben
    verarbeitet = imerg.to_cube()
    assert verarbeitet == []
    assert imerg.monatsstatus(jahr, monat) == imerg.MONAT_LEER


def test_pruefe_gegen_manifest_erkennt_falschen_zustand(tmp_path):
    pfad = tmp_path / "x.HDF5"
    pfad.write_bytes(b"abc")
    eintrag = imerg.ManifestZeile("2018-07", imerg.ZUSTAND_NICHT_GELADEN, datei="x.HDF5")
    grund = imerg._pruefe_gegen_manifest(pfad, eintrag)
    assert grund is not None and "Zustand" in grund


# --- Punkt 5: Zustand 5 (und 0, 3) über wuerfel.lies_monate ----------------------


def _wuerfel_mit_zustaenden(tmp_path, zustaende: dict[tuple[int, int], int]) -> Path:
    """Baut einen Mini-Würfel (nur FERTIG_VARIABLE + eine Variable) für aleph.detect.wuerfel-Tests."""
    zeit = [np.datetime64(f"{j:04d}-{m:02d}-01") for j, m in sorted(zustaende)]
    werte = [zustaende[(np.datetime64(z, "M").astype(object).year, np.datetime64(z, "M").astype(object).month)] for z in zeit]
    ds = xr.Dataset(
        {
            "precipitation_mm_monat": (("zeit", "breite", "laenge"), np.zeros((len(zeit), 2, 2))),
            lesen.FERTIG_VARIABLE: (("zeit",), np.array(werte, dtype="int8")),
        },
        coords={"zeit": zeit, "breite": [0.0, 1.0], "laenge": [0.0, 1.0]},
    )
    pfad = tmp_path / "mini.zarr"
    ds.to_zarr(pfad, mode="w")
    return pfad


def test_zustaende_0_3_5_melden_monat_nicht_fertig_mit_passendem_text(tmp_path):
    pfad = _wuerfel_mit_zustaenden(
        tmp_path,
        {
            (2018, 1): imerg.MONAT_LEER,
            (2018, 2): imerg.MONAT_WIRD_GESCHRIEBEN,
            (2018, 3): imerg.MONAT_NICHT_VORHANDEN,
            (2018, 4): imerg.MONAT_FERTIG,
        },
    )
    with pytest.raises(lesen.MonatNichtFertig) as info:
        lesen.lies_monate(pfad, [(2018, 1), (2018, 2), (2018, 3)], ["precipitation_mm_monat"])
    text = str(info.value)
    assert "2018-01 (nicht geladen)" in text
    assert "2018-02 (wird gerade geschrieben)" in text
    assert "2018-03 (beim Anbieter nicht vorhanden)" in text


def test_monat_zustaende_liefert_rohwerte(tmp_path):
    pfad = _wuerfel_mit_zustaenden(tmp_path, {(2018, 1): 0, (2018, 2): 5})
    zustaende = lesen.monat_zustaende(pfad)
    assert zustaende[(2018, 1)] == 0
    assert zustaende[(2018, 2)] == 5


# --- Punkt 8: Gewichte unabhängig geprüft ----------------------------------------


def test_summe_a_lat_voll_ist_2_sin_90_minus_sin_minus_90():
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    assert a_lat_voll.sum() == pytest.approx(2.0, abs=1e-10)  # sin(90°)-sin(-90°) = 1-(-1) = 2


def test_lat_spaltensummen_entsprechen_unabhaengig_berechneter_sin_differenz():
    """Spaltensummen von W_lat (über alle Zielzeilen) = sin(φ+0,05°) - sin(φ-0,05°)
    des jeweiligen Quellpixels selbst - unabhängig von der Produktionslogik neu
    berechnet (nicht über `_eindimensionale_ueberlappung`)."""
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    quell_summen = np.asarray(w_lat.sum(axis=0)).reshape(-1)
    i = np.arange(imerg.QUELL_BREITE)
    mitte = -89.95 + 0.1 * i
    erwartet = np.sin(np.radians(mitte + 0.05)) - np.sin(np.radians(mitte - 0.05))
    assert np.allclose(quell_summen, erwartet, atol=1e-10)


def test_randpixel_wird_in_laengsrichtung_zu_genau_haelfte_je_nachbarzelle_geteilt():
    """Jeder 3. Quellpixel (0,1-Index 2, 7, 12, ...) liegt genau auf der Grenze
    zweier 0,25°-Zielzellen und wird dort je zur Hälfte (1 von 2 Ticks) gewertet."""
    w_lat, b_lat, w_lon, b_lon, a_lat_voll = imerg._gewichte()
    spalte = np.asarray(w_lon.tocsc()[:, 2].todense()).reshape(-1)
    treffer = np.flatnonzero(spalte)
    assert len(treffer) == 2
    assert np.allclose(spalte[treffer], 1.0)  # je die Hälfte des vollen Gewichts (2 Ticks)
    assert list(treffer) == [0, 1]  # Nachbarzellen 0 und 1


# --- Punkt 8: Achsen absteigend, Form ohne Zeitachse, ganzzahliger Fehlwert ------


def test_lies_monatsdatei_mit_absteigenden_achsen_und_2d_feld_ohne_zeitachse(tmp_path):
    """Lat/Lon von Nord nach Süd bzw. Ost nach West gespeichert, UND das Feld hat die
    Form (lat, lon) direkt, ohne führende Zeit-Dimension - beides muss erkannt und
    richtig ausgerichtet werden (von Anfang bis Ende: über `_lies_monatsdatei`)."""
    pfad = tmp_path / "absteigend.HDF5"
    lat_absteigend = (89.95 - 0.1 * np.arange(imerg.QUELL_BREITE)).astype("float32")  # Nord -> Süd
    lon_absteigend = (179.95 - 0.1 * np.arange(imerg.QUELL_LAENGE)).astype("float32")  # Ost -> West
    # i=1090 (Süd->Nord-Index 1090 = 19,05°N) liegt an absteigender Position 1800-1-1090=709
    precip = np.full((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), imerg.FEHLWERT_DOKU, dtype="float32")
    precip[709, 3600 - 1 - 2528] = 7.0  # (lat_abst_idx, lon_abst_idx) für (19,05°N, 72,85°O)
    null = np.zeros((imerg.QUELL_BREITE, imerg.QUELL_LAENGE), dtype="float32")
    with h5py.File(pfad, "w") as datei:
        gruppe = datei.create_group("Grid")
        gruppe.create_dataset("lat", data=lat_absteigend)
        gruppe.create_dataset("lon", data=lon_absteigend)
        feld = gruppe.create_dataset("precipitation", data=precip)
        feld.attrs["_FillValue"] = np.float32(imerg.FEHLWERT_DOKU)
        for name in ("randomError", "gaugeRelativeWeighting", "probabilityLiquidPrecipitation",
                     "precipitationQualityIndex"):
            gruppe.create_dataset(name, data=null)

    felder = imerg._lies_monatsdatei(pfad)
    werte, gueltig = felder["precipitation"]
    assert werte.shape == (imerg.QUELL_BREITE, imerg.QUELL_LAENGE)
    # nach dem Ausrichten (aufsteigend Süd->Nord, West->Ost) steht der Wert bei (1090, 2528).
    treffer = np.argwhere(gueltig)
    assert treffer.tolist() == [[1090, 2528]]
    assert werte[1090, 2528] == pytest.approx(7.0)


def test_ganzzahliges_feld_mit_fehlwert_minus_9999_fillvalue_ungleich_minus_9999_9(tmp_path):
    """`_FillValue` ist hier ein Ganzzahl-Fehlwert (-9999, nicht -9999,9 wie in der
    Doku) - muss trotzdem als Fehlwert erkannt werden, nicht nur der Dokuwert."""
    pfad = tmp_path / "ganzzahl.HDF5"
    lat = (-89.95 + 0.1 * np.arange(imerg.QUELL_BREITE)).astype("float32")
    lon = (-179.95 + 0.1 * np.arange(imerg.QUELL_LAENGE)).astype("float32")
    precip = np.full((1, imerg.QUELL_LAENGE, imerg.QUELL_BREITE), -9999, dtype="int32")
    precip[0, 1800, 900] = 5  # ein gültiger Pixel irgendwo in der Mitte
    with h5py.File(pfad, "w") as datei:
        gruppe = datei.create_group("Grid")
        gruppe.create_dataset("lat", data=lat)
        gruppe.create_dataset("lon", data=lon)
        feld = gruppe.create_dataset("precipitation", data=precip)
        feld.attrs["_FillValue"] = np.int32(-9999)
        null = np.zeros((1, imerg.QUELL_LAENGE, imerg.QUELL_BREITE), dtype="float32")
        for name in ("randomError", "gaugeRelativeWeighting", "probabilityLiquidPrecipitation",
                     "precipitationQualityIndex"):
            gruppe.create_dataset(name, data=null)

    felder = imerg._lies_monatsdatei(pfad)
    werte, gueltig = felder["precipitation"]
    assert gueltig.sum() == 1
    assert werte[900, 1800] == pytest.approx(5.0)
