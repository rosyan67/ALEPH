"""Layer Wirtschaft: Weltbank World Development Indicators (WDI), jährlich, pro Land.

Steckbrief: docs/sources/weltbank.md. Nutzt denselben Lade- und Speicherweg
wie alle Layer (aleph/core/io.py: SSD-Pfad und Speicherwächter).

Ebene ist das LAND, nicht das Raster (ARCHITECTURE.md Abschnitt 4): Wirtschafts-
daten werden nie auf Gitterzellen verteilt und nie auf Monate umgelegt. Statt
`to_cube()` liefert dieser Layer deshalb `to_table()`: eine Parquet-Tabelle im
Langformat, eine Zeile je Land, Jahr und Indikator. Kein Erkennungs-Layer,
sondern Kontext und Kontrollvariable (ARCHITECTURE.md Abschnitt 5).

Indikatoren (Codes und Namen am 2026-09-23 gegen die Live-API geprüft):
- reales BIP in konstanten US-Dollar (Basisjahr 2015) und in Kaufkraftparitäten
  (konstante internationale Dollar, Basisjahr 2021). Das sind zwei verschiedene
  Basisjahre; die Reihen dürfen nicht vermischt werden.
- reales BIP pro Kopf (beide Varianten), Bevölkerung, reale Exporte und Importe
  von Waren und Dienstleistungen (konstante US-Dollar, Basisjahr 2015).
Laufende US-Dollar sind bewusst NICHT enthalten: Sie enthalten Preisänderungen
(Inflation) und würden in einer Nachtlicht-Wirtschafts-Prüfung Inflation messen.

Ablauf und Sicherheitsnetz:
- `download` legt die Antworten der API unverändert unter
  raw/weltbank/<Abrufzeitpunkt>/ ab, samt `manifest.json` (Prüfsumme je Datei,
  Zeitpunkt, letzte Aktualisierung der Quelle je Indikator). Das Manifest wird
  zuletzt geschrieben; ein Ordner ohne Manifest gilt als nicht fertig. Die Weltbank
  revidiert rückwirkend (quartalsweise), deshalb bleibt der Abrufzeitpunkt erhalten.
- Jeder Aufruf hat ein Zeitlimit und bis zu `MAX_VERSUCHE` Wiederholungen mit
  wachsender Wartezeit. Eine unvollständige oder fremde Antwort (falsche Seitenzahl,
  falscher Indikator, Jahr außerhalb der Anfrage, Fehlermeldung der API) bricht mit
  klarer Meldung ab, statt still weiterzulaufen.
- `baue_tabelle` prüft die Prüfsummen, dass Name und Einheit jedes Indikators noch
  die erwarteten sind (eine Neubasierung durch die Weltbank fällt so auf und
  vermischt keine Basisjahre), dass jeder Datensatz zu einem bekannten Land gehört,
  keine Doppelten und keine negativen oder nicht endlichen Werte vorkommen.
- Aggregate der Weltbank („World", Regionen, Einkommensgruppen) sind in der
  Antwort mit den Ländern vermischt und werden ausgefiltert (Region „Aggregates").
- Fehlende Werte bleiben als leerer Wert (NaN) mit `hat_wert = False` in der
  Tabelle; sie werden nie aufgefüllt oder interpoliert. Die jüngsten Jahre ab
  `VORLAEUFIG_AB` sind als `vorlaeufig` markiert.
- BIP pro Kopf ist für fünf Länder mit `nicht_verwenden` markiert (`PRO_KOPF_ABWEICHEND`),
  weil es dort nicht zu BIP und Bevölkerung passt; die Werte bleiben sichtbar.
"""

import argparse
import hashlib
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from aleph.core import io

API = "https://api.worldbank.org/v2"
START_STANDARD = 2013  # Untersuchungszeitraum E3
ENDE_STANDARD = 2025
VORLAEUFIG_AB = 2024  # Konvention (Steckbrief Abschnitt 8): die jüngsten Jahre gelten als vorläufig

TIMEOUT_SEKUNDEN = 60
MAX_VERSUCHE = 4
WARTEZEIT_BASIS_SEKUNDEN = 5  # verdoppelt sich je Versuch

