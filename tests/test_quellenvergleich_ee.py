"""Tests für aleph/quellenvergleich/ee_nachtlicht.py (ohne Earth Engine, künstliche Daten)."""

import numpy as np
import pytest

from aleph.layers import vnp46a3
from aleph.quellenvergleich import ee_nachtlicht as m

H, W = vnp46a3.GITTER_BREITE, vnp46a3.GITTER_LAENGE


def test_raster_passt_zum_wuerfel():
    t = m.raster_transform()
    assert t == [0.25, 0.0, -180.0, 0.0, -0.25, 90.0]
    breite, laenge = vnp46a3._gitter_koordinaten()
    # Zellmitte der Zelle (z, s) liegt in genau dieser Zelle
    for z, s in [(0, 0), (150, 772), (719, 1439)]:
        assert m.zelle_von(float(breite[z]), float(laenge[s])) == (z, s)


def test_stichproben_zellen():
    assert m.zelle_von(52.52, 13.40) == (149, 773)  # Berlin: 52,50-52,75° N, 13,25-13,50° O
    assert m.zelle_von(25.0, 25.0) == (260, 820)  # genau auf der Kante: Zelle südlich/östlich


def test_zeitraum_2023_bis_2025_gesperrt():
    with pytest.raises(m.ZeitraumGesperrt):
        m.pruefe_zeitraum(2023, 1)
    with pytest.raises(m.ZeitraumGesperrt):
        m.lies_wuerfel(2024, 1)
    m.pruefe_zeitraum(2022, 12)


def _kuenstlich(seed=0):
    rng = np.random.default_rng(seed)
    ref = np.exp(rng.normal(0, 1.5, (H, W))).astype("float64")
    ref[ref < 0.3] = 0.0  # dunkle Zellen mit Null, wie nach der Rauschschwelle
    maske = np.zeros((H, W), bool)
    maske[100:400, 700:1400] = True
    for ort, (b, l) in m.STICHPROBEN.items():
        z, s = m.zelle_von(b, l)
        maske[z, s] = True
        ref[z, s] = 0.0 if ort == "Sahara" else 20.0
    hat = np.ones((H, W), bool)
    return ref, hat, maske


def test_identische_werte_erfuellen_alles():
    ref, hat, maske = _kuenstlich()
    e = m.vergleiche(ref, hat, ref.copy(), hat.copy(), maske)
    assert e["urteil"] == "erfüllt"
    assert all(e["erfuellt"].values())
    assert e["r_log_mittel_und_hell"] == pytest.approx(1.0)
    assert e["klassen"]["hell"]["median_q"] == pytest.approx(1.0)


def test_versatz_20_prozent_verletzt_nur_k2():
    ref, hat, maske = _kuenstlich()
    e = m.vergleiche(ref, hat, ref * 1.2, hat.copy(), maske)
    assert e["erfuellt"]["K1"] and e["erfuellt"]["K3"] and e["erfuellt"]["K5"] and e["erfuellt"]["K6"]
    assert not e["erfuellt"]["K2"]
    assert e["urteil"] == "teilweise"


def test_faktor2_in_zehn_prozent_der_zellen_verletzt_k3():
    ref, hat, maske = _kuenstlich()
    rng = np.random.default_rng(1)
    kand = ref.copy()
    stoerung = rng.random((H, W)) < 0.10
    for ort in m.STICHPROBEN:
        stoerung[m.zelle_von(*m.STICHPROBEN[ort])] = False
    kand[stoerung] *= 2.5
    e = m.vergleiche(ref, hat, kand, hat.copy(), maske)
    assert not e["erfuellt"]["K3"]
    assert e["klassen"]["hell"]["anteil_faktor2"] == pytest.approx(0.10, abs=0.01)


def test_falsches_licht_im_dunkeln_verletzt_k4():
    ref, hat, maske = _kuenstlich()
    kand = ref.copy()
    dunkel = ref < 0.5
    kand[dunkel] = 1.5
    e = m.vergleiche(ref, hat, kand, hat.copy(), maske)
    assert not e["erfuellt"]["K4"]
    assert e["klassen"]["dunkel"]["anteil_falsches_licht"] == pytest.approx(1.0)


