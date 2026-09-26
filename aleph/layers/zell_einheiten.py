"""Zuordnung der 0,25°-Rasterzellen zu Ländern und Sondereinheiten nach Flächenanteil.

Entscheidungen (Nutzer, 2026-09-26):
- Jede Zelle wird nach **Flächenanteil** auf die Einheiten aufgeteilt, nicht nach der Zellmitte.
- ALEPH trifft keine eigenen Souveränitätsentscheidungen (Anweisung Punkt 7). Oberste Ebene ist die
  UN-Sicht (M49, aleph/layers/un_m49.py). Umstrittene Gebiete, besetzte Gebiete/Konfliktzonen und
  Gebiete mit Sonderstatus sind eigene, markierte Einheiten (aleph/layers/sondereinheiten.yaml) und
  gehen nie still im übergeordneten Staat auf. Jede Einheit kennt ihren übergeordneten M49-Eintrag
  (oder „unklar“) und, getrennt davon, welche Weltbank-Zahl ihr Gebiet enthält (Sicht „so wie die
  Weltbank zählt“, mit Art des Belegs).

Einheiten:
1. Sondereinheiten aus der YAML-Liste (Umrisse aus Natural Earth 5.1.1: Länder-, Umstritten- oder
   Provinzdatei; nichts ist selbst gezeichnet).
2. Automatisch weitere Einträge der Natural-Earth-Datei „umstrittene Gebiete“: alle mit einem Anspruch
   in NOTE_BRK („Claimed …“) oder Typ „Indeterminate“, außer den Typen „Overlay“ und „Lease“ (diese
   überlagern andere Einheiten: Pufferzonen, Pachtgebiete). Ein Eintrag, der mit einer Sondereinheit
   der Liste gegenseitig zu mindestens `DOPPEL_ANTEIL` übereinstimmt (derselbe Umriss aus der
   Länderdatei, z. B. Taiwan), wird als Doppel übersprungen. Die übersprungenen Einträge stehen mit
   Grund im Ergebnis (`nicht_aufgenommen`). Einen M49-Eintrag bekommt ein solcher Eintrag nur, wenn er
   (fast) eine ganze Einheit der Länderdatei ist, deren ISO-Code dort nur einmal vorkommt und in M49
   steht, oder wenn sein Name genau einem M49-Namen entspricht; sonst „unklar“.
3. Grundeinheiten: die 258 Einheiten der Natural-Earth-Länderdatei, jeweils ohne die Flächen der
   Sondereinheiten. Bleibt fast nichts übrig (unter `MIN_REST_KM2`), entfällt die Grundeinheit; auch
   das steht im Ergebnis.
Überschneiden sich Sondereinheiten, hat die kleinere Vorrang (Regel seit 2026-09-26: So bleibt ein
umstrittenes Gebiet innerhalb eines anderen sichtbar, z. B. die Hans-Insel in Grönland oder Aksai Chin
am Rand Tibets). Die dabei abgezogene Fläche wird je Einheit festgehalten
(`flaeche_ueberschneidung_km2`). Eine Grundeinheit entfällt nur, wenn Sondereinheiten sie bis auf weniger
als `MIN_REST_KM2` überdecken; kleine Länder ohne Überdeckung (z. B. Vatikan) bleiben immer.

Raster: exakt das Gitter des Nachtlicht-Würfels. Die Definition wird aus `aleph/layers/vnp46a3.py`
gelesen (GITTER_BREITE, GITTER_LAENGE, ZELLGROESSE, _gitter_koordinaten; nur Import, nichts geändert)
und, wenn der Würfel auf der SSD liegt, zusätzlich gegen dessen Koordinaten geprüft (nur lesend).

Fläche auf der Kugel: gerechnet in der flächentreuen Zylinderprojektion EPSG:6933 (WGS 84, auf dem
Ellipsoid). Darin sind die Zellen Rechtecke mit ihrer echten Ellipsoid-Fläche (Zellen werden zu den
Polen kleiner), und Flächenanteile sind echte Flächenanteile. Die Umrisse werden vorher in Grad auf
höchstens `VERDICHTUNG_GRAD` lange Kanten verdichtet, damit eine gerade Kante in Länge/Breite (so sind
die Natural-Earth-Daten gezeichnet) auch nach der Projektion so verläuft. Datumsgrenze: Natural Earth
teilt Umrisse bei ±180° (geprüft: alle Koordinaten in [−180, 180]); Spalte 0 beginnt bei −180°,
Spalte 1439 endet bei +180°, beide Seiten werden also getrennt, aber vollständig erfasst.

Ergebnis auf der SSD unter laender/zell_einheiten/: `einheiten.parquet` (eine Zeile je Einheit, mit
Quellen und Fläche), `zuordnung.parquet` (Zelle → Einheit → Anteil), `manifest.json` (Quellen mit
Prüfsummen, Version der Grenzdatei, Fingerabdruck der Eingaben und des Ergebnisses).

Evidenzstufe: keine Messung. Die Zuordnung ist eine Festlegung aus redaktionellen Grenzen (Natural
Earth) und UN-Dokumenten; ihre Unsicherheit liegt in den Grenzen selbst, nicht in der Rechnung.
"""

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
import yaml
from pyproj import Geod, Transformer
from shapely.ops import unary_union
from shapely.validation import make_valid

