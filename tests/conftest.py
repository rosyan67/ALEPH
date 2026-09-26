"""Gemeinsame Test-Attrappen.

Katalog-Attrappe für den Layer VNP46A3 (seit 2026-09-25): `lade_monat` fragt
den NASA-Katalog über `_katalog_abfrage` ab (Trefferzahl und alle Seiten),
holt je Kachel Größe und MD5 (`_katalog_soll`), prüft jede Datei dagegen
(`_pruefe_gegen_katalog`) und vergleicht mit der Referenzliste
(`lies_referenz_positionen`). Die Tests zum Fehlerverhalten sollen ohne Netz
und mit winzigen Attrappen-Dateien laufen. Deshalb ersetzt diese Attrappe
die vier Stellen:

- Katalog = was der Test als `earthaccess.search_data` vorgibt, Trefferzahl
  = Länge dieser Liste,
- Sollwerte = nur der Dateiname aus dem Link (Größe/MD5 nicht prüfbar),
- Dateiprüfung = nur der Dateiname,
- Referenzliste = genau die Positionen des vorgegebenen Katalogs (sonst
  gälten alle übrigen als „beim Anbieter nicht vorhanden", und die
  Plausibilitätsgrenze dafür bricht den Monat zu Recht ab).

Die echten vier Funktionen haben eigene Tests (tests/test_vnp46a3_katalog.py),
die sie vor dem Ersetzen importieren.
"""

import pytest

from aleph.layers import vnp46a3


def _attrappe_abfrage(jahr, monat):
    granules = vnp46a3.earthaccess.search_data()
    return len(granules), granules


def _attrappe_soll(granule):
    datei = [link.rsplit("/", 1)[-1] for link in granule.data_links() if link.endswith(".h5")][0]
    return vnp46a3.KachelSoll(datei, groesse=-1, md5="-")


def _attrappe_pruefung(pfad, soll):
    return None if pfad.name == soll.datei else f"Dateiname {pfad.name} statt {soll.datei}"


def _attrappe_referenz(pfad=None):
    return {vnp46a3._position(_attrappe_soll(g).datei) for g in vnp46a3.earthaccess.search_data()}


@pytest.fixture(autouse=True)
def katalog_attrappe(monkeypatch, request):
    if request.node.get_closest_marker("echter_katalog"):
        return
    monkeypatch.setattr(vnp46a3, "_katalog_abfrage", _attrappe_abfrage)
    monkeypatch.setattr(vnp46a3, "_katalog_soll", _attrappe_soll)
    monkeypatch.setattr(vnp46a3, "_pruefe_gegen_katalog", _attrappe_pruefung)
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", _attrappe_referenz)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "echter_katalog: ohne Katalog-Attrappe (prüft die echten Katalog-Funktionen)"
    )
