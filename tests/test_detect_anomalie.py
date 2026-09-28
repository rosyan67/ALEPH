"""Prüft die Anomalieerkennung (aleph/detect/anomalie.py) mit künstlichen Würfeln.

Kein echter Würfel, keine echten Daten (Datenleck-Hinweis im LOG: 2023-2025 sind noch nicht
für Auswertungen freigegeben). Jeder Test baut sich einen eigenen Würfel mit bekannter
Wahrheit: Was eingebaut ist, muss gefunden werden; was nicht eingebaut ist, darf nicht
auftauchen.
"""

import numpy as np
import pytest
import xarray as xr

from aleph.detect import anomalie as a
from aleph.detect import wuerfel as w
from aleph.detect.synthetisch import Ereignis, kuenstlicher_wuerfel

FELD = "allangle"


def cube(**kw):
    """Künstlicher Würfel mit hellen, ähnlich hellen Zellen (Median 20 nW). Auffindbarkeits-Tests brauchen das:
    Sehr dunkle Zellen sind wegen der absoluten Mindest-Streuung (0,5 nW) bewusst schwer zu bewerten,
    siehe test_dunkle_zellen_haben_eine_erkennungsgrenze. Rausch-Tests geben die Helligkeit selbst vor."""
    return kuenstlicher_wuerfel(**{"helligkeit_median": 20.0, "helligkeit_sigma": 0.4, **kw})


def block(ereignis: Ereignis) -> tuple[slice, slice]:
    return slice(*ereignis.zeilen), slice(*ereignis.spalten)


def erkenne(ds, monat, freigabe=False, **kw):
    """Künstliche Daten: der Endtest-Zeitraum ist hier unbedenklich, deshalb bei Bedarf `freigabe=True`."""
    return a.erkenne_monat(ds, monat, FELD, a.Schwellen(**kw) if kw else None, endtest_freigabe=freigabe)


# --- Eingebaute Anomalie wird gefunden -------------------------------------------


@pytest.fixture(scope="module")
def cube_mit_ereignissen():
    rueckgang = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.3)  # Rückgang auf 30 %
    anstieg = Ereignis((2020, 7), (25, 30), (50, 56), faktor=3.0)  # Verdreifachung
    return cube(seed=1, anteil_dunkel=0.0, ereignisse=(rueckgang, anstieg)), rueckgang, anstieg


def test_eingebaute_anomalien_werden_gefunden_mit_richtung(cube_mit_ereignissen):
    ds, rueckgang, anstieg = cube_mit_ereignissen
    r = erkenne(ds, (2020, 7))
    assert r.status == "bewertet"
    assert len(r.ereignisse) == 2
    nach_richtung = {z.richtung: z for z in r.ereignisse.itertuples()}
    assert set(nach_richtung) == {"Rückgang", "Anstieg"}

    gemeldet = r.zellen["gemeldet"].values
    ereignis_nr = r.zellen["ereignis_nr"].values
    for e, richtung in ((rueckgang, "Rückgang"), (anstieg, "Anstieg")):
        b = block(e)
        nr = nach_richtung[richtung].nr
        # praktisch der ganze eingebaute Block wird dem Ereignis zugeordnet, und nur er
        treffer = (ereignis_nr[b] == nr).mean()
        assert treffer >= 0.9, (richtung, treffer)
        assert (ereignis_nr == nr).sum() == nach_richtung[richtung].n_zellen
        assert nach_richtung[richtung].n_zellen <= (b[0].stop - b[0].start) * (b[1].stop - b[1].start)
    assert gemeldet.sum() == r.ereignisse["n_zellen"].sum()  # nichts außerhalb der beiden Blöcke


def test_ereignis_hat_alle_pflichtangaben(cube_mit_ereignissen):
    ds, rueckgang, _ = cube_mit_ereignissen
    r = erkenne(ds, (2020, 7))
    zeile = r.ereignisse[r.ereignisse["richtung"] == "Rückgang"].iloc[0]
    assert zeile["band"] in ("auffällig", "stark", "extrem")
    assert zeile["datenlage"] in ("gut", "mittel", "dünn")
    assert zeile["evidenzstufe"] == "beobachtet"
    assert zeile["erkennung_version"] == a.ERKENNUNG_VERSION
    assert zeile["feld"] == FELD and zeile["monat"].year == 2020 and zeile["monat"].month == 7
    assert zeile["z_median"] < 0 and zeile["aenderung_relativ_median"] == pytest.approx(-0.7, abs=0.1)
    # Lage: der Block liegt bei Zeilen 10-16, Spalten 20-26 (Breite 60 - 0,125 - 0,25*Zeile)
    assert 60 - 0.125 - 0.25 * 16 <= zeile["breite_mitte"] <= 60 - 0.125 - 0.25 * 10
    assert zeile["n_basis_min"] >= 5


def test_zellkarten_haben_gitterform_und_koordinaten(cube_mit_ereignissen):
    ds, _, _ = cube_mit_ereignissen
    r = erkenne(ds, (2020, 7))
    for name in ("z", "p_nominal", "bh_nominal", "datenlage", "n_basis", "gemeldet", "band", "richtung", "beobachtet_anteil", "aufgefuellt_anteil"):
        assert r.zellen[name].shape == (ds.sizes["breite"], ds.sizes["laenge"]), name
    np.testing.assert_array_equal(r.zellen["breite"].values, ds["breite"].values)
    assert r.zellen["band"].values.max() <= 3 and r.zellen["band"].values[~r.zellen["gemeldet"].values].max() == 0


def test_neues_licht_in_dunkler_zelle_wird_gefunden():
    """Zellen, die vorher dunkel waren (Median nahe 0), bekommen neues Licht: +8 nW in einem Block."""
    e = Ereignis((2021, 3), (5, 11), (10, 16), zusatz=8.0)
    ds = cube(seed=2, anteil_dunkel=1.0, ereignisse=(e,))  # alle Zellen dunkel
    r = erkenne(ds, (2021, 3))
    # In lauter dunklen Zellen fehlt die Grundlage für die gemeinsame Streuung -> ehrlich nicht bewertbar
    assert r.status == "nicht bewertbar" and r.ereignisse.empty
    # Mit einigen hellen Zellen daneben (Streuung schätzbar) wird das neue Licht gefunden.
    ds = cube(seed=2, anteil_dunkel=0.4, ereignisse=(e,))
    r = erkenne(ds, (2021, 3))
    assert r.status == "bewertet"
    anstiege = r.ereignisse[r.ereignisse["richtung"] == "Anstieg"]
    assert len(anstiege) == 1 and anstiege.iloc[0]["n_zellen"] >= 4


def test_dunkle_zellen_haben_eine_erkennungsgrenze():
    """Bekannte Grenze (Modul-Doku): Bei nur 2 nW Grundhelligkeit ist ein Rückgang um 70 % (-1,4 nW) wegen der
    absoluten Mindest-Streuung (0,5 nW) nicht 5 Standardabweichungen groß; bei 20 nW schon."""
    e = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.3)
    schwach = cube(seed=1, anteil_dunkel=0.0, helligkeit_median=2.0, helligkeit_sigma=0.1, ereignisse=(e,))
    hell = cube(seed=1, anteil_dunkel=0.0, helligkeit_median=20.0, helligkeit_sigma=0.1, ereignisse=(e,))
    assert erkenne(schwach, (2020, 7)).ereignisse.empty
    assert len(erkenne(hell, (2020, 7)).ereignisse) == 1


