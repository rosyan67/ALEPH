"""Prüft den Weltbank-Layer mit einer vorgetäuschten API (kein Netzzugriff, keine echte SSD)."""

import copy
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from aleph.core import io
from aleph.layers import weltbank as wb

CODES = list(wb.INDIKATOREN)

# Länderliste wie bei der Weltbank: Volkswirtschaften und Aggregate gemischt.
LAENDER = [
    {"id": "DEU", "iso2Code": "DE", "name": "Germany", "region": {"id": "ECS", "value": "Europe & Central Asia"}},
    {"id": "EGY", "iso2Code": "EG", "name": "Egypt, Arab Rep.", "region": {"id": "MEA", "value": "Middle East & North Africa "}},
    {"id": "SAU", "iso2Code": "SA", "name": "Saudi Arabia", "region": {"id": "MEA", "value": "Middle East & North Africa "}},
    {"id": "WLD", "iso2Code": "1W", "name": "World", "region": {"id": "NA", "value": "Aggregates"}},
    {"id": "HIC", "iso2Code": "XD", "name": "High income", "region": {"id": "NA", "value": "Aggregates"}},
]
ISO2 = [land["iso2Code"] for land in LAENDER]


def wert(code, iso2, jahr):
    """Erfundener, von Hand nachrechenbarer Wert je Indikator, Land und Jahr."""
    return (CODES.index(code) + 1) * 1000.0 + (ISO2.index(iso2) + 1) * 100.0 + (jahr - 2000)


class FalscheAPI:
    """Ersetzt _hole_json. `luecken` und `aendere` erlauben gezielte Fehler."""

    def __init__(self, luecken=(), aendere=None):
        self.luecken = set(luecken)  # (code, iso2, jahr) -> Wert None
        self.aendere = aendere  # Funktion (pfad, antwort) -> antwort
        self.aufrufe = []

    def __call__(self, pfad, params):
        self.aufrufe.append((pfad, dict(params)))
        if pfad == "country":
            antwort = [{"page": 1, "pages": 1, "per_page": "500", "total": len(LAENDER)}, copy.deepcopy(LAENDER)]
        else:
            code = pfad.split("/")[-1]
            von, bis = (int(x) for x in params["date"].split(":"))
            daten = []
            for iso2 in ISO2:
                land = LAENDER[ISO2.index(iso2)]
                for jahr in range(bis, von - 1, -1):
                    daten.append(
                        {
                            "indicator": {"id": code, "value": wb.INDIKATOREN[code]["name"]},
                            "country": {"id": iso2, "value": land["name"]},
                            "countryiso3code": land["id"] if land["region"]["value"] != "Aggregates" else "",
                            "date": str(jahr),
                            "value": None if (code, iso2, jahr) in self.luecken else wert(code, iso2, jahr),
                            "unit": "",
                            "obs_status": "",
                            "decimal": 0,
                        }
                    )
            antwort = [{"page": 1, "pages": 1, "per_page": 20000, "total": len(daten), "lastupdated": "2026-07-13"}, daten]
        return self.aendere(pfad, antwort) if self.aendere else antwort


@pytest.fixture(autouse=True)
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("ALEPH_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(io, "freier_speicher_gb", lambda pfad: 500.0)
    monkeypatch.setattr(wb.time, "sleep", lambda s: None)


def lade(monkeypatch, api=None, start=2013, ende=2015, zeit=None):
    api = api or FalscheAPI()
    monkeypatch.setattr(wb, "_hole_json", api)
    ordner = wb.download(start, ende, abrufzeit=zeit or datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc))
    return ordner, api


# --- Abruf und Tabelle --------------------------------------------------------


def test_tabelle_hat_nur_volkswirtschaften_und_richtige_zeilenzahl(monkeypatch):
    ordner, _ = lade(monkeypatch)
    tabelle = wb.baue_tabelle(ordner)
    assert set(tabelle["land_iso3"]) == {"DEU", "EGY", "SAU"}  # WLD und HIC (Aggregate) fehlen
    assert len(tabelle) == 3 * 3 * len(CODES)  # 3 Länder x 3 Jahre x 7 Indikatoren
    assert not tabelle.duplicated(["land_iso3", "jahr", "indikator"]).any()


