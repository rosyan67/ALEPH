"""Prüft die Lesefunktion: nur fertige Monate, nie „nicht geladen" als „keine Daten"."""

import numpy as np
import pytest
import xarray as xr

from aleph.detect import wuerfel as w
from aleph.detect.synthetisch import kuenstlicher_wuerfel

FELD = "allangle"
VARS = [f"{FELD}_mittel", f"{FELD}_gueltige_pixel", f"{FELD}_aufgefuellt_pixel"]


@pytest.fixture
def cube():
    # 2013-2016, drei Monate nicht geladen, einer halb geschrieben (Werte da, aber nicht fertig)
    return kuenstlicher_wuerfel(
        ny=6, nx=8, jahre=(2013, 2016), nicht_fertig=((2014, 3), (2014, 4), (2016, 12)), halb_geschrieben=((2015, 6),)
    )


def test_fertige_monate_liefert_nur_fertige_und_sortiert(cube):
    monate = w.fertige_monate(cube)
    assert monate == sorted(monate)
    assert len(monate) == 48 - 3 - 1
    for gesperrt in ((2014, 3), (2014, 4), (2016, 12), (2015, 6)):
        assert gesperrt not in monate


def test_halb_geschriebener_monat_gilt_nicht_als_fertig_obwohl_werte_da_sind(cube):
    i = list(cube["zeit"].values).index(np.datetime64("2015-06-01", "ns"))
    assert np.isfinite(cube[VARS[0]].values[i]).all()  # Werte stehen tatsächlich im Würfel ...
    assert (2015, 6) not in w.fertige_monate(cube)  # ... und trotzdem wird er nicht geliefert
    with pytest.raises(w.MonatNichtFertig, match="2015-06"):
        w.lies_monate(cube, [(2015, 6)], VARS)


def test_verlangter_nicht_geladener_monat_ist_ein_fehler_kein_leeres_ergebnis(cube):
    with pytest.raises(w.MonatNichtFertig) as fehler:
        w.lies_monate(cube, [(2014, 2), (2014, 3), (2014, 4)], VARS)
    text = str(fehler.value)
    assert "2014-03" in text and "2014-04" in text and "2014-02" not in text
    assert "keine Daten" in text  # die Meldung erklärt den Unterschied


def test_monat_ausserhalb_der_zeitachse_ist_ein_fehler(cube):
    with pytest.raises(w.MonatNichtFertig, match="2030-01"):
        w.lies_monate(cube, [(2030, 1)], VARS)


def test_lies_monate_liefert_verlangte_reihenfolge_und_werte(cube):
    ds = w.lies_monate(cube, [(2015, 1), (2013, 1)], VARS)
    assert [str(z)[:7] for z in ds["zeit"].values] == ["2015-01", "2013-01"]
    i = list(cube["zeit"].values).index(np.datetime64("2013-01-01", "ns"))
    np.testing.assert_array_equal(ds[VARS[0]].isel(zeit=1).values, cube[VARS[0]].values[i])


def test_lies_fertige_monate_laesst_nicht_fertige_weg_und_kennt_bereiche(cube):
    ds = w.lies_fertige_monate(cube, VARS)
    assert ds.sizes["zeit"] == 44
    assert np.isfinite(ds[VARS[0]].values).all()  # kein leerer (NaN) Monat rutscht durch
    teil = w.lies_fertige_monate(cube, VARS, von=(2014, 1), bis=(2014, 6))
    assert [str(z)[:7] for z in teil["zeit"].values] == ["2014-01", "2014-02", "2014-05", "2014-06"]


def test_lies_fertige_monate_ohne_fertigen_monat_ist_leer_aber_ehrlich():
    leer = kuenstlicher_wuerfel(ny=4, nx=4, jahre=(2013, 2013), nicht_fertig=tuple((2013, m) for m in range(1, 13)))
    ds = w.lies_fertige_monate(leer, VARS)
    assert ds.sizes["zeit"] == 0


def test_zeitachse_zeigt_auch_nicht_geladene_monate(cube):
    assert len(w.zeitachse_monate(cube)) == 48


def test_wuerfel_ohne_fertig_variable_wird_abgelehnt(cube):
    alt = cube.drop_vars("monat_fertig")
    with pytest.raises(w.WuerfelFormatFehler, match="monat_fertig"):
        w.fertige_monate(alt)
    with pytest.raises(w.WuerfelFormatFehler):
        w.lies_monate(alt, [(2013, 1)], VARS)


def test_unbekannte_variable_wird_gemeldet(cube):
    with pytest.raises(w.WuerfelFormatFehler, match="nicht_da"):
        w.lies_monate(cube, [(2013, 1)], ["nicht_da"])


def test_lesen_von_pfad_und_dataset_geben_dasselbe(cube, tmp_path):
    pfad = tmp_path / "test.zarr"
    cube.to_zarr(pfad)
    assert w.fertige_monate(pfad) == w.fertige_monate(cube)
    a = w.lies_monate(pfad, [(2013, 5)], VARS)
    b = w.lies_monate(cube, [(2013, 5)], VARS)
    xr.testing.assert_equal(a, b)
    with pytest.raises(w.MonatNichtFertig):
        w.lies_monate(pfad, [(2014, 3)], VARS)


def test_nicht_vorhandener_pfad_wird_klar_gemeldet(tmp_path):
    with pytest.raises(w.WuerfelFormatFehler, match="nicht gefunden"):
        w.fertige_monate(tmp_path / "gibt_es_nicht.zarr")


# --- Passt der Leser zum echten Würfel des Layers? ------------------------------


def test_konstanten_und_variablennamen_passen_zum_echten_layer():
    from aleph.layers import vnp46a3

    assert w.FERTIG_VARIABLE == vnp46a3.FERTIG_VARIABLE
    echte = set(vnp46a3._wuerfel_variablen())
    for feld in vnp46a3.FELD_TRIPEL:
        for v in (f"{feld}_mittel", f"{feld}_gueltige_pixel", f"{feld}_aufgefuellt_pixel"):
            assert v in echte, v
    assert vnp46a3.PIXEL_PRO_ZELLE**2 == 3600  # Standard von Schwellen.pixel_pro_zelle


def test_leser_funktioniert_am_echten_wuerfelaufbau(tmp_path, monkeypatch):
    """Legt mit dem Layer-Code einen echten (leeren) Würfel an und markiert einen Monat als fertig."""
    from aleph.layers import vnp46a3

    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    pfad = vnp46a3._wuerfel_pfad()
    vnp46a3._lege_wuerfel_an(pfad)
    assert w.fertige_monate(pfad) == []  # frisch angelegt: nichts fertig, obwohl 156 Monate auf der Achse stehen
    assert len(w.zeitachse_monate(pfad)) == 156
    with pytest.raises(w.MonatNichtFertig):
        w.lies_monate(pfad, [(2018, 1)], ["near_nadir_mittel"])
    region = {"zeit": slice(60, 61)}  # 2018-01
    xr.Dataset({vnp46a3.FERTIG_VARIABLE: (("zeit",), np.array([1], dtype="int8"))}).to_zarr(pfad, mode="r+", region=region)
    assert w.fertige_monate(pfad) == [(2018, 1)]
    ds = w.lies_monate(pfad, [(2018, 1)], ["near_nadir_mittel", "near_nadir_gueltige_pixel", "near_nadir_aufgefuellt_pixel"])
    assert ds.sizes == {"zeit": 1, "breite": 720, "laenge": 1440}
