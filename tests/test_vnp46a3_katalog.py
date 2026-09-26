"""Tests zur Katalogabfrage, Referenzliste, Größen-/MD5-Prüfung und Monatsstatus (Auftrag 2026-09-25).

Anlass: `count=1000` schnitt jede Kachelliste ab (460 statt 540 Kacheln je
Monat), die Vollständigkeitsprüfung verglich nur mit dieser Liste, und unter
dem Namen h12v09 von 2019-05 lag byteidentisch h13v04. Diese Tests laufen
ohne die Katalog-Attrappe aus conftest.py (Marker `echter_katalog`), damit
die echten Funktionen geprüft werden. Kein Netzzugriff: der Katalog selbst
wird durch kleine Attrappen ersetzt.
"""

import hashlib
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from aleph.layers import vnp46a3, vnp46a3_lauf

pytestmark = pytest.mark.echter_katalog


# --- Zeitspanne und Katalogabfrage ------------------------------------------


def test_monatsspanne_beginnt_eine_sekunde_nach_mitternacht_und_endet_am_letzten_tag():
    """Ab 00:00:00 berührt die Suche das Zeitfenster des Vormonats (endet am 1. um 00:00)."""
    assert vnp46a3._monatsspanne(2018, 2) == ("2018-02-01T00:00:01Z", "2018-02-28T23:59:59Z")
    assert vnp46a3._monatsspanne(2024, 2) == ("2024-02-01T00:00:01Z", "2024-02-29T23:59:59Z")
    assert vnp46a3._monatsspanne(2019, 12) == ("2019-12-01T00:00:01Z", "2019-12-31T23:59:59Z")


class _AbfrageAttrappe:
    """Ersetzt earthaccess.DataGranules: `hits` meldet eine Zahl, `get` liefert eine Liste."""

    def __init__(self, gemeldet, geliefert):
        self.gemeldet, self.geliefert = gemeldet, geliefert
        self.parameter = None
        self.grenze = None

    def __call__(self, auth=None):
        return self

    def parameters(self, **kwargs):
        self.parameter = kwargs
        return self

    def hits(self):
        return self.gemeldet

    def get(self, grenze):
        self.grenze = grenze
        return self.geliefert[:grenze]


def test_katalog_abfrage_holt_alle_seiten_ohne_obergrenze_unter_der_trefferzahl(monkeypatch):
    attrappe = _AbfrageAttrappe(1080, list(range(1080)))
    monkeypatch.setattr(vnp46a3.earthaccess, "DataGranules", attrappe)
    gemeldet, granules = vnp46a3._katalog_abfrage(2018, 2)
    assert gemeldet == 1080 and len(granules) == 1080
    assert attrappe.grenze > 1080  # die alte Grenze 1000 hätte hier 80 abgeschnitten
    assert attrappe.parameter["temporal"] == ("2018-02-01T00:00:01Z", "2018-02-28T23:59:59Z")


def test_katalog_abfrage_bricht_ab_wenn_weniger_geholt_als_gemeldet(monkeypatch):
    monkeypatch.setattr(vnp46a3.earthaccess, "DataGranules", _AbfrageAttrappe(540, list(range(460))))
    with pytest.raises(vnp46a3.KatalogUnvollstaendig, match="meldet 540 Treffer, geholt wurden 460"):
        vnp46a3._katalog_abfrage(2018, 2)


def test_katalog_abfrage_bricht_ab_wenn_mehr_geholt_als_gemeldet(monkeypatch):
    monkeypatch.setattr(vnp46a3.earthaccess, "DataGranules", _AbfrageAttrappe(540, list(range(545))))
    with pytest.raises(vnp46a3.KatalogUnvollstaendig):
        vnp46a3._katalog_abfrage(2018, 2)


# --- Referenzliste -----------------------------------------------------------


