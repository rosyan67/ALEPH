"""Prüft die statistischen Bausteine (aleph/detect/statistik.py) an bekannten Werten."""

import numpy as np
import pytest

from aleph.detect.anomalie import zusammenhaengende_gruppen
from aleph.detect.statistik import benjamini_hochberg, normal_zweiseitig


def test_normal_zweiseitig_bekannte_werte():
    # Bekannte Tabellenwerte der Standardnormalverteilung (zweiseitig).
    z = np.array([0.0, 1.0, 1.959963985, 2.575829304, 3.0, 5.0])
    erwartet = np.array([1.0, 0.31731051, 0.05, 0.01, 0.0026997960633, 5.7330314e-7])
    np.testing.assert_allclose(normal_zweiseitig(z), erwartet, rtol=1e-6)


def test_normal_zweiseitig_symmetrie_nan_und_unendlich():
    p = normal_zweiseitig(np.array([-3.0, 3.0, np.nan, np.inf, -np.inf]))
    assert p[0] == p[1]
    assert np.isnan(p[2])
    assert p[3] == 0.0 and p[4] == 0.0


def test_benjamini_hochberg_lehrbuchbeispiel():
    # Selbst gewählte Zahlen, von Hand nachgerechnet (kein Zitat aus der Originalarbeit): m = 10, q = 0.05,
    # Grenzen q*i/m = 0.005, 0.010, 0.015, ...
    p = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.060, 0.074, 0.205, 0.212, 0.216])
    treffer = benjamini_hochberg(p, 0.05)
    assert treffer.tolist() == [True, True] + [False] * 8  # 0.008 <= 0.010, 0.039 > 0.015


def test_benjamini_hochberg_nimmt_alle_bis_zum_groessten_erfuellten_rang():
    # p_(3) = 0.014 <= 0.05*3/4 = 0.0375 erfüllt, obwohl p_(2) = 0.030 > 0.05*2/4 = 0.025 die Grenze reißt.
    p = np.array([0.001, 0.030, 0.014, 0.9])
    assert benjamini_hochberg(p, 0.05).tolist() == [True, True, True, False]


def test_benjamini_hochberg_ignoriert_nan_und_zaehlt_sie_nicht_mit():
    p = np.array([0.03, np.nan, np.nan, np.nan])  # m = 1: 0.03 <= 0.05 * 1/1
    assert benjamini_hochberg(p, 0.05).tolist() == [True, False, False, False]
    p2 = np.array([0.03] + [0.5] * 9)  # m = 10: 0.03 > 0.05 * 1/10
    assert not benjamini_hochberg(p2, 0.05).any()


def test_benjamini_hochberg_ohne_p_werte_und_form_bleibt():
    assert benjamini_hochberg(np.full(5, np.nan), 0.05).shape == (5,)
    assert benjamini_hochberg(np.full((3, 4), 0.9), 0.05).shape == (3, 4)


def test_ohne_korrektur_gaebe_es_viele_treffer_mit_korrektur_fast_keine():
    rng = np.random.default_rng(4)
    p = rng.random(100_000)
    assert (p < 0.05).sum() > 4000  # unkorrigiert: rund 5 % der Zellen
    assert benjamini_hochberg(p, 0.05).sum() == 0


# --- Zusammenhängende Zellen -----------------------------------------------------


def test_gruppen_diagonale_nachbarn_gehoeren_zusammen():
    m = np.zeros((5, 6), bool)
    m[1, 1] = m[2, 2] = m[3, 3] = True  # nur über Ecken verbunden (8er-Nachbarschaft)
    beschr, n = zusammenhaengende_gruppen(m)
    assert n == 1 and set(beschr[m]) == {1}