# --- Reine Saisonalität löst nichts aus ------------------------------------------


def test_reine_saisonalitaet_loest_nichts_aus():
    ds = cube(seed=3, ny=60, nx=120, saison_amplitude=0.8, rauschen_relativ=0.02, anteil_dunkel=0.2, helligkeit_median=5.0, helligkeit_sigma=1.1)
    # Kontrolle: Die Saison ist tatsächlich groß gegen das Rauschen (sonst prüfte der Test nichts).
    x = ds[f"{FELD}_mittel"].values
    hell = np.nanmedian(x, axis=0) > 1.0
    monatssprung = np.abs(np.diff(x[:12], axis=0)) / np.nanmedian(x, axis=0)
    assert np.median(monatssprung[:, hell]) > 0.1  # Sprünge von Monat zu Monat > 10 %, Rauschen nur 2 %

    ergebnisse = a.erkenne_zeitraum(ds, FELD, von=(2018, 1), bis=(2025, 12), endtest_freigabe=True)
    assert len(ergebnisse) == 96 and all(r.status == "bewertet" for r in ergebnisse)
    assert not any(r.warnung for r in ergebnisse)  # auch die Monatsdiagnose bleibt still
    assert sum(len(r.ereignisse) for r in ergebnisse) == 0
    assert sum(int(r.zellen["markiert"].values.sum()) for r in ergebnisse) == 0


def test_saison_wird_gegen_denselben_kalendermonat_verglichen_nicht_gegen_den_vormonat():
    ds = cube(seed=3, ny=40, nx=80, saison_amplitude=0.8, rauschen_relativ=0.02, anteil_dunkel=0.0)
    r = erkenne(ds, (2020, 7))
    assert all(m[1] == 7 and m[0] < 2020 for m in r.basis_monate)
    assert len(r.basis_monate) == 7  # 2013 bis 2019


# --- Basislinie: nie der untersuchte Monat, nie spätere Jahre ---------------------


def test_basislinie_enthaelt_nie_den_untersuchten_monat_oder_spaetere_jahre():
    ds = cube(seed=4, ny=40, nx=80)
    for jahr in (2018, 2020, 2022, 2024):
        r = erkenne(ds, (jahr, 7), freigabe=True)  # 2024 liegt im (künstlichen) Endtest-Zeitraum
        assert (jahr, 7) not in r.basis_monate
        assert all(m[0] < jahr and m[1] == 7 for m in r.basis_monate)
        assert len(r.basis_monate) == jahr - 2013


def test_spaetere_jahre_veraendern_das_ergebnis_eines_frueheren_monats_nicht():
    """Riesige Anomalien in 2024/2025 dürfen die Bewertung von 2020-07 nicht beeinflussen (kein Datenleck)."""
    lauter = (
        Ereignis((2024, 7), (0, 40), (0, 80), faktor=50.0),
        Ereignis((2025, 7), (0, 40), (0, 80), faktor=0.0),
    )
    ohne = cube(seed=4, ny=40, nx=80, anteil_dunkel=0.0)
    mit = cube(seed=4, ny=40, nx=80, anteil_dunkel=0.0, ereignisse=lauter)
    r1, r2 = erkenne(ohne, (2020, 7)), erkenne(mit, (2020, 7))
    np.testing.assert_array_equal(r1.zellen["z"].values, r2.zellen["z"].values)
    assert r1.mindest_streuung == r2.mindest_streuung


def test_der_untersuchte_wert_verschiebt_weder_mediane_noch_streuung_der_anderen_zellen():
    """Ein extremer Wert im untersuchten Monat ändert die Bewertung anderer Zellen und die gemeinsame Streuung nicht."""
    e = Ereignis((2020, 7), (10, 16), (20, 26), faktor=100.0)
    ohne = cube(seed=5, ny=40, nx=80, anteil_dunkel=0.0)
    mit = cube(seed=5, ny=40, nx=80, anteil_dunkel=0.0, ereignisse=(e,))
    r1, r2 = erkenne(ohne, (2020, 7)), erkenne(mit, (2020, 7))
    b = block(e)
    maske = np.ones(r1.zellen["z"].shape, bool)
    maske[b] = False
    np.testing.assert_array_equal(r1.zellen["z"].values[maske], r2.zellen["z"].values[maske])
    assert r1.mindest_streuung == r2.mindest_streuung
    assert (np.abs(r2.zellen["z"].values[b]) > 50).all()  # der Block selbst ist natürlich extrem


# --- Dünne Datenlage wird nicht bewertet -----------------------------------------


def test_zu_wenige_fertige_fruehere_jahre_ist_nicht_bewertbar_und_kein_keine_anomalie():
    ds = cube(seed=6, ny=40, nx=80)
    r = erkenne(ds, (2016, 7))  # nur 2013-2015 als frühere Jahre
    assert r.status == "nicht bewertbar"
    assert "NICHT" in r.grund and "keine Anomalie" in r.grund
    assert r.ereignisse.empty and r.n_getestet == 0
    assert (r.zellen["datenlage"].values == 0).all()  # überall „unzureichend"
    assert len(r.basis_monate) == 3


def test_erstes_bewertbares_jahr_ist_das_sechste():
    ds = cube(seed=6, ny=40, nx=80)
    assert erkenne(ds, (2017, 7)).status == "nicht bewertbar"  # 4 frühere Jahre
    assert erkenne(ds, (2018, 7)).status == "bewertet"  # 5 frühere Jahre


def test_nicht_geladene_fruehere_monate_zaehlen_nicht_und_werden_benannt():
    fehlt = ((2013, 7), (2014, 7), (2015, 7))
    ds = cube(seed=6, ny=40, nx=80, nicht_fertig=fehlt)
    r = erkenne(ds, (2020, 7))  # frühere Jahre 2016-2019: nur 4 fertige
    assert r.status == "nicht bewertbar"
    assert r.fehlende_basis_monate == list(fehlt)
    assert "2013-07" in r.grund  # der Grund nennt, dass Monate nicht geladen sind

    ds2 = cube(seed=6, ny=40, nx=80, nicht_fertig=fehlt[:2])
    r2 = erkenne(ds2, (2020, 7))  # 2015-2019 = 5 fertige: gerade noch bewertbar, aber nur „dünn"
    assert r2.status == "bewertet" and len(r2.basis_monate) == 5
    assert r2.fehlende_basis_monate == list(fehlt[:2])
    assert r2.zellen["datenlage"].values.max() == 1  # bei 5 Basisjahren nie besser als „dünn"


def test_halb_geschriebener_basismonat_wird_nicht_als_basis_benutzt():
    ds = cube(seed=6, ny=40, nx=80, halb_geschrieben=((2016, 7),))
    r = erkenne(ds, (2020, 7))
    assert (2016, 7) not in r.basis_monate and len(r.basis_monate) == 6