from aleph.core import io
from aleph.layers import natural_earth as ne
from aleph.layers import un_m49
from aleph.layers import vnp46a3  # nur die Gitterdefinition des Nachtlicht-Würfels wird gelesen

SONDER_DATEI = Path(__file__).with_name("sondereinheiten.yaml")
PROJEKTION = "EPSG:6933"
VERDICHTUNG_GRAD = 0.05
BLOCK = 20  # Zellen je Blockkante (5°) für die schnelle Vorauswahl
DOPPEL_ANTEIL = 0.95
MIN_REST_KM2 = 1.0
AUSGESCHLOSSENE_TYPEN = ("Overlay", "Lease")
KATEGORIEN = ("umstritten", "besetzt/Konfliktzone", "Sonderstatus/autonom")
UN_ARTEN = ("ausdrücklich", "abgeleitet", "unklar", "M49-Eintrag (gleicher ISO-Code)", "nicht in M49")
WELTBANK_ARTEN = ("belegt", "abgeleitet", "unklar", "keine", "abweichend", "ohne Gebietshinweis")

_ZU_PROJ = Transformer.from_crs("EPSG:4326", PROJEKTION, always_xy=True)
_GEOD = Geod(ellps="WGS84")


class ZuordnungFehler(RuntimeError):
    """Eingaben oder Ergebnis stimmen nicht: Abbruch, nichts wird geschrieben."""


# --- Raster -------------------------------------------------------------------


def gitter():
    """Gitter des Nachtlicht-Würfels: Zellmitten (Breite fallend, Länge steigend) und Zellkanten in Grad."""
    breite, laenge = vnp46a3._gitter_koordinaten()
    halb = vnp46a3.ZELLGROESSE / 2
    breite_kanten = np.round(np.concatenate([[breite[0] + halb], breite - halb]), 10)
    laenge_kanten = np.round(np.concatenate([laenge - halb, [laenge[-1] + halb]]), 10)
    if len(breite) != vnp46a3.GITTER_BREITE or len(laenge) != vnp46a3.GITTER_LAENGE:
        raise ZuordnungFehler("Gitterdefinition in vnp46a3.py ist in sich nicht stimmig.")
    if breite_kanten[0] != 90 or breite_kanten[-1] != -90 or laenge_kanten[0] != -180 or laenge_kanten[-1] != 180:
        raise ZuordnungFehler("Gitterkanten decken nicht genau −90…90° / −180…180° ab.")
    return breite, laenge, breite_kanten, laenge_kanten


def pruefe_gegen_wuerfel():
    """Vergleicht die Gitterkoordinaten mit denen des Nachtlicht-Würfels auf der SSD (nur lesend).

    Liefert True (gleich), None (kein Würfel vorhanden) oder bricht ab (abweichend).
    """
    import xarray as xr

    pfad = io.wuerfel_pfad("vnp46a3.zarr")
    if not pfad.exists():
        return None
    breite, laenge, _, _ = gitter()
    with xr.open_zarr(pfad, chunks=None) as ds:
        wb, wl = ds["breite"].values, ds["laenge"].values
    if not (np.array_equal(wb, breite) and np.array_equal(wl, laenge)):
        raise ZuordnungFehler("Gitter der Zuordnung weicht vom Gitter des Nachtlicht-Würfels ab.")
    return True


def _kanten_projiziert():
    _, _, breite_kanten, laenge_kanten = gitter()
    x, _ = _ZU_PROJ.transform(laenge_kanten, np.zeros_like(laenge_kanten))
    _, y = _ZU_PROJ.transform(np.zeros_like(breite_kanten), breite_kanten)
    return np.asarray(x), np.asarray(y)  # x steigend (West → Ost), y fallend (Nord → Süd)


def zellflaechen_km2():
    """Fläche jeder Zeile (alle Zellen einer Zeile sind gleich groß) in km², Ellipsoid WGS 84."""
    x, y = _kanten_projiziert()
    return (y[:-1] - y[1:]) * (x[1] - x[0]) / 1e6


# --- Geometrie ----------------------------------------------------------------


def projiziere(geometrie):
    """Grad → EPSG:6933, vorher auf höchstens VERDICHTUNG_GRAD lange Kanten verdichtet."""
    verdichtet = shapely.segmentize(geometrie, VERDICHTUNG_GRAD)
    return shapely.transform(verdichtet, lambda xy: np.column_stack(_ZU_PROJ.transform(xy[:, 0], xy[:, 1])))


def projiziere_gueltig(geometrie, name, reparaturen):
    """Wie `projiziere`, prüft aber die Gültigkeit danach. Repariert nur ohne Flächenänderung (relativ 1e-9),
    sonst Abbruch; jede Reparatur wird in `reparaturen` festgehalten."""
    g = projiziere(geometrie)
    if g.is_valid:
        return g
    neu = _nur_flaechen(make_valid(g))
    if not neu.is_valid or abs(neu.area - g.area) > 1e-9 * max(g.area, 1.0):
        raise ZuordnungFehler(f"Umriss {name} ist nach der Projektion ungültig und nicht ohne Flächenänderung reparierbar.")
    reparaturen.append(name)
    return neu


