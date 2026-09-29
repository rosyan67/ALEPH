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
    stand0 = _lies_js(DATEN / "datenstand.js")
    jahre = sorted({int(m[:4]) for m in stand0["angezeigt"]})
    assert L["weltbank"]["jahre"] == jahre and {2018, 2019} <= set(jahre) and max(jahre) < 2023
    for land in L["weltbank"]["werte"].values():
        assert set(land["jahre"]) <= {str(j) for j in jahre}
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


# ---------------------------------------------------------------- Teil 3b: Auswertung Nachtlicht × BIP


def test_auswertungsfeld_traegt_evidenzstufe_und_rahmen():
    js = (WEB / "globus_auswertung.js").read_text(encoding="utf-8")
    assert "Evidenzstufe: statistische Assoziation" in js
    assert "Querschnitt, ein Jahr, Afrika-Europa-Asien, kein Beleg für Ursache und Wirkung" in js
    assert "Liste der ausgeschlossenen Länder" in js
    html = (WEB / "globus.html").read_text(encoding="utf-8")
    assert 'src="daten/auswertung_nachtlicht_bip.js"' in html and 'src="globus_auswertung.js"' in html


@pytest.mark.skipif(not (DATEN / "auswertung_nachtlicht_bip.js").exists(), reason="web/daten nicht erzeugt")
def test_auswertung_im_export():
    A = _lies_js(DATEN / "auswertung_nachtlicht_bip.js")
    assert A["verfuegbar"] is True and sorted(A["jahre"]) == ["2018", "2019"]
    assert A["evidenzstufe"] == "statistische Assoziation"
    for j in A["jahre"].values():
        r = j["varianten"]["haupt"]
        assert r["n"] == len(j["punkte"]) >= 30
        assert r["steigung_unten"] < r["steigung"] < r["steigung_oben"]
        codes = {p["code"] for p in j["punkte"]}
        assert not codes & {"GEO", "MDA", "TZA", "MAR", "CYP"}  # Weltbank-Gebiet weicht ab
        assert not codes & {"USA", "BRA", "ATG", "TTO", "PRI"}  # Amerika: nicht in der Region
        assert len(j["groesste_abweichung"]) == 10


# ---------------------------------------------------------------- Teil 4: Vergleich mit dem Vorjahresmonat


def test_vergleich_nur_2019_gegen_2018_und_beschriftet():
    js = (WEB / "globus.js").read_text(encoding="utf-8")
    html = (WEB / "globus.html").read_text(encoding="utf-8")
    assert 'var VERGLEICH_JAHR = "2019";' in js
    # Differenz nur, wenn BEIDE Monate einen gezeigten Wert haben
    assert "if (vergleichbar(e, neu.anteil[i]) && vergleichbar(alt.meta, alt.anteil[i])) {" in js
    assert "function vergleichbar(e, a) { return a <= 100 && a >= e.min_beobachtet_prozent; }" in js
    assert "beobachtete Differenz, nicht auf Signifikanz geprüft" in html
    assert "kein Vergleich möglich" in html and "dunkler als im Vorjahresmonat" in html and "heller" in html
    assert 'id="vergleich-an" disabled' in html  # erst mit einem 2019-Monat freigegeben


# ---------------------------------------------------------------- Teil 5: Über ALEPH