def test_untersuchter_monat_nicht_geladen_ist_ein_fehler_kein_ergebnis():
    ds = cube(seed=6, ny=40, nx=80, nicht_fertig=((2020, 7),))
    with pytest.raises(w.MonatNichtFertig):
        erkenne(ds, (2020, 7))


def test_zeitraum_weist_nicht_geladene_monate_ausdruecklich_aus():
    ds = cube(seed=6, ny=40, nx=80, nicht_fertig=((2020, 7), (2020, 8)))
    ergebnisse = a.erkenne_zeitraum(ds, FELD, von=(2020, 5), bis=(2020, 10))
    assert [r.monat for r in ergebnisse] == [(2020, m) for m in range(5, 11)]  # keine Lücke in der Liste
    status = {r.monat[1]: r.status for r in ergebnisse}
    assert status == {5: "bewertet", 6: "bewertet", 7: "nicht geladen", 8: "nicht geladen", 9: "bewertet", 10: "bewertet"}
    fehlt = [r for r in ergebnisse if r.status == "nicht geladen"]
    assert all(r.ereignisse.empty and "NICHT „keine Daten“" in r.grund for r in fehlt)
    assert all((r.zellen["datenlage"].values == 0).all() for r in fehlt)


def test_aufgefuellte_pixel_zaehlen_nie_als_beobachtet():
    """Ein starker Rückgang in Zellen, die überwiegend aus historischen Daten aufgefüllt sind, wird nicht bewertet."""
    lauter_aufgefuellt = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.1, aufgefuellt_anteil=0.6)
    genug_beobachtet = Ereignis((2020, 7), (25, 31), (50, 56), faktor=0.1, aufgefuellt_anteil=0.3)
    ds = cube(seed=7, anteil_dunkel=0.0, ereignisse=(lauter_aufgefuellt, genug_beobachtet))
    r = erkenne(ds, (2020, 7))
    b1, b2 = block(lauter_aufgefuellt), block(genug_beobachtet)
    assert (r.zellen["datenlage"].values[b1] == 0).all()  # „Datenlage unzureichend" trotz 90 % Rückgang
    assert np.isnan(r.zellen["z"].values[b1]).all() and not r.zellen["gemeldet"].values[b1].any()
    assert (r.zellen["datenlage"].values[b2] >= 1).all()
    assert r.zellen["gemeldet"].values[b2].mean() >= 0.9
    assert len(r.ereignisse) == 1 and r.ereignisse.iloc[0]["richtung"] == "Rückgang"


def test_grenze_50_prozent_beobachtet_genau():
    """1801 aufgefüllte Pixel von 3600 (49,97 % beobachtet) sind unzureichend, 1799 (50,03 %) gerade noch bewertbar."""
    knapp_zu_wenig = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.1, aufgefuellt_anteil=1801 / 3600)
    knapp_genug = Ereignis((2020, 7), (25, 31), (50, 56), faktor=0.1, aufgefuellt_anteil=1799 / 3600)
    ds = cube(seed=7, anteil_dunkel=0.0, ereignisse=(knapp_zu_wenig, knapp_genug))
    r = erkenne(ds, (2020, 7))
    assert (r.zellen["datenlage"].values[block(knapp_zu_wenig)] == 0).all()
    assert (r.zellen["datenlage"].values[block(knapp_genug)] == 1).all()  # „dünn"


def test_vollstaendig_aufgefuellte_zellen_haben_keine_beobachtung():
    voll = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.1, aufgefuellt_anteil=1.0)
    ds = cube(seed=7, anteil_dunkel=0.0, ereignisse=(voll,))
    r = erkenne(ds, (2020, 7))
    assert (r.zellen["beobachtet_anteil"].values[block(voll)] == 0).all()
    assert (r.zellen["datenlage"].values[block(voll)] == 0).all() and r.ereignisse.empty


def test_aufgefuellte_pixel_im_basisjahr_nehmen_dieses_jahr_aus_der_basislinie():
    """Ist ein Basismonat in einem Block überwiegend aufgefüllt, zählt er dort nicht; n_basis sinkt."""
    e = tuple(Ereignis((j, 7), (10, 16), (20, 26), aufgefuellt_anteil=0.9) for j in (2014, 2016))
    ds = cube(seed=7, anteil_dunkel=0.0, aufgefuellt_mittel=0.0, ereignisse=e)
    r = erkenne(ds, (2020, 7))
    n_basis = r.zellen["n_basis"].values
    assert (n_basis[10:16, 20:26] == 5).all()  # frühere Jahre 2013-2019 = 7, minus 2014 und 2016 = 5
    assert (n_basis[0:5, 0:5] == 7).all()  # außerhalb des Blocks unverändert
    # Fallen drei Basisjahre weg (nur noch 4), ist die Zelle nicht mehr bewertbar: „Datenlage unzureichend".
    e3 = tuple(Ereignis((j, 7), (10, 16), (20, 26), aufgefuellt_anteil=0.9) for j in (2014, 2016, 2018))
    ds3 = cube(seed=7, anteil_dunkel=0.0, aufgefuellt_mittel=0.0, ereignisse=e3 + (Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.1),))
    r3 = erkenne(ds3, (2020, 7))
    assert (r3.zellen["n_basis"].values[10:16, 20:26] == 4).all()
    assert (r3.zellen["datenlage"].values[10:16, 20:26] == 0).all() and r3.ereignisse.empty


def test_datenlage_stufen_nach_beobachtetem_anteil_und_basisjahren():
    e = tuple(
        Ereignis((2021, 7), (r0, r0 + 5), (0, 5), aufgefuellt_anteil=anteil)
        for r0, anteil in ((0, 0.02), (10, 0.25), (20, 0.45), (30, 0.6))
    )
    ds = cube(seed=8, ny=40, nx=80, anteil_dunkel=0.0, aufgefuellt_mittel=0.0, ereignisse=e)
    r = erkenne(ds, (2021, 7))  # 8 frühere Jahre
    d = r.zellen["datenlage"].values
    assert (d[0:5, 0:5] == 3).all()  # 98 % beobachtet, 8 Basisjahre: gut
    assert (d[10:15, 0:5] == 2).all()  # 75 %: mittel
    assert (d[20:25, 0:5] == 1).all()  # 55 %: dünn
    assert (d[30:35, 0:5] == 0).all()  # 40 %: unzureichend
    r2 = erkenne(ds, (2019, 7))  # 6 frühere Jahre: auch bei bester Beobachtung nur „mittel"
    assert r2.zellen["datenlage"].values.max() == 2


def test_zu_wenige_zellen_fuer_die_gemeinsame_streuung_ist_nicht_bewertbar():
    ds = cube(seed=9, ny=5, nx=10, anteil_dunkel=0.0)  # nur 50 Zellen
    r = erkenne(ds, (2020, 7))
    assert r.status == "nicht bewertbar" and r.n_getestet == 0 and r.ereignisse.empty


# --- Zufallsrauschen: nach der Korrektur fast keine Treffer -----------------------


# Die künstlichen Würfel liegen bei 60° N mit zufälliger Auffüllung; ohne diese Einstellung nähme die
# Schnee-Regel (seit 2026-09-26, eigene Tests) Winterzellen heraus. Hier geht es um etwas anderes.
from aleph.detect.schnee import SchneeRegel  # noqa: E402