def geodaetische_flaeche_km2(geometrie_grad):
    """Unabhängige Vergleichsfläche: Ellipsoid-Fläche nach pyproj.Geod (Kanten als Geodäten)."""
    return abs(_GEOD.geometry_area_perimeter(geometrie_grad)[0]) / 1e6


def _nur_flaechen(geometrie):
    if geometrie.is_empty:
        return geometrie
    teile = []
    for teil in getattr(geometrie, "geoms", [geometrie]):
        if teil.geom_type == "Polygon":
            teile.append(teil)
        elif teil.geom_type == "MultiPolygon":
            teile.extend(teil.geoms)
    return shapely.MultiPolygon(teile) if teile else shapely.MultiPolygon()


# --- Einheiten ----------------------------------------------------------------


def lade_sonderliste(pfad=SONDER_DATEI):
    daten = yaml.safe_load(Path(pfad).read_text(encoding="utf-8"))
    ids = [e["id"] for e in daten["einheiten"]]
    if len(ids) != len(set(ids)):
        raise ZuordnungFehler("Doppelte id in sondereinheiten.yaml.")
    for e in daten["einheiten"]:
        falsch = set(e["kategorien"]) - set(KATEGORIEN)
        if falsch or not e["kategorien"]:
            raise ZuordnungFehler(f"{e['id']}: Kategorien {e['kategorien']} ungültig.")
        if e["un_art"] not in UN_ARTEN or e["weltbank_art"] not in WELTBANK_ARTEN:
            raise ZuordnungFehler(f"{e['id']}: un_art oder weltbank_art ungültig.")
        if (e["un_m49"] is None) != (e["un_art"] == "unklar"):
            raise ZuordnungFehler(f"{e['id']}: un_m49 muss genau dann leer sein, wenn un_art „unklar“ ist.")
    return daten


def _quelle_waehlen(g, laender, umstritten, provinzen):
    tabelle = {"laender": laender, "umstritten": umstritten, "provinzen": provinzen}[g["datei"]]
    treffer = tabelle[tabelle[g["feld"]] == g["wert"]]
    if len(treffer) != 1:
        raise ZuordnungFehler(f"Umriss {g}: {len(treffer)} Treffer statt genau einem.")
    return treffer.iloc[0]


