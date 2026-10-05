"""Tests für aleph/diagnose/anstieg_2021_2022.py – nur künstliche Daten (kein Würfel nötig)."""

import numpy as np
import pytest

from aleph.detect.schnee import schnee_verdacht
from aleph.diagnose import anstieg_2021_2022 as an


def test_zeitraum_gesperrt_und_monate():
    with pytest.raises(an.ZeitraumGesperrt):
        an.pruefe_monat((2023, 1))
    an.pruefe_monat((2022, 12))
    assert max(an.MONATE) < (2023, 1)
    assert (2022, 7) not in an.MONATE and len(an.MONATE) == 119


def _reihe(n=118, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    return t, rng.normal(0, 0.01, n)


def test_bruch_findet_eingebaute_stufe():
    t, e = _reihe()
    y = 0.001 * t + 0.15 * (t >= 101) + e
    m = an.bruch_modelle(t, y)
    assert m["M_stufe"]["k"] == 101
    assert abs(m["M_stufe"]["stufe"] - 0.15) < 0.02
    assert m["M_stufe"]["bic"] < m["M_knick"]["bic"] < m["M0"]["bic"]


def test_bruch_erkennt_schleichenden_anstieg():
    t, e = _reihe(seed=2)
    y = 0.004 * np.maximum(t - 80, 0) + e
    m = an.bruch_modelle(t, y)
    assert m["M_knick"]["bic"] < m["M_stufe"]["bic"]
    assert abs(m["M_knick"]["k"] - 80) <= 3


def test_bruch_zusatzregressor_wird_geschaetzt():
    t, e = _reihe(seed=3)
    f = np.clip((t - 99) / 3, 0, 1)
    y = 0.12 * f + e
    m = an.bruch_modelle(t, y, {"M_l1b": f})
    assert abs(m["M_l1b"]["koeffizienten"][0] - 0.12) < 0.02
    assert m["M_l1b"]["bic"] < m["M0"]["bic"]


def test_bruch_bootstrap_lage_eng_bei_klarer_stufe():
    t, e = _reihe(seed=4)
    y = 0.2 * (t >= 60) + e
    ks = an.bruch_bootstrap(t, y, n_boot=40)
    assert np.all(np.abs(ks - 60) <= 1)


def test_basislinie_braucht_vier_jahre():
    monate = [(j, 1) for j in range(2013, 2020)]
    x = np.arange(7, dtype=float)[:, None] * np.ones((1, 2))
    g = np.ones_like(x, dtype=bool)
    g[:4, 1] = False  # Zelle 1 nur 3 Jahre gültig
    b = an.basislinie(x, g, monate)
    assert b[0, 0] == 3.0 and np.isnan(b[0, 1]) and np.isnan(b[1]).all()


def test_monatsindex_gewichtet_und_nur_beleuchtet():
    x = np.array([[2.2, 11.0, 0.3]])
    bm = np.array([[2.0, 10.0, 0.2]])  # Zelle 3 dunkel (B < 0,5): geht nicht ein
    g = np.ones_like(x, dtype=bool)
    a = np.array([1.0, 1.0, 1.0])
    r = an.monatsindex(x, g, bm, a, np.ones(3, dtype=bool))
    assert r["index"][0] == pytest.approx(13.2 / 12.0)
    assert r["zellen"][0] == 2


def test_jahresindex_bootstrap_konstantes_verhaeltnis():
    monate = [(j, m) for j in (2019, 2020) for m in range(1, 13)]
    n = 200
    bm = np.ones((24, n)) * 5
    x = bm.copy()
    x[12:] *= 1.1
    g = np.ones_like(x, dtype=bool)
    kacheln = np.arange(n) // 10
    r = an.jahresindex_bootstrap(x, g, bm, np.ones(n), np.ones(n, dtype=bool), monate, kacheln, [2019, 2020], n_boot=50)
    assert r["wert"] == pytest.approx([1.0, 1.1])
    assert r["unten"][1] == pytest.approx(1.1) and r["oben"][1] == pytest.approx(1.1)
    v = an.verhaeltnis_mit_intervall(r["boot"], [2019, 2020], 2020, 2019, r["wert"])
    assert v["wert"] == pytest.approx(1.1)


def test_klassen_grenzen():
    k = an.klassen(np.array([0.0, 0.49, 0.5, 4.99, 5.0, np.nan]))
    assert list(k) == ["dunkel", "dunkel", "mittel", "mittel", "hell", ""]


def test_schnee_je_zelle_gleich_regel():
    breite = np.array([60.0, 10.0, -40.0, 30.0])
    anteil = np.array([0.6, 0.6, 0.95, 0.8])
    for monat in (1, 6):
        erwartet = np.array([schnee_verdacht(np.array([b]), monat, np.array([[a]]))[0, 0] for b, a in zip(breite, anteil)])
        assert np.array_equal(an._schnee_1d(breite, monat, anteil), erwartet)


def test_regel_r1_waehlt_nur_dunkle_wuestenzellen():
    monate = [(j, m) for j in range(2013, 2020) for m in range(1, 13)]
    x = np.zeros((84, 4))
    x[5, 1] = 0.3  # einmal heller als 0,1
    g = np.ones_like(x, dtype=bool)
    breite = np.array([25.0, 25.0, 50.0, 25.0])
    land = np.array([1.0, 1.0, 1.0, 0.5])
    assert list(an.regel_r1(x, g, monate, breite, land)) == [True, False, False, False]


def test_regel_r2_hauptregel_und_wechsel_zur_ersatzregel():
    monate = [(j, m) for j in range(2013, 2020) for m in range(1, 13)]
    for stabil, erwartet_summe, erwartet_regel in ((35, 35, "Hauptregel"), (20, 4, "Ersatzregel")):
        n = 40
        bm = np.full((84, n), 10.0)
        x = bm.copy()
        x[:12, stabil:] *= 1.2  # 2013 um 20 % höher: diese Zellen sind instabil
        g = np.ones_like(x, dtype=bool)
        m, regel, _ = an.regel_r2(x, g, bm, monate, np.zeros(n), np.array(["hell"] * n, dtype=object))
        assert erwartet_regel in regel and m.sum() == erwartet_summe and not m[stabil:].any()


def test_regel_r2_ersatz_waehlt_zehn_prozent():
    monate = [(j, m) for j in range(2013, 2020) for m in range(1, 13)]
    n = 100
    bm = np.full((84, n), 10.0)
    x = bm.copy()
    x[:12] *= (1.06 + np.arange(n) / 1000)[None, :]  # alle über 5 %, Zelle 0 am stabilsten
    g = np.ones_like(x, dtype=bool)
    m, regel, abw = an.regel_r2(x, g, bm, monate, np.zeros(n), np.array(["hell"] * n, dtype=object))
    assert "Ersatzregel" in regel and m.sum() == 10 and m[:10].all()