def test_referenzliste_im_projekt_hat_540_positionen_und_enthaelt_kairo():
    positionen = vnp46a3.lies_referenz_positionen()
    assert len(positionen) == 540
    assert "h21v05" in positionen  # Kairo, fehlte in 2018-02 wegen der abgeschnittenen Abfrage
    assert all(0 <= int(p[1:3]) <= 35 and 0 <= int(p[4:6]) <= 17 for p in positionen)


def test_referenzliste_lehnt_unerwartete_zeile_ab(tmp_path):
    datei = tmp_path / "liste.txt"
    datei.write_text("# Kommentar\nh21v05\nKairo\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Kairo"):
        vnp46a3.lies_referenz_positionen(datei)


# --- Sollwerte und Dateiprüfung ----------------------------------------------


class _KatalogGranule(dict):
    """Wie earthaccess.DataGranule: dict mit 'umm' und data_links()."""

    def __init__(self, datei: str, groesse: int | None, md5: str | None):
        angaben = {"Name": "Not provided"}  # so liefert LAADS es tatsächlich (gemessen 2026-09-25)
        if groesse is not None:
            angaben["SizeInBytes"] = groesse
        if md5 is not None:
            angaben["Checksum"] = {"Value": md5, "Algorithm": "MD5"}
        super().__init__(umm={"DataGranule": {"ArchiveAndDistributionInformation": [angaben]}})
        self.datei = datei

    def data_links(self):
        return [f"https://example.org/{self.datei}", f"https://example.org/{self.datei}.xml"]


DATEI = "VNP46A3.A2019121.h12v09.002.2025133171805.h5"
INHALT = b"echte Kachel h12v09"
FALSCH = b"Inhalt von h13v04!!"  # gleich lang, anderer Inhalt


def _md5(daten: bytes) -> str:
    return hashlib.md5(daten).hexdigest()


def test_katalog_soll_liest_name_groesse_und_md5():
    soll = vnp46a3._katalog_soll(_KatalogGranule(DATEI, 57392259, "12EF3568FCDA5FD0F4E74B3837E94D97"))
    assert soll == vnp46a3.KachelSoll(DATEI, 57392259, "12ef3568fcda5fd0f4e74b3837e94d97")


def test_katalog_soll_ohne_pruefsumme_ist_ein_fehler_statt_ungeprueft():
    with pytest.raises(vnp46a3.KachelNichtGeladen, match="MD5"):
        vnp46a3._katalog_soll(_KatalogGranule(DATEI, 100, None))


def test_pruefung_erkennt_vertauschten_inhalt_bei_gleicher_groesse(tmp_path):
    pfad = tmp_path / DATEI
    pfad.write_bytes(FALSCH)
    soll = vnp46a3.KachelSoll(DATEI, len(INHALT), _md5(INHALT))
    assert len(FALSCH) == len(INHALT)
    assert "MD5" in vnp46a3._pruefe_gegen_katalog(pfad, soll)
    pfad.write_bytes(INHALT)
    assert vnp46a3._pruefe_gegen_katalog(pfad, soll) is None


def test_pruefung_erkennt_falsche_groesse_und_falschen_namen(tmp_path):
    soll = vnp46a3.KachelSoll(DATEI, len(INHALT), _md5(INHALT))
    pfad = tmp_path / DATEI
    pfad.write_bytes(INHALT + b"x")
    assert "Größe" in vnp46a3._pruefe_gegen_katalog(pfad, soll)
    anders = tmp_path / "VNP46A3.A2019121.h13v04.002.2025133171817.h5"
    anders.write_bytes(INHALT)
    assert "Dateiname" in vnp46a3._pruefe_gegen_katalog(anders, soll)


def _download_attrappe(monkeypatch, inhalte: list[bytes]):
    """earthaccess.download schreibt nacheinander die angegebenen Inhalte (wie ein echter Download)."""
    aufrufe = {"n": 0}

    def fake_download(granules, ordner):
        inhalt = inhalte[min(aufrufe["n"], len(inhalte) - 1)]
        aufrufe["n"] += 1
        ziel = Path(ordner) / granules[0].datei
        if not ziel.exists():  # earthaccess überspringt vorhandene Dateien
            ziel.write_bytes(inhalt)
        return [str(ziel)]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    return aufrufe


