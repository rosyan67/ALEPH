"""Tests für aleph/link/laender_zeitreihen.py mit künstlichen Daten (Regeln F1–F8 im Modulkopf)."""

import numpy as np
import pandas as pd
import pytest

from aleph.link import laender_zeitreihen as lz

NAN = float("nan")


def _monate(von_jahr, anzahl):
    return [f"{von_jahr + i // 12:04d}-{i % 12 + 1:02d}" for i in range(anzahl)]


# ---------------------------------------------------------------- F1 Status


def test_status_reihenfolge_und_grenzen():
    assert lz.monats_status(1.0, 0.0, 0.0, 10.0) == "gueltig"
    assert lz.monats_status(0.95, 0.049, 0.0, 10.0) == "gueltig"
    assert lz.monats_status(0.95, 0.05, 0.0, 10.0) == "schnee"
    assert lz.monats_status(0.89, 0.5, 0.0, 10.0) == "gering"  # geringe Abdeckung geht vor Schnee
    assert lz.monats_status(0.0, 0.0, 0.0, NAN) == "keine"
    assert lz.monats_status(1.0, 0.0, 0.005, 10.0) == "nicht_geladen"
    assert lz.monats_status(1.0, 0.0, 0.004, 10.0) == "gueltig"


# ---------------------------------------------------------------- F2 gleitender Durchschnitt


def test_gleitend_erst_ab_12_gueltigen_monaten():
    m = _monate(2018, 14)
    w = list(range(1, 15))
    g = lz.gleitender_durchschnitt(m, w, ["gueltig"] * 14)
    assert [x["monat"] for x in g] == ["2018-12", "2019-01", "2019-02"]
    assert g[0]["wert"] == pytest.approx(np.mean(range(1, 13)))
    assert g[2]["wert"] == pytest.approx(np.mean(range(3, 15)))


def test_gleitend_luecke_bei_einem_ungueltigen_monat():
    m = _monate(2018, 24)
    s = ["gueltig"] * 24
    s[5] = "schnee"  # 2018-06
    g = lz.gleitender_durchschnitt(m, list(range(24)), s)
    # jedes Fenster, das 2018-06 enthält (endet 2018-06 … 2019-05), fällt weg
    assert [x["monat"] for x in g] == _monate(2018, 24)[17:]


def test_gleitend_luecke_bei_fehlendem_monat_im_wuerfel():
    m = _monate(2018, 24)
    del m[3]
    g = lz.gleitender_durchschnitt(m, [1.0] * 23, ["gueltig"] * 23)
    assert g and all(x["monat"] >= "2019-04" for x in g)


def test_gleitend_nie_mit_none():
    m = _monate(2018, 12)
    w = [1.0] * 12
    w[0] = None
    assert lz.gleitender_durchschnitt(m, w, ["gueltig"] * 12) == []


# ---------------------------------------------------------------- F3 Jahreszeit


def test_jahreszeit_erst_ab_drei_werten_je_kalendermonat():
    m = _monate(2018, 35)  # 2018-01 … 2020-11: Dezember nur zweimal
    r = lz.jahreszeit_abweichung(m, [1.0] * 35, ["gueltig"] * 35)
    assert not r["bestimmbar"] and r["werte"] == []
    assert "mindestens 3 Jahre" in r["grund"]
    assert r["anzahl_je_kalendermonat"][12] == 2