def baue_einheiten(laender, umstritten, provinzen, m49, sonder):
    """Baut alle Einheiten mit projizierter Geometrie.

    Liefert (Einheiten-Tabelle, Geometrien, nicht_aufgenommen, Landfläche gesamt, reparierte Umrisse).
    """
    m49_iso = dict(zip(m49["iso3"], m49["m49"]))
    m49_name = dict(zip(m49["m49"], m49["name"]))
    wb_hinweise = sonder.get("weltbank_laender", {})
    code_zu_iso = dict(zip(laender["ADM0_A3"], laender["land_iso3"]))
    iso_eh = dict(zip(laender["ADM0_A3"], laender["ISO_A3_EH"]))
    iso_anzahl = laender["ISO_A3_EH"].value_counts().to_dict()
    m49_nach_name = dict(zip(m49["name"], m49["m49"]))

    reparaturen = []
    land_proj = {r.ADM0_A3: projiziere_gueltig(r.geometry, f"laender {r.ADM0_A3}", reparaturen) for r in laender.itertuples()}
    land_gesamt = unary_union(list(land_proj.values()))
    shapely.prepare(land_gesamt)

    eintraege, geometrien, nicht_aufgenommen = [], [], []

    def sonder_eintrag(e, herkunft):
        return {
            "einheit_id": e["id"], "name": e["name"], "ebene": "Sondereinheit", "herkunft_umriss": herkunft,
            "kategorien": ", ".join(e["kategorien"]), "un_m49": e["un_m49"],
            "un_name": m49_name.get(e["un_m49"]) if e["un_m49"] else None, "un_art": e["un_art"],
            "un_beleg": e["un_beleg"], "un_status": e["un_status"], "beansprucht_von": e["beansprucht_von"],
            "verwaltet_von": e["verwaltet_von"], "anerkennung": e["anerkennung"], "gueltig": e["gueltig"],
            "weltbank_code": e["weltbank_code"], "weltbank_art": e["weltbank_art"], "weltbank_beleg": e["weltbank_beleg"],
            "umriss_hinweis": e.get("umriss_hinweis", ""),
        }

    # 1. Sondereinheiten aus der Liste (ohne Provinz-Umrisse)
    liste = [e for e in sonder["einheiten"] if e["geometrie"]["datei"] != "provinzen"]
    provinz_liste = [e for e in sonder["einheiten"] if e["geometrie"]["datei"] == "provinzen"]
    for e in liste:
        for code in [e["un_m49"]] if e["un_m49"] else []:
            if code not in m49_name:
                raise ZuordnungFehler(f"{e['id']}: M49-Code {code} steht nicht in der M49-Liste.")
        zeile = _quelle_waehlen(e["geometrie"], laender, umstritten, provinzen)
        g = e["geometrie"]
        eintraege.append(sonder_eintrag(e, f"Natural Earth {ne.VERSION} {g['datei']} {g['feld']}={g['wert']}"))
        geometrien.append(projiziere_gueltig(zeile.geometry, e["id"], reparaturen))

    # 2. weitere Einträge der Umstritten-Datei nach fester Regel
    benutzt = {e["geometrie"]["wert"] for e in sonder["einheiten"] if e["geometrie"]["datei"] == "umstritten"}
    for r in umstritten.itertuples():
        if r.BRK_A3 in benutzt:
            continue
        grund = None
        notiz = r.NOTE_BRK if isinstance(r.NOTE_BRK, str) else ""
        if r.TYPE in AUSGESCHLOSSENE_TYPEN:
            grund = f"Typ „{r.TYPE}“ (überlagert andere Einheiten)"
        elif "laimed" not in notiz and r.TYPE != "Indeterminate":
            grund = "kein Anspruch in NOTE_BRK und nicht „Indeterminate“"
        g = projiziere_gueltig(r.geometry, f"umstritten {r.BRK_A3}", reparaturen)
        if grund is None and g.area > 0:
            for liste_g, liste_e in zip(geometrien, eintraege):
                gemeinsam = shapely.intersection(g, liste_g).area
                if gemeinsam >= DOPPEL_ANTEIL * g.area and gemeinsam >= DOPPEL_ANTEIL * liste_g.area:
                    grund = f"Doppel: derselbe Umriss wie Sondereinheit {liste_e['einheit_id']}"
                    break
        if grund:
            nicht_aufgenommen.append({"quelle": "umstritten", "brk_a3": r.BRK_A3, "name": r.BRK_NAME, "typ": r.TYPE,
                                      "notiz": notiz, "flaeche_km2": g.area / 1e6, "grund": grund})
            continue
        # M49 nur, wenn der Eintrag (fast) eine ganze NE-Einheit mit M49-Code ist, oder bei gleichem Namen
        un_code, un_art, un_beleg = None, "unklar", "keine UN-Quelle zu diesem Gebiet gelesen"
        adm = r.ADM0_A3
        iso_adm = iso_eh.get(adm)
        if adm in land_proj and iso_adm in m49_iso and iso_anzahl.get(iso_adm) == 1:
            einheit = land_proj[adm]
            if einheit.area > 0 and shapely.intersection(einheit, g).area >= DOPPEL_ANTEIL * einheit.area:
                un_code = m49_iso[iso_adm]
        if un_code is None and r.BRK_NAME in m49_nach_name:
            un_code = m49_nach_name[r.BRK_NAME]
        if un_code is not None:
            un_art, un_beleg = "ausdrücklich", f"M49 führt das Gebiet als eigenen Eintrag ({un_code}, {m49_name[un_code]})"
        wb_kandidat = code_zu_iso.get(adm)
        eintraege.append({
            "einheit_id": f"ne_umstritten_{r.BRK_A3}", "name": r.BRK_NAME, "ebene": "Sondereinheit (automatisch)",
            "herkunft_umriss": f"Natural Earth {ne.VERSION} umstritten BRK_A3={r.BRK_A3}",
            "kategorien": "umstritten", "un_m49": un_code, "un_name": m49_name.get(un_code) if un_code else None,
            "un_art": un_art, "un_beleg": un_beleg, "un_status": "unklar",
            "beansprucht_von": f"NE_UMSTR: „{notiz}“" if notiz else "unklar",
            "verwaltet_von": f"NE_UMSTR: „{notiz}“" if notiz else "unklar", "anerkennung": "unklar",
            "gueltig": f"Umriss NE {ne.VERSION} (Typ „{r.TYPE}“); Zeitraum unklar",
            "weltbank_code": wb_kandidat if isinstance(wb_kandidat, str) else None,
            "weltbank_art": "unklar", "weltbank_beleg": "keine Gebietsangabe der Weltbank; Code = verwaltende Grundeinheit laut NE",
        })
        geometrien.append(g)

    # 3. Provinz-Umrisse (Tibet); die Reihenfolge beim Abziehen bestimmt danach die Fläche
    for e in provinz_liste:
        zeile = _quelle_waehlen(e["geometrie"], laender, umstritten, provinzen)
        g = e["geometrie"]
        eintrag = sonder_eintrag(e, f"Natural Earth {ne.VERSION} {g['datei']} {g['feld']}={g['wert']}")
        eintrag["_mutterland"] = zeile["adm0_a3"]
        eintraege.append(eintrag)
        geometrien.append(projiziere_gueltig(zeile.geometry, e["id"], reparaturen))

    # Überschneidungen der Sondereinheiten nach Reihenfolge auflösen, auf Land begrenzen
    roh_alle = [shapely.intersection(g, land_gesamt) for g in geometrien]
    reihenfolge = sorted(range(len(eintraege)), key=lambda i: (roh_alle[i].area, eintraege[i]["einheit_id"]))
    eintraege = [eintraege[i] for i in reihenfolge]
    geometrien = [geometrien[i] for i in reihenfolge]
    roh_alle = [roh_alle[i] for i in reihenfolge]
    fertig, belegt = [], shapely.MultiPolygon()
    for eintrag, g, roh in zip(eintraege, geometrien, roh_alle):
        neu = _nur_flaechen(shapely.difference(roh, belegt))
        eintrag["flaeche_ueberschneidung_km2"] = (roh.area - neu.area) / 1e6
        eintrag["flaeche_ausserhalb_land_km2"] = (g.area - roh.area) / 1e6
        mutter = eintrag.pop("_mutterland", None)
        if mutter is not None:
            # Ein Provinz-Umriss darf keine Fläche eines anderen Landes nehmen (Provinz- und Länderdatei
            # können an den Rändern voneinander abweichen). Fläche außerhalb des Mutterlandes, die nicht
            # schon an kleinere Sondereinheiten ging, führt zum Abbruch.
            if mutter not in land_proj:
                raise ZuordnungFehler(f"{eintrag['einheit_id']}: Mutterland {mutter} fehlt in der Länderdatei.")
            fremd = shapely.difference(neu, land_proj[mutter]).area / 1e6
            if fremd > MIN_REST_KM2:
                raise ZuordnungFehler(f"{eintrag['einheit_id']}: {fremd:.1f} km² liegen außerhalb des Mutterlandes {mutter}.")
            eintrag["flaeche_ausserhalb_mutterland_km2"] = fremd
        fertig.append(neu)
        belegt = shapely.union(belegt, neu)

    # Grundeinheiten: Länderdatei ohne Sondereinheiten
    shapely.prepare(belegt)
    for r in laender.itertuples():
        g = land_proj[r.ADM0_A3]
        rest = _nur_flaechen(shapely.difference(g, belegt)) if shapely.intersects(g, belegt) else g
        iso = r.ISO_A3_EH if r.ISO_A3_EH != ne.PLATZHALTER else None
        un_code = m49_iso.get(iso)
        wb = r.land_iso3 if isinstance(r.land_iso3, str) else None
        hinweis = wb_hinweise.get(wb, {}) if wb else {}
        art = {"passt": "belegt", "abweichend": "abweichend", "unklar": "unklar"}.get(hinweis.get("gebiet"), "ohne Gebietshinweis")
        if rest.area / 1e6 < MIN_REST_KM2 and g.area - rest.area > 0:
            nicht_aufgenommen.append({"quelle": "laender", "brk_a3": r.ADM0_A3, "name": r.ADMIN, "typ": r.TYPE, "notiz": "",
                                      "flaeche_km2": rest.area / 1e6,
                                      "grund": f"Rest nach Abzug der Sondereinheiten unter {MIN_REST_KM2} km² (Fläche ganz in Sondereinheiten)"})
            continue
        eintraege.append({
            "einheit_id": f"land_{r.ADM0_A3}", "name": r.ADMIN, "ebene": "Land (Grenzdatei)",
            "herkunft_umriss": f"Natural Earth {ne.VERSION} laender ADM0_A3={r.ADM0_A3}, ohne Sondereinheiten",
            "kategorien": "", "un_m49": un_code, "un_name": m49_name.get(un_code) if un_code else None,
            "un_art": "M49-Eintrag (gleicher ISO-Code)" if un_code else "nicht in M49",
            "un_beleg": f"ISO_A3_EH {iso} = ISO-alpha3 des M49-Eintrags" if un_code else f"ISO_A3_EH {r.ISO_A3_EH} nicht in M49",
            "un_status": "", "beansprucht_von": "", "verwaltet_von": "", "anerkennung": "", "gueltig": f"Umriss NE {ne.VERSION}",
            "weltbank_code": wb, "weltbank_art": art if wb else "keine", "weltbank_beleg": hinweis.get("beleg", ""),
            "flaeche_ueberschneidung_km2": (g.area - rest.area) / 1e6, "flaeche_ausserhalb_land_km2": 0.0,
        })
        fertig.append(rest)

    tabelle = pd.DataFrame(eintraege)
    if tabelle["einheit_id"].duplicated().any():
        raise ZuordnungFehler("einheit_id ist nicht eindeutig.")
    return tabelle, fertig, pd.DataFrame(nicht_aufgenommen), land_gesamt, reparaturen


