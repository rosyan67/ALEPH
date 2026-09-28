"""Tests für aleph/export/globus.py (Daten für web/globus.html)."""

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from aleph.core import io
from aleph.export import globus as g


# ---------------------------------------------------------------- Hilfen


def _wuerfel(monate, status):
    """Künstlicher Würfel mit dem echten Gitter; alle Zellen: Wert 5,0, alles beobachtet."""
    zeit = pd.to_datetime([f"{m}-01" for m in monate])
    breite = 90 - g.ZELLE / 2 - g.ZELLE * np.arange(g.BREITE)
    laenge = -180 + g.ZELLE / 2 + g.ZELLE * np.arange(g.LAENGE)
    form = (len(monate), g.BREITE, g.LAENGE)
    ds = xr.Dataset(
        {
            "allangle_mittel_beobachtet": (("zeit", "breite", "laenge"), np.full(form, 5.0, dtype="float32")),
            "allangle_gueltige_pixel": (("zeit", "breite", "laenge"), np.full(form, 3600, dtype="int16")),
            "allangle_aufgefuellt_pixel": (("zeit", "breite", "laenge"), np.zeros(form, dtype="int16")),
            "monat_fertig": (("zeit",), np.array(status, dtype="int8")),
        },
        coords={"zeit": zeit, "breite": breite, "laenge": laenge},
    )
    return ds


def _setze(ds, monat, lat, lon, **werte):
    z, s = g.zelle_von(lat, lon)
    i = [str(t)[:7] for t in ds.zeit.values].index(monat)
    for name, wert in werte.items():
        ds[name].values[i, z, s] = wert
    return z, s


# ---------------------------------------------------------------- Monate


def test_nur_fertige_und_region_monate_vor_2023_werden_angezeigt():
    ds = _wuerfel(["2018-01", "2018-02", "2018-03", "2018-04", "2022-12", "2023-01", "2024-01"], [1, 2, 0, 4, 1, 1, 4])
    assert g.anzeigbare_monate(ds) == ["2018-01", "2018-04", "2022-12"]


def test_status_2_und_3_gelten_nie_als_fertig():
    ds = _wuerfel(["2018-01", "2018-02"], [2, 3])
    assert g.anzeigbare_monate(ds) == []


def test_endtestzeitraum_wird_beim_kodieren_verweigert():
    ds = _wuerfel(["2023-01"], [1])
    with pytest.raises(g.ExportFehler, match="Endtest"):
        g.kodiere_monat(ds, "2023-01")


def test_falsches_gitter_bricht_ab():
    ds = _wuerfel(["2018-01"], [1]).isel(breite=slice(0, 700))
    with pytest.raises(g.ExportFehler, match="Gitter"):
        g.pruefe_gitter(ds)


def test_gitter_des_kuenstlichen_wuerfels_ist_gueltig():
    g.pruefe_gitter(_wuerfel(["2018-01"], [1]))


# ---------------------------------------------------------------- Kodierung


def test_fehlende_daten_werden_nie_zu_0():
    ds = _wuerfel(["2018-01"], [1])
    # keine gültigen Pixel (keine Kachel / Polarsommer / Fehlwert): Würfel hat NaN und 0
    zk, sk = _setze(ds, "2018-01", 85.1, 0.1, allangle_mittel_beobachtet=np.nan, allangle_gueltige_pixel=0)
    e = g.kodiere_monat(ds, "2018-01")
    code, anteil = g.entpacke_monat(e)
    assert anteil[zk, sk] == g.ANTEIL_KEINE_DATEN
    assert code[zk, sk] == 0  # trägt keinen Wert; die Klasse steht in `anteil`
    assert e["statistik"]["zellen_keine_daten"] == 1
    # echte Dunkelheit bleibt gemessen dunkel (Wert 0, 100 % beobachtet)
    zd, sd = _setze(ds, "2018-01", 30.0, -40.0, allangle_mittel_beobachtet=0.0)
    code, anteil = g.entpacke_monat(g.kodiere_monat(ds, "2018-01"))
    assert anteil[zd, sd] == 100 and code[zd, sd] == 0


