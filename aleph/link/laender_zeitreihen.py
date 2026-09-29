"""Zeitreihen je Land: Nachtlicht monatlich und jährlich, Weltbank jährlich – NEBENEINANDER, kein Zusammenhang.

Auftrag 2026-09-29 (Länderansicht für die Präsentation). Evidenzstufe aller Werte: „beobachtet“ (gemessene
Strahldichte über Flächen, amtliche Weltbank-Zahlen). Es wird KEIN Zusammenhang gerechnet; die Oberfläche stellt
Licht und BIP nur nebeneinander. Die Regeln unten sind VOR der ersten Rechnung festgelegt.

Bausteine (nicht neu erfunden, nur aufgerufen):
- Monatswert je Land: Verknüpfungsgerüst `aleph/link/nachtlicht_einheiten.py` mit Standard-Einstellungen
  (`nachtlicht_je_einheit`, `je_weltbank_land`), genau wie das Länderfeld des Globus (worktree,
  `aleph/export/globus_laender.py`). Sicht „so wie die Weltbank zählt“ mit unklaren Gebieten.
- Jahreswert je Land: Regeln der Auswertung 2018 (`aleph/link/nachtlicht_bip_querschnitt.py`, `rechne_jahr`,
  `zelle_land_tabelle`, `Regeln()`): je Zelle Mittel der guten Monate (≥ 50 % beobachtet, kein Schnee-Verdacht),
  nur ab 6 guten Monaten; Landessumme mit Abdeckung nach Licht.
- Jahreszeit: Verfahren des Statistik-Gerüsts (`aleph/detect/trend.py`, `_jahreszeit_abziehen`; docs/methoden.md):
  Abweichung vom Median desselben Kalendermonats, Mindestzahl `Mindestlaengen.je_kalendermonat` (3).

Festlegungen (F):
F1 Status eines Monatswerts je Land (Reihenfolge der Prüfung):
   - „nicht_geladen“: mindestens 0,5 % der Landesfläche in diesem Monat noch nicht geladen (Grenze wie das
     Kennzeichen im Gerüst). Kein Punkt: Die Fläche wäre eine andere als in anderen Monaten.
   - „keine“: keine abgedeckte Fläche. Kein Punkt (Lücke).
   - „gering“: Abdeckung unter 90 % (Gerüst: dann keine Landessumme). Gezeigt wird die Teilsumme der abgedeckten
     Fläche als HOHLER, blasser Punkt – ausdrücklich eine Untergrenze, keine Landessumme.
   - „schnee“: Landessumme vorhanden, aber Schnee-Verdacht auf mindestens 5 % der Fläche (Grenze wie das
     Kennzeichen im Gerüst). Hohler Punkt: Das Gerüst zählt diese Zellen mit, der Wert kann durch Schnee erhöht sein.
   - „gueltig“: sonst. Voller Punkt.
F2 Gleitender 12-Monats-Durchschnitt: nachlaufend (Wert am Monat m = Mittel der Monate m−11 … m), NUR wenn alle
   12 Monate des Fensters den Status „gueltig“ haben. Fehlt einer, gibt es für dieses Fenster keinen Wert (Lücke).
   Grund: Jedes Fenster enthält dann jeden Kalendermonat genau einmal; ließe man einen Monat weg (typisch
   Wintermonate mit Schnee-Verdacht), wäre der Durchschnitt jahreszeitlich verschoben. Kein Modell, kein Auffüllen.
F3 Jahreszeit („saisonbereinigt“): Abweichung jedes gültigen Monatswerts vom Median derselben Kalendermonate
   (nur Status „gueltig“). Mindestlänge: für ALLE 12 Kalendermonate mindestens 3 gültige Werte, also mindestens
   3 volle Jahre (Regel `je_kalendermonat` = 3 des Gerüsts). Sonst „noch nicht bestimmbar“ mit Angabe, welcher
   Kalendermonat wie viele Werte hat. Grenzen: Mit 3 Jahren ist das Jahreszeitenmuster nur grob geschätzt; beim
   Median aus 3 Werten ist je Kalendermonat eine Abweichung genau 0 (Eigenschaft des Verfahrens).
F4 Jahreswert gültig, wenn: alle 12 Monate des Jahres im Würfel fertig (Zustand 1 oder 4), keine Fläche des Landes
   „nicht geladen“, Lichtsumme > 0 und Abdeckung nach Licht ≥ 90 % (Regel 5 der Auswertung 2018). Reinheit
   (Regel 4) und abweichendes Weltbank-Gebiet (Regel 3) schließen hier NICHT aus, sie werden als Kennzeichen gezeigt:
   Es wird nicht über Länder hinweg gerechnet, sondern ein Land neben seine eigene Weltbank-Zahl gestellt.
F5 Pro Kopf: Licht geteilt durch die Bevölkerung (SP.POP.TOTL) desselben Kalenderjahres. Nicht gerechnet, wenn die
   Weltbank-Tabelle „BIP pro Kopf“ des Landes als `nicht_verwenden` markiert (CYP, MAR, RUS, TZA, UKR: Bevölkerung
   passt nicht zum Gebiet) – dann passt die Bevölkerung auch nicht als Nenner für das Licht.
F6 Pro km²: Licht geteilt durch die Fläche des Landes in der Weltbank-Sicht (fest, Umrisse Stand Mai 2022). Eigene
   Kennzahl ohne BIP-Partner; eher Siedlungsdichte als Wirtschaftskraft.
F7 Index 2018 = 100: Jahreswert geteilt durch den Jahreswert 2018 (Licht nach F4, BIP und BIP pro Kopf der
   Weltbank), gerechnet mit ungerundeten Werten, auf ganze Zahlen gerundet. Ohne gültigen Wert 2018 kein Index.
F8 Weltbank-Jahre: alle Kalenderjahre mit mindestens einem angezeigten Nachtlicht-Monat (wie das Länderfeld), nie
   ab 2023.
F9 Rundung der Ausgabe: Licht auf 3 gültige Ziffern (für die Kurven; die Tabelle zeigt 2 wie das Länderfeld),
   Anteile in ganzen Prozent (abgerundet).

Zeiträume: nur vor 2023-01. Monate und Weltbank-Werte ab 2023 werden verweigert (Test).

Aufruf: python -m aleph.link.laender_zeitreihen   (schreibt auswertungen/laender_zeitreihen/ergebnis.json auf die SSD)
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from aleph.core import io
from aleph.detect.statistik import Mindestlaengen

VERSION = "0.2.0"  # 0.2.0: Texte nach Auflagen statistik-pruefer 2026-09-29, Rechnung unverändert
FELD = "allangle"
REGION = "afrika_europa_asien"
GESPERRT_AB = (2023, 1)
ERSTES_JAHR = 2013
INDEX_BASISJAHR = 2018
AUSGABE_ORDNER = ("auswertungen", "laender_zeitreihen")

MIN_ABDECKUNG = 0.9          # wie VerknuepfungsEinstellungen.min_abdeckung und Regel 5 der Auswertung 2018
SCHNEE_KENNZEICHEN_AB = 0.05  # wie das Kennzeichen „Schnee-Verdacht“ im Gerüst (_kennzeichen)
NICHT_GELADEN_AB = 0.005      # wie das Kennzeichen „nicht geladen“ im Gerüst (_kennzeichen)
FENSTER = 12
JE_KALENDERMONAT = Mindestlaengen().je_kalendermonat  # 3, Statistik-Gerüst

WB_INDIKATOREN = {"NY.GDP.MKTP.KD": "bip_real", "NY.GDP.PCAP.KD": "bip_pro_kopf", "SP.POP.TOTL": "bevoelkerung"}
WB_QUELLE = "The World Bank: World Development Indicators (CC BY 4.0); Bevölkerung: UN World Population Prospects"

REGELN_TEXT = {
    "status": "voll: Summe über die gemessene Fläche (mindestens 90 % des Landes) ohne Schnee-Verdacht; hohl: "
              "Schnee-Verdacht auf ≥ 5 % der Fläche (nach Fläche, nicht nach Licht gezählt); hohl und blass: unter 90 % "
              "der Fläche gemessen, gezeigt ist nur die Teilsumme (Untergrenze); keine Punkte: keine Messung oder Teile des "
              "Landes noch nicht geladen. Unterschiede von Monat zu Monat können aus der wechselnden Abdeckung kommen; der "
              "Schnee-Verdacht erfasst nicht alle verschneiten Monate (z. B. Helsinki 2019-01)",
    "gleitend": "nachlaufender 12-Monats-Durchschnitt, nur wenn alle 12 Monate des Fensters voll gültig sind; "
                "sonst Lücke (ein fehlender Monat würde den Durchschnitt jahreszeitlich verschieben)",
    "saison": "Abweichung vom Median derselben Kalendermonate (Statistik-Gerüst, trend.py); nur wenn jeder "
              "Kalendermonat mindestens 3 gültige Werte hat, also ab 3 vollen Jahren. Der Median stammt aus denselben "
              "Jahren, der Wert selbst eingeschlossen: beschreibende Zerlegung, kein Vergleich mit früheren Jahren, "
              "keine Anomalie-Bewertung",
    "jahr": "Regeln der Auswertung 2018: je Zelle Mittel der guten Monate (≥ 50 % beobachtet, kein Schnee-Verdacht), "
            "ab 6 guten Monaten; Landessumme nur bei ≥ 90 % des Lichts mit Jahreswert und vollständig geladenem Land. "
            "Welche Monate gut sind, wechselt von Jahr zu Jahr; deshalb sind Jahreswerte zwischen den Jahren nur bedingt "
            "vergleichbar (Anteil des Lichts aus Zellen mit nur 6–8 guten Monaten steht in der Tabelle)",
    "pro_kopf": "Licht geteilt durch die Bevölkerung desselben Jahres (Weltbank SP.POP.TOTL); nicht für Länder, deren "
                "Bevölkerungszahl laut Weltbank-Tabelle nicht zum Gebiet passt. Monatswerte teilen durch die "
                "Jahresbevölkerung; zum Jahreswechsel entsteht dadurch eine kleine Stufe in Höhe des Bevölkerungswachstums",
    "je_km2": "Licht geteilt durch die Landesfläche (Weltbank-Sicht); eher Siedlungsdichte als Wirtschaftskraft",
    "index": "Jahreswert geteilt durch den Jahreswert 2018, mal 100; ohne gültigen Wert 2018 kein Index",
}


class ZeitraumGesperrt(ValueError):
    """Monate oder Jahre ab 2023 (Validierungs- und Endtestzeitraum)."""


def _pruefe_monat(monat: tuple[int, int]) -> None:
    if tuple(monat) >= GESPERRT_AB:
        raise ZeitraumGesperrt(f"{monat[0]:04d}-{monat[1]:02d}: 2023–2025 ist Validierungs- und Endtestzeitraum.")


def _sig(x, stellen=3):
    if x is None or not np.isfinite(x):
        return None
    if x == 0:
        return 0.0
    return float(round(float(x), stellen - 1 - int(math.floor(math.log10(abs(x))))))


def _pz(x):
    if x is None or not np.isfinite(x):
        return None
    return int(np.floor(float(x) * 100 + 1e-9))


# ------------------------------------------------------------------ reine Rechenregeln (mit künstlichen Daten getestet)


def monats_status(abdeckung, anteil_schnee, anteil_nicht_geladen, licht_summe_abgedeckt) -> str:
    """F1. Alle Anteile 0–1; `licht_summe_abgedeckt` NaN, wenn nichts abgedeckt ist."""
    if np.isfinite(anteil_nicht_geladen) and anteil_nicht_geladen >= NICHT_GELADEN_AB:
        return "nicht_geladen"
    if not (np.isfinite(abdeckung) and abdeckung > 0) or not np.isfinite(licht_summe_abgedeckt):
        return "keine"
    if abdeckung < MIN_ABDECKUNG:
        return "gering"
    if np.isfinite(anteil_schnee) and anteil_schnee >= SCHNEE_KENNZEICHEN_AB:
        return "schnee"
    return "gueltig"


def _monatsnummer(monat: str) -> int:
    j, m = (int(t) for t in monat.split("-"))
    return j * 12 + (m - 1)


def gleitender_durchschnitt(monate: list[str], werte: list, status: list[str], fenster: int = FENSTER) -> list[dict]:
    """F2. Nachlaufend; nur Fenster mit `fenster` aufeinanderfolgenden Kalendermonaten, alle „gueltig“."""
    gueltig = {_monatsnummer(m): float(w) for m, w, s in zip(monate, werte, status)
               if s == "gueltig" and w is not None and np.isfinite(w)}
    aus = []
    for m in monate:
        n = _monatsnummer(m)
        teil = [gueltig.get(k) for k in range(n - fenster + 1, n + 1)]
        if all(t is not None for t in teil):
            aus.append({"monat": m, "wert": float(np.mean(teil))})
    return aus


def jahreszeit_abweichung(monate: list[str], werte: list, status: list[str], je_kalendermonat: int = JE_KALENDERMONAT) -> dict:
    """F3. Rückgabe {bestimmbar, grund, anzahl_je_kalendermonat, median_je_kalendermonat, werte[{monat, wert}]}."""
    je_k: dict[int, list[float]] = {k: [] for k in range(1, 13)}
    for m, w, s in zip(monate, werte, status):
        if s == "gueltig" and w is not None and np.isfinite(w):
            je_k[int(m[5:7])].append(float(w))
    anzahl = {k: len(v) for k, v in je_k.items()}
    zu_wenig = [k for k, n in anzahl.items() if n < je_kalendermonat]
    if zu_wenig:
        jahre_da = min(anzahl.values())
        return {"bestimmbar": False, "anzahl_je_kalendermonat": anzahl,
                "grund": f"noch nicht bestimmbar – benötigt mindestens {je_kalendermonat} Jahre "
                         f"(je Kalendermonat {je_kalendermonat} voll gültige Werte); "
                         f"{len(zu_wenig)} Kalendermonat(e) mit weniger, kleinste Zahl {jahre_da}",
                "werte": []}
    median = {k: float(np.median(v)) for k, v in je_k.items()}
    aus = [{"monat": m, "wert": float(w) - median[int(m[5:7])]} for m, w, s in zip(monate, werte, status)
           if s == "gueltig" and w is not None and np.isfinite(w)]
    return {"bestimmbar": True, "grund": "", "anzahl_je_kalendermonat": anzahl, "median_je_kalendermonat": median,
            "werte": aus}


def jahreswert_gueltig(z) -> tuple[bool, str]:
    """F4 für eine Zeile aus `laender_jahr` (Series mit licht_summe, abdeckung_licht, flaeche_nicht_geladen)."""
    if z is None:
        return False, "keine Zelle in der Zuordnung"
    if z["flaeche_nicht_geladen"] > 0:
        return False, "Teile des Landes in diesem Jahr noch nicht geladen"
    if not z["licht_summe"] > 0:
        return False, "Lichtsumme 0 oder nicht bestimmbar"
    if not z["abdeckung_licht"] >= MIN_ABDECKUNG:
        return False, f"nur {_pz(z['abdeckung_licht'])} % des Lichts mit gültigem Jahreswert (Grenze 90 %)"
    return True, ""


def index(werte: dict, basis=INDEX_BASISJAHR) -> dict:
    """F7. `werte`: {jahr: Wert oder None}. Ohne gültige Basis leeres Ergebnis."""
    b = werte.get(basis)
    if b is None or not np.isfinite(b) or b <= 0:
        return {}
    return {j: int(round(100.0 * w / b)) for j, w in werte.items() if w is not None and np.isfinite(w)}


# ------------------------------------------------------------------ Lesen (echte Daten)


def fertige_monate() -> list[tuple[int, int]]:
    from aleph.layers import vnp46a3

    return [(j, m) for j in range(ERSTES_JAHR, GESPERRT_AB[0]) for m in range(1, 13)
            if vnp46a3.monatsstatus(j, m) in (vnp46a3.MONAT_FERTIG, vnp46a3.MONAT_REGION_VOLLSTAENDIG)]


def monatswerte(monate: list[tuple[int, int]]) -> pd.DataFrame:
    """Je Monat und Weltbank-Land die Gerüst-Werte (gleiche Einstellungen wie das Länderfeld)."""
    from aleph.layers import vnp46a3, vnp46a3_regionen, zell_einheiten
    from aleph.link.nachtlicht_einheiten import VerknuepfungsEinstellungen, je_weltbank_land, nachtlicht_je_einheit

    e = VerknuepfungsEinstellungen()
    einheiten, zuordnung, _, _ = zell_einheiten.lade()
    wl = zell_einheiten.lade_sonderliste().get("weltbank_laender", {})
    rein = zell_einheiten.reinheit(einheiten, zuordnung, schwelle=e.reinheit_schwelle)
    geliefert = vnp46a3_regionen.zellmaske(vnp46a3.lies_referenz_positionen(), 720, 1440)
    variablen = [f"{FELD}_mittel_beobachtet", f"{FELD}_gueltige_pixel", f"{FELD}_aufgefuellt_pixel"]
    teile = []
    for monat in monate:
        _pruefe_monat(monat)
        zustand = vnp46a3.monatsstatus(*monat)
        ds = vnp46a3.lies_monate_mit_region([monat], variablen, REGION)
        ng = ds["nicht_geladen"].values[0] & geliefert if zustand == vnp46a3.MONAT_REGION_VOLLSTAENDIG else None
        text = {1: "vollständig", 4: "nur Afrika-Europa-Asien"}.get(zustand, f"Zustand {zustand}")
        je = nachtlicht_je_einheit(monat, text, ds[variablen[0]].values[0], ds[variablen[1]].values[0],
                                   ds[variablen[2]].values[0], ng, zuordnung, ds["breite"].values, e)
        land = je_weltbank_land(je, einheiten, wl, rein, e)
        teile.append(land[["weltbank_code", "monat", "flaeche_km2", "abdeckung", "anteil_nicht_geladen",
                           "anteil_schnee_verdacht", "licht_summe_abgedeckt", "licht_summe", "gebiet_weltbank",
                           "reinheit", "kennzeichen"]])
        print(f"  Monat {monat[0]}-{monat[1]:02d}: {int(land['licht_summe'].notna().sum())} Landessummen", flush=True)
    return pd.concat(teile, ignore_index=True)


def jahreswerte(jahre: list[int]) -> dict[int, pd.DataFrame]:
    """Je vollständigem Jahr die Ländertabelle nach den Regeln der Auswertung 2018."""
    from aleph.layers import zell_einheiten
    from aleph.link.nachtlicht_bip_querschnitt import Regeln, rechne_jahr, zelle_land_tabelle

    r = Regeln()
    einheiten, zuordnung, _, _ = zell_einheiten.lade()
    t = zelle_land_tabelle(einheiten, zuordnung, zell_einheiten.zellflaechen_km2(), r)
    aus = {}
    for jahr in jahre:
        _pruefe_monat((jahr, 1))
        g, _ = rechne_jahr(jahr, t, r)
        aus[jahr] = g
        print(f"  Jahr {jahr}: {len(g)} Länder", flush=True)
    return aus


def weltbank_werte(jahre: list[int]) -> tuple[dict, str]:
    from aleph.layers import weltbank

    if any(j >= GESPERRT_AB[0] for j in jahre):
        raise ZeitraumGesperrt("Weltbank-Werte ab 2023 werden nicht gelesen.")
    t = weltbank.lese_tabelle()
    t = t[t["indikator"].isin(list(WB_INDIKATOREN)) & t["jahr"].isin(jahre)]
    werte: dict = {}
    for z in t.itertuples(index=False):
        land = werte.setdefault(z.land_iso3, {"name": z.land_name, "jahre": {}})
        e = land["jahre"].setdefault(int(z.jahr), {})
        nutzbar = bool(z.hat_wert) and not bool(z.nicht_verwenden)
        e[WB_INDIKATOREN[z.indikator]] = {"wert": float(z.wert) if nutzbar else None,
                                          "vorlaeufig": bool(z.vorlaeufig), "nicht_verwenden": bool(z.nicht_verwenden)}
    return werte, (str(t["abruf_utc"].iloc[0]) if len(t) else "")


# ------------------------------------------------------------------ Zusammenbau je Land


def _wb(wb_land, jahr, art):
    e = ((wb_land or {}).get("jahre") or {}).get(jahr, {}).get(art)
    return None if not e else e["wert"]


def _pro_kopf_erlaubt(wb_land) -> bool:
    for e in ((wb_land or {}).get("jahre") or {}).values():
        if (e.get("bip_pro_kopf") or {}).get("nicht_verwenden"):
            return False
    return True


def reihe_je_land(code: str, mon: pd.DataFrame, jahr_tab: dict[int, pd.DataFrame], wb_land: dict | None,
                  alle_monate: list[str]) -> dict:
    """Alle Werte eines Landes. `mon`: Monatszeilen dieses Landes (Spalten wie `monatswerte`)."""
    mon = mon.set_index("monat")
    pk_ok = _pro_kopf_erlaubt(wb_land)
    flaeche = float(mon["flaeche_km2"].iloc[0]) if len(mon) else None
    monate, status = [], []
    reihen = {"summe": [], "pro_kopf": [], "je_km2": []}
    punkte = []
    for m in alle_monate:
        if m not in mon.index:
            continue
        z = mon.loc[m]
        s = monats_status(z["abdeckung"], z["anteil_schnee_verdacht"], z["anteil_nicht_geladen"], z["licht_summe_abgedeckt"])
        wert = None
        if s in ("gueltig", "schnee"):
            wert = float(z["licht_summe"])
        elif s == "gering":
            wert = float(z["licht_summe_abgedeckt"])
        bev = _wb(wb_land, int(m[:4]), "bevoelkerung") if pk_ok else None
        pk = wert / bev if (wert is not None and bev) else None
        km2 = wert / flaeche if (wert is not None and flaeche) else None
        monate.append(m)
        status.append(s)
        reihen["summe"].append(wert)
        reihen["pro_kopf"].append(pk)
        reihen["je_km2"].append(km2)
        punkte.append({"monat": m, "status": s, "summe": _sig(wert), "pro_kopf": _sig(pk), "je_km2": _sig(km2),
                       "abdeckung": _pz(z["abdeckung"]), "schnee": _pz(z["anteil_schnee_verdacht"]),
                       "nicht_geladen": _pz(z["anteil_nicht_geladen"])})
    gleitend = {k: [{"monat": g["monat"], "wert": _sig(g["wert"])} for g in gleitender_durchschnitt(monate, v, status)]
                for k, v in reihen.items()}
    saison = {}
    for k, v in reihen.items():
        sz = jahreszeit_abweichung(monate, v, status)
        sz["werte"] = [{"monat": w["monat"], "wert": _sig(w["wert"])} for w in sz["werte"]]
        sz.pop("median_je_kalendermonat", None)
        saison[k] = sz

    jahre_wb = sorted({int(m[:4]) for m in monate})
    jahre = {}
    roh = {"licht_summe": {}, "licht_pro_kopf": {}, "licht_je_km2": {}, "bip_real": {}, "bip_pro_kopf": {}}
    for jahr in sorted(set(jahre_wb) | set(jahr_tab)):
        g = jahr_tab.get(jahr)
        z = g.loc[code] if (g is not None and code in g.index) else None
        e = {"jahr": jahr, "licht_berechnet": g is not None}
        if g is not None:
            ok, grund = jahreswert_gueltig(z)
            e.update({"licht_gueltig": ok, "licht_grund": grund})
            if z is not None:
                e.update({"abdeckung_licht": _pz(z["abdeckung_licht"]), "reinheit_licht": _pz(z["reinheit_licht"]),
                          "anteil_wenige_monate": _pz(z["anteil_wenige_monate"]), "anteil_nord65": _pz(z["anteil_nord65"])})
            if ok:
                bev = _wb(wb_land, jahr, "bevoelkerung") if pk_ok else None
                roh["licht_summe"][jahr] = float(z["licht_summe"])
                roh["licht_je_km2"][jahr] = float(z["licht_summe"]) / float(z["flaeche"])
                if bev:
                    roh["licht_pro_kopf"][jahr] = float(z["licht_summe"]) / bev
        else:
            e.update({"licht_gueltig": False, "licht_grund": "Jahr im Würfel noch nicht vollständig (weniger als 12 fertige Monate)"})
        for art in ("bip_real", "bip_pro_kopf", "bevoelkerung"):
            w = _wb(wb_land, jahr, art)
            ein = ((wb_land or {}).get("jahre") or {}).get(jahr, {}).get(art) or {}
            e[art] = _sig(w)
            e[art + "_vorlaeufig"] = bool(ein.get("vorlaeufig"))
            e[art + "_nicht_verwenden"] = bool(ein.get("nicht_verwenden"))
            if art != "bevoelkerung" and w is not None:
                roh[art][jahr] = w
        e["licht_summe"] = _sig(roh["licht_summe"].get(jahr))
        e["licht_pro_kopf"] = _sig(roh["licht_pro_kopf"].get(jahr))
        e["licht_je_km2"] = _sig(roh["licht_je_km2"].get(jahr))
        jahre[str(jahr)] = e
    idx = {k: {str(j): v for j, v in index(w).items()} for k, w in roh.items()}

    letzte = mon.iloc[-1] if len(mon) else None
    basis = jahr_tab.get(INDEX_BASISJAHR)
    zb = basis.loc[code] if (basis is not None and code in basis.index) else None
    kennzeichen = {
        "gebiet_weltbank": None if letzte is None else letzte["gebiet_weltbank"],
        "reinheit_unter_50": bool(zb is not None and np.isfinite(zb["reinheit_licht"]) and zb["reinheit_licht"] < 0.5),
        "nord65_prozent": None if zb is None else _pz(zb["anteil_nord65"]),
        "monate_gering": sum(1 for s in status if s == "gering"),
        "monate_schnee": sum(1 for s in status if s == "schnee"),
        "monate_nicht_geladen": sum(1 for s in status if s == "nicht_geladen"),
        "pro_kopf_erlaubt": pk_ok,
        "tansania": code == "TZA",
        "geruest_text": None if letzte is None else (letzte["kennzeichen"] or ""),
    }
    return {"code": code, "name": (wb_land or {}).get("name", code), "flaeche_km2": _sig(flaeche),
            "monate": punkte, "gleitend": gleitend, "saison": saison, "jahre": jahre, "index": idx,
            "kennzeichen": kennzeichen}


def _git_stand():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10,
                              cwd=Path(__file__).resolve().parents[2]).stdout.strip()
    except Exception:
        return ""


def rechne(monate: list[tuple[int, int]] | None = None) -> dict:
    monate = fertige_monate() if monate is None else list(monate)
    for m in monate:
        _pruefe_monat(m)
    if not monate:
        raise ValueError("Kein fertiger Monat vor 2023 im Würfel.")
    namen = [f"{j:04d}-{m:02d}" for j, m in monate]
    volle_jahre = sorted(j for j in {j for j, _ in monate} if all((j, m) in set(monate) for m in range(1, 13)))
    print(f"Monate: {len(monate)} ({namen[0]} bis {namen[-1]}), volle Jahre: {volle_jahre}", flush=True)
    mon = monatswerte(monate)
    jahr_tab = jahreswerte(volle_jahre)
    jahre_wb = sorted({j for j, _ in monate})
    wb, abruf = weltbank_werte(jahre_wb)
    laender = {}
    for code, teil in mon.groupby("weltbank_code"):
        laender[code] = reihe_je_land(code, teil, jahr_tab, wb.get(code), namen)
    return {
        "titel": "Nachtlicht und Weltbank-Werte je Land, nebeneinander",
        "evidenzstufe": "beobachtet",
        "hinweis": "Nebeneinander gestellt, kein Zusammenhang behauptet.",
        "monate": namen, "volle_jahre": volle_jahre, "weltbank_jahre": jahre_wb, "index_basisjahr": INDEX_BASISJAHR,
        "regeln": REGELN_TEXT,
        "grenzen": {"min_abdeckung": MIN_ABDECKUNG, "schnee_kennzeichen_ab": SCHNEE_KENNZEICHEN_AB,
                    "nicht_geladen_ab": NICHT_GELADEN_AB, "fenster": FENSTER, "je_kalendermonat": JE_KALENDERMONAT},
        "einheiten": {"summe": "nW·cm⁻²·sr⁻¹ × km²", "pro_kopf": "nW·cm⁻²·sr⁻¹ × km² je Einwohner",
                      "je_km2": "nW·cm⁻²·sr⁻¹", "bip_real": "US-Dollar, konstante Preise (Basisjahr 2015)",
                      "bip_pro_kopf": "US-Dollar je Einwohner, konstante Preise (Basisjahr 2015)"},
        "quelle_licht": "NASA VIIRS Black Marble VNP46A3 (AllAngle, schneefrei, nur beobachtete Pixel)",
        "quelle_weltbank": WB_QUELLE, "weltbank_abruf": abruf,
        "sicht": "so wie die Weltbank zählt (mit unklaren Gebieten)",
        "laender": laender,
        "version": VERSION, "git": _git_stand(),
        "erstellt_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def schreibe(ergebnis: dict) -> Path:
    ordner = io.aleph_data_dir().joinpath(*AUSGABE_ORDNER)
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / "ergebnis.json"
    hilfs = pfad.with_suffix(".json.tmp")
    hilfs.write_text(json.dumps(ergebnis, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    hilfs.replace(pfad)
    return pfad


def main(argv=None) -> int:
    e = rechne()
    pfad = schreibe(e)
    print(f"{len(e['laender'])} Länder, geschrieben: {pfad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