# --- Zellanteile -----------------------------------------------------------------


def zellanteile(geometrie, x_kanten, y_kanten, zellflaeche_zeile_m2):
    """Flächenanteile einer (projizierten) Geometrie je Zelle. Liefert Arrays zeile, spalte, flaeche_m2, anteil."""
    if geometrie.is_empty:
        return (np.empty(0, int),) * 2 + (np.empty(0),) * 2
    minx, miny, maxx, maxy = geometrie.bounds
    s0 = max(int(np.searchsorted(x_kanten, minx, "right")) - 1, 0)
    s1 = min(int(np.searchsorted(x_kanten, maxx, "left")), len(x_kanten) - 1)
    neg_y = -y_kanten
    z0 = max(int(np.searchsorted(neg_y, -maxy, "right")) - 1, 0)
    z1 = min(int(np.searchsorted(neg_y, -miny, "left")), len(y_kanten) - 1)
    shapely.prepare(geometrie)
    zeilen, spalten, flaechen = [], [], []
    for zb in range(z0, z1, BLOCK):
        ze = min(zb + BLOCK, z1)
        for sb in range(s0, s1, BLOCK):
            se = min(sb + BLOCK, s1)
            block = shapely.box(x_kanten[sb], y_kanten[ze], x_kanten[se], y_kanten[zb])
            if not shapely.intersects(geometrie, block):
                continue
            zz, ss = np.meshgrid(np.arange(zb, ze), np.arange(sb, se), indexing="ij")
            zz, ss = zz.ravel(), ss.ravel()
            if shapely.contains(geometrie, block):
                f = (y_kanten[zz] - y_kanten[zz + 1]) * (x_kanten[ss + 1] - x_kanten[ss])
            else:
                teil = shapely.intersection(geometrie, block)
                kaesten = shapely.box(x_kanten[ss], y_kanten[zz + 1], x_kanten[ss + 1], y_kanten[zz])
                treffer = shapely.intersects(kaesten, teil)
                zz, ss = zz[treffer], ss[treffer]
                f = shapely.area(shapely.intersection(kaesten[treffer], teil))
            gut = f > 0
            zeilen.append(zz[gut]); spalten.append(ss[gut]); flaechen.append(f[gut])
    if not zeilen:
        return (np.empty(0, int),) * 2 + (np.empty(0),) * 2
    z, s, f = np.concatenate(zeilen), np.concatenate(spalten), np.concatenate(flaechen)
    return z, s, f, f / zellflaeche_zeile_m2[z]


