"""Tests für aleph/link/nachtlicht_einheiten.py (Technikprobe Nachtlicht × Einheiten × Weltbank-Sicht)."""

import numpy as np
import pandas as pd
import pytest

from aleph.link import nachtlicht_einheiten as ne


def _gitter():
    """2 × 3 Zellen. Einheit A: Zelle (0,0) ganz, (0,1) halb (Rest Meer). Einheit B: (1,0), (1,1) ganz.
    Einheit C: (0,2) zu 2 % (Rest Meer), (1,2) ganz. Zellfläche je 100 km²."""
    z = pd.DataFrame([
        (0, 0, "A", 100.0, 1.0), (0, 1, "A", 50.0, 0.5),
        (1, 0, "B", 100.0, 1.0), (1, 1, "B", 100.0, 1.0),
        (0, 2, "C", 2.0, 0.02), (1, 2, "C", 100.0, 1.0),
    ], columns=["zeile", "spalte", "einheit_id", "flaeche_km2", "anteil"])
    mittel = np.array([[10.0, 4.0, 50.0], [2.0, 6.0, 1.0]])
    gueltig = np.full((2, 3), 3600.0)
    aufg = np.zeros((2, 3))
    return z, mittel, gueltig, aufg, np.array([10.0, 9.75])


def test_normierte_verteilung_schiebt_kuestenlicht_aufs_land():
    z, m, g, a, breite = _gitter()
    t = ne.nachtlicht_je_einheit((2018, 1), "vollständig", m, g, a, None, z, breite).set_index("einheit_id")
    # A: Zelle (0,0) 10 × 100; Zelle (0,1) Licht 4 × 100 ganz aufs Land (Normierung durch S = 0,5) -> 1000 + 400
    assert t.loc["A", "licht_summe"] == pytest.approx(1400.0)
    assert t.loc["B", "licht_summe"] == pytest.approx(200.0 + 600.0)
    # C: Zelle (0,2) hat nur 2 % Land (< s_min 0,05): nicht verteilt, getrennt ausgewiesen
    assert t.loc["C", "anteil_nicht_verteilt"] == pytest.approx(2.0 / 102.0)
    assert t.loc["C", "licht_summe_abgedeckt"] == pytest.approx(100.0)
    flach = ne.nachtlicht_je_einheit((2018, 1), "vollständig", m, g, a, None, z, breite,
                                     ne.VerknuepfungsEinstellungen(verteilung="flaechenanteil")).set_index("einheit_id")
    assert flach.loc["A", "licht_summe"] == pytest.approx(1000.0 + 200.0)


def test_fehlende_daten_werden_nie_null_und_nicht_mitgezaehlt():
    z, m, g, a, breite = _gitter()
    g = g.copy()
    a = a.copy()
    nicht_geladen = np.zeros((2, 3), bool)
    nicht_geladen[1, 0] = True  # B halb nicht geladen
    a[1, 1] = 2500.0  # B: andere Hälfte unter 50 % beobachtet
    g[0, 0] = 0.0  # A: Zelle ohne gültige Pixel
    t = ne.nachtlicht_je_einheit((2018, 1), "nur Afrika-Europa-Asien", m, g, a, nicht_geladen, z, breite).set_index("einheit_id")
    assert np.isnan(t.loc["B", "licht_summe_abgedeckt"]) and np.isnan(t.loc["B", "licht_summe"])
    assert t.loc["B", "abdeckung"] == 0
    assert t.loc["B", "anteil_nicht_geladen"] == pytest.approx(0.5) and t.loc["B", "anteil_unzureichend"] == pytest.approx(0.5)
    assert t.loc["A", "anteil_keine_daten"] == pytest.approx(100 / 150)
    assert np.isnan(t.loc["A", "licht_summe"])  # Abdeckung 1/3 < 0,9: keine Summe
    assert t.loc["A", "licht_summe_abgedeckt"] == pytest.approx(400.0)


def test_pflichtfelder():
    z, m, g, a, breite = _gitter()
    t = ne.nachtlicht_je_einheit((2018, 1), "vollständig", m, g, a, None, z, breite)
    for spalte in ("evidenzstufe", "methode", "version", "abdeckung", "n_zellen", "zustand"):
        assert t[spalte].notna().all()


