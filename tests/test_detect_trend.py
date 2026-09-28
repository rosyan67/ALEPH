"""Tests für aleph/detect/trend.py und aleph/detect/schnee.py (nur künstliche Daten)."""

import numpy as np
import pytest

from aleph.detect import trend as tr
from aleph.detect import wuerfel as lesen
from aleph.detect.anomalie import EndtestGesperrt
from aleph.detect.schnee import schnee_verdacht
from aleph.detect.synthetisch import kuenstlicher_wuerfel


def _monate(n, start=(2010, 1)):
    j, m = start
    aus = []
    for _ in range(n):
        aus.append((j, m))
        m += 1
        if m > 12:
            j, m = j + 1, 1
    return aus


def _tropen(ny=6, nx=8, t=120, seed=0, trend_prozent=0.0):
    rng = np.random.default_rng(seed)
    grund = rng.uniform(5, 50, size=(ny, nx))
    monate = _monate(t)
    saison = 1 + 0.2 * np.cos(2 * np.pi * np.array([m for _, m in monate]) / 12.0)
    wachstum = (1 + trend_prozent / 100.0) ** (np.arange(t) / 12.0)
    werte = grund[None] * saison[:, None, None] * wachstum[:, None, None] * (1 + 0.05 * rng.standard_normal((t, ny, nx)))
    breite = 5 - 0.125 - np.arange(ny) * 0.25  # Tropen: kein Schnee-Verdacht
    laenge = -180 + 0.125 + np.arange(nx) * 0.25
    return werte.astype("float32"), monate, breite, laenge


def test_eingepflanzter_trend_wird_von_beiden_korrekturen_gefunden():
    w, monate, b, l = _tropen(trend_prozent=4.0)
    erg = tr.trend_je_zelle(w, monate, b, l)
    z = erg.zellen
    assert z["trend_beide"].values.all()
    assert np.nanmedian(z["sen_relativ_prozent"].values) == pytest.approx(4.0, abs=0.6)
    assert (z["sen_unten"].values <= z["sen_steigung"].values).all() and (z["sen_steigung"].values <= z["sen_oben"].values).all()


def test_ohne_trend_kaum_meldungen():
    w, monate, b, l = _tropen(ny=20, nx=20, seed=5)
    z = tr.trend_je_zelle(w, monate, b, l).zellen
    assert z["trend_beide"].values.sum() <= 2


def test_zu_kurze_reihe_ist_nicht_bestimmbar_nan_und_nie_null():
    w, monate, b, l = _tropen(t=120)
    w[:, 0, 0] = np.nan
    w[:20, 0, 1] = np.nan
    w[:100, 0, 1] = np.nan  # nur 20 gültige Werte
    w[:70, 0, 2] = np.nan  # 50 gültige: nur unkorrigiert
    z = tr.trend_je_zelle(w, monate, b, l).zellen
    assert z["status"].values[0, 0] == 0 and z["status"].values[0, 1] == 0 and z["status"].values[0, 2] == 1
    for f in ("sen_steigung", "z_mk", "p_mk", "z_hamed_rao", "z_yue"):
        assert np.isnan(z[f].values[0, 0]) and np.isnan(z[f].values[0, 1])
    assert np.isfinite(z["z_mk"].values[0, 2]) and np.isnan(z["z_hamed_rao"].values[0, 2])
    assert not z["trend_beide"].values[0, :3].any()
    # 20 Werte: jeder Kalendermonat höchstens 2-mal, unter der Mindestzahl 3 -> alle fallen weg (gezählt wird,
    # was in den Test eingeht).
    assert z["n_gueltig"].values[0, 0] == 0 and z["n_gueltig"].values[0, 1] == 0 and z["n_gueltig"].values[0, 2] == 50


def test_fehlende_monate_zaehlen_nicht_als_beobachtung():
    w, monate, b, l = _tropen(trend_prozent=0.0)
    w2 = w.copy()
    w2[30:40] = np.nan  # ein Block nicht geladener Monate
    z = tr.trend_je_zelle(w2, monate, b, l).zellen
    assert (z["n_gueltig"].values == len(monate) - 10).all()


def test_endtest_gesperrt_und_monatsachse_lueckenlos():
    w, monate, b, l = _tropen(t=12)
    with pytest.raises(EndtestGesperrt):
        tr.trend_je_zelle(w, _monate(12, start=(2022, 6)), b, l)
    with pytest.raises(ValueError):
        tr.trend_je_zelle(w, monate[:6] + monate[7:] + [(2012, 1)], b, l)


