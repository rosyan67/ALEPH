"""Prüft die Verkleinerungs-Logik des Layers VNP46A3 mit synthetischen Kacheln.

Keine echten NASA-Daten, kein Netzzugriff. Die erwarteten Zahlen sind von
Hand nachgerechnet (siehe Kommentare), nicht nur gegen den Code selbst
geprüft.
"""

import sys
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


def _katalog(positionen):
    return {
        p: vnp46a3.KachelSoll(f"VNP46A3.A2024001.{p}.002.2025000000000.h5", 100, "0" * 32) for p in positionen
    }


REFERENZ = {"h00v00", "h01v00", "h02v00", "h03v00"}


def test_pruefe_vollstaendigkeit_akzeptiert_vollstaendigen_monat_und_kennzeichnet_fehlende_beim_anbieter():
    katalog = _katalog(["h00v00", "h01v00", "h02v00"])  # h03v00 gibt es im Juni beim Anbieter nicht
    geladen = {p: Path(s.datei) for p, s in katalog.items()}
    zustaende = vnp46a3.pruefe_vollstaendigkeit(2024, 6, 3, katalog, geladen, REFERENZ)
    assert {p: e.zustand for p, e in zustaende.items()} == {
        "h00v00": vnp46a3.ZUSTAND_GELADEN,
        "h01v00": vnp46a3.ZUSTAND_GELADEN,
        "h02v00": vnp46a3.ZUSTAND_GELADEN,
        "h03v00": vnp46a3.ZUSTAND_NICHT_BEIM_ANBIETER,
    }


def test_pruefe_vollstaendigkeit_erkennt_nicht_geladene_kachel():
    """Der alte Fehler: gegen die eigene (abgeschnittene) Liste geprüft, galt ein Monat mit Lücke als fertig."""
    katalog = _katalog(["h00v00", "h01v00", "h02v00"])
    geladen = {"h00v00": Path(katalog["h00v00"].datei), "h02v00": Path(katalog["h02v00"].datei)}
    with pytest.raises(vnp46a3.MonatUnvollstaendig) as info:
        vnp46a3.pruefe_vollstaendigkeit(2024, 1, 3, katalog, geladen, set(katalog))
    assert info.value.zustaende["h01v00"].zustand == vnp46a3.ZUSTAND_NICHT_GELADEN
    assert "1 von 3" in str(info.value)


def test_pruefe_vollstaendigkeit_andere_dateiversion_gilt_als_nicht_geladen():
    katalog = _katalog(["h00v00"])
    geladen = {"h00v00": Path("VNP46A3.A2024001.h00v00.002.2024999999999.h5")}  # älterer Erzeugungsstand
    with pytest.raises(vnp46a3.MonatUnvollstaendig) as info:
        vnp46a3.pruefe_vollstaendigkeit(2024, 1, 1, katalog, geladen, set(katalog))
    assert "andere Datei" in info.value.zustaende["h00v00"].grund


def test_pruefe_vollstaendigkeit_bricht_ab_wenn_katalogzahl_nicht_zu_den_positionen_passt():
    katalog = _katalog(["h00v00", "h01v00"])
    geladen = {p: Path(s.datei) for p, s in katalog.items()}
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="meldet 3 Kacheln"):
        vnp46a3.pruefe_vollstaendigkeit(2024, 1, 3, katalog, geladen, REFERENZ)


@pytest.mark.parametrize(
    "monat, fehlend, grund",
    [
        (6, [f"h{h:02d}v01" for h in range(11)], "höchstens 10"),  # zu viele
        (1, ["h04v01"], "außerhalb April bis August"),  # falsche Jahreszeit
        (6, ["h21v05"], "südlich 50° N"),  # Kairo fehlt nie wegen Polartag
    ],
)
def test_beim_anbieter_nicht_vorhanden_nur_im_bekannten_muster(monat, fehlend, grund):
    """Sonst bekäme eine lückenhafte Katalogantwort still diesen Namen (Auflage statistik-pruefer)."""
    referenz = {"h00v00"} | set(fehlend)
    katalog = _katalog(["h00v00"])
    geladen = {p: Path(s.datei) for p, s in katalog.items()}
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match=grund):
        vnp46a3.pruefe_vollstaendigkeit(2024, monat, 1, katalog, geladen, referenz)