def test_gruppen_getrennte_zellen_sind_getrennt():
    m = np.zeros((5, 8), bool)
    m[0, 0] = m[0, 1] = True
    m[4, 5] = m[4, 6] = m[3, 6] = True
    beschr, n = zusammenhaengende_gruppen(m)
    assert n == 2
    assert len(set(beschr[0, :2])) == 1 and len(set(beschr[3:, 5:7][m[3:, 5:7]])) == 1
    assert beschr[0, 0] != beschr[4, 5]


def test_gruppen_schliessen_den_laengengrad_umbruch():
    m = np.zeros((4, 10), bool)
    m[1, 0] = m[1, 9] = m[2, 9] = True  # letzte Spalte grenzt an die erste
    beschr, n = zusammenhaengende_gruppen(m)
    assert n == 1


def test_gruppen_umbruch_gilt_nicht_fuer_die_breite():
    m = np.zeros((6, 4), bool)
    m[0, 1] = m[5, 1] = True  # Nordrand und Südrand sind nicht benachbart
    assert zusammenhaengende_gruppen(m)[1] == 2


def test_gruppen_leer():
    beschr, n = zusammenhaengende_gruppen(np.zeros((3, 3), bool))
    assert n == 0 and not beschr.any()


# --- Wann bindet Benjamini-Hochberg wirklich? ---------------------------------------


def test_bh_haelt_bei_einer_million_tests_eine_zelle_knapp_ueber_5_sigma_zurueck():
    """Bei sehr vielen Tests wirkt BH über den festen Mindestwert |z| >= 5 hinaus: Eine einzelne Zelle mit |z| = 5,05
    (p = 4,5e-7) bleibt bei m = 1 000 000 unter der Grenze 0,05/m = 5e-8 nicht erhalten, |z| = 5,6 (p = 2e-8) schon."""
    m = 1_000_000
    hintergrund = np.full(m - 1, 0.5)
    for z, erwartet in ((5.05, False), (5.6, True)):
        p = np.append(hintergrund, normal_zweiseitig(np.array([z])))
        assert bool(benjamini_hochberg(p, 0.05)[-1]) is erwartet, z


def test_bh_bei_kleiner_testzahl_bindet_nicht_enger_als_der_mindestwert():
    """Bei m = 3 200 (Testwürfel) passiert jedes |z| >= 5 (p = 5,7e-7 < 0,05/3200 = 1,6e-5) BH automatisch;
    BH ändert dort am Ergebnis nichts (ehrliche Beschreibung in aleph/detect/anomalie.py)."""
    p = np.append(np.full(3199, 0.5), normal_zweiseitig(np.array([5.0])))
    assert benjamini_hochberg(p, 0.05)[-1]


def test_bh_ist_unter_reinem_zufall_nicht_viel_vorsichtiger_als_q():
    """Unter der globalen Nullhypothese meldet BH in genau etwa q der Läufe etwas (nicht nur „höchstens")."""
    rng = np.random.default_rng(3)
    laeufe = 2000
    anteil = sum(bool(benjamini_hochberg(rng.random(1000), 0.05).any()) for _ in range(laeufe)) / laeufe
    assert 0.035 < anteil < 0.065  # erwartet 0,05, Standardabweichung etwa 0,005


# --- Statistisches Grundgerüst (2026-09-26) ----------------------------------------------------

import math

import scipy.stats as sst

from aleph.detect import statistik as st


def _reihen(seed=1, t=60, n=6):
    rng = np.random.default_rng(seed)
    y = np.round(rng.normal(size=(t, n)).cumsum(0) * 2) / 2 + np.arange(t)[:, None] * 0.05  # mit Bindungen
    return y


def test_mann_kendall_stimmt_mit_scipy_kendalltau_ueberein_auch_mit_bindungen_und_luecken():
    y = _reihen()
    y[5, 2] = np.nan
    y[10:13, 3] = np.nan
    mk = st.mann_kendall(y)
    for j in range(y.shape[1]):
        ok = np.isfinite(y[:, j])
        t = np.arange(len(y))[ok]
        tau = sst.kendalltau(t, y[ok, j], method="asymptotic")
        z_ohne_stetigkeit = mk["s"][j] / math.sqrt(mk["var_s"][j])
        assert mk["n"][j] == ok.sum()
        assert abs(st.normal_zweiseitig(np.array([z_ohne_stetigkeit]))[0] - tau.pvalue) < 1e-9