def test_falsche_datei_wird_verworfen_und_neu_geladen(monkeypatch, tmp_path):
    aufrufe = _download_attrappe(monkeypatch, [FALSCH, INHALT])
    granule = _KatalogGranule(DATEI, len(INHALT), _md5(INHALT))
    pfad = vnp46a3._lade_und_pruefe_kachel(granule, vnp46a3._katalog_soll(granule), tmp_path)
    assert pfad.read_bytes() == INHALT
    assert aufrufe["n"] == 2


def test_nach_drei_falschen_downloads_gilt_die_kachel_als_nicht_geladen(monkeypatch, tmp_path):
    aufrufe = _download_attrappe(monkeypatch, [FALSCH])
    granule = _KatalogGranule(DATEI, len(INHALT), _md5(INHALT))
    with pytest.raises(vnp46a3.KachelNichtGeladen, match="3 Versuch"):
        vnp46a3._lade_und_pruefe_kachel(granule, vnp46a3._katalog_soll(granule), tmp_path)
    assert aufrufe["n"] == 3
    assert not (tmp_path / DATEI).exists()  # verworfen, damit sie nicht wiederverwendet wird


def test_lade_monat_verwirft_vorhandene_falsche_datei_und_laedt_sie_neu(monkeypatch, tmp_path):
    """Der Fall 2019-05: im Rohordner liegt unter dem Namen h12v09 der Inhalt von h13v04."""
    import h5py

    echt = tmp_path / "vorlage.h5"
    with h5py.File(echt, "w") as f:
        f.attrs["kachel"] = "h12v09"
    richtig = echt.read_bytes()
    echt.unlink()
    ordner = tmp_path / "2019-05"
    ordner.mkdir()
    with h5py.File(ordner / DATEI, "w") as f:  # lesbare HDF5-Datei, aber falscher Inhalt
        f.attrs["kachel"] = "h13v04"
    granule = _KatalogGranule(DATEI, len(richtig), _md5(richtig))

    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3, "_katalog_abfrage", lambda jahr, monat: (1, [granule]))
    # h04v02 (60-70° N) fehlt im Mai beim Anbieter; das liegt im erlaubten Muster
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", lambda pfad=None: {"h12v09", "h04v02"})
    aufrufe = _download_attrappe(monkeypatch, [richtig])
    meldungen = []
    ladung = vnp46a3.lade_monat(2019, 5, ordner, gleichzeitige_downloads=1, melde=meldungen.append)

    assert aufrufe["n"] == 1
    assert (ordner / DATEI).read_bytes() == richtig
    assert ladung.zustaende["h12v09"].zustand == vnp46a3.ZUSTAND_GELADEN
    assert ladung.zustaende["h04v02"].zustand == vnp46a3.ZUSTAND_NICHT_BEIM_ANBIETER
    assert any("1 verworfen" in m for m in meldungen)


def test_lade_monat_kennzeichnet_fehlende_kachel_als_nicht_geladen(monkeypatch, tmp_path):
    granules = [
        _KatalogGranule(f"VNP46A3.A2019121.h{h:02d}v09.002.2025133171805.h5", len(INHALT), _md5(INHALT))
        for h in (12, 13)
    ]
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3, "_katalog_abfrage", lambda jahr, monat: (2, granules))
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", lambda pfad=None: {"h12v09", "h13v09"})

    def fake_download(gs, ordner):
        if "h13v09" in gs[0].datei:
            raise RuntimeError("Download failed. Status code: 404")
        ziel = Path(ordner) / gs[0].datei
        ziel.write_bytes(INHALT)
        return [str(ziel)]

    monkeypatch.setattr(vnp46a3.earthaccess, "download", fake_download)
    with pytest.raises(vnp46a3.KachelnFehlen) as info:
        vnp46a3.lade_monat(2019, 5, tmp_path, gleichzeitige_downloads=1)
    zustaende = info.value.zustaende
    assert zustaende["h12v09"].zustand == vnp46a3.ZUSTAND_GELADEN
    assert zustaende["h13v09"].zustand == vnp46a3.ZUSTAND_NICHT_GELADEN
    assert "404" in zustaende["h13v09"].grund