def test_werte_stimmen_mit_der_antwort_ueberein(monkeypatch):
    ordner, _ = lade(monkeypatch)
    tabelle = wb.baue_tabelle(ordner)

    def hole(iso3, jahr, code):
        zeile = tabelle[(tabelle.land_iso3 == iso3) & (tabelle.jahr == jahr) & (tabelle.indikator == code)]
        assert len(zeile) == 1
        return zeile.iloc[0]

    # DEU steht in ISO2 an Position 0, EGY an 1: BIP real (Code 1) = 1000 + 100/200 + Jahr-2000.
    assert hole("DEU", 2014, "NY.GDP.MKTP.KD").wert == 1000 + 100 + 14
    assert hole("EGY", 2015, "SP.POP.TOTL").wert == 5000 + 200 + 15
    assert hole("SAU", 2013, "NE.IMP.GNFS.KD").wert == 7000 + 300 + 13
    zeile = hole("EGY", 2015, "SP.POP.TOTL")
    assert zeile.kurzname == "bevoelkerung"
    assert zeile.land_name == "Egypt, Arab Rep."
    assert zeile.region == "Middle East & North Africa"  # Leerzeichen am Ende der API-Angabe entfernt
    assert zeile.abruf_utc == "2026-09-23T12:00:00Z"


def test_fehlender_wert_bleibt_leer_und_wird_nie_aufgefuellt(monkeypatch):
    ordner, _ = lade(monkeypatch, FalscheAPI(luecken=[("NY.GDP.MKTP.KD", "EG", 2014)]))
    tabelle = wb.baue_tabelle(ordner)
    zeile = tabelle[(tabelle.land_iso3 == "EGY") & (tabelle.jahr == 2014) & (tabelle.indikator == "NY.GDP.MKTP.KD")].iloc[0]
    assert np.isnan(zeile.wert) and not zeile.hat_wert
    # Nachbarjahre unverändert, also nicht interpoliert
    nachbar = tabelle[(tabelle.land_iso3 == "EGY") & (tabelle.indikator == "NY.GDP.MKTP.KD") & (tabelle.jahr != 2014)]
    assert nachbar.hat_wert.all()
    assert tabelle.hat_wert.sum() == len(tabelle) - 1