@pytest.mark.echter_katalog  # echte Referenzdatei, keine Katalog-Attrappe
def test_katalog_mit_nur_einem_treffer_gilt_nicht_als_vollstaendig():
    referenz = vnp46a3.lies_referenz_positionen(vnp46a3.REFERENZ_KACHELN_DATEI)
    katalog = _katalog(["h21v05"])
    geladen = {p: Path(s.datei) for p, s in katalog.items()}
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="539 Positionen"):
        vnp46a3.pruefe_vollstaendigkeit(2024, 6, 1, katalog, geladen, referenz)


def test_pruefe_vollstaendigkeit_meldet_position_ausserhalb_der_referenzliste():
    katalog = _katalog(["h00v00", "h35v17"])
    geladen = {p: Path(s.datei) for p, s in katalog.items()}
    with pytest.raises(vnp46a3.ReferenzlisteVeraltet, match="h35v17"):
        vnp46a3.pruefe_vollstaendigkeit(2024, 1, 2, katalog, geladen, REFERENZ)


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


def test_manifest_enthaelt_zustand_groesse_und_pruefsumme_je_position(fake_ssd):
    soll = vnp46a3.KachelSoll("VNP46A3.A2024001.h19v03.002.123.h5", 57392259, "12ef3568fcda5fd0f4e74b3837e94d97")
    zustaende = {
        "h19v03": vnp46a3.KachelEintrag(vnp46a3.ZUSTAND_GELADEN, soll),
        "h04v01": vnp46a3.KachelEintrag(vnp46a3.ZUSTAND_NICHT_BEIM_ANBIETER),
        "h20v03": vnp46a3.KachelEintrag(
            vnp46a3.ZUSTAND_NICHT_GELADEN,
            vnp46a3.KachelSoll("VNP46A3.A2024001.h20v03.002.124.h5", 10, "a" * 32),
            "HTTP 502\tnach Wiederholung",
        ),
    }
    ziel = vnp46a3.schreibe_manifest(2024, 1, zustaende)
    assert ziel == fake_ssd / "protokoll" / "manifeste" / "vnp46a3" / "2024-01.tsv"
    zeilen = ziel.read_text(encoding="utf-8").splitlines()
    assert zeilen[0].startswith("# VNP46A3 2024-01") and "geladen: 1" in zeilen[0]
    assert zeilen[1] == "position\tzustand\tdatei\tgroesse_bytes\tmd5\tgrund"
    tabelle = {z.split("\t")[0]: z.split("\t") for z in zeilen[2:]}
    assert tabelle["h19v03"] == ["h19v03", "geladen", soll.datei, "57392259", soll.md5, "-"]
    assert tabelle["h04v01"] == ["h04v01", "beim Anbieter nicht vorhanden", "-", "-", "-", "-"]
    assert tabelle["h20v03"][1] == "nicht geladen" and len(tabelle["h20v03"]) == 6  # Tab im Grund entschärft


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
        "granule-1", tmp_path, datei_timeout_sekunden=1, retry_budget_sekunden=3, wartezeit_basis_sekunden=0.01
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
        "granule-1", tmp_path, datei_timeout_sekunden=0.1, retry_budget_sekunden=3, wartezeit_basis_sekunden=0.01
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
            raise OSError("simulierter Verbindungsfehler")
        return [str(Path(local_path) / "kachel.h5")]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    monkeypatch.setattr(vnp46a3.time, "sleep", lambda s: wartezeiten.append(s))
    pfad = vnp46a3._lade_kachel(
        "granule-1", tmp_path, datei_timeout_sekunden=1, retry_budget_sekunden=1800, wartezeit_basis_sekunden=20
    )
    assert pfad == tmp_path / "kachel.h5"
    assert versuche["n"] == 3
    assert wartezeiten == [20, 40]


