"""Prüft das Laden der Ländergrenzen (Natural Earth) mit einer nachgebauten Datei, ohne Netz und ohne echte SSD.

Die letzten Tests (`test_echt_*`) nutzen die echten, geladenen Daten und werden übersprungen,
wenn die SSD nicht angeschlossen oder Natural Earth noch nicht geladen ist.
"""

import json
import zipfile

import geopandas as gpd
import pytest
import requests
from shapely.geometry import Polygon, box

from aleph.core import io
from aleph.layers import natural_earth as ne


def einheit(adm0, name, iso_a3, iso_a3_eh, geometrie, wb_a3="-99", typ="Sovereign country"):
    return {
        "ADM0_A3": adm0, "ADMIN": name, "NAME_DE": name, "TYPE": typ, "SOV_A3": adm0,
        "ISO_A3": iso_a3, "ISO_A3_EH": iso_a3_eh, "WB_A3": wb_a3, "geometry": geometrie,
    }


# Kleine Welt mit den Eigenheiten der echten Datei: Frankreich mit ISO_A3 „-99“, Kosovo ohne Code,
# Jersey/Guernsey, Taiwan ohne Weltbank-Gegenstück, Ägypten mit sich selbst berührender Randlinie.
AEGYPTEN_SELBSTBERUEHREND = Polygon([(25, 22), (35, 22), (35, 32), (30, 32), (32, 29), (30, 26), (28, 29), (30, 32), (25, 32)])
EINHEITEN = [
    einheit("EGY", "Egypt", "EGY", "EGY", AEGYPTEN_SELBSTBERUEHREND),
    einheit("DEU", "Germany", "DEU", "DEU", box(6, 47, 15, 55), wb_a3="DEU"),
    einheit("FRA", "France", "-99", "FRA", box(-5, 42, 6, 51), wb_a3="FRA", typ="Country"),
    einheit("KOS", "Kosovo", "-99", "-99", box(20, 42, 21, 43), wb_a3="KSV", typ="Disputed"),
    einheit("JEY", "Jersey", "JEY", "JEY", box(-2.3, 49.1, -2.0, 49.3), wb_a3="CHI", typ="Country"),
    einheit("GGY", "Guernsey", "GGY", "GGY", box(-2.7, 49.4, -2.5, 49.5), wb_a3="CHI", typ="Country"),
    einheit("TWN", "Taiwan", "TWN", "TWN", box(120, 22, 122, 25)),
]
WELTBANK = {"EGY": "Egypt, Arab Rep.", "DEU": "Germany", "FRA": "France", "XKX": "Kosovo", "CHI": "Channel Islands", "NOR": "Norway"}


def baue_zip(pfad, einheiten=EINHEITEN, version=ne.VERSION):
    """Schreibt eine Zip-Datei im Aufbau der Natural-Earth-Datei (Shapefile plus VERSION.txt)."""
    ordner = pfad.parent / "shp"
    ordner.mkdir(exist_ok=True)
    stamm = ne.DATEI.removesuffix(".zip")
    gpd.GeoDataFrame(einheiten, crs="EPSG:4326").to_file(ordner / f"{stamm}.shp")
    with zipfile.ZipFile(pfad, "w") as z:
        for datei in ordner.iterdir():
            z.write(datei, datei.name)
        z.writestr(f"{stamm}.VERSION.txt", version + "\n")
    return pfad


