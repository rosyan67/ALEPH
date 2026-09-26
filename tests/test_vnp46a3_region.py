"""Tests zum Vorrang nach Region (2026-09-26): Kachelliste, beschränktes Laden,
Zustand 4 im Würfel, Vereinigen in Stufe 2, Lesefunktion („nicht geladen“ nie als 0),
zweistufiger Lauf."""

import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from aleph.core import io
from aleph.detect import wuerfel
from aleph.layers import vnp46a3, vnp46a3_lauf, vnp46a3_regionen


@pytest.fixture
def fake_ssd(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------- Kachelliste


@pytest.mark.echter_katalog
def test_kachelliste_afrika_europa_asien():
    region = vnp46a3_regionen.lies_region(vnp46a3_regionen.AFRIKA_EUROPA_ASIEN)
    assert len(region) == 188
    assert region <= vnp46a3.lies_referenz_positionen()
    kopf = vnp46a3_regionen.listen_pfad(vnp46a3_regionen.AFRIKA_EUROPA_ASIEN).read_text(encoding="utf-8")
    assert "# Regel:" in kopf and "# Quellen:" in kopf and "# Anzahl: 188" in kopf
    # Stichproben: Berlin (h19v03), Kairo (h21v06), Delhi (h25v06), Tokio (h31v05) drin;
    # New York (h12v04), Sydney (h31v12) nicht.
    for p in ("h19v03", "h21v06", "h25v06", "h31v05"):
        assert p in region, p
    for p in ("h12v04", "h31v12"):
        assert p not in region, p


def test_kachelliste_mit_falscher_anzahl_wird_abgelehnt(tmp_path, monkeypatch):
    datei = tmp_path / "liste.txt"
    datei.write_text("# Anzahl: 3\nh19v03\nh20v03\n", encoding="utf-8")
    monkeypatch.setattr(vnp46a3_regionen, "listen_pfad", lambda region: datei)
    with pytest.raises(vnp46a3_regionen.RegionFehler, match="Anzahl"):
        vnp46a3_regionen.lies_region("afrika_europa_asien")


def test_zellmaske_und_kachel_von_zelle():
    m = vnp46a3_regionen.zellmaske({"h00v00", "h19v03"})
    assert m.sum() == 2 * 40 * 40
    assert m[0:40, 0:40].all() and m[120:160, 760:800].all() and not m[40, 0]
    assert vnp46a3_regionen.kachel_von_zelle(149, 773) == "h19v03"  # Berlin


# ---------------------------------------------------------------- lade_monat mit Positionen


class _Granule:
    def __init__(self, url):
        self.url = url

    def data_links(self):
        return [self.url]


def _granules(positionen):
    return [_Granule(f"https://example.org/VNP46A3.A2024001.{p}.002.20240101000000.h5") for p in positionen]


def _lade_attrappe(scheitert=()):
    aufgerufen = []

    def lade(granule, ziel_ordner, **kwargs):
        name = granule.data_links()[0].rsplit("/", 1)[-1]
        pos = vnp46a3._position(name)
        aufgerufen.append(pos)
        if pos in scheitert:
            raise vnp46a3.KachelNichtGeladen(f"{pos}: simuliert 404", dauerhaft=True, status=404)
        pfad = ziel_ordner / name
        pfad.touch()
        return pfad
    return lade, aufgerufen


def test_lade_monat_laedt_nur_die_verlangten_positionen(monkeypatch, tmp_path):
    alle = [f"h{i:02d}v05" for i in range(6)]
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **k: _granules(alle))
    lade, aufgerufen = _lade_attrappe()
    monkeypatch.setattr(vnp46a3, "_lade_kachel", lade)
    meldungen = []
    ladung = vnp46a3.lade_monat(2024, 1, tmp_path, melde=meldungen.append, positionen={"h01v05", "h02v05"})
    assert sorted(aufgerufen) == ["h01v05", "h02v05"]
    assert sorted(vnp46a3._position(p.name) for p in ladung.dateien) == ["h01v05", "h02v05"]
    assert set(ladung.zustaende) == {"h01v05", "h02v05"}
    assert "für 2 ausgewählte Positionen (Katalog gesamt 6)" in meldungen[0]