def test_lade_kachel_gibt_nach_verbrauchtem_budget_auf(monkeypatch, tmp_path):
    def fake_download(granules, local_path):
        raise OSError("vorübergehender Verbindungsfehler")

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    monkeypatch.setattr(vnp46a3.time, "sleep", lambda s: None)
    with pytest.raises(vnp46a3.KachelNichtGeladen, match="vorübergehender Verbindungsfehler") as info:
        vnp46a3._lade_kachel(
            "granule-1", tmp_path, datei_timeout_sekunden=1, retry_budget_sekunden=1, wartezeit_basis_sekunden=0.2
        )
    assert info.value.dauerhaft is False


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

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        aufrufe.append(granule)
        pfad = ziel_ordner / granule.data_links()[0].rsplit("/", 1)[-1]
        pfad.touch()
        return pfad

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    ladung = vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=2)
    assert len(ladung.dateien) == 3
    assert len(aufrufe) == 3
    assert sum(e.zustand == vnp46a3.ZUSTAND_GELADEN for e in ladung.zustaende.values()) == 3


def test_lade_monat_meldet_kacheln_die_auch_nach_wiederholung_scheitern(monkeypatch, tmp_path):
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    granules = _attrappen_granules(2)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **kwargs: granules)

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        raise vnp46a3.DownloadHaengt("simulierter dauerhafter Hänger")

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    with pytest.raises(vnp46a3.KachelnFehlen, match="fehlen"):
        vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=2)


# --- Feste Zeitachse: Monate in beliebiger Reihenfolge (2026-09-23) ---------
#
# Hintergrund: Der große Lauf lädt zuerst 2018-2025 und erst danach 2013-2017.
# Ein hinten angehängter Würfel hätte dann eine unsortierte Zeitachse. Jetzt
# hat der Würfel von Anfang an alle 156 Monate; jeder Monat wird an seine
# Position geschrieben.


def _monat_dataset(tmp_path, jahr, monat):
    """Ein Monat aus einer synthetischen Kachel (Zelle [120,760] = 10, [120,761] = 4)."""
    tag = (np.datetime64(f"{jahr:04d}-{monat:02d}-01") - np.datetime64(f"{jahr:04d}-01-01")).astype(int) + 1
    pfad = _kachel_h19v03(tmp_path, jahr=jahr, tag=int(tag))
    ds = vnp46a3.verkleinere_monat([pfad])
    pfad.unlink()
    return ds


def test_zeitachse_hat_156_monate_2013_bis_2025():
    achse = vnp46a3.zeitachse()
    assert len(achse) == 156
    assert achse[0] == np.datetime64("2013-01-01")
    assert achse[-1] == np.datetime64("2025-12-01")
    assert (np.diff(achse) > np.timedelta64(0, "ns")).all()


def test_monate_in_umgekehrter_reihenfolge_landen_an_richtiger_position(tmp_path, fake_ssd):
    # Erst spät (2018-01, 2025-12), dann früh (2013-01), dann Mitte (2016-07).
    for jahr, monat in [(2018, 1), (2025, 12), (2013, 1), (2016, 7)]:
        vnp46a3.schreibe_in_wuerfel(_monat_dataset(tmp_path, jahr, monat))

    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2025, 12), (2013, 1), (2016, 7)}

    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as ds:
        zeit = ds["zeit"].values
        assert (np.diff(zeit) > np.timedelta64(0, "ns")).all()  # streng aufsteigend
        assert len(zeit) == 156
        for jahr, monat in [(2018, 1), (2025, 12), (2013, 1), (2016, 7)]:
            i = int(np.flatnonzero(zeit == np.datetime64(f"{jahr:04d}-{monat:02d}-01"))[0])
            assert float(ds["near_nadir_mittel"].values[i, 120, 760]) == pytest.approx(10.0)
            assert int(ds[vnp46a3.FERTIG_VARIABLE].values[i]) == 1
        # Ein nicht geschriebener Monat bleibt leer und nicht fertig.
        i_leer = int(np.flatnonzero(zeit == np.datetime64("2015-05-01"))[0])
        assert np.isnan(ds["near_nadir_mittel"].values[i_leer]).all()
        assert (ds["near_nadir_gueltige_pixel"].values[i_leer] == 0).all()
        assert int(ds[vnp46a3.FERTIG_VARIABLE].values[i_leer]) == 0
        assert int(ds[vnp46a3.FERTIG_VARIABLE].values.sum()) == 4