OHNE_SCHNEE = SchneeRegel(min_breite_grad=91.0)


def _null_lauf(**kw):
    ds = cube(ny=100, nx=200, jahre=(2013, 2021), seed=5, helligkeit_median=5.0, helligkeit_sigma=1.1, **kw)
    rs = a.erkenne_zeitraum(ds, FELD, von=(2018, 1), bis=(2021, 12), schwellen=a.Schwellen(schnee_regel=OHNE_SCHNEE))
    assert len(rs) == 48 and all(r.status == "bewertet" for r in rs)
    zellen_monate = sum(r.n_getestet for r in rs)
    markiert = sum(int(r.zellen["markiert"].values.sum()) for r in rs)
    ereignisse = sum(len(r.ereignisse) for r in rs)
    bh = sum(r.n_bh_nominal for r in rs)
    roh = sum(int((np.abs(r.zellen["z"].values) >= 3).sum()) for r in rs)
    return zellen_monate, markiert, ereignisse, bh, roh, ds


def test_gleichmaessiges_rauschen_erzeugt_nach_der_korrektur_keine_treffer():
    zellen_monate, markiert, ereignisse, bh, roh, _ = _null_lauf(rauschen_relativ=0.05)
    assert zellen_monate > 0.99 * 48 * 20_000  # praktisch alle Zellen bewertbar (Auffüllung ist zufällig)
    assert roh > 100  # ohne Korrektur (|z| >= 3) gäbe es Hunderte Treffer
    assert (bh, markiert, ereignisse) == (0, 0, 0)


def test_ungleichmaessiges_rauschen_markiert_zellen_aber_meldet_keine_ereignisse_bekannte_grenze():
    """Ehrlicher Test der Grenze: Bei sehr unterschiedlich verrauschten Zellen sind die p-Werte nur nominell.
    Gemessen (Seed 5, 960 000 Zellen-Monate): 155 markierte Zellen (0,016 %), kein Ereignis. Die Kontrolle auf
    „höchstens q falsche Meldungen" gilt hier NICHT; die Mindestgröße hält nur bei unabhängigem Rauschen."""
    zellen_monate, markiert, ereignisse, bh, roh, _ = _null_lauf(rauschen_relativ=0.05, heterogen_sigma=0.5)
    assert ereignisse == 0
    assert 0 < markiert <= 300, markiert  # tatsächlich etwa 155; die Grenze ist real und wird hier sichtbar gehalten
    assert markiert / zellen_monate < 0.0005


def test_schwere_raender_markieren_einzelne_zellen_aber_keine_ereignisse_bekannte_grenze():
    """Student-t-Rauschen (3 Freiheitsgrade, schwere Ränder): gemessen 902 markierte Zellen von 960 000, kein Ereignis."""
    zellen_monate, markiert, ereignisse, bh, roh, _ = _null_lauf(rauschen_relativ=0.05, rauschen_verteilung="t3")
    assert ereignisse == 0
    assert 0 < markiert <= 1500, markiert


def test_ohne_mindestgroesse_wuerden_bei_ungleichmaessigem_rauschen_ereignisse_entstehen():
    """Gegenprobe: Nicht die Korrektur allein, sondern erst die Mindestgröße hält das Ergebnis sauber."""
    ds = cube(ny=100, nx=200, jahre=(2013, 2021), seed=5, helligkeit_median=5.0, helligkeit_sigma=1.1, rauschen_relativ=0.05, heterogen_sigma=1.0)
    ohne = a.erkenne_zeitraum(ds, FELD, von=(2018, 1), bis=(2021, 12), schwellen=a.Schwellen(min_zellen=1))
    mit = a.erkenne_zeitraum(ds, FELD, von=(2018, 1), bis=(2021, 12))
    assert sum(len(r.ereignisse) for r in ohne) > 100
    assert sum(len(r.ereignisse) for r in mit) == 0


def test_reines_rauschen_ergibt_im_gesamtverfahren_keine_meldung():
    """Unter reinem Zufall hat nominell ein kleiner Anteil der Zellen p < 0,05; gemeldet wird im Gesamtverfahren
    (Mindest-Streuung, BH, Mindestwert, Mindestgröße) nichts. Welcher Schritt wie viel beiträgt, zeigen die anderen Tests."""
    ds = cube(ny=100, nx=200, seed=11, rauschen_relativ=0.05, helligkeit_median=5.0, helligkeit_sigma=1.1)
    r = erkenne(ds, (2021, 7))
    p = r.zellen["p_nominal"].values
    anteil_roh = float((p[np.isfinite(p)] < 0.05).mean())
    assert 0.0 < anteil_roh < 0.2  # nominell ein kleiner Anteil (die Mindest-Streuung macht p konservativ)
    assert r.n_bh_nominal == 0 and r.n_zellen_gemeldet == 0


def test_z_mindestwert_wirkt_und_bh_bleibt_dabei_unveraendert():
    e = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.3)
    ds = cube(seed=1, anteil_dunkel=0.0, ereignisse=(e,))
    normal = erkenne(ds, (2020, 7))
    streng = erkenne(ds, (2020, 7), z_min_zelle=50.0, z_stark=60.0, z_extrem=70.0)
    assert normal.n_bh_nominal > 0 and len(normal.ereignisse) == 1
    assert streng.n_bh_nominal == normal.n_bh_nominal  # BH unverändert ...
    assert len(streng.ereignisse) == 0  # ... aber der Mindestwert je Zelle hält alles zurück
    # Alle gemeldeten Zellen sind nominell BH-auffällig und erfüllen den Mindestwert. (Bei dieser Testgröße von
    # 3 200 Zellen bindet BH nie enger als |z| >= 5, siehe test_detect_statistik.py für den Fall mit 1 Million.)
    gemeldet = normal.zellen["gemeldet"].values
    assert normal.zellen["bh_nominal"].values[gemeldet].all()
    assert (np.abs(normal.zellen["z"].values[gemeldet]) >= 5.0).all()


# --- Mindestgröße, Richtung, Umbruch ---------------------------------------------


def _ereignis_mit_zellen(zeilen, spalten, faktor=0.2):
    return Ereignis((2020, 7), zeilen, spalten, faktor=faktor)


def test_mindestgroesse_drei_zellen_werden_nicht_gemeldet_vier_schon():
    ds3 = cube(seed=1, anteil_dunkel=0.0, ereignisse=(_ereignis_mit_zellen((10, 11), (20, 23)),))
    ds4 = cube(seed=1, anteil_dunkel=0.0, ereignisse=(_ereignis_mit_zellen((10, 11), (20, 24)),))
    r3, r4 = erkenne(ds3, (2020, 7)), erkenne(ds4, (2020, 7))
    assert r3.zellen["markiert"].values[10, 20:23].all()  # die Zellen sind einzeln auffällig ...
    assert len(r3.ereignisse) == 0 and r3.n_zellen_gemeldet == 0  # ... aber zu klein für ein Ereignis
    assert len(r4.ereignisse) == 1 and r4.ereignisse.iloc[0]["n_zellen"] == 4


def test_einzelne_extreme_zelle_ist_kein_ereignis():
    ds = cube(seed=1, anteil_dunkel=0.0, ereignisse=(_ereignis_mit_zellen((10, 11), (20, 21), faktor=0.0),))
    r = erkenne(ds, (2020, 7))
    assert r.zellen["markiert"].values[10, 20] and r.ereignisse.empty