def test_unter_50_prozent_beobachtet_ist_datenlage_unzureichend():
    ds = _wuerfel(["2018-01"], [1])
    # Grönland im März: 3600 gültig, aber 3592 aufgefüllt (8 beobachtet)
    z, s = _setze(ds, "2018-01", 72.1, -40.1, allangle_aufgefuellt_pixel=3592, allangle_mittel_beobachtet=0.0)
    z2, s2 = _setze(ds, "2018-01", 10.0, 10.0, allangle_aufgefuellt_pixel=1800)  # genau 50 %: zeigbar
    z3, s3 = _setze(ds, "2018-01", 11.0, 10.0, allangle_aufgefuellt_pixel=1801)  # knapp darunter
    e = g.kodiere_monat(ds, "2018-01")
    code, anteil = g.entpacke_monat(e)
    assert anteil[z, s] == 0 and code[z, s] == 0
    assert anteil[z2, s2] == 50 and code[z2, s2] == 500
    assert anteil[z3, s3] == 49 and code[z3, s3] == 0
    assert e["statistik"]["zellen_datenlage_unzureichend"] == 2


def test_werte_bleiben_auf_001_genau_erhalten():
    ds = _wuerfel(["2018-01"], [1])
    z, s = _setze(ds, "2018-01", 52.52, 13.40, allangle_mittel_beobachtet=13.939)
    z2, s2 = _setze(ds, "2018-01", 48.86, 2.35, allangle_mittel_beobachtet=62.478)
    code, _ = g.entpacke_monat(g.kodiere_monat(ds, "2018-01"))
    assert code[z, s] / g.WERT_SKALA == pytest.approx(13.94)
    assert code[z2, s2] / g.WERT_SKALA == pytest.approx(62.48)


def test_negative_und_zu_hohe_werte_werden_gezaehlt():
    ds = _wuerfel(["2018-01"], [1])
    _setze(ds, "2018-01", 1.0, 1.0, allangle_mittel_beobachtet=-0.3)
    z, s = _setze(ds, "2018-01", 2.0, 2.0, allangle_mittel_beobachtet=5000.0)
    e = g.kodiere_monat(ds, "2018-01")
    code, _ = g.entpacke_monat(e)
    assert e["statistik"]["zellen_negativ_auf_0_gesetzt"] == 1
    assert e["statistik"]["zellen_oben_begrenzt"] == 1
    assert code[z, s] == g.WERT_MAX_CODE
    assert e["wert_max_code"] == g.WERT_MAX_CODE


def test_zeigbare_zelle_ohne_mittelwert_ist_ein_fehler():
    ds = _wuerfel(["2018-01"], [1])
    _setze(ds, "2018-01", 5.0, 5.0, allangle_mittel_beobachtet=np.nan)  # 3600 gültig, aber NaN
    with pytest.raises(g.ExportFehler, match="ohne Mittelwert"):
        g.kodiere_monat(ds, "2018-01")


def test_kontrollzellen_und_pruefsumme_passen_zu_den_daten():
    ds = _wuerfel(["2018-01"], [1])
    _setze(ds, "2018-01", 85.1, 0.1, allangle_mittel_beobachtet=np.nan, allangle_gueltige_pixel=0)
    e = g.kodiere_monat(ds, "2018-01")
    code, anteil = g.entpacke_monat(e)
    for k in e["kontrolle"].values():
        assert code[k["zeile"], k["spalte"]] == k["wert_code"]
        assert anteil[k["zeile"], k["spalte"]] == k["anteil"]
    assert e["kontrolle"]["Nordpolarmeer 85° N"]["anteil"] == g.ANTEIL_KEINE_DATEN
    assert hashlib.sha256(code.tobytes() + anteil.tobytes()).hexdigest() == e["sha256_roh"]


