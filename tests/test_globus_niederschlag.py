"""Tests für die Niederschlagsebene des Globus (aleph/export/globus_niederschlag.py, web/globus_niederschlag.js)."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from aleph.export import globus_niederschlag as gn

WEB = Path(__file__).resolve().parents[1] / "web"
DATEN = WEB / "daten"


def _monat(mm=50.0, anteil=1.0, fehler=5.0, zeit="2018-07-01"):
    breite = 90 - gn.ZELLE / 2 - gn.ZELLE * np.arange(gn.BREITE)
    laenge = -180 + gn.ZELLE / 2 + gn.ZELLE * np.arange(gn.LAENGE)
    form = (1, gn.BREITE, gn.LAENGE)
    return xr.Dataset(
        {"precipitation_mm_monat": (("zeit", "breite", "laenge"), np.full(form, mm, "float32")),
         "precipitation_gueltig_anteil": (("zeit", "breite", "laenge"), np.full(form, anteil, "float32")),
         "random_error_mm_monat": (("zeit", "breite", "laenge"), np.full(form, fehler, "float32"))},
        coords={"zeit": pd.to_datetime([zeit]), "breite": breite, "laenge": laenge})


def test_werte_klassen_und_rueckweg():
    ds = _monat()
    z1, s1 = gn.zelle_von(19.08, 72.88)
    ds["precipitation_mm_monat"].values[0, z1, s1] = 1072.0
    z2, s2 = gn.zelle_von(89.9, 0.1)  # keine Daten
    ds["precipitation_gueltig_anteil"].values[0, z2, s2] = 0.0
    ds["precipitation_mm_monat"].values[0, z2, s2] = np.nan
    z3, s3 = gn.zelle_von(70.0, 10.0)  # zu wenig Messungen: Teilmittel vorhanden, aber unter 50 %
    ds["precipitation_gueltig_anteil"].values[0, z3, s3] = 0.3
    ds["precipitation_mm_monat"].values[0, z3, s3] = 80.0
    e = gn.kodiere_monat(ds, 2018, 7, trmm=False)
    wert, anteil, fehler = gn.entpacke_monat(e)
    assert wert[z1, s1] == 10720 and anteil[z1, s1] == 100 and fehler[z1, s1] == 5
    assert anteil[z2, s2] == gn.ANTEIL_KEINE_DATEN and wert[z2, s2] == 0
    assert anteil[z3, s3] == 30 and wert[z3, s3] == 0  # kein Wert, nie als Teilmittel gezeigt
    assert e["statistik"]["zellen_keine_daten"] == 1 and e["statistik"]["zellen_zu_wenig"] == 1
    assert e["min_gueltig_prozent"] == 50 and e["kontrolle"]["Mumbai"]["wert_code"] == 10720


def test_null_mm_ist_ein_wert_und_keine_daten_nicht():
    e = gn.kodiere_monat(_monat(mm=0.0), 2018, 7, trmm=False)
    wert, anteil, _ = gn.entpacke_monat(e)
    assert (wert == 0).all() and (anteil == 100).all()  # gemessen trocken: Klasse „Wert“


def test_sperre_2023_und_negative_werte():
    with pytest.raises(gn.NiederschlagFehler):
        gn.kodiere_monat(_monat(zeit="2023-01-01"), 2023, 1, trmm=False)
    with pytest.raises(gn.NiederschlagFehler):
        gn.kodiere_monat(_monat(mm=-1.0), 2018, 7, trmm=False)


def test_ohne_wuerfel_nicht_verfuegbar(tmp_path, monkeypatch):
    from aleph.core import io
    monkeypatch.setattr(io, "wuerfel_pfad", lambda *t: tmp_path.joinpath("cube", *t))
    stand = gn.exportiere_in(tmp_path)
    assert stand["verfuegbar"] is False and (tmp_path / "niederschlag_stand.js").exists()


def _lies_js(pfad):
    return json.loads(re.search(r"= (\{.*\});\s*$", pfad.read_text(encoding="utf-8"), re.S).group(1))


_DA = (DATEN / "niederschlag_stand.js").exists() and (DATEN / "niederschlag_2018-07.js").exists()


@pytest.mark.skipif(not _DA, reason="Niederschlag nicht exportiert")
def test_echter_export_monate_und_sperre():
    stand = _lies_js(DATEN / "niederschlag_stand.js")
    assert stand["verfuegbar"] and stand["evidenzstufe"] == "beobachtet" and stand["einheit"] == "mm/Monat"
    assert stand["monate"] == [f"{j}-{m:02d}" for j in range(2013, 2023) for m in range(1, 13)]
    assert "The IMERG data were provided by" in stand["quellenangabe"]
    namen = sorted(p.name for p in DATEN.glob("niederschlag_*.js"))
    assert not any(re.search(r"202[345]-", n) for n in namen)
    assert not re.search(r'"202[345]-', (DATEN / "niederschlag_stand.js").read_text(encoding="utf-8"))


@pytest.mark.skipif(not _DA, reason="Niederschlag nicht exportiert")
def test_echter_export_stichproben_2018():
    """Dieselben Erwartungen wie im IMERG-Bericht (E1–E4, vor dem Ansehen festgelegt), hier am Export geprüft."""
    def an(monat, la, lo):
        e = json.loads((DATEN / f"niederschlag_{monat}.js").read_text(encoding="utf-8").split(f'["{monat}"] = ', 1)[1].rstrip().rstrip(";"))
        w, a, f = gn.entpacke_monat(e)
        z, s = gn.zelle_von(la, lo)
        return w[z, s] / e["wert_skala"], int(a[z, s]), e
    w, a, e = an("2018-07", 19.08, 72.88)
    assert 400 <= w <= 1500 and a >= 50 and not e["kalibrierung_trmm"]  # Mumbai Juli
    assert an("2018-01", 19.08, 72.88)[0] <= 10  # Mumbai Januar
    assert an("2018-07", 23.125, 28.125)[0] <= 5  # Sahara
    assert an("2018-07", 30.04, 31.24)[0] <= 15  # Kairo
    assert an("2014-01", 52.52, 13.40)[2]["kalibrierung_trmm"] and not an("2014-06", 52.52, 13.40)[2]["kalibrierung_trmm"]


def test_seite_bindet_niederschlag_ein_mit_eigener_farbskala():
    html = (WEB / "globus.html").read_text(encoding="utf-8")
    assert html.index('src="globus.js"') < html.index('src="globus_niederschlag.js"')
    assert 'src="daten/niederschlag_stand.js"' in html
    js = (WEB / "globus_niederschlag.js").read_text(encoding="utf-8")
    for teil in ('var GESPERRT_AB = "2023-01";', "mm/Monat", "beobachtet", "keine Daten", "zu wenig Messungen",
                 "Das ist keine Messung von 0 mm.",
                 "Für großräumige Muster geeignet, an einzelnen Orten deutliche Abweichungen zu Messstationen möglich."):
        assert teil in js
    farben = lambda text, name: set(re.findall(r"\[(\d+), (\d+), (\d+)\]", text.split(f"var {name} = [", 1)[1].split("];", 1)[0]))
    ns = farben(js, "STUFEN")
    nl = farben((WEB / "globus.js").read_text(encoding="utf-8"), "STUFEN")
    assert ns and nl and not (ns & nl)  # keine gemeinsame Farbe mit der Nachtlicht-Skala
    # ein Farbton: ab der zweiten Stufe ist Grün der größte Anteil (die erste ist das fast neutrale Hell für 0 mm)
    stufen = re.findall(r"\[(\d+), (\d+), (\d+)\]", js.split("var STUFEN = [", 1)[1].split("];", 1)[0])
    assert all(int(g) >= int(r) and int(g) >= int(b) for r, g, b in stufen[1:])