def test_luecken_an_anderen_stellen_verletzen_k5():
    ref, hat, maske = _kuenstlich()
    kand_hat = hat.copy()
    kand_hat[100:130, 700:1400] = False  # 10 % der Region ohne Daten beim Kandidaten
    kand = np.where(kand_hat, ref, np.nan)
    e = m.vergleiche(ref, hat, kand, kand_hat, maske)
    assert not e["erfuellt"]["K5"]
    assert e["luecken"]["wuerfel_ja_kandidat_nein"] == pytest.approx(0.1, abs=0.005)


def test_stichprobe_berlin_ausserhalb_band_verletzt_k6():
    ref, hat, maske = _kuenstlich()
    kand = ref.copy()
    kand[m.zelle_von(*m.STICHPROBEN["Berlin"])] = 40.0  # q = 2
    e = m.vergleiche(ref, hat, kand, hat.copy(), maske)
    assert not e["stichproben"]["Berlin"]["erfuellt"]
    assert not e["erfuellt"]["K6"]
    assert e["urteil"] == "nicht erfüllt"


def test_zellen_ausserhalb_der_region_zaehlen_nicht():
    ref, hat, maske = _kuenstlich()
    kand = ref.copy()
    kand[~maske] = 1000.0
    e = m.vergleiche(ref, hat, kand, hat.copy(), maske)
    assert e["urteil"] == "erfüllt"


def test_kriterien_sind_die_festgelegten():
    # Schutz gegen nachträgliches Anpassen (Bericht, Schritt 2, 16:24 UTC)
    assert m.KRITERIEN == {
        "K1_r_log_min": 0.95,
        "K2a_median_q": (0.90, 1.10),
        "K2b_median_abw_max": 0.15,
        "K3_anteil_faktor2_max": 0.05,
        "K4_dunkel_falsches_licht_ab": 1.0,
        "K4_anteil_max": 0.02,
        "K5_gleich_min": 0.95,
        "K5_fehlt_im_kandidat_max": 0.05,
        "K6_stadt_q": (0.67, 1.5),
        "K6_sahara_max": 0.5,
    }
    assert (m.KLASSE_DUNKEL_BIS, m.KLASSE_MITTEL_BIS, m.LOG_ZUSATZ) == (0.5, 5.0, 0.1)


def test_zwischenstand_wird_wiederverwendet(tmp_path, monkeypatch):
    aufrufe = []

    def attrappe(ee, bild, z0, s0, h, w, versuche=4):
        aufrufe.append((z0, s0))
        return np.full((h, w), float(z0 + s0), "float32"), np.ones((h, w), "float32"), 100, 1.0, 0

    monkeypatch.setattr(m, "lade_block", attrappe)
    kacheln = {"h19v03", "h20v03"}
    w1, a1, mess1 = m.lade_region(None, None, kacheln, parallel=2, melde=lambda _: None, zwischen=tmp_path)
    assert sorted(aufrufe) == [(120, 760), (120, 800)] and mess1.anfragen == 2
    (tmp_path / "120_0800.npz").unlink()  # Block „verloren“: nur dieser wird neu gerechnet
    aufrufe.clear()
    w2, a2, mess2 = m.lade_region(None, None, kacheln, parallel=2, melde=lambda _: None, zwischen=tmp_path)
    assert aufrufe == [(120, 800)] and mess2.wiederverwendet == 1 and mess2.anfragen == 1
    np.testing.assert_array_equal(w1, w2)
    assert np.isnan(w2[0, 0]) and w2[120, 760] == 880.0


def test_fehlgeschlagene_bloecke_ergeben_kein_ergebnis(tmp_path, monkeypatch):
    def scheitert(ee, bild, z0, s0, h, w, versuche=4):
        raise RuntimeError(f"Block Zeile {z0} Spalte {s0}: HttpError nach 4 Versuchen")

    monkeypatch.setattr(m, "lade_block", scheitert)
    _, _, mess = m.lade_region(None, None, {"h19v03"}, melde=lambda _: None, zwischen=tmp_path)
    assert mess.fehler and mess.anfragen == 0


