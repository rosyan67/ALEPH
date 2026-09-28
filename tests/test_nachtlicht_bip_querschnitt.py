"""Tests für aleph/link/nachtlicht_bip_querschnitt.py (künstliche Daten; eine Prüfung liest die YAML im Projekt)."""

import numpy as np
import pandas as pd
import pytest

from aleph.link import nachtlicht_bip_querschnitt as q

R = q.Regeln(bootstrap_n=300)


def _monat(sammler, kalendermonat, werte, beob=1.0, breite=(10.0, 10.0), nicht_geladen=None):
    werte = np.asarray(werte, float)
    gueltig = np.full(werte.shape, 3600.0)
    aufgefuellt = np.full(werte.shape, 3600.0 * (1 - beob))
    sammler.monat(kalendermonat, werte, gueltig, aufgefuellt, nicht_geladen, np.asarray(breite), R)


def test_jahreswert_braucht_sechs_gute_monate():
    s = q.JahresSammler((1, 2))
    for m in range(1, 13):
        # Zelle 0: nur 5 Monate mit ≥ 50 % beobachtet; Zelle 1: 6 Monate
        beob = np.array([[1.0 if m <= 5 else 0.3, 1.0 if m <= 6 else 0.3]])
        s.monat(m, np.array([[2.0, 4.0]]), np.full((1, 2), 3600.0), 3600.0 * (1 - beob), None, np.array([10.0]), R)
    e = s.ergebnis(R)
    assert np.isnan(e["jahreswert"][0, 0]) and e["jahreswert"][0, 1] == pytest.approx(4.0)
    assert list(e["n_gut"][0]) == [5, 6]
    # Schätzwert (nur Gewichtung) nutzt auch die dünn beobachteten Monate
    assert e["schaetzwert"][0, 0] == pytest.approx(2.0)


def test_schnee_verdacht_zaehlt_nicht_als_guter_monat():
    s = q.JahresSammler((1, 1))
    for m in range(1, 13):
        # 60° N, Winter (Nov–Apr) mit 80 % beobachtet → Schnee-Verdacht; Sommer 100 %
        beob = 0.8 if m in (11, 12, 1, 2, 3, 4) else 1.0
        wert = 100.0 if m in (11, 12, 1, 2, 3, 4) else 5.0
        _monat(s, m, [[wert]], beob=beob, breite=(60.0,))
    e = s.ergebnis(R)
    assert e["n_gut"][0, 0] == 6 and e["jahreswert"][0, 0] == pytest.approx(5.0)


def _tabelle():
    # Zelle (0,0): ganz Land A; Zelle (0,1): 50/50 A und B; Zelle (0,2): ganz B
    return pd.DataFrame({
        "weltbank_code": ["A", "A", "B", "B"], "zeile": [0, 0, 0, 0], "spalte": [0, 1, 1, 2],
        "anteil": [1.0, 0.5, 0.5, 1.0], "flaeche_km2": [100.0, 50.0, 50.0, 100.0], "land_anteil": [1.0, 1.0, 1.0, 1.0],
        "zellflaeche_km2": [100.0] * 4, "gewicht_km2": [100.0, 50.0, 50.0, 100.0], "verteilt": [True] * 4,
        "rein": [True, False, False, True]})


def _zellen(a, s=None, n=None, ng=None):
    a = np.asarray([a], float)
    return {"jahreswert": a, "schaetzwert": a if s is None else np.asarray([s], float),
            "n_gut": np.full(a.shape, 12) if n is None else np.asarray([n]),
            "nicht_geladen": np.zeros(a.shape, bool) if ng is None else np.asarray([ng]), "monate": 12}


def test_verteilung_reinheit_und_abdeckung_nach_licht():
    g = q.laender_jahr(_tabelle(), _zellen([1.0, 3.0, 2.0]), np.array([10.0]), R)
    # A: 1×100 + 3×50 = 250; rein 100 → Reinheit 0,4
    assert g.loc["A", "licht_summe"] == pytest.approx(250) and g.loc["A", "reinheit_licht"] == pytest.approx(0.4)
    assert g.loc["B", "licht_summe"] == pytest.approx(350) and g.loc["B", "licht_summe_rein"] == pytest.approx(200)
    # Zelle (0,2) ohne Jahreswert, Schätzwert 8 → B: Licht 150 von 150 + 800
    g2 = q.laender_jahr(_tabelle(), _zellen([1.0, 3.0, np.nan], s=[1.0, 3.0, 8.0]), np.array([10.0]), R)
    assert g2.loc["B", "abdeckung_licht"] == pytest.approx(150 / 950)
    assert g2.loc["A", "abdeckung_licht"] == pytest.approx(1.0)