def test_jahreszeit_zieht_kalendermonats_median_ab():
    m = _monate(2018, 36)
    saison = [10, 8, 6, 5, 4, 3, 3, 4, 5, 6, 8, 10]
    w = [saison[i % 12] + (i // 12) for i in range(36)]  # +1 je Jahr
    r = lz.jahreszeit_abweichung(m, w, ["gueltig"] * 36)
    assert r["bestimmbar"]
    werte = [x["wert"] for x in r["werte"]]
    assert werte[:12] == [-1] * 12 and werte[12:24] == [0] * 12 and werte[24:] == [1] * 12


def test_jahreszeit_zaehlt_nur_gueltige():
    m = _monate(2018, 36)
    s = ["gueltig"] * 36
    s[0] = "schnee"  # Januar hat dann nur 2 gültige Werte
    r = lz.jahreszeit_abweichung(m, [1.0] * 36, s)
    assert not r["bestimmbar"] and r["anzahl_je_kalendermonat"][1] == 2


# ---------------------------------------------------------------- F4, F7


def test_jahreswert_regeln():
    z = pd.Series({"flaeche_nicht_geladen": 0.0, "licht_summe": 100.0, "abdeckung_licht": 0.95})
    assert lz.jahreswert_gueltig(z) == (True, "")
    assert not lz.jahreswert_gueltig(z.copy().replace({0.95: 0.89}))[0]
    assert "90 %" in lz.jahreswert_gueltig(pd.Series({"flaeche_nicht_geladen": 0.0, "licht_summe": 1.0, "abdeckung_licht": 0.89}))[1]
    assert not lz.jahreswert_gueltig(pd.Series({"flaeche_nicht_geladen": 5.0, "licht_summe": 1.0, "abdeckung_licht": 1.0}))[0]
    assert not lz.jahreswert_gueltig(pd.Series({"flaeche_nicht_geladen": 0.0, "licht_summe": 0.0, "abdeckung_licht": 1.0}))[0]
    assert not lz.jahreswert_gueltig(None)[0]


def test_index_2018():
    assert lz.index({2018: 200.0, 2019: 210.0, 2020: None}) == {2018: 100, 2019: 105}
    assert lz.index({2019: 1.0}) == {}
    assert lz.index({2018: 0.0, 2019: 1.0}) == {}


# ---------------------------------------------------------------- Zusammenbau je Land


def _monatszeilen(code, monate, abdeckung=1.0, schnee=0.0, ng=0.0, summe=100.0):
    return pd.DataFrame({
        "weltbank_code": code, "monat": monate, "flaeche_km2": 1000.0, "abdeckung": abdeckung,
        "anteil_nicht_geladen": ng, "anteil_schnee_verdacht": schnee, "licht_summe_abgedeckt": summe,
        "licht_summe": summe if abdeckung >= 0.9 else NAN, "gebiet_weltbank": "passt", "reinheit": 0.9, "kennzeichen": "",
    })


def _wb(pk_nicht_verwenden=False):
    j = {}
    for jahr, (bip, bev) in {2018: (1000.0, 10.0), 2019: (1100.0, 10.0)}.items():
        j[jahr] = {"bip_real": {"wert": bip, "vorlaeufig": False, "nicht_verwenden": False},
                   "bip_pro_kopf": {"wert": None if pk_nicht_verwenden else bip / bev, "vorlaeufig": False,
                                    "nicht_verwenden": pk_nicht_verwenden},
                   "bevoelkerung": {"wert": bev, "vorlaeufig": False, "nicht_verwenden": False}}
    return {"name": "Testland", "jahre": j}


def _jahr_tab(summe2018=1200.0, summe2019=1320.0, abdeckung=0.95):
    def g(s):
        return pd.DataFrame({"licht_summe": [s], "flaeche": [1000.0], "flaeche_nicht_geladen": [0.0],
                             "abdeckung_licht": [abdeckung], "reinheit_licht": [0.9], "anteil_wenige_monate": [0.0],
                             "anteil_nord65": [0.0]}, index=["XXX"])
    return {2018: g(summe2018), 2019: g(summe2019)}


def test_reihe_je_land_werte_und_index():
    m = _monate(2018, 24)
    r = lz.reihe_je_land("XXX", _monatszeilen("XXX", m), _jahr_tab(), _wb(), m)
    assert len(r["monate"]) == 24 and all(p["status"] == "gueltig" for p in r["monate"])
    assert r["monate"][0]["pro_kopf"] == 10.0 and r["monate"][0]["je_km2"] == 0.1
    assert r["gleitend"]["summe"][0] == {"monat": "2018-12", "wert": 100.0}
    assert not r["saison"]["summe"]["bestimmbar"]
    assert r["index"]["licht_summe"] == {"2018": 100, "2019": 110}
    assert r["index"]["bip_real"] == {"2018": 100, "2019": 110}
    assert r["index"]["licht_pro_kopf"] == {"2018": 100, "2019": 110}
    assert r["jahre"]["2019"]["licht_summe"] == 1320.0


def test_ungueltiger_jahreswert_2018_gibt_keinen_licht_index():
    m = _monate(2018, 24)
    r = lz.reihe_je_land("XXX", _monatszeilen("XXX", m), _jahr_tab(abdeckung=0.8), _wb(), m)
    assert r["index"]["licht_summe"] == {}
    assert r["jahre"]["2018"]["licht_gueltig"] is False and "90 %" in r["jahre"]["2018"]["licht_grund"]
    assert r["jahre"]["2018"]["licht_summe"] is None


def test_pro_kopf_gesperrt_wenn_bevoelkerung_nicht_passt():
    m = _monate(2018, 12)
    r = lz.reihe_je_land("XXX", _monatszeilen("XXX", m), _jahr_tab(), _wb(pk_nicht_verwenden=True), m)
    assert all(p["pro_kopf"] is None for p in r["monate"])
    assert r["index"]["licht_pro_kopf"] == {} and not r["kennzeichen"]["pro_kopf_erlaubt"]


def test_geringe_abdeckung_zeigt_teilsumme_nie_als_landessumme():
    m = _monate(2018, 12)
    r = lz.reihe_je_land("XXX", _monatszeilen("XXX", m, abdeckung=0.5, summe=40.0), {}, _wb(), m)
    assert all(p["status"] == "gering" and p["summe"] == 40.0 for p in r["monate"])
    assert r["gleitend"]["summe"] == []  # nie aus Teilsummen gemittelt
    assert r["kennzeichen"]["monate_gering"] == 12


def test_nicht_geladen_hat_keinen_wert():
    m = _monate(2018, 3)
    r = lz.reihe_je_land("XXX", _monatszeilen("XXX", m, ng=0.9), {}, _wb(), m)
    assert all(p["status"] == "nicht_geladen" and p["summe"] is None for p in r["monate"])


# ---------------------------------------------------------------- Sperre 2023–2025


def test_sperre_2023():
    with pytest.raises(lz.ZeitraumGesperrt):
        lz._pruefe_monat((2023, 1))
    with pytest.raises(lz.ZeitraumGesperrt):
        lz.rechne([(2022, 12), (2023, 1)])
    with pytest.raises(lz.ZeitraumGesperrt):
        lz.weltbank_werte([2022, 2023])
    lz._pruefe_monat((2022, 12))
