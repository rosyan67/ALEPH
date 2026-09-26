"""Daten für den Globus (web/globus.html): Nachtlicht-Monate und Einheiten.

Liest nur: den Nachtlicht-Würfel `cube/vnp46a3.zarr` und die Zell-Länder-
Zuordnung `laender/zell_einheiten/` auf der SSD (Pfad aus `.env`, über
`aleph/core/io.py`). Schreibt JavaScript-Dateien nach `web/daten/`, damit die
Seite per Doppelklick (file://) ohne Server läuft: Ein <script>-Tag darf lokale
Dateien laden, ein fetch() nicht.

Regeln (Auftrag 2026-09-26, CLAUDE.md, ARCHITECTURE.md Abschnitte 4 und 9a):
- Nur Monate mit `monat_fertig == 1` (vollständig nach der Regel vom
  2026-09-25) oder `== 4` (vollständig nur für Afrika-Europa-Asien; übrige
  Zellen bekommen die eigene Klasse „noch nicht geladen“, nie 0). Status 2
  („unvollständig“) wird nie ausgegeben.
- Nie Monate ab 2023-01 (Validierungs- und Endtestzeitraum), auch wenn fertig.
- Fehlende Daten sind nie 0: Eine Zelle ohne gültigen Pixel (keine Kachel,
  Polarsommer ohne Nacht, Fehlwert −999,9) bekommt die eigene Klasse
  KEINE_DATEN. Eine Zelle mit weniger als 50 % beobachteten Pixeln (Rest
  aufgefüllt aus historischen Daten oder Fehlwert) bekommt die Klasse
  „Datenlage unzureichend“ – dieselbe Grenze und dieselbe Rechnung wie die
  Anomalieerkennung (`aleph/detect/anomalie.py`, `min_beobachtet_anteil`).
- Angezeigt wird der Mittelwert nur über beobachtete Pixel
  (`allangle_mittel_beobachtet`, Evidenzstufe „beobachtet“); aufgefüllte
  Pixel sind keine Messung des Monats.
- Einheiten: Nur wenn die Zuordnung vollständig und unverändert ist (Prüfsummen
  und Anzahl gegen ihr Manifest). Sonst werden KEINE Grenzen ausgegeben – auch
  nicht die Standardansicht von Natural Earth (Sonderregel des Auftrags).
- Angezeigte Zugehörigkeiten stammen ausschließlich aus der Einheitentabelle;
  hier wird nichts ergänzt oder umgedeutet.

Kodierung eines Monats (zlib, dann Base64, im Browser mit DecompressionStream
entpackt): 720 × 1440 Werte uint16 (little endian, Zeile 0 = Nordrand 90°,
Spalte 0 = Westrand −180°), danach 720 × 1440 Werte uint8.
- uint16: Mittelwert beobachtet × WERT_SKALA, gerundet, auf 0 … WERT_MAX_CODE
  begrenzt (Zahl der begrenzten Zellen steht in der Statistik).
- uint8: Anteil beobachteter Pixel in ganzen Prozent (0–100, abgerundet),
  oder ANTEIL_KEINE_DATEN (255), wenn die Zelle keinen gültigen Pixel hat,
  oder ANTEIL_NICHT_GELADEN (254) in Monaten mit Zustand 4 („vollständig nur
  für Afrika-Europa-Asien“) für die Zellen außerhalb der Region (seit 2026-09-26).

Aufruf:  python -m aleph.export.globus            (schreibt web/daten/)
         python -m aleph.export.globus --pruefansicht 2018-03,2018-06 --ziel <ordner>
Die Prüfansicht schreibt einen UNVOLLSTÄNDIGEN Monat (Status 2) mit Warnvermerk,
nur zum Prüfen der Darstellung, nie in web/daten/.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from aleph.core import io
from aleph.detect.anomalie import _beobachtet_anteil

WUERFEL = "vnp46a3.zarr"
FELD = "allangle"  # Standardfeld seit 2026-09-24 (ARCHITECTURE.md Abschnitt 5)
EINHEIT = "nW·cm⁻²·sr⁻¹"
QUELLE_NACHTLICHT = "NASA VIIRS Black Marble VNP46A3, Collection 2, DOI 10.5067/VIIRS/VNP46A3.002 (LAADS DAAC)"

BREITE, LAENGE, ZELLE = 720, 1440, 0.25
PIXEL_JE_ZELLE = 3600  # 60 × 60 Rohpixel je 0,25°-Zelle
WERT_SKALA = 100  # Auflösung 0,01 nW·cm⁻²·sr⁻¹, Obergrenze 650 (2018-03 unvollständig: Höchstwert 388)
WERT_MAX_CODE = 65000
ANTEIL_KEINE_DATEN = 255
ANTEIL_NICHT_GELADEN = 254  # Zustand-4-Monat, Zelle außerhalb der Region: noch nicht geladen (nie „dunkel“)
MIN_BEOBACHTET_ANTEIL = 0.5  # wie aleph/detect/anomalie.py Schwellen.min_beobachtet_anteil
MONAT_FERTIG = 1
MONAT_REGION = 4  # aleph.layers.vnp46a3.MONAT_REGION_VOLLSTAENDIG
REGION = "afrika_europa_asien"
ZUSTAND_TEXT = {MONAT_FERTIG: "vollständig", MONAT_REGION: "nur Afrika-Europa-Asien"}
ENDTEST_AB = "2023-01"

# Kontrollzellen für den Selbsttest im Browser (Werte nach dem Entpacken
# müssen exakt gleich sein, sonst zeigt die Seite kein Nachtlicht).
KONTROLLORTE = {
    "Berlin": (52.52, 13.40),
    "Paris": (48.86, 2.35),
    "Sahara": (23.0, 12.0),
    "Atlantik": (30.0, -40.0),
    "Nordpolarmeer 85° N": (85.1, 0.1),
}

EINHEITEN_ORDNER = ("laender", "zell_einheiten")
EINHEITEN_PFLICHTSPALTEN = (
    "einheit_id", "name", "ebene", "herkunft_umriss", "kategorien", "un_m49", "un_name",
    "un_art", "un_beleg", "un_status", "beansprucht_von", "verwaltet_von", "anerkennung",
    "gueltig", "weltbank_code", "weltbank_art", "umriss_hinweis", "flaeche_km2", "umriss_wkb",
)
EINHEITEN_ANZEIGE = [c for c in EINHEITEN_PFLICHTSPALTEN if c not in ("umriss_wkb",)]
VEREINFACHUNG_GRAD = 0.01  # nur für die Darstellung; die Zuordnung rechnet mit den vollen Umrissen
KOORDINATEN_STELLEN = 3


class ExportFehler(RuntimeError):
    """Die Daten erfüllen eine Bedingung für die Anzeige nicht."""


# ---------------------------------------------------------------- Nachtlicht


def zelle_von(breite_grad: float, laenge_grad: float) -> tuple[int, int]:
    """Zeile/Spalte der 0,25°-Zelle (Zeile 0 = Nordrand, Spalte 0 = Westrand)."""
    zeile = int((90.0 - breite_grad) // ZELLE)
    spalte = int((laenge_grad + 180.0) // ZELLE)
    return min(max(zeile, 0), BREITE - 1), min(max(spalte, 0), LAENGE - 1)


def pruefe_gitter(ds) -> None:
    """Bricht ab, wenn der Würfel nicht das erwartete Gitter hat."""
    b = ds["breite"].values
    l = ds["laenge"].values
    if b.shape != (BREITE,) or l.shape != (LAENGE,):
        raise ExportFehler(f"Gitter {b.shape} × {l.shape}, erwartet {BREITE} × {LAENGE}")
    if not (np.isclose(b[0], 90 - ZELLE / 2) and np.isclose(b[-1], -90 + ZELLE / 2)):
        raise ExportFehler(f"Breite läuft von {b[0]} bis {b[-1]}, erwartet 89,875 bis −89,875")
    if not (np.isclose(l[0], -180 + ZELLE / 2) and np.isclose(l[-1], 180 - ZELLE / 2)):
        raise ExportFehler(f"Länge läuft von {l[0]} bis {l[-1]}, erwartet −179,875 bis 179,875")


def monatsstatus(ds) -> list[tuple[str, int]]:
    """(JJJJ-MM, Status) für jeden Monat der Zeitachse."""
    zeiten = [str(z)[:7] for z in ds["zeit"].values]
    status = [int(s) for s in ds["monat_fertig"].values]
    return list(zip(zeiten, status))


def anzeigbare_monate(ds) -> list[str]:
    """Monate mit Zustand 1 (fertig) oder 4 (nur Afrika-Europa-Asien), nur vor 2023-01."""
    return [m for m, s in monatsstatus(ds) if s in (MONAT_FERTIG, MONAT_REGION) and m < ENDTEST_AB]


def kodiere_monat(ds, monat: str, nicht_geladen: np.ndarray | None = None) -> dict:
    """Wert- und Anteil-Raster eines Monats plus Statistik und Kontrollzellen.

    `nicht_geladen` (bool, Breite × Länge): Zellen, die in diesem Monat noch nicht
    geladen sind (Zustand 4, außerhalb der Region). Sie bekommen ANTEIL_NICHT_GELADEN
    und keinen Wert - unabhängig davon, was im Würfel steht.
    """
    if monat >= ENDTEST_AB:
        raise ExportFehler(f"{monat} liegt im Validierungs-/Endtestzeitraum (ab {ENDTEST_AB})")
    s = ds.sel(zeit=f"{monat}-01")
    mittel_b = s[f"{FELD}_mittel_beobachtet"].values.astype("float64")
    # Zähler können als NaN kommen (lies_monate_mit_region setzt außerhalb der Region alles auf NaN);
    # diese Zellen werden unten ohnehin als „nicht geladen“ überschrieben.
    gueltig = np.nan_to_num(s[f"{FELD}_gueltige_pixel"].values.astype("float64"), nan=0.0)
    aufgefuellt = np.nan_to_num(s[f"{FELD}_aufgefuellt_pixel"].values.astype("float64"), nan=0.0)
    if nicht_geladen is None:
        nicht_geladen = np.zeros((BREITE, LAENGE), dtype=bool)

    anteil = _beobachtet_anteil(gueltig, aufgefuellt, PIXEL_JE_ZELLE)
    keine_daten = gueltig <= 0
    anteil_prozent = np.floor(anteil * 100 + 1e-9).astype("int64")
    anteil_u8 = np.where(keine_daten, ANTEIL_KEINE_DATEN, np.clip(anteil_prozent, 0, 100)).astype("uint8")

    anteil_u8[nicht_geladen] = ANTEIL_NICHT_GELADEN
    keine_daten = keine_daten & ~nicht_geladen
    zeigbar = (~keine_daten) & (~nicht_geladen) & (anteil >= MIN_BEOBACHTET_ANTEIL)
    # Ein zeigbarer Wert ohne Zahl wäre ein Widerspruch im Würfel: nicht still als 0 zeigen.
    widerspruch = zeigbar & ~np.isfinite(mittel_b)
    if widerspruch.any():
        raise ExportFehler(
            f"{monat}: {int(widerspruch.sum())} Zellen mit ≥ 50 % beobachteten Pixeln, aber ohne Mittelwert"
        )
    roh = np.where(np.isfinite(mittel_b), mittel_b, 0.0)
    negativ = int(((roh < 0) & zeigbar).sum())
    code = np.rint(roh * WERT_SKALA)
    begrenzt = int(((code > WERT_MAX_CODE) & zeigbar).sum())
    code = np.clip(code, 0, WERT_MAX_CODE).astype("<u2")
    code = np.where(zeigbar, code, 0).astype("<u2")  # nicht zeigbare Zellen tragen keinen Wert

    kontrolle = {}
    for name, (la, lo) in KONTROLLORTE.items():
        z, sp = zelle_von(la, lo)
        kontrolle[name] = {"zeile": z, "spalte": sp, "wert_code": int(code[z, sp]), "anteil": int(anteil_u8[z, sp])}

    werte = roh[zeigbar]
    statistik = {
        "zellen_gesamt": int(BREITE * LAENGE),
        "zellen_mit_wert": int(zeigbar.sum()),
        "zellen_keine_daten": int(keine_daten.sum()),
        "zellen_datenlage_unzureichend": int(((~keine_daten) & (~nicht_geladen) & ~zeigbar).sum()),
        "zellen_nicht_geladen": int(nicht_geladen.sum()),
        "zellen_negativ_auf_0_gesetzt": negativ,
        "zellen_oben_begrenzt": begrenzt,
        "wert_max": round(float(werte.max()), 1) if werte.size else None,
        "wert_p99": round(float(np.percentile(werte, 99)), 1) if werte.size else None,
    }
    rohbytes = code.tobytes() + anteil_u8.tobytes()
    return {
        "monat": monat,
        "breite": BREITE,
        "laenge": LAENGE,
        "wert_skala": WERT_SKALA,
        "wert_max_code": WERT_MAX_CODE,
        "anteil_keine_daten": ANTEIL_KEINE_DATEN,
        "anteil_nicht_geladen": ANTEIL_NICHT_GELADEN,
        "min_beobachtet_prozent": int(MIN_BEOBACHTET_ANTEIL * 100),
        "sha256_roh": hashlib.sha256(rohbytes).hexdigest(),
        "kontrolle": kontrolle,
        "statistik": statistik,
        "daten_b64": base64.b64encode(zlib.compress(rohbytes, 9)).decode("ascii"),
    }


def entpacke_monat(eintrag: dict) -> tuple[np.ndarray, np.ndarray]:
    """Gegenstück zu `kodiere_monat` (für Tests; der Browser macht dasselbe in JS)."""
    roh = zlib.decompress(base64.b64decode(eintrag["daten_b64"]))
    n = eintrag["breite"] * eintrag["laenge"]
    code = np.frombuffer(roh[: 2 * n], dtype="<u2").reshape(eintrag["breite"], eintrag["laenge"])
    anteil = np.frombuffer(roh[2 * n:], dtype="uint8").reshape(eintrag["breite"], eintrag["laenge"])
    return code, anteil


# ---------------------------------------------------------------- Einheiten


def _sha256_datei(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pruefe_einheiten(ordner: Path) -> tuple[bool, str]:
    """(vollständig?, Begründung). Vollständig heißt: Manifest da, Prüfsummen und Anzahl stimmen."""
    manifest_pfad = ordner / "manifest.json"
    if not manifest_pfad.exists():
        return False, "Einheitentabelle fehlt (kein manifest.json)"
    try:
        manifest = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return False, f"Manifest der Einheitentabelle nicht lesbar: {e}"
    dateien = manifest.get("dateien") or {}
    for name in ("einheiten.parquet", "zuordnung.parquet"):
        if name not in dateien:
            return False, f"{name} steht nicht im Manifest"
        pfad = ordner / name
        if not pfad.exists():
            return False, f"{name} fehlt"
        if _sha256_datei(pfad) != dateien[name]:
            return False, f"{name}: Prüfsumme weicht vom Manifest ab (Datei verändert oder unvollständig)"
    import pandas as pd

    e = pd.read_parquet(ordner / "einheiten.parquet")
    fehlend = [c for c in EINHEITEN_PFLICHTSPALTEN if c not in e.columns]
    if fehlend:
        return False, f"Spalten fehlen: {', '.join(fehlend)}"
    soll = (manifest.get("ergebnis") or {}).get("einheiten")
    if soll is None or len(e) != soll:
        return False, f"{len(e)} Einheiten, Manifest nennt {soll}"
    if e["einheit_id"].duplicated().any():
        return False, "doppelte einheit_id"
    return True, "vollständig (Prüfsummen und Anzahl gegen Manifest geprüft)"


def _hauptkategorie(kategorien: str) -> str:
    """Eine Kategorie für die Farbe; alle Kategorien bleiben im Popup sichtbar."""
    k = kategorien or ""
    if "besetzt/Konfliktzone" in k:
        return "besetzt/Konfliktzone"
    if "umstritten" in k:
        return "umstritten"
    if "Sonderstatus" in k:
        return "Sonderstatus/autonom"
    return ""


def _text(wert) -> str:
    if wert is None:
        return ""
    if isinstance(wert, float) and np.isnan(wert):
        return ""
    return str(wert)


def einheiten_geojson(ordner: Path) -> dict:
    """Einheiten als GeoJSON (WGS 84), Umrisse für die Darstellung vereinfacht."""
    import geopandas as gpd
    import pandas as pd
    from shapely import wkb
    from shapely.geometry import mapping

    e = pd.read_parquet(ordner / "einheiten.parquet")
    z = pd.read_parquet(ordner / "zuordnung.parquet")
    zellsumme = z.groupby("einheit_id")["anteil"].sum()

    geo = gpd.GeoSeries([wkb.loads(bytes(b)) if b is not None else None for b in e["umriss_wkb"]], crs="EPSG:6933")
    geo = geo.to_crs("EPSG:4326")
    features = []
    for i, zeile in enumerate(e.itertuples(index=False)):
        g = geo.iloc[i]
        if g is None or g.is_empty:
            geometrie = None
        else:
            g = g.simplify(VEREINFACHUNG_GRAD, preserve_topology=True)
            if g.is_empty:  # winzige Einheit: lieber unvereinfacht als verschwunden
                g = geo.iloc[i]
            geometrie = _runde(mapping(g))
        props = {c: _text(getattr(zeile, c)) for c in EINHEITEN_ANZEIGE if c != "flaeche_km2"}
        props["flaeche_km2"] = round(float(zeile.flaeche_km2), 1) if np.isfinite(zeile.flaeche_km2) else None
        summe = float(zellsumme.get(zeile.einheit_id, 0.0))
        props["zellen_summe_anteile"] = round(summe, 3)
        props["kleiner_als_eine_zelle"] = summe < 1.0
        props["sondereinheit"] = zeile.ebene.startswith("Sondereinheit")
        props["hauptkategorie"] = _hauptkategorie(zeile.kategorien)
        features.append({"type": "Feature", "id": i, "properties": props, "geometry": geometrie})
    return {"type": "FeatureCollection", "features": features}


def _runde(geometrie: dict) -> dict:
    def r(koord):
        if isinstance(koord, (list, tuple)) and koord and isinstance(koord[0], (int, float)):
            return [round(float(koord[0]), KOORDINATEN_STELLEN), round(float(koord[1]), KOORDINATEN_STELLEN)]
        return [r(k) for k in koord]

    return {"type": geometrie["type"], "coordinates": r(geometrie["coordinates"])}


# ---------------------------------------------------------------- Schreiben


def _js(variable: str, schluessel: str | None, inhalt) -> str:
    text = json.dumps(inhalt, ensure_ascii=False, separators=(",", ":"))
    if schluessel is None:
        return f"window.{variable} = {text};\n"
    return (
        f"window.{variable} = window.{variable} || {{}};\n"
        f"window.{variable}[{json.dumps(schluessel)}] = {text};\n"
    )


def _region_monat(monat: str):
    """Zustand-4-Monat über die geprüfte Lesefunktion aus aleph.layers.vnp46a3 (Stufe-1-Nachweis,
    Kachelliste mit Prüfsumme). Rückgabe: (Dataset mit NaN außerhalb der Region, Maske „nicht geladen“)."""
    from aleph.layers import vnp46a3, vnp46a3_regionen

    jahr, mon = (int(t) for t in monat.split("-"))
    variablen = [f"{FELD}_mittel_beobachtet", f"{FELD}_gueltige_pixel", f"{FELD}_aufgefuellt_pixel"]
    try:
        ds = vnp46a3.lies_monate_mit_region([(jahr, mon)], variablen, REGION)
    except vnp46a3.MonatUnvollstaendig as e:
        raise ExportFehler(f"{monat}: Region-Monat nicht belegt ({e})") from e
    # „Noch nicht geladen“ nur, wo NASA überhaupt Kacheln liefert (Referenzliste
    # der 540 Positionen). Zellen in Kacheln, die es nie gibt (Polkappen v00,
    # v16, v17), sind „keine Daten“ wie in fertigen Monaten – sie kommen nie.
    geliefert = vnp46a3_regionen.zellmaske(vnp46a3.lies_referenz_positionen(), BREITE, LAENGE)
    return ds, ds["nicht_geladen"].values[0] & geliefert


def exportiere(ziel: Path, pruefmonate: list[str] | None = None) -> dict:
    """Schreibt alle Dateien nach `ziel` und gibt den Datenstand zurück.

    Geschrieben wird zuerst in einen Hilfsordner neben `ziel`; erst wenn alles
    fertig ist, wird er gegen `ziel` getauscht. Bricht der Export ab, bleibt der
    alte, in sich stimmige Stand stehen (Datenstand und Monatsdateien passen zusammen).
    """
    import shutil

    endziel = ziel
    ziel = endziel.with_name(endziel.name + ".neu")
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)
    try:
        d = _exportiere_in(ziel, pruefmonate)
    except BaseException:
        shutil.rmtree(ziel, ignore_errors=True)
        raise
    alt = endziel.with_name(endziel.name + ".alt")
    if alt.exists():
        shutil.rmtree(alt)
    if endziel.exists():
        endziel.rename(alt)
    ziel.rename(endziel)
    if alt.exists():
        shutil.rmtree(alt)
    return d


def _exportiere_in(ziel: Path, pruefmonate: list[str] | None) -> dict:
    import xarray as xr

    ds = xr.open_zarr(io.wuerfel_pfad(WUERFEL))
    pruefe_gitter(ds)
    status = monatsstatus(ds)
    zaehlung = {str(k): sum(1 for _, s in status if s == k) for k in sorted({s for _, s in status})}

    pruefansicht = bool(pruefmonate)
    if not pruefansicht:
        monate = anzeigbare_monate(ds)
    else:
        for m in pruefmonate:
            if m >= ENDTEST_AB:
                raise ExportFehler(f"{m} liegt im Validierungs-/Endtestzeitraum")
        monate = list(pruefmonate)

    zustand_je_monat = dict(status)
    eintraege = []
    for m in monate:
        zustand = zustand_je_monat.get(m)
        if zustand == MONAT_REGION and not pruefansicht:
            region_ds, maske = _region_monat(m)
            eintrag = kodiere_monat(region_ds, m, nicht_geladen=maske)
        else:
            eintrag = kodiere_monat(ds, m)
        eintrag["pruefansicht"] = pruefansicht
        eintrag["zustand"] = zustand
        eintrag["zustand_text"] = ZUSTAND_TEXT.get(zustand, f"Zustand {zustand}")
        (ziel / f"nachtlicht_{m}.js").write_text(_js("ALEPH_NACHTLICHT", m, eintrag), encoding="utf-8")
        eintraege.append({k: eintrag[k] for k in ("monat", "statistik", "kontrolle", "zustand", "zustand_text")})

    ordner = io.aleph_data_dir().joinpath(*EINHEITEN_ORDNER)
    ok, grund = pruefe_einheiten(ordner)
    if ok:
        manifest = json.loads((ordner / "manifest.json").read_text(encoding="utf-8"))
        einheiten = {
            "verfuegbar": True,
            "grund": grund,
            "erstellt_utc": manifest.get("erstellt_utc"),
            "quellen": {k: {kk: vv for kk, vv in v.items() if kk in ("url", "version", "abruf_utc", "datei")}
                        for k, v in (manifest.get("quellen") or {}).items()},
            "sha256_einheiten": manifest["dateien"]["einheiten.parquet"],
            "geojson": einheiten_geojson(ordner),
        }
    else:
        einheiten = {"verfuegbar": False, "grund": grund}
    (ziel / "einheiten.js").write_text(_js("ALEPH_EINHEITEN", None, einheiten), encoding="utf-8")

    datenstand = {
        "erstellt_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pruefansicht": pruefansicht,
        "quelle": QUELLE_NACHTLICHT,
        "feld": f"{FELD}_mittel_beobachtet (AllAngle, schneefrei, nur beobachtete Pixel)",
        "einheit": EINHEIT,
        "evidenzstufe": "beobachtet",
        "monate_gesamt": len(status),
        "status_zaehlung": zaehlung,
        "status_bedeutung": {"0": "leer", "1": "fertig", "2": "unvollständig (wird neu geladen)", "3": "wird geschrieben",
                             "4": "vollständig nur für Afrika-Europa-Asien"},
        "fertig_alle": [m for m, s in status if s == MONAT_FERTIG],
        "region_alle": [m for m, s in status if s == MONAT_REGION],
        "fertig_gesperrt_endtest": [m for m, s in status if s in (MONAT_FERTIG, MONAT_REGION) and m >= ENDTEST_AB],
        "angezeigt": monate,
        "monate": eintraege,
        "min_beobachtet_prozent": int(MIN_BEOBACHTET_ANTEIL * 100),
        "einheiten_verfuegbar": einheiten["verfuegbar"],
        "einheiten_grund": einheiten["grund"],
    }
    (ziel / "datenstand.js").write_text(_js("ALEPH_DATENSTAND", None, datenstand), encoding="utf-8")
    return datenstand


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ziel", type=Path, default=Path(__file__).resolve().parents[2] / "web" / "daten")
    p.add_argument("--pruefansicht", metavar="JJJJ-MM[,JJJJ-MM]",
                   help="unvollständige Monate nur zum Prüfen der Darstellung ausgeben (nie nach web/daten)")
    a = p.parse_args(argv)
    standard = (Path(__file__).resolve().parents[2] / "web" / "daten").resolve()
    if a.pruefansicht and a.ziel.resolve() == standard:
        print("Abbruch: Eine Prüfansicht darf nicht nach web/daten geschrieben werden.", file=sys.stderr)
        return 2
    try:
        d = exportiere(a.ziel, a.pruefansicht.split(",") if a.pruefansicht else None)
    except (ExportFehler, io.SSDNichtGefunden) as e:
        print(f"Abbruch: {e}", file=sys.stderr)
        return 1
    print(f"Monate im Würfel: {d['monate_gesamt']}, Status-Zählung: {d['status_zaehlung']}")
    zt = {e["monat"]: e["zustand_text"] for e in d["monate"]}
    print("Angezeigt: " + (", ".join(f"{m} ({zt.get(m, '?')})" for m in d["angezeigt"])
                           or "kein Monat (noch keiner vollständig)"))
    if d["fertig_gesperrt_endtest"]:
        print(f"Fertig, aber gesperrt (ab {ENDTEST_AB}): {', '.join(d['fertig_gesperrt_endtest'])}")
    print(f"Einheiten: {'ja' if d['einheiten_verfuegbar'] else 'NEIN'} – {d['einheiten_grund']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