ORDNER_MUSTER = re.compile(r"^\d{8}T\d{6}Z$")

# Länder, bei denen BIP pro Kopf nicht zu BIP und Bevölkerung passt (Abruf 2026-09-23; nachgerechnet
# 2026-09-24, Steckbrief Abschnitt 14: nur diese fünf von 212 Ländern weichen um mehr als 1 % ab, in
# beiden Pro-Kopf-Reihen gleich). Die Ursache ist nicht geprüft; deshalb wird BIP pro Kopf für diese Länder
# nicht verwendet, sondern mit BIP und Bevölkerung getrennt gerechnet. Die Werte bleiben in der Tabelle
# (nichts wird versteckt), aber `nicht_verwenden` ist gesetzt.
PRO_KOPF_CODES = ("NY.GDP.PCAP.KD", "NY.GDP.PCAP.PP.KD")
PRO_KOPF_ABWEICHEND = ("CYP", "MAR", "RUS", "TZA", "UKR")

INDIKATOREN = {
    "NY.GDP.MKTP.KD": {
        "kurzname": "bip_real",
        "name": "GDP (constant 2015 US$)",
        "einheit": "konstante US-Dollar, Basisjahr 2015",
    },
    "NY.GDP.MKTP.PP.KD": {
        "kurzname": "bip_real_kkp",
        "name": "GDP, PPP (constant 2021 international $)",
        "einheit": "konstante internationale Dollar (Kaufkraftparität), Basisjahr 2021",
    },
    "NY.GDP.PCAP.KD": {
        "kurzname": "bip_pro_kopf_real",
        "name": "GDP per capita (constant 2015 US$)",
        "einheit": "konstante US-Dollar je Einwohner, Basisjahr 2015",
    },
    "NY.GDP.PCAP.PP.KD": {
        "kurzname": "bip_pro_kopf_real_kkp",
        "name": "GDP per capita, PPP (constant 2021 international $)",
        "einheit": "konstante internationale Dollar je Einwohner (Kaufkraftparität), Basisjahr 2021",
    },
    "SP.POP.TOTL": {
        "kurzname": "bevoelkerung",
        "name": "Population, total",
        "einheit": "Personen (Jahresmitte, de facto)",
    },
    "NE.EXP.GNFS.KD": {
        "kurzname": "export_real",
        "name": "Exports of goods and services (constant 2015 US$)",
        "einheit": "konstante US-Dollar, Basisjahr 2015",
    },
    "NE.IMP.GNFS.KD": {
        "kurzname": "import_real",
        "name": "Imports of goods and services (constant 2015 US$)",
        "einheit": "konstante US-Dollar, Basisjahr 2015",
    },
}

