"""Niederschlag (NASA GPM IMERG, monatlich) für den Globus: zweite, umschaltbare Ebene (Auftrag 2026-10-05, Teil 3).

Liest nur: den IMERG-Würfel `cube/imerg.zarr` über dieselbe Lesefunktion wie die Erkennung
(`aleph/detect/wuerfel.lies_monate`: liefert nur Monate mit `monat_fertig == 1`). Schreibt JavaScript-Dateien
nach `web/daten/` (wie aleph/export/globus.py, damit die Seite ohne Server läuft).

Regeln:
- Nur Monate vor 2023-01 (Validierungs- und Endtestzeitraum gesperrt), auch wenn sie im Würfel fertig sind.
- Gültig ist eine Zelle nach der Regel des Layers (`aleph.layers.imerg.nutzbar_maske`, gültiger Flächenanteil
  mindestens `MINDEST_GUELTIG_ANTEIL` = 0,5, festgelegt vor dem Ansehen der Daten). Darunter: „zu wenig Messungen“;
  ganz ohne gültigen Quellpixel: „keine Daten“. Beides nie als 0 mm.
- Angezeigt wird `precipitation_mm_monat` (Monatssumme, mm/Monat) und als Unsicherheit `random_error_mm_monat`
  (zufälliger Fehler laut Anbieter; als Flächenmittel eine Obergrenze, siehe Steckbrief docs/sources/imerg.md).
- Evidenzstufe „beobachtet“ (Satellitenschätzung, an Regenmesser angepasst). Kein Stationswert.
- Kennzeichen je Monat: TRMM-Kalibrierung bis 2014-05 (`kalibrierung_trmm`, möglicher Bruch).

Kodierung eines Monats (zlib, dann Base64): 720 × 1440 Werte uint16 (Niederschlag × WERT_SKALA, gerundet,
begrenzt auf WERT_MAX_CODE), dann 720 × 1440 uint8 (gültiger Flächenanteil in ganzen Prozent, abgerundet, oder
ANTEIL_KEINE_DATEN), dann 720 × 1440 uint16 (zufälliger Fehler in ganzen mm/Monat). Zeile 0 = Nordrand,
Spalte 0 = Westrand, wie beim Nachtlicht.
"""

from __future__ import annotations

import base64
import hashlib
import json
import zlib

import numpy as np

from aleph.core import io
from aleph.detect import wuerfel
from aleph.layers import imerg

WUERFEL = "imerg.zarr"
ENDTEST_AB = (2023, 1)
BREITE, LAENGE, ZELLE = 720, 1440, 0.25
WERT_SKALA = 10  # 0,1 mm/Monat; höchster Monatswert 2018 laut IMERG-Bericht 2289 mm, Obergrenze hier 6500 mm
WERT_MAX_CODE = 65000
FEHLER_MAX_CODE = 65000
ANTEIL_KEINE_DATEN = 255
EINHEIT = "mm/Monat"
VARIABLEN = ["precipitation_mm_monat", "precipitation_gueltig_anteil", "random_error_mm_monat"]
QUELLE = ("NASA GPM IMERG Final Run V07B, monatlich (GPM_3IMERGM), DOI 10.5067/GPM/IMERG/3B-MONTH/07, "
          "GES DISC; auf 0,25° flächengewichtet")
# Pflicht-Quellenangabe des Anbieters (docs/sources/imerg.md Abschnitt 6), wörtlich aus dem Würfel-Attribut `quelle`.
KONTROLLORTE = {
    "Mumbai": (19.08, 72.88),
    "Kairo": (30.04, 31.24),
    "Berlin": (52.52, 13.40),
    "Singapur": (1.35, 103.82),
    "Nordpol 89,9° N": (89.9, 0.1),
}


class NiederschlagFehler(RuntimeError):
    """Die Daten erfüllen eine Bedingung für die Anzeige nicht."""