def _einheiten():
    return pd.DataFrame({
        "einheit_id": ["A", "B", "C"],
        "weltbank_code": ["TZA", "GEO", "GEO"],
        "weltbank_art": ["abweichend", "abweichend", "unklar"],
        "ebene": ["Land (Grenzdatei)", "Land (Grenzdatei)", "Sondereinheit (automatisch)"],
    })


def test_weltbank_sicht_summen_und_kennzeichen():
    z, m, g, a, breite = _gitter()
    je = ne.nachtlicht_je_einheit((2018, 1), "vollständig", m, g, a, None, z, breite)
    laender = {"TZA": {"gebiet": "abweichend"}, "GEO": {"gebiet": "abweichend"}}
    w = ne.je_weltbank_land(je, _einheiten(), laender).set_index("weltbank_code")
    assert w.loc["GEO", "licht_summe_abgedeckt"] == pytest.approx(800.0 + 100.0)
    assert "Sansibar" in w.loc["TZA", "kennzeichen"] and "Festland" in w.loc["TZA", "kennzeichen"]
    assert "berücksichtigt" in w.loc["GEO", "kennzeichen"]
    assert w.loc["GEO", "anteil_unklare_flaeche"] == pytest.approx(102 / 302)
    ohne = ne.je_weltbank_land(je, _einheiten(), laender, e=ne.VerknuepfungsEinstellungen(mit_unklar=False)).set_index("weltbank_code")
    assert ohne.loc["GEO", "licht_summe_abgedeckt"] == pytest.approx(800.0)
    raus = ne.je_weltbank_land(je, _einheiten(), laender, e=ne.VerknuepfungsEinstellungen(tansania="ausschliessen"))
    assert "TZA" not in set(raus["weltbank_code"])


def test_einstellungen_pruefen_sich_und_sansibar_ist_nicht_gebaut():
    with pytest.raises(NotImplementedError):
        ne.VerknuepfungsEinstellungen(tansania="sansibar_abziehen")
    with pytest.raises(ValueError):
        ne.VerknuepfungsEinstellungen(verteilung="gleichmaessig")


def _ssd_da():
    try:
        from aleph.layers import vnp46a3, zell_einheiten
        return vnp46a3._wuerfel_pfad().exists() and (zell_einheiten.ergebnis_ordner() / "manifest.json").is_file()
    except Exception:
        return False


@pytest.mark.echter_katalog  # liest die echte Referenzliste (Stufe-1-Nachweis), ohne Netz
@pytest.mark.skipif(not _ssd_da(), reason="SSD mit Würfel und Zell-Zuordnung nicht angeschlossen")
def test_technikprobe_2018_01_echte_daten():
    r = ne.technikprobe((2018, 1))
    w = r["je_land"].set_index("weltbank_code")
    for code in ("EGY", "DEU", "SAU", "NGA", "IND"):
        assert w.loc[code, "abdeckung"] > 0.95 and w.loc[code, "licht_summe"] > 0
    # USA: im Zustand 4 (nur Afrika-Europa-Asien) „nicht geladen“; seit 2018-01 vollständig ist (Ladestand 2026-10),
    # sind die USA gemessen – im Januar mit Schnee unter 90 % Abdeckung, also ohne Landessumme.
    import xarray as xr
    from aleph.layers import vnp46a3
    ds = xr.open_zarr(vnp46a3._wuerfel_pfad())
    zustand = int(ds["monat_fertig"].sel(zeit="2018-01-01").values)
    ds.close()
    if zustand == 4:
        assert np.isnan(w.loc["USA", "licht_summe"]) and "nicht geladen" in w.loc["USA", "kennzeichen"]
    else:
        assert zustand == 1 and "nicht geladen" not in w.loc["USA", "kennzeichen"]
        assert w.loc["USA", "abdeckung"] > 0.5
    assert (r["je_land"]["evidenzstufe"] == "beobachtet").all()
    with pytest.raises(ValueError):
        ne.technikprobe((2023, 1))