def test_monat_ausserhalb_der_zeitachse_wird_abgelehnt(tmp_path, fake_ssd):
    ds = _monat_dataset(tmp_path, 2012, 12)
    with pytest.raises(vnp46a3.MonatAusserhalbZeitachse):
        vnp46a3.schreibe_in_wuerfel(ds)
    ds = _monat_dataset(tmp_path, 2026, 1)
    with pytest.raises(vnp46a3.MonatAusserhalbZeitachse):
        vnp46a3.schreibe_in_wuerfel(ds)


def test_fertiger_monat_wird_nicht_ueberschrieben(tmp_path, fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat_dataset(tmp_path, 2020, 6))
    with pytest.raises(vnp46a3.MonatSchonVorhanden):
        vnp46a3.schreibe_in_wuerfel(_monat_dataset(tmp_path, 2020, 6))


def test_absturz_vor_fertig_markierung_hinterlaesst_keinen_fertigen_monat(tmp_path, fake_ssd, monkeypatch):
    """Simuliert einen Abbruch nach dem Schreiben der Werte, vor dem Setzen von monat_fertig.

    Der Monat darf dann nicht als vorhanden gelten und muss beim nächsten
    Versuch sauber neu geschrieben werden können.
    """
    ds = _monat_dataset(tmp_path, 2020, 6)
    original = xr.Dataset.to_zarr
    aufrufe = {"n": 0}

    def zerbrochenes_to_zarr(self, *args, **kwargs):
        aufrufe["n"] += 1
        if vnp46a3.FERTIG_VARIABLE in self.data_vars and kwargs.get("region"):
            raise OSError("simulierter Absturz beim Fertig-Markieren")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(xr.Dataset, "to_zarr", zerbrochenes_to_zarr)
    with pytest.raises(OSError, match="simulierter Absturz"):
        vnp46a3.schreibe_in_wuerfel(ds)
    monkeypatch.setattr(xr.Dataset, "to_zarr", original)

    assert vnp46a3.vorhandene_monate() == set()
    vnp46a3.schreibe_in_wuerfel(ds)  # zweiter Versuch klappt
    assert vnp46a3.vorhandene_monate() == {(2020, 6)}


def test_wuerfel_im_alten_aufbau_wird_abgelehnt(tmp_path, fake_ssd):
    """Ein Würfel im alten Aufbau (angehängt, ohne monat_fertig) darf nicht weiterbenutzt werden."""
    alt = _monat_dataset(tmp_path, 2024, 1)
    pfad = vnp46a3._wuerfel_pfad()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    alt.to_zarr(pfad, mode="w")
    with pytest.raises(vnp46a3.WuerfelFormat):
        vnp46a3.vorhandene_monate()
    with pytest.raises(vnp46a3.WuerfelFormat):
        vnp46a3.schreibe_in_wuerfel(_monat_dataset(tmp_path, 2020, 6))


def test_werte_stimmen_nach_dem_schreiben_exakt_ueberein(tmp_path, fake_ssd):
    ds = _monat_dataset(tmp_path, 2019, 3)
    vnp46a3.schreibe_in_wuerfel(ds)
    achse = vnp46a3.zeitachse()
    i = int(np.flatnonzero(achse == np.datetime64("2019-03-01"))[0])
    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as gelesen:
        for name in vnp46a3._wuerfel_variablen():
            assert np.array_equal(gelesen[name].values[i], ds[name].values[0], equal_nan=True), name
        assert gelesen[vnp46a3.FERTIG_VARIABLE].values.dtype == np.int8


def test_lade_monat_meldet_kachelzahl(monkeypatch, tmp_path):
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **kwargs: _attrappen_granules(3))

    def fake_lade_kachel(granule, ziel_ordner, **kwargs):
        pfad = ziel_ordner / granule.data_links()[0].rsplit("/", 1)[-1]
        pfad.touch()
        return pfad

    monkeypatch.setattr(vnp46a3, "_lade_kachel", fake_lade_kachel)
    meldungen = []
    vnp46a3.lade_monat(2024, 1, tmp_path, gleichzeitige_downloads=2, melde=meldungen.append)
    assert meldungen == [
        "3 Kacheln bei NASA gemeldet (Katalog: 3 Treffer, alle geholt; Referenzliste 3 Positionen), "
        "Download beginnt."
    ]
    # Das Statusmodul liest die Zahl am Zeilenanfang; das Format muss dazu passen.
    assert vnp46a3_status._MONAT_GEMELDET.match("2024-01: " + meldungen[0]).group(3) == "3"