def test_gegenlaeufige_nachbarn_werden_nicht_zu_einem_ereignis():
    hoch = _ereignis_mit_zellen((10, 14), (20, 24), faktor=3.0)
    tief = _ereignis_mit_zellen((10, 14), (24, 28), faktor=0.2)  # direkt daneben
    ds = cube(seed=1, anteil_dunkel=0.0, ereignisse=(hoch, tief))
    r = erkenne(ds, (2020, 7))
    assert sorted(r.ereignisse["richtung"]) == ["Anstieg", "Rückgang"]


def test_ereignis_ueber_den_laengengrad_umbruch_ist_eines():
    """Globales Gitter (1440 Spalten, -180 bis 180): Ereignis über die Datumsgrenze hinweg."""
    links = Ereignis((2020, 7), (5, 9), (1438, 1440), faktor=0.2)
    rechts = Ereignis((2020, 7), (5, 9), (0, 2), faktor=0.2)
    ds = cube(seed=12, ny=20, nx=1440, anteil_dunkel=0.0, ereignisse=(links, rechts))
    r = erkenne(ds, (2020, 7))
    assert len(r.ereignisse) == 1
    z = r.ereignisse.iloc[0]
    assert z["n_zellen"] == 16
    assert abs(abs(z["laenge_mitte"]) - 180) < 0.5  # Mitte bei der Datumsgrenze, nicht bei 0°
    # Ausdehnung von 179,625°O (Spalte 1438) über die Datumsgrenze bis 179,625°W (Spalte 1): kein Band über die ganze Erde
    assert z["laenge_min"] == pytest.approx(179.625) and z["laenge_max"] == pytest.approx(-179.625)


# --- Bänder -----------------------------------------------------------------------


def test_baender_nehmen_mit_der_staerke_zu_und_folgen_den_schwellen():
    faktoren = {"schwach": 0.8, "mittel": 0.55, "stark": 0.1}
    ereignisse = tuple(
        Ereignis((2020, 7), (2 + 12 * i, 8 + 12 * i), (10, 16), faktor=f) for i, f in enumerate(faktoren.values())
    )
    ds = cube(seed=13, ny=40, nx=40, anteil_dunkel=0.0, rauschen_relativ=0.02, ereignisse=ereignisse)
    r = erkenne(ds, (2020, 7))
    tabelle = r.ereignisse.sort_values("breite_mitte", ascending=False)
    rang = {"auffällig": 1, "stark": 2, "extrem": 3}
    baender = [rang[b] for b in tabelle["band"]]
    z_betrag = [abs(z) for z in tabelle["z_median"]]
    assert len(tabelle) >= 2
    assert baender == sorted(baender) and z_betrag == sorted(z_betrag)  # je stärker der Rückgang, desto höher das Band
    assert tabelle.iloc[-1]["band"] == "extrem"
    # Andere Schwellen verschieben die Bänder (Schwellen sind wirklich die einzige Quelle).
    hoch = erkenne(ds, (2020, 7), z_stark=1000.0, z_extrem=2000.0)
    assert set(hoch.ereignisse["band"]) == {"auffällig"}


def test_zellband_und_ereignisband_stimmen_mit_den_z_werten_ueberein():
    e = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.05)
    ds = cube(seed=13, anteil_dunkel=0.0, rauschen_relativ=0.02, ereignisse=(e,))
    r = erkenne(ds, (2020, 7))
    z = np.abs(r.zellen["z"].values)
    band = r.zellen["band"].values
    gemeldet = r.zellen["gemeldet"].values
    assert (band[gemeldet & (z >= 12)] == 3).all()
    assert (band[gemeldet & (z >= 8) & (z < 12)] == 2).all()
    assert (band[gemeldet & (z < 8)] == 1).all()


# --- Mindestdauer -------------------------------------------------------------------


def test_mindestdauer_verlangt_aufeinanderfolgende_monate_gleicher_richtung():
    dauer3 = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.2, dauer_monate=3)  # Juli, August, September
    einmalig = Ereignis((2020, 8), (25, 31), (50, 56), faktor=0.2)  # nur August
    ds = cube(seed=14, anteil_dunkel=0.0, ereignisse=(dauer3, einmalig))

    def ereignisse_je_monat(dauer):
        rs = a.erkenne_zeitraum(ds, FELD, von=(2020, 6), bis=(2020, 10), schwellen=a.Schwellen(min_dauer_monate=dauer))
        return {r.monat: len(r.ereignisse) for r in rs}

    assert ereignisse_je_monat(1) == {(2020, 6): 0, (2020, 7): 1, (2020, 8): 2, (2020, 9): 1, (2020, 10): 0}
    assert ereignisse_je_monat(2) == {(2020, 6): 0, (2020, 7): 0, (2020, 8): 1, (2020, 9): 1, (2020, 10): 0}
    assert ereignisse_je_monat(3) == {(2020, 6): 0, (2020, 7): 0, (2020, 8): 0, (2020, 9): 1, (2020, 10): 0}


def test_nicht_geladener_monat_unterbricht_die_dauer_kette():
    dauer3 = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.2, dauer_monate=3)
    ds = cube(seed=14, anteil_dunkel=0.0, ereignisse=(dauer3,), nicht_fertig=((2020, 8),))
    rs = a.erkenne_zeitraum(ds, FELD, von=(2020, 6), bis=(2020, 10), schwellen=a.Schwellen(min_dauer_monate=2))
    assert [(r.monat[1], r.status) for r in rs] == [(6, "bewertet"), (7, "bewertet"), (8, "nicht geladen"), (9, "bewertet"), (10, "bewertet")]
    assert sum(len(r.ereignisse) for r in rs) == 0  # Juli und September sind nicht aufeinanderfolgend


def test_erkenne_zeitraum_gleicht_erkenne_monat_bei_dauer_eins(cube_mit_ereignissen):
    ds, _, _ = cube_mit_ereignissen
    einzel = erkenne(ds, (2020, 7))
    zeitraum = a.erkenne_zeitraum(ds, FELD, von=(2020, 7), bis=(2020, 7))[0]
    xr.testing.assert_equal(einzel.zellen, zeitraum.zellen)
    assert einzel.ereignisse.equals(zeitraum.ereignisse)


# --- Eingaben, Pfade, Schwellen -----------------------------------------------------


def test_erkennung_vom_pfad_gleicht_der_vom_dataset(cube_mit_ereignissen, tmp_path):
    ds, _, _ = cube_mit_ereignissen
    pfad = tmp_path / "kuenstlich.zarr"
    ds.to_zarr(pfad)
    r1, r2 = erkenne(ds, (2020, 7)), erkenne(pfad, (2020, 7))
    xr.testing.assert_equal(r1.zellen, r2.zellen)
    assert r1.ereignisse.equals(r2.ereignisse)