def test_fehlende_region_kachel_macht_die_region_unvollstaendig(monkeypatch, tmp_path):
    alle = [f"h{i:02d}v05" for i in range(6)]
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **k: _granules(alle))
    lade, aufgerufen = _lade_attrappe(scheitert={"h02v05", "h04v05"})
    monkeypatch.setattr(vnp46a3, "_lade_kachel", lade)
    with pytest.raises(vnp46a3.KachelnFehlen) as info:
        vnp46a3.lade_monat(2024, 1, tmp_path, positionen={"h01v05", "h02v05"})
    assert "h04v05" not in aufgerufen  # außerhalb der Region nicht versucht
    assert info.value.zustaende["h02v05"].zustand == vnp46a3.ZUSTAND_NICHT_GELADEN


def test_region_position_fehlt_im_katalog(monkeypatch, tmp_path):
    """Streng wie bisher: eine Region-Position der Referenzliste, die der Katalog nicht meldet, bricht ab."""
    alle = [f"h{i:02d}v05" for i in range(3)]
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **k: _granules(alle))
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", lambda pfad=None: set(alle) | {"h09v05"})
    lade, _ = _lade_attrappe()
    monkeypatch.setattr(vnp46a3, "_lade_kachel", lade)
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="h09v05"):
        vnp46a3.lade_monat(2024, 1, tmp_path, positionen={"h01v05", "h09v05"})


def test_positionen_ausserhalb_der_referenz_werden_abgelehnt(monkeypatch, tmp_path):
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data", lambda **k: _granules(["h01v05"]))
    with pytest.raises(vnp46a3.ReferenzlisteVeraltet):
        vnp46a3.lade_monat(2024, 1, tmp_path, positionen={"h30v17"})


# ---------------------------------------------------------------- Würfel: Zustand 4, Vereinigen, Lesen

REGION = {"h19v03"}  # Berlin
REST = {"h20v03"}


def _monat(jahr, monat, positionen, wert):
    """Monatsdaten wie aus verkleinere_monat: Werte nur in den Zellen der Kacheln `positionen`."""
    breite, laenge = vnp46a3._gitter_koordinaten()
    maske = vnp46a3_regionen.zellmaske(positionen)
    variablen = {}
    for name, dtyp in vnp46a3._wuerfel_variablen().items():
        if dtyp.startswith("float"):
            a = np.full(maske.shape, np.nan, dtype=dtyp)
            a[maske] = wert
        else:
            a = np.zeros(maske.shape, dtype=dtyp)
            a[maske] = 3600
        variablen[name] = (("zeit", "breite", "laenge"), a[np.newaxis])
    return xr.Dataset(variablen, coords={"zeit": [np.datetime64(f"{jahr:04d}-{monat:02d}-01")],
                                         "breite": breite, "laenge": laenge})


def test_zustand_4_zaehlt_nicht_als_vorhanden_und_wird_nie_als_0_gelesen(fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 1, REGION, 7.0), zielzustand=vnp46a3.MONAT_REGION_VOLLSTAENDIG)
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, REGION | REST, 5.0))  # ganz fertig
    assert vnp46a3.monatsstatus(2018, 1) == vnp46a3.MONAT_REGION_VOLLSTAENDIG
    assert vnp46a3.vorhandene_monate() == {(2018, 2)}
    pfad = vnp46a3._wuerfel_pfad()
    # Die bisherigen Lesefunktionen liefern den Region-Monat gar nicht.
    assert wuerfel.fertige_monate(pfad) == [(2018, 2)]
    with pytest.raises(wuerfel.MonatNichtFertig):
        wuerfel.lies_monate(pfad, [(2018, 1)], ["allangle_mittel"])
    # Die neue Lesefunktion: außerhalb der Region NaN in JEDER Variable (auch Zählern) und markiert.
    maske = vnp46a3_regionen.zellmaske(REGION)
    variablen = ["allangle_mittel", "allangle_gueltige_pixel", "allangle_beobachtete_pixel"]
    ds = wuerfel.lies_monate_mit_region(pfad, [(2018, 1), (2018, 2)], variablen, maske)
    ng = ds["nicht_geladen"].values
    assert ng[0].sum() == (~maske).sum() and not ng[0][maske].any()
    assert not ng[1].any()  # fertiger Monat: nichts „nicht geladen“
    for v in variablen:
        werte = ds[v].values[0]
        assert np.isnan(werte[~maske]).all(), v  # nie 0, nie „dunkel“
        assert np.isfinite(werte[maske]).all(), v
    assert ds["allangle_mittel"].values[0][maske][0] == 7.0
    # Im fertigen Monat bleibt eine echte 0 (Zähler außerhalb der geladenen Kacheln) eine 0.
    assert ds["allangle_gueltige_pixel"].values[1][~vnp46a3_regionen.zellmaske(REGION | REST)][0] == 0