def test_pflichtfelder_und_flaechenanteile():
    w, monate, b, l = _tropen(trend_prozent=3.0)
    erg = tr.trend_je_zelle(w, monate, b, l)
    for k in ("evidenzstufe", "methode", "version", "unsicherheit"):
        assert erg.zellen.attrs[k]
    assert erg.zellen.attrs["evidenzstufe"] == "beobachtet"
    assert "n_gueltig" in erg.zellen and "uneinig" in erg.zellen
    assert erg.zusammenfassung["trend_beide_flaechenanteil"] == pytest.approx(1.0)
    assert erg.zusammenfassung["moran"]["reste_zeitpunkte"] > 0


def test_uneinig_ist_kennzeichen_wenn_korrekturen_sich_widersprechen():
    # Starke Autokorrelation ohne Trend: Yue (Prewhitening) meldet mehr als Hamed-Rao; Zellen mit
    # Widerspruch sind „uneinig“ und NIE „trend_beide“.
    ds = kuenstlicher_wuerfel(ny=20, nx=20, jahre=(2010, 2022), seed=3, ar1=0.8, anteil_dunkel=0.0, breite_start=5.0)
    w = ds["allangle_mittel_beobachtet"].values[:150]
    monate = _monate(150)
    z = tr.trend_je_zelle(w, monate, ds["breite"].values, ds["laenge"].values).zellen
    assert z["uneinig"].values.any()
    assert not (z["uneinig"].values & z["trend_beide"].values).any()


def test_schnee_verdacht_regel():
    breite = np.array([60.0, 10.0, -45.0])
    anteil = np.full((3, 2), 0.5)
    v = schnee_verdacht(breite, 1, anteil)
    assert v[0].all() and not v[1].any() and not v[2].any()  # Januar: Nordwinter, Südsommer, Tropen nie
    assert schnee_verdacht(breite, 7, anteil)[2].all()
    assert not schnee_verdacht(breite, 1, np.full((3, 2), 0.95))[0].any()  # >= 90 % beobachtet: kein Verdacht
    assert not schnee_verdacht(breite, 1, np.full((3, 2), np.nan)).any()


def test_trend_nimmt_schnee_verdacht_heraus_und_zaehlt_ihn():
    w, monate, _, l = _tropen()
    b = 60 - 0.125 - np.arange(w.shape[1]) * 0.25
    anteil = np.full(w.shape, 0.99)
    januare = [i for i, (_, m) in enumerate(monate) if m == 1]
    anteil[januare] = 0.6
    erg = tr.trend_je_zelle(w, monate, b, l, anteil)
    assert (erg.zellen["n_schnee_ausgeschlossen"].values == len(januare)).all()
    assert (erg.zellen["n_gueltig"].values == len(monate) - len(januare)).all()
    ohne = tr.trend_je_zelle(w, monate, b, l, anteil, tr.TrendEinstellungen(schnee_ausschliessen=False))
    assert (ohne.zellen["n_gueltig"].values == len(monate)).all()


def test_lies_reihe_nicht_fertige_monate_und_nicht_geladene_zellen_sind_nan():
    ds = kuenstlicher_wuerfel(ny=4, nx=6, jahre=(2016, 2018), nicht_fertig=((2017, 3),))
    fertig = ds["monat_fertig"].values.copy()
    fertig[5] = 4  # 2016-06: nur Region
    ds["monat_fertig"] = ("zeit", fertig)
    maske = np.zeros((4, 6), bool)
    maske[:, :3] = True
    r = tr.lies_reihe(ds, "allangle", (2016, 1), (2018, 12), region_maske=maske)
    i_fehlt = r["monate"].index((2017, 3))
    assert r["zustand"][i_fehlt] == "fehlt" and np.isnan(r["werte"][i_fehlt]).all()
    assert r["zustand"][5] == "nur Region"
    assert np.isnan(r["werte"][5][:, 3:]).all() and np.isfinite(r["werte"][5][:, :3]).any()
    r2 = tr.lies_reihe(ds, "allangle", (2016, 1), (2018, 12))
    assert r2["zustand"][5] == "fehlt"  # ohne Region-Maske: Zustand 4 wird nicht gelesen
    with pytest.raises(EndtestGesperrt):
        tr.lies_reihe(ds, "allangle", (2016, 1), (2023, 1))
    assert lesen.fertige_monate(ds)  # Würfel unverändert lesbar