def test_lade_monat_meldet_katalogposition_ausserhalb_der_referenzliste_vor_dem_download(monkeypatch, tmp_path):
    granule = _KatalogGranule("VNP46A3.A2019121.h12v09.002.2025133171805.h5", 1, "0" * 32)
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3, "_katalog_abfrage", lambda jahr, monat: (1, [granule]))
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", lambda pfad=None: {"h00v00"})
    monkeypatch.setattr(vnp46a3.earthaccess, "download", lambda *a: pytest.fail("darf nicht laden"))
    with pytest.raises(vnp46a3.ReferenzlisteVeraltet, match="h12v09"):
        vnp46a3.lade_monat(2019, 5, tmp_path)


# --- Monatsstatus im Würfel: unvollständig markieren, ersetzen -----------------


@pytest.fixture
def fake_ssd(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    return tmp_path


def _monat(jahr, monat, wert):
    breite, laenge = vnp46a3._gitter_koordinaten()
    variablen = {}
    for name, dtyp in vnp46a3._wuerfel_variablen().items():
        variablen[name] = (("zeit", "breite", "laenge"), np.full((1, len(breite), len(laenge)), wert, dtype=dtyp))
    return xr.Dataset(
        variablen, coords={"zeit": [np.datetime64(f"{jahr:04d}-{monat:02d}-01")], "breite": breite, "laenge": laenge}
    )


def _status(jahr, monat):
    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as ds:
        return int(ds[vnp46a3.FERTIG_VARIABLE].values[vnp46a3._monat_index(jahr, monat)])


def test_unvollstaendig_markierter_monat_behaelt_seine_werte_gilt_aber_nicht_als_vorhanden(fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, 7))
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 3, 7))
    assert vnp46a3.markiere_unvollstaendig([(2018, 2), (2018, 4)]) == [(2018, 2)]  # 2018-04 war leer
    assert vnp46a3.vorhandene_monate() == {(2018, 3)}
    assert _status(2018, 2) == vnp46a3.MONAT_UNVOLLSTAENDIG
    assert _status(2018, 4) == vnp46a3.MONAT_LEER
    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as ds:  # nichts gelöscht
        assert float(ds["allangle_mittel"].values[vnp46a3._monat_index(2018, 2)].max()) == 7


def test_unvollstaendiger_monat_wird_beim_neuladen_ersetzt(fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, 7))
    vnp46a3.markiere_unvollstaendig([(2018, 2)])
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, 9))
    assert vnp46a3.vorhandene_monate() == {(2018, 2)}
    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as ds:
        assert float(ds["allangle_mittel"].values[vnp46a3._monat_index(2018, 2)].min()) == 9


def test_absturz_beim_ersetzen_hinterlaesst_weder_fertig_noch_alte_daten_markierung(fake_ssd, monkeypatch):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, 7))
    vnp46a3.markiere_unvollstaendig([(2018, 2)])
    original = xr.Dataset.to_zarr

    def abbruch_beim_werte_schreiben(self, *args, **kwargs):
        if vnp46a3.FERTIG_VARIABLE not in self.data_vars:
            raise OSError("simulierter Absturz beim Schreiben der Werte")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(xr.Dataset, "to_zarr", abbruch_beim_werte_schreiben)
    with pytest.raises(OSError):
        vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, 9))
    monkeypatch.setattr(xr.Dataset, "to_zarr", original)
    assert _status(2018, 2) == vnp46a3.MONAT_WIRD_GESCHRIEBEN
    assert vnp46a3.vorhandene_monate() == set()
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, 9))  # Neustart schreibt den Monat erneut
    assert vnp46a3.vorhandene_monate() == {(2018, 2)}