def test_zustand_0_2_3_werden_auch_regional_nicht_geliefert(fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 1, REGION, 7.0), zielzustand=vnp46a3.MONAT_REGION_VOLLSTAENDIG)
    with pytest.raises(wuerfel.MonatNichtFertig, match="2018-03"):
        wuerfel.lies_monate_mit_region(vnp46a3._wuerfel_pfad(), [(2018, 1), (2018, 3)], ["allangle_mittel"],
                                       vnp46a3_regionen.zellmaske(REGION))


def test_region_monat_nicht_zweimal_und_nur_zulaessige_zielzustaende(fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 1, REGION, 7.0), zielzustand=vnp46a3.MONAT_REGION_VOLLSTAENDIG)
    with pytest.raises(vnp46a3.MonatSchonVorhanden):
        vnp46a3.schreibe_in_wuerfel(_monat(2018, 1, REGION, 8.0), zielzustand=vnp46a3.MONAT_REGION_VOLLSTAENDIG)
    with pytest.raises(ValueError):
        vnp46a3.schreibe_in_wuerfel(_monat(2018, 3, REGION, 1.0), zielzustand=vnp46a3.MONAT_UNVOLLSTAENDIG)


def test_stufe_2_vereinigt_region_aus_dem_wuerfel_mit_dem_rest(fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 1, REGION, 7.0), zielzustand=vnp46a3.MONAT_REGION_VOLLSTAENDIG)
    ganz = vnp46a3.vereine_mit_region(_monat(2018, 1, REST, 3.0), REGION)
    vnp46a3.schreibe_in_wuerfel(ganz)
    assert vnp46a3.vorhandene_monate() == {(2018, 1)}
    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as ds:
        werte = ds["allangle_mittel"].isel(zeit=vnp46a3._monat_index(2018, 1)).values
    assert (werte[vnp46a3_regionen.zellmaske(REGION)] == 7.0).all()
    assert (werte[vnp46a3_regionen.zellmaske(REST)] == 3.0).all()


def test_stufe_2_bricht_bei_ueberschneidung_oder_falschem_zustand_ab(fake_ssd):
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 1, REGION, 7.0), zielzustand=vnp46a3.MONAT_REGION_VOLLSTAENDIG)
    with pytest.raises(vnp46a3.MonatStimmtNicht, match="überschneiden"):
        vnp46a3.vereine_mit_region(_monat(2018, 1, REGION | REST, 3.0), REGION)
    vnp46a3.schreibe_in_wuerfel(_monat(2018, 2, REGION | REST, 3.0))
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="Zustand 4"):
        vnp46a3.vereine_mit_region(_monat(2018, 2, REST, 3.0), REGION)


# ---------------------------------------------------------------- zweistufiger Lauf