def test_land_ohne_jeden_eintrag_wird_als_leer_gefuehrt_und_im_manifest_genannt(monkeypatch):
    def ohne_saudi(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            antwort[1] = [s for s in antwort[1] if s["country"]["id"] != "SA"]
            antwort[0]["total"] = len(antwort[1])
        return antwort

    ordner, _ = lade(monkeypatch, FalscheAPI(aendere=ohne_saudi))
    manifest = json.loads((ordner / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["indikatoren"]["SP.POP.TOTL"]["laender_ohne_eintrag"] == ["SAU"]
    assert manifest["indikatoren"]["NY.GDP.MKTP.KD"]["laender_ohne_eintrag"] == []
    tabelle = wb.baue_tabelle(ordner)
    saudi = tabelle[(tabelle.land_iso3 == "SAU") & (tabelle.indikator == "SP.POP.TOTL")]
    assert len(saudi) == 3 and not saudi.hat_wert.any()


def test_vorlaeufig_ab_2024(monkeypatch):
    ordner, _ = lade(monkeypatch, start=2022, ende=2025)
    tabelle = wb.baue_tabelle(ordner)
    assert set(tabelle[tabelle.vorlaeufig].jahr) == {2024, 2025}
    assert set(tabelle[~tabelle.vorlaeufig].jahr) == {2022, 2023}


def test_anfrage_nutzt_zeitraum_und_eine_seite(monkeypatch):
    _, api = lade(monkeypatch, start=2013, ende=2025)
    _, params = [a for a in api.aufrufe if a[0].endswith("NY.GDP.MKTP.KD")][0]
    assert params["date"] == "2013:2025" and params["per_page"] == 20000 and params["format"] == "json"
    assert len(api.aufrufe) == 1 + len(CODES)  # Länderliste + je Indikator eine Anfrage


def test_tabelle_wird_geschrieben_zurueckgelesen_und_ersetzt(monkeypatch, tmp_path):
    ordner, _ = lade(monkeypatch)
    pfad = wb.to_table(ordner)
    assert pfad == tmp_path / "laender" / "weltbank.parquet"
    gelesen = wb.lese_tabelle()
    pd.testing.assert_frame_equal(gelesen, wb.baue_tabelle(ordner))
    wb.to_table(ordner)  # zweites Mal ersetzt die Datei
    assert sorted(p.name for p in pfad.parent.iterdir()) == ["weltbank.parquet"]  # kein Hilfsrest


def test_to_table_ohne_abruf_meldet_klar(monkeypatch):
    with pytest.raises(wb.WeltbankFehler, match="Kein vollständiger Abruf"):
        wb.to_table()


def test_to_table_nimmt_den_neuesten_abruf(monkeypatch):
    alt, _ = lade(monkeypatch, zeit=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    neu, _ = lade(monkeypatch, zeit=datetime(2026, 9, 23, 0, 0, 0, tzinfo=timezone.utc))
    assert wb.letzter_abruf() == neu and neu != alt
    wb.to_table()
    assert (wb.lese_tabelle().abruf_utc == "2026-09-23T00:00:00Z").all()


# --- Sicherheitsnetz -----------------------------------------------------------


def test_abbruch_hinterlaesst_keinen_abruf_ordner(monkeypatch, tmp_path):
    def kaputt(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            raise wb.WeltbankFehler("Absturz mitten im Abruf")
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=kaputt))
    with pytest.raises(wb.WeltbankFehler, match="Absturz"):
        wb.download(2013, 2015)
    basis = tmp_path / "raw" / "weltbank"
    assert not basis.exists() or list(basis.iterdir()) == []
    assert wb.letzter_abruf() is None


def test_ordner_ohne_manifest_gilt_nicht_als_abruf(monkeypatch, tmp_path):
    (tmp_path / "raw" / "weltbank" / "20260101T000000Z").mkdir(parents=True)
    (tmp_path / "raw" / "weltbank" / "20260202T000000Z.tmp").mkdir(parents=True)
    assert wb.letzter_abruf() is None


def test_bestehender_abruf_wird_nicht_ueberschrieben(monkeypatch):
    lade(monkeypatch)
    with pytest.raises(wb.WeltbankFehler, match="existiert schon"):
        lade(monkeypatch)  # gleicher Zeitpunkt


def test_ungueltiger_zeitraum():
    with pytest.raises(ValueError):
        wb.download(2025, 2013)
    with pytest.raises(ValueError):
        wb.download("2013", 2025)


def test_neubasierung_wird_abgelehnt(monkeypatch):
    def neu_basiert(pfad, antwort):
        if pfad.endswith("NY.GDP.MKTP.KD"):
            for satz in antwort[1]:
                satz["indicator"]["value"] = "GDP (constant 2021 US$)"
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=neu_basiert))
    with pytest.raises(wb.WeltbankFehler, match="neu basiert"):
        wb.download(2013, 2015)


def test_fremder_indikator_wird_abgelehnt(monkeypatch):
    def fremd(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            antwort[1][0]["indicator"]["id"] = "NY.GDP.MKTP.CD"
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=fremd))
    with pytest.raises(wb.WeltbankFehler, match="gehört zu NY.GDP.MKTP.CD"):
        wb.download(2013, 2015)


def test_jahr_ausserhalb_der_anfrage_wird_abgelehnt(monkeypatch):
    def zu_frueh(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            antwort[1][0]["date"] = "1999"
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=zu_frueh))
    with pytest.raises(wb.WeltbankFehler, match="außerhalb"):
        wb.download(2013, 2015)


def test_mehrere_seiten_werden_abgelehnt(monkeypatch):
    def zwei_seiten(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            antwort[0]["pages"] = 2
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=zwei_seiten))
    with pytest.raises(wb.WeltbankFehler, match="2 Seiten"):
        wb.download(2013, 2015)