def test_zelle_von_nutzt_nordrand_und_westrand():
    assert g.zelle_von(89.9, -179.9) == (0, 0)
    assert g.zelle_von(-89.9, 179.9) == (719, 1439)
    assert g.zelle_von(52.52, 13.40) == (149, 773)  # Zeile 149: 52,75° bis 52,50° N (Mitte 52,625°)


# ---------------------------------------------------------------- Einheiten


def _einheiten_ordner(tmp_path, n_manifest=None, verfaelschen=False):
    """Kleine Einheitentabelle im Format von laender/zell_einheiten (Umrisse in EPSG:6933)."""
    from pyproj import Transformer
    from shapely.geometry import box
    from shapely.ops import transform

    nach6933 = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    zeilen = []
    for eid, name, ebene, kat, m49, un_name, bb in [
        ("land_UKR", "Ukraine", "Land (Grenzdatei)", "", "804", "Ukraine", (22, 45, 40, 52)),
        ("krim", "Krim", "Sondereinheit", "umstritten, besetzt/Konfliktzone", "804", "Ukraine", (32.5, 44.4, 36.6, 46.2)),
        ("klein", "Kleine Insel", "Sondereinheit (automatisch)", "umstritten", None, None, (10.0, 10.0, 10.05, 10.05)),
    ]:
        zeilen.append({
            "einheit_id": eid, "name": name, "ebene": ebene, "herkunft_umriss": "Test", "kategorien": kat,
            "un_m49": m49, "un_name": un_name, "un_art": "ausdrücklich" if m49 else "unklar",
            "un_beleg": "Beleg " + eid, "un_status": "", "beansprucht_von": "Ukraine" if eid == "krim" else "",
            "verwaltet_von": "Russland (Stand Mai 2022)" if eid == "krim" else "", "anerkennung": "",
            "gueltig": "", "weltbank_code": None, "weltbank_art": "unklar", "umriss_hinweis": None,
            "flaeche_km2": 1.0, "umriss_wkb": transform(nach6933, box(*bb)).wkb,
        })
    pd.DataFrame(zeilen).to_parquet(tmp_path / "einheiten.parquet")
    pd.DataFrame({"zeile": [1, 2, 3], "spalte": [1, 2, 3], "einheit_id": ["land_UKR", "krim", "klein"],
                  "anteil": [1.0, 1.0, 0.02]}).to_parquet(tmp_path / "zuordnung.parquet")
    manifest = {
        "erstellt_utc": "2026-09-25T23:10:39Z",
        "ergebnis": {"einheiten": n_manifest if n_manifest is not None else 3},
        "dateien": {n: g._sha256_datei(tmp_path / n) for n in ("einheiten.parquet", "zuordnung.parquet")},
        "quellen": {"natural_earth_laender": {"url": "u", "version": "5.1.1", "sha256": "x"}},
    }
    if verfaelschen:
        manifest["dateien"]["einheiten.parquet"] = "0" * 64
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path


def test_einheiten_ohne_manifest_gelten_als_fehlend(tmp_path):
    ok, grund = g.pruefe_einheiten(tmp_path)
    assert not ok and "fehlt" in grund


def test_einheiten_mit_falscher_pruefsumme_gelten_als_unvollstaendig(tmp_path):
    ok, grund = g.pruefe_einheiten(_einheiten_ordner(tmp_path, verfaelschen=True))
    assert not ok and "Prüfsumme" in grund


def test_einheiten_mit_falscher_anzahl_gelten_als_unvollstaendig(tmp_path):
    ok, grund = g.pruefe_einheiten(_einheiten_ordner(tmp_path, n_manifest=324))
    assert not ok and "324" in grund


def test_vollstaendige_einheiten_werden_angenommen(tmp_path):
    ok, _ = g.pruefe_einheiten(_einheiten_ordner(tmp_path))
    assert ok


