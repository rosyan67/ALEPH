"""Prüfungen der Zusatzteile des Globus (Blickpunkte, Länderwerte, Auswertung, Vergleich).

Die Oberfläche hat keinen eigenen Browser-Test; geprüft wird hier, dass die festen Inhalte der
Zusatzdateien zu den exportierten Daten passen und die Sperre 2023–2025 einhalten.
"""

import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
DATEN = WEB / "daten"


def _lies_js(pfad):
    text = pfad.read_text(encoding="utf-8")
    m = re.search(r"= (\{.*\});\s*$", text, re.S)
    return json.loads(m.group(1))


def _blickpunkte():
    js = (WEB / "globus_blickpunkte.js").read_text(encoding="utf-8")
    return re.findall(r'id: "([a-z]+)", titel: "([^"]+)", monat: "(\d{4}-\d{2})".*?einheit: (null|"[^"]+")', js, re.S)


def test_sechs_blickpunkte_mit_monat_vor_2023():
    bp = _blickpunkte()
    assert [b[0] for b in bp] == ["nil", "korea", "nigerdelta", "irak", "indien", "europa"]
    for _, _, monat, _ in bp:
        assert "2018-01" <= monat < "2023-01"


def test_blickpunkte_sind_in_der_seite_eingebunden():
    html = (WEB / "globus.html").read_text(encoding="utf-8")
    assert html.index('src="globus.js"') < html.index('src="globus_blickpunkte.js"')


@pytest.mark.skipif(not (DATEN / "datenstand.js").exists(), reason="web/daten nicht erzeugt")
def test_blickpunkte_nutzen_angezeigte_monate_und_echte_einheiten():
    stand = _lies_js(DATEN / "datenstand.js")
    eh = _lies_js(DATEN / "einheiten.js")
    ids = {f["properties"]["einheit_id"] for f in eh["geojson"]["features"]}
    for bid, _, monat, einheit in _blickpunkte():
        assert monat in stand["angezeigt"], bid
        if einheit != "null":
            assert einheit.strip('"') in ids, bid