@pytest.mark.parametrize(
    "kw",
    [
        {"min_beobachtet_anteil": 0.0},
        {"min_beobachtet_anteil": 0.8, "datenlage_mittel_anteil": 0.7},
        {"min_basisjahre": 1},
        {"z_min_zelle": 9.0, "z_stark": 8.0},
        {"q_bh": 1.5},
        {"min_zellen": 0},
        {"min_dauer_monate": 0},
    ],
)
def test_unsinnige_schwellen_werden_abgelehnt(kw):
    with pytest.raises(ValueError):
        a.Schwellen(**kw)


def test_ereignistabelle_ist_bei_keinem_ereignis_leer_mit_allen_spalten():
    ds = cube(seed=15, ny=40, nx=80)
    r = erkenne(ds, (2020, 7))
    assert list(r.ereignisse.columns) == a.SPALTEN_EREIGNISSE and r.ereignisse.empty
    assert r.status == "bewertet"  # bewertet UND nichts gefunden: etwas anderes als „nicht bewertbar"


# --- Endtest-Sperre (ARCHITECTURE.md 9a) ------------------------------------------


def test_endtest_monate_sind_ohne_freigabe_gesperrt():
    ds = cube(seed=16, ny=40, nx=80)
    with pytest.raises(a.EndtestGesperrt, match="Endtest"):
        a.erkenne_monat(ds, (2023, 1), FELD)
    with pytest.raises(a.EndtestGesperrt):
        a.erkenne_monat(ds, (2025, 12), FELD)
    assert a.erkenne_monat(ds, (2022, 12), FELD).status == "bewertet"  # der Monat davor ist frei
    with pytest.warns(a.EndtestFreigabeHinweis, match="im LOG vermerken"):  # jede Freigabe wird sichtbar gemacht
        assert a.erkenne_monat(ds, (2023, 1), FELD, endtest_freigabe=True).status == "bewertet"


def test_freigabe_ausserhalb_des_endtests_loest_keine_warnung_aus(recwarn):
    ds = cube(seed=16, ny=40, nx=80)
    a.erkenne_monat(ds, (2022, 12), FELD, endtest_freigabe=True)
    assert not [w_ for w_ in recwarn if issubclass(w_.category, a.EndtestFreigabeHinweis)]


def test_zeitraum_ohne_ende_wird_abgelehnt_und_nennt_den_grund():
    """Ein Zeitraum ohne `bis` reicht bis 2025 und würde den Endtest verbrauchen."""
    ds = cube(seed=16, ny=40, nx=80)
    with pytest.raises(a.EndtestGesperrt, match="2023-01"):
        a.erkenne_zeitraum(ds, FELD, von=(2018, 1))
    with pytest.raises(a.EndtestGesperrt):
        a.erkenne_zeitraum(ds, FELD)
    frei = a.erkenne_zeitraum(ds, FELD, von=(2021, 11), bis=(2022, 12))
    assert len(frei) == 14 and all(r.monat < a.ENDTEST_AB for r in frei)
    assert len(a.erkenne_zeitraum(ds, FELD, von=(2022, 12), bis=(2023, 2), endtest_freigabe=True)) == 3


def test_sperre_greift_vor_dem_lesen():
    """Auch ein nicht geladener oder unbewertbarer Endtest-Monat wird gesperrt, bevor irgendetwas gelesen wird."""
    ds = cube(seed=16, ny=40, nx=80, nicht_fertig=((2024, 5),))
    with pytest.raises(a.EndtestGesperrt):
        a.erkenne_monat(ds, (2024, 5), FELD)


# --- Monatsdiagnose: globale Verschiebung ----------------------------------------


def test_lokale_ereignisse_loesen_die_diagnose_nicht_aus(cube_mit_ereignissen):
    ds, _, _ = cube_mit_ereignissen
    r = erkenne(ds, (2020, 7))
    assert r.diagnose["verdaechtig"] is False and r.warnung == ""
    assert abs(r.diagnose["median_z"]) < 0.5 and r.diagnose["anteil_markiert"] < 0.05


def test_verschiebung_des_ganzen_monats_wird_als_verdacht_gekennzeichnet():
    """Das ganze Gitter um 30 % heller (Sensor, Aufbereitung): viele Meldungen, aber die Diagnose warnt."""
    e = Ereignis((2020, 7), (0, 40), (0, 80), faktor=1.3)
    ds = cube(seed=1, anteil_dunkel=0.0, ereignisse=(e,))
    r = erkenne(ds, (2020, 7))
    assert r.diagnose["verdaechtig"] is True and r.diagnose["median_z"] > 2  # gemessen etwa +4,6
    assert "Verschiebung" in r.warnung and "Ursache ist nicht geklärt" in r.warnung  # keine behauptete Ursache
    assert r.n_zellen_gemeldet > 0.2 * r.n_getestet  # ohne Diagnose sähe das wie viele echte Ereignisse aus
    # Der Vormonat ist unauffällig.
    assert erkenne(ds, (2020, 6)).warnung == ""


def test_langsamer_trend_erzeugt_hier_keine_ereignisse_aber_die_diagnose_schlaegt_an():
    """Trend von 8 % je Jahr im ganzen Gitter: gemessen 0 Ereignisse, Median-z etwa +1,5 (Diagnose)."""
    ds = cube(seed=1, ny=40, nx=80, anteil_dunkel=0.0, trend_pro_jahr=0.08)
    r = erkenne(ds, (2021, 7))
    assert r.diagnose["median_z"] > 0.5 and r.diagnose["verdaechtig"] is True
    assert r.status == "bewertet" and r.ereignisse.empty  # gemessen: keine Ereignisse, aber verschobenes z


def test_raeumlich_zusammenhaengende_stoerung_wird_als_echtes_ereignis_gemeldet_bekannte_grenze():
    """Eine 8 x 8 Zellen große Störung (Wolken, Schnee, Sensor) ist von einem echten Rückgang nicht zu unterscheiden.
    Die Mindestgröße schützt nur vor unabhängigem Rauschen (Modul-Doku)."""
    wolke = Ereignis((2020, 7), (10, 18), (20, 28), faktor=0.7)
    ds = cube(seed=1, ny=40, nx=80, anteil_dunkel=0.0, rauschen_relativ=0.02, ereignisse=(wolke,))
    r = erkenne(ds, (2020, 7))
    assert len(r.ereignisse) == 1 and r.ereignisse.iloc[0]["richtung"] == "Rückgang"
    assert r.warnung == ""  # lokal, also keine Monatswarnung


# --- Rückgang schwerer erkennbar als Anstieg (relative Streuung) -------------------


def test_bei_grossem_rauschen_ist_ein_totalausfall_nicht_erkennbar_ein_anstieg_schon():
    """Ist die typische Schwankung 25 %, erreicht ein Totalausfall (-100 %) höchstens |z| = 4 < 5,
    ein Anstieg auf das Fünffache aber |z| = 16 (Modul-Doku: Rückgänge sind auf -100 % begrenzt)."""
    aus = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.0)
    auf = Ereignis((2020, 7), (25, 31), (50, 56), faktor=5.0)
    ds = cube(seed=17, ny=40, nx=80, anteil_dunkel=0.0, rauschen_relativ=0.25, ereignisse=(aus, auf))
    r = erkenne(ds, (2020, 7))
    richtungen = set(r.ereignisse["richtung"])
    assert "Anstieg" in richtungen and "Rückgang" not in richtungen
    assert np.nanmax(np.abs(r.zellen["z"].values[block(aus)])) < 5.0  # auch die beste Zelle des Blocks reicht nicht