def test_auswahleffekt_bei_reinem_rauschen_und_gegenmittel():
    # Würfel und Kandidat = derselbe wahre Wert mit gleich großem, unabhängigem Rauschen,
    # ohne jeden Versatz. Klassen nach dem Würfelwert zeigen trotzdem „hell dunkler“
    # (Regression zur Mitte); Klassen nach dem geometrischen Mittel nicht.
    rng = np.random.default_rng(3)
    wahr = np.exp(rng.normal(0.5, 1.5, (H, W)))
    ref = wahr * np.exp(rng.normal(0, 0.3, (H, W)))
    kand = wahr * np.exp(rng.normal(0, 0.3, (H, W)))
    hat = np.ones((H, W), bool)
    maske = np.ones((H, W), bool)
    nach_ref = m.vergleiche(ref, hat, kand, hat, maske)["klassen"]
    nach_beiden = m.klassen_nach_beiden(ref, hat, kand, hat, maske)
    assert nach_ref["hell"]["median_q"] < 0.95  # Artefakt der Einteilung
    assert nach_beiden["hell"]["median_q"] == pytest.approx(1.0, abs=0.02)
    assert nach_beiden["mittel"]["median_q"] == pytest.approx(1.0, abs=0.02)


def test_negative_kandidatenwerte_zaehlen_als_grosse_abweichung():
    ref, hat, maske = _kuenstlich()
    kand = ref.copy()
    hell = ref >= 5
    kand[hell] = -1.0
    e = m.vergleiche(ref, hat, kand, hat.copy(), maske)
    assert e["klassen"]["hell"]["anteil_faktor2"] == pytest.approx(1.0)
    assert np.isfinite(e["r_log_mittel_und_hell"])


def test_nan_in_stichprobenzelle_ist_nicht_erfuellt():
    ref, hat, maske = _kuenstlich()
    kand = ref.copy()
    kand[m.zelle_von(*m.STICHPROBEN["Kairo"])] = np.nan
    e = m.vergleiche(ref, hat, kand, hat.copy(), maske)
    assert not e["stichproben"]["Kairo"]["erfuellt"]
    assert not e["erfuellt"]["K6"]


def test_maske_bleibt_auf_region_beschraenkt_wenn_monat_ganz_fertig(monkeypatch):
    import xarray as xr

    region = np.zeros((H, W), bool)
    region[0:40, 0:40] = True
    leer = np.zeros((1, H, W))
    ds = xr.Dataset(
        {v: (("zeit", "breite", "laenge"), leer) for v in (m.WUERFEL_WERT, m.WUERFEL_PIXEL, m.WUERFEL_WERT_MIT_AUFFUELLUNG)}
        | {"nicht_geladen": (("zeit", "breite", "laenge"), np.zeros((1, H, W), bool))}  # Zustand 1
    )
    monkeypatch.setattr(m.vnp46a3, "lies_monate_mit_region", lambda *a, **k: ds)
    monkeypatch.setattr(m, "region_maske", lambda: region)
    assert (m.lies_wuerfel(2018, 10)["maske"] == region).all()


def test_block_bootstrap_liefert_intervall_um_den_wert():
    ref, hat, maske = _kuenstlich()
    kand = ref * 1.05
    b = m.block_bootstrap(ref, hat, kand, hat.copy(), maske, wiederholungen=50)
    assert b["hell_median_q"][0] == pytest.approx(1.05) and b["hell_median_q"][1] == pytest.approx(1.05)
    assert b["bloecke"] > 10