META = {
    "name": "Weltbank WDI",
    "bereich": "Wirtschaft",
    "rolle": "Kontext und Kontrollvariable, kein Erkennungs-Layer (ARCHITECTURE.md Abschnitt 5)",
    "quelle": (
        "The World Bank, World Development Indicators (WDI), über die World Bank Indicators API v2. "
        "Die Reihen stammen aus nationalen Statistiken und internationalen Quellen; laut "
        "Indikator-Metadaten kommt die Bevölkerung aus den UN World Population Prospects, "
        "die KKP-Reihen aus dem International Comparison Program der Weltbank."
    ),
    "zugang": "frei, ohne Konto und ohne Token; keine Variable in .env nötig",
    "lizenz": "Creative Commons Attribution 4.0 (CC BY 4.0)",
    "lizenz_beleg": (
        "Am 2026-09-23 auf datacatalog.worldbank.org gelesen (WDI-Katalogeintrag: 'licensed under Creative "
        "Commons Attribution 4.0'; Seite 'public-licenses': CC BY 4.0 erlaubt Vervielfältigung und Weitergabe "
        "in jedem Format für jeden Zweck, auch kommerziell, verpflichtet nur zu Quellenangabe und Hinweis "
        "auf Änderungen). Beide Seiten wurden über einen Seitenauszug gelesen, nicht im vollen Wortlaut. "
        "Ob für die Drittquellen in WDI (z. B. UN-Bevölkerung) getrennte Bedingungen gelten, "
        "nennt keine der beiden Seiten und wurde nicht gesondert geprüft."
    ),
    "anzeige": (
        "Rohwerte dürfen öffentlich angezeigt werden (Länder-Jahr-Werte, auch einzeln), "
        "mit Quellenangabe und Hinweis auf Änderungen (z. B. Zusammenfassung, Umrechnung)."
    ),
    "quellenangabe": (
        "The World Bank: World Development Indicators (CC BY 4.0), abgerufen am <Abrufdatum>. "
        "Bei Bevölkerung zusätzlich: UN World Population Prospects. "
        "(Die genaue Zitierform schreibt die Lizenzseite nicht vor; dies ist die ALEPH-Form.)"
    ),
    "raeumliche_ebene": "Land (217 Volkswirtschaften der Weltbank-Länderliste), nie auf das Raster verteilt",
    "native_aufloesung": "Land x Jahr",
    "ziel_aufloesung": "Land x Jahr (bleibt jährlich, nicht auf Monate verteilt)",
    "zeitraum": f"{START_STANDARD}-{ENDE_STANDARD} (Entscheidung E3); die Quelle reicht bis 1960 zurück",
    "indikatoren": {code: {"name": i["name"], "einheit": i["einheit"]} for code, i in INDIKATOREN.items()},
    "evidenzstufe": (
        "beobachtet (amtliche Statistik, keine Modellprojektion). Einzelne Länderwerte sind selbst Schätzungen "
        "nationaler Statistikämter bzw. der UN und für Länder mit schwacher Datenlage unsicher."
    ),
    "bekannte_schwaechen": [
        f"Die jüngsten Jahre (ab {VORLAEUFIG_AB}) sind bei vielen Ländern vorläufig oder fehlen; Spalte `vorlaeufig`. "
        "Der Anteil fehlender Werte je Indikator und Jahr steht in `datenlage()`.",
        "Konflikt- und fragile Staaten haben oft Lücken oder unzuverlässige Reihen (Steckbrief Abschnitt 8, Drittquelle).",
        "Rückwirkende Revisionen (quartalsweise): Der Abrufzeitpunkt bleibt in den Rohdaten und in der Tabelle erhalten.",
        "Zwei Basisjahre: reale US-Dollar-Reihen (2015) und KKP-Reihen (2021) nicht mischen. Die US-Dollar-Reihen "
        "dienen dem Vergleich über die Zeit innerhalb eines Landes; für Vergleiche des Niveaus zwischen Ländern "
        "sind die KKP-Reihen gedacht.",
        "Nicht jede Volkswirtschaft ist enthalten (z. B. steht Taiwan nicht in der Weltbank-Länderliste). "
        "Die Zuordnung der 217 Einträge zu ALEPH-Ländergrenzen ist nicht geprüft.",
        "Keine Auflösung unterhalb der Länderebene: Innerstaatliche Unterschiede sind nicht abbildbar.",
        "Gemessen am Abruf 2026-09-23 (Zahlen ändern sich mit Revisionen): Export und Import fehlen je Jahr bei "
        "15 bis 41 % der Volkswirtschaften, das BIP bei 2 bis 14 % (2025 am höchsten), die Bevölkerung nie.",
        "Gemessen am Abruf 2026-09-23: Bei Zypern, Marokko, Russland, Tansania und der Ukraine passt BIP pro Kopf "
        "mal Bevölkerung nicht zum BIP (Abweichung 1,5 bis 44 %, bei Zypern am größten; nachgerechnet 2026-09-24: "
        "bei Russland und Ukraine erst ab 2014, dort in jedem Jahr um dieselbe Personenzahl von etwa 2,3 bis 2,5 "
        "Millionen in entgegengesetzter Richtung; bei allen anderen 207 Ländern null). Die Ursache ist nicht "
        "geprüft (Steckbrief Abschnitt 14). Deshalb ist BIP pro Kopf für diese Länder mit `nicht_verwenden` "
        "markiert; dort mit BIP und Bevölkerung getrennt rechnen.",
        "Gemessen am Abruf 2026-09-23: Das Verhältnis KKP-BIP zu BIP in konstanten US-Dollar ist bei allen 199 Ländern "
        "mit beiden Reihen über alle Jahre konstant. Die KKP-Reihe hat also dieselbe Veränderung über die Zeit und "
        "bringt für Zeitreihen nichts Neues; sie ist nur für Niveauvergleiche zwischen Ländern nützlich.",
    ],
    "messsystem_bruche": [
        "Neubasierung der Preisreihen durch die Weltbank (Basisjahr 2015 bzw. 2021 kann wechseln). "
        "`baue_tabelle` bricht ab, wenn sich Name oder Basisjahr eines Indikators ändern.",
        "Wechsel der Erhebungs- und Fortschreibungsmethoden nationaler Statistikämter über die Zeit: nicht länderweise geprüft.",
    ],
}