# --- Datenlage: Grenzen genau, Randzellen, Rückfall der Streuung -----------------


def test_grenzen_der_datenlage_stufen_genau():
    """Anteil beobachtet: 0,5 -> dünn, 0,7 -> mittel, 0,9 -> gut (jeweils schon bei gleich); ein Pixel mehr aufgefüllt = eine Stufe tiefer."""
    faelle = {  # aufgefüllte Pixel von 3600 -> erwartete Stufe (8 Basisjahre in 2021)
        1800: 1, 1801: 0,  # 50,0 % gerade noch dünn, 49,97 % unzureichend
        1080: 2, 1081: 1,  # 70,0 % mittel, 69,97 % dünn
        360: 3, 361: 2,  # 90,0 % gut, 89,97 % mittel
    }
    ereignisse = tuple(
        Ereignis((2021, 7), (5 * i, 5 * i + 5), (0, 5), aufgefuellt_anteil=k / 3600) for i, k in enumerate(faelle)
    )
    ds = cube(seed=8, ny=40, nx=80, anteil_dunkel=0.0, aufgefuellt_mittel=0.0, ereignisse=ereignisse)
    d = erkenne(ds, (2021, 7)).zellen["datenlage"].values
    for i, (k, stufe) in enumerate(faelle.items()):
        assert (d[5 * i : 5 * i + 5, 0:5] == stufe).all(), (k, stufe, d[5 * i, 0])


def test_randzellen_mit_weniger_als_3600_gueltigen_pixeln():
    """Gültige Pixel < 3600 (Küste, Kachelrand): 2500 gültig ohne Auffüllung = 69 % beobachtet (dünn), 1700 = 47 % (unzureichend)."""
    mittel = Ereignis((2020, 7), (10, 16), (20, 26), gueltige_pixel=2500)
    wenig = Ereignis((2020, 7), (25, 31), (50, 56), gueltige_pixel=1700)
    ds = cube(seed=9, ny=40, nx=80, anteil_dunkel=0.0, aufgefuellt_mittel=0.0, ereignisse=(mittel, wenig))
    d = erkenne(ds, (2020, 7)).zellen["datenlage"].values
    assert (d[block(mittel)] == 1).all() and (d[block(wenig)] == 0).all()


def test_rueckfall_der_gemeinsamen_streuung_bei_kleinen_gruppen():
    """Zellen mit anderer Zahl von Basisjahren als der Rest (hier 5 statt 7) bilden eine Gruppe unter 100 Zellen
    und bekommen dann die gemeinsame Streuung des Gesamtbestands."""
    e = tuple(Ereignis((j, 7), (10, 16), (20, 26), aufgefuellt_anteil=0.9) for j in (2014, 2016))
    ds = cube(seed=7, ny=40, nx=80, anteil_dunkel=0.0, aufgefuellt_mittel=0.0, ereignisse=e)
    info = erkenne(ds, (2020, 7)).mindest_streuung
    assert info[5]["zellen"] == 36 < 100 and info[7]["zellen"] >= 100
    assert info[5]["rho"] == info["gesamt"]["rho"]  # Rückfall auf den Gesamtwert
    assert info["gesamt"]["zellen"] == info[5]["zellen"] + info[7]["zellen"]  # der Gesamtwert umfasst beide Gruppen


# --- Ereignistabelle: Band, Fläche, Basisjahre -----------------------------------


def test_ereignisband_ist_das_band_des_median_z(cube_mit_ereignissen):
    ds, _, _ = cube_mit_ereignissen
    r = erkenne(ds, (2020, 7))
    for zeile in r.ereignisse.itertuples():
        z = np.abs(r.zellen["z"].values[r.zellen["ereignis_nr"].values == zeile.nr])
        erwartet = a.BAND_NAMEN[a._band(float(np.median(z)), r.schwellen)]
        assert zeile.band == erwartet


def test_band_grenzen_genau():
    s = a.Schwellen()
    assert [a._band(z, s) for z in (5.0, 7.99, 8.0, 11.99, 12.0, 40.0)] == [1, 1, 2, 2, 3, 3]


def test_ereignistabelle_nennt_flaeche_und_basisjahre(cube_mit_ereignissen):
    ds, rueckgang, _ = cube_mit_ereignissen
    r = erkenne(ds, (2020, 7))
    zeile = r.ereignisse[r.ereignisse["richtung"] == "Rückgang"].iloc[0]
    assert (zeile["basis_von"], zeile["basis_bis"], zeile["n_fehlende_basismonate"]) == ("2013-07", "2019-07", 0)
    # Fläche = Summe der Zellflächen der Ereigniszellen (Breite 60° nach Norden hin abnehmend)
    breite = ds["breite"].values
    ys = np.nonzero((r.zellen["ereignis_nr"].values == zeile["nr"]).any(axis=1))[0]
    zeilen_je_y = (r.zellen["ereignis_nr"].values == zeile["nr"]).sum(axis=1)[ys]
    erwartet = float((a.zellflaeche_km2(breite[ys]) * zeilen_je_y).sum())
    assert zeile["flaeche_km2"] == pytest.approx(erwartet)
    je_zelle = zeile["flaeche_km2"] / zeile["n_zellen"]
    assert je_zelle == pytest.approx(772.8 * np.cos(np.radians(zeile["breite_mitte"])), rel=0.02)  # etwa 420 km² bei 57°N


def test_zellflaeche_nimmt_mit_der_breite_ab():
    f = a.zellflaeche_km2(np.array([0.0, 60.0, 80.0]))
    assert f[0] == pytest.approx(772.8, rel=0.01)
    assert f[1] / f[0] == pytest.approx(0.5, rel=0.01)  # cos(60°)
    assert f[2] / f[0] == pytest.approx(np.cos(np.radians(80)), rel=0.01)


def test_fehlende_basismonate_stehen_in_der_ereignistabelle():
    e = Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.2)
    ds = cube(seed=1, ny=40, nx=80, anteil_dunkel=0.0, ereignisse=(e,), nicht_fertig=((2013, 7), (2014, 7)))
    r = erkenne(ds, (2020, 7))
    zeile = r.ereignisse.iloc[0]
    assert (zeile["basis_von"], zeile["basis_bis"], zeile["n_fehlende_basismonate"]) == ("2015-07", "2019-07", 2)


# --- Mindestdauer über den Jahreswechsel -------------------------------------------


def test_mindestdauer_kette_ueber_den_jahreswechsel():
    e = Ereignis((2020, 12), (10, 16), (20, 26), faktor=0.2, dauer_monate=3)  # Dezember, Januar, Februar
    ds = cube(seed=14, ny=40, nx=80, anteil_dunkel=0.0, ereignisse=(e,))
    rs = a.erkenne_zeitraum(ds, FELD, von=(2020, 11), bis=(2021, 3),
                            schwellen=a.Schwellen(min_dauer_monate=3, schnee_regel=OHNE_SCHNEE))
    assert {r.monat: len(r.ereignisse) for r in rs} == {
        (2020, 11): 0, (2020, 12): 0, (2021, 1): 0, (2021, 2): 1, (2021, 3): 0,
    }


