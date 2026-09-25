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