def baue_zuordnung(einheiten, geometrien):
    """Zelle → Einheit → Anteil für alle Einheiten. Prüft: Summe je Zelle höchstens 1 (+ Rundung)."""
    x, y = _kanten_projiziert()
    zf = (y[:-1] - y[1:]) * (x[1] - x[0])
    teile = []
    for eid, g in zip(einheiten["einheit_id"], geometrien):
        z, s, f, a = zellanteile(g, x, y, zf)
        teile.append(pd.DataFrame({"zeile": z.astype("int16"), "spalte": s.astype("int16"), "einheit_id": eid,
                                   "flaeche_km2": f / 1e6, "anteil": a}))
    zuordnung = pd.concat(teile, ignore_index=True)
    breite, laenge, _, _ = gitter()
    zuordnung["breite"] = breite[zuordnung["zeile"]]
    zuordnung["laenge"] = laenge[zuordnung["spalte"]]
    return zuordnung


def pruefe_summen(zuordnung, toleranz=1e-9):
    """Größte Summe der Anteile je Zelle; bricht ab, wenn sie über 1 + toleranz liegt."""
    summe = zuordnung.groupby(["zeile", "spalte"])["anteil"].sum()
    if summe.max() > 1 + toleranz:
        schlimm = summe[summe > 1 + toleranz].sort_values(ascending=False).head(10)
        raise ZuordnungFehler(f"Summe der Anteile über 1 in {int((summe > 1 + toleranz).sum())} Zellen, z. B. {schlimm.to_dict()}")
    return float(summe.max())


def pruefe_landflaeche(zuordnung, land_gesamt, toleranz=1e-6):
    """Erhaltung je Zelle: Summe der Anteile = Landanteil der Zelle, direkt aus der Vereinigung aller Länder
    der Grenzdatei gerechnet (unabhängig vom Bau der Einheiten). Liefert die größte Abweichung; bricht ab,
    wenn sie über `toleranz` liegt (dann wäre Land verloren gegangen oder doppelt gezählt)."""
    x, y = _kanten_projiziert()
    zf = (y[:-1] - y[1:]) * (x[1] - x[0])
    z, s, _, a = zellanteile(land_gesamt, x, y, zf)
    land = pd.Series(a, index=pd.MultiIndex.from_arrays([z, s], names=["zeile", "spalte"]))
    summe = zuordnung.groupby(["zeile", "spalte"])["anteil"].sum()
    alle = land.index.union(summe.index)
    abw = (summe.reindex(alle).fillna(0) - land.reindex(alle).fillna(0)).abs()
    if abw.max() > toleranz:
        raise ZuordnungFehler(f"Summe der Anteile weicht in {int((abw > toleranz).sum())} Zellen vom Landanteil ab (max {abw.max():.2e}).")
    return float(abw.max())