def _lauf_attrappe(monkeypatch, referenz, region, scheitert=()):
    """lade_monat/verkleinere_monat als Attrappen; `scheitert`: Menge von (Monat, Stufe) mit KachelnFehlen."""
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", lambda pfad=None: set(referenz))
    monkeypatch.setattr(vnp46a3_regionen, "lies_region", lambda r: set(region))
    monkeypatch.setattr(io, "pruefe_speicher", lambda *a, **k: None)
    aufrufe = []

    def lade_monat(jahr, monat, ziel_ordner, gleichzeitige_downloads=3, melde=None, positionen=None):
        positionen = set(positionen) if positionen is not None else set(referenz)
        stufe = "region" if positionen == set(region) else ("rest" if positionen == set(referenz) - set(region) else "voll")
        aufrufe.append(((jahr, monat), stufe))
        if ((jahr, monat), stufe) in scheitert:
            raise vnp46a3.KachelnFehlen(f"{jahr}-{monat:02d}: 1 Kachel fehlt (simuliert).", dauerhaft=1, vorlaeufig=0)
        ziel_ordner.mkdir(parents=True, exist_ok=True)
        dateien, zustaende = [], {}
        for p in sorted(positionen):
            f = ziel_ordner / f"VNP46A3.A{jahr:04d}001.{p}.002.x.h5"
            f.touch()
            dateien.append(f)
            zustaende[p] = vnp46a3.KachelEintrag(vnp46a3.ZUSTAND_GELADEN, vnp46a3.KachelSoll(f.name, 0, "-"))
        return vnp46a3.MonatsLadung(dateien=dateien, zustaende=zustaende, katalog_positionen=set(referenz))

    def verkleinere(dateien, erwarteter_monat=None):
        pos = {vnp46a3._position(f.name) for f in dateien}
        return _monat(*erwarteter_monat, pos, 1.0 if pos == set(region) else 2.0)

    monkeypatch.setattr(vnp46a3, "lade_monat", lade_monat)
    monkeypatch.setattr(vnp46a3, "verkleinere_monat", verkleinere)
    return aufrufe


def _starte_lauf(monkeypatch, ende="2018-02"):
    monkeypatch.setattr(sys, "argv", ["x", "--start", "2018-01", "--ende", ende, "--region-zuerst", "afrika_europa_asien"])
    monkeypatch.setattr(vnp46a3_lauf, "NACHHOL_PAUSE_SEKUNDEN", 0)
    return vnp46a3_lauf.main()


def test_lauf_laedt_erst_die_region_aller_monate_dann_den_rest(fake_ssd, monkeypatch):
    aufrufe = _lauf_attrappe(monkeypatch, REGION | REST, REGION)
    assert _starte_lauf(monkeypatch) == 0
    assert aufrufe == [((2018, 1), "region"), ((2018, 2), "region"), ((2018, 1), "rest"), ((2018, 2), "rest")]
    assert vnp46a3.vorhandene_monate() == {(2018, 1), (2018, 2)}
    log = (fake_ssd / "protokoll" / "vnp46a3.log").read_text(encoding="utf-8")
    assert "2018-01: fertig für Afrika-Europa-Asien, 1 Kacheln" in log
    assert "2018-01: fertig (Stufe 2, übrige Kacheln), 1 Kacheln" in log
    assert "Stufe 1 (Afrika-Europa-Asien) beendet" in log and "Lauf fertig" in log
    manifest = (fake_ssd / "protokoll" / "manifeste" / "vnp46a3" / "2018-01_afrika_europa_asien.tsv").read_text(encoding="utf-8")
    assert f"Region-Kacheln-Prüfsumme: {vnp46a3_regionen.pruefsumme(REGION)}" in manifest
    assert (fake_ssd / "protokoll" / "manifeste" / "vnp46a3" / "2018-01_rest.tsv").exists()
    assert not (fake_ssd / "raw" / "vnp46a3" / "2018-01").exists()  # nach Stufe 2 aufgeräumt
    # die Region-Zellen stammen aus Stufe 1, die übrigen aus Stufe 2
    with xr.open_zarr(vnp46a3._wuerfel_pfad(), chunks=None) as ds:
        w = ds["allangle_mittel"].isel(zeit=vnp46a3._monat_index(2018, 1)).values
    assert (w[vnp46a3_regionen.zellmaske(REGION)] == 1.0).all() and (w[vnp46a3_regionen.zellmaske(REST)] == 2.0).all()