def test_bindungssumme_von_hand():
    # Werte 1,1,2,2,2,3: Gruppen 2 und 3 -> 2*1*9 + 3*2*11 = 18 + 66 = 84; NaN zählt nicht.
    y = np.array([1, 1, 2, 2, 2, 3, np.nan], dtype=float)
    assert st.bindungs_summe(y)[0] == 84


def test_sen_steigung_stimmt_mit_scipy_theilslopes_ueberein():
    y = _reihen(seed=3)
    mk = st.mann_kendall(y)
    sen = st.sen_steigung(y, mk["var_s"])
    for j in range(y.shape[1]):
        ts = sst.theilslopes(y[:, j], np.arange(len(y)), alpha=0.95)
        assert abs(sen["steigung"][j] - ts.slope) < 1e-5
        assert sen["unten"][j] <= sen["steigung"][j] <= sen["oben"][j]
        assert abs(sen["unten"][j] - ts.low_slope) < 1e-5  # untere Grenze gleich; obere weicht je nach Bindungsrechnung minimal ab


def test_konstante_reihe_gibt_s_null_und_z_null_nicht_nan():
    mk = st.mann_kendall(np.zeros((30, 2)))
    assert mk["s"].tolist() == [0, 0] and mk["z"].tolist() == [0, 0]


def test_zu_kurze_oder_leere_reihe_liefert_nan_nicht_null():
    y = np.full((30, 1), np.nan)
    mk = st.mann_kendall(y)
    assert mk["n"][0] == 0 and np.isnan(st.sen_steigung(y)["steigung"][0])


def _ar1(rho, t=150, n=3000, seed=0):
    rng = np.random.default_rng(seed)
    e = rng.normal(size=(t, n))
    y = np.empty_like(e)
    y[0] = e[0]
    for k in range(1, t):
        y[k] = rho * y[k - 1] + math.sqrt(1 - rho * rho) * e[k]
    return y


def test_hamed_rao_vergroessert_bei_autokorrelation_und_nie_unter_eins():
    for rho, mindest_median in ((0.0, 1.0), (0.8, 2.0)):
        y = _ar1(rho)
        mk = st.mann_kendall(y)
        b = st.sen_steigung(y, mk["var_s"])["steigung"]
        f = st.hamed_rao(y, b, mk["var_s"])["faktor"]
        assert np.nanmin(f) >= 1.0
        assert np.nanmedian(f) >= mindest_median
    y = _ar1(0.0, seed=4)
    mk = st.mann_kendall(y)
    b = st.sen_steigung(y, mk["var_s"])["steigung"]
    assert (st.hamed_rao(y, b, mk["var_s"], nur_vergroessern=False)["faktor"] < 1).any()  # ohne Untergrenze: auch < 1


def test_hamed_rao_senkt_falsche_treffer_bei_autokorrelation():
    y = _ar1(0.5, seed=2)
    mk = st.mann_kendall(y)
    b = st.sen_steigung(y, mk["var_s"])["steigung"]
    hr = st.hamed_rao(y, b, mk["var_s"])
    z = (mk["s"] - np.sign(mk["s"])) / np.sqrt(hr["var_s"])
    ohne = (st.normal_zweiseitig(mk["z"]) < 0.05).mean()
    mit = (st.normal_zweiseitig(z) < 0.05).mean()
    assert ohne > 0.15 and mit < 0.5 * ohne


