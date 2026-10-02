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
"""

from pathlib import Path

import h5py
import numpy as np
import pytest
import xarray as xr
from earthaccess.exceptions import EulaNotAccepted

from aleph.core import io
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


def _baue_imerg_testdatei(pfad: Path, precip_wert: float, mumbai_lat_idx: int, mumbai_lon_idx: int) -> None:
    """Baut eine HDF5-Datei im (vermutlich) echten IMERG-Layout: time=1, lon=3600, lat=1800.

    Alle Felder sind Fehlwert, außer ein einziges Pixel von `precipitation`
    bei (mumbai_lat_idx, mumbai_lon_idx).
    """
    lat = (-89.95 + 0.1 * np.arange(imerg.QUELL_BREITE)).astype("float32")
    lon = (-179.95 + 0.1 * np.arange(imerg.QUELL_LAENGE)).astype("float32")
    precip = np.full((1, imerg.QUELL_LAENGE, imerg.QUELL_BREITE), imerg.FEHLWERT_DOKU, dtype="float32")
    precip[0, mumbai_lon_idx, mumbai_lat_idx] = precip_wert
    null = np.zeros((1, imerg.QUELL_LAENGE, imerg.QUELL_BREITE), dtype="float32")
    with h5py.File(pfad, "w") as datei:
        gruppe = datei.create_group("Grid")
        gruppe.create_dataset("lat", data=lat)
        gruppe.create_dataset("lon", data=lon)
        gruppe.create_dataset("time", data=np.array([0.0]))
        feld = gruppe.create_dataset("precipitation", data=precip)
        feld.attrs["_FillValue"] = np.float32(imerg.FEHLWERT_DOKU)
        for name in ("randomError", "gaugeRelativeWeighting", "probabilityLiquidPrecipitation",
                     "precipitationQualityIndex"):
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


def test_tage_je_monat_schaltjahre():
    from calendar import monthrange

    assert monthrange(2016, 2)[1] == 29  # Schaltjahr
    assert monthrange(2018, 2)[1] == 28  # kein Schaltjahr


def test_umrechnung_nutzt_tage_des_kalendermonats(tmp_path):
    pfad_feb_2016 = tmp_path / "feb2016.HDF5"
    pfad_feb_2018 = tmp_path / "feb2018.HDF5"
    _baue_imerg_testdatei(pfad_feb_2016, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800)
    _baue_imerg_testdatei(pfad_feb_2018, precip_wert=1.0, mumbai_lat_idx=900, mumbai_lon_idx=1800)

    ds_2016 = imerg._verarbeite_monat(pfad_feb_2016, 2016, 2)
    ds_2018 = imerg._verarbeite_monat(pfad_feb_2018, 2018, 2)
    wert_2016 = np.nanmax(ds_2016["precipitation_mm_monat"].values)
    wert_2018 = np.nanmax(ds_2018["precipitation_mm_monat"].values)
    assert wert_2016 == pytest.approx(1.0 * 24 * 29)
    assert wert_2018 == pytest.approx(1.0 * 24 * 28)


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