def test_geojson_uebernimmt_nur_angaben_aus_der_tabelle(tmp_path):
    gj = g.einheiten_geojson(_einheiten_ordner(tmp_path))
    f = {x["properties"]["einheit_id"]: x for x in gj["features"]}
    krim = f["krim"]["properties"]
    assert krim["un_name"] == "Ukraine" and krim["un_m49"] == "804"
    assert krim["verwaltet_von"] == "Russland (Stand Mai 2022)"
    assert krim["sondereinheit"] is True and krim["hauptkategorie"] == "besetzt/Konfliktzone"
    assert set(krim) == set(g.EINHEITEN_ANZEIGE) | {"zellen_summe_anteile", "kleiner_als_eine_zelle", "sondereinheit", "hauptkategorie"}
    assert f["klein"]["properties"]["un_m49"] == ""  # fehlend bleibt leer, wird nicht ergänzt
    assert f["klein"]["properties"]["kleiner_als_eine_zelle"] is True
    assert f["klein"]["geometry"] is not None  # winzige Einheit verschwindet nicht
    # Umriss zurück in Grad (WGS 84)
    xs = [p[0] for p in f["krim"]["geometry"]["coordinates"][0]]
    ys = [p[1] for p in f["krim"]["geometry"]["coordinates"][0]]
    assert min(xs) == pytest.approx(32.5, abs=0.02) and max(ys) == pytest.approx(46.2, abs=0.02)


def test_hauptkategorie():
    assert g._hauptkategorie("umstritten, besetzt/Konfliktzone") == "besetzt/Konfliktzone"
    assert g._hauptkategorie("umstritten") == "umstritten"
    assert g._hauptkategorie("Sonderstatus/autonom") == "Sonderstatus/autonom"
    assert g._hauptkategorie("") == ""


# ---------------------------------------------------------------- Gesamtablauf


def _lies_js(pfad):
    text = pfad.read_text(encoding="utf-8")
    m = re.search(r"= (\{.*\});\s*$", text, re.S)
    return json.loads(m.group(1))


@pytest.fixture
def fake_ssd(tmp_path, monkeypatch):
    daten = tmp_path / "ssd"
    (daten / "cube").mkdir(parents=True)
    ds = _wuerfel(["2018-01", "2018-02", "2023-01"], [1, 2, 1])
    ds.to_zarr(daten / "cube" / g.WUERFEL)
    monkeypatch.setattr(io, "aleph_data_dir", lambda: daten)
    monkeypatch.setattr(io, "wuerfel_pfad", lambda *t: daten.joinpath("cube", *t))
    return daten


def test_export_ohne_einheiten_zeigt_keine_grenzen(fake_ssd, tmp_path):
    ziel = tmp_path / "web_daten"
    ziel.mkdir()
    (ziel / "nachtlicht_2017-12.js").write_text("veraltet")  # darf nicht stehen bleiben
    d = g.exportiere(ziel)
    assert d["angezeigt"] == ["2018-01"]
    assert d["fertig_gesperrt_endtest"] == ["2023-01"]
    assert sorted(p.name for p in ziel.glob("nachtlicht_*.js")) == ["nachtlicht_2018-01.js"]
    eh = _lies_js(ziel / "einheiten.js")
    assert eh["verfuegbar"] is False and "geojson" not in eh
    stand = _lies_js(ziel / "datenstand.js")
    assert stand["einheiten_verfuegbar"] is False and stand["evidenzstufe"] == "beobachtet"


def test_export_mit_einheiten(fake_ssd, tmp_path):
    ordner = fake_ssd.joinpath(*g.EINHEITEN_ORDNER)
    ordner.mkdir(parents=True)
    _einheiten_ordner(ordner)
    ziel = tmp_path / "web_daten"
    g.exportiere(ziel)
    eh = _lies_js(ziel / "einheiten.js")
    assert eh["verfuegbar"] is True and len(eh["geojson"]["features"]) == 3
    # Die künstliche Tabelle reicht nicht für Länderwerte: sichtbar „nicht verfügbar“ mit Grund, Globus läuft weiter.
    lw = _lies_js(ziel / "laender.js")
    assert lw["verfuegbar"] is False and lw["grund"].startswith("Länderwerte nicht berechnet")