# --- Lauf: Reihenfolge und Protokoll ----------------------------------------

from aleph.layers import vnp46a3_lauf, vnp46a3_status  # noqa: E402


def test_reihenfolge_erst_ab_2018_dann_frueher():
    monate = vnp46a3_lauf._monatsliste("2013-01", "2025-12")
    ordnung = vnp46a3_lauf._reihenfolge(monate, "2018-01")
    assert len(ordnung) == 156 and set(ordnung) == set(monate)
    assert ordnung[0] == (2018, 1)
    assert ordnung[95] == (2025, 12)  # 96 Monate 2018-2025
    assert ordnung[96] == (2013, 1)
    assert ordnung[-1] == (2017, 12)
    assert ordnung[:96] == sorted(ordnung[:96]) and ordnung[96:] == sorted(ordnung[96:])


def test_reihenfolge_ohne_angabe_ist_zeitlich():
    monate = [(2020, 3), (2013, 1), (2018, 1)]
    assert vnp46a3_lauf._reihenfolge(monate, None) == [(2013, 1), (2018, 1), (2020, 3)]


def test_reihenfolge_nur_offene_monate_bleibt_in_der_vorgabe():
    # Fertige Monate sind schon herausgefiltert; die Ordnung gilt für den Rest.
    offen = [(2018, 5), (2015, 2), (2019, 1)]
    assert vnp46a3_lauf._reihenfolge(offen, "2018-01") == [(2018, 5), (2019, 1), (2015, 2)]


def test_verarbeite_monat_schreibt_zeitstempel_und_ordnet_richtig_ein(monkeypatch, tmp_path, fake_ssd):
    """Ganzer Ablauf mit Attrappe statt NASA: erst 2018-01, dann 2013-01."""

    def fake_lade_monat(jahr, monat, ziel_ordner, gleichzeitige_downloads=3, melde=None):
        ziel_ordner.mkdir(parents=True, exist_ok=True)
        if melde:
            melde("1 Kacheln bei NASA gemeldet, Download beginnt.")
        return vnp46a3.MonatsLadung(dateien=[_kachel_h19v03(ziel_ordner, jahr=jahr, tag=1)], zustaende={})

    monkeypatch.setattr(vnp46a3.io, "aleph_data_dir", lambda: fake_ssd)
    monkeypatch.setattr(vnp46a3, "lade_monat", fake_lade_monat)
    protokoll = vnp46a3_lauf.Protokoll(fake_ssd / "protokoll" / "vnp46a3.log")
    protokoll.schreibe("Lauf gestartet: Test.")
    vnp46a3_lauf.verarbeite_monat(2018, 1, protokoll, 3)
    vnp46a3_lauf.verarbeite_monat(2013, 1, protokoll, 3)

    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2013, 1)}
    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as ds:
        assert (np.diff(ds["zeit"].values) > np.timedelta64(0, "ns")).all()
    # Rohdaten weg, Manifest da
    assert not (fake_ssd / "raw" / "vnp46a3" / "2018-01").exists()
    assert (fake_ssd / "protokoll" / "manifeste" / "vnp46a3" / "2013-01.tsv").exists()

    text = (fake_ssd / "protokoll" / "vnp46a3.log").read_text(encoding="utf-8")
    assert "2018-01: Start " in text and "2013-01: Start " in text
    assert text.index("2018-01: fertig") < text.index("2013-01: Start ")  # Reihenfolge wie aufgerufen
    fertig_zeile = [z for z in text.splitlines() if "2018-01: fertig" in z][0]
    for teil in ("Start 20", "Ende 20", "Dauer gesamt", "Download", "Verkleinern und Schreiben"):
        assert teil in fertig_zeile

    p = vnp46a3_status.lies_protokoll(text.splitlines())
    assert [(a[0], a[1], a[2]) for a in p["abgeschlossen"]] == [(2018, 1, 1), (2013, 1, 1)]
    assert p["aktuell"] is None and p["lauf_beginn"] is not None