def test_wenige_monate_und_nord_kennzeichen():
    g = q.laender_jahr(_tabelle(), _zellen([1.0, 3.0, 2.0], n=[7, 12, 12]), np.array([70.0]), R)
    assert g.loc["A", "anteil_wenige_monate"] == pytest.approx(100 / 250)
    assert g.loc["A", "anteil_nord65"] == pytest.approx(1.0)


def test_auswahl_schliesst_nach_regeln_aus():
    g = q.laender_jahr(_tabelle(), _zellen([1.0, 3.0, 2.0], n=[7, 12, 12]), np.array([10.0]), R)
    bip = pd.Series({"A": 1e9, "B": 2e9})
    t = q.auswahl(g, bip, {}, {}, R).set_index("code")
    assert not t.loc["A", "aufgenommen"] and any("Reinheit" in x for x in t.loc["A", "gruende"])
    assert t.loc["A", "wenige_monate"]  # 40 % > ein Drittel
    assert t.loc["B", "aufgenommen"]  # Reinheit 200/350 = 57 %
    t30 = q.auswahl(g, bip, {}, {}, R, reinheit_grenze=0.3).set_index("code")
    assert t30.loc["A", "aufgenommen"]
    t = q.auswahl(g, bip, {"B": "abweichend"}, {}, R).set_index("code")
    assert not t.loc["B", "aufgenommen"] and any("weicht ab" in x for x in t.loc["B", "gruende"])
    g_ng = q.laender_jahr(_tabelle(), _zellen([1.0, 3.0, 2.0], ng=[False, False, True]), np.array([10.0]), R)
    t = q.auswahl(g_ng, bip, {}, {}, R).set_index("code")
    assert any("nicht vollständig geladen" in x for x in t.loc["B", "gruende"])
    t = q.auswahl(g, pd.Series({"A": 1e9}), {}, {}, R).set_index("code")
    assert any("kein reales BIP" in x for x in t.loc["B", "gruende"])


def test_regression_findet_steigung_und_bereich():
    rng = np.random.default_rng(1)
    x = rng.uniform(20, 30, 80)
    y = 0.8 * x + rng.normal(0, 0.5, 80)
    r = q.regression(x, y, 1000, 5)
    assert r["n"] == 80 and r["steigung"] == pytest.approx(0.8, abs=0.05)
    assert r["steigung_unten"] < 0.8 < r["steigung_oben"] and 0.8 < r["r2"] < 1
    assert q.regression(x, y, 1000, 5)["steigung_unten"] == r["steigung_unten"]  # fester Startwert


def test_gesperrte_jahre_werden_verweigert():
    with pytest.raises(ValueError, match="gesperrt"):
        q.rechne(jahre=(2018, 2024))
    with pytest.raises(ValueError):
        q.rechne_jahr(2023, None, R)


def test_ausschlussliste_stimmt_mit_bericht_und_yaml():
    from aleph.layers import zell_einheiten
    sonder = zell_einheiten.lade_sonderliste().get("weltbank_laender", {})
    assert {k for k, v in sonder.items() if v.get("gebiet") == "abweichend"} == q.ABWEICHEND_LAUT_BERICHT
    bericht = (q.Path(q.__file__).resolve().parents[2] / "berichte" / "2026-09-26_weltbank-gebiete.md").read_text(encoding="utf-8")
    assert "Georgien" in bericht and "Moldau" in bericht and "Tansania" in bericht and "Marokko" in bericht and "Zypern" in bericht


def test_land_ausserhalb_der_region_wird_ausgeschlossen_auch_wenn_geladen():
    g = q.laender_jahr(_tabelle(), _zellen([1.0, 3.0, 2.0]), np.array([10.0]), R)
    bip = pd.Series({"A": 1e9, "B": 2e9})
    t = q.auswahl(g, bip, {}, {}, R, region={"A": "Europe", "B": "Americas"}).set_index("code")
    assert not t.loc["B", "aufgenommen"] and any("nicht in Afrika-Europa-Asien" in x for x in t.loc["B", "gruende"])