def test_gesperrte_monate_stehen_in_keiner_datei_der_oberflaeche(fake_ssd, tmp_path):
    """2023–2025: nicht auswählbar UND nicht sichtbar – auch nicht als Name oder Zählung (Auftrag 2026-09-28)."""
    ziel = tmp_path / "web_daten"
    d = g.exportiere(ziel)
    assert d["fertig_gesperrt_endtest"] == ["2023-01"]  # nur die Konsole erfährt es
    for datei in ziel.iterdir():
        text = datei.read_text(encoding="utf-8")
        for jahr in ("2023-", "2024-", "2025-"):
            assert jahr not in text, (datei.name, jahr)
    stand = _lies_js(ziel / "datenstand.js")
    assert stand["monate_gesamt"] == 2 and stand["status_zaehlung"] == {"1": 1, "2": 1}
    assert "fertig_gesperrt_endtest" not in stand


def test_seite_filtert_gesperrte_monate_zusaetzlich():
    js = (Path(__file__).resolve().parents[1] / "web" / "globus.js").read_text(encoding="utf-8")
    assert 'var GESPERRT_AB = "2023-01";' in js
    assert "DS.angezeigt = (DS.angezeigt || []).filter(function (m) { return m < GESPERRT_AB; });" in js
    assert "fertig_gesperrt_endtest" not in js


def test_pruefansicht_markiert_und_verweigert_endtest(fake_ssd, tmp_path):
    d = g.exportiere(tmp_path / "pruef", ["2018-02"])
    assert d["pruefansicht"] is True and d["angezeigt"] == ["2018-02"]
    assert _lies_js(tmp_path / "pruef" / "datenstand.js")["pruefansicht"] is True
    with pytest.raises(g.ExportFehler):
        g.exportiere(tmp_path / "pruef2", ["2023-01"])


def test_pruefansicht_darf_nicht_nach_web_daten(fake_ssd):
    assert g.main(["--pruefansicht", "2018-02"]) == 2


# ---------------------------------------------------------------- echte Daten (nur mit SSD)


def _ssd_da():
    try:
        return (io.aleph_data_dir() / "laender" / "zell_einheiten" / "manifest.json").exists()
    except Exception:
        return False


@pytest.mark.skipif(not _ssd_da(), reason="SSD mit Einheitentabelle nicht angeschlossen")
def test_echte_einheitentabelle_krim_taiwan_groenland():
    ordner = io.aleph_data_dir().joinpath(*g.EINHEITEN_ORDNER)
    ok, grund = g.pruefe_einheiten(ordner)
    assert ok, grund
    gj = g.einheiten_geojson(ordner)
    f = {x["properties"]["einheit_id"]: x["properties"] for x in gj["features"]}
    assert len(f) == 326  # seit 2026-09-26 mit Sabah und Süd-Belize
    assert f["krim"]["sondereinheit"] and f["krim"]["un_m49"] == "804" and f["krim"]["un_name"] == "Ukraine"
    assert f["taiwan"]["sondereinheit"] and f["taiwan"]["un_m49"] == "156"
    assert f["groenland"]["hauptkategorie"] == "Sonderstatus/autonom"
    for eid in ("tibet", "westjordanland", "gaza", "donezk_2014", "luhansk_2014", "kosovo", "nordzypern"):
        assert f[eid]["sondereinheit"], eid
    assert sum(1 for p in f.values() if p["sondereinheit"]) == 89
    assert f["sued_belize"]["hauptkategorie"] == "umstritten" and f["sued_belize"]["un_art"] == "unklar"
    assert f["sabah_north_borneo"]["beansprucht_von"].startswith("Philippinen")
    assert f["sabah_north_borneo"]["name"] == "Ost-Sabah (von den Philippinen beansprucht)"  # Tabelle neu gebaut 2026-09-28


# ---------------------------------------------------------------- Zustand 4 (nur Afrika-Europa-Asien)


