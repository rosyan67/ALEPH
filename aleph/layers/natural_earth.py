"""Ländergrenzen: Natural Earth, Admin 0 – Countries, Maßstab 1:10m, Version 5.1.1.

Steckbrief: docs/sources/natural_earth.md. Nutzt denselben Lade- und Speicherweg
wie alle Layer (aleph/core/io.py: SSD-Pfad und Speicherwächter), mit demselben
Muster wie der Weltbank-Layer: Hilfsordner, Manifest mit Prüfsumme zuletzt,
erst dann umbenennen.

Kein Erkennungs-Layer, sondern die zweite räumliche Ebene (ARCHITECTURE.md
Abschnitt 4): Sie ordnet Orte (später 0,25°-Zellen) einem Land zu, damit
Rasterwerte mit Länderdaten der Weltbank verknüpft werden können.

Grenzen kommen nur aus dieser benannten Quelle. Scheitert der Download oder
passt die Datei nicht (Version, Anzahl, Prüfsumme), bricht das Modul mit
`NaturalEarthFehler` ab. Es gibt keinen Ersatz, keine fest eingetragenen
Grenzen und kein Nachbauen.

Entscheidungen (Begründung und Messungen im Steckbrief):
- Maßstab 1:10m: 1:50m (242 Einträge) verliert auf dem 0,25°-Raster Bahrain ganz,
  1:110m (177) 48 Weltbank-Länder; POV-Dateien gibt es nur für 1:10m. Die Datei ist
  4,9 MB groß; für das 0,25°-Raster ist das kein Rechenproblem.
- Standarddatei („de facto“ nach der Regel des Anbieters für de-facto-souveräne Staaten,
  NICHT die tatsächliche Kontrolle vor Ort: Abspaltungsgebiete wie die Ostukraine bleiben
  beim Mutterstaat, die Krim liegt bei Russland), keine POV-Datei.
- Code-Feld ISO_A3_EH. ISO_A3 hat bei 22 Einheiten den Platzhalter „-99“, darunter
  Frankreich und Norwegen; WB_A3 enthält teils veraltete Weltbank-Codes (z. B. ROM,
  ZAR). Zusätzlich die Korrekturen in `WELTBANK_KORREKTUREN`.
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import Point
from shapely.validation import make_valid

from aleph.core import io

VERSION = "5.1.1"
DATEI = "ne_10m_admin_0_countries.zip"
URL = f"https://naciscdn.org/naturalearth/10m/cultural/{DATEI}"
# Anbieterangabe in der beiliegenden README (Seite „Admin 0 – Countries“): „There are 258 countries in the world.“
# Der Satz steht wortgleich auch bei 1:50m (242 Einträge) und 1:110m (177); er passt nur zu 1:10m.
ANZAHL_LAUT_QUELLE = 258

# Netzwerkregel (CLAUDE.md): Zeitlimit je Anfrage und Wiederholung mit wachsenden Pausen
# (5, 10, 20 s; zusammen 35 s). Das reicht für kurze Störungen; eine längere Störung soll
# mit klarer Meldung abbrechen statt still zu warten. Jede Wiederholung wird gemeldet.
TIMEOUT_SEKUNDEN = 120  # eine Datei von etwa 5 MB, auch bei langsamer Leitung
MAX_VERSUCHE = 4
WARTEZEIT_BASIS_SEKUNDEN = 5  # verdoppelt sich je Versuch

CODE_FELD = "ISO_A3_EH"
PLATZHALTER = "-99"
REPARATUR_TOLERANZ = 1e-9  # höchste erlaubte relative Flächenänderung bei der Reparatur eines Umrisses

# Einheiten, deren ISO_A3_EH nicht der Weltbank-Code ist, obwohl die Weltbank sie führt
# (am 2026-09-25 gegen die Weltbank-Länderliste vom Abruf 2026-09-23 geprüft).
# Schlüssel ist ADM0_A3 (in der Datei eindeutig, nie „-99“).
WELTBANK_KORREKTUREN = {
    "KOS": "XKX",  # Kosovo: ISO_A3_EH ist „-99“, die Weltbank nutzt XKX
    "JEY": "CHI",  # Jersey: die Weltbank führt nur „Channel Islands“ (CHI)
    "GGY": "CHI",  # Guernsey: ebenso
}

SPALTEN = ["ADM0_A3", "ADMIN", "NAME_DE", "TYPE", "SOV_A3", "ISO_A3", "ISO_A3_EH", "WB_A3"]

META = {
    "name": "Natural Earth Admin 0 – Countries",
    "bereich": "Verwaltungsgrenzen",
    "rolle": "Zuordnung von Orten und Rasterzellen zu Ländern (ARCHITECTURE.md Abschnitt 4), kein Erkennungs-Layer",
    "quelle": "Natural Earth (naturalearthdata.com), Admin 0 – Countries, 1:10m",
    "version": VERSION,
    "download": URL,
    "zugang": "frei, ohne Konto und ohne Token; keine Variable in .env nötig",
    "lizenz": "Public Domain laut Anbieter; Einzelheiten und Beleg im Steckbrief",
    "sichtweise": (
        "Standarddatei („de facto“ nach Anbieterregel für de-facto-souveräne Staaten, nicht die Kontrolle vor Ort), "
        "keine POV-Variante"
    ),
    "code_feld": f"{CODE_FELD}, dazu WELTBANK_KORREKTUREN; Ergebnis in Spalte land_iso3 (wie in der Weltbank-Tabelle)",
    "anzahl_laut_quelle": ANZAHL_LAUT_QUELLE,
    "evidenzstufe": "keine Messung: Grenzen sind eine redaktionelle Festlegung des Anbieters",
    "bekannte_schwaechen": [
        "„de facto“ ist eine Anbieterregel, nicht die Kontrolle vor Ort: Die Krim liegt im Polygon Russlands, der größte "
        "Teil der Westsahara in Marokko, Donezk, Luhansk, Transnistrien, Abchasien, Südossetien und Bergkarabach "
        "beim Mutterstaat. Ob die Weltbank-Statistik dieselben Gebiete umfasst, ist nicht geprüft.",
        "Einheiten ohne Weltbank-Gegenstück (u. a. Taiwan, Somaliland, Westsahara, Nordzypern): land_iso3 ist dort "
        "gesetzt oder leer, aber es gibt keine Weltbank-Daten dazu; siehe abgleich_weltbank().",
        "Ein fester Grenzstand (Version 5.1.1, Dateien vom Mai 2022) gilt für alle Jahre 2013–2025: z. B. liegt die "
        "Krim auch 2013 bei Russland. Spätere Grenzänderungen sind nicht enthalten.",
        "Bei Zuordnung über Zellmitten bekommen kleine Länder auf dem 0,25°-Raster keine Zelle (Messung im Steckbrief).",
    ],
}


class NaturalEarthFehler(RuntimeError):
    """Download oder Datei stimmt nicht: Lauf wird gestoppt, es gibt keinen Ersatz."""


# --- Download ------------------------------------------------------------------


def _pruefsumme(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def _hole_datei(url, ziel):
    """Lädt eine Datei mit Zeitlimit und Wiederholung. Liefert die Antwort-Kopfzeilen."""
    letzter_fehler = None
    for versuch in range(1, MAX_VERSUCHE + 1):
        try:
            antwort = requests.get(url, timeout=TIMEOUT_SEKUNDEN)
            status = antwort.status_code
            if 400 <= status < 500 and status != 429:
                raise NaturalEarthFehler(
                    f"Natural Earth lehnt den Download ab (HTTP {status}): {url}. Es wird kein Ersatz verwendet."
                )
            antwort.raise_for_status()
            ziel.write_bytes(antwort.content)
            return dict(antwort.headers)
        except NaturalEarthFehler:
            raise
        except requests.RequestException as fehler:
            letzter_fehler = fehler
            if versuch < MAX_VERSUCHE:
                pause = WARTEZEIT_BASIS_SEKUNDEN * 2 ** (versuch - 1)
                print(f"Natural Earth: Versuch {versuch}/{MAX_VERSUCHE} gescheitert ({type(fehler).__name__}), "
                      f"neuer Versuch in {pause} s: {url}", file=sys.stderr, flush=True)
                time.sleep(pause)
    raise NaturalEarthFehler(
        f"Download gescheitert nach {MAX_VERSUCHE} Versuchen: {url} ({letzter_fehler}). "
        "Es wird kein Ersatz verwendet; Netz und Adresse prüfen."
    )


def _version_im_zip(pfad):
    """Liest die Versionsdatei, die Natural Earth jedem Zip beilegt."""
    try:
        with zipfile.ZipFile(pfad) as z:
            namen = [n for n in z.namelist() if n.endswith(".VERSION.txt")]
            if len(namen) != 1:
                raise NaturalEarthFehler(f"{pfad.name}: erwartet genau eine VERSION-Datei, gefunden {namen}.")
            return z.read(namen[0]).decode("utf-8").strip()
    except zipfile.BadZipFile as fehler:
        raise NaturalEarthFehler(f"{pfad.name} ist keine gültige Zip-Datei: {fehler}") from fehler


def _lies_zip(pfad):
    return gpd.read_file(f"zip://{pfad}")


def _pruefe_inhalt(laender, herkunft):
    """Prüft Anzahl, Koordinatensystem und Eindeutigkeit. Bricht bei jeder Abweichung ab."""
    if len(laender) != ANZAHL_LAUT_QUELLE:
        raise NaturalEarthFehler(
            f"{herkunft}: {len(laender)} Einheiten, laut Quelle {ANZAHL_LAUT_QUELLE}. Falsche Datei oder neue Version?"
        )
    if laender.crs is None or laender.crs.to_epsg() != 4326:
        raise NaturalEarthFehler(f"{herkunft}: Koordinatensystem {laender.crs}, erwartet EPSG:4326.")
    fehlend = [s for s in SPALTEN if s not in laender.columns]
    if fehlend:
        raise NaturalEarthFehler(f"{herkunft}: Spalten fehlen: {fehlend}")
    if laender["ADM0_A3"].duplicated().any() or (laender["ADM0_A3"] == PLATZHALTER).any():
        raise NaturalEarthFehler(f"{herkunft}: ADM0_A3 ist nicht eindeutig oder enthält „-99“.")
    unbekannt = set(WELTBANK_KORREKTUREN) - set(laender["ADM0_A3"])
    if unbekannt:
        raise NaturalEarthFehler(f"{herkunft}: Einheiten für die Weltbank-Korrektur fehlen: {sorted(unbekannt)}")


def _repariere(laender, herkunft):
    """Repariert formal ungültige Umrisse, wenn sich dabei die Fläche nicht ändert. Liefert die ADM0_A3-Codes.

    In Version 5.1.1 (1:10m) ist genau Ägypten betroffen: Die Randlinie berührt sich an einem Punkt
    selbst (35,621° O / 23,139° N). Die Reparatur der Geometrie-Bibliothek (make_valid) ändert die
    Fläche dort um weniger als 1e-13 Grad². Ändert sich bei einer Einheit die Fläche um mehr als
    `REPARATUR_TOLERANZ` (relativ) oder entsteht kein Flächenobjekt, wird abgebrochen: Dann wäre
    die Reparatur eine inhaltliche Änderung der Grenze.
    """
    repariert = []
    for index in laender.index[~laender.geometry.is_valid]:
        alt = laender.geometry[index]
        neu = make_valid(alt)
        code = laender.at[index, "ADM0_A3"]
        if neu.geom_type not in ("Polygon", "MultiPolygon") or not neu.is_valid:
            raise NaturalEarthFehler(f"{herkunft}: Umriss von {code} ist ungültig und nicht als Fläche reparierbar.")
        if abs(neu.area - alt.area) > REPARATUR_TOLERANZ * alt.area:
            raise NaturalEarthFehler(
                f"{herkunft}: Die Reparatur des Umrisses von {code} ändert die Fläche ({alt.area} → {neu.area} Grad²). "
                "Das wäre eine inhaltliche Änderung der Grenze; abgebrochen."
            )
        laender.at[index, "geometry"] = neu
        repariert.append(code)
    return repariert


def ordner():
    """Ablageort der Rohdaten dieser Version auf der SSD."""
    return io.rohdaten_pfad("natural_earth", VERSION)


def download(abrufzeit=None):
    """Lädt die Datei nach raw/natural_earth/<Version>/ und liefert den Ordner.

    Liegt die Version schon vollständig vor (Manifest vorhanden), wird nichts geladen.
    Der Ordner entsteht zuerst unter Hilfsnamen; ein Abbruch hinterlässt nichts.
    """
    ziel = ordner()
    if (ziel / "manifest.json").is_file():
        return ziel
    if ziel.exists():
        raise NaturalEarthFehler(
            f"{ziel.name}: Ordner ohne Manifest vorhanden (abgebrochener Abruf?). Bitte prüfen, es wird nichts überschrieben."
        )
    io.pruefe_speicher()
    abrufzeit = abrufzeit or datetime.now(timezone.utc)
    hilfs = ziel.with_name(ziel.name + ".tmp")
    if hilfs.exists():
        shutil.rmtree(hilfs)  # Rest eines abgebrochenen Laufs, nie ein fertiger Abruf
    hilfs.mkdir(parents=True)
    try:
        zip_pfad = hilfs / DATEI
        kopf = _hole_datei(URL, zip_pfad)
        version = _version_im_zip(zip_pfad)
        if version != VERSION:
            raise NaturalEarthFehler(
                f"Die geladene Datei hat Version {version}, erwartet {VERSION}. Neue Version: erst Steckbrief und "
                "Messungen prüfen, dann VERSION anpassen."
            )
        laender = _lies_zip(zip_pfad)
        _pruefe_inhalt(laender, DATEI)
        repariert = _repariere(laender, DATEI)
        manifest = {
            "abruf_utc": abrufzeit.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": URL,
            "datei": DATEI,
            "version": version,
            "bytes": zip_pfad.stat().st_size,
            "sha256": _pruefsumme(zip_pfad),
            "last_modified_laut_server": kopf.get("Last-Modified") or kopf.get("last-modified"),
            "anzahl_einheiten": len(laender),
            "umriss_repariert": repariert,
        }
        (hilfs / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except BaseException:
        shutil.rmtree(hilfs, ignore_errors=True)
        raise
    hilfs.rename(ziel)
    return ziel


# --- Lesen ---------------------------------------------------------------------


def _land_iso3(zeile):
    if zeile["ADM0_A3"] in WELTBANK_KORREKTUREN:
        return WELTBANK_KORREKTUREN[zeile["ADM0_A3"]]
    code = zeile[CODE_FELD]
    return None if code == PLATZHALTER else code


def lade_laender(abruf_ordner=None):
    """Liest die geladenen Grenzen als GeoDataFrame (eine Zeile je Einheit, EPSG:4326).

    Prüft vorher die Prüfsumme gegen das Manifest. Spalte `land_iso3` ist der Code
    für die Verknüpfung mit der Weltbank-Tabelle (dort ebenfalls `land_iso3`), leer,
    wenn die Quelle keinen Code hat. Ob die Weltbank das Land führt, sagt
    `abgleich_weltbank`.
    """
    abruf_ordner = Path(abruf_ordner) if abruf_ordner else ordner()
    manifest_pfad = abruf_ordner / "manifest.json"
    if not manifest_pfad.is_file():
        raise NaturalEarthFehler("Natural Earth ist nicht geladen (kein Manifest). Zuerst download() ausführen.")
    manifest = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    zip_pfad = abruf_ordner / manifest["datei"]
    if _pruefsumme(zip_pfad) != manifest["sha256"]:
        raise NaturalEarthFehler(f"Prüfsumme von {manifest['datei']} stimmt nicht mit dem Manifest überein: Datei verändert.")
    laender = _lies_zip(zip_pfad)
    _pruefe_inhalt(laender, manifest["datei"])
    repariert = _repariere(laender, manifest["datei"])
    if repariert != manifest["umriss_repariert"]:
        raise NaturalEarthFehler(f"Reparierte Umrisse {repariert} weichen vom Manifest ab ({manifest['umriss_repariert']}).")
    laender = laender[SPALTEN + ["geometry"]].copy()
    laender["land_iso3"] = laender.apply(_land_iso3, axis=1)
    return laender


def land_an_punkt(laender, lon, lat):
    """Einheit, in der der Punkt liegt, als Zeile (Series), oder None (z. B. offenes Meer).

    Liegt ein Punkt in mehr als einer Einheit, ist die Datei fehlerhaft: Abbruch.
    """
    punkt = Point(lon, lat)
    kandidaten = laender.iloc[laender.sindex.query(punkt, predicate="intersects")]
    if len(kandidaten) > 1:
        raise NaturalEarthFehler(f"Punkt ({lon}, {lat}) liegt in mehreren Einheiten: {list(kandidaten['ADM0_A3'])}")
    return None if kandidaten.empty else kandidaten.iloc[0]


def abgleich_weltbank(laender, weltbank_laender):
    """Vergleicht `land_iso3` mit der Weltbank-Länderliste {ISO3-Code: Name}.

    Liefert ein Wörterbuch:
    - `passend`: Weltbank-Codes, die mindestens eine Einheit haben,
    - `weltbank_ohne_grenze`: Weltbank-Länder ohne Einheit,
    - `grenze_ohne_weltbank`: Einheiten, deren Code die Weltbank nicht führt (oder ohne Code),
    - `mehrere_einheiten`: Weltbank-Codes mit mehr als einer Einheit (z. B. Australien mit Außengebieten).
    """
    codes = laender["land_iso3"]
    in_wb = codes.isin(list(weltbank_laender))
    gruppen = laender[in_wb].groupby("land_iso3")["ADMIN"].apply(list)
    return {
        "passend": sorted(set(codes[in_wb])),
        "weltbank_ohne_grenze": sorted(set(weltbank_laender) - set(codes[in_wb])),
        "grenze_ohne_weltbank": laender.loc[~in_wb, ["ADM0_A3", "ADMIN", "TYPE", "land_iso3"]].reset_index(drop=True),
        "mehrere_einheiten": {code: namen for code, namen in gruppen.items() if len(namen) > 1},
    }


# --- Zusatzdateien derselben Version (seit 2026-09-26) ----------------------------
#
# Für die Sondereinheiten der Zell-Zuordnung (aleph/layers/zell_einheiten.py): umstrittene
# Gebiete (Krim, Abchasien, Kaschmir-Teile usw.) und die Provinzdatei (nur für Tibet/Xizang).
# Gleiches Muster wie oben: eigener Ordner raw/natural_earth/<Version>_<Schlüssel>/ mit
# Manifest, Abbruch statt Ersatz. Die Anzahl ist bei beiden eine eigene Zählung vom
# 2026-09-26 (die beiliegenden README-Dateien nennen keine Zahl), keine Anbieterangabe.
ZUSATZ = {
    "umstritten": {"datei": "ne_10m_admin_0_disputed_areas.zip", "anzahl_gemessen": 99},
    "provinzen": {"datei": "ne_10m_admin_1_states_provinces.zip", "anzahl_gemessen": 4596},
}


def ordner_zusatz(schluessel):
    return io.rohdaten_pfad("natural_earth", f"{VERSION}_{schluessel}")


def _eintrag_zusatz(schluessel):
    if schluessel not in ZUSATZ:
        raise NaturalEarthFehler(f"Unbekannte Zusatzdatei „{schluessel}“, bekannt sind {sorted(ZUSATZ)}.")
    return ZUSATZ[schluessel]


def download_zusatz(schluessel, abrufzeit=None):
    """Lädt eine Zusatzdatei (siehe ZUSATZ) nach raw/natural_earth/<Version>_<Schlüssel>/. Liefert den Ordner."""
    eintrag = _eintrag_zusatz(schluessel)
    ziel = ordner_zusatz(schluessel)
    if (ziel / "manifest.json").is_file():
        return ziel
    if ziel.exists():
        raise NaturalEarthFehler(f"{ziel.name}: Ordner ohne Manifest vorhanden. Bitte prüfen, es wird nichts überschrieben.")
    io.pruefe_speicher()
    abrufzeit = abrufzeit or datetime.now(timezone.utc)
    hilfs = ziel.with_name(ziel.name + ".tmp")
    if hilfs.exists():
        shutil.rmtree(hilfs)
    hilfs.mkdir(parents=True)
    try:
        url = f"https://naciscdn.org/naturalearth/10m/cultural/{eintrag['datei']}"
        zip_pfad = hilfs / eintrag["datei"]
        kopf = _hole_datei(url, zip_pfad)
        version = _version_im_zip(zip_pfad)
        if version != VERSION:
            raise NaturalEarthFehler(f"{eintrag['datei']} hat Version {version}, erwartet {VERSION}.")
        daten = _lies_zip(zip_pfad)
        _pruefe_zusatz(daten, eintrag)
        manifest = {
            "abruf_utc": abrufzeit.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": url,
            "datei": eintrag["datei"],
            "version": version,
            "bytes": zip_pfad.stat().st_size,
            "sha256": _pruefsumme(zip_pfad),
            "last_modified_laut_server": kopf.get("Last-Modified") or kopf.get("last-modified"),
            "anzahl_einheiten": len(daten),
        }
        (hilfs / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except BaseException:
        shutil.rmtree(hilfs, ignore_errors=True)
        raise
    hilfs.rename(ziel)
    return ziel


def _pruefe_zusatz(daten, eintrag):
    if len(daten) != eintrag["anzahl_gemessen"]:
        raise NaturalEarthFehler(
            f"{eintrag['datei']}: {len(daten)} Einträge, bei der Prüfung am 2026-09-26 waren es "
            f"{eintrag['anzahl_gemessen']}. Andere Datei oder neue Version?"
        )
    if daten.crs is None or daten.crs.to_epsg() != 4326:
        raise NaturalEarthFehler(f"{eintrag['datei']}: Koordinatensystem {daten.crs}, erwartet EPSG:4326.")


def lade_zusatz(schluessel):
    """Liest eine geladene Zusatzdatei als GeoDataFrame (Prüfsumme gegen Manifest). Liefert (Daten, Manifest).

    Ungültige Umrisse werden nur repariert, wenn sich die Fläche nicht ändert (wie bei den Ländern).
    """
    eintrag = _eintrag_zusatz(schluessel)
    abruf_ordner = ordner_zusatz(schluessel)
    manifest_pfad = abruf_ordner / "manifest.json"
    if not manifest_pfad.is_file():
        raise NaturalEarthFehler(f"Zusatzdatei „{schluessel}“ ist nicht geladen. Zuerst download_zusatz('{schluessel}').")
    manifest = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    zip_pfad = abruf_ordner / manifest["datei"]
    if _pruefsumme(zip_pfad) != manifest["sha256"]:
        raise NaturalEarthFehler(f"Prüfsumme von {manifest['datei']} stimmt nicht mit dem Manifest überein.")
    daten = _lies_zip(zip_pfad)
    _pruefe_zusatz(daten, eintrag)
    repariert = []
    for index in daten.index[~daten.geometry.is_valid]:
        alt = daten.geometry[index]
        neu = make_valid(alt)
        if neu.geom_type not in ("Polygon", "MultiPolygon"):
            neu = _nur_flaechen(neu)
        if neu is None or not neu.is_valid or abs(neu.area - alt.area) > REPARATUR_TOLERANZ * alt.area:
            raise NaturalEarthFehler(f"{manifest['datei']}: Umriss Zeile {index} ist nicht ohne Flächenänderung reparierbar.")
        daten.at[index, "geometry"] = neu
        repariert.append(int(index))
    manifest["umriss_repariert_beim_lesen"] = repariert  # nur im Speicher; wird ins Manifest der Zuordnung übernommen
    return daten, manifest


def _nur_flaechen(geometrie):
    """Aus einer GeometryCollection nur die Flächenteile (make_valid liefert manchmal Linienreste mit)."""
    from shapely.geometry import MultiPolygon

    teile = []
    for teil in getattr(geometrie, "geoms", [geometrie]):
        if teil.geom_type == "Polygon":
            teile.append(teil)
        elif teil.geom_type == "MultiPolygon":
            teile.extend(teil.geoms)
    return MultiPolygon(teile) if teile else None


def main():
    argparse.ArgumentParser(description="Natural Earth Ländergrenzen laden und prüfen.").parse_args()
    ziel = download()
    laender = lade_laender(ziel)
    print(f"Natural Earth {VERSION} geladen: raw/natural_earth/{ziel.name} ({len(laender)} Einheiten, laut Quelle {ANZAHL_LAUT_QUELLE})")
    for schluessel in ZUSATZ:
        ordner_z = download_zusatz(schluessel)
        daten, _ = lade_zusatz(schluessel)
        print(f"Zusatzdatei {schluessel}: raw/natural_earth/{ordner_z.name} ({len(daten)} Einträge)")


if __name__ == "__main__":
    main()