def test_scheitert_stufe_1_laedt_stufe_2_den_ganzen_monat(fake_ssd, monkeypatch):
    aufrufe = _lauf_attrappe(monkeypatch, REGION | REST, REGION, scheitert={((2018, 1), "region")})
    assert _starte_lauf(monkeypatch, ende="2018-01") == 0
    # Stufe 1 und ihr Nachhol-Durchgang scheitern (kein Fortschritt), Stufe 2 lädt den ganzen Monat
    assert aufrufe[-1] == ((2018, 1), "voll")
    assert all(a == ((2018, 1), "region") for a in aufrufe[:-1])
    assert vnp46a3.vorhandene_monate() == {(2018, 1)}


def test_geaenderte_kachelliste_zwischen_den_stufen_fuehrt_zum_vollen_neuladen(fake_ssd, monkeypatch):
    """Auflage B1: Zustand 4 mit einer anderen Liste darf nicht still zu Zustand 1 vereinigt werden."""
    _lauf_attrappe(monkeypatch, REGION | REST, REGION)
    monkeypatch.setattr(sys, "argv", ["x", "--start", "2018-01", "--ende", "2018-01", "--region-zuerst", "afrika_europa_asien"])
    vnp46a3_lauf.verarbeite_monat(2018, 1, vnp46a3_lauf.Protokoll(fake_ssd / "protokoll" / "vnp46a3.log"), 3,
                                  stufe=vnp46a3_lauf.STUFE_REGION, region="afrika_europa_asien")
    assert vnp46a3.monatsstatus(2018, 1) == vnp46a3.MONAT_REGION_VOLLSTAENDIG
    groesser = REGION | {"h21v03"}
    aufrufe = _lauf_attrappe(monkeypatch, REGION | REST | {"h21v03"}, groesser)  # Liste wurde neu erzeugt
    ok, grund, _ = vnp46a3.pruefe_stufe1_nachweis(2018, 1, "afrika_europa_asien")
    assert not ok and "geändert" in grund
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="geändert"):
        vnp46a3.lies_monate_mit_region([(2018, 1)], ["allangle_mittel"], "afrika_europa_asien")
    vnp46a3_lauf.verarbeite_monat(2018, 1, vnp46a3_lauf.Protokoll(fake_ssd / "protokoll" / "vnp46a3.log"), 3,
                                  stufe=vnp46a3_lauf.STUFE_REST, region="afrika_europa_asien")
    assert aufrufe == [((2018, 1), "voll")]  # kein Vereinigen, sondern ganzer Monat
    assert vnp46a3.vorhandene_monate() == {(2018, 1)}
    log = (fake_ssd / "protokoll" / "vnp46a3.log").read_text(encoding="utf-8")
    assert "Stufe-1-Nachweis passt nicht" in log


def test_grenze_beim_anbieter_nicht_vorhanden_gilt_fuer_den_ganzen_monat(monkeypatch, tmp_path):
    """Auflage B2: 11 fehlende Positionen im Monat brechen auch dann ab, wenn nur 5 davon in der Stufe liegen."""
    katalog = [f"h{i:02d}v05" for i in range(4)]
    fehlend = {f"h{i:02d}v01" for i in range(11)}  # nördlich 50° N, im Juni an sich erlaubt, aber 11 > 10
    monkeypatch.setattr(vnp46a3, "earthdata_login", lambda: True)
    monkeypatch.setattr(vnp46a3.earthaccess, "search_data",
                        lambda **k: [_Granule(f"https://example.org/VNP46A3.A2018152.{p}.002.x.h5") for p in katalog])
    monkeypatch.setattr(vnp46a3, "lies_referenz_positionen", lambda pfad=None: set(katalog) | fehlend)
    lade, aufgerufen = _lade_attrappe()
    monkeypatch.setattr(vnp46a3, "_lade_kachel", lade)
    stufe = {"h00v05", "h01v05"} | {f"h{i:02d}v01" for i in range(5)}
    with pytest.raises(vnp46a3.MonatUnvollstaendig, match="11 Positionen"):
        vnp46a3.lade_monat(2018, 6, tmp_path, positionen=stufe)
    assert aufgerufen == []  # vor jedem Download abgebrochen
