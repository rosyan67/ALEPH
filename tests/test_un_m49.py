"""Tests für aleph/layers/un_m49.py (Lesen der M49-Tabelle) und die Natural-Earth-Zusatzdateien.

Teil 1 mit einer kleinen Nachbildung der Seite, Teil 2 mit den echten, auf der SSD liegenden Abrufen.
"""

import pytest

from aleph.core import io
from aleph.layers import natural_earth as ne
from aleph.layers import un_m49

KOPF = ("<tr><th>Global Code</th><th>Region Name</th><th>Sub-region Name</th><th>Country or Area</th>"
        "<th>M49 Code</th><th>ISO-alpha3 Code</th></tr>")


def _seite(*zeilen):
    rumpf = "".join(f"<tr><td>001</td><td>{r}</td><td>{s}</td><td>{n}</td><td>{c}</td><td>{i}</td></tr>" for r, s, n, c, i in zeilen)
    return f'<html><table id = "downloadTableEN" class="compact">{KOPF}{rumpf}</table><table id = "downloadTableZH"></table></html>'


def test_liest_englische_tabelle():
    t = un_m49.lies_tabelle(_seite(("Europe", "Eastern Europe", "Ukraine", "804", "UKR"),
                                   ("Africa", "Northern Africa", "Western Sahara", "732", "ESH")))
    assert list(t.columns) == ["name", "m49", "iso3", "region", "subregion"]
    assert t.set_index("iso3").loc["UKR", "m49"] == "804"


def test_html_zeichen_werden_umgewandelt():
    t = un_m49.lies_tabelle(_seite(("Africa", "Sub-Saharan Africa", "C&ocirc;te d&#8217;Ivoire", "384", "CIV")))
    assert t.name.iloc[0] == "Côte d’Ivoire"


def test_doppelte_codes_brechen_ab():
    with pytest.raises(un_m49.M49Fehler, match="eindeutig"):
        un_m49.lies_tabelle(_seite(("A", "B", "X", "001", "XXX"), ("A", "B", "Y", "001", "YYY")))


def test_fehlende_tabelle_bricht_ab():
    with pytest.raises(un_m49.M49Fehler, match="nicht gefunden"):
        un_m49.lies_tabelle("<html></html>")


# --- echte Daten -------------------------------------------------------------------


@pytest.fixture(scope="module")
def echt():
    try:
        return un_m49.lade()
    except (io.SSDNichtGefunden, un_m49.M49Fehler) as grund:
        pytest.skip(f"M49 nicht geladen: {grund}")


def test_echte_liste(echt):
    tabelle, manifest = echt
    assert len(tabelle) == un_m49.ANZAHL_GEMESSEN == manifest["anzahl_eintraege"]
    codes = dict(zip(tabelle.iso3, tabelle.m49))
    assert codes["UKR"] == "804" and codes["CHN"] == "156" and codes["SRB"] == "688" and codes["ESH"] == "732"
    assert "TWN" not in codes and "XKX" not in codes  # Taiwan und Kosovo führt M49 nicht


def test_belegstellen_stehen_im_gespeicherten_original(echt):
    text = un_m49.hauptseite_text()
    assert "Kosovo is currently considered part of Serbia (numerical code 688)" in text
    assert "Taiwan Province of China is considered part of China (numerical code 156)" in text


@pytest.mark.parametrize("schluessel, anzahl, feld, wert", [
    ("umstritten", 99, "BRK_A3", "B89"),
    ("provinzen", 4596, "adm1_code", "CHN-1662"),
])
def test_natural_earth_zusatzdateien(schluessel, anzahl, feld, wert):
    try:
        daten, manifest = ne.lade_zusatz(schluessel)
    except (io.SSDNichtGefunden, ne.NaturalEarthFehler) as grund:
        pytest.skip(f"Zusatzdatei nicht geladen: {grund}")
    assert len(daten) == anzahl and manifest["version"] == ne.VERSION
    assert (daten[feld] == wert).sum() == 1
    assert daten.geometry.is_valid.all()


def test_unbekannte_zusatzdatei_bricht_ab():
    with pytest.raises(ne.NaturalEarthFehler, match="Unbekannte"):
        ne.ordner_zusatz  # vorhanden
        ne._eintrag_zusatz("gibt_es_nicht")