def test_gesamtzahl_passt_nicht_zur_datensatzzahl(monkeypatch):
    def falsche_summe(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            antwort[0]["total"] += 5
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=falsche_summe))
    with pytest.raises(wb.WeltbankFehler, match="Datensätze"):
        wb.download(2013, 2015)


def test_fehlermeldung_der_api_wird_weitergereicht(monkeypatch):
    def fehler(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            return [{"message": [{"id": "175", "key": "Invalid format", "value": "The indicator was not found."}]}]
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=fehler))
    with pytest.raises(wb.WeltbankFehler, match="not found"):
        wb.download(2013, 2015)


def test_leere_antwort_wird_abgelehnt(monkeypatch):
    def leer(pfad, antwort):
        if pfad.endswith("SP.POP.TOTL"):
            return [{"page": 1, "pages": 1, "per_page": 20000, "total": 0}, None]
        return antwort

    monkeypatch.setattr(wb, "_hole_json", FalscheAPI(aendere=leer))
    with pytest.raises(wb.WeltbankFehler, match="keine Datensätze"):
        wb.download(2013, 2015)


def test_veraenderte_rohdatei_wird_erkannt(monkeypatch):
    ordner, _ = lade(monkeypatch)
    datei = ordner / "SP.POP.TOTL.json"
    datei.write_text(datei.read_text(encoding="utf-8").replace("5", "6", 1), encoding="utf-8")
    with pytest.raises(wb.WeltbankFehler, match="Prüfsumme"):
        wb.baue_tabelle(ordner)