def test_lade_block_wiederholt_mit_wachsenden_pausen_und_meldet(monkeypatch, capsys):
    """Netzwerkregel: Zeitüberschreitung → neuer Versuch nach 5, 10 s; jede Wiederholung gemeldet."""
    import io as bytes_io
    from types import SimpleNamespace

    puffer = bytes_io.BytesIO()
    feld = np.zeros((2, 2), dtype=[("wert", "f4"), ("anteil", "f4")])
    np.save(puffer, feld)
    antworten = iter([TimeoutError("x"), TimeoutError("x"), puffer.getvalue()])

    def compute(anfrage):
        a = next(antworten)
        if isinstance(a, Exception):
            raise a
        return a

    ee = SimpleNamespace(data=SimpleNamespace(computePixels=compute))
    pausen = []
    monkeypatch.setattr(m.time, "sleep", pausen.append)
    wert, anteil, nbytes, sek, wdh = m.lade_block(ee, "bild", 0, 0, 2, 2)
    assert wdh == 2 and wert.shape == (2, 2)
    assert pausen == [m.BLOCK_PAUSE_BASIS_SEKUNDEN, 2 * m.BLOCK_PAUSE_BASIS_SEKUNDEN]
    fehlerausgabe = capsys.readouterr().err
    assert "Versuch 1/4" in fehlerausgabe and "Versuch 2/4" in fehlerausgabe and "TimeoutError" in fehlerausgabe


def test_nach_breite_ordnet_zellen_dem_richtigen_band_zu():
    """Künstlich: eine helle Zelle bei 70° N mit q = 2,5, eine bei 30° N mit q = 1, falsches Licht bei 70° N."""
    ref = np.zeros((H, W), dtype="float32")
    kand = np.zeros((H, W), dtype="float32")
    maske = np.zeros((H, W), dtype=bool)
    z70, s = m.zelle_von(70.1, 100.1)
    z30, _ = m.zelle_von(30.1, 100.1)
    ref[z70, s], kand[z70, s] = 2.0, 5.0
    ref[z30, s], kand[z30, s] = 10.0, 10.0
    ref[z70, s + 1], kand[z70, s + 1] = 0.0, 1.5
    maske[[z70, z30, z70], [s, s, s + 1]] = True
    hat = np.ones((H, W), dtype=bool)
    ergebnis = {tuple(e["band"]): e for e in m.nach_breite(ref, hat, kand, hat, maske)}
    assert ergebnis[(68, 72)]["zellen_ab_0_5"] == 1
    assert ergebnis[(68, 72)]["median_q"] == pytest.approx(2.5)
    assert ergebnis[(68, 72)]["anteil_faktor2"] == 1.0
    assert ergebnis[(68, 72)]["falsches_licht"] == 1
    assert ergebnis[(20, 40)]["median_q"] == pytest.approx(1.0)
    assert ergebnis[(20, 40)]["anteil_faktor2"] == 0.0
    assert sum(e["zellen_ab_0_5"] for e in ergebnis.values()) == 2


def test_breitenbaender_ueberlappen_nicht_und_sind_lueckenlos():
    b = m.BREITENBAENDER
    assert all(unten < oben for unten, oben in b)
    assert all(b[i][0] == b[i + 1][1] for i in range(len(b) - 1))


def test_nach_breite_beachtet_maske_und_zaehlt_luecken():
    ref = np.zeros((H, W), dtype="float32")
    kand = np.zeros((H, W), dtype="float32")
    maske = np.zeros((H, W), dtype=bool)
    z, s = m.zelle_von(30.1, 100.1)
    ref[z, s], kand[z, s] = 10.0, 30.0  # außerhalb der Maske: darf nicht zählen
    ref[z, s + 1], kand[z, s + 1] = 0.2, 0.8  # dunkel, Kandidat < 1: kein falsches Licht
    maske[z, s + 1 : s + 4] = True
    ref_hat = np.ones((H, W), dtype=bool)
    kand_hat = np.ones((H, W), dtype=bool)
    kand_hat[z, s + 2] = False  # nur Würfel
    ref_hat[z, s + 3] = False  # nur Kandidat
    e = {tuple(x["band"]): x for x in m.nach_breite(ref, ref_hat, kand, kand_hat, maske)}[(20, 40)]
    assert e["zellen_ab_0_5"] == 0
    assert e["falsches_licht"] == 0
    assert e["nur_wuerfel"] == 1 and e["nur_kandidat"] == 1


def test_nach_breite_leeres_band_liefert_nan_statt_fehler():
    leer = np.zeros((H, W), dtype="float32")
    hat = np.ones((H, W), dtype=bool)
    e = m.nach_breite(leer, hat, leer, hat, np.zeros((H, W), dtype=bool))[0]
    assert e["zellen_ab_0_5"] == 0 and np.isnan(e["median_q"])