def test_nicht_geladene_zellen_bekommen_eigene_kennung_und_nie_0():
    ds = _wuerfel(["2018-01"], [4])
    maske = np.zeros((g.BREITE, g.LAENGE), dtype=bool)
    maske[:, :720] = True  # westliche Hälfte „noch nicht geladen“
    # lies_monate_mit_region liefert dort NaN in allen Variablen (auch Zählern)
    for v in ("allangle_mittel_beobachtet", "allangle_gueltige_pixel", "allangle_aufgefuellt_pixel"):
        ds[v] = ds[v].astype("float64")
        ds[v].values[0][maske] = np.nan
    e = g.kodiere_monat(ds, "2018-01", nicht_geladen=maske)
    code, anteil = g.entpacke_monat(e)
    assert (anteil[maske] == g.ANTEIL_NICHT_GELADEN).all() and (code[maske] == 0).all()
    assert (anteil[~maske] == 100).all() and (code[~maske] == 500).all()
    st = e["statistik"]
    assert st["zellen_nicht_geladen"] == int(maske.sum())
    assert st["zellen_keine_daten"] == 0 and st["zellen_datenlage_unzureichend"] == 0
    assert e["anteil_nicht_geladen"] == 254 != g.ANTEIL_KEINE_DATEN


def test_export_zeigt_region_monat_mit_zustand(fake_ssd, tmp_path, monkeypatch):
    ds = _wuerfel(["2018-01", "2018-02"], [4, 1])
    import shutil
    shutil.rmtree(fake_ssd / "cube" / g.WUERFEL)
    ds.to_zarr(fake_ssd / "cube" / g.WUERFEL)
    maske = np.zeros((g.BREITE, g.LAENGE), dtype=bool)
    maske[:10, :10] = True
    aufrufe = []

    def region_monat(monat):
        aufrufe.append(monat)
        return ds, maske

    monkeypatch.setattr(g, "_region_monat", region_monat)
    ziel = tmp_path / "web_daten"
    d = g.exportiere(ziel)
    assert aufrufe == ["2018-01"]  # nur der Zustand-4-Monat über die geprüfte Region-Lesefunktion
    assert d["angezeigt"] == ["2018-01", "2018-02"]
    zustand = {e["monat"]: e["zustand_text"] for e in d["monate"]}
    assert zustand == {"2018-01": "nur Afrika-Europa-Asien", "2018-02": "vollständig"}
    text = (ziel / "nachtlicht_2018-01.js").read_text(encoding="utf-8")
    eintrag = json.loads(text.split('["2018-01"] = ', 1)[1].rstrip().rstrip(";"))
    assert eintrag["zustand"] == 4
    code, anteil = g.entpacke_monat(eintrag)
    assert (anteil[:10, :10] == g.ANTEIL_NICHT_GELADEN).all()


def test_export_tauscht_erst_am_ende(fake_ssd, tmp_path, monkeypatch):
    """Bricht der Export ab, bleibt der alte, stimmige Stand stehen."""
    ziel = tmp_path / "web_daten"
    g.exportiere(ziel)
    vorher = sorted(p.name for p in ziel.iterdir())
    monkeypatch.setattr(g, "kodiere_monat", lambda *a, **k: (_ for _ in ()).throw(g.ExportFehler("simuliert")))
    with pytest.raises(g.ExportFehler):
        g.exportiere(ziel)
    assert sorted(p.name for p in ziel.iterdir()) == vorher
    assert not (tmp_path / "web_daten.neu").exists()