class WeltbankFehler(RuntimeError):
    """Die Weltbank-Antwort ist fehlerhaft, unvollständig oder unerwartet: Lauf wird gestoppt."""


# --- Abruf -------------------------------------------------------------------


def _hole_json(pfad, params):
    """Ein GET gegen die Weltbank-API mit Zeitlimit und Wiederholung. Liefert das geparste JSON."""
    url = f"{API}/{pfad}"
    letzter_fehler = None
    for versuch in range(1, MAX_VERSUCHE + 1):
        try:
            antwort = requests.get(url, params=params, timeout=TIMEOUT_SEKUNDEN)
            status = antwort.status_code
            if 400 <= status < 500 and status != 429:
                # Falsche Anfrage: Wiederholen hilft nicht.
                raise WeltbankFehler(f"Die Weltbank-API lehnt die Anfrage ab (HTTP {status}): {url} {params}")
            antwort.raise_for_status()
            return antwort.json()
        except WeltbankFehler:
            raise
        except (requests.RequestException, ValueError) as fehler:
            letzter_fehler = fehler
            if versuch < MAX_VERSUCHE:
                time.sleep(WARTEZEIT_BASIS_SEKUNDEN * 2 ** (versuch - 1))
    raise WeltbankFehler(f"Abruf gescheitert nach {MAX_VERSUCHE} Versuchen: {url} {params} ({letzter_fehler})")


def _pruefe_antwort(json_antwort, beschreibung):
    """Trennt Kopf und Datensätze und prüft, dass die Antwort vollständig auf einer Seite liegt."""
    if not (isinstance(json_antwort, list) and json_antwort and isinstance(json_antwort[0], dict)):
        raise WeltbankFehler(f"{beschreibung}: unerwartetes Antwortformat: {str(json_antwort)[:200]}")
    kopf = json_antwort[0]
    if "message" in kopf:
        raise WeltbankFehler(f"{beschreibung}: die API meldet einen Fehler: {kopf['message']}")
    if len(json_antwort) < 2 or not json_antwort[1]:
        raise WeltbankFehler(f"{beschreibung}: die Antwort enthält keine Datensätze.")
    daten = json_antwort[1]
    if int(kopf.get("pages", 0)) != 1:
        raise WeltbankFehler(
            f"{beschreibung}: die Antwort umfasst {kopf.get('pages')} Seiten, es wird nur eine gelesen. "
            "Unvollständige Daten werden nicht verwendet."
        )
    if int(kopf["total"]) != len(daten):
        raise WeltbankFehler(f"{beschreibung}: laut Kopf {kopf['total']} Datensätze, erhalten {len(daten)}.")
    return kopf, daten


def _schreibe_json(pfad, inhalt):
    """Schreibt JSON und liefert die Prüfsumme der geschriebenen Datei."""
    rohbytes = json.dumps(inhalt, ensure_ascii=False).encode("utf-8")
    pfad.write_bytes(rohbytes)
    return hashlib.sha256(rohbytes).hexdigest()


def _pruefsumme(pfad):
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def _lese_json(pfad):
    return json.loads(pfad.read_text(encoding="utf-8"))


def _ist_aggregat(land):
    return land["region"]["value"].strip() == "Aggregates"