def test_yue_vorbleichung_nur_bei_signifikantem_r1_und_erster_wert_fehlt():
    y = np.concatenate([_ar1(0.8, n=5), _ar1(0.0, n=5, seed=9)], axis=1)
    b = st.sen_steigung(y)["steigung"]
    v = st.yue_vorbleichung(y, b)
    assert v["wirksam"][:5].all()
    assert np.isnan(v["reihe"][0, :5]).all()  # kein Auffüllen
    ohne = ~v["wirksam"]
    np.testing.assert_array_equal(v["reihe"][:, ohne], y[:, ohne])


def test_alpha_fdr_ist_doppeltes_globales_niveau():
    assert st.alpha_fdr(0.05) == pytest.approx(0.10)
    with pytest.raises(ValueError):
        st.alpha_fdr(0.6)


def test_mindestlaengen_pruefen_sich_selbst():
    with pytest.raises(ValueError):
        st.Mindestlaengen(mann_kendall=5)
    with pytest.raises(ValueError):
        st.Mindestlaengen(mann_kendall=30, autokorrelation=20)


def test_zellflaechen_ergeben_die_kugeloberflaeche_und_schrumpfen_zu_den_polen():
    breite = 90 - 0.125 - np.arange(720) * 0.25
    gesamt = st.zellflaeche_km2(breite).sum() * 1440
    assert gesamt == pytest.approx(4 * math.pi * st.ERDRADIUS_KM**2, rel=1e-9)
    f = st.zellflaeche_km2(np.array([0.125, 60.125]))
    assert f[1] / f[0] == pytest.approx(0.5, abs=0.003)


def test_flaechenanteil_gewichtet_nach_breite_und_ignoriert_die_laenge():
    breite = np.array([0.125, 60.125])
    maske = np.array([[True, True], [False, False]])
    bezug = np.ones((2, 2), bool)
    # Äquatorzeile hat doppelte Fläche der 60°-Zeile: Anteil ≈ 2/3, nicht 1/2 (ungewichtet).
    assert st.flaechenanteil(maske, bezug, breite) == pytest.approx(2 / 3, abs=0.002)
    assert np.isnan(st.flaechenanteil(maske, np.zeros((2, 2), bool), breite))


def test_nachbarschaft_schliesst_die_datumsgrenze_und_ist_symmetrisch():
    m = np.ones((4, 10), bool)
    w, ys, xs = st.nachbarschaft(m)
    d = w.toarray()
    assert (d == d.T).all() and d.diagonal().sum() == 0
    i = lambda y, x: int(np.flatnonzero((ys == y) & (xs == x))[0])
    assert d[i(1, 0), i(1, 9)] == 1 and d[i(1, 0), i(2, 9)] == 1  # Spalte 0 grenzt an Spalte 9
    assert d.sum(axis=1)[i(1, 5)] == 8 and d.sum(axis=1)[i(0, 5)] == 5
    w2, *_ = st.nachbarschaft(m, umbruch=False)
    assert w2.toarray()[i(1, 0), i(1, 9)] == 0


def test_morans_i_wie_volle_matrix_und_vorzeichen():
    m = np.ones((12, 16), bool)
    w, ys, xs = st.nachbarschaft(m)
    rng = np.random.default_rng(3)
    x = rng.normal(size=ys.size)
    d = w.toarray()
    z = x - x.mean()
    direkt = (len(z) / d.sum()) * (z @ d @ z) / (z @ z)
    assert st.morans_i(x, w)["i"][0] == pytest.approx(direkt)
    glatt = np.sin(ys / 3.0) + np.cos(xs / 3.0)
    streifen = np.where(xs % 2 == 0, 1.0, -1.0)  # 6 von 8 Nachbarn mit anderem Vorzeichen (Schachbrett wäre ~0)
    assert st.morans_i(glatt, w)["i"][0] > 0.5
    assert st.morans_i(streifen, w)["i"][0] < -0.2
    assert st.morans_i(x, w)["erwartung"] == pytest.approx(-1 / (ys.size - 1))


def test_mad_faktor_ist_kehrwert_des_normalquantils():
    assert 1 / st._normal_quantil(0.75) == pytest.approx(1.4826, abs=1e-4)