# --- Monatsdiagnose auf realistischerem (dunkelreichem) Gitter, Spalte, Attribute ---


def test_diagnose_erkennt_verschiebung_auch_bei_vielen_dunklen_zellen():
    """Die Hälfte der Zellen ist dunkel (z nahe 0): die Diagnose rechnet nur über die hellen und schlägt trotzdem an."""
    ganzes_gitter = Ereignis((2020, 7), (0, 40), (0, 80), faktor=1.3)
    ds = cube(seed=1, anteil_dunkel=0.5, ereignisse=(ganzes_gitter,))
    r = erkenne(ds, (2020, 7))
    assert r.diagnose["n_helle_zellen"] < 0.7 * r.n_getestet  # tatsächlich viele dunkle Zellen dabei
    assert r.diagnose["verdaechtig"] is True and r.diagnose["median_z"] > 1.0
    ruhig = erkenne(cube(seed=1, anteil_dunkel=0.5), (2020, 7))
    assert ruhig.diagnose["verdaechtig"] is False


def test_ereignistabelle_traegt_die_monatswarnung_mit():
    """Wird die Tabelle allein weitergegeben (Karte, Export), bleibt der Verdacht sichtbar."""
    ds = cube(seed=1, anteil_dunkel=0.0, ereignisse=(Ereignis((2020, 7), (0, 40), (0, 80), faktor=1.3),))
    r = erkenne(ds, (2020, 7))
    assert len(r.ereignisse) > 0 and r.ereignisse["monat_verdaechtig"].all()
    normal = erkenne(cube(seed=1, anteil_dunkel=0.0, ereignisse=(Ereignis((2020, 7), (10, 16), (20, 26), faktor=0.3),)), (2020, 7))
    assert len(normal.ereignisse) == 1 and not normal.ereignisse["monat_verdaechtig"].any()


def test_diagnose_ist_none_wenn_nichts_bewertet_wurde():
    ds = cube(seed=6, ny=40, nx=80, nicht_fertig=((2020, 8),))
    zu_wenig = erkenne(ds, (2016, 7))
    nicht_geladen = a.erkenne_zeitraum(ds, FELD, von=(2020, 8), bis=(2020, 8))[0]
    for r in (zu_wenig, nicht_geladen):
        assert r.diagnose["verdaechtig"] is None and r.diagnose["median_z"] is None  # nicht „unauffällig"


def test_status_steht_als_attribut_in_der_zellkarte():
    ds = cube(seed=6, ny=40, nx=80, nicht_fertig=((2020, 8),))
    rs = {r.monat[1]: r for r in a.erkenne_zeitraum(ds, FELD, von=(2020, 7), bis=(2020, 8))}
    assert rs[7].zellen.attrs["status"] == "bewertet"
    assert rs[8].zellen.attrs["status"] == "nicht geladen" and "keine Daten" in rs[8].zellen.attrs["grund"]
    assert erkenne(ds, (2016, 7)).zellen.attrs["status"] == "nicht bewertbar"


# --- Grundgerüst 2026-09-26: klassischer z-Wert, Basislinie nur beobachtet, Schnee, Pflichtfelder -------------


def test_klassischer_z_parallel_und_uneinig_bei_ausreisser_in_der_basislinie():
    ziel = (2021, 6)
    ds = kuenstlicher_wuerfel(ny=20, nx=30, jahre=(2010, 2022), seed=5, anteil_dunkel=0.0, breite_start=10.0, ereignisse=(
        Ereignis(monat=(2017, 6), zeilen=(5, 8), spalten=(5, 8), faktor=6.0),
        Ereignis(monat=ziel, zeilen=(5, 8), spalten=(5, 8), faktor=2.0),
    ))
    erk = a.erkenne_monat(ds, ziel, "allangle")
    z = erk.zellen
    block = (slice(5, 8), slice(5, 8))
    assert np.nanmedian(z["z"].values[block]) > 5 > np.nanmedian(z["z_klassisch"].values[block])
    assert z["z_uneinig"].values[block].any()
    bewertbar = z["datenlage"].values > 0
    assert np.isfinite(z["z_klassisch"].values[bewertbar]).all()
    assert (erk.ereignisse["anteil_z_uneinig"] > 0).any()


def test_basislinie_nutzt_nur_beobachtete_pixel():
    ds = kuenstlicher_wuerfel(ny=10, nx=12, jahre=(2010, 2022), seed=2, anteil_dunkel=0.0, breite_start=10.0)
    ziel = (2021, 6)
    vorher = a.erkenne_monat(ds, ziel, "allangle").zellen["z"].values
    ds2 = ds.copy(deep=True)
    werte = ds2["allangle_mittel"].values
    werte[:] = 1000.0  # Mittel MIT aufgefüllten Pixeln verfälscht: darf nichts ändern
    ds2["allangle_mittel"] = (ds2["allangle_mittel"].dims, werte)
    nachher = a.erkenne_monat(ds2, ziel, "allangle").zellen["z"].values
    np.testing.assert_allclose(vorher, nachher, equal_nan=True)


def test_schnee_verdacht_wird_nicht_bewertet_weder_im_ziel_noch_in_der_basis():
    ds = kuenstlicher_wuerfel(ny=10, nx=12, jahre=(2010, 2022), seed=4, anteil_dunkel=0.0, breite_start=62.0, aufgefuellt_mittel=0.0,
                              ereignisse=(Ereignis(monat=(2021, 1), zeilen=(0, 5), spalten=(0, 12), aufgefuellt_anteil=0.2, faktor=3.0),
                                          Ereignis(monat=(2016, 1), zeilen=(5, 10), spalten=(0, 12), aufgefuellt_anteil=0.2)))
    erk = a.erkenne_monat(ds, (2021, 1), "allangle")
    z = erk.zellen
    verdacht = z["schnee_verdacht"].values
    assert verdacht[:5].all() and not verdacht[5:].any()
    assert (z["datenlage"].values[:5] == 0).all() and np.isnan(z["z"].values[:5]).all()  # Verdreifachung, aber nicht bewertet
    assert not z["gemeldet"].values[:5].any()
    # Basislinie: 11 frühere Januare (2010-2020); in den Zeilen 5-9 fällt 2016-01 (Verdacht) heraus -> 10
    assert (z["n_basis"].values[:5] == 11).all() and (z["n_basis"].values[5:] == 10).all()


def test_ereigniszeilen_tragen_pflichtfelder():
    ds = kuenstlicher_wuerfel(ny=20, nx=30, jahre=(2010, 2022), seed=6, anteil_dunkel=0.0, breite_start=10.0,
                              ereignisse=(Ereignis(monat=(2021, 6), zeilen=(2, 6), spalten=(2, 6), faktor=3.0),))
    erk = a.erkenne_monat(ds, (2021, 6), "allangle")
    t = erk.ereignisse
    assert len(t) >= 1
    for spalte in ("evidenzstufe", "unsicherheit", "n_zellen", "n_basis_min", "methode", "erkennung_version"):
        assert t[spalte].notna().all()
    assert (t["evidenzstufe"] == "beobachtet").all()
    for k in ("evidenzstufe", "methode", "version", "unsicherheit"):
        assert erk.zellen.attrs[k]