# --- Status: Protokoll lesen -------------------------------------------------


def test_status_erkennt_laufenden_monat_und_phase():
    zeilen = [
        "2026-09-23 12:00:00 UTC  Lauf gestartet: 2013-01 bis 2025-12, gleichzeitig=3.",
        "2026-09-23 12:00:01 UTC  2018-01: Start 2026-09-23 12:00:01 UTC.",
        "2026-09-23 12:00:05 UTC  2018-01: 512 Kacheln bei NASA gemeldet, Download beginnt.",
    ]
    p = vnp46a3_status.lies_protokoll(zeilen)
    assert p["aktuell"]["monat"] == (2018, 1)
    assert p["aktuell"]["gemeldet"] == 512
    assert p["aktuell"]["download_fertig"] is False
    zeilen.append("2026-09-23 13:20:00 UTC  2018-01: Download fertig nach 80.0 Minuten.")
    assert vnp46a3_status.lies_protokoll(zeilen)["aktuell"]["download_fertig"] is True


def test_status_ignoriert_fehler_aus_frueheren_laeufen():
    zeilen = [
        "2026-09-22 10:00:00 UTC  Lauf gestartet: alt.",
        "2026-09-22 10:05:00 UTC  FEHLER bei 2024-01: alt\nTraceback ...",
        "2026-09-23 12:00:00 UTC  Lauf gestartet: neu.",
    ]
    assert vnp46a3_status.lies_protokoll(zeilen)["fehler"] == []


# --- Schutzprüfungen nach der Prüfung durch statistik-pruefer (2026-09-23) --


def test_verkleinere_monat_lehnt_falschen_monat_ab(tmp_path):
    pfad = _kachel_h19v03(tmp_path, jahr=2020, tag=153)  # Juni 2020
    with pytest.raises(vnp46a3.MonatStimmtNicht):
        vnp46a3.verkleinere_monat([pfad], erwarteter_monat=(2020, 7))
    assert vnp46a3.verkleinere_monat([pfad], erwarteter_monat=(2020, 6)) is not None


def test_verkleinere_monat_lehnt_gemischte_monate_ab(tmp_path):
    juni = _kachel_h19v03(tmp_path, jahr=2020, tag=153)
    ordner2 = tmp_path / "zweiter"
    ordner2.mkdir()
    juli = _schreibe_kachel(ordner2, h=20, v=3, jahr=2020, tag_im_jahr=183)
    with pytest.raises(vnp46a3.MonatStimmtNicht):
        vnp46a3.verkleinere_monat([juni, juli])


def test_verkleinere_monat_lehnt_doppelte_kachel_ab(tmp_path):
    erste = _kachel_h19v03(tmp_path, jahr=2020, tag=153)
    ordner2 = tmp_path / "kopie"
    ordner2.mkdir()
    zweite = ordner2 / erste.name.replace("2025133214434", "2025140000000")  # gleiche h/v, andere Version
    zweite.write_bytes(erste.read_bytes())
    with pytest.raises(vnp46a3.MonatStimmtNicht, match="doppelt"):
        vnp46a3.verkleinere_monat([erste, zweite])


def test_monat_argument_ist_streng():
    import argparse

    assert vnp46a3_lauf._monat_argument("2018-01") == "2018-01"
    for falsch in ["2018", "2018-13", "2018-1", "18-01", "2018-00", ""]:
        with pytest.raises(argparse.ArgumentTypeError):
            vnp46a3_lauf._monat_argument(falsch)


def test_lauf_lehnt_monate_ausserhalb_der_zeitachse_vor_dem_download_ab(monkeypatch, fake_ssd):
    monkeypatch.setattr(vnp46a3.io, "aleph_data_dir", lambda: fake_ssd)
    heruntergeladen = []
    monkeypatch.setattr(vnp46a3, "lade_monat", lambda *a, **k: heruntergeladen.append(1))
    monkeypatch.setattr(sys, "argv", ["lauf", "--start", "2012-01", "--ende", "2013-03"])
    assert vnp46a3_lauf.main() == 1
    assert heruntergeladen == []
    assert "Kein Download gestartet" in (fake_ssd / "protokoll" / "vnp46a3.log").read_text(encoding="utf-8")