def zelle_von(breite_grad: float, laenge_grad: float) -> tuple[int, int]:
    zeile = int((90.0 - breite_grad) // ZELLE)
    spalte = int((laenge_grad + 180.0) // ZELLE)
    return min(max(zeile, 0), BREITE - 1), min(max(spalte, 0), LAENGE - 1)


def anzeigbare_monate(pfad) -> list[tuple[int, int]]:
    return [m for m in wuerfel.fertige_monate(pfad) if tuple(m) < ENDTEST_AB]


def kodiere_monat(ds_monat, jahr: int, monat: int, trmm: bool) -> dict:
    """`ds_monat`: Dataset mit genau diesem Monat (Variablen VARIABLEN)."""
    if (jahr, monat) >= ENDTEST_AB:
        raise NiederschlagFehler(f"{jahr:04d}-{monat:02d} liegt im Validierungs-/Endtestzeitraum")
    if ds_monat["breite"].shape != (BREITE,) or not np.isclose(float(ds_monat["breite"].values[0]), 90 - ZELLE / 2):
        raise NiederschlagFehler("IMERG-Würfel hat nicht das Gitter des Nachtlicht-Würfels (Nordrand zuerst)")
    if ds_monat["laenge"].shape != (LAENGE,) or not np.isclose(float(ds_monat["laenge"].values[0]), -180 + ZELLE / 2):
        raise NiederschlagFehler("IMERG-Würfel: Länge beginnt nicht am Westrand")
    s = ds_monat.isel(zeit=0)
    mm = s["precipitation_mm_monat"].values.astype("float64")
    anteil = np.nan_to_num(s["precipitation_gueltig_anteil"].values.astype("float64"), nan=0.0)
    fehler = s["random_error_mm_monat"].values.astype("float64")
    nutzbar = np.asarray(imerg.nutzbar_maske(s)).astype(bool)

    keine_daten = anteil <= 0
    anteil_u8 = np.where(keine_daten, ANTEIL_KEINE_DATEN,
                         np.clip(np.floor(anteil * 100 + 1e-9), 0, 100)).astype("uint8")
    zeigbar = nutzbar & ~keine_daten
    widerspruch = zeigbar & ~np.isfinite(mm)
    if widerspruch.any():
        raise NiederschlagFehler(f"{jahr}-{monat:02d}: {int(widerspruch.sum())} gültige Zellen ohne Wert")
    negativ = int(((mm < 0) & zeigbar).sum())
    if negativ:
        raise NiederschlagFehler(f"{jahr}-{monat:02d}: {negativ} negative Niederschlagswerte")
    code = np.rint(np.where(zeigbar, mm, 0.0) * WERT_SKALA)
    begrenzt = int((code > WERT_MAX_CODE).sum())
    code = np.clip(code, 0, WERT_MAX_CODE).astype("<u2")
    f_code = np.clip(np.rint(np.where(zeigbar & np.isfinite(fehler), fehler, 0.0)), 0, FEHLER_MAX_CODE).astype("<u2")

    name = f"{jahr:04d}-{monat:02d}"
    kontrolle = {}
    for ort, (la, lo) in KONTROLLORTE.items():
        z, sp = zelle_von(la, lo)
        kontrolle[ort] = {"zeile": z, "spalte": sp, "wert_code": int(code[z, sp]), "anteil": int(anteil_u8[z, sp])}
    werte = mm[zeigbar]
    statistik = {
        "zellen_gesamt": BREITE * LAENGE,
        "zellen_mit_wert": int(zeigbar.sum()),
        "zellen_keine_daten": int(keine_daten.sum()),
        "zellen_zu_wenig": int((~keine_daten & ~zeigbar).sum()),
        "zellen_oben_begrenzt": begrenzt,
        "wert_max": round(float(werte.max()), 0) if werte.size else None,
        "wert_p99": round(float(np.percentile(werte, 99)), 0) if werte.size else None,
    }
    roh = code.tobytes() + anteil_u8.tobytes() + f_code.tobytes()
    return {
        "monat": name, "breite": BREITE, "laenge": LAENGE, "wert_skala": WERT_SKALA, "wert_max_code": WERT_MAX_CODE,
        "anteil_keine_daten": ANTEIL_KEINE_DATEN, "min_gueltig_prozent": int(imerg.MINDEST_GUELTIG_ANTEIL * 100),
        "kalibrierung_trmm": bool(trmm), "sha256_roh": hashlib.sha256(roh).hexdigest(), "kontrolle": kontrolle,
        "statistik": statistik, "daten_b64": base64.b64encode(zlib.compress(roh, 9)).decode("ascii"),
    }


def entpacke_monat(e: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gegenstück zu `kodiere_monat` (für Tests)."""
    roh = zlib.decompress(base64.b64decode(e["daten_b64"]))
    n = e["breite"] * e["laenge"]
    form = (e["breite"], e["laenge"])
    return (np.frombuffer(roh[:2 * n], "<u2").reshape(form), np.frombuffer(roh[2 * n:3 * n], "uint8").reshape(form),
            np.frombuffer(roh[3 * n:], "<u2").reshape(form))


def _js(variable: str, schluessel: str | None, inhalt) -> str:
    text = json.dumps(inhalt, ensure_ascii=False, separators=(",", ":"))
    if schluessel is None:
        return f"window.{variable} = {text};\n"
    return f"window.{variable} = window.{variable} || {{}};\nwindow.{variable}[{json.dumps(schluessel)}] = {text};\n"


def exportiere_in(ziel) -> dict:
    """Schreibt niederschlag_<JJJJ-MM>.js und niederschlag_stand.js nach `ziel`. Ohne Würfel: Stand „nicht verfügbar“."""
    pfad = io.wuerfel_pfad(WUERFEL)
    if not pfad.exists():
        stand = {"verfuegbar": False, "grund": "IMERG-Würfel nicht vorhanden"}
        (ziel / "niederschlag_stand.js").write_text(_js("ALEPH_NIEDERSCHLAG_STAND", None, stand), encoding="utf-8")
        return stand
    monate = anzeigbare_monate(pfad)
    import xarray as xr

    voll = xr.open_zarr(pfad)
    trmm_je_monat = {(int(str(z)[:4]), int(str(z)[5:7])): bool(t)
                     for z, t in zip(voll["zeit"].values, voll["kalibrierung_trmm"].values)}
    attrs = dict(voll.attrs)
    voll.close()
    eintraege = []
    for jahr, mon in monate:
        ds = wuerfel.lies_monate(pfad, [(jahr, mon)], VARIABLEN)
        e = kodiere_monat(ds, jahr, mon, trmm_je_monat.get((jahr, mon), False))
        (ziel / f"niederschlag_{e['monat']}.js").write_text(_js("ALEPH_NIEDERSCHLAG", e["monat"], e), encoding="utf-8")
        eintraege.append({k: e[k] for k in ("monat", "statistik", "kalibrierung_trmm")})
    stand = {
        "verfuegbar": bool(eintraege),
        "grund": "" if eintraege else "kein fertiger Monat vor 2023",
        "monate": [e["monat"] for e in eintraege],
        "monate_info": eintraege,
        "quelle": QUELLE,
        # Nur der Pflichtsatz des Anbieters; der interne Herkunftsvermerk im Attribut („(wörtlich aus …)“) bleibt weg.
        "quellenangabe": attrs.get("quelle", "").split(" (wörtlich", 1)[0].strip(),
        "zitierweise": attrs.get("zitierweise", ""),
        "version": attrs.get("version", ""),
        "einheit": EINHEIT,
        "evidenzstufe": "beobachtet",
        "evidenz_text": "Satellitenschätzung, an Regenmesser angepasst; Zellenmittel über rund 28 × 28 km, kein Stationswert",
        "min_gueltig_prozent": int(imerg.MINDEST_GUELTIG_ANTEIL * 100),
        "verminderte_guete_ab_breite": float(imerg.VERMINDERTE_GUETE_BREITENGRENZE),
        "kalibrierung_gpm_ab": "%04d-%02d" % imerg.KALIBRIERUNG_GPM_AB,
    }
    (ziel / "niederschlag_stand.js").write_text(_js("ALEPH_NIEDERSCHLAG_STAND", None, stand), encoding="utf-8")
    return stand