def reinheit(einheiten, zuordnung, schluessel="weltbank_code", schwelle=0.9):
    """Reinheitsmaß je Gruppe (Vorschlag statistik-pruefer 2026-09-26): Anteil der Fläche einer Gruppe, der in
    Zellen liegt, in denen die Gruppe mindestens `schwelle` des Landes der Zelle stellt. Braucht keine BIP-Daten.

    Niedrige Werte heißen: Die Gruppe liegt überwiegend in Zellen, die sie mit anderen Ländern teilt (Mischung).
    Gruppen ohne Schlüssel (leer) werden nicht bewertet."""
    z = zuordnung.merge(einheiten[["einheit_id", schluessel]], on="einheit_id")
    z = z[z[schluessel].notna()]
    land = zuordnung.groupby(["zeile", "spalte"])["anteil"].sum().rename("land")
    je = z.groupby([schluessel, "zeile", "spalte"]).agg(anteil=("anteil", "sum"), flaeche=("flaeche_km2", "sum")).reset_index()
    je = je.join(land, on=["zeile", "spalte"])
    je["rein"] = je["anteil"] / je["land"] >= schwelle
    ergebnis = je.groupby(schluessel).apply(lambda g: pd.Series({
        "flaeche_km2": g["flaeche"].sum(),
        "reinheit": g.loc[g["rein"], "flaeche"].sum() / g["flaeche"].sum() if g["flaeche"].sum() > 0 else np.nan,
        "zellen": len(g)}), include_groups=False)
    return ergebnis.sort_values("reinheit")


def weltbank_sicht(einheiten, mit_unklar=True):
    """Sicht „so wie die Weltbank zählt“: Zuordnung Einheit → Weltbank-Code.

    mit_unklar=True (Hauptsicht): alle Einheiten mit gesetztem `weltbank_code` (bei „unklar“ ist das der
    verwaltende Staat laut Natural Earth). mit_unklar=False (Gegenprobe): Einheiten mit `weltbank_art` „unklar“
    fallen weg. Einheiten ohne Code (z. B. Taiwan, Krim, Nordzypern) gehören in keiner der beiden Sichten zu einem
    Weltbank-Land. Welche Sicht benutzt wurde, muss jedes Ergebnis nennen."""
    sicht = einheiten[einheiten["weltbank_code"].notna()]
    if not mit_unklar:
        sicht = sicht[sicht["weltbank_art"] != "unklar"]
    return sicht.set_index("einheit_id")["weltbank_code"]


def zu_klein(einheiten, zuordnung):
    """Einheiten, deren Fläche kleiner als eine Zelle ist (Summe der Anteile < 1). Mit Zahl der Zellen mit Anteil ≥ 0,5."""
    je = zuordnung.groupby("einheit_id").agg(summe_anteile=("anteil", "sum"), zellen=("anteil", "size"),
                                             zellen_ab_halb=("anteil", lambda a: int((a >= 0.5).sum())),
                                             flaeche_km2=("flaeche_km2", "sum"))
    je = einheiten.set_index("einheit_id")[["name", "ebene", "weltbank_code"]].join(je, how="left")
    je[["summe_anteile", "zellen", "zellen_ab_halb", "flaeche_km2"]] = je[["summe_anteile", "zellen", "zellen_ab_halb", "flaeche_km2"]].fillna(0)
    return je[je["summe_anteile"] < 1].sort_values("summe_anteile").reset_index()


# --- Bauen, Speichern, Lesen -----------------------------------------------------


def ergebnis_ordner():
    return io.aleph_data_dir() / "laender" / "zell_einheiten"


def _git_stand():
    try:
        kopf = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).parent).stdout.strip()
        geaendert = subprocess.run(["git", "status", "--porcelain", "--", "aleph/layers/zell_einheiten.py", "aleph/layers/sondereinheiten.yaml"],
                                   capture_output=True, text=True, cwd=Path(__file__).parents[2]).stdout.strip()
        return {"commit": kopf, "zuordnungs_code_uncommitted": bool(geaendert)}
    except OSError:
        return {"commit": None, "zuordnungs_code_uncommitted": None}