@pytest.fixture(autouse=True)
def umgebung(tmp_path, monkeypatch):
    daten = tmp_path / "daten"
    daten.mkdir()
    monkeypatch.setattr(io, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("ALEPH_DATA_DIR", str(daten))
    monkeypatch.setattr(io, "freier_speicher_gb", lambda pfad: 500.0)
    monkeypatch.setattr(ne.time, "sleep", lambda s: None)
    monkeypatch.setattr(ne, "ANZAHL_LAUT_QUELLE", len(EINHEITEN))


def falscher_server(monkeypatch, tmp_path, **zip_args):
    """Ersetzt den Download: kopiert eine nachgebaute Zip-Datei. Liefert die Liste der Aufrufe."""
    quelle = baue_zip(tmp_path / "quelle.zip", **zip_args)
    aufrufe = []

    def hole(url, ziel):
        aufrufe.append(url)
        ziel.write_bytes(quelle.read_bytes())
        return {"Last-Modified": "Fri, 13 May 2022 05:20:49 GMT"}

    monkeypatch.setattr(ne, "_hole_datei", hole)
    return aufrufe


def test_download_schreibt_manifest_und_liest_zurueck(monkeypatch, tmp_path):
    falscher_server(monkeypatch, tmp_path)
    ordner = ne.download()
    manifest = json.loads((ordner / "manifest.json").read_text())
    assert ordner.name == ne.VERSION
    assert manifest["version"] == ne.VERSION and manifest["anzahl_einheiten"] == len(EINHEITEN)
    assert manifest["sha256"] == ne._pruefsumme(ordner / ne.DATEI)
    assert manifest["umriss_repariert"] == ["EGY"]
    assert not ordner.with_name(ordner.name + ".tmp").exists()
    laender = ne.lade_laender()
    assert len(laender) == len(EINHEITEN)
    assert laender.geometry.is_valid.all()


def test_code_feld_und_korrekturen(monkeypatch, tmp_path):
    falscher_server(monkeypatch, tmp_path)
    ne.download()
    codes = ne.lade_laender().set_index("ADM0_A3")["land_iso3"]
    assert codes["FRA"] == "FRA"  # ISO_A3 ist „-99“, ISO_A3_EH trägt den Code
    assert codes["KOS"] == "XKX"
    assert codes["JEY"] == "CHI" and codes["GGY"] == "CHI"
    assert codes["TWN"] == "TWN"


def test_platzhalter_wird_leer_nicht_minus99(monkeypatch, tmp_path):
    einheiten = EINHEITEN + [einheit("SOL", "Somaliland", "-99", "-99", box(43, 8, 48, 11))]
    monkeypatch.setattr(ne, "ANZAHL_LAUT_QUELLE", len(einheiten))
    falscher_server(monkeypatch, tmp_path, einheiten=einheiten)
    ne.download()
    codes = ne.lade_laender().set_index("ADM0_A3")["land_iso3"]
    assert codes.isna()["SOL"]
    assert (codes != ne.PLATZHALTER).all()


def test_zweiter_download_laedt_nicht_erneut(monkeypatch, tmp_path):
    aufrufe = falscher_server(monkeypatch, tmp_path)
    ne.download()
    ne.download()
    assert len(aufrufe) == 1


def test_falsche_version_bricht_ab_und_hinterlaesst_nichts(monkeypatch, tmp_path):
    falscher_server(monkeypatch, tmp_path, version="5.2.0")
    with pytest.raises(ne.NaturalEarthFehler, match="Version 5.2.0"):
        ne.download()
    assert not ne.ordner().exists()
    assert not ne.ordner().with_name(ne.VERSION + ".tmp").exists()


def test_falsche_anzahl_bricht_ab(monkeypatch, tmp_path):
    falscher_server(monkeypatch, tmp_path, einheiten=EINHEITEN[:-1])
    with pytest.raises(ne.NaturalEarthFehler, match="laut Quelle"):
        ne.download()
    assert not ne.ordner().exists()


def test_keine_zip_datei_bricht_ab(monkeypatch):
    monkeypatch.setattr(ne, "_hole_datei", lambda url, ziel: ziel.write_bytes(b"<html>Fehlerseite</html>") or {})
    with pytest.raises(ne.NaturalEarthFehler, match="keine gültige Zip"):
        ne.download()
    assert not ne.ordner().exists()


def test_ordner_ohne_manifest_wird_nicht_ueberschrieben(monkeypatch, tmp_path):
    falscher_server(monkeypatch, tmp_path)
    ne.ordner().mkdir(parents=True)
    with pytest.raises(ne.NaturalEarthFehler, match="ohne Manifest"):
        ne.download()


def test_veraenderte_datei_wird_erkannt(monkeypatch, tmp_path):
    falscher_server(monkeypatch, tmp_path)
    ordner = ne.download()
    with open(ordner / ne.DATEI, "ab") as datei:
        datei.write(b"x")
    with pytest.raises(ne.NaturalEarthFehler, match="Prüfsumme"):
        ne.lade_laender()


def test_nicht_geladen_meldet_klar():
    with pytest.raises(ne.NaturalEarthFehler, match="nicht geladen"):
        ne.lade_laender()


def test_reparatur_mit_flaechenaenderung_bricht_ab(monkeypatch, tmp_path):
    schleife = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])  # Achterform: Fläche 0 vorher, 2 nachher
    einheiten = EINHEITEN[:-1] + [einheit("TWN", "Taiwan", "TWN", "TWN", schleife)]
    falscher_server(monkeypatch, tmp_path, einheiten=einheiten)
    with pytest.raises(ne.NaturalEarthFehler, match="ändert die Fläche"):
        ne.download()


# --- Herunterladen: Fehlerverhalten ------------------------------------------------


class Antwort:
    def __init__(self, status, inhalt=b""):
        self.status_code = status
        self.content = inhalt
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_http_404_bricht_sofort_ab(monkeypatch, tmp_path):
    aufrufe = []
    monkeypatch.setattr(ne.requests, "get", lambda url, timeout: aufrufe.append(url) or Antwort(404))
    with pytest.raises(ne.NaturalEarthFehler, match="HTTP 404"):
        ne._hole_datei(ne.URL, tmp_path / "x.zip")
    assert len(aufrufe) == 1


