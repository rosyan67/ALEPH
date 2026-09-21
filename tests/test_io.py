"""Prüft den Speicherwächter mit vorgetäuschtem freien Platz."""

from collections import namedtuple

import pytest

from aleph.core import io

GB = 1024**3
Platte = namedtuple("Platte", "total used free")


def freier_platz(monkeypatch, gb):
    monkeypatch.setattr(io.shutil, "disk_usage", lambda pfad: Platte(500 * GB, 0, int(gb * GB)))


def test_genug_platz_laeuft_weiter(monkeypatch):
    freier_platz(monkeypatch, 131)
    io.pruefe_speicher()  # darf keinen Fehler auslösen


def test_genau_an_der_grenze_laeuft_weiter(monkeypatch):
    freier_platz(monkeypatch, 20)
    io.pruefe_speicher()


def test_knapp_unter_der_grenze_stoppt(monkeypatch):
    freier_platz(monkeypatch, 19.9)
    with pytest.raises(io.SpeicherZuKnapp) as fehler:
        io.pruefe_speicher()
    assert "19.9 GB frei" in str(fehler.value)
    assert "20 GB" in str(fehler.value)


def test_eigene_grenze(monkeypatch):
    freier_platz(monkeypatch, 5)
    io.pruefe_speicher(minimum_gb=3)
    with pytest.raises(io.SpeicherZuKnapp):
        io.pruefe_speicher(minimum_gb=10)


def test_echte_platte_liefert_positive_zahl():
    assert io.freier_speicher_gb(".") > 0