def _sha(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def baue(schreiben=True):
    """Baut Einheiten und Zuordnung aus den geladenen Quellen und schreibt sie (Hilfsordner, Manifest, umbenennen)."""
    laender = ne.lade_laender()
    ne_manifest = json.loads((ne.ordner() / "manifest.json").read_text(encoding="utf-8"))
    umstritten, man_u = ne.lade_zusatz("umstritten")
    provinzen, man_p = ne.lade_zusatz("provinzen")
    m49, man_m = un_m49.lade()
    sonder = lade_sonderliste()
    if laender.total_bounds[0] < -180 or laender.total_bounds[2] > 180:
        raise ZuordnungFehler("Grenzdatei hat Längen außerhalb −180…180°.")
    wuerfel_gleich = pruefe_gegen_wuerfel()

    einheiten, geometrien, nicht_aufgenommen, land_gesamt, reparaturen = baue_einheiten(laender, umstritten, provinzen, m49, sonder)
    einheiten["flaeche_km2"] = [g.area / 1e6 for g in geometrien]
    zuordnung = baue_zuordnung(einheiten, geometrien)
    max_summe = pruefe_summen(zuordnung)
    max_verlust = pruefe_landflaeche(zuordnung, land_gesamt)
    einheiten["umriss_wkb"] = [shapely.to_wkb(g) for g in geometrien]  # projiziert, EPSG:6933

    if not schreiben:
        return einheiten, zuordnung, nicht_aufgenommen
    io.pruefe_speicher()
    ziel = ergebnis_ordner()
    hilfs = ziel.with_name(ziel.name + ".tmp")
    if hilfs.exists():
        shutil.rmtree(hilfs)
    hilfs.mkdir(parents=True)
    try:
        einheiten.to_parquet(hilfs / "einheiten.parquet", index=False)
        zuordnung.to_parquet(hilfs / "zuordnung.parquet", index=False)
        nicht_aufgenommen.to_parquet(hilfs / "nicht_aufgenommen.parquet", index=False)
        pd.testing.assert_frame_equal(pd.read_parquet(hilfs / "zuordnung.parquet"), zuordnung)
        manifest = {
            "erstellt_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "quellen": {
                "natural_earth_laender": {k: ne_manifest[k] for k in ("url", "version", "sha256", "abruf_utc")},
                "natural_earth_umstritten": {k: man_u[k] for k in ("url", "version", "sha256", "abruf_utc")},
                "natural_earth_provinzen": {k: man_p[k] for k in ("url", "version", "sha256", "abruf_utc")},
                "un_m49": {"ordner": man_m["ordner"], "abruf_utc": man_m["abruf_utc"],
                           "sha256": {k: v["sha256"] for k, v in man_m["seiten"].items()}},
                "sondereinheiten_yaml": {"datei": "aleph/layers/sondereinheiten.yaml", "sha256": _sha(SONDER_DATEI)},
            },
            "gitter": {"herkunft": "aleph/layers/vnp46a3.py (GITTER_BREITE, GITTER_LAENGE, ZELLGROESSE, _gitter_koordinaten)",
                       "zeilen": vnp46a3.GITTER_BREITE, "spalten": vnp46a3.GITTER_LAENGE, "zellgroesse_grad": vnp46a3.ZELLGROESSE,
                       "zeile_0": "Nordrand 90°", "spalte_0": "Westrand −180°", "gleich_wie_wuerfel_auf_ssd": wuerfel_gleich},
            "methode": {"projektion": PROJEKTION, "verdichtung_grad": VERDICHTUNG_GRAD, "doppel_anteil": DOPPEL_ANTEIL,
                        "min_rest_km2": MIN_REST_KM2, "ausgeschlossene_typen": list(AUSGESCHLOSSENE_TYPEN)},
            "code": _git_stand(),
            "reparierte_umrisse_nach_projektion": reparaturen,
            "reparierte_umrisse_zusatzdateien": {"umstritten": man_u.get("umriss_repariert_beim_lesen", []),
                                                 "provinzen": man_p.get("umriss_repariert_beim_lesen", [])},
            "ergebnis": {"einheiten": len(einheiten), "zeilen_zuordnung": len(zuordnung), "max_summe_anteile_je_zelle": max_summe,
                         "max_abweichung_je_zelle_gegen_landflaeche": max_verlust,
                         "nicht_aufgenommen": len(nicht_aufgenommen)},
            "dateien": {},
        }
        for datei in ("einheiten.parquet", "zuordnung.parquet", "nicht_aufgenommen.parquet"):
            manifest["dateien"][datei] = _sha(hilfs / datei)
        (hilfs / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except BaseException:
        shutil.rmtree(hilfs, ignore_errors=True)
        raise
    if ziel.exists():
        alt = ziel.with_name(ziel.name + ".alt")
        if alt.exists():
            shutil.rmtree(alt)
        ziel.rename(alt)
        hilfs.rename(ziel)
        shutil.rmtree(alt)
    else:
        hilfs.rename(ziel)
    return einheiten, zuordnung, nicht_aufgenommen


def lade():
    """Liest (einheiten, zuordnung, nicht_aufgenommen, manifest) von der SSD; prüft die Prüfsummen."""
    ordner = ergebnis_ordner()
    pfad = ordner / "manifest.json"
    if not pfad.is_file():
        raise ZuordnungFehler("Zell-Zuordnung ist nicht gebaut. Zuerst baue() ausführen.")
    manifest = json.loads(pfad.read_text(encoding="utf-8"))
    for datei, summe in manifest["dateien"].items():
        if _sha(ordner / datei) != summe:
            raise ZuordnungFehler(f"Prüfsumme von {datei} stimmt nicht mit dem Manifest überein.")
    return (pd.read_parquet(ordner / "einheiten.parquet"), pd.read_parquet(ordner / "zuordnung.parquet"),
            pd.read_parquet(ordner / "nicht_aufgenommen.parquet"), manifest)


def main():
    import time

    beginn = time.monotonic()
    einheiten, zuordnung, nicht = baue()
    print(f"Zell-Zuordnung gebaut: {len(einheiten)} Einheiten, {len(zuordnung)} Zeilen, "
          f"{len(nicht)} Einträge nicht aufgenommen, {time.monotonic() - beginn:.0f} s")


if __name__ == "__main__":
    main()