def test_ueber_aleph_nennt_stufen_regeln_und_naechste_schritte():
    js = (WEB / "globus_ueber.js").read_text(encoding="utf-8")
    for stufe in ("beobachtet", "statistische Assoziation", "Modellprojektion", "hypothetisches Szenario"):
        assert stufe in js
    for wort in ("Niederschlag", "Vegetation", "Konfliktereignisse", "2023 bis 2025", "Umstrittene"):
        assert wort in js
    assert 'src="globus_ueber.js"' in (WEB / "globus.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------- Länderansicht mit Zeitreihen (2026-09-29)


def test_zeitreihen_seite_eingebunden_mit_hinweis_und_sperre():
    html = (WEB / "globus.html").read_text(encoding="utf-8")
    assert 'src="daten/laender_zeitreihen.js"' in html
    assert html.index('src="globus_laender.js"') < html.index('src="globus_zeitreihen.js"')
    js = (WEB / "globus_zeitreihen.js").read_text(encoding="utf-8")
    assert "Nebeneinander gestellt, kein Zusammenhang behauptet." in js
    assert 'GESPERRT_AB = "2023-01", GESPERRT_AB_JAHR = 2023' in js
    assert "Evidenzstufe: beobachtet" in js
    # keine Grafik mit zwei y-Achsen: jede Grafik hat genau eine Achsenbeschriftung links
    assert "RAND.l - 6" in js and "B - RAND.r + " not in js


def test_zeitreihen_export_filtert_2023(tmp_path, monkeypatch):
    from aleph.core import io
    from aleph.export import globus

    ordner = tmp_path / "auswertungen" / "laender_zeitreihen"
    ordner.mkdir(parents=True)
    land = {"monate": [{"monat": "2022-12"}, {"monat": "2023-01"}],
            "gleitend": {"summe": [{"monat": "2022-12", "wert": 1}, {"monat": "2024-01", "wert": 1}]},
            "saison": {"summe": {"werte": [{"monat": "2025-03", "wert": 1}]}},
            "jahre": {"2022": {}, "2023": {}}, "index": {"bip_real": {"2018": 100, "2024": 110}}}
    (ordner / "ergebnis.json").write_text(json.dumps({"monate": ["2022-12", "2023-01"], "volle_jahre": [2022, 2023],
                                                      "weltbank_jahre": [2022, 2024], "laender": {"XXX": land}}))
    monkeypatch.setattr(io, "aleph_data_dir", lambda: tmp_path)
    e = globus.laender_zeitreihen()
    text = json.dumps(e)
    for verboten in ("2023", "2024", "2025"):
        assert verboten not in text
    assert e["verfuegbar"] and e["monate"] == ["2022-12"]


@pytest.mark.skipif(not (DATEN / "laender_zeitreihen.js").exists(), reason="web/daten nicht erzeugt")
def test_zeitreihen_echter_export_ohne_2023_und_zum_laenderfeld_passend():
    Z = _lies_js(DATEN / "laender_zeitreihen.js")
    text = (DATEN / "laender_zeitreihen.js").read_text(encoding="utf-8")
    for verboten in ('"2023', '"2024', '"2025'):
        assert verboten not in text
    assert Z["verfuegbar"] and all(m < "2023-01" for m in Z["monate"])
    # Monatliche Landessumme = Wert im Länderfeld (gleiches Gerüst, dort auf 2 Ziffern gerundet)
    L = _lies_js(DATEN / "laender.js")
    geprueft = 0
    for code in ("EGY", "DEU", "IND", "NGA"):
        for p in Z["laender"][code]["monate"]:
            lf = L["monate"].get(p["monat"], {}).get("land", {}).get(code)
            if lf is None:
                continue
            if lf["licht_summe"] is None:
                assert p["status"] in ("gering", "keine", "nicht_geladen")
            else:
                assert p["status"] in ("gueltig", "schnee")
                assert p["summe"] == pytest.approx(lf["licht_summe"], rel=0.051)
            geprueft += 1
    assert geprueft >= 4 * 24


# ---------------------------------------------------------------- Ländervergleich (2026-09-29)


def test_vergleich_eingebunden_hoechstens_vier_und_farben_getrennt():
    html = (WEB / "globus.html").read_text(encoding="utf-8")
    assert html.index('src="globus_auswertung.js"') < html.index('src="globus_vergleich.js"')
    assert html.index('src="globus_zeitreihen.js"') < html.index('src="globus_vergleich.js"')
    js = (WEB / "globus_vergleich.js").read_text(encoding="utf-8")
    assert "MAX = 4" in js
    farben = re.findall(r'farbe: "(#[0-9a-f]{6})"', js)
    assert len(farben) == 4 and len(set(farben)) == 4
    css = (WEB / "globus.css").read_text(encoding="utf-8").lower()
    belegt = set(re.findall(r"--(?:keine|duenn|nicht)-[ab]: (#[0-9a-f]{6})", css))
    belegt |= set(re.findall(r"--(?:umstritten|besetzt|sonder|fehler|gold|gold-soft): (#[0-9a-f]{6})", css))
    belegt |= {"#b3261e", "#8fb4e8"}  # rote Kennzeichen, Punkte der Punktwolke
    assert len(belegt) >= 10 and not (set(farben) & belegt)
    formen = re.findall(r'form: "(kreis|quadrat|dreieck|raute)"', js)
    assert len(set(formen)) == 4