def download(start=START_STANDARD, ende=ENDE_STANDARD, abrufzeit=None):
    """Lädt Länderliste und alle Indikatoren nach raw/weltbank/<Abrufzeitpunkt>/. Liefert den Ordner.

    Der Ordner entsteht zuerst unter Hilfsnamen und wird erst nach dem Schreiben des
    Manifests umbenannt: Ein Abbruch hinterlässt keinen scheinbar fertigen Abruf.
    """
    if not (isinstance(start, int) and isinstance(ende, int) and 1960 <= start <= ende):
        raise ValueError(f"Ungültiger Zeitraum {start}-{ende}: erwartet ganze Jahre, 1960 <= start <= ende.")
    io.pruefe_speicher()
    beginn = time.monotonic()
    abrufzeit = abrufzeit or datetime.now(timezone.utc)
    name = abrufzeit.strftime("%Y%m%dT%H%M%SZ")
    ziel = io.rohdaten_pfad("weltbank", name)
    hilfs = ziel.with_name(name + ".tmp")
    if ziel.exists() or hilfs.exists():
        raise WeltbankFehler(f"Der Abruf-Ordner {name} existiert schon; es wird nichts überschrieben.")
    hilfs.mkdir(parents=True)
    try:
        _lade_in(hilfs, start, ende, abrufzeit, beginn)
    except BaseException:
        shutil.rmtree(hilfs, ignore_errors=True)  # kein halb fertiger Abruf bleibt liegen
        raise
    hilfs.rename(ziel)
    return ziel