@pytest.mark.echter_katalog
def test_polkappen_ohne_nasa_kacheln_sind_keine_daten_statt_nicht_geladen(monkeypatch):
    """Kacheln, die NASA nie liefert (nicht in der Referenzliste, z. B. v00 = 80–90° N),
    dürfen nicht „noch nicht geladen“ heißen – sie kommen nie (Plausibilitätsprüfung 2026-09-26)."""
    from aleph.layers import vnp46a3

    alles = xr.Dataset({"nicht_geladen": (("zeit", "lat", "lon"), np.ones((1, g.BREITE, g.LAENGE), dtype=bool))})
    monkeypatch.setattr(vnp46a3, "lies_monate_mit_region", lambda *a, **k: alles)
    _, maske = g._region_monat("2018-01")
    assert not maske[:40].any()          # v00: 90–80° N, keine NASA-Kachel
    assert not maske[-80:].any()         # v16/v17: 70–90° S
    assert maske[4 * 40 + 20, 10 * 40 + 20]   # h10v04 (Nordamerika) ist geliefert
    assert int(maske.sum()) == 540 * 1600


# ---------------------------------------------------------------- Stichproben am echten Export (web/daten)

WEB_DATEN = Path(__file__).resolve().parents[1] / "web" / "daten"


def _web_daten_da():
    return (WEB_DATEN / "datenstand.js").exists() and any(WEB_DATEN.glob("nachtlicht_2019-*.js"))


def _monat_aus_web(monat):
    text = (WEB_DATEN / f"nachtlicht_{monat}.js").read_text(encoding="utf-8")
    return json.loads(text.split(f'["{monat}"] = ', 1)[1].rstrip().rstrip(";"))


@pytest.mark.skipif(not _web_daten_da(), reason="web/daten nicht erzeugt (Globus aktualisieren)")
def test_echter_export_24_monate_und_2024_gesperrt():
    stand = _lies_js(WEB_DATEN / "datenstand.js")
    soll = [f"{j}-{m:02d}" for j in (2018, 2019) for m in range(1, 13)]
    # Alle 24 Monate 2018–2019 müssen da sein; später fertige Monate vor 2023 dürfen dazukommen.
    assert set(soll) <= set(stand["angezeigt"]) and all(m < "2023-01" for m in stand["angezeigt"])
    assert sorted(p.name for p in WEB_DATEN.glob("nachtlicht_*.js")) == [f"nachtlicht_{m}.js" for m in stand["angezeigt"]]
    for datei in WEB_DATEN.iterdir():
        text = datei.read_text(encoding="utf-8")
        assert "2024-01" not in text and "2023-" not in text and "2025-" not in text, datei.name


@pytest.mark.skipif(not _web_daten_da(), reason="web/daten nicht erzeugt (Globus aktualisieren)")
@pytest.mark.parametrize("monat", ["2018-06", "2019-06"])
def test_echter_export_stichproben(monat):
    code, anteil = g.entpacke_monat(_monat_aus_web(monat))

    def an(lat, lon):
        z, s = g.zelle_von(lat, lon)
        return code[z, s] / g.WERT_SKALA, int(anteil[z, s])

    for ort, (lat, lon), lo, hi in (("Berlin", (52.52, 13.40), 3, 80), ("Paris", (48.86, 2.35), 20, 200),
                                    ("Kairo", (30.05, 31.24), 15, 200)):
        wert, a = an(lat, lon)
        assert 50 <= a <= 100 and lo <= wert <= hi, (ort, wert, a)
    wert, a = an(23.0, 12.0)  # Sahara
    assert 50 <= a <= 100 and wert < 0.5
    assert an(5.0, -75.0)[1] == g.ANTEIL_NICHT_GELADEN  # Kolumbien: noch nicht geladen
    assert an(40.0, -100.0)[1] == g.ANTEIL_NICHT_GELADEN  # USA
    assert an(85.1, 0.1)[1] == g.ANTEIL_KEINE_DATEN  # Arktis: keine Daten, nicht „nicht geladen“


@pytest.mark.skipif(not _web_daten_da(), reason="web/daten nicht erzeugt (Globus aktualisieren)")
def test_echter_export_ost_sabah_auf_dem_globus():
    eh = _lies_js(WEB_DATEN / "einheiten.js")
    namen = {f["properties"]["einheit_id"]: f["properties"]["name"] for f in eh["geojson"]["features"]}
    assert namen["sabah_north_borneo"] == "Ost-Sabah (von den Philippinen beansprucht)"