def _mit_manipulierten_rohdaten(monkeypatch, code, aendere):
    """Lädt sauber, ändert dann die Rohdatei und rechnet die Prüfsumme neu (Fehler steckt in den Daten selbst)."""
    ordner, _ = lade(monkeypatch)
    datei = ordner / f"{code}.json"
    daten = json.loads(datei.read_text(encoding="utf-8"))
    aendere(daten)
    neu = wb._schreibe_json(datei, daten)
    manifest = json.loads((ordner / "manifest.json").read_text(encoding="utf-8"))
    manifest["indikatoren"][code]["sha256"] = neu
    (ordner / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return ordner


def test_negativer_wert_wird_abgelehnt(monkeypatch):
    def negativ(daten):
        daten[0]["value"] = -5.0
        daten[0]["country"] = {"id": "DE", "value": "Germany"}

    ordner = _mit_manipulierten_rohdaten(monkeypatch, "SP.POP.TOTL", negativ)
    with pytest.raises(wb.WeltbankFehler, match="negativ"):
        wb.baue_tabelle(ordner)


def test_doppelter_datensatz_wird_abgelehnt(monkeypatch):
    ordner = _mit_manipulierten_rohdaten(monkeypatch, "SP.POP.TOTL", lambda d: d.append(copy.deepcopy(d[0])))
    with pytest.raises(wb.WeltbankFehler, match="doppelter Datensatz"):
        wb.baue_tabelle(ordner)


def test_unbekannte_einheit_wird_abgelehnt(monkeypatch):
    def fremd(daten):
        daten[0]["country"] = {"id": "ZZ", "value": "Nirgendwo"}

    ordner = _mit_manipulierten_rohdaten(monkeypatch, "SP.POP.TOTL", fremd)
    with pytest.raises(wb.WeltbankFehler, match="unbekannte Einheit"):
        wb.baue_tabelle(ordner)


# --- Wiederholung und Zeitlimit -------------------------------------------------


class Antwort:
    def __init__(self, status=200, inhalt=None, json_fehler=False):
        self.status_code = status
        self._inhalt = inhalt
        self._json_fehler = json_fehler

    def raise_for_status(self):
        if self.status_code >= 400:
            raise wb.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._json_fehler:
            raise ValueError("kein JSON")
        return self._inhalt


def test_wiederholung_mit_wachsender_wartezeit_und_zeitlimit(monkeypatch):
    versuche, pausen, zeitlimits = [], [], []

    def get(url, params, timeout):
        versuche.append(url)
        zeitlimits.append(timeout)
        if len(versuche) < 3:
            raise wb.requests.ConnectionError("Verbindung abgebrochen")
        return Antwort(inhalt=["ok"])

    monkeypatch.setattr(wb.requests, "get", get)
    monkeypatch.setattr(wb.time, "sleep", pausen.append)
    assert wb._hole_json("country", {"format": "json"}) == ["ok"]
    assert len(versuche) == 3
    assert pausen == [wb.WARTEZEIT_BASIS_SEKUNDEN, 2 * wb.WARTEZEIT_BASIS_SEKUNDEN]
    assert set(zeitlimits) == {wb.TIMEOUT_SEKUNDEN}  # jeder Versuch hat ein Zeitlimit


def test_endgueltiges_scheitern_nennt_url_und_grund(monkeypatch):
    monkeypatch.setattr(wb.requests, "get", lambda url, params, timeout: (_ for _ in ()).throw(wb.requests.Timeout("zu langsam")))
    with pytest.raises(wb.WeltbankFehler, match=r"nach 4 Versuchen.*zu langsam"):
        wb._hole_json("country", {})


def test_serverfehler_und_ueberlastung_werden_wiederholt_kein_json_ebenso(monkeypatch):
    folge = [Antwort(status=503), Antwort(status=429), Antwort(json_fehler=True), Antwort(inhalt=["ok"])]
    monkeypatch.setattr(wb.requests, "get", lambda url, params, timeout: folge.pop(0))
    assert wb._hole_json("country", {}) == ["ok"]


def test_falsche_anfrage_wird_nicht_wiederholt(monkeypatch):
    aufrufe = []

    def get(url, params, timeout):
        aufrufe.append(1)
        return Antwort(status=400)

    monkeypatch.setattr(wb.requests, "get", get)
    with pytest.raises(wb.WeltbankFehler, match="HTTP 400"):
        wb._hole_json("country", {})
    assert len(aufrufe) == 1


# --- Auswertungshilfen ----------------------------------------------------------


def test_datenlage_zaehlt_fehlende_werte_je_indikator_und_jahr(monkeypatch):
    luecken = [("NY.GDP.MKTP.KD", "EG", 2014), ("NY.GDP.MKTP.KD", "SA", 2014), ("SP.POP.TOTL", "DE", 2015)]
    ordner, _ = lade(monkeypatch, FalscheAPI(luecken=luecken))
    lage = wb.datenlage(wb.baue_tabelle(ordner))
    assert lage.loc["bip_real", 2014] == pytest.approx(2 / 3)  # 2 von 3 Ländern fehlen
    assert lage.loc["bip_real", 2013] == 0.0
    assert lage.loc["bevoelkerung", 2015] == pytest.approx(1 / 3)
    assert lage.loc["bevoelkerung", 2014] == 0.0


def test_konsistenz_bip_pro_kopf_mal_bevoelkerung():
    def zeile(land, jahr, kurz, w):
        return {"land_iso3": land, "jahr": jahr, "kurzname": kurz, "wert": w}

    zeilen = []
    for land, jahr, bip, bev, pro_kopf in [("AAA", 2020, 1000.0, 10.0, 100.0), ("BBB", 2020, 500.0, 5.0, 110.0)]:
        zeilen += [zeile(land, jahr, "bip_real", bip), zeile(land, jahr, "bevoelkerung", bev), zeile(land, jahr, "bip_pro_kopf_real", pro_kopf)]
    zeilen.append(zeile("CCC", 2020, "bip_real", np.nan))  # unvollständiges Land-Jahr zählt nicht
    ergebnis = wb.konsistenz_bip_pro_kopf(pd.DataFrame(zeilen))
    assert ergebnis["n"] == 2
    assert ergebnis["min"] == pytest.approx(1.0)  # 100 * 10 / 1000
    assert ergebnis["max"] == pytest.approx(1.1)  # 110 * 5 / 500


# --- META -----------------------------------------------------------------------


def test_meta_ist_vollstaendig_und_ehrlich():
    for feld in ("name", "bereich", "quelle", "lizenz", "anzeige", "quellenangabe", "native_aufloesung", "zeitraum",
                 "evidenzstufe", "bekannte_schwaechen", "messsystem_bruche", "raeumliche_ebene", "indikatoren"):
        assert wb.META.get(feld), f"META-Feld {feld} fehlt"
    assert "CC BY 4.0" in wb.META["lizenz"]
    assert "Quellenangabe" in wb.META["anzeige"]
    assert "nie auf das Raster verteilt" in wb.META["raeumliche_ebene"]
    # Keine laufenden US-Dollar (würden Inflation messen).
    assert not any(code.endswith(".CD") for code in wb.INDIKATOREN)
    assert set(wb.META["indikatoren"]) == set(wb.INDIKATOREN)


# --- Spalte nicht_verwenden (2026-09-24) ------------------------------------------
#
# Die fünf Länder stehen nicht in der vorgetäuschten Länderliste (DEU, EGY, SAU). Der Mechanismus wird
# deshalb mit einer geänderten Liste geprüft; die echte Liste prüft ein eigener Test.

PRO_KOPF = ("NY.GDP.PCAP.KD", "NY.GDP.PCAP.PP.KD")


def test_nicht_verwenden_markiert_nur_bip_pro_kopf_der_gelisteten_laender(monkeypatch):
    monkeypatch.setattr(wb, "PRO_KOPF_ABWEICHEND", ("EGY",))
    ordner, _ = lade(monkeypatch)
    tabelle = wb.baue_tabelle(ordner)
    markiert = tabelle[tabelle["nicht_verwenden"]]
    assert set(markiert["land_iso3"]) == {"EGY"}
    assert set(markiert["indikator"]) == set(PRO_KOPF)
    assert len(markiert) == 3 * len(PRO_KOPF)  # 3 Jahre x 2 Pro-Kopf-Reihen
    # Andere Indikatoren desselben Landes und alle anderen Länder bleiben unmarkiert.
    egy_rest = tabelle[(tabelle.land_iso3 == "EGY") & ~tabelle.indikator.isin(PRO_KOPF)]
    assert not egy_rest["nicht_verwenden"].any()
    assert not tabelle[tabelle.land_iso3 != "EGY"]["nicht_verwenden"].any()


def test_nicht_verwenden_versteckt_keine_werte(monkeypatch):
    monkeypatch.setattr(wb, "PRO_KOPF_ABWEICHEND", ("EGY",))
    ordner, _ = lade(monkeypatch)
    tabelle = wb.baue_tabelle(ordner)
    zeile = tabelle[(tabelle.land_iso3 == "EGY") & (tabelle.jahr == 2014) & (tabelle.indikator == "NY.GDP.PCAP.KD")].iloc[0]
    assert zeile.nicht_verwenden and zeile.hat_wert
    assert zeile.wert == wert("NY.GDP.PCAP.KD", "EG", 2014)  # Wert unverändert, nur markiert


def test_nicht_verwenden_ist_ohne_treffer_ueberall_falsch_und_bool(monkeypatch):
    ordner, _ = lade(monkeypatch)  # DEU, EGY, SAU stehen nicht in der echten Liste
    tabelle = wb.baue_tabelle(ordner)
    assert tabelle["nicht_verwenden"].dtype == bool
    assert not tabelle["nicht_verwenden"].any()


def test_liste_der_abweichenden_laender_und_codes():
    assert set(wb.PRO_KOPF_ABWEICHEND) == {"CYP", "MAR", "RUS", "TZA", "UKR"}
    assert set(wb.PRO_KOPF_CODES) == set(PRO_KOPF)
    assert {wb.INDIKATOREN[c]["kurzname"] for c in wb.PRO_KOPF_CODES} == {"bip_pro_kopf_real", "bip_pro_kopf_real_kkp"}


def test_nicht_verwenden_ueberlebt_schreiben_und_lesen(monkeypatch):
    monkeypatch.setattr(wb, "PRO_KOPF_ABWEICHEND", ("SAU",))
    lade(monkeypatch)
    wb.to_table()
    gelesen = wb.lese_tabelle()
    assert "nicht_verwenden" in gelesen.columns and gelesen["nicht_verwenden"].dtype == bool
    assert set(gelesen[gelesen["nicht_verwenden"]]["land_iso3"]) == {"SAU"}