# --- Lauf: Vorrang-Reihenfolge ------------------------------------------------


def test_vorrang_argument_liest_bereiche_und_einzelmonate():
    monate = vnp46a3_lauf._vorrang_argument("2018-01..2019-12,2024-01")
    assert len(monate) == 25
    assert monate[0] == (2018, 1) and monate[11] == (2018, 12) and monate[12] == (2019, 1)
    assert monate[-1] == (2024, 1)


@pytest.mark.parametrize("text", ["2018-13", "2019-12..2018-01", "2018-01...2018-02", "2018"])
def test_vorrang_argument_lehnt_unsinn_ab(text):
    import argparse

    with pytest.raises(argparse.ArgumentTypeError):
        vnp46a3_lauf._vorrang_argument(text)


def test_reihenfolge_mit_vorrang_erst_2018_dann_2019_dann_2024_01_dann_rest():
    alle = vnp46a3_lauf._monatsliste("2013-01", "2025-12")
    fertig = {(2025, 1)}
    offen = [m for m in alle if m not in fertig]
    vorrang = vnp46a3_lauf._vorrang_argument("2018-01..2019-12,2024-01")
    ordnung = vnp46a3_lauf._reihenfolge(offen, "2018-01", vorrang)
    assert len(ordnung) == len(offen) == len(set(ordnung))
    assert ordnung[:12] == [(2018, m) for m in range(1, 13)]
    assert ordnung[12:24] == [(2019, m) for m in range(1, 13)]
    assert ordnung[24] == (2024, 1)
    assert ordnung[25] == (2020, 1)  # danach der bisher geplante Rest ab 2018 ...
    assert (2024, 1) not in ordnung[25:]
    assert ordnung[-1] == (2017, 12)  # ... und zuletzt 2013-2017


# --- Auflagen statistik-pruefer 2026-09-25: lückenhafte Katalogantwort -------


def _monat_mit_katalog(monkeypatch, gemeldet, granules, referenz):
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3, "_katalog_abfrage", lambda jahr, monat: (gemeldet, granules))
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", lambda pfad=None: set(referenz))
    monkeypatch.setattr(vnp46a3.earthaccess, "download", lambda *a: pytest.fail("darf nicht laden"))


def test_katalog_ohne_treffer_bricht_vor_dem_download_ab(monkeypatch, tmp_path):
    _monat_mit_katalog(monkeypatch, 0, [], vnp46a3.lies_referenz_positionen(vnp46a3.REFERENZ_KACHELN_DATEI))
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="540 Positionen"):
        vnp46a3.lade_monat(2019, 6, tmp_path)


def test_katalog_mit_kurzer_liste_bricht_vor_dem_download_ab(monkeypatch, tmp_path):
    """Wie 2018-06 damals: 99 statt 534 Einträge, und die Trefferzahl passte dazu."""
    referenz = vnp46a3.lies_referenz_positionen(vnp46a3.REFERENZ_KACHELN_DATEI)
    granules = [
        _KatalogGranule(f"VNP46A3.A2018152.{p}.002.2025000000000.h5", 1, "0" * 32) for p in sorted(referenz)[:99]
    ]
    _monat_mit_katalog(monkeypatch, 99, granules, referenz)
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="441 Positionen"):
        vnp46a3.lade_monat(2018, 6, tmp_path)


def test_eintrag_aus_anderem_monat_ist_ein_abbruchgrund(monkeypatch, tmp_path):
    granules = [
        _KatalogGranule("VNP46A3.A2019121.h12v09.002.2025133171805.h5", 1, "0" * 32),
        _KatalogGranule("VNP46A3.A2019091.h12v09.002.2025133170224.h5", 1, "0" * 32),  # April
    ]
    _monat_mit_katalog(monkeypatch, 2, granules, {"h12v09"})
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="davon passen 1"):
        vnp46a3.lade_monat(2019, 5, tmp_path)