def test_netzfehler_wird_wiederholt_dann_klarer_abbruch(monkeypatch, tmp_path):
    aufrufe = []

    def kaputt(url, timeout):
        aufrufe.append(url)
        raise requests.ConnectionError("keine Verbindung")

    monkeypatch.setattr(ne.requests, "get", kaputt)
    with pytest.raises(ne.NaturalEarthFehler, match="kein Ersatz"):
        ne._hole_datei(ne.URL, tmp_path / "x.zip")
    assert len(aufrufe) == ne.MAX_VERSUCHE
    assert not (tmp_path / "x.zip").exists()


def test_wiederholungen_werden_mit_wachsenden_pausen_gemeldet(monkeypatch, tmp_path, capsys):
    pausen = []
    monkeypatch.setattr(ne.time, "sleep", pausen.append)
    monkeypatch.setattr(ne.requests, "get", lambda url, timeout: (_ for _ in ()).throw(requests.Timeout("x")))
    with pytest.raises(ne.NaturalEarthFehler):
        ne._hole_datei(ne.URL, tmp_path / "x.zip")
    assert pausen == [5, 10, 20]
    fehlerausgabe = capsys.readouterr().err
    assert "Versuch 1/4" in fehlerausgabe and "Versuch 3/4" in fehlerausgabe and "Timeout" in fehlerausgabe


def test_serverfehler_dann_erfolg(monkeypatch, tmp_path):
    antworten = iter([Antwort(503), Antwort(200, b"inhalt")])
    monkeypatch.setattr(ne.requests, "get", lambda url, timeout: next(antworten))
    ne._hole_datei(ne.URL, tmp_path / "x.zip")
    assert (tmp_path / "x.zip").read_bytes() == b"inhalt"


# --- Zuordnung und Abgleich ------------------------------------------------------------


@pytest.fixture
def laender(monkeypatch, tmp_path):
    falscher_server(monkeypatch, tmp_path)
    ne.download()
    return ne.lade_laender()


def test_punkt_in_land_und_im_meer(laender):
    assert ne.land_an_punkt(laender, 13.4, 52.5)["land_iso3"] == "DEU"
    assert ne.land_an_punkt(laender, 26.0, 24.0)["land_iso3"] == "EGY"  # im reparierten Umriss
    assert ne.land_an_punkt(laender, -40.0, 30.0) is None


def test_punkt_im_ausgesparten_teil_liegt_in_keinem_land(laender):
    # Die Schleife des Ägypten-Testumrisses ist eine Aussparung, kein Land.
    assert ne.land_an_punkt(laender, 30.0, 29.0) is None


def test_ueberlappende_einheiten_brechen_ab(laender):
    doppelt = laender.copy()
    doppelt.loc[doppelt["ADM0_A3"] == "TWN", "geometry"] = box(10, 50, 12, 52)  # liegt in Deutschland
    with pytest.raises(ne.NaturalEarthFehler, match="mehreren Einheiten"):
        ne.land_an_punkt(doppelt, 11.0, 51.0)


def test_abgleich_weltbank(laender):
    ergebnis = ne.abgleich_weltbank(laender, WELTBANK)
    assert ergebnis["passend"] == ["CHI", "DEU", "EGY", "FRA", "XKX"]
    assert ergebnis["weltbank_ohne_grenze"] == ["NOR"]
    assert list(ergebnis["grenze_ohne_weltbank"]["ADM0_A3"]) == ["TWN"]
    assert ergebnis["mehrere_einheiten"] == {"CHI": ["Jersey", "Guernsey"]}


# --- Echte Daten (nur mit angeschlossener SSD und geladener Datei) ----------------------


@pytest.fixture
def echte_laender(monkeypatch):
    monkeypatch.undo()  # echte .env und echte SSD statt der Test-Umgebung
    try:
        return ne.lade_laender()
    except (io.SSDNichtGefunden, ne.NaturalEarthFehler) as grund:
        pytest.skip(f"Echte Natural-Earth-Daten nicht verfügbar: {grund}")


@pytest.mark.parametrize(
    "ort, lon, lat, erwartet",
    [
        ("Kairo", 31.2357, 30.0444, "EGY"),
        ("Berlin", 13.4050, 52.5200, "DEU"),
        ("Paris", 2.3522, 48.8566, "FRA"),
        ("Riad", 46.6753, 24.7136, "SAU"),
        ("Atlantik", -40.0, 30.0, None),
    ],
)
def test_echt_punktprobe(echte_laender, ort, lon, lat, erwartet):
    zeile = ne.land_an_punkt(echte_laender, lon, lat)
    assert (None if zeile is None else zeile["land_iso3"]) == erwartet


def test_echt_anzahl_wie_quelle(echte_laender):
    assert len(echte_laender) == 258