def _lade_in(hilfs, start, ende, abrufzeit, beginn):
    """Lädt alles in den Hilfsordner und schreibt als Letztes das Manifest."""
    kopf, laender = _pruefe_antwort(_hole_json("country", {"format": "json", "per_page": 500}), "Länderliste")
    laender_summe = _schreibe_json(hilfs / "laender.json", laender)
    echte = {land["iso2Code"]: land for land in laender if not _ist_aggregat(land)}

    manifest_indikatoren = {}
    for code, info in INDIKATOREN.items():
        beschreibung = f"Indikator {code}"
        kopf, daten = _pruefe_antwort(
            _hole_json(
                f"country/all/indicator/{code}",
                {"format": "json", "date": f"{start}:{ende}", "per_page": 20000},
            ),
            beschreibung,
        )
        for satz in daten:
            if satz["indicator"]["id"] != code:
                raise WeltbankFehler(f"{beschreibung}: Datensatz gehört zu {satz['indicator']['id']}.")
            if not start <= int(satz["date"]) <= ende:
                raise WeltbankFehler(f"{beschreibung}: Jahr {satz['date']} liegt außerhalb {start}-{ende}.")
        namen_in_daten = {satz["indicator"]["value"] for satz in daten}
        if namen_in_daten != {info["name"]}:
            raise WeltbankFehler(
                f"{beschreibung}: Name in den Daten {sorted(namen_in_daten)} statt '{info['name']}'. "
                "Wahrscheinlich hat die Weltbank den Indikator neu basiert oder umbenannt; "
                "Einheit prüfen, bevor er verwendet wird."
            )
        datei = f"{code}.json"
        summe = _schreibe_json(hilfs / datei, daten)
        vorhanden = {satz["country"]["id"] for satz in daten}
        manifest_indikatoren[code] = {
            "datei": datei,
            "sha256": summe,
            "name_in_daten": info["name"],
            "quelle_zuletzt_aktualisiert": kopf.get("lastupdated"),
            "n_datensaetze": len(daten),
            "n_ohne_wert": sum(1 for satz in daten if satz["value"] is None),
            "laender_ohne_eintrag": sorted(echte[iso2]["id"] for iso2 in set(echte) - vorhanden),
        }

    manifest = {
        "abruf_utc": abrufzeit.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "api": API,
        "start": start,
        "ende": ende,
        "laender": {
            "datei": "laender.json",
            "sha256": laender_summe,
            "n_eintraege": len(laender),
            "n_volkswirtschaften": len(echte),
        },
        "indikatoren": manifest_indikatoren,
        "dauer_sekunden": round(time.monotonic() - beginn, 1),
    }
    (hilfs / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def letzter_abruf():
    """Neuester vollständiger Abruf (Ordner mit Manifest) oder None."""
    basis = io.rohdaten_pfad("weltbank")
    if not basis.is_dir():
        return None
    fertig = sorted(
        ordner for ordner in basis.iterdir()
        if ordner.is_dir() and ORDNER_MUSTER.match(ordner.name) and (ordner / "manifest.json").is_file()
    )
    return fertig[-1] if fertig else None


# --- Tabelle -----------------------------------------------------------------


def baue_tabelle(abruf_ordner):
    """Baut aus einem Abruf die Länder-Jahr-Indikator-Tabelle (Langformat), ohne etwas zu schreiben."""
    abruf_ordner = Path(abruf_ordner)
    manifest = _lese_json(abruf_ordner / "manifest.json")
    start, ende = manifest["start"], manifest["ende"]

    def gepruefte_datei(eintrag):
        pfad = abruf_ordner / eintrag["datei"]
        if _pruefsumme(pfad) != eintrag["sha256"]:
            raise WeltbankFehler(f"Prüfsumme von {eintrag['datei']} stimmt nicht mit dem Manifest überein: Datei verändert.")
        return _lese_json(pfad)

    laender = gepruefte_datei(manifest["laender"])
    alle_iso2 = {land["iso2Code"] for land in laender}
    echte = {land["iso2Code"]: land for land in laender if not _ist_aggregat(land)}
    jahre = list(range(start, ende + 1))

    teile = []
    for code, info in INDIKATOREN.items():
        eintrag = manifest["indikatoren"].get(code)
        if eintrag is None:
            raise WeltbankFehler(f"Indikator {code} fehlt im Manifest.")
        if eintrag["name_in_daten"] != info["name"]:
            raise WeltbankFehler(
                f"Indikator {code} heißt im Abruf '{eintrag['name_in_daten']}', erwartet '{info['name']}': "
                "mögliche Neubasierung, Einheit prüfen."
            )
        daten = gepruefte_datei(eintrag)
        werte = {}
        for satz in daten:
            iso2 = satz["country"]["id"]
            if iso2 not in alle_iso2:
                raise WeltbankFehler(f"{code}: Datensatz für unbekannte Einheit '{iso2}' ({satz['country']['value']}).")
            if iso2 not in echte:
                continue  # Aggregat (Welt, Region, Einkommensgruppe)
            schluessel = (iso2, int(satz["date"]))
            if schluessel in werte:
                raise WeltbankFehler(f"{code}: doppelter Datensatz für {schluessel}.")
            werte[schluessel] = np.nan if satz["value"] is None else float(satz["value"])
        zeilen = []
        for iso2, land in sorted(echte.items(), key=lambda kv: kv[1]["id"]):
            for jahr in jahre:
                zeilen.append(
                    {
                        "land_iso3": land["id"],
                        "land_iso2": iso2,
                        "land_name": land["name"],
                        "region": land["region"]["value"].strip(),
                        "jahr": jahr,
                        "indikator": code,
                        "kurzname": info["kurzname"],
                        "wert": werte.get((iso2, jahr), np.nan),
                        "einheit": info["einheit"],
                        "quelle_zuletzt_aktualisiert": eintrag["quelle_zuletzt_aktualisiert"],
                    }
                )
        teile.append(pd.DataFrame(zeilen))

    tabelle = pd.concat(teile, ignore_index=True)
    tabelle["jahr"] = tabelle["jahr"].astype("int16")
    tabelle["hat_wert"] = tabelle["wert"].notna()
    tabelle["vorlaeufig"] = tabelle["jahr"] >= VORLAEUFIG_AB
    tabelle["nicht_verwenden"] = tabelle["indikator"].isin(PRO_KOPF_CODES) & tabelle["land_iso3"].isin(PRO_KOPF_ABWEICHEND)
    tabelle["abruf_utc"] = manifest["abruf_utc"]

    erwartet = len(echte) * len(jahre) * len(INDIKATOREN)
    if len(tabelle) != erwartet:
        raise WeltbankFehler(f"Tabelle hat {len(tabelle)} Zeilen, erwartet {erwartet}.")
    if tabelle.duplicated(["land_iso3", "jahr", "indikator"]).any():
        raise WeltbankFehler("Tabelle enthält doppelte Schlüssel (Land, Jahr, Indikator).")
    mit_wert = tabelle[tabelle["hat_wert"]]
    schlecht = mit_wert[~np.isfinite(mit_wert["wert"]) | (mit_wert["wert"] < 0)]
    if len(schlecht):
        raise WeltbankFehler(
            f"{len(schlecht)} Werte sind negativ oder nicht endlich, z. B.: "
            + "; ".join(f"{r.land_iso3} {r.jahr} {r.indikator} = {r.wert}" for r in schlecht.head(5).itertuples())
        )
    return tabelle.sort_values(["land_iso3", "indikator", "jahr"], ignore_index=True)


def tabellen_pfad():
    return io.aleph_data_dir() / "laender" / "weltbank.parquet"


def to_table(abruf_ordner=None):
    """Schreibt die Tabelle des (neuesten) Abrufs nach laender/weltbank.parquet und liefert den Pfad.

    Die Datei wird zuerst unter Hilfsnamen geschrieben, zurückgelesen und mit der Tabelle im
    Speicher verglichen; erst dann ersetzt sie die alte.
    """
    if abruf_ordner is None:
        abruf_ordner = letzter_abruf()
        if abruf_ordner is None:
            raise WeltbankFehler("Kein vollständiger Abruf vorhanden. Zuerst download() ausführen.")
    tabelle = baue_tabelle(abruf_ordner)
    ziel = tabellen_pfad()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    hilfs = ziel.with_name(ziel.name + ".tmp")
    tabelle.to_parquet(hilfs, index=False)
    pd.testing.assert_frame_equal(pd.read_parquet(hilfs), tabelle)
    hilfs.replace(ziel)
    return ziel


def lese_tabelle():
    """Liest die fertige Tabelle."""
    pfad = tabellen_pfad()
    if not pfad.is_file():
        raise WeltbankFehler("laender/weltbank.parquet fehlt. Zuerst to_table() ausführen.")
    return pd.read_parquet(pfad)


# --- Auswertungshilfen ---------------------------------------------------------


def datenlage(tabelle):
    """Anteil fehlender Werte je Indikator (Zeilen) und Jahr (Spalten), als Anteil 0 bis 1."""
    return (
        tabelle.assign(fehlt=~tabelle["hat_wert"])
        .pivot_table(index="kurzname", columns="jahr", values="fehlt", aggfunc="mean")
    )


def konsistenz_bip_pro_kopf(tabelle):
    """Innere Stimmigkeit: BIP pro Kopf mal Bevölkerung geteilt durch das BIP (real, Basisjahr 2015).

    Sollte nahe 1 liegen, wenn beide Reihen dieselbe Bevölkerung verwenden. Nur Land-Jahre, in
    denen alle drei Werte vorhanden sind. Liefert Anzahl und Verteilung des Verhältnisses.
    """
    breit = tabelle.pivot(index=["land_iso3", "jahr"], columns="kurzname", values="wert")
    breit = breit[["bip_real", "bip_pro_kopf_real", "bevoelkerung"]].dropna()
    breit = breit[breit["bip_real"] > 0]
    verhaeltnis = breit["bip_pro_kopf_real"] * breit["bevoelkerung"] / breit["bip_real"]
    return {
        "n": int(len(verhaeltnis)),
        "min": float(verhaeltnis.min()),
        "median": float(verhaeltnis.median()),
        "max": float(verhaeltnis.max()),
    }


def _relativ(pfad):
    """Pfad relativ zum Datenordner (der absolute SSD-Pfad steht nur in .env und wird nicht ausgegeben)."""
    return str(Path(pfad).relative_to(io.aleph_data_dir()))


def main():
    parser = argparse.ArgumentParser(description="Weltbank-Layer: Abruf und Tabelle.")
    parser.add_argument("--start", type=int, default=START_STANDARD)
    parser.add_argument("--ende", type=int, default=ENDE_STANDARD)
    parser.add_argument("--nur-tabelle", action="store_true", help="keinen neuen Abruf, nur die Tabelle aus dem letzten bauen")
    args = parser.parse_args()
    ordner = None
    if not args.nur_tabelle:
        ordner = download(args.start, args.ende)
        print(f"Abruf fertig: {_relativ(ordner)}")
    pfad = to_table(ordner)
    tabelle = lese_tabelle()
    print(f"Tabelle geschrieben: {_relativ(pfad)} ({len(tabelle)} Zeilen, {tabelle['land_iso3'].nunique()} Länder)")


if __name__ == "__main__":
    main()
