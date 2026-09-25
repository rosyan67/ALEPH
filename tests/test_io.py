"""Prüft den Speicherwächter und den SSD-Pfad mit vorgetäuschten Werten."""

from collections import namedtuple

import pytest

from aleph.core import io

GB = 1024**3
Platte = namedtuple("Platte", "total used free")


@pytest.fixture(autouse=True)
def keine_echte_env(monkeypatch):
    # Die echte .env darf in diesen Tests nie geladen werden.
    monkeypatch.setattr(io, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("ALEPH_DATA_DIR", raising=False)


def freier_platz(monkeypatch, gb):
    monkeypatch.setattr(io.shutil, "disk_usage", lambda pfad: Platte(500 * GB, 0, int(gb * GB)))


# --- aleph_data_dir --------------------------------------------------------


def test_data_dir_fehlt_wenn_variable_nicht_gesetzt():
    with pytest.raises(io.SSDNichtGefunden) as fehler:
        io.aleph_data_dir()
    assert "ALEPH_DATA_DIR" in str(fehler.value)


def test_data_dir_fehlt_wenn_ordner_nicht_erreichbar(monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", "/Volumes/SSD-nicht-da/ALEPH-data")
    with pytest.raises(io.SSDNichtGefunden) as fehler:
        io.aleph_data_dir()
    assert "SSD nicht gefunden" in str(fehler.value)


def test_data_dir_liefert_pfad_wenn_ssd_da(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    assert io.aleph_data_dir() == tmp_path


def test_rohdaten_und_wuerfel_pfad_liegen_unter_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    assert io.rohdaten_pfad("vnp46a3") == tmp_path / "raw" / "vnp46a3"
    assert io.wuerfel_pfad("vnp46a3.zarr") == tmp_path / "cube" / "vnp46a3.zarr"


# --- pruefe_speicher --------------------------------------------------------


def test_genug_platz_laeuft_weiter(monkeypatch):
    freier_platz(monkeypatch, 131)
    io.pruefe_speicher(".")  # darf keinen Fehler auslösen


def test_genau_an_der_grenze_laeuft_weiter(monkeypatch):
    freier_platz(monkeypatch, 50)
    io.pruefe_speicher(".")


def test_knapp_unter_der_grenze_stoppt(monkeypatch):
    freier_platz(monkeypatch, 49.9)
    with pytest.raises(io.SpeicherZuKnapp) as fehler:
        io.pruefe_speicher(".")
    assert "49.9 GB frei" in str(fehler.value)
    assert "50 GB" in str(fehler.value)


def test_eigene_grenze(monkeypatch):
    freier_platz(monkeypatch, 5)
    io.pruefe_speicher(".", minimum_gb=3)
    with pytest.raises(io.SpeicherZuKnapp):
        io.pruefe_speicher(".", minimum_gb=10)


def test_ohne_pfad_wird_die_ssd_geprueft(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    freier_platz(monkeypatch, 49.9)
    with pytest.raises(io.SpeicherZuKnapp) as fehler:
        io.pruefe_speicher()
    assert str(tmp_path) in str(fehler.value)


def test_ohne_pfad_und_ohne_ssd_bricht_mit_ssd_meldung_ab():
    with pytest.raises(io.SSDNichtGefunden):
        io.pruefe_speicher()


def test_echte_platte_liefert_positive_zahl():
    assert io.freier_speicher_gb(".") > 0
