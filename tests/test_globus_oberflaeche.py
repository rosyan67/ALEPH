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


# ---------------------------------------------------------------- Teil 3a: Länderwerte


def test_laenderfeld_sagt_kein_zusammenhang_und_sperrt_2023():
    js = (WEB / "globus_laender.js").read_text(encoding="utf-8")
    assert "Nebeneinander gestellt, kein Zusammenhang behauptet." in js
    assert "var GESPERRT_AB_JAHR = 2023;" in js and "jahr >= GESPERRT_AB_JAHR" in js
    html = (WEB / "globus.html").read_text(encoding="utf-8")
    assert 'src="daten/laender.js"' in html and 'src="globus_laender.js"' in html


@pytest.mark.skipif(not (DATEN / "laender.js").exists(), reason="web/daten nicht erzeugt")
def test_laenderwerte_im_export():
    L = _lies_js(DATEN / "laender.js")
    assert L["verfuegbar"] is True
    assert L["weltbank"]["jahre"] == [2018, 2019]
    for land in L["weltbank"]["werte"].values():
        assert set(land["jahre"]) <= {"2018", "2019"}
    text = (DATEN / "laender.js").read_text(encoding="utf-8")
    for jahr in ("2023-", "2024-", "2025-", '"2023"', '"2024"', '"2025"'):
        assert jahr not in text
    stand = _lies_js(DATEN / "datenstand.js")
    assert sorted(L["monate"]) == stand["angezeigt"]
    m = L["monate"]["2018-01"]["land"]
    # Technikprobe 2018-01 (Bericht statistik-geruest): Deutschland 400 000, Ägypten 713 000 (gerundet)
    assert m["DEU"]["licht_summe"] == 400000 and m["EGY"]["licht_summe"] == 710000
    assert m["RUS"]["licht_summe"] is None and m["RUS"]["abdeckung_prozent"] < 90  # keine Landessumme
    assert m["USA"]["licht_summe"] is None  # Amerika noch nicht geladen
    assert {c for c, g in L["gebiet_weltbank"].items() if g == "abweichend"} == {"CYP", "GEO", "MAR", "MDA", "TZA"}
    # BIP pro Kopf mit unpassendem Nenner wird nicht als Zahl ausgegeben
    assert L["weltbank"]["werte"]["RUS"]["jahre"]["2018"]["bip_pro_kopf_real"]["wert"] is None


def test_weltbank_werte_ab_2023_werden_verweigert():
    from aleph.core import io
    try:
        da = (io.aleph_data_dir() / "laender" / "weltbank.parquet").exists()
    except Exception:
        da = False
    if not da:
        pytest.skip("SSD mit Weltbank-Tabelle nicht angeschlossen")
    from aleph.export.globus_laender import Laenderwerte
    lw = object.__new__(Laenderwerte)
    wb = lw.weltbank([2018, 2023, 2024])
    assert wb["jahre"] == [2018]
    assert all(set(v["jahre"]) <= {"2018"} for v in wb["werte"].values())
