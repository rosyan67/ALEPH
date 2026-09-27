"""Tests der Zell-Zuordnung (aleph/layers/zell_einheiten.py) und der Sondereinheiten-Liste.

Teil 1 ohne SSD: Gitter, Flächenrechnung, Datumsgrenze, Liste der Sondereinheiten.
Teil 2 mit echten Daten (nur mit angeschlossener SSD und gebauter Zuordnung, sonst übersprungen).
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import shapely
from shapely.geometry import box

from aleph.core import io
from aleph.layers import natural_earth as ne
from aleph.layers import vnp46a3
from aleph.layers import zell_einheiten as ze

# --- Teil 1: ohne SSD -------------------------------------------------------------


def test_gitter_ist_das_des_nachtlicht_wuerfels():
    breite, laenge, bk, lk = ze.gitter()
    vb, vl = vnp46a3._gitter_koordinaten()
    assert np.array_equal(breite, vb) and np.array_equal(laenge, vl)
    assert len(breite) == 720 and len(laenge) == 1440
    assert breite[0] == 89.875 and laenge[0] == -179.875
    assert bk[0] == 90 and bk[-1] == -90 and lk[0] == -180 and lk[-1] == 180
    assert np.allclose(np.diff(lk), 0.25) and np.allclose(np.diff(bk), -0.25)


def test_zellflaechen_werden_zu_den_polen_kleiner_und_summieren_sich_zur_erdoberflaeche():
    zf = ze.zellflaechen_km2()
    assert np.all(np.diff(zf[:360]) > 0) and np.all(np.diff(zf[360:]) < 0)  # Nord: wächst zum Äquator, Süd: fällt
    assert np.allclose(zf[:360], zf[::-1][:360])  # symmetrisch
    # Erdoberfläche des WGS-84-Ellipsoids aus a und f (authalische Kugel), nicht aus dem Gedächtnis
    a, f = 6378137.0, 1 / 298.257223563
    e = np.sqrt(f * (2 - f))
    flaeche = 2 * np.pi * a**2 * (1 + (1 - e**2) / e * np.arctanh(e)) / 1e6
    assert zf.sum() * 1440 == pytest.approx(flaeche, rel=1e-9)
    # Äquatorzelle: etwa 27,8 km × 27,6 km
    assert 760 < zf[359] < 775


def _anteile_grad(geom_grad):
    x, y = ze._kanten_projiziert()
    zf = (y[:-1] - y[1:]) * (x[1] - x[0])
    return ze.zellanteile(ze.projiziere(geom_grad), x, y, zf)


def test_genau_eine_zelle_hat_anteil_eins():
    z, s, f, a = _anteile_grad(box(10.0, 50.0, 10.25, 50.25))
    assert list(z) == [159] and list(s) == [760]
    assert a[0] == pytest.approx(1.0, abs=1e-9)


def test_halbe_zelle_und_ueber_zellgrenze():
    z, s, f, a = _anteile_grad(box(10.0, 50.0, 10.125, 50.25))
    assert a.sum() == pytest.approx(0.5, abs=1e-6)
    z, s, f, a = _anteile_grad(box(10.125, 50.0, 10.375, 50.25))
    assert sorted(s) == [760, 761]
    assert np.allclose(a, 0.5, atol=1e-6)


def test_anteil_ist_flaechenanteil_nicht_breitenanteil():
    # Untere Hälfte einer Zelle bei 60° N ist etwas größer als die obere (Zelle wird nach Norden schmaler)
    unten = _anteile_grad(box(10.0, 60.0, 10.25, 60.125))[3].sum()
    oben = _anteile_grad(box(10.0, 60.125, 10.25, 60.25))[3].sum()
    assert unten + oben == pytest.approx(1.0, abs=1e-9)
    assert unten > oben


def test_datumsgrenze_beide_seiten_werden_erfasst():
    fiji_artig = shapely.MultiPolygon([box(179.8, -17.2, 180.0, -16.9), box(-180.0, -17.2, -179.8, -16.9)])
    z, s, f, a = _anteile_grad(fiji_artig)
    assert 0 in set(s) and 1439 in set(s)
    assert not set(s) - {0, 1438, 1439}


def test_pol_zellen():
    z, s, f, a = _anteile_grad(box(-180, -90, 180, -89.75))
    assert set(z) == {719} and len(s) == 1440
    assert np.allclose(a, 1.0)


def test_sonderliste_vollstaendig_und_gueltig():
    daten = ze.lade_sonderliste()
    ids = {e["id"]: e for e in daten["einheiten"]}
    pflicht = {"taiwan", "westjordanland", "gaza", "tibet", "groenland", "krim", "donezk_2014", "luhansk_2014",
               "westsahara_marokko", "westsahara_ost", "nordzypern", "kosovo", "abchasien", "suedossetien",
               "transnistrien", "golan", "kaschmir_jammu_kaschmir", "kaschmir_azad", "kaschmir_gilgit_baltistan",
               "kaschmir_aksai_chin", "kaschmir_shaksgam", "kaschmir_siachen", "somaliland", "bergkarabach",
               "hongkong", "macau"}
    assert pflicht <= set(ids)
    assert ids["krim"]["un_m49"] == "804"
    assert ids["taiwan"]["un_m49"] == "156" and ids["kosovo"]["un_m49"] == "688"
    for e in daten["einheiten"]:
        assert e["un_beleg"] and e["gueltig"] and e["verwaltet_von"] and e["beansprucht_von"], e["id"]
        for feld in ("un_beleg", "un_status", "anerkennung", "weltbank_beleg"):
            assert "unklar" in e[feld] or any(q in e[feld] for q in daten["quellen"]) or "M49" in e[feld] or "WDI" in e[feld] \
                or "Weltbank" in e[feld] or e[feld].startswith(("wie ", "nicht zutreffend", "eigener", "keine")), (e["id"], feld)


def test_sonderliste_prueft_widersprueche(tmp_path):
    kaputt = tmp_path / "s.yaml"
    kaputt.write_text(ze.SONDER_DATEI.read_text(encoding="utf-8").replace('un_m49: "804"', "un_m49: null", 1), encoding="utf-8")
    with pytest.raises(ze.ZuordnungFehler, match="un_m49"):
        ze.lade_sonderliste(kaputt)


# --- Teil 2: echte Daten -------------------------------------------------------------


@pytest.fixture(scope="module")
def gebaut():
    try:
        return ze.lade()
    except (io.SSDNichtGefunden, ze.ZuordnungFehler, FileNotFoundError) as grund:
        pytest.skip(f"Zell-Zuordnung nicht verfügbar: {grund}")


def _zelle(lon, lat):
    breite, laenge, bk, lk = ze.gitter()
    return int(np.searchsorted(-bk, -lat, "right") - 1), int(np.searchsorted(lk, lon, "right") - 1)


def _groesster_anteil(zuordnung, lon, lat):
    z, s = _zelle(lon, lat)
    hier = zuordnung[(zuordnung.zeile == z) & (zuordnung.spalte == s)]
    return hier.sort_values("anteil", ascending=False).iloc[0] if len(hier) else None


def test_summe_der_anteile_je_zelle_hoechstens_eins(gebaut):
    _, zuordnung, _, manifest = gebaut
    summe = zuordnung.groupby(["zeile", "spalte"])["anteil"].sum()
    assert summe.max() <= 1 + 1e-9
    assert manifest["ergebnis"]["max_summe_anteile_je_zelle"] <= 1 + 1e-9


@pytest.mark.parametrize("einheit, lon, lat", [
    ("taiwan", 120.9, 23.7),          # Inselmitte
    ("krim", 34.1, 45.0),             # bei Simferopol
    ("tibet", 91.1, 29.7),            # bei Lhasa
    ("westjordanland", 35.25, 32.2),  # bei Nablus
    ("groenland", -40.0, 72.0),       # Inlandeis
    ("sued_belize", -88.81, 16.10),   # Punta Gorda (seit 2026-09-26)
    ("sabah_north_borneo", 118.12, 5.84),  # Sandakan (seit 2026-09-26)
])
def test_zellen_gehoeren_zur_eigenen_einheit(gebaut, einheit, lon, lat):
    _, zuordnung, _, _ = gebaut
    oben = _groesster_anteil(zuordnung, lon, lat)
    assert oben is not None and oben.einheit_id == einheit


def test_gaza_hat_eigene_zellanteile_und_keine_palaestina_grundeinheit(gebaut):
    """Der Gazastreifen ist schmaler als eine Zelle und hat in keiner Zelle die Mehrheit; geprüft wird,
    dass die Zelle von Gaza-Stadt (34,46° O / 31,52° N) die Einheit gaza enthält und die Fläche nirgends
    einer Grundeinheit Palästina (land_PSX) zugeschlagen ist."""
    einheiten, zuordnung, _, _ = gebaut
    z, s = _zelle(34.46, 31.52)
    hier = zuordnung[(zuordnung.zeile == z) & (zuordnung.spalte == s)].set_index("einheit_id")["anteil"]
    assert hier.get("gaza", 0) > 0.05
    assert "land_PSX" not in set(einheiten.einheit_id)
    gaza = einheiten.set_index("einheit_id").loc["gaza"]
    assert zuordnung[zuordnung.einheit_id == "gaza"].flaeche_km2.sum() == pytest.approx(gaza.flaeche_km2, rel=1e-6)


def test_krim_zellen_liegen_nicht_bei_russland_oder_ukraine(gebaut):
    einheiten, zuordnung, _, _ = gebaut
    z, s = _zelle(34.1, 45.0)
    hier = set(zuordnung[(zuordnung.zeile == z) & (zuordnung.spalte == s)].einheit_id)
    assert "krim" in hier and "land_RUS" not in hier


def test_krim_hat_uebergeordneten_un_eintrag_ukraine(gebaut):
    einheiten, _, _, _ = gebaut
    krim = einheiten.set_index("einheit_id").loc["krim"]
    assert krim.un_m49 == "804" and krim.un_name == "Ukraine"
    assert "umstritten" in krim.kategorien and "besetzt/Konfliktzone" in krim.kategorien


def test_zelle_mitten_im_atlantik_hat_kein_land(gebaut):
    _, zuordnung, _, _ = gebaut
    assert _groesster_anteil(zuordnung, -40.0, 30.0) is None


def test_fidschi_auf_beiden_seiten_der_datumsgrenze(gebaut):
    _, zuordnung, _, _ = gebaut
    spalten = set(zuordnung[zuordnung.einheit_id == "land_FJI"].spalte)
    assert 0 in spalten and 1439 in spalten


def test_russland_im_osten_ueber_die_datumsgrenze(gebaut):
    _, zuordnung, _, _ = gebaut
    spalten = set(zuordnung[zuordnung.einheit_id == "land_RUS"].spalte)
    assert 0 in spalten and 1439 in spalten  # Tschukotka westlich von −180° / östlich von 180°


def test_flaeche_je_einheit_bleibt_erhalten(gebaut):
    einheiten, zuordnung, _, _ = gebaut
    summe = zuordnung.groupby("einheit_id")["flaeche_km2"].sum()
    vergleich = einheiten.set_index("einheit_id")["flaeche_km2"]
    rel = (summe.reindex(vergleich.index).fillna(0) - vergleich).abs() / vergleich
    assert rel.max() < 1e-6


def test_jede_einheit_hat_un_angabe_und_weltbank_angabe(gebaut):
    einheiten, _, _, _ = gebaut
    assert einheiten["un_art"].isin(ze.UN_ARTEN).all()
    assert einheiten["weltbank_art"].isin(ze.WELTBANK_ARTEN).all()
    unklar = einheiten[einheiten.un_m49.isna()]
    assert unklar["un_art"].isin(["unklar", "nicht in M49"]).all()


@pytest.fixture(scope="module")
def echte_laender():
    try:
        return ne.lade_laender()
    except (io.SSDNichtGefunden, ne.NaturalEarthFehler) as grund:
        pytest.skip(f"Echte Natural-Earth-Daten nicht verfügbar: {grund}")


@pytest.mark.parametrize("code", ["DEU", "EGY", "SAU", "RUS", "BHR"])
def test_zellflaechen_gegen_flaeche_der_grenzdatei(echte_laender, code):
    """Summe der Zellstücke des ganzen NE-Umrisses = Fläche des Umrisses; dazu Vergleich mit Geod (Geodäten)."""
    umriss = echte_laender[echte_laender.ADM0_A3 == code].geometry.iloc[0]
    x, y = ze._kanten_projiziert()
    zf = (y[:-1] - y[1:]) * (x[1] - x[0])
    projiziert = ze.projiziere(umriss)
    _, _, f, _ = ze.zellanteile(projiziert, x, y, zf)
    assert f.sum() == pytest.approx(projiziert.area, rel=1e-9)
    assert projiziert.area / 1e6 == pytest.approx(ze.geodaetische_flaeche_km2(umriss), rel=1e-4)


@pytest.mark.parametrize("sonder, grundeinheiten", [
    ("krim", ["land_RUS", "land_UKR"]),
    ("taiwan", ["land_CHN"]),
    ("tibet", ["land_CHN", "land_IND", "land_NPL", "land_BTN", "land_MMR"]),
    ("westjordanland", ["land_ISR", "land_JOR"]),
    ("gaza", ["land_ISR", "land_EGY"]),
    ("groenland", ["land_DNK", "land_CAN"]),
])
def test_keine_grundeinheit_ueberlappt_eine_sondereinheit(gebaut, sonder, grundeinheiten):
    """Prüft die ganzen Umrisse (nicht nur eine Zelle): Randstreifen, die beim Nachbarland hängen bleiben, fielen hier auf."""
    einheiten, _, _, _ = gebaut
    umriss = dict(zip(einheiten.einheit_id, shapely.from_wkb(einheiten.umriss_wkb)))
    for g in grundeinheiten:
        assert shapely.intersection(umriss[sonder], umriss[g]).area / 1e6 < 1e-3, g


def test_manifest_erhaltung_je_zelle(gebaut):
    _, _, _, manifest = gebaut
    assert manifest["ergebnis"]["max_abweichung_je_zelle_gegen_landflaeche"] < 1e-6


# --- Bau-Regeln mit kleinen Beispielflächen -------------------------------------------


def _beispielwelt(zusatz_umstritten=()):
    laender = gpd.GeoDataFrame({
        "ADM0_A3": ["AAA", "BBB", "VVV", "CCC"], "ADMIN": ["Aland", "Bland", "Winzig", "Cland"],
        "TYPE": ["Sovereign country"] * 4, "ISO_A3_EH": ["AAA", "BBB", "VVV", "CCC"],
        "land_iso3": ["AAA", "BBB", "VVV", "CCC"],
        "geometry": [box(0, 0, 10, 10), box(10, 0, 20, 10), box(30, 0, 30.001, 0.001), box(40, 0, 42, 2)],
    }, crs="EPSG:4326")
    zeilen = [
        {"BRK_A3": "D1", "BRK_NAME": "Streitgebiet", "TYPE": "Disputed", "NOTE_BRK": "Admin. by A; Claimed by B", "ADM0_A3": "AAA", "geometry": box(1, 1, 5, 5)},
        {"BRK_A3": "D2", "BRK_NAME": "Innen", "TYPE": "Disputed", "NOTE_BRK": "Admin. by A; Claimed by C", "ADM0_A3": "AAA", "geometry": box(2, 2, 3, 3)},
        {"BRK_A3": "D3", "BRK_NAME": "Puffer", "TYPE": "Overlay", "NOTE_BRK": "patrolled; Claimed by X", "ADM0_A3": "BBB", "geometry": box(12, 1, 13, 2)},
        {"BRK_A3": "D4", "BRK_NAME": "Pacht", "TYPE": "Lease", "NOTE_BRK": "Leased", "ADM0_A3": "BBB", "geometry": box(14, 1, 15, 2)},
        {"BRK_A3": "D5", "BRK_NAME": "Ohne Anspruch", "TYPE": "Disputed", "NOTE_BRK": None, "ADM0_A3": "BBB", "geometry": box(16, 1, 17, 2)},
        {"BRK_A3": "D6", "BRK_NAME": "Cland doppelt", "TYPE": "Disputed", "NOTE_BRK": "Self admin.; Claimed by A", "ADM0_A3": "CCC", "geometry": box(40, 0, 42, 2)},
        {"BRK_A3": "D7", "BRK_NAME": "Namensinsel", "TYPE": "Disputed", "NOTE_BRK": "Admin. by B; Claimed by A", "ADM0_A3": "BBB", "geometry": box(18, 8, 19, 9)},
        *zusatz_umstritten,
    ]
    umstritten = gpd.GeoDataFrame(zeilen, crs="EPSG:4326")
    provinzen = gpd.GeoDataFrame({"adm1_code": ["AAA-1"], "adm0_a3": ["AAA"], "geometry": [box(6, 6, 9, 9)]}, crs="EPSG:4326")
    m49 = pd.DataFrame({"name": ["Aland", "Bland", "Winzig", "Cland", "Namensinsel"], "m49": ["001", "002", "003", "004", "005"],
                        "iso3": ["AAA", "BBB", "VVV", "CCC", "NNN"]})
    def eintrag(i, datei, feld, wert, un):
        return {"id": i, "name": i, "geometrie": {"datei": datei, "feld": feld, "wert": wert}, "kategorien": ["umstritten"],
                "un_m49": un, "un_art": "ausdrücklich", "un_beleg": "x", "un_status": "x", "beansprucht_von": "x",
                "verwaltet_von": "x", "anerkennung": "x", "gueltig": "x", "weltbank_code": None, "weltbank_art": "keine",
                "weltbank_beleg": "x"}
    sonder = {"einheiten": [eintrag("cland_sonder", "laender", "ADM0_A3", "CCC", "004"),
                            eintrag("provinz", "provinzen", "adm1_code", "AAA-1", "001")], "weltbank_laender": {}}
    return laender, umstritten, provinzen, m49, sonder


def test_bauregeln_an_beispielflaechen():
    tab, geoms, nicht, land, rep = ze.baue_einheiten(*_beispielwelt())
    fl = dict(zip(tab.einheit_id, [g.area for g in geoms]))
    ids = set(tab.einheit_id)
    # kleinere Sondereinheit hat Vorrang: D2 behält ihre ganze Fläche, D1 hat ein Loch
    assert fl["ne_umstritten_D2"] == pytest.approx(ze.projiziere(box(2, 2, 3, 3)).area, rel=1e-9)
    assert fl["ne_umstritten_D1"] == pytest.approx(ze.projiziere(box(1, 1, 5, 5)).area - fl["ne_umstritten_D2"], rel=1e-9)
    # Grundeinheit ohne die Sondereinheiten
    abzug = fl["ne_umstritten_D1"] + fl["ne_umstritten_D2"] + fl["provinz"]
    assert fl["land_AAA"] == pytest.approx(ze.projiziere(box(0, 0, 10, 10)).area - abzug, rel=1e-9)
    # ganz überdeckte Grundeinheit entfällt, winziges Land ohne Überdeckung bleibt
    assert "land_CCC" not in ids and "land_VVV" in ids
    grund = dict(zip(nicht.brk_a3, nicht.grund))
    assert grund["CCC"].startswith("Rest nach Abzug")
    # Doppel, Overlay, Lease, ohne Anspruch
    assert grund["D6"].startswith("Doppel") and "Overlay" in grund["D3"] and "Lease" in grund["D4"]
    assert grund["D5"].startswith("kein Anspruch")
    # M49: über den Namen (D7) und nicht über einen fremden ISO-Code
    un = dict(zip(tab.einheit_id, tab.un_m49))
    assert un["ne_umstritten_D7"] == "005" and pd.isna(un["ne_umstritten_D1"])
    # Summe der Flächen = Landfläche (nichts verloren, nichts doppelt)
    assert sum(fl.values()) == pytest.approx(land.area, rel=1e-9)


def test_geteilter_iso_code_gibt_keinen_m49_eintrag():
    laender, umstritten, provinzen, m49, sonder = _beispielwelt()
    laender = pd.concat([laender, gpd.GeoDataFrame({"ADM0_A3": ["BB2"], "ADMIN": ["Bland-Insel"], "TYPE": ["Dependency"],
                         "ISO_A3_EH": ["BBB"], "land_iso3": ["BBB"], "geometry": [box(50, 0, 50.5, 0.5)]}, crs="EPSG:4326")], ignore_index=True)
    umstritten = pd.concat([umstritten, gpd.GeoDataFrame([{"BRK_A3": "D8", "BRK_NAME": "Inselstreit", "TYPE": "Indeterminate",
                            "NOTE_BRK": "Claimed by B and A", "ADM0_A3": "BB2", "geometry": box(50, 0, 50.5, 0.5)}], crs="EPSG:4326")], ignore_index=True)
    tab, *_ = ze.baue_einheiten(laender, umstritten, provinzen, m49, sonder)
    assert pd.isna(tab.set_index("einheit_id").loc["ne_umstritten_D8", "un_m49"])


def test_provinz_ausserhalb_des_mutterlandes_bricht_ab():
    laender, umstritten, provinzen, m49, sonder = _beispielwelt()
    provinzen.loc[0, "geometry"] = box(8, 6, 12, 9)  # ragt 2° in Bland hinein
    with pytest.raises(ze.ZuordnungFehler, match="außerhalb des Mutterlandes"):
        ze.baue_einheiten(laender, umstritten, provinzen, m49, sonder)


def test_weltbank_sicht_und_reinheit():
    einheiten = pd.DataFrame({"einheit_id": ["a", "b", "c", "d"], "weltbank_code": ["AAA", "AAA", "BBB", None],
                              "weltbank_art": ["belegt", "unklar", "ohne Gebietshinweis", "keine"]})
    assert set(ze.weltbank_sicht(einheiten).index) == {"a", "b", "c"}
    assert set(ze.weltbank_sicht(einheiten, mit_unklar=False).index) == {"a", "c"}
    zuordnung = pd.DataFrame({"zeile": [0, 1, 1, 2], "spalte": [0, 0, 0, 0], "einheit_id": ["a", "a", "c", "b"],
                              "anteil": [1.0, 0.5, 0.5, 0.3], "flaeche_km2": [10.0, 5.0, 5.0, 3.0]})
    r = ze.reinheit(einheiten, zuordnung)
    # AAA: Zelle 0 rein (10), Zelle 1 geteilt (5), Zelle 2 rein bezogen auf Land (3) → 13/18
    assert r.loc["AAA", "reinheit"] == pytest.approx(13 / 18)
    assert r.loc["BBB", "reinheit"] == pytest.approx(0.0)


@pytest.mark.parametrize("einheit, verwaltet, beansprucht, quelle", [
    ("sued_belize", "Belize", "Guatemala", "ICJ_177"),
    ("sabah_north_borneo", "Malaysia", "Philippinen", "RA_5446"),
])
def test_sabah_und_sued_belize_sind_umstrittene_eigene_einheiten(gebaut, einheit, verwaltet, beansprucht, quelle):
    """Auftrag 2026-09-26: eigene Einheiten nach denselben Regeln; keine UN-Zuordnung behauptet, die nicht belegt ist."""
    einheiten, zuordnung, _, _ = gebaut
    e = einheiten.set_index("einheit_id").loc[einheit]
    assert e.kategorien == "umstritten" and e.ebene == "Sondereinheit"
    assert e.un_art == "unklar" and (e.un_m49 is None or e.un_m49 != e.un_m49 or e.un_m49 == "")  # leer bzw. NaN
    assert e.beansprucht_von.startswith(beansprucht) and quelle in e.beansprucht_von + e.un_beleg
    assert e.verwaltet_von.startswith(verwaltet)
    assert "Nicht selbst nachgezeichnet" in e.umriss_hinweis
    assert zuordnung[zuordnung.einheit_id == einheit].anteil.sum() > 1


def test_sabah_name_passt_zum_umriss():
    """Auftrag 2026-09-27: Der Umriss (NE C04 „North Borneo“) deckt nur den Osten Sabahs ab; der Name sagt das."""
    import yaml

    daten = yaml.safe_load(ze.SONDER_DATEI.read_text(encoding="utf-8"))
    eintraege = daten if isinstance(daten, list) else next(v for v in daten.values() if isinstance(v, list))
    e = next(x for x in eintraege if x["id"] == "sabah_north_borneo")
    assert e["name"] == "Ost-Sabah (von den Philippinen beansprucht)"
    assert "östlichen Teil des Bundesstaats Sabah" in e["umriss_hinweis"]
    assert e["geometrie"] == {"datei": "umstritten", "feld": "BRK_A3", "wert": "C04"}  # Quelle unverändert
    assert "RA_5446" in e["beansprucht_von"] and "ICJ_102" in e["un_beleg"]
